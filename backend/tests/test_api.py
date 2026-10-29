########################################################################
#                      backend/tests/test_api.py                       #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests the review service: evidence, one decision per field, the export
gate, and the edge checks.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

# Third-party
import pytest
from fastapi.testclient import TestClient
from kds.args import required
from kds.logs import get_logger

# Local
from eeoc_intake.config import AppSettings
from eeoc_intake.core.generate import generate
from support import make_settings, scripted, started

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the prefix every route is under")
API = "/api/v1"
# log.debug("Sets a file that starts like a PDF but is not one")
PDF = b"%PDF-1.4\n%made up\n"


########################################################################
#                         Review service tests                         #
########################################################################
# log.debug("Defines a started client in demo mode, over the ten samples")
@pytest.fixture
def client(settings: AppSettings) -> Iterator[TestClient]:
    """Yields a started client in demo mode, over the ten samples.

    Args:
        settings: Offline settings over the ten samples.

    Yields:
        The client.
    """
    # log.debug("Starts the app and yields its client")
    with started(settings) as c:
        # log.debug("Yields it")
        yield c


# log.debug("Defines how a test extracts one sample")
def _sample(client: TestClient | None = None, sample_id: str | None = None) -> dict[str, Any]:
    """Extracts one sample and returns the review.

    Args:
        client: The started client. Required.
        sample_id: The sample's id, such as charge-000. Required.

    Returns:
        The review, as the service returned it.
    """
    # log.debug("Takes the client, which the caller must give")
    client = required(client=client)
    # log.debug("Takes the sample id, which the caller must give")
    sample_id = required(sample_id=sample_id)
    # log.debug("Posts the extraction")
    response = client.post(f"{API}/extract/sample/{sample_id}")
    # log.debug("Checks it worked")
    assert response.status_code == 200, response.text
    # log.debug("Returns the review")
    return dict(response.json())


# log.debug("Defines how a test records one decision on every field")
def _decide_all(
    client: TestClient | None = None, review: dict[str, Any] | None = None, action: str = "accept"
) -> None:
    """Records the same decision on every field of the review.

    Args:
        client: The started client. Required.
        review: The review, as the service returned it. Required.
        action: The decision to record on every field.
    """
    # log.debug("Takes the client, which the caller must give")
    client = required(client=client)
    # log.debug("Takes the review, which the caller must give")
    review = required(review=review)
    # log.debug("Decides each field")
    for name in review["fields"]:
        # log.debug("Posts the decision")
        client.post(
            f"{API}/reviews/{review['review_id']}/decisions",
            json={"field": name, "action": action},
        )


# log.debug("Defines how a test posts two files as the charge and the notice")
def _upload(client: TestClient | None = None, data: bytes = PDF) -> Any:
    """Posts two files as the charge and the notice.

    Args:
        client: The started client. Required.
        data: The bytes of both files.

    Returns:
        The service's response.
    """
    # log.debug("Takes the client, which the caller must give")
    client = required(client=client)
    # log.debug("Posts both files")
    return client.post(
        f"{API}/extract",
        files={
            "charge": ("c.pdf", data, "application/pdf"),
            "notice": ("n.pdf", data, "application/pdf"),
        },
    )


# log.debug("Defines the test: health reports demo mode and version")
def test_health_reports_demo_mode_and_version(client: TestClient) -> None:
    """Checks the health check says the stand-in is answering.

    Args:
        client: A started client in demo mode, over the ten samples.
    """
    # log.debug("Reads the health report")
    body = client.get(f"{API}/health").json()
    # log.debug("Checks it is up, in demo mode, with a version")
    assert body["ok"] is True and body["demo"] is True and body["version"]


# log.debug("Defines the test: samples are listed with their kind")
def test_samples_are_listed_with_their_kind(client: TestClient) -> None:
    """Checks the ten samples are listed; the fifth has no number.

    Args:
        client: A started client in demo mode, over the ten samples.
    """
    # log.debug("Reads the samples")
    listed = client.get(f"{API}/samples").json()
    # log.debug("Checks the count, the first id and the hard case's tag")
    assert len(listed) == 10 and listed[0]["id"] == "charge-000"
    # log.debug("Checks the kinds")
    assert listed[0]["tags"] == ["clean"] and listed[4]["tags"] == ["missing_number"]
    # log.debug("Checks no folder is shown, only file names")
    assert listed[0]["charge_pdf"] == "charge-000.pdf"


