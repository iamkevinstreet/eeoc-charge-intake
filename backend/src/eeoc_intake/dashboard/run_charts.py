########################################################################
#           backend/src/eeoc_intake/dashboard/run_charts.py            #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Draws the two charts with a row per run: seconds per document, each
document a dot over its run's box, and cost per document, a bar per
run.
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

# Local
from eeoc_intake.config import SETTINGS
from eeoc_intake.dashboard.theme import THEMES, Theme, dollars, hover, shared_layout, top_down
from eeoc_intake.dashboard.views import long_labels, present
from eeoc_intake.evals.shares import fixed

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the run id column, from the config")
RUN_ID: Final = SETTINGS.columns_run_id
# log.debug("Takes the document id column, from the config")
CASE_ID: Final = SETTINGS.columns_case_id
# log.debug("Takes the column of each document's time, from the config")
LATENCY_MS: Final = SETTINGS.columns_latency_ms
# log.debug("Takes the runs table's cost per document column, from the config")
COST_PER_CASE: Final = SETTINGS.columns_cost_per_case
# log.debug("Takes the milliseconds in a second, from the config")
MS_PER_SECOND: Final = SETTINGS.units_ms_per_second
# log.debug("Takes the light scheme's name, from the config")
LIGHT: Final = SETTINGS.charts_light_scheme
# log.debug("Takes the size of chart text, from the config")
FONT_SIZE: Final = SETTINGS.charts_font_size
# log.debug("Takes the size of value-axis ticks and small notes, from the config")
TICK_SIZE: Final = SETTINGS.charts_tick_size
# log.debug("Takes the colour that lets the card show through, from the config")
CLEAR: Final = SETTINGS.charts_clear
# log.debug("Takes the edge notes line up on, from the config")
LEFT: Final = SETTINGS.charts_align

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the height of a chart with a row per run, above its rows")
RUNS_BASE: Final = 64
# log.debug("Sets where the middle half of a run's times starts")
LOWER_QUARTILE: Final = 0.25
# log.debug("Sets where the middle half of a run's times ends")
UPPER_QUARTILE: Final = 0.75
# log.debug("Sets the far-out fence: this many spreads of the middle half past it")
FENCE_SPREADS: Final = 3
# log.debug("Sets the least padding at each end of the time axis, in seconds")
MIN_PAD: Final = 0.15
# log.debug("Sets the padding at each end as a share of the times shown")
PAD_SHARE: Final = 0.06
# log.debug("Sets how far the dots spread across their row")
JITTER: Final = 0.6
# log.debug("Sets the width of a box's whiskers, as a share of the box")
WHISKER_WIDTH: Final = 0.6


########################################################################
#                         Time and cost charts                         #
########################################################################
# log.debug("Defines the time chart")
def fig_latency(
    cases: pd.DataFrame | None = None,
    run_ids: str | Sequence[str] | None = None,
    theme: str = LIGHT,
    labels: dict[str, str] | None = None,
) -> go.Figure:
    """Returns each document's time as a dot over its run's box.

    The box spans the middle half of the times, and each row names its
    run's typical (median) time. Documents past the end of the axis are
    counted beside their row instead.

    Args:
        cases: The documents table from `frames`. Required.
        run_ids: Up to three runs, the run in focus first. Required.
        theme: The colour scheme, light or dark.
        labels: Each run's name; long labels when None.

    Returns:
        The chart.
    """
    # log.debug("Takes the documents table, which the caller must give")
    cases = required(cases=cases)
    # log.debug("Stops when the caller left out the run ids")
    if run_ids is None:
        # log.debug("Raises the missing-argument error")
        raise missing(run_ids=run_ids)
    # log.debug("Takes the scheme's colours")
    colours = THEMES[theme]
    # log.debug("Keeps the runs the table holds, at most three")
    ids = present(cases, run_ids)
    # log.debug("Names each run, from the labels given or the table")
    names = labels or long_labels(cases, ids)
    # log.debug("Reads each run's times in seconds")
    secs = {r: cases.loc[cases[RUN_ID] == r, LATENCY_MS] / MS_PER_SECOND for r in ids}
    # log.debug("Fits the time axis to where the documents fall")
    x_range = _time_axis(list(secs.values()))
    # log.debug("Starts an empty figure")
    fig = go.Figure()
    # log.debug("Starts the list of row names")
    rows: list[str] = []
    # log.debug("Draws each run's row in turn")
    for index, run_id in enumerate(ids):
        # log.debug("Draws the run's dots and box, and keeps its row's name")
        rows.append(
            _time_row(
                fig,
                cases[cases[RUN_ID] == run_id],
                secs[run_id],
                x_range[1],
                index=index,
                label=names[run_id],
                colours=colours,
            )
        )
    # log.debug("Lists the runs from the top down and fits the time axis")
    fig.update_layout(yaxis=top_down(rows), xaxis=dict(range=x_range, ticksuffix=" s"))
    # log.debug("Applies the shared layout, a row per run")
    fig = shared_layout(fig, RUNS_BASE + 62 * max(1, len(ids)), colours)
    # log.debug("Makes room on the right when a row notes slower documents")
    if fig.layout.annotations:
        # log.debug("Widens the right margin")
        fig.update_layout(margin=dict(r=88))
    # log.debug("Returns the chart")
    return fig


