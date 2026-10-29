########################################################################
#             backend/src/eeoc_intake/dashboard/heatmap.py             #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Draws the accuracy chart by field and kind of document: a panel per
run, every panel on the same scale. Only the cells that are not all
right carry a number; the colour says the rest. The fields are listed
in the order the record lists them, as in the chart by field.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

from collections.abc import Sequence
from typing import Final

# Third-party
import pandas as pd
import plotly.graph_objects as go
from kds.args import missing, required
from kds.logs import get_logger
from plotly.subplots import make_subplots

# Local
from eeoc_intake.config import SETTINGS
from eeoc_intake.dashboard.field_charts import field_order
from eeoc_intake.dashboard.theme import THEMES, Theme, hover, shared_layout
from eeoc_intake.dashboard.views import long_labels, present
from eeoc_intake.evals.shares import pct_label

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the run id column, from the config")
RUN_ID: Final = SETTINGS.columns_run_id
# log.debug("Takes the document id column, from the config")
CASE_ID: Final = SETTINGS.columns_case_id
# log.debug("Takes the kind of document column, from the config")
CASE_KIND: Final = SETTINGS.columns_case_kind
# log.debug("Takes the field column, from the config")
FIELD: Final = SETTINGS.columns_field
# log.debug("Takes the column that is 1 when a field is right, from the config")
CORRECT: Final = SETTINGS.columns_correct
# log.debug("Takes the name of each kind of document, from the config")
KIND_LABELS: Final = SETTINGS.labels_kinds
# log.debug("Takes the column head of each kind of document, from the config")
KIND_TICKS: Final = SETTINGS.charts_kind_heads
# log.debug("Takes the light scheme's name, from the config")
LIGHT: Final = SETTINGS.charts_light_scheme
# log.debug("Takes the size of chart text, from the config")
FONT_SIZE: Final = SETTINGS.charts_font_size
# log.debug("Takes the size of value-axis ticks and small notes, from the config")
TICK_SIZE: Final = SETTINGS.charts_tick_size
# log.debug("Takes the margin every chart keeps at its edges, from the config")
EDGE: Final = SETTINGS.charts_edge
# log.debug("Takes the edge titles line up on, from the config")
LEFT: Final = SETTINGS.charts_align
# log.debug("Takes the tick format of a share: a whole percent, from the config")
PERCENT_TICKS: Final = SETTINGS.charts_percent_ticks

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the ticks of the heatmap's colour bar")
HALVES: Final = (0, 0.5, 1)
# log.debug("Sets the gap between heatmap cells, in pixels")
CELL_GAP: Final = 3
# log.debug("Sets the heatmap's height when no run picked is held")
EMPTY_HEIGHT: Final = 300


########################################################################
#                      Accuracy by field and kind                      #
########################################################################
# log.debug("Defines the accuracy chart by field and kind of document")
def fig_heatmap(
    fields: pd.DataFrame | None = None,
    run_ids: str | Sequence[str] | None = None,
    theme: str = LIGHT,
    labels: dict[str, str] | None = None,
) -> go.Figure:
    """Returns fields right by field and kind, a panel per run.

    Every panel is on the same scale, and only the cells that are not
    all right carry a number; the colour says the rest.

    Args:
        fields: The fields table from `frames`. Required.
        run_ids: Up to three runs, the run in focus first. Required.
        theme: The colour scheme, light or dark.
        labels: Each run's name for titles and hover; long labels when
            None.

    Returns:
        The chart.
    """
    # log.debug("Takes the fields, which the caller must give")
    fields = required(fields=fields)
    # log.debug("Stops when the caller left out the run ids")
    if run_ids is None:
        # log.debug("Raises the missing-argument error")
        raise missing(run_ids=run_ids)
    # log.debug("Takes the scheme's colours")
    colours = THEMES[theme]
    # log.debug("Keeps the runs the table holds, at most three")
    ids = present(fields, run_ids)
    # log.debug("Draws an empty chart when the table holds none of them")
    if not ids:
        # log.debug("Returns the empty chart")
        return shared_layout(go.Figure(), EMPTY_HEIGHT, colours)
    # log.debug("Lists the fields the table holds, in record order")
    order = field_order(fields)
    # log.debug("Draws a panel per run")
    fig = _panels(fields, ids, labels or long_labels(fields, ids), order, colours)
    # As top_down, but keyed in the order the committed figures.json
    # has, so writing the figures again changes no byte of it.
    # log.debug("Lists the fields from the top down in every panel")
    fig.update_yaxes(autorange="reversed", categoryorder="array", categoryarray=order)
    # log.debug("Drops the grid and keeps the column heads level")
    fig.update_xaxes(showgrid=False, tickangle=0, tickfont=dict(size=TICK_SIZE))
    # log.debug("Puts each panel's title over the panel's left edge")
    _place_titles(fig, colours)
    # log.debug("Notes whether there are several panels, which then carry titles")
    several = len(ids) > 1
    # log.debug("Applies the shared layout, a row per field and room for the titles")
    fig = shared_layout(fig, 96 + 32 * len(order) + (24 if several else 0), colours)
    # log.debug("Leaves room for the titles above and the column heads below")
    fig.update_layout(margin=dict(t=30 if several else EDGE, b=40))
    # log.debug("Drops the grid the shared layout puts on the column axes")
    fig.update_xaxes(showgrid=False)
    # log.debug("Returns the chart")
    return fig


