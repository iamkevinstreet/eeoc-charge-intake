########################################################################
#                                                                      #
#               backend/src/eeoc_intake/evals/replay.py                #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

Replays every document of each live run as a reviewed export, in the
shape the review service exports under contract v1, so the warehouse
has reviewed charges to load: one JSON Lines file per run, one export
per line, in `[data] reviews`.

    python -m eeoc_intake.evals.replay

No person made these reviews. The reviewer here knows each document's
true values: a field the model read right is accepted, a field it
filled where the document holds nothing is rejected, and any other it
read wrong is edited to the true value. The summary is accepted, since
no answer key holds a paraphrase. A review carries its run's start and
finish as its times, so no review time is measured.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Final

# Third-party
from kds.args import required
from kds.logs import get_logger, log_event, setup_logging

# Local
from eeoc_intake.api.review import stamp
from eeoc_intake.config import REMOVED, SCORES, SETTINGS, get_app_settings
from eeoc_intake.core.extract import response_due
from eeoc_intake.core.schema import FIELDS, SUMMARY_FIELD
from eeoc_intake.evals.score import same

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the encoding every file is read and written in, from the config")
ENCODING: Final = SETTINGS.files_encoding
# log.debug("Takes the key only a run's results file has, from the config")
RESULTS_KEY: Final = SETTINGS.eval_results_key
# log.debug("Takes the name and version of the export contract, from the config")
CONTRACT: Final = SETTINGS.exports_contract
# log.debug("Takes the days a respondent has to answer, from the config")
RESPONSE_DAYS: Final = SETTINGS.extract_response_days
# log.debug("Takes the hex digits of a review's id, from the config")
ID_DIGITS: Final = SETTINGS.exports_id_digits

########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Sets the pattern of a live run's results file")
LIVE_RUNS: Final = "live-*.json"
# log.debug("Names the decision that keeps what the model read")
KEEP: Final = "accept"
# log.debug("Names the decision that puts the true value in")
CORRECT: Final = "edit"
# log.debug("Names the decision that empties the field")
CLEAR: Final = "reject"
# log.debug("Names a document's id in its result")
CASE_ID: Final = "case_id"
# log.debug("Names when a run started, and when a review began")
STARTED_AT: Final = "started_at"
# log.debug("Sets the field holding the notice date, which sets the response deadline")
NOTICE_FIELD: Final = "notice_date"


########################################################################
#                                                                      #
#                                Replay                                #
#                                                                      #
########################################################################
# log.debug("Defines one field's decision by a reviewer who knows the answer")
def decide(field: str | None = None, extracted: Any = None, known: Any = None) -> str:
    """Returns accept, reject or edit for one field.

    Args:
        field: The field's name. Required.
        extracted: The value the model read; None for an empty field.
        known: The document's true value; None when it has none.

    Returns:
        accept for the summary or a value read right, reject for a
        value where the document has none, edit for any other.
    """
    # log.debug("Takes the field, which the caller must give")
    field = required(field=field)
    # log.debug("Accepts the summary, and any value the model read right")
    if field == SUMMARY_FIELD or same(extracted, known):
        # log.debug("Returns accept")
        return KEEP
    # log.debug("Rejects a value where the document holds none, edits any other")
    return CLEAR if known in (None, []) else CORRECT


