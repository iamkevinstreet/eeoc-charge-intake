########################################################################
#                                                                      #
#                    backend/tests/test_tracing.py                     #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-07
Last modified on:  2026-11-07

Tests the spans of an extraction and of an evaluation run: one extract
span holding the model call and the quote check, the fields the check
emptied named on it, each document one eval span with its scores but
not its values, and a kept run's spans written beside its results.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import json
from pathlib import Path

# Third-party
from kds.args import required
from kds.evals.case import EvalCase, load_cases
from kds.llm import ModelAdapter
from kds.logs import get_logger
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# Local
from eeoc_intake.config import SETTINGS, AppSettings
from eeoc_intake.core.extract import EXTRACT, VERIFY, Extraction, extract
from eeoc_intake.core.offline import PLANTED_FIELD, PLANTED_SPAN, adapter_for, gold_record
from eeoc_intake.core.schema import FIELDS, is_empty
from eeoc_intake.evals.index import build_index
from eeoc_intake.evals.run import evaluate
from support import make_settings, scripted

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
# log.debug("Names the run every evaluation test makes")
RUN = "offline"
# log.debug("Starts the name of every score an eval span records")
SCORE = "kds.eval.score."


########################################################################
#                                                                      #
#                            Tracing tests                             #
#                                                                      #
########################################################################
# log.debug("Defines a span's parent's id")
def _parent(span: ReadableSpan | None = None) -> int | None:
    """Returns the id of the span's parent.

    Args:
        span: The span.

    Returns:
        The parent's id, or None for a span that starts its trace.
    """
    # log.debug("Returns the parent's id")
    return span.parent.span_id if span and span.parent else None


# log.debug("Defines a span's own id")
def _own(span: ReadableSpan | None = None) -> int | None:
    """Returns the span's id.

    Args:
        span: The span.

    Returns:
        Its id, or None without a context.
    """
    # log.debug("Returns the id from the span's context")
    return span.context.span_id if span and span.context else None


# log.debug("Defines a span's attributes")
def _attrs(span: ReadableSpan | None = None) -> dict[str, object]:
    """Returns the span's attributes.

    Args:
        span: The span.

    Returns:
        Its attributes by name; empty without any.
    """
    # log.debug("Returns them as a plain table")
    return dict(span.attributes or {}) if span else {}


# log.debug("Defines the first generated sample")
def _first(settings: AppSettings | None = None) -> EvalCase:
    """Returns the first of the session's generated samples.

    Args:
        settings: The test's settings, which name the samples.
            Required.

    Returns:
        The first case, a clean document.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Returns the first case")
    return load_cases(settings.data_samples / SETTINGS.samples_cases)[0]


# log.debug("Defines one extraction of a case")
def _extract(adapter: ModelAdapter | None = None, case: EvalCase | None = None) -> Extraction:
    """Extracts the case's charge and notice with `adapter`.

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
    # log.debug("Extracts the case's two documents")
    return extract(
        adapter,
        case.input[SETTINGS.samples_charge_input],
        case.input[SETTINGS.samples_notice_input],
    )


# log.debug("Defines the test of an extraction's spans")
def test_an_extraction_is_one_span_holding_its_call_and_check(
    settings: AppSettings, spans: InMemorySpanExporter
) -> None:
    """The model call and the quote check sit inside the extract span.

    Args:
        settings: Offline settings over the ten samples.
        spans: The spans this test records.
    """
    # log.debug("Takes the first sample")
    case = _first(settings)
    # log.debug("Extracts it through the stand-in")
    ex = _extract(adapter_for(settings, [case]), case)
    # log.debug("Takes the spans")
    finished = spans.get_finished_spans()
    # log.debug("Takes the extraction's span")
    (whole,) = [s for s in finished if s.name == EXTRACT]
    # log.debug("Takes the check's span")
    (check,) = [s for s in finished if s.name == VERIFY]
    # log.debug("Checks the other spans are the model call and the check")
    assert sorted(s.name for s in finished if s is not whole) == ["chat fake-model", VERIFY]
    # log.debug("Checks both sit inside the extraction's span")
    assert {_parent(s) for s in finished if s is not whole} == {_own(whole)}
    # log.debug("Checks the check is shown as a guardrail, and emptied nothing")
    assert (_attrs(check)["langfuse.observation.type"], _attrs(check)["verify.removed"]) == (
        "guardrail",
        (),
    )
    # log.debug("Counts the fields the record fills")
    filled = sum(1 for f in FIELDS if not is_empty(ex.record.sourced(f).value))
    # log.debug("Checks the extraction's span says so, and that none was lost")
    assert filled and (_attrs(whole)["extract.filled"], _attrs(whole)["extract.removed"]) == (
        filled,
        0,
    )


