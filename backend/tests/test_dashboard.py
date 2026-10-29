########################################################################
#                   backend/tests/test_dashboard.py                    #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Tests the dashboard's tables, charts, tiles,     #
#                     figures export, command line and app.            #
########################################################################
"""Tests for the dashboard and the exports that share its tables.

Each test writes its own small runs under tmp_path and passes the
folders explicitly, so none depends on the current folder or settings.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from kds.logs import get_logger

from eeoc_intake.config import get_app_settings
from eeoc_intake.dashboard.__main__ import main
from eeoc_intake.dashboard.app import build_app
from eeoc_intake.dashboard.data import frames, load_runs, run_labels
from eeoc_intake.dashboard.export import export_figures
from eeoc_intake.dashboard.field_charts import fig_accuracy_by_field, fig_heatmap
from eeoc_intake.dashboard.run_charts import fig_cost, fig_latency
from eeoc_intake.dashboard.tiles import tile_rows
from eeoc_intake.evals.export import export
from eeoc_intake.evals.stats import RANK, clear_change

# Module constants
log = get_logger(__name__)
# log.debug("Sets a live run of two documents; the second misses its charge number")
RUN: dict[str, Any] = {
    "name": "t",
    "model": "fake-model",
    "provider": "fake",
    "started_at": "2026-10-15T00:00:00+00:00",
    "finished_at": "2026-10-15T00:00:01+00:00",
    "prices_as_of": "2026-10-15",
    "cases": 2,
    "failures": 0,
    "summary": {
        "field_accuracy": 0.95,
        "unsupported_rate": 0.05,
        "latency_p50_ms": 10,
        "latency_p95_ms": 12,
    },
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
# log.debug("Matches Dash 4's warning that its tables will move to a separate package")
TABLE_DEPRECATED = r"ignore:\s*The dash_table.DataTable will be removed:DeprecationWarning"


# log.debug("Defines a live folder holding the one run")
def _live(tmp_path: Path) -> Path:
    """Write RUN as the only live run; return the live folder."""
    # log.debug("Makes the live folder")
    live = tmp_path / "live"
    # log.debug("Creates it")
    live.mkdir()
    # log.debug("Writes the run")
    (live / "t-1.json").write_text(json.dumps(RUN), encoding="utf-8")
    # log.debug("Returns the folder")
    return live


# log.debug("Defines a live folder holding two runs an hour apart")
def _two_runs(tmp_path: Path) -> Path:
    """A later run gets charge-004's charge number right, costs more."""
    # log.debug("Copies the run")
    later = copy.deepcopy(RUN)
    # log.debug("Starts it an hour later")
    later["started_at"] = "2026-10-15T01:00:00+00:00"
    # log.debug("Gives it every field right and a higher cost")
    later["summary"] = {**RUN["summary"], "field_accuracy": 1.0, "cost_per_case_usd": 0.002}
    # log.debug("Gets the second document's charge number right")
    later["results"][1]["scores"]["f_charge_number"] = 1
    # log.debug("Makes the live folder")
    live = tmp_path / "live"
    # log.debug("Creates it")
    live.mkdir()
    # log.debug("Writes the earlier run, with its cost")
    (live / "t-1.json").write_text(
        json.dumps({**RUN, "summary": {**RUN["summary"], "cost_per_case_usd": 0.0015}}),
        encoding="utf-8",
    )
    # log.debug("Writes the later run")
    (live / "t-2.json").write_text(json.dumps(later), encoding="utf-8")
    # log.debug("Returns the folder")
    return live


