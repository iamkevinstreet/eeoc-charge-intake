########################################################################
#                                                                      #
#                   warehouse/pipelines/receipts.py                    #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

The dlt source for the EEOC's published charge statistics: Table E1a,
charge receipts by basis or statute, FY 1997 to FY 2025, an XLSX file.

The sheet is read by its shape, not by fixed cells: the header is the
first row naming at least five fiscal years, each later row with a
label is one basis, a row without a label (a basis's shares of all
charges) is passed over, and the table ends at its notes or at the
first blank row after it. A count printed as text ("29,199") is read
as a number; a share is never a count. The file's SHA-256 goes on
every row, so a revised table shows up as a new hash.

Restored from ai-operations at 8c6b715, where it began: the national
statistics belong beside the charges they put in context.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from io import BytesIO
from typing import Any, Final

# Third-party
import dlt
from dlt.extract.resource import DltResource
from dlt.sources.helpers import requests
from kds.args import required
from kds.logs import get_logger, log_event
from kds.pipelines import load
from openpyxl import load_workbook

# Local
from pipelines.config import AppSettings
from pipelines.rows import ReceiptRow

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
# log.debug("Sets the EEOC's name for the table")
TABLE: Final = "E1a"
# log.debug("Sets the column that names the table on every row")
TABLE_ID: Final = "table_id"
# log.debug("Sets how many fiscal years make a row the header")
MIN_YEARS: Final = 5
# log.debug("Sets how far down the sheet the header may start")
HEADER_ROWS: Final = 20
# log.debug("Sets the span of years a fiscal-year header can name")
YEARS: Final = range(1990, 2100)
# log.debug("Sets the pattern of a fiscal-year heading, such as FY 2025")
FISCAL_YEAR: Final = re.compile(r"FY\s*(\d{4})", re.IGNORECASE)
# log.debug("Sets the pattern of a count printed as text, such as 29,199")
COUNT_TEXT: Final = re.compile(r"\d{1,3}(,\d{3})*|\d+")
# log.debug("Sets the pattern of a label that starts the table's notes")
NOTES: Final = re.compile(r"(note|source)s?\b", re.IGNORECASE)
# log.debug("Sets the footnote marks a label may end with")
MARKS: Final = "*0123456789¹²³ "
# log.debug("Sets the client name the download is sent under")
AGENT: Final = {"User-Agent": "eeoc-charge-intake"}
# log.debug("Sets the pipeline's name, which names its state under data/generated/dlt")
PIPELINE: Final = "receipts"


########################################################################
#                                                                      #
#                          National receipts                           #
#                                                                      #
########################################################################
# log.debug("Defines the dlt source")
@dlt.source(name="receipts", max_table_nesting=0)
def receipts(
    settings: AppSettings | None = None, *, loaded_at: datetime | None = None
) -> list[DltResource]:
    """Returns the receipts table, merging on basis and fiscal year.

    Args:
        settings: The file's address and how long to wait. Required.
        loaded_at: When this load started. Required.

    Returns:
        The one resource.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Takes the load's time, which the caller must give")
    loaded_at = required(loaded_at=loaded_at)
    # log.debug("Returns the resource")
    return [
        dlt.resource(
            _download(settings, loaded_at),
            name="charge_receipts",
            primary_key=(TABLE_ID, "basis", "fiscal_year"),
            write_disposition="merge",
            columns=ReceiptRow,
        )
    ]


# log.debug("Defines the load of the receipts table")
def load_receipts(settings: AppSettings | None = None) -> None:
    """Loads the EEOC's receipts table, as `load receipts` runs it.

    Args:
        settings: The table's address and the warehouse. Required.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Loads the source, stamped with this load's time")
    load(
        settings,
        name=PIPELINE,
        dataset=settings.receipts_dataset,
        source=receipts(settings, loaded_at=datetime.now(UTC)),
    )


