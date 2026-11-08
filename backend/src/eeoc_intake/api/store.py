########################################################################
#                                                                      #
#                 backend/src/eeoc_intake/api/store.py                 #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-08
Last modified on:  2026-11-08

Keeps reviews in Postgres, so a review survives a restart and every
export is on record: `[reviews] store = "postgres"` with the database's
address in REVIEWS_DATABASE_URL. The in-memory store stays the default,
for the demo and the tests.

The schema is db/*.sql, applied once each, in order, and recorded in
schema_migrations. A review is one row holding its extraction as JSON;
each field's latest decision is a row of its own; each export is a row
the database will not let anyone change or delete.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

from importlib import resources
from typing import Any, Final

# Third-party
import psycopg
from kds.args import required
from kds.logs import get_logger, log_event
from psycopg.types.json import Jsonb

# Local
from eeoc_intake.api.review import Review, Store, stamp, start_review
from eeoc_intake.api.reviews import ReviewStore
from eeoc_intake.config import SETTINGS, AppSettings
from eeoc_intake.core.extract import Extraction
from eeoc_intake.core.guard import Flagged
from eeoc_intake.core.schema import FIELDS, ChargeRecord, Decision

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the name every export's contract goes by, from the config")
CONTRACT: Final = SETTINGS.exports_contract
# log.debug("Takes the text encoding of every file read, from the config")
ENCODING: Final = SETTINGS.files_encoding

########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Sets the store that keeps reviews in Postgres")
POSTGRES: Final = "postgres"
# log.debug("Sets the package folder that holds the migrations")
MIGRATIONS: Final = "db"
# log.debug("Sets the table that records the migrations applied")
APPLIED: Final = (
    "create table if not exists schema_migrations"
    " (version text primary key, applied_at timestamptz not null default now())"
)
# log.debug("Sets how a model is written to a JSON column")
AS_JSON: Final = "json"
# log.debug("Lists the extraction's fields that are models, rebuilt by name")
RECORDS: Final = ("record", "raw")
# log.debug("Sets the extraction's field of warnings")
WARNINGS: Final = "warnings"
# log.debug("Sets the lock that keeps two services from migrating at once")
LOCK: Final = "select pg_advisory_xact_lock(7302261)"


########################################################################
#                                                                      #
#                           Postgres reviews                           #
#                                                                      #
########################################################################
# log.debug("Defines the store the settings name")
def open_store(settings: AppSettings | None = None) -> Store:
    """Returns the Postgres store when the settings say so, else memory.

    Args:
        settings: The store's kind, its database and the memory limit.
            Required.

    Returns:
        The store the routes share.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Returns the in-memory store unless Postgres is named")
    if settings.reviews_store != POSTGRES:
        # log.debug("Returns the memory store")
        return ReviewStore(settings.api_max_reviews)
    # log.debug("Takes the database's address, which the settings checked is set")
    url = required(reviews_database_url=settings.reviews_database_url)
    # log.debug("Returns the Postgres store, migrated")
    return PostgresReviewStore(url.get_secret_value())


# log.debug("Defines the migrations, applied once each")
def migrate(url: str | None = None) -> list[str]:
    """Applies every migration not yet applied, in name order.

    Args:
        url: The database's address. Required.

    Returns:
        The migrations this call applied; none when all were.
    """
    # log.debug("Takes the address, which the caller must give")
    url = required(url=url)
    # log.debug("Lists the migration files in name order")
    files = sorted(
        (f for f in resources.files("eeoc_intake").joinpath(MIGRATIONS).iterdir()),
        key=lambda f: f.name,
    )
    # log.debug("Opens one transaction for the whole migration")
    with psycopg.connect(url) as db:
        # log.debug("Waits for any other service migrating the same database")
        db.execute(LOCK)
        # log.debug("Makes the record of migrations")
        db.execute(APPLIED)
        # log.debug("Reads which are applied")
        done = {row[0] for row in db.execute("select version from schema_migrations")}
        # log.debug("Lists the ones still to apply")
        todo = [f for f in files if f.name.endswith(".sql") and f.name not in done]
        # log.debug("Applies each and records it")
        for file in todo:
            # log.debug("Runs the file")
            db.execute(file.read_text(encoding=ENCODING))
            # log.debug("Records it")
            db.execute("insert into schema_migrations (version) values (%s)", (file.name,))
    # log.debug("Logs what was applied")
    log_event(log, "store.migrated", applied=[f.name for f in todo])
    # log.debug("Returns their names")
    return [f.name for f in todo]


# log.debug("Defines the Postgres store")
class PostgresReviewStore:
    """Reviews, decisions and exports, kept in Postgres."""

    # log.debug("Defines the constructor")
    def __init__(self, url: str | None = None) -> None:
        """Keeps the address and brings the schema up to date.

        Args:
            url: The database's address. Required.
        """
        # log.debug("Takes the address, which the caller must give")
        self.url = required(url=url)
        # log.debug("Applies any migration not yet applied")
        migrate(self.url)

    # log.debug("Defines the start of a review")
    def add(
        self,
        extraction: Extraction | None = None,
        *,
        source: str | None = None,
        demo: bool | None = None,
        request_id: str | None = None,
    ) -> Review:
        """Starts a review of an extraction and saves it.

        Args:
            extraction: The extraction to review. Required.
            source: Where the documents came from. Required.
            demo: Whether the offline stand-in made the extraction.
                Required.
            request_id: The request that made the extraction. Required.

        Returns:
            The new review, with no decisions yet.
        """
        # log.debug("Takes the extraction, which the caller must give")
        extraction = required(extraction=extraction)
        # log.debug("Takes the source, which the caller must give")
        source = required(source=source)
        # log.debug("Takes whether this is demo output, which the caller must give")
        demo = required(demo=demo)
        # log.debug("Takes the request id, which the caller must give")
        request_id = required(request_id=request_id)
        # log.debug("Builds the review as the memory store does")
        review = start_review(extraction, source=source, demo=demo, request_id=request_id)
        # log.debug("Saves it")
        with psycopg.connect(self.url) as db:
            # log.debug("Inserts the review with its extraction as JSON")
            db.execute(
                "insert into reviews (review_id, source, demo, created_at, request_id, extraction)"
                " values (%s, %s, %s, %s, %s, %s)",
                (
                    review.review_id,
                    review.source,
                    review.demo,
                    review.created_at,
                    review.request_id,
                    Jsonb(extraction_json(review.extraction)),
                ),
            )
        # log.debug("Returns it")
        return review

    # log.debug("Defines the lookup of a review")
    def get(self, review_id: str | None = None) -> Review | None:
        """Returns the review with its decisions, or None.

        Args:
            review_id: The review's id. Required.

        Returns:
            The review, or None when the database has none with the id.
        """
        # log.debug("Takes the id, which the caller must give")
        review_id = required(review_id=review_id)
        # log.debug("Reads the review and its decisions in one transaction")
        with psycopg.connect(self.url) as db:
            # log.debug("Reads the review")
            row = db.execute(
                "select source, demo, created_at, request_id, extraction"
                " from reviews where review_id = %s",
                (review_id,),
            ).fetchone()
            # log.debug("Reads its decisions")
            decisions = db.execute(
                "select field, action, value from decisions where review_id = %s", (review_id,)
            ).fetchall()
        # log.debug("Returns None for an unknown id")
        if row is None:
            # log.debug("Returns no review")
            return None
        # log.debug("Unpacks the row")
        source, demo, created_at, request_id, extraction = row
        # log.debug("Returns the review, rebuilt")
        return Review(
            review_id=review_id,
            source=source,
            demo=demo,
            created_at=stamp(created_at),
            request_id=request_id,
            extraction=extraction_from(extraction),
            decisions={f: Decision(field=f, action=a, value=v) for f, a, v in decisions},
        )

    # log.debug("Defines the record of a decision")
    def decide(self, review: Review | None = None, decision: Decision | None = None) -> int:
        """Saves a decision on one field, replacing any earlier one.

        Args:
            review: The review the decision is for. Required.
            decision: The reviewer's decision on one field. Required.

        Returns:
            How many of the review's fields now have a decision.

        Raises:
            ValueError: For a field the record does not have.
        """
        # log.debug("Takes the review, which the caller must give")
        review = required(review=review)
        # log.debug("Takes the decision, which the caller must give")
        decision = required(decision=decision)
        # log.debug("Refuses a field the record does not have")
        if decision.field not in FIELDS:
            # log.debug("Raises the unknown field's error")
            raise ValueError(f"unknown field {decision.field}")
        # log.debug("Saves it, replacing any earlier decision on the field")
        with psycopg.connect(self.url) as db:
            # log.debug("Inserts or replaces the decision")
            db.execute(
                "insert into decisions (review_id, field, action, value) values (%s, %s, %s, %s)"
                " on conflict (review_id, field) do update set action = excluded.action,"
                " value = excluded.value, decided_at = now()",
                (review.review_id, decision.field, decision.action, Jsonb(decision.value)),
            )
        # log.debug("Keeps the review in step")
        review.decisions[decision.field] = decision
        # log.debug("Returns how many fields are decided")
        return len(review.decisions)

    # log.debug("Defines the record of an export")
    def record_export(
        self, review: Review | None = None, export: dict[str, Any] | None = None
    ) -> None:
        """Saves the export; the database refuses to change it after.

        Args:
            review: The review exported. Required.
            export: What the export returned. Required.
        """
        # log.debug("Takes the review, which the caller must give")
        review = required(review=review)
        # log.debug("Takes the export, which the caller must give")
        export = required(export=export)
        # log.debug("Saves it")
        with psycopg.connect(self.url) as db:
            # log.debug("Inserts the export with its contract")
            db.execute(
                "insert into exports (review_id, exported_at, contract, payload)"
                " values (%s, %s, %s, %s)",
                (review.review_id, export["exported_at"], CONTRACT, Jsonb(export)),
            )


# log.debug("Defines an extraction as JSON")
def extraction_json(ex: Extraction | None = None) -> dict[str, Any]:
    """Returns the extraction as JSON values, for its database column.

    Args:
        ex: The extraction. Required.

    Returns:
        Every field of the extraction.
    """
    # log.debug("Takes the extraction, which the caller must give")
    ex = required(ex=ex)
    # log.debug("Returns each field, the records and warnings as their JSON")
    return {
        **{k: getattr(ex, k).model_dump(mode=AS_JSON) for k in RECORDS},
        "removed": ex.removed,
        "charge_pages": ex.charge_pages,
        "notice_pages": ex.notice_pages,
        "model": ex.model,
        "cost_usd": ex.cost_usd,
        "latency_ms": ex.latency_ms,
        WARNINGS: [w.model_dump(mode=AS_JSON) for w in ex.warnings],
    }


# log.debug("Defines an extraction from its JSON")
def extraction_from(values: dict[str, Any] | None = None) -> Extraction:
    """Returns the extraction its database column holds.

    Args:
        values: What extraction_json wrote. Required.

    Returns:
        The extraction.
    """
    # log.debug("Takes the values, which the caller must give")
    values = required(values=values)
    # log.debug("Returns the extraction, its records and warnings validated")
    record, raw = (ChargeRecord.model_validate(values[k]) for k in RECORDS)
    # log.debug("Takes every other field as it was written")
    rest: dict[str, Any] = {k: v for k, v in values.items() if k not in {*RECORDS, WARNINGS}}
    # log.debug("Returns the extraction")
    return Extraction(
        record=record,
        raw=raw,
        warnings=[Flagged.model_validate(w) for w in values[WARNINGS]],
        **rest,
    )
