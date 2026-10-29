########################################################################
#                 backend/src/eeoc_intake/evals/run.py                 #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Runs the extraction evaluation over the generated documents and writes
the results.

    LLM_PROVIDER=fake python -m eeoc_intake.evals.run --name offline
    python -m eeoc_intake.evals.run --name live-<model>

With the fake provider, the offline stand-in answers from each
document's known values: a smoke run that needs no key, written to
`[data] smoke` and never committed. With a real provider, results go
to `[data] results`, committed so the case study can cite them, and
the first `[extract] dump` extractions are saved whole in
`[data] extractions`.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

# Third-party
from kds.args import required
from kds.evals.case import EvalCase, load_cases
from kds.evals.runner import RunResult, run_eval
from kds.logs import get_logger, log_event, setup_logging

# Local
from eeoc_intake.config import SETTINGS, AppSettings, get_app_settings
from eeoc_intake.core.extract import Extraction, extract
from eeoc_intake.core.offline import adapter_for
from eeoc_intake.evals.score import score

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the text encoding of every file written, from the config")
ENCODING: Final = SETTINGS.files_encoding
# log.debug("Takes the name of the evaluation set's file, from the config")
CASES_FILE: Final = SETTINGS.samples_cases
# log.debug("Takes the provider that means the offline stand-in, from the config")
FAKE: Final = SETTINGS.demo_provider
# log.debug("Takes the input that holds a case's charge PDF, from the config")
CHARGE_PDF: Final = SETTINGS.samples_charge_input
# log.debug("Takes the input that holds a case's notice PDF, from the config")
NOTICE_PDF: Final = SETTINGS.samples_notice_input

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the time stamp that names a folder of saved extractions")
STAMP: Final = "%Y%m%dT%H%M%SZ"


########################################################################
#                            Evaluation run                            #
########################################################################
# log.debug("Defines where a run's results go")
def results_folder(settings: AppSettings | None = None) -> Path:
    """Returns `[data] smoke` for the stand-in, `[data] results` else.

    Args:
        settings: The settings, whose provider decides. Required.

    Returns:
        The folder the run's results are written to.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Returns the smoke folder offline and the results folder live")
    return settings.data_smoke if settings.llm_provider == FAKE else settings.data_results


# log.debug("Defines how one extraction is saved whole, for the case study")
def save_extraction(
    folder: Path | None = None, case: EvalCase | None = None, ex: Extraction | None = None
) -> Path:
    """Writes the case's record, raw answer and page texts as JSON.

    Args:
        folder: The run's folder of saved extractions. Required.
        case: The case that was extracted. Required.
        ex: The case's extraction. Required.

    Returns:
        The path of the JSON file written.
    """
    # log.debug("Takes the folder, which the caller must give")
    folder = required(folder=folder)
    # log.debug("Takes the case, which the caller must give")
    case = required(case=case)
    # log.debug("Takes the extraction, which the caller must give")
    ex = required(ex=ex)
    # log.debug("Makes the folder")
    folder.mkdir(parents=True, exist_ok=True)
    # log.debug("Names the file after the case")
    path = folder / f"{case.id}.json"
    # log.debug("Collects everything the demo page shows")
    payload = {
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
    }
    # log.debug("Writes it")
    path.write_text(json.dumps(payload, indent=1), encoding=ENCODING)
    # log.debug("Returns where it went")
    return path


# log.debug("Defines the system under test: extract, saving the first few")
class Extractor:
    """Extracts one case at a time, saving the first `dump` whole."""

    # log.debug("Defines the constructor")
    def __init__(
        self,
        settings: AppSettings | None = None,
        cases: list[EvalCase] | None = None,
        *,
        dump: int | None = None,
        name: str | None = None,
    ) -> None:
        """Builds the adapter and names the saved extractions' folder.

        Args:
            settings: The settings the adapter and folders come from.
                Required.
            cases: The cases, which the offline stand-in answers from.
                Required.
            dump: How many extractions to save whole. Required.
            name: The run's name, which names the saved folder.
                Required.
        """
        # log.debug("Takes the settings, which the caller must give")
        settings = required(settings=settings)
        # log.debug("Takes the cases, which the caller must give")
        cases = required(cases=cases)
        # log.debug("Takes how many to save whole, which the caller must give")
        dump = required(dump=dump)
        # log.debug("Takes the name, which the caller must give")
        name = required(name=name)
        # log.debug("Builds the adapter: the stand-in offline, the model live")
        self.adapter = adapter_for(settings, cases)
        # log.debug("Keeps how many extractions to save")
        self.dump = dump
        # log.debug("Names the folder the saved extractions go to")
        self.folder = settings.data_extractions / f"{name}-{datetime.now(UTC):{STAMP}}"
        # log.debug("Starts the count of saved extractions")
        self.saved = 0

    # log.debug("Defines one case's extraction")
    def __call__(self, case: EvalCase | None = None) -> Extraction:
        """Extracts the case, saving it whole while under the count.

        Args:
            case: The case to extract. Required.

        Returns:
            The extraction, for scoring.
        """
        # log.debug("Takes the case, which the caller must give")
        case = required(case=case)
        # log.debug("Extracts the case's two documents")
        ex = extract(self.adapter, case.input[CHARGE_PDF], case.input[NOTICE_PDF])
        # log.debug("Saves it whole while fewer than dump are saved")
        if self.saved < self.dump:
            # log.debug("Writes the extraction")
            save_extraction(self.folder, case, ex)
            # log.debug("Counts it")
            self.saved += 1
        # log.debug("Returns the extraction for scoring")
        return ex


# log.debug("Defines a whole evaluation run")
def evaluate(
    settings: AppSettings | None = None,
    *,
    name: str | None = None,
    limit: int | None = None,
    dump: int = 0,
) -> RunResult:
    """Runs every generated case and writes the results.

    Args:
        settings: Where the cases are, which provider, where to write.
            Required.
        name: The results file's prefix. Required.
        limit: Run only the first `limit` cases.
        dump: How many extractions to save whole.

    Returns:
        The run, also written as JSON and Markdown to its folder.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Takes the name, which the caller must give")
    name = required(name=name)
    # log.debug("Loads the generated cases, as many as asked")
    cases = load_cases(settings.data_samples / CASES_FILE)[:limit]
    # log.debug("Builds the system under test")
    system = Extractor(settings, cases, dump=dump, name=name)
    # log.debug("Runs every case and writes the results")
    return run_eval(
        name=name,
        cases=cases,
        adapter=system.adapter,
        system_fn=system,
        scorer_fn=score,
        out_dir=results_folder(settings),
        keep_output=False,
    )


