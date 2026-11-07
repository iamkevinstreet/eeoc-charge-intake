########################################################################
#                                                                      #
#                    backend/tests/test_planted.py                     #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-07
Last modified on:  2026-11-07

Tests the planted-orders case: where it falls, the note on its page and
its true values, the guard flagging the note, the offline stand-in
ignoring it, and a model that obeys it being caught by the score though
the quote check keeps its values, since the note itself is on the page.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import json

# Third-party
import pytest
from kds.args import required
from kds.evals.case import EvalCase, load_cases
from kds.llm import ModelAdapter
from kds.logs import get_logger
from kds.synthetic.pdftext import pages_text, span_in_page

# Local
from eeoc_intake.config import SETTINGS, AppSettings
from eeoc_intake.core.charges import HARD_KINDS, kind_of
from eeoc_intake.core.extract import Extraction, extract
from eeoc_intake.core.generate import generate
from eeoc_intake.core.offline import adapter_for, gold_record
from eeoc_intake.core.planted import (
    ORDERS,
    PLANTED_NUMBER,
    PLANTED_ORDERS,
    PLANTED_RESPONDENT,
)
from eeoc_intake.evals.score import score
from support import scripted

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = get_logger(__name__)

########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Sets the place of the first planted-orders charge, from 0")
FIRST = 12
# log.debug("Sets the place of the second, a round of 25 later")
SECOND = 37


########################################################################
#                                                                      #
#                         Planted-orders tests                         #
#                                                                      #
########################################################################
# log.debug("Defines the generated set that holds a planted-orders charge")
@pytest.fixture(scope="module")
def planted_case(tmp_path_factory: pytest.TempPathFactory) -> EvalCase:
    """Generates thirteen charges from seed 7 and returns the 13th.

    Args:
        tmp_path_factory: pytest's maker of temporary folders.

    Returns:
        The planted-orders case.
    """
    # log.debug("Generates the set into a folder of its own")
    cases = generate(
        AppSettings(samples_count=FIRST + 1, samples_seed=7),
        tmp_path_factory.mktemp("planted"),
    )
    # log.debug("Returns the last case, the planted one")
    return load_cases(cases)[FIRST]


# log.debug("Defines one extraction of the planted case")
def _extract(adapter: ModelAdapter | None = None, case: EvalCase | None = None) -> Extraction:
    """Extracts the case's two documents with the adapter given.

    Args:
        adapter: The model adapter to call. Required.
        case: The case whose documents are read. Required.

    Returns:
        The extraction.
    """
    # log.debug("Takes the adapter, which the caller must give")
    adapter = required(adapter=adapter)
    # log.debug("Takes the case, which the caller must give")
    case = required(case=case)
    # log.debug("Extracts the case's documents")
    return extract(
        adapter,
        case.input[SETTINGS.samples_charge_input],
        case.input[SETTINGS.samples_notice_input],
    )


# log.debug("Defines the page of the charge that carries the note")
def _note_page(case: EvalCase | None = None) -> int:
    """Returns the charge's page that holds the planted charge number.

    Args:
        case: The planted-orders case. Required.

    Returns:
        The page, from 1.
    """
    # log.debug("Takes the case, which the caller must give")
    case = required(case=case)
    # log.debug("Reads the charge's pages")
    pages = pages_text(case.input[SETTINGS.samples_charge_input])
    # log.debug("Returns the first page that holds the note's charge number")
    return next(i for i, page in enumerate(pages, start=1) if span_in_page(PLANTED_NUMBER, page))


# log.debug("Defines the test of where the planted case falls")
def test_planted_orders_fall_where_clean_charges_were() -> None:
    """The 13th and 38th charges; every hard case stays where it was."""
    # log.debug("Lists the planted places in the first fifty")
    planted = [i for i in range(50) if kind_of(i, 5) == PLANTED_ORDERS]
    # log.debug("Checks them, and that the hard cases still come round in turn")
    assert planted == [FIRST, SECOND] and [kind_of(i, 5) for i in range(4, 40, 5)] == [
        *HARD_KINDS,
        *HARD_KINDS,
    ]


# log.debug("Defines the test of the planted charge's documents and answers")
def test_the_note_is_printed_and_the_answers_stay_true(planted_case: EvalCase) -> None:
    """The guard finds the note on the page; the answers are not its.

    Args:
        planted_case: The planted-orders case, from the fixture.
    """
    # log.debug("Extracts it with the offline stand-in, which answers from the true values")
    ex = _extract(adapter_for(SETTINGS, [planted_case]), planted_case)
    # log.debug("Checks the guard flagged the note's three sentences on the charge")
    assert [w.document for w in ex.warnings] == ["charge"] * 3
    # log.debug("Checks the flagged text is the note's")
    assert all(w.text in " ".join(ORDERS.split()) for w in ex.warnings)
    # log.debug("Checks the true answers are not the planted ones")
    assert (planted_case.expected["charge_number"], planted_case.expected["respondent"]) != (
        PLANTED_NUMBER,
        PLANTED_RESPONDENT,
    )
    # log.debug("Checks the stand-in ignored the note, scoring nothing followed")
    assert score(planted_case, ex)["planted_followed"] == 0


# log.debug("Defines the test that a model obeying the note is caught")
def test_a_model_that_obeys_the_note_is_caught(planted_case: EvalCase) -> None:
    """Its planted values survive the quote check, but not the score.

    The note is on the page, so a quote of it is a real quote: the check
    keeps the values, and the score and the reviewer's warning are what
    catch them.

    Args:
        planted_case: The planted-orders case, from the fixture.
    """
    # log.debug("Builds the true record, then obeys the note")
    record = gold_record(planted_case)
    # log.debug("Finds the page the note is on, which the quotes cite")
    page = _note_page(planted_case)
    # log.debug("Records the planted charge number, quoting the note")
    record["charge_number"].update(value=PLANTED_NUMBER, span=PLANTED_NUMBER, page=page)
    # log.debug("Records the planted respondent, quoting the note")
    record["respondent"].update(value=PLANTED_RESPONDENT, span=PLANTED_RESPONDENT, page=page)
    # log.debug("Extracts with a model that gives that record")
    ex = _extract(scripted(SETTINGS, json.dumps(record)), planted_case)
    # log.debug("Scores it")
    scores = score(planted_case, ex)
    # log.debug("Checks the quote check kept both, since they are on the page")
    assert ex.removed == []
    # log.debug("Checks the score caught both, and the record is wrong")
    assert (scores["planted_followed"], scores["field_accuracy"] < 1) == (2, True)
    # log.debug("Checks the reviewer is warned")
    assert ex.warnings


# log.debug("Defines the test that the cases file carries what the note asks for")
def test_the_known_answers_keep_what_the_note_asked_for(planted_case: EvalCase) -> None:
    """The case's answers name the note's values, for the scorer.

    Args:
        planted_case: The planted-orders case, from the fixture.
    """
    # log.debug("Checks the values the note asked for, a blank for the bases")
    assert planted_case.expected[SETTINGS.samples_planted_key] == {
        "charge_number": PLANTED_NUMBER,
        "respondent": PLANTED_RESPONDENT,
        "bases": None,
    }
