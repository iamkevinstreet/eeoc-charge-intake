########################################################################
#               backend/src/eeoc_intake/core/charges.py                #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Draws one made-up charge from the seeded generators and writes its two
documents: the EEOC Form 5 and the notice letter. Every fifth charge is
a hard case, in turn: a missing charge number, a rotated first page,
particulars that run to three pages, or two respondents. The order of
the draws is part of the data, so the same seed always makes the same
documents, draw for draw.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Final

# Third-party
from kds.args import required
from kds.logs import get_logger
from kds.synthetic.names import NameGen
from kds.synthetic.pdf import PdfDoc

# Local
from eeoc_intake.config import SETTINGS

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the kind of a document that is not a hard case, from the config")
CLEAN: Final = SETTINGS.samples_clean

########################################################################
#                           Local constants                            #
########################################################################
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


########################################################################
#                           Made-up charges                            #
########################################################################
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
def kind_of(i: int | None = None, hard_every: int | None = None) -> str:
    """Returns "clean", or the hard case that falls at position i.

    Args:
        i: The charge's position in the set, from 0. Required.
        hard_every: How often a hard case comes round: every fifth
            document by default. Required.

    Returns:
        The kind of case: clean, or one of the hard cases in turn.
    """
    # log.debug("Takes the position, which the caller must give")
    i = required(i=i)
    # log.debug("Takes the hard-case rate, which the caller must give")
    hard_every = required(hard_every=hard_every)
    # log.debug("Returns clean unless this is the last of a group")
    if i % hard_every != hard_every - 1:
        # log.debug("Returns clean")
        return CLEAN
    # log.debug("Returns the hard kinds in turn")
    return HARD_KINDS[(i // hard_every) % len(HARD_KINDS)]


# log.debug("Defines the draws for one charge, in a fixed order")
def draw(
    i: int | None = None,
    rng: random.Random | None = None,
    gen: NameGen | None = None,
    hard_every: int | None = None,
) -> Charge:
    """Draws every value of charge i from the two seeded generators.

    The order of the draws is part of the data: changing it changes
    every document after it.

    Args:
        i: The charge's position in the set, from 0. Required.
        rng: The seeded generator of values. Required.
        gen: The seeded generator of names, places and companies.
            Required.
        hard_every: How often a hard case comes round. Required.

    Returns:
        Every value the charge's two documents print.
    """
    # log.debug("Takes the position, which the caller must give")
    i = required(i=i)
    # log.debug("Takes the generator of values, which the caller must give")
    rng = required(rng=rng)
    # log.debug("Takes the generator of names, which the caller must give")
    gen = required(gen=gen)
    # log.debug("Takes the hard-case rate, which the caller must give")
    hard_every = required(hard_every=hard_every)
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
    respondent: str | None = None,
    bases: list[str] | None = None,
    issues: list[str] | None = None,
    harm: tuple[date, date] | None = None,
    rng: random.Random | None = None,
) -> list[str]:
    """Returns the particulars: issues described, never named.

    Args:
        respondent: The employer the charge is against. Required.
        bases: The protected bases the charge names. Required.
        issues: The employment actions to describe. Required.
        harm: The first and last dates of harm. Required.
        rng: The seeded generator, which picks a basis for each issue.
            Required.

    Returns:
        The paragraphs: the employment and dates, one sentence for each
        issue, and the bases.
    """
    # log.debug("Takes the respondent, which the caller must give")
    respondent = required(respondent=respondent)
    # log.debug("Takes the bases, which the caller must give")
    bases = required(bases=bases)
    # log.debug("Takes the issues, which the caller must give")
    issues = required(issues=issues)
    # log.debug("Takes the dates of harm, which the caller must give")
    harm = required(harm=harm)
    # log.debug("Takes the generator of values, which the caller must give")
    rng = required(rng=rng)
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
def write_charge(charge: Charge | None = None, out: Path | None = None) -> Path:
    """Writes the EEOC Form 5 for `charge` into the folder `out`.

    Args:
        charge: The charge's values. Required.
        out: The folder to write into. Required.

    Returns:
        The path of the PDF written.
    """
    # log.debug("Takes the charge, which the caller must give")
    charge = required(charge=charge)
    # log.debug("Takes the folder, which the caller must give")
    out = required(out=out)
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
def write_notice(charge: Charge | None = None, out: Path | None = None) -> Path:
    """Writes the notice letter for `charge` into the folder `out`.

    Args:
        charge: The charge's values. Required.
        out: The folder to write into. Required.

    Returns:
        The path of the PDF written.
    """
    # log.debug("Takes the charge, which the caller must give")
    charge = required(charge=charge)
    # log.debug("Takes the folder, which the caller must give")
    out = required(out=out)
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
