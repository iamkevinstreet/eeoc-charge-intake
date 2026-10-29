########################################################################
#                       backend/tests/support.py                       #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Holds the helpers the tests share: the repository root, settings that
write only to a test's own folder, a started client, a model that
always gives the same answer, and the made-up runs the dashboard tests
draw.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import copy
import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

# Third-party
from fastapi.testclient import TestClient
from kds.args import required
from kds.llm import ModelAdapter
from kds.llm.fake import FakeProvider
from kds.logs import get_logger

# Local
from eeoc_intake.api.app import create_app
from eeoc_intake.config import AppSettings

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Finds the repository root, two folders above this file")
REPO = Path(__file__).resolve().parents[2]
# log.debug("Sets the address the test client calls, which the host check allows")
LOCAL = "http://127.0.0.1"
# log.debug("Sets a live run of two documents; the second misses its charge number")
RUN: dict[str, Any] = {
    "name": "t",
    "model": "fake-model",
    "provider": "fake",
    "started_at": "2026-10-15T00:00:00+00:00",
    "finished_at": "2026-10-15T00:00:01+00:00",
    "prices_as_of": "2026-10-15",
    "cases": 2,
    "failures": 0,
    "summary": {
        "field_accuracy": 0.95,
        "unsupported_rate": 0.05,
        "latency_p50_ms": 10,
        "latency_p95_ms": 12,
    },
    "results": [
        {
            "case_id": "charge-000",
            "tags": ["clean"],
            "ok": True,
            "scores": {
                "field_accuracy": 1.0,
                "f_charge_number": 1,
                "f_bases": 1,
                "values": {},
                "gold": {},
                "removed": [],
            },
            "error": None,
            "latency_ms": 10,
            "cost_usd": 0.001,
            "calls": 1,
        },
        {
            "case_id": "charge-004",
            "tags": ["missing_number"],
            "ok": True,
            "scores": {
                "field_accuracy": 0.9,
                "f_charge_number": 0,
                "f_bases": 1,
                "values": {"charge_number": "x"},
                "gold": {"charge_number": None},
                "removed": [],
            },
            "error": None,
            "latency_ms": 12,
            "cost_usd": 0.002,
            "calls": 1,
        },
    ],
}


########################################################################
#                             Test helpers                             #
########################################################################
# log.debug("Defines settings that read the samples and write to a temp folder")
def make_settings(
    tmp: Path | None = None, samples: Path | None = None, **overrides: Any
) -> AppSettings:
    """Returns settings that write only under `tmp`.

    Args:
        tmp: The test's own folder, under which everything is
            written. Required.
        samples: The folder of generated samples to read. Required.
        **overrides: Settings to change, by field name.

    Returns:
        The settings, offline unless overridden.
    """
    # log.debug("Takes the test's folder, which the caller must give")
    tmp = required(tmp=tmp)
    # log.debug("Takes the samples, which the caller must give")
    samples = required(samples=samples)
    # log.debug("Returns the settings, offline unless overridden")
    return AppSettings(
        **{
            "llm_provider": "fake",
            "data_samples": samples,
            "data_results": tmp / "results",
            "data_smoke": tmp / "smoke",
            "data_extractions": tmp / "extractions",
            "data_export": tmp / "export",
            "log_dir": tmp / "logs",
            "ui_dist": tmp / "no-ui",
            **overrides,
        }
    )


# log.debug("Defines a started test client")
@contextmanager
def started(
    settings: AppSettings | None = None, adapter: ModelAdapter | None = None
) -> Iterator[TestClient]:
    """Yields a started client addressed to this machine.

    Args:
        settings: The settings to start the app with. Required.
        adapter: The model to call; None builds one from the settings.

    Yields:
        The client, with the app started.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Starts the app and yields the client")
    with TestClient(create_app(settings, adapter=adapter), base_url=LOCAL) as client:
        # log.debug("Yields it")
        yield client


# log.debug("Defines a model that always gives the same answer")
def scripted(settings: AppSettings | None = None, answer: str | None = None) -> ModelAdapter:
    """Returns an adapter whose model answers `answer` every time.

    Args:
        settings: The settings the adapter reads its budget from.
            Required.
        answer: What the model answers to every prompt. Required.

    Returns:
        The adapter.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Takes the answer, which the caller must give")
    answer = required(answer=answer)
    # log.debug("Returns the adapter, with no waits between retries")
    return ModelAdapter(
        FakeProvider(responder=lambda _: answer),
        model="scripted",
        settings=settings,
        sleep=lambda _: None,
    )