# log.debug("Defines the test: upload is refused in demo mode")
def test_upload_is_refused_in_demo_mode(client: TestClient) -> None:
    """Checks the stand-in answers only for the samples.

    Args:
        client: A started client in demo mode, over the ten samples.
    """
    # log.debug("Checks the upload is refused with 409")
    assert _upload(client).status_code == 409


# log.debug("Defines the test: extraction returns evidence and page text")
def test_extraction_returns_evidence_and_page_text(client: TestClient) -> None:
    """Checks each value comes with its page and the quoted text.

    Args:
        client: A started client in demo mode, over the ten samples.
    """
    # log.debug("Extracts the first sample")
    body = _sample(client, "charge-000")
    # log.debug("Reads the charging party")
    party = body["record"]["charging_party"]
    # log.debug("Checks the review starts undecided over eleven fields")
    assert body["demo"] is True and body["total"] == 11 and body["decided"] == 0
    # log.debug("Checks the quote is on the page it cites")
    assert party["page"] == 1 and party["span"] in body["pages"]["charge"][0]
    # log.debug("Checks the notice's text came back too")
    assert body["pages"]["notice"][0].startswith("U.S. EQUAL EMPLOYMENT")
    # log.debug("Checks nothing was emptied")
    assert body["removed"] == []


# log.debug("Defines the test: missing charge number is empty with a reason")
def test_missing_charge_number_is_empty_with_a_reason(client: TestClient) -> None:
    """Checks the hard case with a blank number says why it is empty.

    Args:
        client: A started client in demo mode, over the ten samples.
    """
    # log.debug("Extracts the sample with no number")
    number = _sample(client, "charge-004")["record"]["charge_number"]
    # log.debug("Checks it is empty, with a reason and no confidence")
    assert number["value"] is None and number["reason"] and number["confidence"] == 0.0


# log.debug("Defines the test: export waits for every field")
def test_export_waits_for_every_field(client: TestClient) -> None:
    """Checks for 409 until the last field is decided, then the record.

    Args:
        client: A started client in demo mode, over the ten samples.
    """
    # log.debug("Starts a review")
    review = _sample(client, "charge-001")
    # log.debug("Names its export route")
    export = f"{API}/reviews/{review['review_id']}/export"
    # log.debug("Decides every field but the last")
    for name in review["fields"][:-1]:
        # log.debug("Accepts it")
        client.post(
            f"{API}/reviews/{review['review_id']}/decisions",
            json={"field": name, "action": "accept"},
        )
    # log.debug("Checks the export is refused")
    assert client.get(export).status_code == 409
    # log.debug("Decides the last field")
    _decide_all(client, review)
    # log.debug("Exports the record")
    out = client.get(export)
    # log.debug("Checks it worked and carries the deadline")
    assert out.status_code == 200 and out.json()["response_due"] is not None


# log.debug("Defines the test: edits and rejections shape the export")
def test_edits_and_rejections_shape_the_export(client: TestClient) -> None:
    """Checks a rejected field exports empty and an edited one the edit.

    Args:
        client: A started client in demo mode, over the ten samples.
    """
    # log.debug("Starts a review and accepts every field")
    review = _sample(client, "charge-002")
    # log.debug("Accepts everything")
    _decide_all(client, review)
    # log.debug("Names the decisions route")
    decisions = f"{API}/reviews/{review['review_id']}/decisions"
    # log.debug("Rejects the summary")
    client.post(decisions, json={"field": "summary", "action": "reject"})
    # log.debug("Edits the office")
    client.post(decisions, json={"field": "eeoc_office", "action": "edit", "value": "Elsewhere"})
    # log.debug("Exports the record")
    out = client.get(f"{API}/reviews/{review['review_id']}/export").json()
    # log.debug("Checks the rejection and the edit")
    assert out["record"]["summary"] is None and out["record"]["eeoc_office"] == "Elsewhere"
    # log.debug("Checks the decisions are listed")
    assert out["decisions"]["summary"] == "reject"


