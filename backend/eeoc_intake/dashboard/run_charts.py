########################################################################
#             backend/eeoc_intake/dashboard/run_charts.py              #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Draws the two charts with a row per run: seconds #
#                     per document and cost per document.              #
########################################################################
"""The charts with a row per run: seconds and cost per document."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

import pandas as pd
import plotly.graph_objects as go
from kds.logs import get_logger

from eeoc_intake.dashboard.data import (
    CASE_ID,
    COST_PER_CASE,
    LATENCY_MS,
    RUN_ID,
    long_labels,
    present,
)
from eeoc_intake.dashboard.theme import (
    CLEAR,
    FONT_SIZE,
    LEFT,
    LIGHT,
    MS_PER_SECOND,
    THEMES,
    TICK_SIZE,
    Theme,
    dollars,
    hover,
    shared_layout,
    top_down,
)
from eeoc_intake.evals.stats import fixed

# Module constants
log = get_logger(__name__)
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


# log.debug("Defines the time chart")
def fig_latency(
    cases: pd.DataFrame,
    run_ids: str | Sequence[str],
    theme: str = LIGHT,
    labels: dict[str, str] | None = None,
) -> go.Figure:
    """Return each document's time as a dot over its run's box.

    The box spans the middle half of the times, and each row names its
    run's typical (median) time. Documents past the end of the axis are
    counted beside their row instead.

    Args:
        cases: The documents table from `frames`.
        run_ids: Up to three runs, the run in focus first.
        theme: The colour scheme, light or dark.
        labels: Each run's name; long labels when None.

    Returns:
        The chart.
    """
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
    runs_df: pd.DataFrame,
    run_ids: str | Sequence[str],
    theme: str = LIGHT,
    labels: dict[str, str] | None = None,
) -> go.Figure:
    """Return the cost per document at list prices, a bar per run.

    Each bar carries its cost at its end.

    Args:
        runs_df: The runs table from `frames`.
        run_ids: Up to three runs, the run in focus first.
        theme: The colour scheme, light or dark.
        labels: Each run's name; long labels when None.

    Returns:
        The chart.
    """
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
def _time_axis(secs: list[pd.Series[float]]) -> list[float]:
    """Return the time axis's range, fitted to where documents fall.

    Times have a long right tail, so the axis stops at the far-out fence
    (the upper quartile plus three times the spread of the middle half)
    of the most spread-out run, and documents past it are noted beside
    their row rather than stretched across the chart. It never starts
    below zero.
    """
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
def _fence(secs: pd.Series[float]) -> float:
    """Return the upper quartile plus three middle-half spreads."""
    # log.debug("Reads the upper quartile")
    upper = secs.quantile(UPPER_QUARTILE)
    # log.debug("Returns the fence")
    return float(upper + FENCE_SPREADS * (upper - secs.quantile(LOWER_QUARTILE)))


# log.debug("Defines one run's row of the time chart")
def _time_row(
    fig: go.Figure,
    rows: pd.DataFrame,
    secs: pd.Series[float],
    edge: float,
    *,
    index: int,
    label: str,
    colours: Theme,
) -> str:
    """Draw one run's dots and box, noting documents past the axis.

    The box and its quartiles come from every document; dots past the
    axis are drawn clear rather than cut in half at its edge, since the
    note beside the row counts them.

    Args:
        fig: The chart to draw on.
        rows: The run's rows of the documents table.
        secs: The run's times in seconds.
        edge: Where the time axis ends.
        index: The run's place among those picked; 0 is in focus.
        label: The run's name.
        colours: The scheme to draw in.

    Returns:
        The row's name: the run and its typical time.
    """
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
def _slower_note(past: pd.Series[float], row: str, colours: Theme) -> go.layout.Annotation:
    """Return the note of how many are slower, and the slowest time.

    It sits in the margin, so it never covers the dots or the axis.
    """
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
    rows: pd.DataFrame,
    secs: pd.Series[float],
    row: str,
    inside: list[int] | None,
    *,
    index: int,
    label: str,
    colours: Theme,
) -> go.Box:
    """Return a run's times: every document as a dot, over the box.

    Args:
        rows: The run's rows of the documents table.
        secs: The run's times in seconds.
        row: The row's name.
        inside: The dots to draw when some are past the axis; all when
            None.
        index: The run's place among those picked; 0 is in focus.
        label: The run's name for the hover.
        colours: The scheme to draw in.
    """
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
def _cost_bar(cost: float, *, index: int, label: str, colours: Theme) -> go.Bar:
    """Return a run's bar, with its cost written at its end."""
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