# log.debug("Defines the download and its rows")
def _download(
    settings: AppSettings | None = None, loaded_at: datetime | None = None
) -> Iterator[ReceiptRow]:
    """Downloads the file and yields its rows.

    Args:
        settings: The file's address and how long to wait. Required.
        loaded_at: When this load started. Required.

    Yields:
        One row per basis per fiscal year.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Takes the load's time, which the caller must give")
    loaded_at = required(loaded_at=loaded_at)
    # log.debug("Downloads the file, with dlt's retries")
    response = requests.get(
        settings.receipts_url, headers=AGENT, timeout=settings.receipts_timeout_s
    )
    # log.debug("Raises for any status but success")
    response.raise_for_status()
    # log.debug("Yields its rows")
    yield from parse_receipts(
        response.content, source_url=settings.receipts_url, loaded_at=loaded_at
    )


# log.debug("Defines the rows of the workbook")
def parse_receipts(
    content: bytes | None = None,
    *,
    source_url: str | None = None,
    loaded_at: datetime | None = None,
) -> list[ReceiptRow]:
    """Returns one row per basis per fiscal year of the first sheet.

    Args:
        content: The XLSX file's bytes. Required.
        source_url: Where the file came from. Required.
        loaded_at: When this load started. Required.

    Returns:
        The rows, in the sheet's order.

    Raises:
        ValueError: When no row names enough fiscal years to be the
            header, or the table under it has no counts.
    """
    # log.debug("Takes the file, which the caller must give")
    content = required(content=content)
    # log.debug("Takes the address, which the caller must give")
    source_url = required(source_url=source_url)
    # log.debug("Takes the load's time, which the caller must give")
    loaded_at = required(loaded_at=loaded_at)
    # log.debug("Reads the first sheet's values, not its formulas")
    sheet = load_workbook(BytesIO(content), read_only=True, data_only=True).worksheets[0]
    # log.debug("Takes every row as a tuple of values")
    rows = [tuple(row) for row in sheet.iter_rows(values_only=True)]
    # log.debug("Finds the header and the column of each fiscal year")
    at, years = _header(rows)
    # log.debug("Names the parts every row shares")
    part: dict[str, Any] = {
        TABLE_ID: TABLE,
        "source_url": source_url,
        "source_sha256": hashlib.sha256(content).hexdigest(),
        "loaded_at": loaded_at,
    }
    # log.debug("Reads every basis under the header")
    found = [
        ReceiptRow(**part, basis=basis, fiscal_year=year, receipts=count)
        for basis, cells in _bases(rows[at + 1 :], first=min(years))
        for column, year in years.items()
        if (count := _count(cells[column] if column < len(cells) else None)) is not None
    ]
    # log.debug("Refuses a table with no counts, which means the sheet changed shape")
    if not found:
        # log.debug("Raises the empty table's error")
        raise ValueError("no counts under the fiscal-year header")
    # log.debug("Logs what was read")
    log_event(log, "receipts.read", rows=len(found), years=len(years))
    # log.debug("Returns the rows")
    return found


# log.debug("Defines where the header is and which column is which year")
def _header(rows: Sequence[tuple[Any, ...]] | None = None) -> tuple[int, dict[int, int]]:
    """Returns the header's row index and each fiscal year's column.

    Args:
        rows: The sheet's rows. Required.

    Returns:
        The header's index, and each column's fiscal year.

    Raises:
        ValueError: When no row near the top names enough years.
    """
    # log.debug("Takes the rows, which the caller must give")
    rows = required(rows=rows)
    # log.debug("Walks the rows near the top")
    for at, row in enumerate(rows[:HEADER_ROWS]):
        # log.debug("Reads the fiscal year each cell names, if any")
        years = {column: year for column, cell in enumerate(row) if (year := _year(cell))}
        # log.debug("Returns the first row that names enough of them")
        if len(years) >= MIN_YEARS:
            # log.debug("Returns the header")
            return at, years
    # log.debug("Raises when no row did")
    raise ValueError("no row names five fiscal years")


# log.debug("Defines the fiscal year a header cell names")
def _year(cell: Any = None) -> int | None:
    """Returns 2025 for "FY 2025", "FY2025" or 2025; None otherwise.

    Args:
        cell: A header cell's value.

    Returns:
        The year, or None.
    """
    # log.debug("Reads the year from a heading or a number")
    match cell:
        case str() if found := FISCAL_YEAR.fullmatch(cell.strip()):
            # log.debug("Takes the year a heading names")
            year = int(found.group(1))
        case int() if not isinstance(cell, bool):
            # log.debug("Takes a number as the year")
            year = cell
        case _:
            # log.debug("Returns None for anything else")
            return None
    # log.debug("Returns the year when it is a plausible one")
    return year if year in YEARS else None


# log.debug("Defines the labelled rows of the table under the header")
def _bases(
    rows: Sequence[tuple[Any, ...]] | None = None, *, first: int | None = None
) -> Iterator[tuple[str, tuple[Any, ...]]]:
    """Yields each basis's label and row, until the notes or a gap.

    Args:
        rows: The rows under the header. Required.
        first: The column of the first fiscal year; labels sit before
            it. Required.

    Yields:
        Each basis's label, without footnote marks, and its row.
    """
    # log.debug("Takes the rows, which the caller must give")
    rows = required(rows=rows)
    # log.debug("Takes the first year's column, which the caller must give")
    first = required(first=first)
    # log.debug("Counts the bases seen, to tell a gap after the table from one before")
    seen = 0
    # log.debug("Walks the rows")
    for row in rows:
        # log.debug("Takes the row's label: its first text before the years")
        label = next((c.strip() for c in row[:first] if isinstance(c, str) and c.strip()), None)
        # log.debug("Stops at the notes")
        if label and NOTES.match(label):
            # log.debug("Ends the table")
            return
        # log.debug("Stops at a blank row after the table, skips one before it")
        if all(c is None or (isinstance(c, str) and not c.strip()) for c in row):
            # log.debug("Ends the table, or keeps looking for its start")
            if seen:
                # log.debug("Ends the table")
                return
            # log.debug("Moves to the next row")
            continue
        # log.debug("Yields a labelled row; a row of shares has no label")
        if label:
            # log.debug("Counts the basis")
            seen += 1
            # log.debug("Yields it without its footnote marks")
            yield label.rstrip(MARKS), row


# log.debug("Defines the count a cell holds")
def _count(cell: Any = None) -> int | None:
    """Returns the whole number a cell holds; None for a share or blank.

    Args:
        cell: A cell's value.

    Returns:
        The count, or None.
    """
    # log.debug("Reads a count from a number or from text")
    match cell:
        case bool() | None:
            # log.debug("Returns None for a truth value or a blank")
            return None
        case int():
            # log.debug("Returns a whole number as it is")
            return cell
        case float() if cell.is_integer() and cell >= 1:
            # log.debug("Returns a whole float as a whole number")
            return int(cell)
        case str() if COUNT_TEXT.fullmatch(cell.strip()):
            # log.debug("Returns a count printed as text, without its commas")
            return int(cell.strip().replace(",", ""))
        case _:
            # log.debug("Returns None for a share or anything else")
            return None
