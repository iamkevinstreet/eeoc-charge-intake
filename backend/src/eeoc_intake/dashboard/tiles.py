########################################################################
#              backend/src/eeoc_intake/dashboard/tiles.py              #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Builds the headline tiles: each measure for the run in focus, and
whether it moved beyond noise. A change that rounds to nothing at the
precision shown is no change. Given the per-document rows, a change
gets a direction and a colour only when it is bigger than run-to-run
noise. The six tiles are judged together (Holm), so when nothing
changed, the chance of even one false arrow is at most 5%; a change
that does not clear its threshold is no clear change. The tests are in
evals/stats.py.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Final, Literal, TypedDict

# Third-party
import pandas as pd
from kds.args import required
from kds.logs import get_logger

# Local
from eeoc_intake.config import SETTINGS
from eeoc_intake.dashboard.theme import dollars
from eeoc_intake.evals.shares import fixed, pct_label
from eeoc_intake.evals.stats import holm, p_value

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the run id column, from the config")
RUN_ID: Final = SETTINGS.columns_run_id
# log.debug("Takes the column of each document's time, from the config")
LATENCY_MS: Final = SETTINGS.columns_latency_ms
# log.debug("Takes the runs table's cost per document column, from the config")
COST_PER_CASE: Final = SETTINGS.columns_cost_per_case
# log.debug("Takes the milliseconds in a second, from the config")
MS_PER_SECOND: Final = SETTINGS.units_ms_per_second
# log.debug("Takes the name of the rank test, used for time, from the config")
RANK: Final = SETTINGS.stats_rank_test
# log.debug("Takes the name of Welch's t-test, used for averages, from the config")
WELCH: Final = SETTINGS.stats_welch_test

########################################################################
#                           Local constants                            #
########################################################################
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


########################################################################
#                            Headline tiles                            #
########################################################################
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
def _all_or_tenths(share: float | None = None) -> str:
    """Returns a share to one decimal, all right as a whole 100%.

    Args:
        share: The share right, from 0 to 1. Required.

    Returns:
        The share as a percent: 100% when all were right, else to one
        decimal.
    """
    # log.debug("Takes the share, which the caller must give")
    share = required(share=share)
    # log.debug("Returns a hundred percent when all were right, else one decimal")
    return "100%" if share >= 1 else pct_label(share, 1)


# log.debug("Defines how a change in a share is written")
def _points(size: float | None = None) -> str:
    """Returns the size of a change in a share, in percentage points.

    Args:
        size: The size of the change in a share, from 0 to 1.
            Required.

    Returns:
        The change in percentage points, to one decimal.
    """
    # log.debug("Takes the size, which the caller must give")
    size = required(size=size)
    # log.debug("Returns the points, to one decimal")
    return f"{fixed(size * POINTS, 1)} pts"


# log.debug("Defines how a count per document is written")
def _hundredths(count: float | None = None) -> str:
    """Returns a count per document to two decimals.

    Args:
        count: The count per document. Required.

    Returns:
        The count to two decimals.
    """
    # log.debug("Takes the count, which the caller must give")
    count = required(count=count)
    # log.debug("Returns the count to two places")
    return fixed(count, 2)


# log.debug("Defines how a time in milliseconds is written")
def _seconds(ms: float | None = None) -> str:
    """Returns a time in milliseconds as seconds, to one decimal.

    Args:
        ms: The time, in milliseconds. Required.

    Returns:
        The time in seconds, to one decimal.
    """
    # log.debug("Takes the time, which the caller must give")
    ms = required(ms=ms)
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


# log.debug("Defines the tiles for the runs picked")
def tile_rows(
    runs_df: pd.DataFrame | None = None,
    run_ids: Sequence[str] | None = None,
    cases_df: pd.DataFrame | None = None,
) -> list[TileRow]:
    """Returns each measure for the run in focus, and how it moved.

    It moved against the second run picked. Without the documents
    table, every change that survives rounding gets its arrow.

    Args:
        runs_df: The runs table from `frames`. Required.
        run_ids: The runs picked, the run in focus first. Required.
        cases_df: The documents table, to judge changes against noise.

    Returns:
        A row per tile, in the order shown; none when no run is picked.
    """
    # log.debug("Takes the runs table, which the caller must give")
    runs_df = required(runs_df=runs_df)
    # log.debug("Takes the run ids, which the caller must give")
    run_ids = required(run_ids=run_ids)
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
def _judged(
    cases_df: pd.DataFrame | None = None, run_ids: Sequence[str] | None = None
) -> dict[str, bool]:
    """Returns, per tile, whether its change is bigger than noise.

    The six tests are judged together, with Holm's correction.

    Args:
        cases_df: The documents table from `frames`. Required.
        run_ids: The runs picked, the run in focus first. Required.

    Returns:
        Each tile's column mapped to whether its change holds up.
    """
    # log.debug("Takes the documents table, which the caller must give")
    cases_df = required(cases_df=cases_df)
    # log.debug("Takes the run ids, which the caller must give")
    run_ids = required(run_ids=run_ids)
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
def _per_document(
    cases_df: pd.DataFrame | None = None, run_id: str | None = None, column: str | None = None
) -> list[float]:
    """Returns the run's values in the column, missing ones left out.

    Args:
        cases_df: The documents table from `frames`. Required.
        run_id: The run whose values to read. Required.
        column: The per-document column to read. Required.

    Returns:
        The run's values, as floats.
    """
    # log.debug("Takes the documents table, which the caller must give")
    cases_df = required(cases_df=cases_df)
    # log.debug("Takes the run id, which the caller must give")
    run_id = required(run_id=run_id)
    # log.debug("Takes the column, which the caller must give")
    column = required(column=column)
    # log.debug("Returns the run's values as floats")
    return cases_df.loc[cases_df[RUN_ID] == run_id, column].dropna().astype(float).tolist()


# log.debug("Defines one tile's row")
def _row(
    tile: Tile | None = None,
    now: pd.Series[Any] | None = None,
    then: pd.Series[Any] | None = None,
    called: dict[str, bool] | None = None,
) -> TileRow:
    """Returns the tile for the run in focus, with its change if any.

    Args:
        tile: The tile. Required.
        now: The run in focus's row of the runs table. Required.
        then: The second run's row, to compare with; None when only
            one run is picked.
        called: Each tile's column mapped to whether its change holds
            up; empty when changes are not judged. Required.

    Returns:
        The tile's row, as the page shows it.
    """
    # log.debug("Takes the tile, which the caller must give")
    tile = required(tile=tile)
    # log.debug("Takes the run in focus, which the caller must give")
    now = required(now=now)
    # log.debug("Takes the tests' calls, which the caller must give")
    called = required(called=called)
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
def _change(
    tile: Tile | None = None, diff: float | None = None, called: dict[str, bool] | None = None
) -> tuple[str, bool | None]:
    """Returns the change as written, and whether it is for the better.

    A change that rounds to nothing, or one the tests did not call, has
    no direction and is neither good nor bad.

    Args:
        tile: The tile. Required.
        diff: The run in focus's value less the earlier run's.
            Required.
        called: Each tile's column mapped to whether its change holds
            up. Required.

    Returns:
        The change as written, and True for the better, False for the
        worse, or None for no change or no clear change.
    """
    # log.debug("Takes the tile, which the caller must give")
    tile = required(tile=tile)
    # log.debug("Takes the difference, which the caller must give")
    diff = required(diff=diff)
    # log.debug("Takes the tests' calls, which the caller must give")
    called = required(called=called)
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
