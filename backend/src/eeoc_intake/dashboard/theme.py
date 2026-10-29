########################################################################
#              backend/src/eeoc_intake/dashboard/theme.py              #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Fonts, colours, labels and the chart layout,     #
#                     after the design of kevindstreet.com.            #
########################################################################
"""Fonts, colours, labels and the layout every chart shares.

The look follows the design system of kevindstreet.com (Geist, a
near-black or paper ground, one yellow highlight, green for right), in
light and dark, so the app and the case study read as one product.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final

import plotly.graph_objects as go
from kds.logs import get_logger

from eeoc_intake.evals.stats import fixed

# Module constants
log = get_logger(__name__)
# log.debug("Names the light scheme, the one the case study and the export use")
LIGHT: Final = "light"
# log.debug("Names the dark scheme")
DARK: Final = "dark"
# log.debug("Sets the font stack of kevindstreet.com")
FONT: Final = (
    "Geist, 'Geist Variable', ui-sans-serif, system-ui, 'Helvetica Neue', Arial, sans-serif"
)
# log.debug("Sets the size of chart text")
FONT_SIZE: Final = 12
# log.debug("Sets the size of value-axis ticks and small notes")
TICK_SIZE: Final = 11
# log.debug("Sets the margin every chart keeps at its edges, in pixels")
EDGE: Final = 8
# log.debug("Sets a colour that lets the card show through")
CLEAR: Final = "rgba(0,0,0,0)"
# log.debug("Sets the anchor that puts a note's left edge at its x")
LEFT: Final = "left"
# log.debug("Sets the most runs a chart draws: one per step of the run ramp")
MAX_RUNS: Final = 3
# log.debug("Sets the decimals a cost is written with")
COST_PLACES: Final = 4
# log.debug("Sets the milliseconds in a second")
MS_PER_SECOND: Final = 1000
# log.debug("Titles the accuracy chart by field")
BY_FIELD_TITLE: Final = "Fields right, by field"
# log.debug("Titles the accuracy chart by field and kind of document")
HEATMAP_TITLE: Final = "Fields right, by field and kind of document"
# log.debug("Titles the time chart")
LATENCY_TITLE: Final = "Seconds per document"
# log.debug("Titles the cost chart")
COST_TITLE: Final = "Cost per document, at list prices"
# log.debug("Names each scored field as the charts and tables show it")
FIELD_LABELS: Final = {
    "charge_number": "Charge number",
    "charging_party": "Charging party",
    "respondent": "Respondent",
    "eeoc_office": "EEOC office",
    "bases": "Bases",
    "issues": "Issues",
    "earliest_date": "Earliest date",
    "latest_date": "Latest date",
    "continuing_action": "Continuing action",
    "notice_date": "Notice date",
}
# log.debug("Names each kind of document as the charts and tables show it")
KIND_LABELS: Final = {
    "clean": "Clean",
    "missing_number": "Missing charge number",
    "rotated": "Rotated page",
    "long": "Long particulars",
    "two_respondents": "Two respondents",
}
# Column heads for the heatmap: short lines, so each fits under its
# cell even when the panels are narrow.
# log.debug("Sets the heatmap's column head for each kind of document")
KIND_TICKS: Final = {
    "Clean": "Standard",
    "Missing charge number": "No charge<br>number",
    "Rotated page": "Rotated<br>page",
    "Long particulars": "Long<br>particulars",
    "Two respondents": "Two<br>respondents",
}


# log.debug("Defines the colours of one scheme")
@dataclass(frozen=True)
class Theme:
    """The colours the charts use in one scheme, from kevindstreet.com.

    Runs are an ordered ramp: the run in focus in full ink, earlier
    runs in lighter steps of the same gray (monotone, visible steps,
    the light end clear of the surface). Accuracy is one hue, from the
    surface to the green the site uses for right.
    """

    # log.debug("Holds the card background")
    surface: str
    # log.debug("Holds the raised background, for hover labels and empty cells")
    surface2: str
    # log.debug("Holds the main text colour")
    ink: str
    # log.debug("Holds the secondary text colour")
    ink2: str
    # log.debug("Holds the faint text colour, for value-axis ticks")
    ink3: str
    # log.debug("Holds the grid line colour")
    grid: str
    # log.debug("Holds the rule colour, for borders and the lines joining dots")
    rule: str
    # log.debug("Holds the pale highlight behind fields that changed")
    mark_wash: str
    # log.debug("Holds the green for right")
    right: str
    # log.debug("Holds the run ramp, the run in focus first")
    runs: tuple[str, str, str]


# log.debug("Sets the two schemes by name")
THEMES: Final = {
    LIGHT: Theme(
        surface="#ffffff",
        surface2="#ecece8",
        ink="#111214",
        ink2="#585d66",
        ink3="#868c96",
        grid="rgba(17,18,20,0.08)",
        rule="rgba(17,18,20,0.20)",
        mark_wash="rgba(255,228,92,0.42)",
        right="#13794a",
        runs=("#111214", "#80868f", "#a7acb4"),
    ),
    DARK: Theme(
        surface="#121419",
        surface2="#1a1d24",
        ink="#f2f3f5",
        ink2="#9aa1ac",
        ink3="#6e7581",
        grid="rgba(255,255,255,0.07)",
        rule="rgba(255,255,255,0.22)",
        mark_wash="rgba(243,207,74,0.14)",
        right="#5dd39e",
        runs=("#f2f3f5", "#7d8490", "#4a505b"),
    ),
}


# log.debug("Defines the layout every chart shares")
def shared_layout(fig: go.Figure, height: int, colours: Theme) -> go.Figure:
    """Return the figure in the shared fonts, margins, axes and hover.

    Args:
        fig: The chart, with its traces and its own axis settings.
        height: The chart's height in pixels.
        colours: The scheme to draw in.

    Returns:
        The same figure, restyled.
    """
    # log.debug("Sets the font, margins, clear backgrounds, the hidden legend and the hover")
    fig.update_layout(
        template="none",
        height=height,
        margin=dict(l=EDGE, r=12, t=EDGE, b=EDGE),
        font=dict(family=FONT, size=FONT_SIZE, color=colours.ink2),
        paper_bgcolor=CLEAR,
        plot_bgcolor=CLEAR,
        showlegend=False,
        legend=dict(
            orientation="h",
            x=0,
            xanchor=LEFT,
            y=1.0,
            yanchor="bottom",
            font=dict(color=colours.ink2, size=FONT_SIZE),
            bgcolor=CLEAR,
            itemclick="toggleothers",
        ),
        hoverlabel=dict(
            bgcolor=colours.surface2,
            bordercolor=colours.rule,
            font=dict(family=FONT, color=colours.ink, size=FONT_SIZE),
        ),
        hovermode="closest",
    )
    # log.debug("Gives the value axis a faint grid and no line or ticks")
    fig.update_xaxes(
        automargin=True,
        showgrid=True,
        gridcolor=colours.grid,
        gridwidth=1,
        zeroline=False,
        showline=False,
        ticks="",
        tickfont=dict(color=colours.ink3, size=TICK_SIZE),
    )
    # log.debug("Gives the category axis no grid, line or ticks, and room beside its labels")
    fig.update_yaxes(
        automargin=True,
        showgrid=False,
        zeroline=False,
        showline=False,
        ticks="",
        ticklabelstandoff=10,
        tickfont=dict(color=colours.ink2, size=FONT_SIZE),
    )
    # log.debug("Returns the figure")
    return fig


# log.debug("Defines the axis settings that list categories from the top down")
def top_down(categories: Sequence[str]) -> dict[str, Any]:
    """Return axis settings that list categories in order, top first.

    The order is set here, not left to the order traces name them.
    """
    # log.debug("Returns the fixed order, reversed so the first is at the top")
    return dict(categoryorder="array", categoryarray=list(categories), autorange="reversed")


# log.debug("Defines a hover template that names the run")
def hover(text: str, label: str) -> str:
    """Return a hover template: the text, and the run's label."""
    # log.debug("Returns the template with the label as its trace name")
    return f"{text}<extra>{label}</extra>"


# log.debug("Defines how a cost is written")
def dollars(value: float) -> str:
    """Return a cost in dollars, to four decimals."""
    # log.debug("Returns the dollar sign and the rounded cost")
    return f"${fixed(value, COST_PLACES)}"
