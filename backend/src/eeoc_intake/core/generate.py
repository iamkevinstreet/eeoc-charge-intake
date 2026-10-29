########################################################################
#               backend/src/eeoc_intake/core/generate.py               #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Generates the evaluation set: made-up charge forms and notice letters,
and cases.jsonl, which lists each pair with its known answers.

    python -m eeoc_intake.core.generate    # see [samples] in the config

The settings give the count, the seed and how often a hard case comes
round; the same seed always makes the same documents.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Final

# Third-party
from kds.args import required
from kds.logs import get_logger
from kds.synthetic.names import NameGen

# Local
from eeoc_intake.config import SETTINGS, AppSettings, get_app_settings
from eeoc_intake.core.charges import Charge, draw, write_charge, write_notice

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the file the evaluation set is written to, from the config")
CASES_FILE: Final = SETTINGS.samples_cases
# log.debug("Takes the text encoding of every file written, from the config")
ENCODING: Final = SETTINGS.files_encoding
# log.debug("Takes the input that holds a case's charge PDF, from the config")
CHARGE_PDF: Final = SETTINGS.samples_charge_input
# log.debug("Takes the input that holds a case's notice PDF, from the config")
NOTICE_PDF: Final = SETTINGS.samples_notice_input


########################################################################
#                            Evaluation set                            #
########################################################################
# log.debug("Defines the known answers for one charge")
def expected(charge: Charge | None = None) -> dict[str, Any]:
    """Returns the values a correct extraction of `charge` finds.

    Args:
        charge: The charge's values. Required.

    Returns:
        Each scored field's true value: a list for two respondents, and
        None for a charge number the form leaves blank.
    """
    # log.debug("Takes the charge, which the caller must give")
    charge = required(charge=charge)
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
    i: int | None = None,
    rng: random.Random | None = None,
    gen: NameGen | None = None,
    out: Path | None = None,
    *,
    hard_every: int | None = None,
) -> dict[str, Any]:
    """Draws charge i, writes its two PDFs into `out`, returns its case.

    Args:
        i: The charge's position in the set, from 0. Required.
        rng: The seeded generator of values. Required.
        gen: The seeded generator of names, places and companies.
            Required.
        out: The folder to write the PDFs into. Required.
        hard_every: How often a hard case comes round. Required.

    Returns:
        The case: its id, the paths of its two PDFs, its known answers
        and its kind.
    """
    # log.debug("Takes the position, which the caller must give")
    i = required(i=i)
    # log.debug("Takes the generator of values, which the caller must give")
    rng = required(rng=rng)
    # log.debug("Takes the generator of names, which the caller must give")
    gen = required(gen=gen)
    # log.debug("Takes the folder, which the caller must give")
    out = required(out=out)
    # log.debug("Takes the hard-case rate, which the caller must give")
    hard_every = required(hard_every=hard_every)
    # log.debug("Draws the charge's values")
    charge = draw(i, rng, gen, hard_every)
    # log.debug("Returns the case: its documents, its answers and its kind")
    return {
        "id": f"charge-{i:03d}",
        "input": {
            CHARGE_PDF: str(write_charge(charge, out)),
            NOTICE_PDF: str(write_notice(charge, out)),
        },
        "expected": expected(charge),
        "tags": [charge.kind],
    }


# log.debug("Defines a whole evaluation set")
def generate(settings: AppSettings | None = None, out: Path | None = None) -> Path:
    """Writes the documents and cases.jsonl, and returns the cases file.

    Args:
        settings: The count, seed and hard-case rate to use. Required.
        out: The folder to write to; `[data] samples` if None.

    Returns:
        The path of cases.jsonl.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
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
    """Generates the set the settings describe, or one --out folder."""
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