# log.debug("Defines the test: unknown review field and sample")
def test_unknown_review_field_and_sample(client: TestClient) -> None:
    """Checks 404 for an unknown review or sample, 400 for a bad field.

    Args:
        client: A started client in demo mode, over the ten samples.
    """
    # log.debug("Checks an unknown review")
    assert client.get(f"{API}/reviews/0123456789").status_code == 404
    # log.debug("Checks a malformed review id is refused before any lookup")
    assert client.get(f"{API}/reviews/nope").status_code == 422
    # log.debug("Checks an unknown sample")
    assert client.post(f"{API}/extract/sample/charge-999").status_code == 404
    # log.debug("Starts a review")
    review = _sample(client, "charge-003")
    # log.debug("Decides a field the record does not have")
    response = client.post(
        f"{API}/reviews/{review['review_id']}/decisions",
        json={"field": "salary", "action": "accept"},
    )
    # log.debug("Checks it is refused")
    assert response.status_code == 400


# log.debug("Defines the test: latest results fall back to the smoke run")
def test_latest_results_fall_back_to_the_smoke_run(client: TestClient) -> None:
    """Checks for 404 before any run, then a live run over a smoke one.

    Args:
        client: A started client in demo mode, over the ten samples.
    """
    # log.debug("Checks there is nothing yet")
    assert client.get(f"{API}/evals/latest").status_code == 404


# log.debug("Defines the test: every reply carries the request id and headers")
def test_every_reply_carries_the_request_id_and_headers(client: TestClient) -> None:
    """Checks the request id is echoed and security headers are set.

    Args:
        client: A started client in demo mode, over the ten samples.
    """
    # log.debug("Sends a request with an id")
    response = client.get(f"{API}/health", headers={"X-Request-ID": "abc-123"})
    # log.debug("Checks the id is echoed")
    assert response.headers["X-Request-ID"] == "abc-123"
    # log.debug("Checks the API headers")
    assert response.headers["Cache-Control"] == "no-store"
    # log.debug("Checks framing is refused")
    assert response.headers["X-Frame-Options"] == "DENY"


# log.debug("Defines the test: other host names are refused")
def test_other_host_names_are_refused(client: TestClient) -> None:
    """Checks a page on another name cannot reach the service by DNS.

    Args:
        client: A started client in demo mode, over the ten samples.
    """
    # log.debug("Sends a request addressed to another host")
    response = client.get(f"{API}/health", headers={"Host": "attacker.example"})
    # log.debug("Checks it is refused, with the headers still set")
    assert response.status_code == 400 and response.headers["X-Content-Type-Options"]


# log.debug("Defines the test: bodies without or over a length are refused")
def test_bodies_without_or_over_a_length_are_refused(client: TestClient) -> None:
    """Checks for 411 without Content-Length and 413 over the limit.

    Args:
        client: A started client in demo mode, over the ten samples.
    """
    # log.debug("Names the decisions route of a made-up review")
    route = f"{API}/reviews/0123456789/decisions"
    # log.debug("Sends a chunked body, which declares no length")
    chunked = client.post(route, content=iter([b"{}"]))
    # log.debug("Checks 411")
    assert chunked.status_code == 411
    # log.debug("Sends a JSON body over the small limit")
    big = client.post(route, content=b"x" * 70_000, headers={"Content-Type": "application/json"})
    # log.debug("Checks 413")
    assert big.status_code == 413


# log.debug("Defines the test: root says how to build the screen")
def test_root_says_how_to_build_the_screen(client: TestClient) -> None:
    """Checks / says where the API is and how to build the screen.

    Args:
        client: A started client in demo mode, over the ten samples.
    """
    # log.debug("Reads the root")
    body = client.get("/").json()
    # log.debug("Checks it names the API")
    assert body["api"] == API


