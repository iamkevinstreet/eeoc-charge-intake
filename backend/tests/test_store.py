########################################################################
#                                                                      #
#                     backend/tests/test_store.py                      #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-08
Last modified on:  2026-11-08

Tests where reviews and exports are kept: every export matches its
contract, the memory store records it, a folder gets a copy, and in
Postgres a review survives a restart, a later decision replaces an
earlier one, the migrations apply once, and no export can be changed.

The Postgres tests run against REVIEWS_TEST_DATABASE_URL, a database
they empty first; CI starts one. Without it they are skipped.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import json
import os
from collections.abc import Iterator
from importlib import resources
from pathlib import Path
from typing import Any, Final

# Third-party
import psycopg
import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from kds.args import required
from kds.logs import get_logger
from pydantic import SecretStr

# Local
from eeoc_intake.api.store import PostgresReviewStore, migrate
from eeoc_intake.config import AppSettings
from support import started

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
# log.debug("Sets the API's prefix")
API: Final = "/api/v1"
# log.debug("Sets the sample every test reviews")
SAMPLE: Final = "charge-000"
# log.debug("Takes the test database's address, when there is one")
DATABASE: Final = os.environ.get("REVIEWS_TEST_DATABASE_URL", "")
# log.debug("Skips a test that needs Postgres when there is none")
NEEDS_POSTGRES: Final = pytest.mark.skipif(not DATABASE, reason="no REVIEWS_TEST_DATABASE_URL")
# log.debug("Reads the export contract that ships in the package")
CONTRACT: Final = Draft202012Validator(
    json.loads(
        resources.files("eeoc_intake").joinpath("contracts/review_export_v1.json").read_text()
    ),
    format_checker=Draft202012Validator.FORMAT_CHECKER,
)


########################################################################
#                                                                      #
#                          Review store tests                          #
#                                                                      #
########################################################################
# log.debug("Defines one review taken to its export")
def _export(client: TestClient | None = None, edit: str | None = None) -> dict[str, Any]:
    """Extracts the sample, decides every field and exports it.

    Args:
        client: The started client. Required.
        edit: A field to edit to "Edited" instead of accepting.

    Returns:
        The export.
    """
    # log.debug("Takes the client, which the caller must give")
    client = required(client=client)
    # log.debug("Extracts the sample")
    review = client.post(f"{API}/extract/sample/{SAMPLE}").json()
    # log.debug("Names the review's routes")
    base = f"{API}/reviews/{review['review_id']}"
    # log.debug("Decides every field, editing the one named")
    for name in review["fields"]:
        # log.debug("Posts the decision")
        client.post(
            f"{base}/decisions",
            json={"field": name, "action": "accept"}
            if name != edit
            else {"field": name, "action": "edit", "value": "Edited"},
        )
    # log.debug("Returns the export")
    return dict(client.get(f"{base}/export").json())


# log.debug("Defines settings that keep reviews in the test database")
@pytest.fixture
def postgres(settings: AppSettings) -> Iterator[AppSettings]:
    """Empties the test database and yields settings that use it.

    Args:
        settings: Offline settings over the ten samples.

    Yields:
        The same settings, with the Postgres store.
    """
    # log.debug("Empties the database, so every test starts from no schema")
    with psycopg.connect(DATABASE, autocommit=True) as db:
        # log.debug("Drops and remakes the public schema")
        db.execute("drop schema public cascade; create schema public")
    # log.debug("Yields the settings with the Postgres store")
    yield settings.model_copy(
        update={"reviews_store": "postgres", "reviews_database_url": SecretStr(DATABASE)}
    )


# log.debug("Defines the test that an export keeps its contract")
def test_every_export_matches_its_contract_and_is_recorded(settings: AppSettings) -> None:
    """Version 1's fields, types and formats; the memory store keeps it.

    Args:
        settings: Offline settings over the ten samples.
    """
    # log.debug("Starts the app")
    with started(settings) as client:
        # log.debug("Exports a review with one field edited")
        export = _export(client, edit="respondent")
        # log.debug("Takes the app's store")
        store = client.app.state.services.reviews  # type: ignore[attr-defined]
        # log.debug("Reads the review back from it")
        review = store.get(export["review_id"])
    # log.debug("Checks the contract holds")
    assert list(CONTRACT.iter_errors(export)) == []
    # log.debug("Checks the edit, what the model read, and the record kept")
    assert (export["record"]["respondent"], export["decisions"]["respondent"]) == (
        "Edited",
        "edit",
    )
    # log.debug("Checks the model's own reading is beside it, and the store kept the export")
    assert (export["extracted"]["respondent"] != "Edited", review.exports == [export]) == (
        True,
        True,
    )