# log.debug("Defines a live folder holding the one run")
def one_run(tmp_path: Path | None = None) -> Path:
    """Writes RUN as the only live run, and returns the live folder.

    Args:
        tmp_path: The test's temporary folder. Required.

    Returns:
        The live folder.
    """
    # log.debug("Takes the test's folder, which the caller must give")
    tmp_path = required(tmp_path=tmp_path)
    # log.debug("Makes the live folder")
    live = tmp_path / "live"
    # log.debug("Creates it")
    live.mkdir()
    # log.debug("Writes the run")
    (live / "t-1.json").write_text(json.dumps(RUN), encoding="utf-8")
    # log.debug("Returns the folder")
    return live


# log.debug("Defines a live folder holding two runs an hour apart")
def two_runs(tmp_path: Path | None = None) -> Path:
    """Writes RUN and a later run that is more often right and dearer.

    The later run, an hour after, gets charge-004's charge number right.

    Args:
        tmp_path: The test's temporary folder. Required.

    Returns:
        The live folder, holding both runs.
    """
    # log.debug("Takes the test's folder, which the caller must give")
    tmp_path = required(tmp_path=tmp_path)
    # log.debug("Copies the run")
    later = copy.deepcopy(RUN)
    # log.debug("Starts it an hour later")
    later["started_at"] = "2026-10-15T01:00:00+00:00"
    # log.debug("Gives it every field right and a higher cost")
    later["summary"] = {**RUN["summary"], "field_accuracy": 1.0, "cost_per_case_usd": 0.002}
    # log.debug("Gets the second document's charge number right")
    later["results"][1]["scores"]["f_charge_number"] = 1
    # log.debug("Makes the live folder")
    live = tmp_path / "live"
    # log.debug("Creates it")
    live.mkdir()
    # log.debug("Writes the earlier run, with its cost")
    (live / "t-1.json").write_text(
        json.dumps({**RUN, "summary": {**RUN["summary"], "cost_per_case_usd": 0.0015}}),
        encoding="utf-8",
    )
    # log.debug("Writes the later run")
    (live / "t-2.json").write_text(json.dumps(later), encoding="utf-8")
    # log.debug("Returns the folder")
    return live


# log.debug("Defines a live run of documents that are all right")
def write_run(
    live: Path | None = None,
    name: str | None = None,
    started: str | None = None,
    latencies_ms: list[int] | None = None,
    cost: float | None = None,
) -> None:
    """Writes a run with the given times and one cost per document.

    Args:
        live: The live folder, made if need be. Required.
        name: The run file's name, without .json. Required.
        started: When the run started, as an ISO time. Required.
        latencies_ms: Each document's time, in milliseconds. Required.
        cost: Every document's cost, in dollars. Required.
    """
    # log.debug("Takes the live folder, which the caller must give")
    live = required(live=live)
    # log.debug("Takes the run's name, which the caller must give")
    name = required(name=name)
    # log.debug("Takes the start time, which the caller must give")
    started = required(started=started)
    # log.debug("Takes the times, which the caller must give")
    latencies_ms = required(latencies_ms=latencies_ms)
    # log.debug("Takes the cost, which the caller must give")
    cost = required(cost=cost)
    # log.debug("Copies the run")
    run = copy.deepcopy(RUN)
    # log.debug("Sets its start")
    run["started_at"] = started
    # log.debug("Takes the first document as the pattern")
    base = run["results"][0]
    # log.debug("Makes one document per time")
    run["results"] = [
        {**copy.deepcopy(base), "case_id": f"charge-{i:03d}", "latency_ms": ms, "cost_usd": cost}
        for i, ms in enumerate(latencies_ms)
    ]
    # log.debug("Counts the documents")
    run["cases"] = len(latencies_ms)
    # log.debug("Writes the summary to match")
    run["summary"] = {
        **RUN["summary"],
        "field_accuracy": 1.0,
        "latency_p50_ms": sorted(latencies_ms)[len(latencies_ms) // 2],
        "cost_per_case_usd": cost,
    }
    # log.debug("Makes the live folder if it is not there yet")
    live.mkdir(exist_ok=True)
    # log.debug("Writes the run")
    (live / f"{name}.json").write_text(json.dumps(run), encoding="utf-8")
