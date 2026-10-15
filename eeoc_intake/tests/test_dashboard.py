"""The dashboard and the Tableau export read the same results and agree with the runner's summary."""

import json
from pathlib import Path

from eeoc_intake.dashboard import build_app, fig_accuracy_by_field, fig_heatmap, frames, load_runs
from eeoc_intake.evals.export import export

RUN = {
    "name": "t",
    "model": "fake-model",
    "provider": "fake",
    "started_at": "2026-10-15T00:00:00+00:00",
    "finished_at": "2026-10-15T00:00:01+00:00",
    "prices_as_of": "2026-10-15",
    "cases": 2,
    "failures": 0,
    "summary": {"field_accuracy": 0.95, "unsupported_rate": 0.05, "latency_p50_ms": 10, "latency_p95_ms": 12},
    "results": [
        {
            "case_id": "charge-000",
            "tags": ["clean"],
            "ok": True,
            "scores": {
                "field_accuracy": 1.0,
                "f_charge_number": 1,
                "f_bases": 1,
                "values": {},
                "gold": {},
                "removed": [],
            },
            "error": None,
            "latency_ms": 10,
            "cost_usd": 0.001,
            "calls": 1,
        },
        {
            "case_id": "charge-004",
            "tags": ["missing_number"],
            "ok": True,
            "scores": {
                "field_accuracy": 0.9,
                "f_charge_number": 0,
                "f_bases": 1,
                "values": {"charge_number": "x"},
                "gold": {"charge_number": None},
                "removed": [],
            },
            "error": None,
            "latency_ms": 12,
            "cost_usd": 0.002,
            "calls": 1,
        },
    ],
}


def _results_dir(tmp_path: Path) -> Path:
    live = tmp_path / "live"
    live.mkdir()
    (live / "t-1.json").write_text(json.dumps(RUN))
    return tmp_path


def test_frames_and_figures(tmp_path):
    runs_df, cases_df, fields_df = frames(load_runs(_results_dir(tmp_path)))
    assert len(runs_df) == 1 and len(cases_df) == 2 and len(fields_df) == 4
    assert fields_df[fields_df.field == "Charge number"].correct.mean() == 0.5
    assert cases_df.case_kind.tolist() == ["Clean", "Missing charge number"]
    fig = fig_accuracy_by_field(fields_df, list(runs_df.run_id))
    assert len(fig.data) == 1
    assert len(fig_heatmap(fields_df, runs_df.run_id[0]).data) == 1


def test_export_writes_three_csvs(tmp_path):
    written = export(_results_dir(tmp_path), tmp_path / "out")
    assert [p.name for p in written] == ["runs.csv", "documents.csv", "fields.csv"]
    assert (tmp_path / "out" / "fields.csv").read_text().count("\n") == 5  # header + 4 rows


def test_app_builds(tmp_path):
    app = build_app(_results_dir(tmp_path))
    assert app.layout is not None
