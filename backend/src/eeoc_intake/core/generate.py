########################################################################
#               backend/src/eeoc_intake/core/generate.py               #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Generates made-up charge forms and notice        #
#                     letters with known answers: the evaluation set.  #
########################################################################
"""Generate made-up charge forms and notice letters with known answers.

    python -m eeoc_intake.core.generate    # see [samples] in settings

Every fifth document is a hard case: a missing charge number, a rotated
page, particulars that run to three pages, or two respondents. The
`cases.jsonl` it writes is the evaluation set. The same seed always
makes the same documents, draw for draw.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Final

from kds.logs import get_logger
from kds.synthetic.names import NameGen
from kds.synthetic.pdf import PdfDoc

from eeoc_intake.config import AppSettings, get_app_settings

# Module constants
log = get_logger(__name__)
# log.debug("Lists the EEOC offices a charge may be filed with")
OFFICES: Final = (
    "Atlanta District Office",
    "Chicago District Office",
    "Dallas District Office",
    "Phoenix District Office",
)
# log.debug("Lists the protected bases a charge may name")
BASES: Final = (
    "Race",
    "Sex",
    "Age",
    "Disability",
    "Religion",
    "National Origin",
    "Retaliation",
    "Color",
)
# log.debug("Maps each issue to the plain sentence a charging party writes for it")
ISSUE_SENTENCES: Final = {
    "Discharge": "On or about {latest}, I was discharged from my position.",
    "Harassment": "Throughout this period I was subjected to harassment by my supervisor, "
    "including repeated remarks about my {basis} that made it difficult to do my job.",
    "Terms/Conditions": "My schedule, duties and pay were changed to less favorable terms and "
    "conditions of employment than those of my coworkers.",
    "Promotion": "I applied for a promotion for which I was qualified and was denied it in favor "
    "of a less experienced employee.",
    "Discipline": "I was issued written discipline for conduct that similarly situated employees "
    "engaged in without consequence.",
    "Reasonable Accommodation": "I requested a reasonable accommodation and my request was "
    "denied without discussion.",
}
# log.debug("Lists the issues, in the order the sentences are listed")
ISSUES: Final = tuple(ISSUE_SENTENCES)
# log.debug("Sets the background paragraph that makes a long case run to three pages")
FILLER: Final = (
    "Paragraph {n} of additional background. I reported my concerns to human resources in "
    "writing and received no response. I have kept copies of my emails, schedules and "
    "performance reviews from this period."
)
# log.debug("Lists the hard cases, in the order they come round")
HARD_KINDS: Final = ("missing_number", "rotated", "long", "two_respondents")
# log.debug("Names the ordinary case")
CLEAN: Final = "clean"
# log.debug("Names the hard case with no charge number")
MISSING_NUMBER: Final = HARD_KINDS[0]
# log.debug("Names the hard case with a page turned on its side")
ROTATED: Final = HARD_KINDS[1]
# log.debug("Names the hard case whose particulars run to three pages")
LONG: Final = HARD_KINDS[2]
# log.debug("Names the hard case with two respondents")
TWO_RESPONDENTS: Final = HARD_KINDS[3]
# log.debug("Sets the most bases one charge names")
MAX_BASES: Final = 3
# log.debug("Sets the most issues one charge describes")
MAX_ISSUES: Final = 2
# log.debug("Sets the year the harm begins in")
YEAR: Final = 2025
# log.debug("Sets the months in a year")
MONTHS: Final = 12
# log.debug("Sets the last day every month has, so any month's date is valid")
LAST_SAFE_DAY: Final = 28
# log.debug("Sets the most days the harm may run")
MAX_SPAN_DAYS: Final = 200
# log.debug("Sets how often the form marks a continuing action")
CONTINUING_SHARE: Final = 0.3
# log.debug("Sets the fewest days between the last harm and the notice")
MIN_NOTICE_DAYS: Final = 20
# log.debug("Sets the most days between the last harm and the notice")
MAX_NOTICE_DAYS: Final = 90
# log.debug("Sets the first charge number's serial")
FIRST_SERIAL: Final = 10_000
# log.debug("Numbers the six background paragraphs a long case adds")
FILLERS: Final = tuple(FILLER.format(n=n) for n in range(1, 7))
# log.debug("Sets how many paragraphs a long case puts on each page")
PARAGRAPHS_PER_PAGE: Final = 3
# log.debug("Sets the long date the particulars use")
LONG_DATE: Final = "%B %d, %Y"
# log.debug("Sets the short date the forms use")
FORM_DATE: Final = "%m/%d/%Y"
# log.debug("Sets the file the evaluation set is written to")
CASES_FILE: Final = "cases.jsonl"
# log.debug("Sets the text encoding of every file written")
ENCODING: Final = "utf-8"


# log.debug("Defines the values one charge and its notice print")
@dataclass(frozen=True)
class Charge:
    """One made-up charge: every value its two documents print.

    Attributes:
        index: Its number in the set, which names its files.
        kind: "clean", or which hard case it is.
        number: The charge number, or None when the form has none.
        party: The charging party.
        city_state: Where the charging party lives.
        respondents: The employer, and a second one for that hard case.
        office: The EEOC office.
        bases: The protected bases, sorted.
        issues: The employment actions, sorted.
        earliest: The first date of harm.
        latest: The last date of harm.
        continuing: Whether the form marks a continuing action.
        notice: The date of the EEOC's notice.
        paragraphs: The particulars, one paragraph each.
    """

    # log.debug("Holds the charge's number in the set")
    index: int
    # log.debug("Holds the kind of case")
    kind: str
    # log.debug("Holds the charge number, if printed")
    number: str | None
    # log.debug("Holds the charging party")
    party: str
    # log.debug("Holds the party's city and state")
    city_state: str
    # log.debug("Holds the respondents")
    respondents: tuple[str, ...]
    # log.debug("Holds the EEOC office")
    office: str
    # log.debug("Holds the bases")
    bases: list[str]
    # log.debug("Holds the issues")
    issues: list[str]
    # log.debug("Holds the first date of harm")
    earliest: date
    # log.debug("Holds the last date of harm")
    latest: date
    # log.debug("Holds whether the harm continues")
    continuing: bool
    # log.debug("Holds the notice date")
    notice: date
    # log.debug("Holds the particulars")
    paragraphs: list[str]


# log.debug("Defines which kind of case a position in the set is")
def kind_of(i: int, hard_every: int) -> str:
    """Return "clean", or the hard case that falls at position i."""
    # log.debug("Returns clean unless this is the last of a group")
    if i % hard_every != hard_every - 1:
        # log.debug("Returns clean")
        return CLEAN
    # log.debug("Returns the hard kinds in turn")
    return HARD_KINDS[(i // hard_every) % len(HARD_KINDS)]


# log.debug("Defines the draws for one charge, in a fixed order")
def draw(i: int, rng: random.Random, gen: NameGen, hard_every: int) -> Charge:
    """Draw every value of charge i from the two seeded generators.

    The order of the draws is part of the data: changing it changes
    every document after it.
    """
    # log.debug("Works out the kind of case")
    kind = kind_of(i, hard_every)
    # log.debug("Draws the charging party")
    party = gen.person()
    # log.debug("Draws the employer")
    respondent = gen.company()
    # log.debug("Draws a second employer for that hard case only")
    second = (gen.company(),) if kind == TWO_RESPONDENTS else ()
    # log.debug("Draws the office")
    office = rng.choice(OFFICES)
    # log.debug("Draws one to three bases")
    bases = sorted(rng.sample(BASES, rng.randint(1, MAX_BASES)))
    # log.debug("Draws one or two issues")
    issues = sorted(rng.sample(ISSUES, rng.randint(1, MAX_ISSUES)))
    # log.debug("Draws the first date of harm")
    earliest = date(YEAR, rng.randint(1, MONTHS), rng.randint(1, LAST_SAFE_DAY))
    # log.debug("Draws how long the harm ran")
    latest = earliest + timedelta(days=rng.randint(0, MAX_SPAN_DAYS))
    # log.debug("Draws whether the form marks a continuing action")
    continuing = rng.random() < CONTINUING_SHARE
    # log.debug("Draws when the notice went out")
    notice = latest + timedelta(days=rng.randint(MIN_NOTICE_DAYS, MAX_NOTICE_DAYS))
    # log.debug("Draws where the charging party lives")
    city_state = gen.city_state()
    # log.debug("Writes the particulars, which draw a basis for each issue")
    paragraphs = particulars(respondent, bases, issues, (earliest, latest), rng)
    # log.debug("Returns every value of the charge")
    return Charge(
        index=i,
        kind=kind,
        number=None if kind == MISSING_NUMBER else f"410-2026-{FIRST_SERIAL + i:05d}",
        party=party,
        city_state=city_state,
        respondents=(respondent, *second),
        office=office,
        bases=bases,
        issues=issues,
        earliest=earliest,
        latest=latest,
        continuing=continuing,
        notice=notice,
        paragraphs=[*paragraphs, *FILLERS] if kind == LONG else paragraphs,
    )


# log.debug("Defines the particulars a charging party writes")
def particulars(
    respondent: str,
    bases: list[str],
    issues: list[str],
    harm: tuple[date, date],
    rng: random.Random,
) -> list[str]:
    """Return the particulars: issues described, never named."""
    # log.debug("Unpacks the first and last dates of harm")
    earliest, latest = harm
    # log.debug("Opens with the employment and the dates")
    opening = (
        f"I was employed by {respondent.rstrip('.')} beginning before {earliest:{LONG_DATE}}. "
        f"The conduct described below began on or about {earliest:{LONG_DATE}} and continued "
        f"through {latest:{LONG_DATE}}."
    )
    # log.debug("Describes each issue in the charging party's words")
    events = [
        ISSUE_SENTENCES[issue].format(
            latest=f"{latest:{LONG_DATE}}", basis=rng.choice(bases).lower()
        )
        for issue in issues
    ]
    # log.debug("Closes with the bases")
    closing = (
        "I believe I have been discriminated against because of my "
        + " and ".join(basis.lower() for basis in bases)
        + ", in violation of applicable federal law."
    )
    # log.debug("Returns the paragraphs in order")
    return [opening, *events, closing]


# log.debug("Defines the charge form")
def write_charge(charge: Charge, out: Path) -> Path:
    """Write the EEOC Form 5 for `charge` to `out`; return its path."""
    # log.debug("Starts the PDF")
    doc = PdfDoc(out / f"charge-{charge.index:03d}.pdf")
    # log.debug("Writes the form's heading lines and the charge number")
    for line in (
        "EEOC FORM 5 (11/09)",
        "CHARGE OF DISCRIMINATION",
        f"Charge No. {charge.number}" if charge.number else "Charge No. ____________",
        f"EEOC Office: {charge.office}",
        "",
        f"Charging Party: {charge.party}",
        f"City/State: {charge.city_state}",
        "Respondent: " + "; ".join(charge.respondents),
        "",
        "DISCRIMINATION BASED ON: " + ", ".join(charge.bases),
        f"DATE(S) DISCRIMINATION TOOK PLACE: Earliest {charge.earliest:{FORM_DATE}} "
        f"Latest {charge.latest:{FORM_DATE}}",
    ):
        # log.debug("Writes one line")
        doc.line(line)
    # log.debug("Ticks the continuing action box when the charge says so")
    if charge.continuing:
        # log.debug("Writes the ticked box")
        doc.line("[X] CONTINUING ACTION")
    # log.debug("Leaves a blank line before the particulars")
    doc.line("")
    # log.debug("Writes the particulars' heading")
    doc.line("THE PARTICULARS ARE:")
    # log.debug("Writes each paragraph, numbered")
    for n, text in enumerate(charge.paragraphs, start=1):
        # log.debug("Writes the paragraph")
        doc.para(f"{n}. {text}")
        # log.debug("Breaks a long case's page after every third paragraph")
        if charge.kind == LONG and n % PARAGRAPHS_PER_PAGE == 0:
            # log.debug("Starts a new page")
            doc.page_break()
    # log.debug("Saves the PDF, turning the first page for that hard case")
    doc.write(rotate_pages={1} if charge.kind == ROTATED else None)
    # log.debug("Returns where it was saved")
    return doc.path


# log.debug("Defines the EEOC's notice letter")
def write_notice(charge: Charge, out: Path) -> Path:
    """Write the notice for `charge` to `out`; return its path."""
    # log.debug("Starts the PDF")
    doc = PdfDoc(out / f"notice-{charge.index:03d}.pdf")
    # log.debug("Writes the letter's heading, date, addressee and reference")
    for line in (
        "U.S. EQUAL EMPLOYMENT OPPORTUNITY COMMISSION",
        charge.office,
        "NOTICE OF CHARGE OF DISCRIMINATION",
        f"Date of Notice: {charge.notice:{FORM_DATE}}",
        f"To: {charge.respondents[0]}",
        f"Re: Charge No. {charge.number}"
        if charge.number
        else "Re: Charge pending assignment of number",
    ):
        # log.debug("Writes one line")
        doc.line(line)
    # log.debug("Writes the body of the letter")
    doc.para(
        "This is notice that a charge of employment discrimination has been filed against your "
        "organization. No action is required on your part at this time. A position statement "
        "may be requested."
    )
    # log.debug("Saves the PDF")
    doc.write()
    # log.debug("Returns where it was saved")
    return doc.path


# log.debug("Defines the known answers for one charge")
def expected(charge: Charge) -> dict[str, Any]:
    """Return the values a correct extraction of `charge` finds."""
    # log.debug("Returns each scored field's true value")
    return {
        "charge_number": charge.number,
        "charging_party": charge.party,
        "respondent": charge.respondents[0]
        if len(charge.respondents) == 1
        else list(charge.respondents),
        "eeoc_office": charge.office,
        "bases": charge.bases,
        "issues": charge.issues,
        "earliest_date": charge.earliest.isoformat(),
        "latest_date": charge.latest.isoformat(),
        "continuing_action": charge.continuing,
        "notice_date": charge.notice.isoformat(),
    }


# log.debug("Defines one evaluation case: two documents and their answers")
def make_case(
    i: int, rng: random.Random, gen: NameGen, out: Path, *, hard_every: int
) -> dict[str, Any]:
    """Draw charge i, write its two PDFs into `out`, return its case."""
    # log.debug("Draws the charge's values")
    charge = draw(i, rng, gen, hard_every)
    # log.debug("Returns the case: its documents, its answers and its kind")
    return {
        "id": f"charge-{i:03d}",
        "input": {
            "charge_pdf": str(write_charge(charge, out)),
            "notice_pdf": str(write_notice(charge, out)),
        },
        "expected": expected(charge),
        "tags": [charge.kind],
    }


# log.debug("Defines a whole evaluation set")
def generate(settings: AppSettings, out: Path | None = None) -> Path:
    """Write the documents and cases.jsonl; return the cases file.

    Args:
        settings: The count, seed and hard-case rate to use.
        out: The folder to write to; `[data] samples` if None.
    """
    # log.debug("Picks the folder, from settings unless given")
    folder = out or settings.data_samples
    # log.debug("Makes the folder")
    folder.mkdir(parents=True, exist_ok=True)
    # log.debug("Seeds the generator of values")
    rng = random.Random(settings.samples_seed)  # noqa: S311 - made-up data, not security
    # log.debug("Seeds the generator of names with the same seed")
    gen = NameGen(seed=settings.samples_seed)
    # log.debug("Makes every case in order, so each draw happens in sequence")
    cases = [
        make_case(i, rng, gen, folder, hard_every=settings.samples_hard_every)
        for i in range(settings.samples_count)
    ]
    # log.debug("Names the cases file")
    path = folder / CASES_FILE
    # log.debug("Writes one case per line")
    path.write_text("".join(json.dumps(c) + "\n" for c in cases), encoding=ENCODING)
    # log.debug("Returns the cases file")
    return path


# log.debug("Defines the command line")
def main() -> None:
    """Generate the set the settings describe, or one --out folder."""
    # log.debug("Reads the one option: where to write")
    parser = argparse.ArgumentParser(description="Generate made-up charges with answers.")
    # log.debug("Adds the folder option")
    parser.add_argument("--out", type=Path, default=None, help="default: [data] samples")
    # log.debug("Parses the command line")
    args = parser.parse_args()
    # log.debug("Writes the set")
    path = generate(get_app_settings(), args.out)
    # log.debug("Says where the cases went")
    print(f"wrote {path}")


# log.debug("Runs the command when the module is run as a script")
if __name__ == "__main__":
    # log.debug("Calls main")
    main()
