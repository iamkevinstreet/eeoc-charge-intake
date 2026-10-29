########################################################################
#                   backend/tests/test_dashboard.py                    #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests the dashboard's tables, the Tableau and figures exports, the
command line and the app. The charts and tiles have their own tests.

Each test writes its own small runs under tmp_path and passes the
folders explicitly, so none depends on the current folder or settings.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import copy
import json
from pathlib import Path

# Third-party
import pytest
from kds.logs import get_logger

# Local
from eeoc_intake.config import get_app_settings
from eeoc_intake.dashboard.__main__ import main
from eeoc_intake.dashboard.app import build_app
from eeoc_intake.dashboard.data import frames, load_runs, run_labels
from eeoc_intake.dashboard.export import export_figures
from eeoc_intake.dashboard.field_charts import fig_accuracy_by_field
from eeoc_intake.dashboard.heatmap import fig_heatmap
from eeoc_intake.evals.export import export
from support import RUN, one_run, two_runs

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Matches Dash 4's warning that its tables will move to a separate package")
TABLE_DEPRECATED = r"ignore:\s*The dash_table.DataTable will be removed:DeprecationWarning"


########################################################################
#                           Dashboard tests                            #
########################################################################
# log.debug("Defines the test of the tables and the single-run charts")
def test_frames_and_figures(tmp_path: Path) -> None:
    """Checks one run makes a run row, two documents and four fields.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Builds the tables")
    runs_df, cases_df, fields_df = frames(load_runs(one_run(tmp_path)))
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
    """Checks the export writes runs, documents and fields as CSV.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Exports the live run")
    written = export(one_run(tmp_path), None, tmp_path / "out")
    # log.debug("Checks the three files, in order")
    assert [p.name for p in written] == ["runs.csv", "documents.csv", "fields.csv"]
    # log.debug("Checks the field file has a header and four rows")
    assert (tmp_path / "out" / "fields.csv").read_text(encoding="utf-8").count("\n") == 5


# log.debug("Defines the test of the parts the case study restyles")
def test_export_figures_carries_roles(tmp_path: Path) -> None:
    """Checks each trace says its part, for the case study to restyle.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Exports the figures of both runs")
    payload = export_figures(two_runs(tmp_path), tmp_path / "figures.json")
    # log.debug("Checks the four figures, in order")
    assert [f["name"] for f in payload["figures"]] == ["by_field", "heatmap", "latency", "cost"]
    # log.debug("Checks the runs, newest first")
    assert [r["run_id"] for r in payload["runs"]] == ["t-2", "t-1"]
    # log.debug("Checks every trace has a part")
    assert all(trace["meta"]["role"] for f in payload["figures"] for trace in f["spec"]["data"])


# log.debug("Defines the test that the export keeps the latest three runs")
def test_export_figures_keeps_three_runs(tmp_path: Path) -> None:
    """Checks the figures draw up to three runs, newest first.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Writes two runs")
    live = two_runs(tmp_path)
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
    """Checks an empty folder is refused, saying what to do.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Exports from a folder that does not exist")
    with pytest.raises(FileNotFoundError, match="no live runs"):
        # log.debug("Tries the export")
        export_figures(tmp_path / "nowhere", tmp_path / "figures.json")


# log.debug("Defines the test of the live and smoke folders")
def test_smoke_runs_come_from_their_own_folder(tmp_path: Path) -> None:
    """Checks smoke runs come only from a smoke folder, and are marked.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Writes the live run")
    live = one_run(tmp_path)
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
    """Checks the figures go beside the live runs when no path is given.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
        monkeypatch: pytest's helper for patching the environment and
            objects.
        capsys: pytest's capture of what the test prints.
    """
    # log.debug("Writes two runs")
    live = two_runs(tmp_path)
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
    """Checks the app lays out its page and serves it in its template.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Builds the app over the live run")
    app = build_app(one_run(tmp_path))
    # log.debug("Checks it has a layout")
    assert app.layout is not None
    # log.debug("Asks it for the page")
    page = app.server.test_client().get("/")
    # log.debug("Checks the page is served")
    assert page.status_code == 200
    # log.debug("Checks it is the site's template, with the app's title")
    assert "<title>EEOC charge intake: evaluation</title>" in page.text
