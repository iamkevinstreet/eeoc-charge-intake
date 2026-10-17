"""Run the extraction evaluation.

    python -m eeoc_intake.evals.run --cases eeoc_intake/data/generated/cases.jsonl
    python -m eeoc_intake.evals.run --cases ... --fake      # offline smoke run, no API calls

Scores per case:

- field_accuracy: share of the ten scored fields whose final value equals the ground truth
- f_<field>: 1 or 0 for each scored field, so the by-tag table shows which fields fail on which documents
- unsupported_removed: fields the model filled whose quoted span was not on the cited page; verification
  emptied them before anyone saw them. The share of raw filled fields that were unsupported is
  unsupported_rate.
- false_abstentions: fields left empty that the document did support
- guesses: fields filled when the document had no value
- empty_precision / empty_recall: how well "I could not find it" matches the documents that lacked a value

The runner adds latency, cost and failures. Offline runs land in eeoc_intake/evals/results/smoke/ (ignored by
git); live runs in eeoc_intake/evals/results/live/, which is committed so the case study can cite it.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from kds.evals.case import EvalCase, load_cases
from kds.evals.metrics import exact_match, null_metrics
from kds.evals.runner import run_eval
from kds.llm.adapter import ModelAdapter
from kds.llm.fake import FakeProvider

from eeoc_intake.extract import Extraction, extract
from eeoc_intake.fake import SCORED_FIELDS, gold_responder

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def score(case: EvalCase, ex: Extraction) -> dict:
    values = ex.record.values()
    gold = {f: case.expected.get(f) for f in SCORED_FIELDS}
    per_field = {f: _same(values.get(f), gold.get(f)) for f in SCORED_FIELDS}
    nulls = null_metrics(values, gold, SCORED_FIELDS)
    raw_filled = sum(1 for f in SCORED_FIELDS if getattr(ex.raw, f).value not in (None, "", []))
    removed = [f for f in ex.removed if f in SCORED_FIELDS]
    scores = {
        "field_accuracy": round(sum(per_field.values()) / len(per_field), 4),
        "raw_filled_fields": raw_filled,
        "unsupported_removed": len(removed),
        "unsupported_rate": round(len(removed) / raw_filled, 4) if raw_filled else 0.0,
        "false_abstentions": nulls["false_abstentions"],
        "guesses": nulls["guesses"],
        "empty_precision": nulls["precision"],
        "empty_recall": nulls["recall"],
        "model_latency_ms": ex.latency_ms,
    }
    for f in SCORED_FIELDS:
        scores[f"f_{f}"] = int(per_field[f])
    # Non-numeric entries are kept in the results file for inspection; the summary ignores them.
    scores["values"] = values
    scores["gold"] = gold
    scores["removed"] = removed
    return scores


def _same(a: object, b: object) -> bool:
    """Exact match after normalisation; a one-item list and its item count as the same value."""
    if isinstance(a, list) and len(a) == 1 and not isinstance(b, list):
        a = a[0]
    if isinstance(b, list) and len(b) == 1 and not isinstance(a, list):
        b = b[0]
    return exact_match(a, b)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--name", default="eeoc-extraction")
    ap.add_argument("--fake", action="store_true", help="use the offline stand-in provider")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument(
        "--out", type=Path, default=None, help="default: results/smoke for --fake, results/live otherwise"
    )
    ap.add_argument(
        "--dump",
        type=int,
        default=0,
        help="also write the full extraction (record, raw output, pages) for the first N cases",
    )
    args = ap.parse_args()
    if args.out is None:
        args.out = RESULTS_DIR / ("smoke" if args.fake else "live")
    dump_dir = (
        args.out / "extractions" / f"{args.name}-{datetime.now(UTC):%Y%m%dT%H%M%SZ}" if args.dump else None
    )

    cases = load_cases(args.cases)[: args.limit]
    adapter = (
        ModelAdapter(FakeProvider(responder=gold_responder(cases)), model="fake-model")
        if args.fake
        else ModelAdapter()
    )

    dumped = 0

    def system_fn(case: EvalCase) -> Extraction:
        nonlocal dumped
        ex = extract(adapter, case.input["charge_pdf"], case.input["notice_pdf"])
        if dump_dir is not None and dumped < args.dump:
            dump_dir.mkdir(parents=True, exist_ok=True)
            (dump_dir / f"{case.id}.json").write_text(
                json.dumps(
                    {
                        "case_id": case.id,
                        "tags": case.tags,
                        "expected": case.expected,
                        "model": ex.model,
                        "cost_usd": ex.cost_usd,
                        "latency_ms": ex.latency_ms,
                        "record": ex.record.model_dump(),
                        "raw": ex.raw.model_dump(),
                        "removed": ex.removed,
                        "pages": {"charge": ex.charge_pages, "notice": ex.notice_pages},
                    },
                    indent=1,
                ),
                encoding="utf-8",
            )
            dumped += 1
        return ex

    run = run_eval(
        name=args.name,
        cases=cases,
        adapter=adapter,
        system_fn=system_fn,
        scorer_fn=score,
        out_dir=args.out,
        keep_output=False,
    )
    print((args.out / f"{args.name}-latest.md").read_text())
    print(f"spent ${adapter.spent_usd:.4f}; failures {run.failures}/{run.cases}")


if __name__ == "__main__":
    main()
