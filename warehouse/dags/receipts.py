########################################################################
#                                                                      #
#                      warehouse/dags/receipts.py                      #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

Loads the EEOC's Table E1a, charge receipts by basis, on the third of
each month, and updates the raw_eeoc_stats asset, which starts the
warehouse build. The EEOC publishes it once a year; a monthly load
catches a revision, which shows as a new hash on its rows.
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
from defaults import DAG_DEFAULTS, RAW_EEOC_STATS, pipelines_task

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
# log.debug("Defines the monthly load")
with DAG(
    dag_id="load_receipts",
    schedule="43 7 3 * *",
    tags=["eeoc", "load"],
    doc_md=__doc__,
    **DAG_DEFAULTS,
):
    # log.debug("Runs the load, updating its raw schema's asset")
    pipelines_task("load_table", "load receipts", outlets=[RAW_EEOC_STATS])
