########################################################################
#                                                                      #
#                    warehouse/pipelines/reviews.py                    #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-10

The dlt source for review exports under contract v1: every file in
`[reviews] folder`, one export to a .json file as the review service
writes them, or one per line of a .jsonl file as the replay of the live
runs writes them.

Every export is checked against the contract before any row is made,
so a file the contract refuses fails the load instead of loading half a
review. An export is keyed by its review and its time, so loading the
same files again changes nothing, and a review exported again adds a
version beside the first. On Databricks, each load ends by putting the
column mask on the names (pipelines/masks.py).
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

# Third-party
import dlt
from dlt.extract.resource import DltResource
from jsonschema import Draft202012Validator
from kds.args import required
from kds.logs import get_logger, log_event
from kds.pipelines import load
from pydantic import BaseModel

# Local
from pipelines.config import SETTINGS, AppSettings
from pipelines.masks import mask_reviews
from pipelines.rows import DecisionRow, ExportRow, ValueRow

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the encoding every file is read in, from the config")
ENCODING: Final = SETTINGS.files_encoding

########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Sets the pipeline's name, which names its state under data/generated/dlt")
PIPELINE: Final = "reviews"
# log.debug("Names an export's review")
REVIEW_ID: Final = "review_id"
# log.debug("Names when an export was made")
EXPORTED_AT: Final = "exported_at"
# log.debug("Sets the suffix of a file holding one export per line")
LINES: Final = ".jsonl"
# log.debug("Lists the files the folder's exports may be in")
SUFFIXES: Final = (".json", LINES)
# log.debug("Names each table, its row model and its key")
TABLES: Final[dict[str, tuple[type[BaseModel], tuple[str, ...]]]] = {
    "exports": (ExportRow, ("export_id",)),
    "export_values": (ValueRow, ("export_id", "version", "field", "position")),
    "export_decisions": (DecisionRow, ("export_id", "field")),
}


########################################################################
#                                                                      #
#                            Review exports                            #
#                                                                      #
########################################################################
# log.debug("Defines the dlt source")
@dlt.source(name="reviews", max_table_nesting=0)
def reviews(
    settings: AppSettings | None = None, *, loaded_at: datetime | None = None
) -> list[DltResource]:
    """Returns the three tables, each merging on its key.

    Args:
        settings: The folder of exports and the contract. Required.
        loaded_at: When this load started. Required.

    Returns:
        The resources: exports, their values and their decisions.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Takes the load's time, which the caller must give")
    loaded_at = required(loaded_at=loaded_at)
    # log.debug("Reads and checks every export once, for all three tables")
    tables = rows_of(read_exports(settings.reviews_folder, settings.reviews_contract), loaded_at)
    # log.debug("Returns a resource per table")
    return [
        dlt.resource(
            tables[name],
            name=name,
            primary_key=key,
            write_disposition="merge",
            columns=model,
        )
        for name, (model, key) in TABLES.items()
    ]


# log.debug("Defines the load of the review exports")
def load_reviews(settings: AppSettings | None = None) -> None:
    """Loads every export in the folder, as `load reviews` runs it.

    On Databricks, then puts the column mask on the names it loaded.

    Args:
        settings: The folder, the contract and the warehouse. Required.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Loads the source, stamped with this load's time")
    load(
        settings,
        name=PIPELINE,
        dataset=settings.reviews_dataset,
        source=reviews(settings, loaded_at=datetime.now(UTC)),
    )
    # log.debug("Masks the names it loaded, where the warehouse has masks")
    mask_reviews(settings)