# log.debug("Defines the cost chart")
def fig_cost(
    runs_df: pd.DataFrame | None = None,
    run_ids: str | Sequence[str] | None = None,
    theme: str = LIGHT,
    labels: dict[str, str] | None = None,
) -> go.Figure:
    """Returns the cost per document at list prices, a bar per run.

    Each bar carries its cost at its end.

    Args:
        runs_df: The runs table from `frames`. Required.
        run_ids: Up to three runs, the run in focus first. Required.
        theme: The colour scheme, light or dark.
        labels: Each run's name; long labels when None.

    Returns:
        The chart.
    """
    # log.debug("Takes the runs table, which the caller must give")
    runs_df = required(runs_df=runs_df)
    # log.debug("Stops when the caller left out the run ids")
    if run_ids is None:
        # log.debug("Raises the missing-argument error")
        raise missing(run_ids=run_ids)
    # log.debug("Takes the scheme's colours")
    colours = THEMES[theme]
    # log.debug("Keeps the runs the table holds, at most three")
    ids = present(runs_df, run_ids)
    # log.debug("Names each run, from the labels given or the table")
    names = labels or long_labels(runs_df, ids)
    # log.debug("Starts an empty figure")
    fig = go.Figure()
    # log.debug("Starts the highest cost at zero")
    top = 0.0
    # log.debug("Draws each run's bar in turn")
    for index, run_id in enumerate(ids):
        # log.debug("Reads the run's cost per document, a missing one as zero")
        cost = float(runs_df.loc[runs_df[RUN_ID] == run_id, COST_PER_CASE].fillna(0).iloc[0])
        # log.debug("Keeps the highest cost, which sets the axis")
        top = max(top, cost)
        # log.debug("Adds the run's bar")
        fig.add_trace(_cost_bar(cost, index=index, label=names[run_id], colours=colours))
    # log.debug("Lists the runs from the top down, with room for each bar's value")
    fig.update_layout(
        barmode="overlay",
        yaxis=top_down([names[r] for r in ids]),
        xaxis=dict(tickprefix="$", tickformat=".3f", range=[0, max(0.01, top * 1.32)]),
    )
    # log.debug("Returns the chart in the shared layout, a row per run")
    return shared_layout(fig, RUNS_BASE + 52 * max(1, len(ids)), colours)


# log.debug("Defines the fit of the time axis")
def _time_axis(secs: list[pd.Series[float]] | None = None) -> list[float]:
    """Returns the time axis's range, fitted to where documents fall.

    Times have a long right tail, so the axis stops at the far-out fence
    (the upper quartile plus three times the spread of the middle half)
    of the most spread-out run, and documents past it are noted beside
    their row rather than stretched across the chart. It never starts
    below zero.

    Args:
        secs: Each run's times, in seconds. Required.

    Returns:
        The axis's start and end, in seconds.
    """
    # log.debug("Takes the times, which the caller must give")
    secs = required(secs=secs)
    # log.debug("Keeps the runs with any documents")
    shown = [s for s in secs if len(s)]
    # log.debug("Finds the fastest document of all")
    fastest = min(float(s.min()) for s in shown) if shown else 0.0
    # log.debug("Finds the slowest document of all")
    slowest = max(float(s.max()) for s in shown) if shown else 1.0
    # log.debug("Finds the furthest far-out fence of any run")
    fence = max(_fence(s) for s in shown) if shown else 1.0
    # log.debug("Ends the times shown at the slowest document or the fence")
    top = min(slowest, fence)
    # log.debug("Pads each end a little, never by less than the least padding")
    pad = max(MIN_PAD, (top - fastest) * PAD_SHARE)
    # log.debug("Returns the range: padded past the slowest, or cut at the fence")
    return [max(0.0, fastest - pad), top + pad if slowest <= fence else fence]


