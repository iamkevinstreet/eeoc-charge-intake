########################################################################
#             backend/src/eeoc_intake/dashboard/export.py              #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Writes the Plotly JSON of the four charts for the case study: the
latest live runs, up to three, as many as the charts draw. Each trace
carries its part in `meta.role` (run-0 is the latest run, run-1 the one
before it, run-2 the one before that, connector, accuracy) and each
highlight shape is named, so a page with its own palette can restyle
them and pick which run to put in focus. The titles stay in the
layout, for pages that draw them from there.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

# Third-party
from kds.args import required
from kds.logs import get_logger

# Local
from eeoc_intake.config import SETTINGS
from eeoc_intake.dashboard.data import frames, load_runs, run_labels
from eeoc_intake.dashboard.field_charts import fig_accuracy_by_field
from eeoc_intake.dashboard.heatmap import fig_heatmap
from eeoc_intake.dashboard.run_charts import fig_cost, fig_latency

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the run id column, from the config")
RUN_ID: Final = SETTINGS.columns_run_id
# log.debug("Takes the model column, from the config")
MODEL: Final = SETTINGS.columns_model
# log.debug("Takes the start time column, from the config")
STARTED_AT: Final = SETTINGS.columns_started_at
# log.debug("Takes the most runs a chart compares, from the config")
MAX_RUNS: Final = SETTINGS.charts_max_runs
# log.debug("Takes the light scheme's name, which the figures use, from the config")
LIGHT: Final = SETTINGS.charts_light_scheme
# log.debug("Takes the edge titles line up on, from the config")
LEFT: Final = SETTINGS.charts_align
# log.debug("Takes the title of the accuracy chart by field, from the config")
BY_FIELD_TITLE: Final = SETTINGS.charts_by_field_title
# log.debug("Takes the title of the accuracy chart by field and kind, from the config")
HEATMAP_TITLE: Final = SETTINGS.charts_heatmap_title
# log.debug("Takes the title of the time chart, from the config")
LATENCY_TITLE: Final = SETTINGS.charts_latency_title
# log.debug("Takes the title of the cost chart, from the config")
COST_TITLE: Final = SETTINGS.charts_cost_title
# log.debug("Takes the encoding the file is written in, from the config")
ENCODING: Final = SETTINGS.files_encoding

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the size of each chart's title")
TITLE_SIZE: Final = 14


########################################################################
#                          Case study figures                          #
########################################################################
# log.debug("Defines the export of the figures")
def export_figures(live: Path | None = None, out: Path | None = None) -> dict[str, Any]:
    """Writes the four charts of the latest live runs as Plotly JSON.

    Args:
        live: The folder of live runs. Required.
        out: The file to write; its folder is made if need be. Required.

    Returns:
        What was written: the latest run, the runs drawn and their
        labels, and each figure's name, title and Plotly spec.

    Raises:
        FileNotFoundError: When the folder holds no runs.
    """
    # log.debug("Takes the live results folder, which the caller must give")
    live = required(live=live)
    # log.debug("Takes the file to write, which the caller must give")
    out = required(out=out)
    # log.debug("Reads the live runs, newest first")
    runs = load_runs(live)
    # log.debug("Stops when there is nothing to draw")
    if not runs:
        # log.debug("Says where it looked and what to do")
        msg = f"no live runs in {live}: run a live evaluation first"
        # log.debug("Raises it")
        raise FileNotFoundError(msg)
    # log.debug("Builds the three tables")
    runs_df, cases_df, fields_df = frames(runs)
    # log.debug("Takes the latest runs, as many as the charts draw")
    ids = list(runs_df[RUN_ID][:MAX_RUNS])
    # log.debug("Names them")
    labels = run_labels(runs_df, ids)
    # log.debug("Takes the latest run")
    latest = runs_df.iloc[0]
    # log.debug("Draws the four charts in the light scheme, each with its name and title")
    figures = [
        ("by_field", BY_FIELD_TITLE, fig_accuracy_by_field(fields_df, ids, LIGHT, labels)),
        ("heatmap", HEATMAP_TITLE, fig_heatmap(fields_df, ids, LIGHT, labels)),
        ("latency", LATENCY_TITLE, fig_latency(cases_df, ids, LIGHT, labels)),
        ("cost", COST_TITLE, fig_cost(runs_df, ids, LIGHT, labels)),
    ]
    # log.debug("Writes each chart's title into its layout")
    for _, title, fig in figures:
        # log.debug("Sets the title at the top left")
        fig.update_layout(title=dict(text=title, x=0, xanchor=LEFT, font=dict(size=TITLE_SIZE)))
    # log.debug("Collects the latest run, the runs drawn and the figures")
    payload = dict(
        run_id=latest[RUN_ID],
        model=latest[MODEL],
        started_at=latest[STARTED_AT],
        runs=[dict(run_id=r, label=labels[r]) for r in ids],
        figures=[dict(name=n, title=t, spec=json.loads(f.to_json())) for n, t, f in figures],
    )
    # log.debug("Makes the file's folder")
    out.parent.mkdir(parents=True, exist_ok=True)
    # log.debug("Writes the JSON on one line")
    out.write_text(json.dumps(payload), encoding=ENCODING)
    # log.debug("Returns what was written")
    return payload
