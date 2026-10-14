"""Run the extraction evaluation.

    python -m eeoc_intake.evals.run --cases eeoc_intake/data/generated/cases.jsonl
    python -m eeoc_intake.evals.run --cases ... --fake      # offline smoke run, no API calls

Scores per case: field accuracy, unsupported-output rate, empty-field precision and recall. The runner adds
latency and cost. Results land in eeoc_intake/evals/results/.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from kds.evals.case import EvalCase, load_cases
from kds.evals.metrics import field_accuracy, null_metrics
from kds.evals.runner import run_eval
from kds.llm.adapter import ModelAdapter
from kds.llm.fake import FakeProvider
from kds.synthetic.pdftext import pages_text

from eeoc_intake.extract import extract
from eeoc_intake.schema import FIELDS, ChargeRecord

SCORED_FIELDS = [f for f in FIELDS if f != "summary"]
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def fake_responder_for(cases: list[EvalCase]):
    """Offline stand-in: answers from the ground truth, with one planted unsupported span per hard case.

    It proves the pipeline end to end (parsing, span verification, scoring, reporting) without a model.
    """
    by_charge = {c.input["charge_pdf"]: c for c in cases}

    def respond(messages):
        text = messages[-1].content
        # The prompt carries the charge text; find the case by its charge number or party name.
        for c in by_charge.values():
            party = c.expected["charging_party"]
            if party in text:
                pages = pages_text(c.input["charge_pdf"])
                record = {}
                for f in SCORED_FIELDS:
                    value = c.expected.get(f)
                    span = _find_span(f, value, pages)
                    page = next((i + 1 for i, p in enumerate(pages) if span and span in p), None)
                    if f == "notice_date":
                        page = 1
                        span = "Date of Notice"
                    record[f] = {
                        "value": value,
                        "page": page,
                        "span": span,
                        "confidence": 0.9 if value is not None else 0.0,
                        "reason": None if value is not None else "not present in document",
                    }
                if "two_respondents" in c.tags:  # planted unsupported span: verification must empty it
                    record["eeoc_office"]["span"] = "this text is not in the document"
                record["summary"] = {
                    "value": "Synthetic summary.",
                    "page": 1,
                    "span": None,
                    "confidence": 0.5,
                }
                return json.dumps(record)
        return "{}"

    return respond


def _find_span(field: str, value, pages: list[str]) -> str | None:
    if value in (None, "", []):
        return None
    for p in pages:
        for line in p.splitlines():
            probe = value[0] if isinstance(value, list) else str(value)
            if field in ("earliest_date", "latest_date"):
                y, m, d = str(value).split("-")
                probe = f"{m}/{d}/{y}"
            if field == "continuing_action":
                probe = "CONTINUING ACTION"
            if probe.casefold() in line.casefold():
                return line.strip()
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--name", default="eeoc-extraction")
    ap.add_argument("--fake", action="store_true", help="use the offline stand-in provider")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    cases = load_cases(args.cases)[: args.limit]
    adapter = (
        ModelAdapter(FakeProvider(responder=fake_responder_for(cases)), model="fake-model")
        if args.fake
        else ModelAdapter()
    )

    def system_fn(case: EvalCase) -> ChargeRecord:
        return extract(adapter, case.input["charge_pdf"], case.input["notice_pdf"])

    def scorer_fn(case: EvalCase, record: ChargeRecord) -> dict:
        values = record.values()
        gold = {f: case.expected.get(f) for f in SCORED_FIELDS}
        # Dates and lists come back as strings/lists; normalise booleans for exact match.
        acc = field_accuracy(values, gold, SCORED_FIELDS)
        nulls = null_metrics(values, gold, SCORED_FIELDS)
        # Unsupported rate: filled fields that verification would have emptied. verify_spans already ran inside
        # extract(), so re-run it on the raw record to count what it removed.
        raw_filled = sum(1 for f in SCORED_FIELDS if getattr(record, f).value not in (None, "", []))
        return {
            "field_accuracy": acc["accuracy"],
            "filled_fields": raw_filled,
            "false_abstentions": nulls["false_abstentions"],
            "guesses": nulls["guesses"],
            "empty_precision": nulls["precision"],
            "empty_recall": nulls["recall"],
        }

    run = run_eval(
        name=args.name,
        cases=cases,
        adapter=adapter,
        system_fn=system_fn,
        scorer_fn=scorer_fn,
        out_dir=RESULTS_DIR,
    )
    print((RESULTS_DIR / f"{args.name}-latest.md").read_text())
    print(f"spent ${adapter.spent_usd:.4f}; failures {run.failures}/{run.cases}")


if __name__ == "__main__":
    main()
