########################################################################
#                                                                      #
#                   warehouse/tests/test_receipts.py                   #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

Tests the reading of the EEOC's receipts table by its shape, on a
workbook these tests build in the layout the EEOC uses: title rows, a
header of fiscal years, a count row per basis with its shares in the
row under it, counts printed as text, footnote marks, then notes. The
real file is read by the warehouse job in CI, not here, where the
build checks its totals against the ones the EEOC published.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Final

# Third-party
import pytest
from kds.logs import get_logger

# Local
from pipelines.receipts import parse_receipts
from support import workbook

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = get_logger(__name__)

########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Sets the time every test's load is stamped with")
AT: Final = datetime(2026, 11, 8, tzinfo=UTC)
# log.debug("Sets the address the rows are said to come from")
URL: Final = "https://example.org/receipts.xlsx"
# log.debug("Lays out a sheet the EEOC's way, with made-up counts")
SHEET: Final[list[list[Any]]] = [
    ["Charge Receipts by Basis or Statute (All Statutes)"],
    [],
    [None, "FY 2021", "FY 2022", "FY 2023", "FY 2024", "FY 2025"],
    ["Total Charges", 61331, 73485, 81055, 88531, 88201],
    ["Race", 20908, 20992, 27505, 29199, 30000],
    [None, 0.341, 0.286, 0.339, 0.33, 0.333],
    ["Sex*", "18,762", "19,805", "23,962", "25,000", "26,000"],
    [None, "30.6%", "27.0%", "29.6%", "28.2%", "28.9%"],
    ["Genetic Information", 242, 410, 276, None, 300],
    [],
    ["Note: charges can cite more than one basis, so bases sum past the total."],
]


########################################################################
#                                                                      #
#                           EEOC table tests                           #
#                                                                      #
########################################################################
# log.debug("Defines the test of the table's counts")
def test_each_basis_gives_one_count_per_year_and_shares_are_passed_over() -> None:
    """Counts as numbers or text load; shares and blanks do not."""
    # log.debug("Parses the sheet")
    rows = parse_receipts(workbook(SHEET), source_url=URL, loaded_at=AT)
    # log.debug("Indexes the counts by basis and year")
    counts = {(r.basis, r.fiscal_year): r.receipts for r in rows}
    # log.debug("Checks a count, a text count and the footnote mark dropped")
    assert (counts[("Race", 2024)], counts[("Sex", 2022)]) == (29199, 19805)
    # log.debug("Checks the blank cell gave no row and the notes no basis")
    assert (("Genetic Information", 2024) not in counts, len(rows)) == (True, 4 * 5 - 1)


# log.debug("Defines the test that every row names its source")
def test_every_row_carries_the_files_hash() -> None:
    """A revised file shows up as a new hash on its rows."""
    # log.debug("Parses the sheet")
    rows = parse_receipts(workbook(SHEET), source_url=URL, loaded_at=AT)
    # log.debug("Checks one hash and one address across every row")
    assert {(r.source_url, len(r.source_sha256), r.table_id) for r in rows} == {(URL, 64, "E1a")}


# log.debug("Defines the test that a changed layout is refused")
def test_a_sheet_without_a_fiscal_year_header_is_refused() -> None:
    """Reading nothing would load an empty table and call it current."""
    # log.debug("Checks a sheet with no year header fails")
    with pytest.raises(ValueError, match="fiscal years"):
        # log.debug("Parses a sheet of labels only")
        parse_receipts(workbook([["Race", 1, 2], ["Sex", 3, 4]]), source_url=URL, loaded_at=AT)
