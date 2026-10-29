########################################################################
#              backend/eeoc_intake/dashboard/__init__.py               #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           The evaluation dashboard: compare runs and see   #
#                     which fields fail on which documents.            #
########################################################################
"""The evaluation dashboard (Plotly Dash): compare runs, see failures.

Run it with `python -m eeoc_intake.dashboard`. The modules: data
(run files to tables, which the Tableau export shares), theme, the
charts (field_charts, run_charts), tiles, layout, page, app, and
export (the figures the case study draws). Nothing is imported here,
so reading the tables does not load Dash.
"""