# log.debug("Defines the heatmap's panels")
def _panels(
    fields: pd.DataFrame | None = None,
    ids: list[str] | None = None,
    names: dict[str, str] | None = None,
    order: list[str] | None = None,
    colours: Theme | None = None,
) -> go.Figure:
    """Returns a panel per run, side by side on one field axis.

    Several panels carry their run's name as a title; the last panel
    shows the colour scale.

    Args:
        fields: The fields table from `frames`. Required.
        ids: The runs to draw, the run in focus first. Required.
        names: Each run's name, for the titles and the hover.
            Required.
        order: The fields, in the order they are listed. Required.
        colours: The scheme to draw in. Required.

    Returns:
        The figure with a panel per run.
    """
    # log.debug("Takes the fields, which the caller must give")
    fields = required(fields=fields)
    # log.debug("Takes the run ids, which the caller must give")
    ids = required(ids=ids)
    # log.debug("Takes the runs' names, which the caller must give")
    names = required(names=names)
    # log.debug("Takes the field order, which the caller must give")
    order = required(order=order)
    # log.debug("Takes the colours, which the caller must give")
    colours = required(colours=colours)
    # log.debug("Lays the panels out in one row, sharing the field axis")
    fig = make_subplots(
        rows=1,
        cols=len(ids),
        shared_yaxes=True,
        horizontal_spacing=0.035,
        subplot_titles=[names[r] for r in ids] if len(ids) > 1 else None,
    )
    # log.debug("Fills each panel with its run's cells")
    for col, run_id in enumerate(ids, start=1):
        # log.debug("Takes the run's rows")
        rows = fields[fields[RUN_ID] == run_id]
        # log.debug("Adds the run's cells to its panel; the last panel shows the scale")
        fig.add_trace(_cells(rows, order, names[run_id], colours, col == len(ids)), row=1, col=col)
    # log.debug("Returns the panels")
    return fig


