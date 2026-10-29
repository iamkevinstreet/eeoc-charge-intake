########################################################################
#                     backend/tests/test_charts.py                     #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests the dashboard's charts and tiles: what a comparison of two runs
marks, how the time axis fits the documents, and which changes the
tiles call bigger than run-to-run noise.

Each test writes its own small runs under tmp_path and passes the
folders explicitly, so none depends on the current folder or settings.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

from pathlib import Path

# Third-party
from kds.logs import get_logger

# Local
from eeoc_intake.dashboard.data import frames, load_runs
from eeoc_intake.dashboard.field_charts import fig_accuracy_by_field
from eeoc_intake.dashboard.heatmap import fig_heatmap
from eeoc_intake.dashboard.run_charts import fig_cost, fig_latency
from eeoc_intake.dashboard.tiles import tile_rows
from eeoc_intake.evals.stats import RANK, clear_change
from support import two_runs, write_run

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)


########################################################################
#                         Chart and tile tests                         #
########################################################################
# log.debug("Defines the test of a two-run comparison")
def test_comparison_marks_what_changed(tmp_path: Path) -> None:
    """Checks only the field that moved is marked; the focus run is top.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Builds the tables of both runs")
    runs_df, cases_df, fields_df = frames(load_runs(two_runs(tmp_path)))
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


# log.debug("Defines the test of the time axis")
def test_time_axis_fits_most_documents(tmp_path: Path) -> None:
    """Checks a slow document is counted beside its row, not drawn.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Makes thirty times between 4 and 5 seconds and one of 16")
    times = [4000 + 37 * i % 900 for i in range(30)] + [16000]
    # log.debug("Writes them as a run")
    write_run(tmp_path / "live", "t-1", "2026-10-15T00:00:00+00:00", times, 0.001)
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
    """Checks 60 ms is within the spread of these times and 2 s is not.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Makes forty times between 4 and 4.7 seconds")
    same = [4000 + 53 * i % 700 for i in range(40)]
    # log.debug("Names the live folder")
    live = tmp_path / "live"
    # log.debug("Writes a first run")
    write_run(live, "t-1", "2026-10-15T00:00:00+00:00", same, 0.013363)
    # log.debug("Writes a second run 60 ms slower, at a cost that rounds the same")
    write_run(live, "t-2", "2026-10-15T01:00:00+00:00", [t + 60 for t in same], 0.013375)
    # log.debug("Writes a third run 2 seconds slower")
    write_run(live, "t-3", "2026-10-15T02:00:00+00:00", [t + 2000 for t in same], 0.013375)
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
    """Checks 110 ms clears 0.05 alone (p about 0.02), not 0.05 / 6.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Makes forty times between 4 and 4.7 seconds")
    same = [4000 + 53 * i % 700 for i in range(40)]
    # log.debug("Makes the same times 110 ms slower")
    slower = [t + 110 for t in same]
    # log.debug("Checks the rank test alone calls it a change")
    assert clear_change(same, slower, RANK)
    # log.debug("Names the live folder")
    live = tmp_path / "live"
    # log.debug("Writes the first run")
    write_run(live, "t-1", "2026-10-15T00:00:00+00:00", same, 0.013363)
    # log.debug("Writes the slower run")
    write_run(live, "t-2", "2026-10-15T01:00:00+00:00", slower, 0.013363)
    # log.debug("Builds the tables")
    runs_df, cases_df, _ = frames(load_runs(live))
    # log.debug("Builds the tiles of the slower run against the first")
    tiles = {tile["measure"]: tile for tile in tile_rows(runs_df, ["t-2", "t-1"], cases_df)}
    # log.debug("Checks the six tiles together do not call it a change")
    assert tiles["latency_p50_ms"]["delta"] == "no clear change"
    # log.debug("Checks it is neither good nor bad")
    assert tiles["latency_p50_ms"]["good"] is None
