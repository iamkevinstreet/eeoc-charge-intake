########################################################################
#                                                                      #
#                    warehouse/tests/test_build.py                     #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

Tests the whole build on the committed exports and a stand-in for
Table E1a laid out as the EEOC lays it out, its totals the published
ones: every seed, model, contract, unit test and data test passes, the
published totals among them, in a process of its own as in production,
and the marts hold what the exports say.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import os
import subprocess
import sys
from collections import Counter

# Third-party
import duckdb
import pytest
from kds.logs import get_logger

# Local
from pipelines import receipts as receipts_module
from pipelines.config import AppSettings
from pipelines.receipts import load_receipts
from pipelines.reviews import load_reviews
from support import REPO, TABLE_E1A, Download, committed_exports, settings_in, workbook

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = get_logger(__name__)


########################################################################
#                                                                      #
#                             Build tests                              #
#                                                                      #
########################################################################
# log.debug("Defines the warehouse every build test reads, built once")
@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> AppSettings:
    """Loads both sources into a warehouse of its own, then builds it.

    Args:
        tmp_path_factory: pytest's maker of temporary folders.

    Returns:
        The built warehouse's settings.
    """
    # log.debug("Makes the warehouse's folder")
    folder = tmp_path_factory.mktemp("build")
    # log.debug("Moves to the repository, whose settings name the folders read")
    with pytest.MonkeyPatch.context() as patch:
        # log.debug("Moves there")
        patch.chdir(REPO)
        # log.debug("Builds the settings")
        settings = settings_in(folder)
        # log.debug("Loads the committed exports")
        load_reviews(settings)
        # log.debug("Answers the table's download with the stand-in")
        patch.setattr(receipts_module, "requests", Download(workbook(TABLE_E1A)))
        # log.debug("Loads the table")
        load_receipts(settings)
    # log.debug("Points the command at the test's warehouse")
    env = os.environ | {"WAREHOUSE_PATH": str(settings.warehouse_path)}
    # log.debug("Builds every seed, model and test, as the DAG does")
    build = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "pipelines",
            "dbt",
            "build",
            "--target-path",
            str(folder / "target"),
        ],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    # log.debug("Checks the build passed, showing its output when it did not")
    assert build.returncode == 0, build.stdout[-3000:]
    # log.debug("Returns the settings")
    return settings


# log.debug("Defines the test that every charge is in the mart once")
def test_every_reviewed_charge_is_one_row_with_its_reviews_counted(built: AppSettings) -> None:
    """Charges by number, or by document without one; reviews summed.

    Args:
        built: The built warehouse's settings.
    """
    # log.debug("Counts each charge's reviews in the files")
    charges = Counter(e["record"]["charge_number"] or e["source"] for e in committed_exports())
    # log.debug("Reads the mart")
    with duckdb.connect(str(built.warehouse_path), read_only=True) as db:
        # log.debug("Counts its charges and their reviews")
        row = db.execute("select count(*), sum(reviews) from charges.fct_charges").fetchone()
    # log.debug("Checks one row per charge, and every review counted")
    assert row == (len(charges), sum(charges.values()))


# log.debug("Defines the test that the corrections are the files' own")
def test_each_fields_corrections_are_the_exports_edits_and_rejections(built: AppSettings) -> None:
    """The mart corrects a field exactly as often as the exports say.

    Args:
        built: The built warehouse's settings.
    """
    # log.debug("Counts each field's edits and rejections in the files")
    expected = Counter(
        f for e in committed_exports() for f, d in e["decisions"].items() if d != "accept"
    )
    # log.debug("Reads the mart")
    with duckdb.connect(str(built.warehouse_path), read_only=True) as db:
        # log.debug("Counts each field's corrections there")
        rows = db.execute(
            "select field, count(*) from charges.fct_field_reviews where corrected group by field"
        ).fetchall()
    # log.debug("Checks they match")
    assert dict(rows) == dict(expected)
