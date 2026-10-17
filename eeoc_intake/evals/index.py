"""Write index.json for a results folder so a static site can fetch the files without listing a directory.

python -m eeoc_intake.evals.index eeoc_intake/evals/results/live
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_index(folder: Path) -> dict:
    runs = sorted(p.name for p in folder.glob("*.json") if p.name not in ("index.json", "figures.json"))
    extractions = {}
    for d in sorted((folder / "extractions").glob("*")) if (folder / "extractions").exists() else []:
        if d.is_dir():
            extractions[d.name] = sorted(p.name for p in d.glob("*.json"))
    return {
        "runs": runs,
        "extractions": extractions,
        "figures": "figures.json" if (folder / "figures.json").exists() else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    args = ap.parse_args()
    index = build_index(args.folder)
    (args.folder / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {args.folder / 'index.json'}: {len(index['runs'])} runs, {len(index['extractions'])} extraction folders"
    )


if __name__ == "__main__":
    main()
