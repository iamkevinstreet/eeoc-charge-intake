########################################################################
#                                                                      #
#                    warehouse/pipelines/config.py                     #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-10

Every setting this project's loaders, build and DAGs read. The shared
ones (the warehouse, dlt's state, dbt, Databricks and Snowflake) come
from kds.pipelines; each source adds its own here, and
config/config.toml lists them all at their defaults. SETTINGS holds
the settings loaded once at import; functions that take settings still
take them, so tests can pass their own.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Final

# Third-party
from kds.logs import get_logger
from kds.pipelines import PipelineSettings
from pydantic import Field

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
# log.debug("Sets the EEOC's Table E1a, receipts by basis, FY 1997 to FY 2025, of April 2026")
RECEIPTS: Final = (
    "https://www.eeoc.gov/sites/default/files/2026-04/"
    "Table_E1a._Charge_Receipts_by_Basis_or_Statute_%28All_Statutes%29_FY_1997_-_FY_2025_0.xlsx"
)


########################################################################
#                                                                      #
#                               Settings                               #
#                                                                      #
########################################################################
# log.debug("Defines this project's settings, the shared ones and its own")
class AppSettings(PipelineSettings):
    """Every setting the loaders, the build and the DAGs read."""

    # log.debug("Holds the schema the EEOC's national statistics load into")
    receipts_dataset: str = "raw_eeoc_stats"
    # log.debug("Holds the address of the EEOC's receipts table")
    receipts_url: str = RECEIPTS
    # log.debug("Holds how long the table's download may take")
    receipts_timeout_s: float = Field(default=60.0, gt=0)

    # log.debug("Holds the schema the review exports load into")
    reviews_dataset: str = "raw_reviews"
    # log.debug("Holds the folder of review exports, one file each or one per line")
    reviews_folder: Path = Path("../data/reviews")
    # log.debug("Holds the export contract every file must meet")
    reviews_contract: Path = Path("../backend/src/eeoc_intake/contracts/review_export_v1.json")
    # log.debug("Holds the fields whose values name a person, each a plain field name")
    reviews_personal_fields: list[Annotated[str, Field(pattern=r"^[a-z_]+$")]] = Field(
        default_factory=lambda: ["charging_party"], min_length=1
    )
    # log.debug("Holds the group a Databricks mask shows a name to, with no quote in its name")
    reviews_personal_readers: str = Field(
        default="personal-data-readers", pattern=r"^[A-Za-z0-9 ._-]+$"
    )
    # log.debug("Holds the role a Snowflake mask shows a name to, a plain role name")
    reviews_personal_role: str = Field(
        default="PERSONAL_DATA_READER", pattern=r"^[A-Z][A-Z0-9_]*$"
    )


# log.debug("Defines how the settings are read")
@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    """Returns the settings, read once per process.

    Returns:
        The settings from config/config.toml, config/.env and the
        environment.
    """
    # log.debug("Reads the settings")
    return AppSettings()


# log.debug("Reads the settings once, for the values modules bind at import")
SETTINGS: Final = get_app_settings()
