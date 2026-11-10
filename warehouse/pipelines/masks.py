########################################################################
#                                                                      #
#                     warehouse/pipelines/masks.py                     #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-10
Last modified on:  2026-11-10

The column mask on the raw review values, put on after every load into
Databricks. A value of a field that names a person, the charging
party's, shows to every reader as its initial and a fingerprint of its
text in lower case and trimmed, such as "J. 3f9a0c2b71de", unless the
reader belongs to `[reviews] personal_readers`, a group no one is in.

The mask binds the table's owner too, and the build: dbt reads the
masked value and needs no more, since the fingerprint tells two people
apart and the initial is all the marts keep. So no query returns a
name, and the name never leaves the raw table. DuckDB has no masks;
there the build reads the name and the marts still hold a key and an
initial only.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

from typing import Final

# Third-party
import dlt
from kds.args import required
from kds.logs import get_logger, log_event
from kds.pipelines import DUCKDB, destination

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
# log.debug("Names dlt's switch for its usage reports, which stay off")
TELEMETRY: Final = "runtime.dlthub_telemetry"
# log.debug("Names the mask's function, kept beside the table it masks")
FUNCTION: Final = "mask_personal"
# log.debug("Names the masked table: every value of every export")
TABLE: Final = "export_values"
# log.debug("Sets how many hex digits of the SHA-256 the fingerprint keeps")
FINGERPRINT: Final = 12
# log.debug("Sets the function: a personal field's value, its initial and fingerprint")
MASK: Final = """\
CREATE OR REPLACE FUNCTION {function}(value STRING, field STRING)
RETURNS STRING
COMMENT 'The mask on {table}.value: a personal field shows its initial and a fingerprint.'
RETURN CASE
    WHEN field IN ({fields}) AND NOT is_account_group_member('{readers}')
        THEN concat(
            upper(substring(trim(value), 1, 1)),
            '. ',
            substring(sha2(lower(trim(value)), 256), 1, {fingerprint})
        )
    ELSE value
END"""
# log.debug("Sets the statement that puts the mask on the values")
SET_MASK: Final = (
    "ALTER TABLE {table} ALTER COLUMN value SET MASK {function} USING COLUMNS (field)"
)


########################################################################
#                                                                      #
#                             Column masks                             #
#                                                                      #
########################################################################
# log.debug("Defines the statements that make the mask and put it on")
def mask_statements(
    settings: AppSettings | None = None, dataset: str | None = None, table: str | None = None
) -> list[str]:
    """Returns the SQL that makes the mask's function and sets it.

    Args:
        settings: The personal fields and the group that may read
            them. Required.
        dataset: The dataset's qualified name, as the destination
            quotes it. Required.
        table: The values table's qualified name. Required.

    Returns:
        The function's statement, then the table's.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Takes the dataset, which the caller must give")
    dataset = required(dataset=dataset)
    # log.debug("Takes the table, which the caller must give")
    table = required(table=table)
    # log.debug("Names the function inside the dataset")
    function = f"{dataset}.{FUNCTION}"
    # log.debug("Quotes each personal field, as the settings check allows no quote in one")
    fields = ", ".join(f"'{f}'" for f in settings.reviews_personal_fields)
    # log.debug("Fills the function's statement")
    make = MASK.format(
        function=function,
        table=TABLE,
        fields=fields,
        readers=settings.reviews_personal_readers,
        fingerprint=FINGERPRINT,
    )
    # log.debug("Returns it, then the statement that sets it")
    return [make, SET_MASK.format(table=table, function=function)]


# log.debug("Defines the mask's setting after a load")
def mask_reviews(settings: AppSettings | None = None) -> bool:
    """Puts the column mask on the review values in Databricks.

    Runs after every load, since a first load makes the table; both
    statements are safe to run again. DuckDB has no masks, so a load
    there puts none.

    Args:
        settings: The warehouse, the dataset and the personal fields.
            Required.

    Returns:
        Whether a mask was put on.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Skips DuckDB, which has no masks")
    if settings.warehouse_destination == DUCKDB:
        # log.debug("Says so")
        return False
    # log.debug("Turns dlt's usage reports off before the pipeline exists")
    dlt.config[TELEMETRY] = False
    # log.debug("Opens the destination as the loads see it")
    pipeline = dlt.pipeline(
        pipeline_name="masks",
        destination=destination(settings),
        dataset_name=settings.reviews_dataset,
        pipelines_dir=str(settings.warehouse_state),
    )
    # log.debug("Runs both statements in one session")
    with pipeline.sql_client() as client:
        # log.debug("Builds them with the destination's own quoting")
        statements = mask_statements(
            settings,
            dataset=client.fully_qualified_dataset_name(),
            table=client.make_qualified_table_name(TABLE),
        )
        # log.debug("Runs each")
        for statement in statements:
            # log.debug("Runs it")
            client.execute_sql(statement)
    # log.debug("Logs the mask")
    log_event(log, "masks.set", table=TABLE, fields=len(settings.reviews_personal_fields))
    # log.debug("Says so")
    return True