# log.debug("Defines the command line")
def main(argv: Sequence[str] | None = None) -> int:
    """Runs the evaluation and prints its table.

    Args:
        argv: The command's arguments; the process's own when None.

    Returns:
        1 when the offline stand-in fails a case, which means a bug;
        0 otherwise. A live run's failures are part of what it
        measures, so its results are still written and kept.
    """
    # log.debug("Describes the command")
    parser = argparse.ArgumentParser(description="Run the extraction evaluation.")
    # log.debug("Adds the run's name, which prefixes its files")
    parser.add_argument("--name", required=True, help="results prefix, such as offline")
    # log.debug("Adds a cap on the cases run")
    parser.add_argument("--limit", type=int, default=None, help="run only the first N cases")
    # log.debug("Adds how many extractions to save whole")
    parser.add_argument("--dump", type=int, default=None, help="default: [extract] dump, live")
    # log.debug("Parses the command line")
    args = parser.parse_args(argv)
    # log.debug("Reads the settings")
    settings = get_app_settings()
    # log.debug("Starts logging to the configured folder")
    setup_logging(settings)
    # log.debug("Saves the configured number whole on a live run, none offline")
    dump = args.dump if args.dump is not None else _default_dump(settings)
    # log.debug("Runs the evaluation")
    run = evaluate(settings, name=args.name, limit=args.limit, dump=dump)
    # log.debug("Prints the results table the runner wrote")
    print((results_folder(settings) / f"{args.name}-latest.md").read_text(encoding=ENCODING))
    # log.debug("Logs the run's end with its failures")
    log_event(log, "eval.done", name=args.name, failures=run.failures, cases=run.cases)
    # log.debug("Fails the command only when the offline stand-in failed a case")
    return 1 if run.failures and settings.llm_provider == FAKE else 0


# log.debug("Defines how many extractions a run saves whole by default")
def _default_dump(settings: AppSettings | None = None) -> int:
    """Returns `[extract] dump` for a live run and 0 offline.

    Args:
        settings: The settings, whose provider and dump decide.
            Required.

    Returns:
        How many extractions to save whole.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Returns none for the stand-in, whose output says nothing new")
    return 0 if settings.llm_provider == FAKE else settings.extract_dump


# log.debug("Runs the command when the module is run as a script")
if __name__ == "__main__":
    # log.debug("Exits with main's status")
    raise SystemExit(main())
