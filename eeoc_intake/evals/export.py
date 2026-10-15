"""Export evaluation results as tidy CSV files for Tableau (or any BI tool).

    python -m eeoc_intake.evals.export                 # writes eeoc_intake/evals/results/export/*.csv

Three files, one row per run, per document, and per (document, field). They come from the same frames the
Dash dashboard uses, so the numbers agree. docs/TABLEAU.md describes the sheets to build from them.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from eeoc_intake.dashboard import RESULTS_DIR, frames, load_runs


def export(results_dir: Path, out: Path) -> list[Path]:
    runs_df, cases_df, fields_df = frames(load_runs(results_dir))
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, df in (("runs", runs_df), ("documents", cases_df), ("fields", fields_df)):
        path = out / f"{name}.csv"
        df.to_csv(path, index=False)
        written.append(path)
    return written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, default=RESULTS_DIR)
    ap.add_argument("--out", type=Path, default=RESULTS_DIR / "export")
    args = ap.parse_args()
    for p in export(args.results, args.out):
        print(f"wrote {p} ({sum(1 for _ in p.open()) - 1} rows)")


if __name__ == "__main__":
    main()
