"""Shared fixtures for the cut-9 continuity tests (testing_contract §7, cpoc §6).

The document ``D12`` is a Continuation Document written at the start of tick 12 of a bursty Run (seed 7) in a
10-floor, 3-car, capacity-4 building. The request count and horizon (25, 20) are test data chosen so that, for
both ``cost_based`` and ``round_robin``, at t = 12 there is at least one ONBOARD and one WAITING passenger, a
Request with request_time > 12, and a WAITING passenger with request_time + distance < 12 (row 24). They are
not a definition of the cut-10 witness fixture. Mutations here use an independent canonical writer and hash
implementation (hashlib and json), not the code under test."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass

import pytest

from elevator import api, checkpoint
from elevator.scenarios import Scenario, generate

F, N, C, T = 10, 3, 4, 12
SCENARIO = Scenario("bursty", {"num_requests": 25, "horizon": 20}, 7)


def trace_rows():
    return generate(SCENARIO, F, N, C).canonical_rows()


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def snapshot_hash_of(doc) -> str:
    return sha(canonical({k: v for k, v in doc["snapshot"].items() if k != "snapshot_hash"}))


def history_hash_of(doc) -> str:
    h = doc["simulation_history"]
    return sha(canonical({"events": h["events"], "tick_records": h["tick_records"]}))


def recompute_snapshot_hash(doc) -> None:
    doc["snapshot"]["snapshot_hash"] = snapshot_hash_of(doc)


def recompute_history_hash(doc) -> None:
    doc["simulation_history"]["history_hash"] = history_hash_of(doc)


@dataclass
class Fixture:
    store: str
    execution_id: str
    store_id: str
    path: str
    d12: bytes
    live: object
    writer: object

    def doc(self):
        return json.loads(self.d12)

    def put(self, doc_or_bytes, path=None):
        data = doc_or_bytes if isinstance(doc_or_bytes, bytes) else canonical(doc_or_bytes)
        with open(path or self.path, "wb") as fh:
            fh.write(data)

    def on_disk(self) -> bytes:
        with open(self.path, "rb") as fh:
            return fh.read()


def build_d12(tmp_path, policy: str = "cost_based", *, t: int = T, store_name: str = "S") -> Fixture:
    """Run the fixture to the boundary ``t`` in-process, write the checkpoint, and keep the bytes."""
    store = os.path.join(str(tmp_path), store_name)
    store_id = (checkpoint.read_store(store) if os.path.exists(os.path.join(store, checkpoint.STORE_FILE))
                else checkpoint.init_store(store))  # a second Execution may share an existing Store
    live = api.create_engine(trace_rows(), N, F, C, policy=policy)
    writer = checkpoint.CheckpointWriter(store, live.execution, live.run_identity, live._config, live._trace)
    while live.t < t:
        live.step()
    writer.checkpoint(live)
    path = checkpoint.document_path(store, live.execution.execution_id)
    with open(path, "rb") as fh:
        d12 = fh.read()
    return Fixture(store, live.execution.execution_id, store_id, path, d12, live, writer)


def refusal(store: str, execution_id: str):
    """The ``CheckpointRefusal`` a load raises, or ``None`` if it was admitted."""
    try:
        checkpoint.load(store, execution_id)
    except checkpoint.CheckpointRefusal as exc:
        return exc
    return None


def expect_refusal(fx: Fixture, reason: str, step: int) -> None:
    before = fx.on_disk()
    got = refusal(fx.store, fx.execution_id)
    assert got is not None, f"load was admitted; expected {reason} at step {step}"
    assert (got.reason, got.step) == (reason, step), (got.reason, got.step, str(got))
    assert fx.on_disk() == before  # the bad artifact is neither repaired nor overwritten


@pytest.fixture
def fx(tmp_path):
    return build_d12(tmp_path)
