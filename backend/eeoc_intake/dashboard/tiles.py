########################################################################
#                backend/eeoc_intake/dashboard/tiles.py                #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           The headline tiles: each measure for the run in  #
#                     focus, and whether it moved beyond noise.        #
########################################################################
"""The headline tiles: each measure for the run in focus, and its move.

A change that rounds to nothing at the precision shown is no change.
Given the per-document rows, a change gets a direction and a colour
only when it is bigger than run-to-run noise. The six tiles are judged
together (Holm), so when nothing changed, the chance of even one false
arrow is at most 5%; a change that does not clear its threshold is no
clear change. The tests are in evals/stats.py.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Final, Literal, TypedDict

import pandas as pd
from kds.logs import get_logger

from eeoc_intake.dashboard.data import COST_PER_CASE, LATENCY_MS, RUN_ID
from eeoc_intake.dashboard.theme import MS_PER_SECOND, dollars
from eeoc_intake.evals.stats import RANK, WELCH, fixed, holm, p_value, pct_label

# Module constants
log = get_logger(__name__)
# log.debug("Names a rise")
UP: Final = "up"
# log.debug("Names a fall")
DOWN: Final = "down"
# log.debug("Sets the words for a change that rounds to nothing")
NO_CHANGE: Final = "no change"
# log.debug("Sets the words for a change within run-to-run noise")
NO_CLEAR_CHANGE: Final = "no clear change"
# log.debug("Lists the digits that show a change survived rounding")
NONZERO_DIGITS: Final = "123456789"
# log.debug("Sets the smallest difference that is not zero")
TINY: Final = 1e-12
# log.debug("Sets the percentage points in a share of one")
POINTS: Final = 100


# log.debug("Defines one headline measure")
@dataclass(frozen=True)
class Tile:
    """One headline measure, in the words the case study uses.

    Attributes:
        column: The runs table column it shows.
        label: What the tile calls it.
        value: How its value is written.
        better: Which way is better, up or down.
        change: How the size of a change is written; like the value
            when None.
    """

    # log.debug("Holds the runs table column")
    column: str
    # log.debug("Holds the tile's label")
    label: str
    # log.debug("Holds how the value is written")
    value: Callable[[float], str]
    # log.debug("Holds which way is better")
    better: Literal["up", "down"]
    # log.debug("Holds how the size of a change is written, when not like the value")
    change: Callable[[float], str] | None = None


# log.debug("Defines one tile as the page shows it")
class TileRow(TypedDict):
    """One tile: its measure, label, value, change and tone.

    The change is None when no second run is picked; good is None when
    there is no change, or no clear one.
    """

    # log.debug("Holds the runs table column")
    measure: str
    # log.debug("Holds the label")
    label: str
    # log.debug("Holds the value as written")
    value: str
    # log.debug("Holds the change as written, with its direction")
    delta: str | None
    # log.debug("Holds whether the change is for the better")
    good: bool | None


# log.debug("Defines how fields right is written")
def _all_or_tenths(share: float) -> str:
    """Return a share to one decimal, all right as a whole 100%."""
    # log.debug("Returns a hundred percent when all were right, else one decimal")
    return "100%" if share >= 1 else pct_label(share, 1)


# log.debug("Defines how a change in a share is written")
def _points(size: float) -> str:
    """Return the size of a change in a share, in percentage points."""
    # log.debug("Returns the points, to one decimal")
    return f"{fixed(size * POINTS, 1)} pts"


# log.debug("Defines how a count per document is written")
def _hundredths(count: float) -> str:
    """Return a count per document to two decimals."""
    # log.debug("Returns the count to two places")
    return fixed(count, 2)


# log.debug("Defines how a time in milliseconds is written")
def _seconds(ms: float) -> str:
    """Return a time in milliseconds as seconds, to one decimal."""
    # log.debug("Returns the seconds")
    return f"{fixed(ms / MS_PER_SECOND, 1)} s"


# Plain-language measures, in the words the case study uses: the
# column, its label, how to write it, which way is better, and how to
# write a change when not like the value.
# log.debug("Lists the six tiles in the order they are shown")
TILES: Final = (
    Tile("field_accuracy", "Fields right", _all_or_tenths, UP, _points),
    Tile("unsupported_rate", "Quotes that did not match the page", pct_label, DOWN, _points),
    Tile("guesses", "Made-up values per document", _hundredths, DOWN),
    Tile("false_abstentions", "Fields wrongly left blank, per document", _hundredths, DOWN),
    Tile("latency_p50_ms", "Seconds per document, typical", _seconds, DOWN),
    Tile(COST_PER_CASE, "Cost per document", dollars, DOWN),
)
# Each tile's per-document values, and the test that says whether two
# runs really differ: the rank test for time, Welch's for averages.
# log.debug("Maps each tile to its per-document column and its test")
TILE_TESTS: Final = {
    "field_accuracy": ("field_accuracy", WELCH),
    "unsupported_rate": ("unsupported_removed", WELCH),
    "guesses": ("guesses", WELCH),
    "false_abstentions": ("false_abstentions", WELCH),
    "latency_p50_ms": (LATENCY_MS, RANK),
    COST_PER_CASE: ("cost_usd", WELCH),
}


# log.debug("Defines the tiles for the runs picked")
def tile_rows(
    runs_df: pd.DataFrame, run_ids: Sequence[str], cases_df: pd.DataFrame | None = None
) -> list[TileRow]:
    """Return each measure for the run in focus, and how it moved.

    It moved against the second run picked. Without the documents
    table, every change that survives rounding gets its arrow.

    Args:
        runs_df: The runs table from `frames`.
        run_ids: The runs picked, the run in focus first.
        cases_df: The documents table, to judge changes against noise.

    Returns:
        A row per tile, in the order shown; none when no run is picked.
    """
    # log.debug("Shows no tiles when no run is picked")
    if not run_ids:
        # log.debug("Returns no rows")
        return []
    # log.debug("Takes the run in focus")
    now = runs_df[runs_df[RUN_ID] == run_ids[0]].iloc[0]
    # log.debug("Takes the run to compare with, when a second is picked")
    then = runs_df[runs_df[RUN_ID] == run_ids[1]].iloc[0] if len(run_ids) > 1 else None
    # log.debug("Judges every change against noise when there is a run and documents")
    called = _judged(cases_df, run_ids) if then is not None and cases_df is not None else {}
    # log.debug("Returns a row per tile")
    return [_row(tile, now, then, called) for tile in TILES]


# log.debug("Defines the judgement of the six changes together")
def _judged(cases_df: pd.DataFrame, run_ids: Sequence[str]) -> dict[str, bool]:
    """Return, per tile, whether its change is bigger than noise.

    The six tests are judged together, with Holm's correction.
    """
    # log.debug("Tests each tile's per-document values, the earlier run first")
    p_values = {
        column: p_value(
            _per_document(cases_df, run_ids[1], per_document),
            _per_document(cases_df, run_ids[0], per_document),
            test,
        )
        for column, (per_document, test) in TILE_TESTS.items()
    }
    # log.debug("Returns which changes hold up when judged together")
    return dict(zip(p_values, holm(list(p_values.values())), strict=True))


# log.debug("Defines one run's values in one per-document column")
def _per_document(cases_df: pd.DataFrame, run_id: str, column: str) -> list[float]:
    """Return the run's values in the column, missing ones left out."""
    # log.debug("Returns the run's values as floats")
    return cases_df.loc[cases_df[RUN_ID] == run_id, column].dropna().astype(float).tolist()


