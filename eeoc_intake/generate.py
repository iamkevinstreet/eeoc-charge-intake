"""Generate made-up charge forms and notice letters with known answers.

    python -m eeoc_intake.generate --n 30 --out eeoc_intake/data/generated

Every fifth document is a hard case: a missing charge number, a rotated page, particulars that run to three
pages, or two respondents. The `cases.jsonl` it writes is the evaluation set.
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path

from kds.synthetic.names import NameGen
from kds.synthetic.pdf import PdfDoc

OFFICES = [
    "Atlanta District Office",
    "Chicago District Office",
    "Dallas District Office",
    "Phoenix District Office",
]
BASES = ["Race", "Sex", "Age", "Disability", "Religion", "National Origin", "Retaliation", "Color"]
ISSUES = [
    "Discharge",
    "Harassment",
    "Terms/Conditions",
    "Promotion",
    "Discipline",
    "Reasonable Accommodation",
]


def make_one(i: int, rng: random.Random, gen: NameGen, out: Path) -> dict:
    hard = i % 5 == 4
    kind = ["missing_number", "rotated", "long", "two_respondents"][(i // 5) % 4] if hard else "clean"
    party = gen.person()
    respondent = gen.company()
    second = gen.company() if kind == "two_respondents" else None
    office = rng.choice(OFFICES)
    bases = sorted(rng.sample(BASES, rng.randint(1, 3)))
    issues = sorted(rng.sample(ISSUES, rng.randint(1, 2)))
    earliest = date(2025, rng.randint(1, 12), rng.randint(1, 28))
    latest = earliest + timedelta(days=rng.randint(0, 200))
    continuing = rng.random() < 0.3
    notice = latest + timedelta(days=rng.randint(20, 90))
    number = None if kind == "missing_number" else f"410-2026-{10000 + i:05d}"

    charge = PdfDoc(out / f"charge-{i:03d}.pdf")
    charge.line("EEOC FORM 5 (11/09)")
    charge.line("CHARGE OF DISCRIMINATION")
    charge.line(f"Charge No. {number}" if number else "Charge No. ____________")
    charge.line(f"EEOC Office: {office}")
    charge.line("")
    charge.line(f"Charging Party: {party}")
    charge.line(f"City/State: {gen.city_state()}")
    resp_line = f"Respondent: {respondent}" + (f"; {second}" if second else "")
    charge.line(resp_line)
    charge.line("")
    charge.line("DISCRIMINATION BASED ON: " + ", ".join(bases))
    charge.line(f"DATE(S) DISCRIMINATION TOOK PLACE: Earliest {earliest:%m/%d/%Y} Latest {latest:%m/%d/%Y}")
    if continuing:
        charge.line("[X] CONTINUING ACTION")
    charge.line("")
    charge.line("THE PARTICULARS ARE:")
    paragraphs = 2 if kind != "long" else 9
    for p in range(paragraphs):
        charge.para(
            f"{p + 1}. I was employed by {respondent.rstrip('.')}. I believe I was subjected to "
            f"{' and '.join(i.lower() for i in issues)} because of my {' and '.join(b.lower() for b in bases)}, "
            f"in violation of applicable law. On or about {earliest:%B %d, %Y} the conduct began and it "
            f"continued through {latest:%B %d, %Y}."
        )
        if kind == "long" and p % 3 == 2:
            charge.page_break()
    charge.write(rotate_pages={1} if kind == "rotated" else None)

    notice_doc = PdfDoc(out / f"notice-{i:03d}.pdf")
    notice_doc.line("U.S. EQUAL EMPLOYMENT OPPORTUNITY COMMISSION")
    notice_doc.line(office)
    notice_doc.line("NOTICE OF CHARGE OF DISCRIMINATION")
    notice_doc.line(f"Date of Notice: {notice:%m/%d/%Y}")
    notice_doc.line(f"To: {respondent}")
    notice_doc.line(f"Re: Charge No. {number}" if number else "Re: Charge pending assignment of number")
    notice_doc.para(
        "This is notice that a charge of employment discrimination has been filed against your organization. "
        "No action is required on your part at this time. A position statement may be requested."
    )
    notice_doc.write()

    gold = {
        "charge_number": number,
        "charging_party": party,
        "respondent": respondent if not second else [respondent, second],
        "eeoc_office": office,
        "bases": bases,
        "issues": issues,
        "earliest_date": earliest.isoformat(),
        "latest_date": latest.isoformat(),
        "continuing_action": continuing,
        "notice_date": notice.isoformat(),
    }
    return {
        "id": f"charge-{i:03d}",
        "input": {"charge_pdf": str(charge.path), "notice_pdf": str(notice_doc.path)},
        "expected": gold,
        "tags": [kind],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", type=Path, default=Path("eeoc_intake/data/generated"))
    args = ap.parse_args()
    rng = random.Random(args.seed)
    gen = NameGen(seed=args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    cases = [make_one(i, rng, gen, args.out) for i in range(args.n)]
    with (args.out / "cases.jsonl").open("w", encoding="utf-8") as fh:
        for c in cases:
            fh.write(json.dumps(c) + "\n")
    print(f"wrote {len(cases)} cases to {args.out / 'cases.jsonl'}")


if __name__ == "__main__":
    main()