# log.debug("Defines the test that the check names the fields it emptied")
def test_the_check_names_the_fields_it_emptied(
    settings: AppSettings, spans: InMemorySpanExporter
) -> None:
    """A quote on no page: the check's span names its field.

    Args:
        settings: Offline settings over the ten samples.
        spans: The spans this test records.
    """
    # log.debug("Takes the first sample")
    case = _first(settings)
    # log.debug("Builds its record with one quote that is on no page")
    record = gold_record(case)
    # log.debug("Puts the quote that is on no page in the planted field")
    record[PLANTED_FIELD]["span"] = PLANTED_SPAN
    # log.debug("Extracts it through a model that gives that record")
    ex = _extract(scripted(settings, json.dumps(record)), case)
    # log.debug("Takes the check's span")
    (check,) = [s for s in spans.get_finished_spans() if s.name == VERIFY]
    # log.debug("Checks the field was emptied")
    assert ex.removed == [PLANTED_FIELD]
    # log.debug("Checks the check's span names it")
    assert _attrs(check)["verify.removed"] == (PLANTED_FIELD,)


# log.debug("Defines the test that each document is an eval span")
def test_each_document_is_an_eval_span_holding_its_extraction(
    settings: AppSettings, spans: InMemorySpanExporter
) -> None:
    """Two documents: two eval spans in one session, each scored.

    The scores are on each span; the values read and expected, which
    the results file keeps, are not.

    Args:
        settings: Offline settings over the ten samples.
        spans: The spans this test records.
    """
    # log.debug("Runs two documents offline")
    evaluate(settings, name=RUN, limit=2)
    # log.debug("Takes the spans")
    finished = spans.get_finished_spans()
    # log.debug("Takes the documents' spans")
    cases = [s for s in finished if s.name.startswith("eval ")]
    # log.debug("Checks each extraction sits inside its document's span")
    assert {_parent(s) for s in finished if s.name == EXTRACT} == {_own(s) for s in cases}
    # log.debug("Reads the one session both documents' spans are in")
    (session,) = {str(_attrs(s)["session.id"]) for s in cases}
    # log.debug("Checks there are two, and the session is named for the run")
    assert len(cases) == 2 and session.startswith(f"{RUN}-")
    # log.debug("Lists the scores the first document's span records")
    shown = {k.removeprefix(SCORE) for k in _attrs(cases[0]) if k.startswith(SCORE)}
    # log.debug("Checks the headline score is there and the values are not")
    assert "field_accuracy" in shown and not shown & {"values", "gold", "removed"}


# log.debug("Defines the test that a kept run writes its spans")
def test_a_kept_run_writes_its_spans_beside_its_results(tmp_path: Path, samples: Path) -> None:
    """With spans kept, one file of spans, which the index leaves out.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
        samples: The folder of the session's generated samples.
    """
    # log.debug("Keeps the spans of an offline run of one document")
    settings = make_settings(tmp_path, samples, spans_keep=True)
    # log.debug("Runs it")
    evaluate(settings, name=RUN, limit=1)
    # log.debug("Finds the run's spans file")
    (path,) = settings.data_smoke.glob(f"{RUN}-*.spans.jsonl")
    # log.debug("Reads the names of the spans it holds")
    names = {json.loads(line)["name"] for line in path.read_text().splitlines()}
    # log.debug("Checks it holds the document, its extraction, call and check")
    assert names == {f"eval {_first(settings).id}", EXTRACT, "chat fake-model", VERIFY}
    # log.debug("Checks the index the case study reads lists only the run")
    assert len(build_index(settings.data_smoke, settings.data_extractions)["runs"]) == 1
