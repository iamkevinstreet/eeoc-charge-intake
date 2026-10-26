"""The dashboard and the Tableau export read the same results and agree with the runner's summary."""

import copy
import json
from pathlib import Path

from eeoc_intake.dashboard import (
    build_app,
    export_figures,
    fig_accuracy_by_field,
    fig_cost,
    fig_heatmap,
    fig_latency,
    frames,
    load_runs,
    tile_rows,
)
from eeoc_intake.evals.export import export
from eeoc_intake.evals.stats import clear_change

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


def _two_runs(tmp_path: Path) -> Path:
    """A second, later run that gets charge_number right on charge-004 and costs a little more."""
    later = copy.deepcopy(RUN)
    later["started_at"] = "2026-10-15T01:00:00+00:00"
    later["summary"] = {**RUN["summary"], "field_accuracy": 1.0, "cost_per_case_usd": 0.002}
    later["results"][1]["scores"]["f_charge_number"] = 1
    live = tmp_path / "live"
    live.mkdir()
    (live / "t-1.json").write_text(
        json.dumps({**RUN, "summary": {**RUN["summary"], "cost_per_case_usd": 0.0015}})
    )
    (live / "t-2.json").write_text(json.dumps(later))
    return tmp_path


def test_comparison_marks_what_changed(tmp_path):
    runs_df, cases_df, fields_df = frames(load_runs(_two_runs(tmp_path)))
    ids = list(runs_df.run_id)  # newest first: t-2, then t-1
    fig = fig_accuracy_by_field(fields_df, ids)
    roles = [tr.meta["role"] for tr in fig.data]
    assert roles.count("connector") == 1  # only Charge number moved
    assert [s.name for s in fig.layout.shapes] == ["highlight"]
    assert roles[-1] == "run-0"  # the run in focus is drawn last, on top
    assert len(fig_heatmap(fields_df, ids).data) == 2  # one panel per run
    assert [tr.meta["role"] for tr in fig_latency(cases_df, ids).data] == ["run-0", "run-1"]
    assert [tr.meta["role"] for tr in fig_cost(runs_df, ids).data] == ["run-0", "run-1"]
    tiles = {t["measure"]: t for t in tile_rows(runs_df, ids)}
    assert tiles["field_accuracy"]["delta"] == "up 5.0 pts" and tiles["field_accuracy"]["good"] is True
    assert tiles["cost_per_case_usd"]["good"] is False


def test_export_figures_carries_roles(tmp_path):
    payload = export_figures(_two_runs(tmp_path), tmp_path / "figures.json")
    assert [f["name"] for f in payload["figures"]] == ["by_field", "heatmap", "latency", "cost"]
    assert [r["run_id"] for r in payload["runs"]] == ["t-2", "t-1"]
    assert all(tr["meta"]["role"] for f in payload["figures"] for tr in f["spec"]["data"])


def _run_with(tmp_path: Path, name: str, started: str, latencies_ms: list[int], cost: float) -> None:
    """A live run of documents that are all right, with the given times and the same cost each."""
    run = copy.deepcopy(RUN)
    run["started_at"] = started
    base = run["results"][0]
    run["results"] = []
    for i, ms in enumerate(latencies_ms):
        r = copy.deepcopy(base)
        r["case_id"] = f"charge-{i:03d}"
        r["latency_ms"] = ms
        r["cost_usd"] = cost
        run["results"].append(r)
    run["cases"] = len(latencies_ms)
    run["summary"] = {
        **RUN["summary"],
        "field_accuracy": 1.0,
        "latency_p50_ms": sorted(latencies_ms)[len(latencies_ms) // 2],
        "cost_per_case_usd": cost,
    }
    live = tmp_path / "live"
    live.mkdir(exist_ok=True)
    (live / f"{name}.json").write_text(json.dumps(run))


def test_time_axis_fits_most_documents(tmp_path):
    times = [4000 + 37 * i % 900 for i in range(30)] + [16000]
    _run_with(tmp_path, "t-1", "2026-10-15T00:00:00+00:00", times, 0.001)
    runs_df, cases_df, _ = frames(load_runs(tmp_path))
    fig = fig_latency(cases_df, list(runs_df.run_id))
    low, high = fig.layout.xaxis.range
    assert 3 < low < 4 and high < 8  # no zero start, and the one slow document doesn't stretch the axis
    assert [a.text for a in fig.layout.annotations] == ["1 slower,<br>up to 16.0 s"]
    assert (
        len(fig.data[0].selectedpoints) == 30
    )  # the slow one is counted beside the row, not drawn at the edge


def test_tiles_call_only_changes_bigger_than_noise(tmp_path):
    same = [4000 + 53 * i % 700 for i in range(40)]
    _run_with(tmp_path, "t-1", "2026-10-15T00:00:00+00:00", same, 0.013363)
    _run_with(tmp_path, "t-2", "2026-10-15T01:00:00+00:00", [t + 60 for t in same], 0.013375)
    _run_with(tmp_path, "t-3", "2026-10-15T02:00:00+00:00", [t + 2000 for t in same], 0.013375)
    runs_df, cases_df, _ = frames(load_runs(tmp_path))
    near = {t["measure"]: t for t in tile_rows(runs_df, ["t-2", "t-1"], cases_df)}
    # 0.1 s slower shows on the tile, but 60 ms is well inside the spread of these times
    assert near["latency_p50_ms"]["delta"] == "no clear change" and near["latency_p50_ms"]["good"] is None
    assert near["cost_per_case_usd"]["delta"] == "no change"  # $0.000012 rounds to nothing at four places
    far = {t["measure"]: t for t in tile_rows(runs_df, ["t-3", "t-1"], cases_df)}
    assert far["latency_p50_ms"]["delta"] == "up 2.0 s" and far["latency_p50_ms"]["good"] is False


def test_tiles_are_judged_together(tmp_path):
    """110 ms slower clears the 0.05 line on its own (p about 0.02), but not Holm's 0.05 / 6 for six tiles."""
    same = [4000 + 53 * i % 700 for i in range(40)]
    slower = [t + 110 for t in same]
    assert clear_change(same, slower, "rank")
    _run_with(tmp_path, "t-1", "2026-10-15T00:00:00+00:00", same, 0.013363)
    _run_with(tmp_path, "t-2", "2026-10-15T01:00:00+00:00", slower, 0.013363)
    runs_df, cases_df, _ = frames(load_runs(tmp_path))
    tiles = {t["measure"]: t for t in tile_rows(runs_df, ["t-2", "t-1"], cases_df)}
    assert tiles["latency_p50_ms"]["delta"] == "no clear change" and tiles["latency_p50_ms"]["good"] is None


def test_export_figures_keeps_three_runs(tmp_path):
    """The case study draws up to three runs, newest first, so the export keeps the latest three."""
    results = _two_runs(tmp_path)
    third = copy.deepcopy(RUN)
    third["started_at"] = "2026-10-15T02:00:00+00:00"
    (results / "live" / "t-3.json").write_text(json.dumps(third))
    payload = export_figures(results, tmp_path / "figures.json")
    assert [r["run_id"] for r in payload["runs"]] == ["t-3", "t-2", "t-1"]
    roles = {tr["meta"]["role"] for tr in payload["figures"][0]["spec"]["data"]}
    assert {"run-0", "run-1", "run-2"} <= roles


def test_app_builds(tmp_path):
    app = build_app(_results_dir(tmp_path))
    assert app.layout is not None
