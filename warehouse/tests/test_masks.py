########################################################################
#                                                                      #
#                    warehouse/tests/test_masks.py                     #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-10
Last modified on:  2026-11-10

Tests the column mask without Databricks: its statements name every
personal field and the one group that may read them, and a setting
cannot break out of their quotes; the personal fields are dbt's; a load
into DuckDB puts no mask; and on Databricks both statements run, the
function first, in one session.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import json
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Final

# Third-party
import pytest
from kds.logs import get_logger
from pydantic import SecretStr, ValidationError

# Local
from pipelines import masks
from pipelines.config import AppSettings
from pipelines.masks import mask_reviews, mask_statements
from support import REPO, settings_in

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
# log.debug("Sets the dataset's name as Databricks quotes it")
DATASET: Final = "`kds`.`raw_reviews`"
# log.debug("Sets the values table's name as Databricks quotes it")
TABLE: Final = f"{DATASET}.`export_values`"


########################################################################
#                                                                      #
#                              Mask tests                              #
#                                                                      #
########################################################################
# log.debug("Defines a SQL client that keeps what it is asked to run")
class FakeClient:
    """Stands in for dlt's Databricks SQL client."""

    # log.debug("Defines the client's start")
    def __init__(self) -> None:
        """Starts with nothing run."""
        # log.debug("Starts the statements run")
        self.run: list[str] = []

    # log.debug("Defines the dataset's name")
    def fully_qualified_dataset_name(self) -> str:
        """Returns the dataset's quoted name.

        Returns:
            The name.
        """
        # log.debug("Returns it")
        return DATASET

    # log.debug("Defines a table's name")
    def make_qualified_table_name(self, table: str = "") -> str:
        """Returns the values table's quoted name.

        Args:
            table: The table's bare name.

        Returns:
            The name.
        """
        # log.debug("Returns it, checking it is the values table")
        return TABLE if table == masks.TABLE else table

    # log.debug("Defines a statement's run")
    def execute_sql(self, sql: str = "") -> None:
        """Keeps the statement.

        Args:
            sql: The statement.
        """
        # log.debug("Keeps it")
        self.run.append(sql)


# log.debug("Defines a pipeline whose SQL client is the fake")
class FakePipeline:
    """Stands in for the dlt pipeline the mask opens."""

    # log.debug("Defines the pipeline's start")
    def __init__(self) -> None:
        """Starts with a fresh client and no session opened."""
        # log.debug("Starts the client")
        self.client = FakeClient()
        # log.debug("Starts the count of sessions")
        self.sessions = 0

    # log.debug("Defines a session with the client")
    @contextmanager
    def sql_client(self) -> Iterator[FakeClient]:
        """Yields the client, counting the session.

        Yields:
            The client.
        """
        # log.debug("Counts the session")
        self.sessions += 1
        # log.debug("Yields the client")
        yield self.client


# log.debug("Defines the test that the mask names each personal field and its readers")
def test_the_mask_names_each_personal_field_and_the_group_that_may_read_them() -> None:
    """The function masks every personal field for all but one group."""
    # log.debug("Builds the statements")
    make, set_mask = mask_statements(AppSettings(), dataset=DATASET, table=TABLE)
    # log.debug("Checks the function's rule and the statement that sets it")
    assert (
        "WHEN field IN ('charging_party') "
        "AND NOT is_account_group_member('personal-data-readers')" in make,
        make.startswith(f"CREATE OR REPLACE FUNCTION {DATASET}.mask_personal(value STRING"),
        set_mask,
    ) == (
        True,
        True,
        f"ALTER TABLE {TABLE} ALTER COLUMN value SET MASK {DATASET}.mask_personal "
        "USING COLUMNS (field)",
    )


# log.debug("Defines the test that a setting cannot break out of the mask's quotes")
@pytest.mark.parametrize(
    "setting",
    [
        {"reviews_personal_fields": ["charging_party') OR ('a"]},
        {"reviews_personal_readers": "readers') OR true OR ('a"},
        {"reviews_personal_fields": []},
    ],
)
def test_a_setting_cannot_break_out_of_the_mask_s_quotes(setting: dict[str, Any]) -> None:
    """A field or group with a quote in it is refused, as is no field.

    Args:
        setting: The setting to try.
    """
    # log.debug("Checks the settings refuse it")
    with pytest.raises(ValidationError):
        # log.debug("Tries it")
        AppSettings(**setting)


# log.debug("Defines the test that the personal fields are dbt's")
def test_the_personal_fields_are_dbt_s() -> None:
    """The settings and dbt's personal_fields variable name the same."""
    # log.debug("Reads dbt's project file")
    text = (REPO / "dbt" / "dbt_project.yml").read_text(encoding="utf-8")
    # log.debug("Finds the variable's list, written as JSON is")
    found = re.search(r"^\s*personal_fields:\s*(\[.*\])\s*$", text, re.MULTILINE)
    # log.debug("Reads the settings' fields")
    fields = AppSettings().reviews_personal_fields
    # log.debug("Checks the variable names them")
    assert found is not None and json.loads(found.group(1)) == fields


# log.debug("Defines the test that a DuckDB load puts no mask")
def test_a_load_into_duckdb_puts_no_mask(tmp_path: Path) -> None:
    """DuckDB has no masks, so the mask is skipped.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Checks no mask is put on")
    assert mask_reviews(settings_in(tmp_path)) is False


# log.debug("Defines the test that a Databricks load runs both statements")
def test_a_load_into_databricks_runs_both_statements(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both statements run, the function first, in one session.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
        monkeypatch: pytest's way to stand in for dlt's pipeline.
    """
    # log.debug("Makes the fake pipeline")
    pipeline = FakePipeline()
    # log.debug("Stands it in for dlt's pipeline")
    monkeypatch.setattr("dlt.pipeline", lambda **_: pipeline)
    # log.debug("Stands in for the destination, which would check the connection")
    monkeypatch.setattr(masks, "destination", lambda _: None)
    # log.debug("Sets up Databricks as the destination, with a made-up connection")
    settings = settings_in(tmp_path).model_copy(
        update={
            "warehouse_destination": "databricks",
            "databricks_host": "example.cloud.databricks.com",
            "databricks_http_path": "/sql/1.0/warehouses/example",
            "databricks_token": SecretStr("not-a-token"),
        }
    )
    # log.debug("Puts the mask on")
    masked = mask_reviews(settings)
    # log.debug("Checks one session ran the function, then the mask")
    assert (masked, pipeline.sessions, [s.split()[0] for s in pipeline.client.run]) == (
        True,
        1,
        ["CREATE", "ALTER"],
    )
