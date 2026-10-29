########################################################################
#          backend/src/eeoc_intake/dashboard/field_charts.py           #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Draws the two accuracy charts: fields right by   #
#                     field, and by field and kind of document.        #
########################################################################
"""The accuracy charts: fields right by field, and by kind of document.

Both list the fields in the order the record does. The runs' key sits
above all the charts on the page, so no chart carries one of its own.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

import pandas as pd
import plotly.graph_objects as go
from kds.logs import get_logger
from plotly.subplots import make_subplots

from eeoc_intake.core.schema import SCORED_FIELDS
from eeoc_intake.dashboard.data import (
    CASE_ID,
    CASE_KIND,
    CORRECT,
    FIELD,
    RUN_ID,
    long_labels,
    present,
)
from eeoc_intake.dashboard.theme import (
    EDGE,
    FIELD_LABELS,
    FONT_SIZE,
    KIND_LABELS,
    KIND_TICKS,
    LEFT,
    LIGHT,
    THEMES,
    TICK_SIZE,
    Theme,
    hover,
    shared_layout,
    top_down,
)
from eeoc_intake.evals.stats import pct_label

# Module constants
log = get_logger(__name__)
# log.debug("Sets the smallest spread between runs that counts as a change")
NOISE: Final = 0.001
# log.debug("Sets half the height of a changed field's highlight, in rows")
HALF_BAND: Final = 0.42
# log.debug("Sets the tick format of a share: a whole percent")
PERCENT_TICKS: Final = ".0%"
# log.debug("Sets the ticks of the by-field chart's share axis")
QUARTERS: Final = (0, 0.25, 0.5, 0.75, 1)
# log.debug("Sets the ticks of the heatmap's colour bar")
HALVES: Final = (0, 0.5, 1)
# log.debug("Sets the height of the by-field chart above its rows")
DOTS_BASE: Final = 48
# log.debug("Sets the height of each field's row in the by-field chart")
DOTS_ROW: Final = 30
# log.debug("Sets the gap between heatmap cells, in pixels")
CELL_GAP: Final = 3
# log.debug("Sets the heatmap's height when no run picked is held")
EMPTY_HEIGHT: Final = 300


# log.debug("Defines the accuracy chart by field")
def fig_accuracy_by_field(
    fields: pd.DataFrame,
    run_ids: str | Sequence[str],
    theme: str = LIGHT,
    labels: dict[str, str] | None = None,
) -> go.Figure:
    """Return a dot per run on each field, joined where runs disagree.

    Fields that changed get the highlight, and their dots their share.

    Args:
        fields: The fields table from `frames`.
        run_ids: Up to three runs, the run in focus first.
        theme: The colour scheme, light or dark.
        labels: Each run's name for the hover; long labels when None.

    Returns:
        The chart.
    """
    # log.debug("Takes the scheme's colours")
    colours = THEMES[theme]
    # log.debug("Keeps the runs the table holds, at most three")
    ids = present(fields, run_ids)
    # log.debug("Names each run, from the labels given or the table")
    names = labels or long_labels(fields, ids)
    # log.debug("Computes each run's share right on each field")
    shares = fields[fields[RUN_ID].isin(ids)].groupby([RUN_ID, FIELD])[CORRECT].mean()
    # log.debug("Lists the fields the table holds, in record order")
    order = _field_order(fields)
    # log.debug("Starts an empty figure")
    fig = go.Figure()
    # log.debug("Highlights and joins the fields the runs disagree on")
    changed = _mark_changes(fig, shares, ids, order, colours)
    # log.debug("Adds each run's dots, earlier runs first so the run in focus is on top")
    for index in reversed(range(len(ids))):
        # log.debug("Adds one run's dots")
        fig.add_trace(
            _dots(
                [shares.get((ids[index], field)) for field in order],
                order,
                changed,
                index=index,
                label=names[ids[index]],
                colours=colours,
            )
        )
    # log.debug("Sets the share axis and lists the fields from the top down")
    fig.update_layout(
        xaxis=dict(range=[-0.02, 1.13], tickvals=list(QUARTERS), tickformat=PERCENT_TICKS),
        yaxis=dict(top_down(order), showgrid=True, gridcolor=colours.grid),
    )
    # log.debug("Returns the chart in the shared layout, a row per field")
    return shared_layout(fig, DOTS_BASE + DOTS_ROW * len(order), colours)


# log.debug("Defines the accuracy chart by field and kind of document")
def fig_heatmap(
    fields: pd.DataFrame,
    run_ids: str | Sequence[str],
    theme: str = LIGHT,
    labels: dict[str, str] | None = None,
) -> go.Figure:
    """Return fields right by field and kind, a panel per run.

    Every panel is on the same scale, and only the cells that are not
    all right carry a number; the colour says the rest.

    Args:
        fields: The fields table from `frames`.
        run_ids: Up to three runs, the run in focus first.
        theme: The colour scheme, light or dark.
        labels: Each run's name for titles and hover; long labels when
            None.

    Returns:
        The chart.
    """
    # log.debug("Takes the scheme's colours")
    colours = THEMES[theme]
    # log.debug("Keeps the runs the table holds, at most three")
    ids = present(fields, run_ids)
    # log.debug("Draws an empty chart when the table holds none of them")
    if not ids:
        # log.debug("Returns the empty chart")
        return shared_layout(go.Figure(), EMPTY_HEIGHT, colours)
    # log.debug("Lists the fields the table holds, in record order")
    order = _field_order(fields)
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


# log.debug("Defines the order fields are listed in")
def _field_order(fields: pd.DataFrame) -> list[str]:
    """Return the labels of the fields held, in record order."""
    # log.debug("Lists the field labels the table holds")
    held = set(fields[FIELD])
    # log.debug("Returns them in the order the record lists its fields")
    return [FIELD_LABELS[f] for f in SCORED_FIELDS if FIELD_LABELS[f] in held]


# log.debug("Defines the marks on the fields the runs disagree on")
def _mark_changes(
    fig: go.Figure,
    shares: pd.Series[float],
    ids: list[str],
    order: list[str],
    colours: Theme,
) -> list[str]:
    """Highlight each field the runs disagree on, and join its dots.

    Returns:
        The fields that changed by more than noise.
    """
    # log.debug("Starts with no changed fields")
    changed: list[str] = []
    # log.debug("Checks each field's row in turn")
    for row, field in enumerate(order):
        # log.debug("Collects the runs' shares on the field")
        values = [shares[(r, field)] for r in ids if (r, field) in shares]
        # log.debug("Marks the field when two or more runs differ by more than noise")
        if len(values) > 1 and max(values) - min(values) > NOISE:
            # log.debug("Notes the change")
            changed.append(field)
            # log.debug("Shades the field's row across the whole chart")
            fig.add_shape(
                type="rect",
                xref="paper",
                x0=0,
                x1=1,
                yref="y",
                y0=row - HALF_BAND,
                y1=row + HALF_BAND,
                fillcolor=colours.mark_wash,
                line=dict(width=0),
                layer="below",
                name="highlight",
            )
            # log.debug("Joins the lowest and the highest share with a line")
            fig.add_scatter(
                x=[min(values), max(values)],
                y=[field, field],
                mode="lines",
                line=dict(color=colours.rule, width=2),
                hoverinfo="skip",
                showlegend=False,
                meta=dict(role="connector"),
            )
    # log.debug("Returns the changed fields")
    return changed


# log.debug("Defines one run's dots")
def _dots(
    xs: list[float | None],
    order: list[str],
    changed: list[str],
    *,
    index: int,
    label: str,
    colours: Theme,
) -> go.Scatter:
    """Return one run's dots, its share written beside changed fields.

    Args:
        xs: The run's share on each field, None where it has none.
        order: The fields, in the order they are listed.
        changed: The fields the runs disagree on.
        index: The run's place among those picked; 0 is in focus.
        label: The run's name for the hover.
        colours: The scheme to draw in.
    """
    # log.debug("Returns the dots, the share written out so the hover never rounds up to all")
    return go.Scatter(
        x=xs,
        y=order,
        mode="markers+text",
        name=label,
        marker=dict(size=12, color=colours.runs[index], line=dict(color=colours.surface, width=2)),
        text=[
            pct_label(v) if (f in changed and v is not None) else ""
            for v, f in zip(xs, order, strict=True)
        ],
        textposition="middle right" if index == 0 else "middle left",
        textfont=dict(color=colours.ink2, size=FONT_SIZE),
        cliponaxis=False,
        customdata=[pct_label(v) if v is not None else "" for v in xs],
        hovertemplate=hover("<b>%{customdata}</b>  %{y}", label),
        meta=dict(role=f"run-{index}"),
    )


# log.debug("Defines the heatmap's panels")
def _panels(
    fields: pd.DataFrame,
    ids: list[str],
    names: dict[str, str],
    order: list[str],
    colours: Theme,
) -> go.Figure:
    """Return a panel per run, side by side on one field axis.

    Several panels carry their run's name as a title; the last panel
    shows the colour scale.
    """
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
    rows: pd.DataFrame, order: list[str], label: str, colours: Theme, scale: bool
) -> go.Heatmap:
    """Return one run's share right per field and kind of document.

    Args:
        rows: The run's rows of the fields table.
        order: The fields, in the order they are listed.
        label: The run's name for the hover.
        colours: The scheme to draw in.
        scale: Whether this panel shows the colour scale.
    """
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
def _cell_notes(pivot: pd.DataFrame, kinds: list[str], counts: pd.Series[int]) -> list[list[str]]:
    """Return each cell's note: share, field, kind and documents."""
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
def _place_titles(fig: go.Figure, colours: Theme) -> None:
    """Put each panel's title over its left edge, in soft ink."""
    # log.debug("Walks the titles; only panel titles are notes so far")
    for i, note in enumerate(fig.layout.annotations, start=1):
        # log.debug("Finds the span of the panel's column axis")
        domain = fig.layout[f"xaxis{'' if i == 1 else i}"].domain
        # log.debug("Moves the title to the panel's left edge")
        note.update(font=dict(color=colours.ink2, size=FONT_SIZE), xanchor=LEFT, x=domain[0])