# log.debug("Defines the reading of every export in the folder")
def read_exports(
    folder: Path | None = None, contract: Path | None = None
) -> list[tuple[str, dict[str, Any]]]:
    """Returns every export with the file it came from, each checked.

    Args:
        folder: The folder of export files. Required.
        contract: The JSON Schema every export must meet. Required.

    Returns:
        Each export, in file and line order.

    Raises:
        ValueError: When an export does not meet the contract, naming
            its file and line.
    """
    # log.debug("Takes the folder, which the caller must give")
    folder = required(folder=folder)
    # log.debug("Takes the contract, which the caller must give")
    contract = required(contract=contract)
    # log.debug("Reads the contract")
    checker = Draft202012Validator(json.loads(contract.read_text(encoding=ENCODING)))
    # log.debug("Starts with no exports")
    found: list[tuple[str, dict[str, Any]]] = []
    # log.debug("Walks the folder's export files in name order")
    for path in sorted(p for p in folder.iterdir() if p.suffix in SUFFIXES):
        # log.debug("Reads the file's exports: its lines, or the one it holds")
        text = path.read_text(encoding=ENCODING)
        # log.debug("Splits a lines file, keeps a single export whole")
        chunks = [t for t in text.splitlines() if t.strip()] if path.suffix == LINES else [text]
        # log.debug("Checks and keeps each export")
        for line, chunk in enumerate(chunks, start=1):
            # log.debug("Parses the export")
            export = json.loads(chunk)
            # log.debug("Finds the first thing the contract refuses, if any")
            error = next(iter(checker.iter_errors(export)), None)
            # log.debug("Refuses an export the contract refuses")
            if error is not None:
                # log.debug("Raises, naming the file, the line and the error")
                raise ValueError(f"{path.name}:{line} breaks the contract: {error.message}")
            # log.debug("Keeps it")
            found.append((path.name, export))
    # log.debug("Logs what was read")
    log_event(log, "reviews.read", exports=len(found))
    # log.debug("Returns the exports")
    return found


# log.debug("Defines the rows of every export")
def rows_of(
    exports: list[tuple[str, dict[str, Any]]] | None = None, loaded_at: datetime | None = None
) -> dict[str, list[BaseModel]]:
    """Returns each table's rows for the exports.

    Args:
        exports: Each export with its file. Required.
        loaded_at: When this load started. Required.

    Returns:
        The rows of exports, export_values and export_decisions.
    """
    # log.debug("Takes the exports, which the caller must give")
    exports = required(exports=exports)
    # log.debug("Takes the load's time, which the caller must give")
    loaded_at = required(loaded_at=loaded_at)
    # log.debug("Starts each table empty")
    tables: dict[str, list[BaseModel]] = {name: [] for name in TABLES}
    # log.debug("Walks the exports")
    for file, export in exports:
        # log.debug("Names the export by its review and its time")
        key = {"export_id": export_id(export), REVIEW_ID: export[REVIEW_ID]}
        # log.debug("Adds the export's row")
        tables["exports"].append(
            ExportRow(
                **key,
                contract=export["contract"],
                source=export["source"],
                demo=export["demo"],
                started_at=export["started_at"],
                exported_at=export[EXPORTED_AT],
                response_due=export["response_due"],
                file=file,
                loaded_at=loaded_at,
            )
        )
        # log.debug("Adds every value of the record and of what the model read")
        tables["export_values"] += [
            ValueRow(
                **key, version=version, field=field, position=at, value=text, loaded_at=loaded_at
            )
            for version in ("record", "extracted")
            for field, value in export[version].items()
            for at, text in _items(value)
        ]
        # log.debug("Adds each field's decision, and whether the quote check emptied it")
        tables["export_decisions"] += [
            DecisionRow(
                **key,
                field=field,
                decision=decision,
                removed=field in export["removed"],
                loaded_at=loaded_at,
            )
            for field, decision in export["decisions"].items()
        ]
    # log.debug("Returns the tables")
    return tables


# log.debug("Defines an export's key")
def export_id(export: dict[str, Any] | None = None) -> str:
    """Returns the review's id and the export's time, as files name it.

    Args:
        export: The export. Required.

    Returns:
        The key, such as 0a1b2c3d4e-2026-11-08T052901+0000.
    """
    # log.debug("Takes the export, which the caller must give")
    export = required(export=export)
    # log.debug("Returns the key, safe in any file system")
    return f"{export[REVIEW_ID]}-{export[EXPORTED_AT].replace(':', '')}"


# log.debug("Defines the text of each item of a value")
def _items(value: Any = None) -> Iterator[tuple[int, str]]:
    """Yields each item of a value with its place, as text.

    Args:
        value: A field's value: text, a list of text, a yes or no, or
            None for an empty field.

    Yields:
        Each item's place and text; none for an empty field.
    """
    # log.debug("Reads the value by its kind")
    match value:
        case None:
            # log.debug("Yields nothing for an empty field")
            return
        case bool():
            # log.debug("Yields a yes or no as true or false")
            yield 0, str(value).lower()
        case list():
            # log.debug("Yields each item of a list with its place")
            yield from enumerate(str(item) for item in value)
        case _:
            # log.debug("Yields a single value")
            yield 0, str(value)
