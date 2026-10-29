########################################################################
#                backend/src/eeoc_intake/evals/index.py                #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Writes index.json, which lists the committed results so a static site
never lists a folder.

    python -m eeoc_intake.evals.index

The case study fetches files by name from the repository, so it needs
a list: the run files and the figures in `[data] results`, and each
folder of saved extractions in `[data] extractions`.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

# Third-party
from kds.args import required
from kds.logs import get_logger

# Local
from eeoc_intake.config import SETTINGS, get_app_settings

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the name of the figures file the dashboard exports, from the config")
FIGURES: Final = SETTINGS.data_figures
# log.debug("Takes the encoding the index is written in, from the config")
ENCODING: Final = SETTINGS.files_encoding

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the name of the index file")
INDEX: Final = "index.json"
# log.debug("Names the list of run files")
RUNS: Final = "runs"
# log.debug("Names the map of saved-extraction folders")
EXTRACTIONS: Final = "extractions"
# log.debug("Sets the pattern of a JSON file")
JSON_FILES: Final = "*.json"


########################################################################
#                            Results index                             #
########################################################################
# log.debug("Defines the index of a results folder and an extractions folder")
def build_index(results: Path | None = None, extractions: Path | None = None) -> dict[str, Any]:
    """Returns the run files, the saved extractions and the figures.

    Args:
        results: The folder of run files, the index and the figures.
            Required.
        extractions: The folder of saved-extraction folders. Required.

    Returns:
        The run files' names, each saved-extraction folder with its
        files, and the figures file's name, or None before it exists.
    """
    # log.debug("Takes the results folder, which the caller must give")
    results = required(results=results)
    # log.debug("Takes the extractions folder, which the caller must give")
    extractions = required(extractions=extractions)
    # log.debug("Lists the run files, leaving out the index and the figures")
    runs = sorted(p.name for p in results.glob(JSON_FILES) if p.name not in (INDEX, FIGURES))
    # log.debug("Lists each saved-extraction folder's files")
    saved = {
        folder.name: sorted(p.name for p in folder.glob(JSON_FILES))
        for folder in sorted(extractions.glob("*"))
        if folder.is_dir()
    }
    # log.debug("Returns the index, naming the figures only when they exist")
    return {
        RUNS: runs,
        EXTRACTIONS: saved,
        "figures": FIGURES if (results / FIGURES).exists() else None,
    }


# log.debug("Defines the command line")
def main() -> None:
    """Writes `[data] results`/index.json and says what it lists."""
    # log.debug("Reads the settings")
    settings = get_app_settings()
    # log.debug("Builds the index")
    index = build_index(settings.data_results, settings.data_extractions)
    # log.debug("Names the index file")
    path = settings.data_results / INDEX
    # log.debug("Writes it, with a final newline")
    path.write_text(json.dumps(index, indent=2) + "\n", encoding=ENCODING)
    # log.debug("Says what it lists")
    print(f"wrote {path}: {len(index[RUNS])} runs, {len(index[EXTRACTIONS])} folders")


# log.debug("Runs the command when the module is run as a script")
if __name__ == "__main__":
    # log.debug("Calls main")
    main()