# log.debug("Defines a run's far-out fence")
def _fence(secs: pd.Series[float] | None = None) -> float:
    """Returns the upper quartile plus three middle-half spreads.

    Args:
        secs: One run's times, in seconds. Required.

    Returns:
        The far-out fence, in seconds.
    """
    # log.debug("Takes the times, which the caller must give")
    secs = required(secs=secs)
    # log.debug("Reads the upper quartile")
    upper = secs.quantile(UPPER_QUARTILE)
    # log.debug("Returns the fence")
    return float(upper + FENCE_SPREADS * (upper - secs.quantile(LOWER_QUARTILE)))


# log.debug("Defines one run's row of the time chart")
def _time_row(
    fig: go.Figure | None = None,
    rows: pd.DataFrame | None = None,
    secs: pd.Series[float] | None = None,
    edge: float | None = None,
    *,
    index: int | None = None,
    label: str | None = None,
    colours: Theme | None = None,
) -> str:
    """Draws one run's dots and box, noting documents past the axis.

    The box and its quartiles come from every document; dots past the
    axis are drawn clear rather than cut in half at its edge, since the
    note beside the row counts them.

    Args:
        fig: The chart to draw on. Required.
        rows: The run's rows of the documents table. Required.
        secs: The run's times in seconds. Required.
        edge: Where the time axis ends. Required.
        index: The run's place among those picked; 0 is in focus.
            Required.
        label: The run's name. Required.
        colours: The scheme to draw in. Required.

    Returns:
        The row's name: the run and its typical time.
    """
    # log.debug("Takes the figure, which the caller must give")
    fig = required(fig=fig)
    # log.debug("Takes the rows, which the caller must give")
    rows = required(rows=rows)
    # log.debug("Takes the times, which the caller must give")
    secs = required(secs=secs)
    # log.debug("Takes the axis's end, which the caller must give")
    edge = required(edge=edge)
    # log.debug("Takes the run's place, which the caller must give")
    index = required(index=index)
    # log.debug("Takes the label, which the caller must give")
    label = required(label=label)
    # log.debug("Takes the colours, which the caller must give")
    colours = required(colours=colours)
    # log.debug("Names the row with the run and its median time")
    row = f"{label}<br><b>{fixed(secs.median(), 1)} s</b> typical"
    # log.debug("Finds the documents slower than the axis shows")
    past = secs[secs > edge]
    # log.debug("Notes them beside the row, when there are any")
    if len(past):
        # log.debug("Adds the note in the right margin")
        fig.add_annotation(_slower_note(past, row, colours))
    # log.debug("Lists the documents the axis shows, when some are past it")
    inside = [i for i, v in enumerate(secs) if v <= edge] if len(past) else None
    # log.debug("Adds the run's dots and box")
    fig.add_trace(_time_box(rows, secs, row, inside, index=index, label=label, colours=colours))
    # log.debug("Returns the row's name")
    return row