# log.debug("Defines the export of one replayed review")
def replay_case(
    run: dict[str, Any] | None = None, case: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Returns one document's review as the service would export it.

    Args:
        run: The run's file, for its name and times. Required.
        case: The document's result, with its values and the known
            ones. Required.

    Returns:
        The export, shaped by contract v1.
    """
    # log.debug("Takes the run, which the caller must give")
    run = required(run=run)
    # log.debug("Takes the document, which the caller must give")
    case = required(case=case)
    # log.debug("Reads the values the model read and the true ones")
    extracted, known = case[SCORES]["values"], case[SCORES]["gold"]
    # log.debug("Decides each field")
    decisions = {f: decide(f, extracted.get(f), known.get(f)) for f in FIELDS}
    # log.debug("Applies each decision: accepted keeps, edited takes the truth, rejected empties")
    record = {
        f: {KEEP: extracted.get(f), CORRECT: known.get(f), CLEAR: None}[decisions[f]]
        for f in FIELDS
    }
    # log.debug("Reads the notice date the record ends with")
    notice = record[NOTICE_FIELD]
    # log.debug("Returns the export")
    return {
        "contract": CONTRACT,
        "review_id": review_id(run["name"], run[STARTED_AT], case[CASE_ID]),
        "source": f"sample:{case[CASE_ID]}",
        "demo": False,
        STARTED_AT: stamp(datetime.fromisoformat(run[STARTED_AT])),
        "exported_at": stamp(datetime.fromisoformat(run["finished_at"])),
        "record": record,
        "extracted": {f: extracted.get(f) for f in FIELDS},
        "decisions": decisions,
        REMOVED: list(case[SCORES].get(REMOVED, [])),
        "response_due": response_due(date.fromisoformat(notice), RESPONSE_DAYS).isoformat()
        if isinstance(notice, str)
        else None,
    }


# log.debug("Defines a replayed review's id")
def review_id(
    name: str | None = None, started_at: str | None = None, case_id: str | None = None
) -> str:
    """Returns ten hex digits that name one document in one run.

    Args:
        name: The run's name. Required.
        started_at: When the run started. Required.
        case_id: The document. Required.

    Returns:
        The id, the same on every replay.
    """
    # log.debug("Takes the run's name, which the caller must give")
    name = required(name=name)
    # log.debug("Takes the run's start, which the caller must give")
    started_at = required(started_at=started_at)
    # log.debug("Takes the document, which the caller must give")
    case_id = required(case_id=case_id)
    # log.debug("Returns the start of the hash of all three")
    return hashlib.sha256(f"{name}/{started_at}/{case_id}".encode()).hexdigest()[:ID_DIGITS]


# log.debug("Defines the replay of every live run")
def replay(results: Path | None = None, out: Path | None = None) -> list[Path]:
    """Writes each live run's reviews to <run>.jsonl in out.

    A document that failed has no extraction to review and is left out.

    Args:
        results: The folder of live runs' files. Required.
        out: Where the reviews go. Required.

    Returns:
        Each file written, in the runs' order.
    """
    # log.debug("Takes the results folder, which the caller must give")
    results = required(results=results)
    # log.debug("Takes the output folder, which the caller must give")
    out = required(out=out)
    # log.debug("Makes the output folder")
    out.mkdir(parents=True, exist_ok=True)
    # log.debug("Starts with no files written")
    written: list[Path] = []
    # log.debug("Walks the live runs' files")
    for path in sorted(results.glob(LIVE_RUNS)):
        # log.debug("Reads the file")
        run = json.loads(path.read_text(encoding=ENCODING))
        # log.debug("Passes over a file that is not a run's results")
        if not isinstance(run, dict) or RESULTS_KEY not in run:
            # log.debug("Moves to the next file")
            continue
        # log.debug("Replays each document that has an extraction")
        lines = [
            json.dumps(replay_case(run, c), sort_keys=True) for c in run[RESULTS_KEY] if c["ok"]
        ]
        # log.debug("Names the run's file after the run's")
        target = out / f"{path.stem}.jsonl"
        # log.debug("Writes one export per line")
        target.write_text("\n".join(lines) + "\n", encoding=ENCODING)
        # log.debug("Logs the run replayed")
        log_event(log, "replay.run", run=path.stem, reviews=len(lines))
        # log.debug("Keeps the file")
        written.append(target)
    # log.debug("Returns the files")
    return written


# log.debug("Defines the command")
def main() -> None:
    """Replays every live run into `[data] reviews`."""
    # log.debug("Reads the settings")
    settings = get_app_settings()
    # log.debug("Starts logging")
    setup_logging(settings)
    # log.debug("Replays the runs")
    replay(settings.data_results, settings.data_reviews)


# log.debug("Runs the command when the module is run as a script")
if __name__ == "__main__":
    # log.debug("Runs it")
    main()
