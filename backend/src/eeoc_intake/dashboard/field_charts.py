########################################################################
#          backend/src/eeoc_intake/dashboard/field_charts.py           #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Draws the accuracy chart by field: a dot per run on each field, the
fields the runs disagree on highlighted and their dots joined. The
fields are listed in the order the record lists them, which the chart
by field and kind shares. The runs' key sits above all the charts on
the page, so no chart carries one of its own.
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
from eeoc_intake.core.schema import SCORED_FIELDS
from eeoc_intake.dashboard.theme import THEMES, Theme, hover, shared_layout, top_down
from eeoc_intake.dashboard.views import long_labels, present
from eeoc_intake.evals.shares import pct_label

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the run id column, from the config")
RUN_ID: Final = SETTINGS.columns_run_id
# log.debug("Takes the field column, from the config")
FIELD: Final = SETTINGS.columns_field
# log.debug("Takes the column that is 1 when a field is right, from the config")
CORRECT: Final = SETTINGS.columns_correct
# log.debug("Takes the name of each field, from the config")
FIELD_LABELS: Final = SETTINGS.labels_fields
# log.debug("Takes the light scheme's name, from the config")
LIGHT: Final = SETTINGS.charts_light_scheme
# log.debug("Takes the size of chart text, from the config")
FONT_SIZE: Final = SETTINGS.charts_font_size
# log.debug("Takes the tick format of a share: a whole percent, from the config")
PERCENT_TICKS: Final = SETTINGS.charts_percent_ticks

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the smallest spread between runs that counts as a change")
NOISE: Final = 0.001
# log.debug("Sets half the height of a changed field's highlight, in rows")
HALF_BAND: Final = 0.42
# log.debug("Sets the ticks of the by-field chart's share axis")
QUARTERS: Final = (0, 0.25, 0.5, 0.75, 1)
# log.debug("Sets the height of the by-field chart above its rows")
DOTS_BASE: Final = 48
# log.debug("Sets the height of each field's row in the by-field chart")
DOTS_ROW: Final = 30


########################################################################
#                          Accuracy by field                           #
########################################################################
# log.debug("Defines the accuracy chart by field")
def fig_accuracy_by_field(
    fields: pd.DataFrame | None = None,
    run_ids: str | Sequence[str] | None = None,
    theme: str = LIGHT,
    labels: dict[str, str] | None = None,
) -> go.Figure:
    """Returns a dot per run on each field, joined where runs disagree.

    Fields that changed get the highlight, and their dots their share.

    Args:
        fields: The fields table from `frames`. Required.
        run_ids: Up to three runs, the run in focus first. Required.
        theme: The colour scheme, light or dark.
        labels: Each run's name for the hover; long labels when None.

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
    # log.debug("Names each run, from the labels given or the table")
    names = labels or long_labels(fields, ids)
    # log.debug("Computes each run's share right on each field")
    shares = fields[fields[RUN_ID].isin(ids)].groupby([RUN_ID, FIELD])[CORRECT].mean()
    # log.debug("Lists the fields the table holds, in record order")
    order = field_order(fields)
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


# log.debug("Defines the order fields are listed in")
def field_order(fields: pd.DataFrame | None = None) -> list[str]:
    """Returns the labels of the fields held, in record order.

    Args:
        fields: The fields table from `frames`. Required.

    Returns:
        The names of the fields the table holds, as the charts show
        them, in the order the record lists them.
    """
    # log.debug("Takes the fields, which the caller must give")
    fields = required(fields=fields)
    # log.debug("Lists the field labels the table holds")
    held = set(fields[FIELD])
    # log.debug("Returns them in the order the record lists its fields")
    return [FIELD_LABELS[f] for f in SCORED_FIELDS if FIELD_LABELS[f] in held]


# log.debug("Defines the marks on the fields the runs disagree on")
def _mark_changes(
    fig: go.Figure | None = None,
    shares: pd.Series[float] | None = None,
    ids: list[str] | None = None,
    order: list[str] | None = None,
    colours: Theme | None = None,
) -> list[str]:
    """Highlights each field the runs disagree on, and joins its dots.

    Args:
        fig: The chart to draw the marks on. Required.
        shares: Each run's share right on each field. Required.
        ids: The runs drawn, the run in focus first. Required.
        order: The fields, in the order they are listed. Required.
        colours: The scheme to draw in. Required.

    Returns:
        The fields that changed by more than noise.
    """
    # log.debug("Takes the figure, which the caller must give")
    fig = required(fig=fig)
    # log.debug("Takes the shares, which the caller must give")
    shares = required(shares=shares)
    # log.debug("Takes the run ids, which the caller must give")
    ids = required(ids=ids)
    # log.debug("Takes the field order, which the caller must give")
    order = required(order=order)
    # log.debug("Takes the colours, which the caller must give")
    colours = required(colours=colours)
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
    xs: list[float | None] | None = None,
    order: list[str] | None = None,
    changed: list[str] | None = None,
    *,
    index: int | None = None,
    label: str | None = None,
    colours: Theme | None = None,
) -> go.Scatter:
    """Returns one run's dots, its share written beside changed fields.

    Args:
        xs: The run's share on each field, None where it has none.
            Required.
        order: The fields, in the order they are listed. Required.
        changed: The fields the runs disagree on. Required.
        index: The run's place among those picked; 0 is in focus.
            Required.
        label: The run's name for the hover. Required.
        colours: The scheme to draw in. Required.

    Returns:
        The run's dots, with their hover.
    """
    # log.debug("Takes the shares, which the caller must give")
    xs = required(xs=xs)
    # log.debug("Takes the field order, which the caller must give")
    order = required(order=order)
    # log.debug("Takes the changed fields, which the caller must give")
    changed = required(changed=changed)
    # log.debug("Takes the run's place, which the caller must give")
    index = required(index=index)
    # log.debug("Takes the label, which the caller must give")
    label = required(label=label)
    # log.debug("Takes the colours, which the caller must give")
    colours = required(colours=colours)
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