# log.debug("Defines the test: samples made after startup appear without a restart")
def test_samples_made_after_startup_appear(tmp_path: Path) -> None:
    """Checks samples made after startup appear when the screen reloads.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Builds demo settings over an empty samples folder")
    empty = make_settings(tmp_path, tmp_path / "later")
    # log.debug("Starts the app")
    with started(empty) as c:
        # log.debug("Checks there are no samples yet")
        assert c.get(f"{API}/samples").json() == []
        # log.debug("Generates two documents while the service runs")
        generate(AppSettings(samples_count=2, samples_seed=5, data_samples=tmp_path / "later"))
        # log.debug("Checks both are listed now")
        assert len(c.get(f"{API}/samples").json()) == 2
        # log.debug("Checks the stand-in can extract one of them")
        assert c.post(f"{API}/extract/sample/charge-001").status_code == 200


# log.debug("Defines the test: live uploads must be pdfs within the limit")
def test_live_uploads_must_be_pdfs_within_the_limit(tmp_path: Any, samples: Any) -> None:
    """Checks live uploads get 415 for a non-PDF and 413 over the limit.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
        samples: The folder of the session's ten generated samples.
    """
    # log.debug("Builds settings for a real provider with a small upload limit")
    live = _live(tmp_path, samples, api_max_upload_bytes=20_000)
    # log.debug("Starts the app with a scripted model")
    with started(live, scripted(live, "{}")) as c:
        # log.debug("Checks a file that is not a PDF")
        assert _upload(c, b"not a pdf").status_code == 415
        # log.debug("Checks a PDF over the limit")
        assert _upload(c, PDF + b"x" * 30_000).status_code == 413
        # log.debug("Checks a PDF the reader cannot parse")
        assert _upload(c).status_code == 422


# log.debug("Defines the test: live extractions are limited per minute")
def test_live_extractions_are_limited_per_minute(tmp_path: Any, samples: Any) -> None:
    """Checks the seventh extraction in a minute is refused with 429.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
        samples: The folder of the session's ten generated samples.
    """
    # log.debug("Builds settings for a real provider")
    live = _live(tmp_path, samples)
    # log.debug("Starts the app with a model that gives an empty record")
    with started(live, scripted(live, "{}")) as c:
        # log.debug("Makes six extractions")
        codes = [c.post(f"{API}/extract/sample/charge-000").status_code for _ in range(7)]
    # log.debug("Checks six worked and the seventh was refused")
    assert codes == [200] * 6 + [429]


# log.debug("Defines the test: a model answer that never fits is a 502")
def test_a_model_answer_that_never_fits_is_a_502(tmp_path: Any, samples: Any) -> None:
    """Checks an answer that never validates, even repaired, is a 502.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
        samples: The folder of the session's ten generated samples.
    """
    # log.debug("Builds settings for a real provider")
    live = _live(tmp_path, samples)
    # log.debug("Starts the app with a model that answers prose")
    with started(live, scripted(live, "not json")) as c:
        # log.debug("Checks the extraction fails cleanly")
        assert c.post(f"{API}/extract/sample/charge-000").status_code == 502


# log.debug("Defines the settings for a real provider; the tests pass the model")
def _live(tmp_path: Any = None, samples: Any = None, **overrides: Any) -> AppSettings:
    """Returns settings for a real provider; the tests pass the model.

    Args:
        tmp_path: The test's temporary folder. Required.
        samples: The folder of generated samples. Required.
        **overrides: Settings to change, by field name.

    Returns:
        The settings, with a real provider.
    """
    # log.debug("Takes the test's folder, which the caller must give")
    tmp_path = required(tmp_path=tmp_path)
    # log.debug("Takes the samples folder, which the caller must give")
    samples = required(samples=samples)
    # log.debug("Returns them")
    return AppSettings(
        llm_provider="anthropic",
        data_samples=samples,
        data_results=tmp_path / "results",
        data_smoke=tmp_path / "smoke",
        log_dir=tmp_path / "logs",
        ui_dist=tmp_path / "no-ui",
        **overrides,
    )


# log.debug("Defines the test: the API schema describes each route by its summary")
def test_the_api_schema_leaves_out_doc_block_sections(client: TestClient) -> None:
    """The schema keeps each route's summary, not its Args or Returns.

    Args:
        client: A client of the app with test settings.
    """
    # log.debug("Reads the schema the app publishes")
    paths = client.get(f"{API}/openapi.json").json()["paths"]
    # log.debug("Collects every route's description")
    described = [op.get("description", "") for ops in paths.values() for op in ops.values()]
    # log.debug("Checks there are routes to describe")
    assert described
    # log.debug("Checks each is described by its summary alone")
    assert all(d and "Args:" not in d and "Returns:" not in d for d in described)
