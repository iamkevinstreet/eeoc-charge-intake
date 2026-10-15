"""Test setup: offline provider, a temporary log directory and a small set of generated sample documents.

The environment is set here, before any eeoc_intake module is imported, because the service reads it at
import time.
"""

from __future__ import annotations

import json
import os
import random
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="eeoc-tests-"))
os.environ["LLM_PROVIDER"] = "fake"
os.environ["LLM_MODEL"] = "fake-model"
os.environ["LOG_DIR"] = str(_TMP / "logs")
os.environ["EEOC_SAMPLES_DIR"] = str(_TMP / "samples")
os.environ["EEOC_RESULTS_DIR"] = str(_TMP / "results")

import pytest  # noqa: E402
from kds.synthetic.names import NameGen  # noqa: E402

from eeoc_intake.generate import make_one  # noqa: E402


@pytest.fixture(scope="session")
def samples_dir() -> Path:
    out = Path(os.environ["EEOC_SAMPLES_DIR"])
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(7)
    gen = NameGen(seed=7)
    cases = [make_one(i, rng, gen, out) for i in range(10)]  # i=4 and i=9 are hard cases
    with (out / "cases.jsonl").open("w", encoding="utf-8") as fh:
        for c in cases:
            fh.write(json.dumps(c) + "\n")
    return out
