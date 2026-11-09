########################################################################
#                                                                      #
#                      warehouse/tests/support.py                      #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

What the tests share: the repository's root, settings that keep a
test's warehouse, dlt's state and its logs in a folder of its own, a
workbook laid out as the EEOC lays out Table E1a, and a stand-in for
its download.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any, Final

# Third-party
from kds.args import required
from kds.logs import get_logger
from openpyxl import Workbook

# Local
from pipelines.config import AppSettings

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
# log.debug("Sets the repository's root, where config/ and dbt/ are")
REPO: Final = Path(__file__).resolve().parents[1]
# log.debug("Sets the folder of committed exports: the live runs replayed")
EXPORTS: Final = REPO.parent / "data" / "reviews"
# log.debug("Sets the fields every finished review decides")
FIELDS: Final = 11
# log.debug("Lays out Table E1a: FY 2023 to 2025's totals as published, the rest made up")
TABLE_E1A: Final[list[list[Any]]] = [
    ["Charge Receipts by Basis or Statute (All Statutes)"],
    [],
    [None, "FY 2021", "FY 2022", "FY 2023", "FY 2024", "FY 2025"],
    ["Total Charges", 60000, 70000, 81055, 88531, 88201],
    ["Race", 20000, 21000, 27505, 29199, 28000],
    [None, 0.333, 0.3, 0.339, 0.33, 0.317],
    ["Sex*", "18,000", "19,000", "23,962", "25,000", "24,500"],
    ["National Origin", 6000, 7000, 8000, 8500, 8300],
    ["Religion", 2000, 13000, 3000, 3200, 3100],
    ["Color", 3000, 3500, 4000, 4100, 4050],
    ["Retaliation - All Statutes", 34000, 38000, 46000, 50000, 49000],
    ["Retaliation - Title VII Only", 24000, 27000, 32000, 34000, 33500],
    ["Age", 12000, 14000, 16000, 17000, 16800],
    ["Disability", 22000, 25000, 29000, 32000, 31500],
    ["Equal Pay Act", 800, 850, 900, 950, 920],
    ["Genetic Information", 240, 410, 276, 300, 290],
    [],
    ["Note: charges can cite more than one basis, so bases sum past the total."],
]


########################################################################
#                                                                      #
#                             Test helpers                             #
#                                                                      #
########################################################################
# log.debug("Defines settings that keep a test's files in its own folder")
def settings_in(folder: Path | None = None) -> AppSettings:
    """Returns settings with the warehouse, state and logs in folder.

    Args:
        folder: A temporary folder. Required.

    Returns:
        The settings, everything else as configured.
    """
    # log.debug("Takes the folder, which the caller must give")
    folder = required(folder=folder)
    # log.debug("Returns the settings")
    return AppSettings(
        warehouse_path=folder / "warehouse.duckdb",
        warehouse_state=folder / "dlt",
        log_dir=folder / "logs",
    )


# log.debug("Defines a workbook's bytes for a layout")
def workbook(rows: list[list[Any]] | None = None) -> bytes:
    """Returns an XLSX file holding the rows on its first sheet.

    Args:
        rows: The sheet's rows. Required.

    Returns:
        The file's bytes.
    """
    # log.debug("Takes the rows, which the caller must give")
    rows = required(rows=rows)
    # log.debug("Makes a workbook")
    book = Workbook()
    # log.debug("Writes each row")
    for row in rows:
        # log.debug("Appends the row")
        book.active.append(row)  # type: ignore[union-attr]
    # log.debug("Saves it to memory")
    buffer = BytesIO()
    # log.debug("Writes the file")
    book.save(buffer)
    # log.debug("Returns its bytes")
    return buffer.getvalue()


# log.debug("Defines the stand-in for the table's download")
class Download:
    """Answers the download with a workbook, as the EEOC's site does."""

    # log.debug("Defines the constructor")
    def __init__(self, content: bytes | None = None) -> None:
        """Keeps the workbook to answer with.

        Args:
            content: The XLSX file's bytes. Required.
        """
        # log.debug("Takes the file, which the caller must give")
        self.content = required(content=content)

    # log.debug("Defines the status check, which a good answer passes")
    def raise_for_status(self) -> None:
        """Passes: the stand-in always answers with the file."""

    # log.debug("Defines the request, which returns this answer whatever is asked")
    def get(self, *args: Any, **kwargs: Any) -> Download:
        """Returns this answer.

        Args:
            *args: The request's address, ignored.
            **kwargs: The request's options, ignored.

        Returns:
            This answer.
        """
        # log.debug("Returns the answer")
        return self


# log.debug("Defines the committed exports, counted from their files")
def committed_exports() -> list[dict[str, Any]]:
    """Returns every export the committed files hold, in file order.

    Returns:
        Each export, parsed.
    """
    # log.debug("Returns each line of each file, parsed")
    return [
        json.loads(line)
        for path in sorted(EXPORTS.glob("*.jsonl"))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