# log.debug("Defines the note of documents slower than the axis shows")
def _slower_note(
    past: pd.Series[float] | None = None, row: str | None = None, colours: Theme | None = None
) -> go.layout.Annotation:
    """Returns the note of how many are slower, and the slowest time.

    It sits in the margin, so it never covers the dots or the axis.

    Args:
        past: The times past the end of the axis, in seconds.
            Required.
        row: The row's name, which the note sits beside. Required.
        colours: The scheme to draw in. Required.

    Returns:
        The note.
    """
    # log.debug("Takes the times past the axis, which the caller must give")
    past = required(past=past)
    # log.debug("Takes the row, which the caller must give")
    row = required(row=row)
    # log.debug("Takes the colours, which the caller must give")
    colours = required(colours=colours)
    # log.debug("Returns the note, anchored at its left edge just past the plot")
    return go.layout.Annotation(
        x=1,
        xref="paper",
        xanchor=LEFT,
        xshift=10,
        y=row,
        yref="y",
        showarrow=False,
        align=LEFT,
        text=f"{len(past)} slower,<br>up to {fixed(past.max(), 1)} s",
        font=dict(color=colours.ink2, size=TICK_SIZE),
        name="beyond",
    )


# log.debug("Defines one run's dots and box")
def _time_box(
    rows: pd.DataFrame | None = None,
    secs: pd.Series[float] | None = None,
    row: str | None = None,
    inside: list[int] | None = None,
    *,
    index: int | None = None,
    label: str | None = None,
    colours: Theme | None = None,
) -> go.Box:
    """Returns a run's times: every document as a dot, over the box.

    Args:
        rows: The run's rows of the documents table. Required.
        secs: The run's times in seconds. Required.
        row: The row's name. Required.
        inside: The dots to draw when some are past the axis; all when
            None.
        index: The run's place among those picked; 0 is in focus.
            Required.
        label: The run's name for the hover. Required.
        colours: The scheme to draw in. Required.

    Returns:
        The run's box, with a dot per document.
    """
    # log.debug("Takes the rows, which the caller must give")
    rows = required(rows=rows)
    # log.debug("Takes the times, which the caller must give")
    secs = required(secs=secs)
    # log.debug("Takes the row's name, which the caller must give")
    row = required(row=row)
    # log.debug("Takes the run's place, which the caller must give")
    index = required(index=index)
    # log.debug("Takes the label, which the caller must give")
    label = required(label=label)
    # log.debug("Takes the colours, which the caller must give")
    colours = required(colours=colours)
    # log.debug("Returns the box, its dots spread across the row")
    return go.Box(
        x=secs,
        y=[row] * len(rows),
        name=label,
        orientation="h",
        selectedpoints=inside,
        unselected=dict(marker=dict(opacity=0)),
        boxpoints="all",
        jitter=JITTER,
        pointpos=0,
        width=0.36,
        whiskerwidth=WHISKER_WIDTH,
        marker=dict(
            color=colours.runs[index],
            size=7,
            opacity=0.8,
            line=dict(color=colours.surface, width=1),
        ),
        line=dict(color=colours.runs[index], width=1.5),
        fillcolor=CLEAR,
        hovertemplate=hover("<b>%{x:.1f} s</b>  %{text}", label),
        text=rows[CASE_ID],
        meta=dict(role=f"run-{index}"),
    )


# log.debug("Defines one run's cost bar")
def _cost_bar(
    cost: float | None = None,
    *,
    index: int | None = None,
    label: str | None = None,
    colours: Theme | None = None,
) -> go.Bar:
    """Returns a run's bar, with its cost written at its end.

    Args:
        cost: The run's cost per document, in dollars. Required.
        index: The run's place among those picked; 0 is in focus.
            Required.
        label: The run's name. Required.
        colours: The scheme to draw in. Required.

    Returns:
        The bar, with its cost written at its end.
    """
    # log.debug("Takes the cost, which the caller must give")
    cost = required(cost=cost)
    # log.debug("Takes the run's place, which the caller must give")
    index = required(index=index)
    # log.debug("Takes the label, which the caller must give")
    label = required(label=label)
    # log.debug("Takes the colours, which the caller must give")
    colours = required(colours=colours)
    # log.debug("Returns the bar")
    return go.Bar(
        x=[cost],
        y=[label],
        name=label,
        orientation="h",
        width=0.34,
        marker=dict(color=colours.runs[index], line=dict(width=0), cornerradius=4),
        text=[dollars(cost)],
        textposition="outside",
        textfont=dict(color=colours.ink2, size=FONT_SIZE),
        cliponaxis=False,
        hovertemplate=hover("<b>$%{x:.4f}</b> per document", label),
        meta=dict(role=f"run-{index}"),
    )