# log.debug("Defines one run's cells")
def _cells(
    rows: pd.DataFrame | None = None,
    order: list[str] | None = None,
    label: str | None = None,
    colours: Theme | None = None,
    scale: bool | None = None,
) -> go.Heatmap:
    """Returns one run's share right per field and kind of document.

    Args:
        rows: The run's rows of the fields table. Required.
        order: The fields, in the order they are listed. Required.
        label: The run's name for the hover. Required.
        colours: The scheme to draw in. Required.
        scale: Whether this panel shows the colour scale. Required.

    Returns:
        The run's cells, with their numbers and hover notes.
    """
    # log.debug("Takes the rows, which the caller must give")
    rows = required(rows=rows)
    # log.debug("Takes the field order, which the caller must give")
    order = required(order=order)
    # log.debug("Takes the label, which the caller must give")
    label = required(label=label)
    # log.debug("Takes the colours, which the caller must give")
    colours = required(colours=colours)
    # log.debug("Takes whether to show the scale, which the caller must give")
    scale = required(scale=scale)
    # log.debug("Computes the share right per field and kind of document")
    pivot = rows.pivot_table(index=FIELD, columns=CASE_KIND, values=CORRECT, aggfunc="mean")
    # log.debug("Counts the documents of each kind")
    counts = rows.groupby(CASE_KIND)[CASE_ID].nunique()
    # log.debug("Puts the fields in record order")
    pivot = pivot.reindex(order)
    # log.debug("Lists the kinds the run has, in the order they are named")
    kinds = [k for k in KIND_LABELS.values() if k in pivot.columns]
    # log.debug("Puts the kinds in that order")
    pivot = pivot[kinds]
    # log.debug("Returns the cells, a number only where not all were right")
    return go.Heatmap(
        z=pivot.values,
        x=[f"{KIND_TICKS.get(k, k)}<br>({counts[k]})" for k in kinds],
        y=list(pivot.index),
        zmin=0,
        zmax=1,
        colorscale=[[0, colours.surface2], [1, colours.right]],
        xgap=CELL_GAP,
        ygap=CELL_GAP,
        text=[["" if pd.isna(v) or v >= 1 else pct_label(v) for v in row] for row in pivot.values],
        texttemplate="%{text}",
        textfont=dict(size=FONT_SIZE),
        showscale=scale,
        colorbar=dict(
            tickformat=PERCENT_TICKS,
            tickvals=list(HALVES),
            thickness=8,
            len=0.9,
            outlinewidth=0,
            tickfont=dict(color=colours.ink3, size=TICK_SIZE),
        ),
        customdata=_cell_notes(pivot, kinds, counts),
        hovertemplate=hover("%{customdata}", label),
        meta=dict(role="accuracy"),
    )


# log.debug("Defines the hover of each cell")
def _cell_notes(
    pivot: pd.DataFrame | None = None,
    kinds: list[str] | None = None,
    counts: pd.Series[int] | None = None,
) -> list[list[str]]:
    """Returns each cell's note: share, field, kind and documents.

    Args:
        pivot: The run's share right, a row per field and a column per
            kind. Required.
        kinds: The kinds, in the order of the columns. Required.
        counts: The documents of each kind. Required.

    Returns:
        A note per cell, row by row; "no documents" where the run had
        none of that kind.
    """
    # log.debug("Takes the shares, which the caller must give")
    pivot = required(pivot=pivot)
    # log.debug("Takes the kinds, which the caller must give")
    kinds = required(kinds=kinds)
    # log.debug("Takes the counts, which the caller must give")
    counts = required(counts=counts)
    # log.debug("Returns a note per cell, row by row")
    return [
        [
            "no documents"
            if pd.isna(v)
            else f"<b>{pct_label(v)}</b>  {field}, "
            f"{KIND_TICKS.get(k, k).replace('<br>', ' ')} ({counts[k]} documents)"
            for v, k in zip(row, kinds, strict=True)
        ]
        for field, row in zip(pivot.index, pivot.values, strict=True)
    ]


# log.debug("Defines where the panel titles sit")
def _place_titles(fig: go.Figure | None = None, colours: Theme | None = None) -> None:
    """Puts each panel's title over its left edge, in soft ink.

    Args:
        fig: The figure with its panels and their titles. Required.
        colours: The scheme to draw in. Required.
    """
    # log.debug("Takes the figure, which the caller must give")
    fig = required(fig=fig)
    # log.debug("Takes the colours, which the caller must give")
    colours = required(colours=colours)
    # log.debug("Walks the titles; only panel titles are notes so far")
    for i, note in enumerate(fig.layout.annotations, start=1):
        # log.debug("Finds the span of the panel's column axis")
        domain = fig.layout[f"xaxis{'' if i == 1 else i}"].domain
        # log.debug("Moves the title to the panel's left edge")
        note.update(font=dict(color=colours.ink2, size=FONT_SIZE), xanchor=LEFT, x=domain[0])
