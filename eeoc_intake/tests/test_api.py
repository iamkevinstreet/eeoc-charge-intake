"""The review service: extraction with evidence, one decision per field, export only when every field is decided."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(samples_dir):
    from eeoc_intake import api

    api.sample_cases.cache_clear()
    with TestClient(api.app) as c:
        yield c


def test_health_reports_demo_mode(client):
    body = client.get("/api/health").json()
    assert body["ok"] is True
    assert body["demo"] is True


def test_samples_are_listed_with_tags(client):
    samples = client.get("/api/samples").json()
    assert len(samples) == 10
    assert samples[0]["id"] == "charge-000"
    assert "clean" in samples[0]["tags"]
    assert samples[4]["tags"] == ["missing_number"]


def test_upload_is_refused_in_demo_mode(client):
    r = client.post(
        "/api/extract",
        files={
            "charge": ("c.pdf", b"%PDF-1.4", "application/pdf"),
            "notice": ("n.pdf", b"%PDF-1.4", "application/pdf"),
        },
    )
    assert r.status_code == 409


def test_extract_sample_returns_evidence_and_page_text(client):
    body = client.post("/api/extract/sample/charge-000").json()
    rec = body["record"]
    assert body["demo"] is True
    assert body["total"] == 11 and body["decided"] == 0
    assert rec["charging_party"]["value"]
    assert rec["charging_party"]["page"] == 1
    assert rec["charging_party"]["span"] in body["pages"]["charge"][0]
    assert body["pages"]["notice"][0].startswith("U.S. EQUAL EMPLOYMENT")
    assert body["removed"] == []


def test_missing_charge_number_comes_back_empty_with_reason(client):
    body = client.post("/api/extract/sample/charge-004").json()  # hard case: missing_number
    cn = body["record"]["charge_number"]
    assert cn["value"] is None
    assert cn["reason"]
    assert cn["confidence"] == 0.0


def test_export_is_gated_until_every_field_is_decided(client):
    body = client.post("/api/extract/sample/charge-001").json()
    rid = body["review_id"]
    fields = body["fields"]
    for f in fields[:-1]:
        r = client.post(f"/api/reviews/{rid}/decisions", json={"field": f, "action": "accept"})
        assert r.status_code == 200
    assert client.get(f"/api/reviews/{rid}/export").status_code == 409
    client.post(f"/api/reviews/{rid}/decisions", json={"field": fields[-1], "action": "accept"})
    out = client.get(f"/api/reviews/{rid}/export")
    assert out.status_code == 200
    assert out.json()["response_due"] is not None


def test_edits_and_rejections_shape_the_export(client):
    body = client.post("/api/extract/sample/charge-002").json()
    rid = body["review_id"]
    for f in body["fields"]:
        client.post(f"/api/reviews/{rid}/decisions", json={"field": f, "action": "accept"})
    client.post(f"/api/reviews/{rid}/decisions", json={"field": "summary", "action": "reject"})
    client.post(
        f"/api/reviews/{rid}/decisions",
        json={"field": "eeoc_office", "action": "edit", "value": "Atlanta District Office"},
    )
    out = client.get(f"/api/reviews/{rid}/export").json()
    assert out["record"]["summary"] is None
    assert out["record"]["eeoc_office"] == "Atlanta District Office"
    assert out["decisions"]["summary"] == "reject"
    assert client.get(f"/api/reviews/{rid}").json()["decided"] == 11


def test_unknown_review_and_field(client):
    assert client.get("/api/reviews/nope").status_code == 404
    body = client.post("/api/extract/sample/charge-003").json()
    r = client.post(
        f"/api/reviews/{body['review_id']}/decisions", json={"field": "salary", "action": "accept"}
    )
    assert r.status_code == 400