# log.debug("Defines a live run of documents that are all right")
def _run_with(live: Path, name: str, started: str, latencies_ms: list[int], cost: float) -> None:
    """Write a run with the given times and one cost per document."""
    # log.debug("Copies the run")
    run = copy.deepcopy(RUN)
    # log.debug("Sets its start")
    run["started_at"] = started
    # log.debug("Takes the first document as the pattern")
    base = run["results"][0]
    # log.debug("Makes one document per time")
    run["results"] = [
        {**copy.deepcopy(base), "case_id": f"charge-{i:03d}", "latency_ms": ms, "cost_usd": cost}
        for i, ms in enumerate(latencies_ms)
    ]
    # log.debug("Counts the documents")
    run["cases"] = len(latencies_ms)
    # log.debug("Writes the summary to match")
    run["summary"] = {
        **RUN["summary"],
        "field_accuracy": 1.0,
        "latency_p50_ms": sorted(latencies_ms)[len(latencies_ms) // 2],
        "cost_per_case_usd": cost,
    }
    # log.debug("Makes the live folder if it is not there yet")
    live.mkdir(exist_ok=True)
    # log.debug("Writes the run")
    (live / f"{name}.json").write_text(json.dumps(run), encoding="utf-8")


# log.debug("Defines the test of the tables and the single-run charts")
def test_frames_and_figures(tmp_path: Path) -> None:
    """One run makes one run row, two documents and four field rows."""
    # log.debug("Builds the tables")
    runs_df, cases_df, fields_df = frames(load_runs(_live(tmp_path)))
    # log.debug("Checks the row counts")
    assert [len(runs_df), len(cases_df), len(fields_df)] == [1, 2, 4]
    # log.debug("Checks one of the two charge numbers was right")
    assert fields_df[fields_df["field"] == "Charge number"]["correct"].mean() == 0.5
    # log.debug("Checks the kinds of document are named")
    assert cases_df["case_kind"].tolist() == ["Clean", "Missing charge number"]
    # log.debug("Checks the by-field chart draws one run")
    assert len(fig_accuracy_by_field(fields_df, list(runs_df["run_id"])).data) == 1
    # log.debug("Checks the heatmap takes a single run id")
    assert len(fig_heatmap(fields_df, str(runs_df["run_id"].iloc[0])).data) == 1


# log.debug("Defines the test of the Tableau export")
def test_export_writes_three_csvs(tmp_path: Path) -> None:
    """The export writes runs, documents and fields from the tables."""
    # log.debug("Exports the live run")
    written = export(_live(tmp_path), None, tmp_path / "out")
    # log.debug("Checks the three files, in order")
    assert [p.name for p in written] == ["runs.csv", "documents.csv", "fields.csv"]
    # log.debug("Checks the field file has a header and four rows")
    assert (tmp_path / "out" / "fields.csv").read_text(encoding="utf-8").count("\n") == 5


# log.debug("Defines the test of a two-run comparison")
def test_comparison_marks_what_changed(tmp_path: Path) -> None:
    """Only the field that moved is marked; the focus run is on top."""
    # log.debug("Builds the tables of both runs")
    runs_df, cases_df, fields_df = frames(load_runs(_two_runs(tmp_path)))
    # log.debug("Picks both, newest first: t-2, then t-1")
    ids = list(runs_df["run_id"])
    # log.debug("Draws the by-field chart")
    fig = fig_accuracy_by_field(fields_df, ids)
    # log.debug("Lists each trace's part")
    roles = [trace.meta["role"] for trace in fig.data]
    # log.debug("Checks one line joins dots: only Charge number moved")
    assert roles.count("connector") == 1
    # log.debug("Checks the one highlight is named for restyling")
    assert [shape.name for shape in fig.layout.shapes] == ["highlight"]
    # log.debug("Checks the run in focus is drawn last, on top")
    assert roles[-1] == "run-0"
    # log.debug("Checks the heatmap has a panel per run")
    assert len(fig_heatmap(fields_df, ids).data) == 2
    # log.debug("Checks the time chart has a row per run, in focus first")
    assert [trace.meta["role"] for trace in fig_latency(cases_df, ids).data] == ["run-0", "run-1"]
    # log.debug("Checks the cost chart has a bar per run, in focus first")
    assert [trace.meta["role"] for trace in fig_cost(runs_df, ids).data] == ["run-0", "run-1"]
    # log.debug("Builds the tiles without the documents, so every change counts")
    tiles = {tile["measure"]: tile for tile in tile_rows(runs_df, ids)}
    # log.debug("Checks fields right went up five points")
    assert tiles["field_accuracy"]["delta"] == "up 5.0 pts"
    # log.debug("Checks that is for the better")
    assert tiles["field_accuracy"]["good"] is True
    # log.debug("Checks the higher cost is for the worse")
    assert tiles["cost_per_case_usd"]["good"] is False


# log.debug("Defines the test of the parts the case study restyles")
def test_export_figures_carries_roles(tmp_path: Path) -> None:
    """Every trace says its part, so the case study can restyle it."""
    # log.debug("Exports the figures of both runs")
    payload = export_figures(_two_runs(tmp_path), tmp_path / "figures.json")
    # log.debug("Checks the four figures, in order")
    assert [f["name"] for f in payload["figures"]] == ["by_field", "heatmap", "latency", "cost"]
    # log.debug("Checks the runs, newest first")
    assert [r["run_id"] for r in payload["runs"]] == ["t-2", "t-1"]
    # log.debug("Checks every trace has a part")
    assert all(trace["meta"]["role"] for f in payload["figures"] for trace in f["spec"]["data"])


# log.debug("Defines the test of the time axis")
def test_time_axis_fits_most_documents(tmp_path: Path) -> None:
    """One slow document is counted beside its row, not stretched to."""
    # log.debug("Makes thirty times between 4 and 5 seconds and one of 16")
    times = [4000 + 37 * i % 900 for i in range(30)] + [16000]
    # log.debug("Writes them as a run")
    _run_with(tmp_path / "live", "t-1", "2026-10-15T00:00:00+00:00", times, 0.001)
    # log.debug("Builds the tables")
    runs_df, cases_df, _ = frames(load_runs(tmp_path / "live"))
    # log.debug("Draws the time chart")
    fig = fig_latency(cases_df, list(runs_df["run_id"]))
    # log.debug("Reads the axis range")
    low, high = fig.layout.xaxis.range
    # log.debug("Checks the axis neither starts at zero nor stretches to the slow one")
    assert 3 < low < 4 and high < 8
    # log.debug("Checks the slow one is noted beside the row")
    assert [note.text for note in fig.layout.annotations] == ["1 slower,<br>up to 16.0 s"]
    # log.debug("Checks the slow one's dot is left out, not cut at the edge")
    assert len(fig.data[0].selectedpoints) == 30


# log.debug("Defines the test that tiles mark only changes bigger than noise")
def test_tiles_call_only_changes_bigger_than_noise(tmp_path: Path) -> None:
    """60 ms is within the spread of these times; 2 s is not."""
    # log.debug("Makes forty times between 4 and 4.7 seconds")
    same = [4000 + 53 * i % 700 for i in range(40)]
    # log.debug("Names the live folder")
    live = tmp_path / "live"
    # log.debug("Writes a first run")
    _run_with(live, "t-1", "2026-10-15T00:00:00+00:00", same, 0.013363)
    # log.debug("Writes a second run 60 ms slower, at a cost that rounds the same")
    _run_with(live, "t-2", "2026-10-15T01:00:00+00:00", [t + 60 for t in same], 0.013375)
    # log.debug("Writes a third run 2 seconds slower")
    _run_with(live, "t-3", "2026-10-15T02:00:00+00:00", [t + 2000 for t in same], 0.013375)
    # log.debug("Builds the tables")
    runs_df, cases_df, _ = frames(load_runs(live))
    # log.debug("Builds the tiles of the second run against the first")
    near = {tile["measure"]: tile for tile in tile_rows(runs_df, ["t-2", "t-1"], cases_df)}
    # log.debug("Checks 0.1 s slower on the tile is no clear change")
    assert near["latency_p50_ms"]["delta"] == "no clear change"
    # log.debug("Checks no clear change is neither good nor bad")
    assert near["latency_p50_ms"]["good"] is None
    # log.debug("Checks a cost change of $0.000012 rounds to nothing at four places")
    assert near["cost_per_case_usd"]["delta"] == "no change"
    # log.debug("Builds the tiles of the third run against the first")
    far = {tile["measure"]: tile for tile in tile_rows(runs_df, ["t-3", "t-1"], cases_df)}
    # log.debug("Checks 2 s slower is a change")
    assert far["latency_p50_ms"]["delta"] == "up 2.0 s"
    # log.debug("Checks it is for the worse")
    assert far["latency_p50_ms"]["good"] is False


# log.debug("Defines the test that the six tiles are judged together")
def test_tiles_are_judged_together(tmp_path: Path) -> None:
    """110 ms slower clears 0.05 alone (p about 0.02), not 0.05 / 6."""
    # log.debug("Makes forty times between 4 and 4.7 seconds")
    same = [4000 + 53 * i % 700 for i in range(40)]
    # log.debug("Makes the same times 110 ms slower")
    slower = [t + 110 for t in same]
    # log.debug("Checks the rank test alone calls it a change")
    assert clear_change(same, slower, RANK)
    # log.debug("Names the live folder")
    live = tmp_path / "live"
    # log.debug("Writes the first run")
    _run_with(live, "t-1", "2026-10-15T00:00:00+00:00", same, 0.013363)
    # log.debug("Writes the slower run")
    _run_with(live, "t-2", "2026-10-15T01:00:00+00:00", slower, 0.013363)
    # log.debug("Builds the tables")
    runs_df, cases_df, _ = frames(load_runs(live))
    # log.debug("Builds the tiles of the slower run against the first")
    tiles = {tile["measure"]: tile for tile in tile_rows(runs_df, ["t-2", "t-1"], cases_df)}
    # log.debug("Checks the six tiles together do not call it a change")
    assert tiles["latency_p50_ms"]["delta"] == "no clear change"
    # log.debug("Checks it is neither good nor bad")
    assert tiles["latency_p50_ms"]["good"] is None


# log.debug("Defines the test that the export keeps the latest three runs")
def test_export_figures_keeps_three_runs(tmp_path: Path) -> None:
    """The case study draws up to three runs, newest first."""
    # log.debug("Writes two runs")
    live = _two_runs(tmp_path)
    # log.debug("Copies the run for a third")
    third = copy.deepcopy(RUN)
    # log.debug("Starts it last")
    third["started_at"] = "2026-10-15T02:00:00+00:00"
    # log.debug("Writes it")
    (live / "t-3.json").write_text(json.dumps(third), encoding="utf-8")
    # log.debug("Exports the figures")
    payload = export_figures(live, tmp_path / "figures.json")
    # log.debug("Checks the three runs, newest first")
    assert [r["run_id"] for r in payload["runs"]] == ["t-3", "t-2", "t-1"]
    # log.debug("Lists the parts of the by-field chart's traces")
    roles = {trace["meta"]["role"] for trace in payload["figures"][0]["spec"]["data"]}
    # log.debug("Checks each run has its part")
    assert {"run-0", "run-1", "run-2"} <= roles


# log.debug("Defines the test that the export needs live runs")
def test_export_figures_needs_live_runs(tmp_path: Path) -> None:
    """An empty folder is refused with a message saying what to do."""
    # log.debug("Exports from a folder that does not exist")
    with pytest.raises(FileNotFoundError, match="no live runs"):
        # log.debug("Tries the export")
        export_figures(tmp_path / "nowhere", tmp_path / "figures.json")


# log.debug("Defines the test of the live and smoke folders")
def test_smoke_runs_come_from_their_own_folder(tmp_path: Path) -> None:
    """Smoke runs are read only from a smoke folder, and marked."""
    # log.debug("Writes the live run")
    live = _live(tmp_path)
    # log.debug("Writes an index beside it, which is not a run")
    (live / "index.json").write_text(json.dumps({"runs": ["t-1.json"]}), encoding="utf-8")
    # log.debug("Makes the smoke folder")
    smoke = tmp_path / "smoke"
    # log.debug("Creates it")
    smoke.mkdir()
    # log.debug("Writes a smoke run a day later")
    (smoke / "s-1.json").write_text(
        json.dumps({**RUN, "started_at": "2026-10-16T00:00:00+00:00"}), encoding="utf-8"
    )
    # log.debug("Reads both folders")
    runs = load_runs(live, smoke)
    # log.debug("Checks both runs, newest first, each with its kind")
    assert [(r["run_id"], r["kind"]) for r in runs] == [("s-1", "smoke"), ("t-1", "live")]
    # log.debug("Checks the live folder alone holds just the live run")
    assert [r["run_id"] for r in load_runs(live)] == ["t-1"]
    # log.debug("Checks a smoke folder that does not exist adds nothing")
    assert [r["run_id"] for r in load_runs(live, tmp_path / "no-smoke")] == ["t-1"]
    # log.debug("Checks the short names mark the smoke run")
    assert run_labels(frames(runs)[0], ["s-1", "t-1"]) == {
        "s-1": "Oct 16, 00:00 UTC (smoke)",
        "t-1": "Oct 15, 00:00 UTC",
    }


# log.debug("Defines the test of the figures command")
def test_command_writes_figures_beside_the_live_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without a path, the figures go beside the live runs."""
    # log.debug("Writes two runs")
    live = _two_runs(tmp_path)
    # log.debug("Points [data] results at them")
    monkeypatch.setenv("DATA_RESULTS", str(live))
    # log.debug("Sends any log file to the temp folder")
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    # log.debug("Forgets any cached settings, so the command reads these")
    get_app_settings.cache_clear()
    # log.debug("Checks the command succeeds")
    assert main(["--export-figures"]) == 0
    # log.debug("Checks it says what it wrote")
    assert "(4 figures for t-2)" in capsys.readouterr().out
    # log.debug("Reads the file it wrote")
    written = json.loads((live / "figures.json").read_text(encoding="utf-8"))
    # log.debug("Checks it holds both runs")
    assert [r["run_id"] for r in written["runs"]] == ["t-2", "t-1"]


# log.debug("Defines the test that the app builds and serves its page")
@pytest.mark.filterwarnings(TABLE_DEPRECATED)
def test_app_builds(tmp_path: Path) -> None:
    """The app lays out its page and serves it in its template."""
    # log.debug("Builds the app over the live run")
    app = build_app(_live(tmp_path))
    # log.debug("Checks it has a layout")
    assert app.layout is not None
    # log.debug("Asks it for the page")
    page = app.server.test_client().get("/")
    # log.debug("Checks the page is served")
    assert page.status_code == 200
    # log.debug("Checks it is the site's template, with the app's title")
    assert "<title>EEOC charge intake: evaluation</title>" in page.text