# log.debug("Defines one tile's row")
def _row(
    tile: Tile, now: pd.Series[Any], then: pd.Series[Any] | None, called: dict[str, bool]
) -> TileRow:
    """Return the tile for the run in focus, with its change if any."""
    # log.debug("Reads the value, a missing one as zero")
    value = float(now[tile.column] or 0)
    # log.debug("Reads the earlier run's value, when there is one, a missing one as zero")
    before = None if then is None else float(then[tile.column] or 0)
    # log.debug("Writes the change against it")
    delta, good = (None, None) if before is None else _change(tile, value - before, called)
    # log.debug("Returns the row")
    return TileRow(
        measure=tile.column, label=tile.label, value=tile.value(value), delta=delta, good=good
    )


# log.debug("Defines how a change is written and judged")
def _change(tile: Tile, diff: float, called: dict[str, bool]) -> tuple[str, bool | None]:
    """Return the change as written, and whether it is for the better.

    A change that rounds to nothing, or one the tests did not call, has
    no direction and is neither good nor bad.
    """
    # log.debug("Writes the size of the change as the tile writes it")
    shown = (tile.change or tile.value)(abs(diff))
    # log.debug("Calls a change that rounds to nothing no change")
    if abs(diff) < TINY or not any(digit in NONZERO_DIGITS for digit in shown):
        # log.debug("Returns no change")
        return NO_CHANGE, None
    # log.debug("Calls a change the tests did not clear no clear change")
    if not called.get(tile.column, True):
        # log.debug("Returns no clear change")
        return NO_CLEAR_CHANGE, None
    # log.debug("Returns the direction and size, and whether that is for the better")
    return f"{UP if diff > 0 else DOWN} {shown}", (diff > 0) == (tile.better == UP)