# log.debug("Defines the test that a folder gets a copy")
def test_an_export_is_copied_to_the_exports_folder(settings: AppSettings, tmp_path: Path) -> None:
    """One file per export, named by the review and the time.

    Args:
        settings: Offline settings over the ten samples.
        tmp_path: A folder of the test's own.
    """
    # log.debug("Points the exports at the folder")
    folder = tmp_path / "exports"
    # log.debug("Exports one review")
    with started(settings.model_copy(update={"exports_folder": str(folder)})) as client:
        # log.debug("Exports it")
        export = _export(client)
    # log.debug("Reads the one file written")
    (path,) = folder.iterdir()
    # log.debug("Checks it holds the export, under the review's id")
    assert (json.loads(path.read_text()), path.name.startswith(export["review_id"])) == (
        export,
        True,
    )


# log.debug("Defines the test that a review survives a restart")
@NEEDS_POSTGRES
def test_a_review_in_postgres_survives_a_restart(postgres: AppSettings) -> None:
    """A second app finds the review, its decisions and its export.

    Args:
        postgres: Settings that keep reviews in the test database.
    """
    # log.debug("Exports a review from one app")
    with started(postgres) as client:
        # log.debug("Exports it")
        export = _export(client, edit="respondent")
    # log.debug("Reads it from a second app")
    with started(postgres) as client:
        # log.debug("Fetches the review")
        again = client.get(f"{API}/reviews/{export['review_id']}").json()
    # log.debug("Checks the decision survived")
    assert again["decisions"]["respondent"]["value"] == "Edited"
    # log.debug("Counts the exports the database recorded")
    with psycopg.connect(DATABASE) as db:
        # log.debug("Reads the review's exports")
        rows = db.execute(
            "select contract, payload from exports where review_id = %s", (export["review_id"],)
        ).fetchall()
    # log.debug("Checks the one export is on record, with its contract")
    assert rows == [("eeoc-review-export/v1", export)]


# log.debug("Defines the test that a later decision replaces an earlier one")
@NEEDS_POSTGRES
def test_a_later_decision_replaces_the_earlier_one(postgres: AppSettings) -> None:
    """Deciding a field twice keeps one decision, the second.

    Args:
        postgres: Settings that keep reviews in the test database.
    """
    # log.debug("Starts the app")
    with started(postgres) as client:
        # log.debug("Extracts the sample")
        review = client.post(f"{API}/extract/sample/{SAMPLE}").json()
        # log.debug("Names the decisions route")
        url = f"{API}/reviews/{review['review_id']}/decisions"
        # log.debug("Accepts the respondent")
        client.post(url, json={"field": "respondent", "action": "accept"})
        # log.debug("Then rejects it")
        second = client.post(url, json={"field": "respondent", "action": "reject"}).json()
        # log.debug("Reads the review back")
        again = client.get(f"{API}/reviews/{review['review_id']}").json()
    # log.debug("Checks one decision counted, and it is the rejection")
    assert (second["decided"], again["decisions"]["respondent"]["action"]) == (1, "reject")


# log.debug("Defines the test that exports cannot be changed")
@NEEDS_POSTGRES
def test_the_database_refuses_to_change_or_delete_an_export(postgres: AppSettings) -> None:
    """The trigger refuses an update and a delete alike.

    Args:
        postgres: Settings that keep reviews in the test database.
    """
    # log.debug("Exports one review")
    with started(postgres) as client:
        # log.debug("Exports it")
        _export(client)
    # log.debug("Tries both changes")
    for change in ("update exports set contract = 'x'", "delete from exports"):
        # log.debug("Checks the database refuses it")
        with psycopg.connect(DATABASE) as db, pytest.raises(psycopg.errors.RaiseException):
            # log.debug("Runs the change")
            db.execute(change)


# log.debug("Defines the test that each migration applies once")
@NEEDS_POSTGRES
def test_each_migration_applies_once(postgres: AppSettings) -> None:
    """The first store applies 001; a second applies nothing.

    Args:
        postgres: Settings that keep reviews in the test database.
    """
    # log.debug("Opens a store, which migrates")
    PostgresReviewStore(DATABASE)
    # log.debug("Checks a second migration applies nothing")
    assert (migrate(DATABASE), postgres.reviews_store) == ([], "postgres")
