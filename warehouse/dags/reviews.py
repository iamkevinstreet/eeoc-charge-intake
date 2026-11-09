########################################################################
#                                                                      #
#                      warehouse/dags/reviews.py                       #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

Loads every review export in `[reviews] folder` each day, each checked
against contract v1, and updates the raw_reviews asset, which starts
the warehouse build.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

# Third-party
from airflow.sdk import DAG
from kds.logs import get_logger

# Local
from defaults import DAG_DEFAULTS, RAW_REVIEWS, pipelines_task

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = get_logger(__name__)

########################################################################
#                                                                      #
#                                 DAG                                  #
#                                                                      #
########################################################################
# log.debug("Defines the daily load")
with DAG(
    dag_id="load_reviews",
    schedule="37 5 * * *",
    tags=["eeoc", "load"],
    doc_md=__doc__,
    **DAG_DEFAULTS,
):
    # log.debug("Runs the load, updating its raw schema's asset")
    pipelines_task("load_exports", "load reviews", outlets=[RAW_REVIEWS])
