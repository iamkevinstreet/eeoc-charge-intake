########################################################################
#               backend/src/eeoc_intake/evals/export.py                #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Exports the evaluation results as tidy CSV files for Tableau or any
other BI tool.

    python -m eeoc_intake.evals.export      # writes [data] export/*.csv

Three files, one row per run, per document, and per document and
field. They come from the same tables the dashboard draws, so the
numbers agree; data/README.md describes the sheets to build from them.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

from pathlib import Path
from typing import Final

# Third-party
from kds.args import required
from kds.logs import get_logger

# Local
from eeoc_intake.config import SETTINGS, get_app_settings
from eeoc_intake.dashboard.data import frames, load_runs

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the encoding the files are read in, from the config")
ENCODING: Final = SETTINGS.files_encoding

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Names the three files, in the order the tables come")
NAMES: Final = ("runs", "documents", "fields")


########################################################################
#                            Tableau export                            #
########################################################################
# log.debug("Defines the export")
def export(
    live: Path | None = None, smoke: Path | None = None, out: Path | None = None
) -> list[Path]:
    """Writes runs.csv, documents.csv and fields.csv into `out`.

    Live runs are exported when there are any; otherwise every run,
    the offline smoke runs included.

    Args:
        live: The folder of live results. Required.
        smoke: The folder of offline smoke results; None leaves smoke
            runs out.
        out: The folder to write the CSV files into. Required.

    Returns:
        The files written.
    """
    # log.debug("Takes the live results folder, which the caller must give")
    live = required(live=live)
    # log.debug("Takes the output folder, which the caller must give")
    out = required(out=out)
    # log.debug("Reads the live runs, or every run when there is none")
    runs = load_runs(live) or load_runs(live, smoke)
    # log.debug("Makes the folder")
    out.mkdir(parents=True, exist_ok=True)
    # log.debug("Starts the list of files written")
    written: list[Path] = []
    # log.debug("Writes each table as a CSV file without the index column")
    for name, table in zip(NAMES, frames(runs), strict=True):
        # log.debug("Names the file")
        path = out / f"{name}.csv"
        # log.debug("Writes the table")
        table.to_csv(path, index=False)
        # log.debug("Records it")
        written.append(path)
    # log.debug("Returns the files")
    return written


# log.debug("Defines the command line")
def main() -> None:
    """Exports the results and says how many rows each file has."""
    # log.debug("Reads the settings")
    settings = get_app_settings()
    # log.debug("Writes the three files")
    paths = export(settings.data_results, settings.data_smoke, settings.data_export)
    # log.debug("Says what each file holds")
    for path in paths:
        # log.debug("Counts the rows below the header")
        rows = len(path.read_text(encoding=ENCODING).splitlines()) - 1
        # log.debug("Prints the file and its rows")
        print(f"wrote {path} ({rows} rows)")


# log.debug("Runs the command when the module is run as a script")
if __name__ == "__main__":
    # log.debug("Calls main")
    main()
