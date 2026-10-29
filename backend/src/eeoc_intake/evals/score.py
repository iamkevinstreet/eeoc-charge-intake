########################################################################
#                backend/src/eeoc_intake/evals/score.py                #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Scores one extraction against the document's known values: fields right,
guesses, abstentions.

- field_accuracy: the share of the ten scored fields whose final value
  equals the known one
- f_<field>: 1 or 0 for each scored field, so the by-kind table shows
  which fields fail on which documents
- unsupported_removed: fields the model filled whose quote was not on
  the cited page; verification emptied them before anyone saw them.
  Their share of the raw filled fields is unsupported_rate.
- false_abstentions: fields left empty that the document did support
- guesses: fields filled when the document had no value
- empty_precision and empty_recall: how well "I could not find it"
  matches the documents that lacked a value
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

from typing import Any, Final

# Third-party
from kds.args import required
from kds.evals.case import EvalCase
from kds.evals.metrics import exact_match, null_metrics
from kds.logs import get_logger

# Local
from eeoc_intake.config import SETTINGS
from eeoc_intake.core.extract import Extraction
from eeoc_intake.core.schema import SCORED_FIELDS, is_empty

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the name of the count of fields wrongly left empty, from the config")
FALSE_ABSTENTIONS: Final = SETTINGS.scores_false_abstentions
# log.debug("Takes the name of the count of fields filled with nothing to find, from the config")
GUESSES: Final = SETTINGS.scores_guesses
# log.debug("Takes what comes before a field's name in its own score, from the config")
FIELD_SCORE: Final = SETTINGS.scores_field_prefix

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the decimals a share is rounded to in the results file")
PLACES: Final = 4


########################################################################
#                               Scoring                                #
########################################################################
# log.debug("Defines the scores of one extraction")
def score(case: EvalCase | None = None, ex: Extraction | None = None) -> dict[str, Any]:
    """Returns the case's scores, then its values for inspection.

    The summary averages the numeric scores only; the values, the known
    answers and the emptied fields are kept for the results file.

    Args:
        case: The generated case, with its known answers. Required.
        ex: The extraction to score. Required.

    Returns:
        The headline scores, a 1 or 0 for each scored field, then the
        values, the known answers and the emptied fields.
    """
    # log.debug("Takes the case, which the caller must give")
    case = required(case=case)
    # log.debug("Takes the extraction, which the caller must give")
    ex = required(ex=ex)
    # log.debug("Reads the final values, after verification")
    values = ex.record.values()
    # log.debug("Reads the known values of the scored fields")
    gold = {f: case.expected.get(f) for f in SCORED_FIELDS}
    # log.debug("Marks each scored field right or wrong")
    per_field = {f: same(values.get(f), gold.get(f)) for f in SCORED_FIELDS}
    # log.debug("Counts guesses and wrong abstentions")
    nulls = null_metrics(values, gold, SCORED_FIELDS)
    # log.debug("Counts the fields the model filled before verification")
    raw_filled = sum(1 for f in SCORED_FIELDS if not is_empty(ex.raw.sourced(f).value))
    # log.debug("Keeps the scored fields verification emptied")
    removed = [f for f in ex.removed if f in SCORED_FIELDS]
    # log.debug("Builds the headline scores")
    scores: dict[str, Any] = {
        "field_accuracy": round(sum(per_field.values()) / len(per_field), PLACES),
        "raw_filled_fields": raw_filled,
        "unsupported_removed": len(removed),
        "unsupported_rate": round(len(removed) / raw_filled, PLACES) if raw_filled else 0.0,
        FALSE_ABSTENTIONS: nulls[FALSE_ABSTENTIONS],
        GUESSES: nulls[GUESSES],
        "empty_precision": nulls["precision"],
        "empty_recall": nulls["recall"],
        "model_latency_ms": ex.latency_ms,
    }
    # log.debug("Adds a right-or-wrong score for each field")
    scores.update({f"{FIELD_SCORE}{f}": int(per_field[f]) for f in SCORED_FIELDS})
    # log.debug("Keeps the values, answers and emptied fields for inspection")
    scores.update({"values": values, "gold": gold, "removed": removed})
    # log.debug("Returns the scores")
    return scores


# log.debug("Defines when an extracted value equals the known one")
def same(a: object = None, b: object = None) -> bool:
    """Returns exact equality after normalising case and spacing.

    A one-item list and its item count as the same value.

    Args:
        a: The extracted value; None for an empty field.
        b: The known value; None when the document has none.

    Returns:
        True when the two match, case and spacing aside.
    """
    # log.debug("Unwraps a one-item list compared with a single value")
    if isinstance(a, list) and len(a) == 1 and not isinstance(b, list):
        # log.debug("Takes the item")
        a = a[0]
    # log.debug("Unwraps the known value the same way")
    if isinstance(b, list) and len(b) == 1 and not isinstance(a, list):
        # log.debug("Takes the item")
        b = b[0]
    # log.debug("Returns whether the two match exactly")
    return exact_match(a, b)
