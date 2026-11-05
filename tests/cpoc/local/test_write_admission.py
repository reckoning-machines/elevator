"""Cut 9: write admission, receipt ordering, atomic replace and finality (cpoc §3.2 to §3.4; cpoc §6 rows 9, 10),
all on the real Store path: two writers holding different tokens write to one document at one path."""

import json
import os

import pytest

from elevator import api, checkpoint as C, operations
from elevator.domain import Configuration
from elevator.engine import Engine
from elevator.policies import make_policy
from tests.cpoc import fixture as X
from tests.cpoc.fixture import fx  # noqa: F401


def log_of(fx):
    return operations.read_log(os.path.join(fx.store, fx.execution_id, "operational.jsonl"))


def second_engine(fx, steps):
    """Another engine of the same Run (as a stale or foreign holder might have), run for `steps` ticks."""
    cfg = fx.live._config
    e = Engine.create(cfg, fx.live._trace, make_policy(cfg.policy, cfg.policy_params))
    for _ in range(steps):
        e.step()
    return e


def test_write_admission_stale_writer(fx):
    """cpoc §6 row 9 exactly. A RUNNING document at write_sequence 1; writer A holds token 1 and performs an
    admitted checkpoint write, advancing it to 2 (A now holds token 2); writer B, an old holder of token 1, calls
    the write function against the still-RUNNING document: STALE_WRITER, and A's document is intact."""
    a, b_token = fx.writer, 1
    assert a.last_known == 1 and json.loads(fx.on_disk())["write_sequence"] == 1
    fx.live.step()  # tick 12 executes; the next boundary is 13
    receipt = a.checkpoint(fx.live)
    assert (receipt.write_sequence, a.last_known) == (2, 2)
    a_bytes, records_before = fx.on_disk(), len(log_of(fx))
    assert json.loads(a_bytes)["write_sequence"] == 2 and json.loads(a_bytes)["snapshot"]["t"] == 13
    stale_engine = second_engine(fx, 14)  # B is at a different boundary with different content
    with pytest.raises(C.CheckpointRefusal) as info:
        C.write_checkpoint(fx.store, fx.live.execution, fx.live.run_identity, fx.live._config, fx.live._trace,
                           stale_engine, token=b_token)
    assert info.value.reason == "STALE_WRITER" and info.value.step is None
    assert fx.on_disk() == a_bytes  # the durable state is still A's: no partial overwrite, no last-writer-wins
    assert not os.path.exists(os.path.join(fx.store, fx.execution_id, "run.json.tmp"))
    assert len(log_of(fx)) == records_before  # a rejected attempt is not admitted, so it leaves no receipt
    # B, as a writer object, halts itself and cannot retry around the refusal
    b = C.CheckpointWriter(fx.store, fx.live.execution, fx.live.run_identity, fx.live._config, fx.live._trace, token=1)
    with pytest.raises(C.CheckpointRefusal) as first:
        b.checkpoint(stale_engine)
    assert first.value.reason == "STALE_WRITER" and b.halted is first.value
    with pytest.raises(C.CheckpointRefusal) as again:
        b.checkpoint(stale_engine)
    assert again.value is first.value  # a halted writer re-raises, it does not look at the document again
    with pytest.raises(C.CheckpointRefusal):
        b.finalize(second_engine(fx, 3))
    assert fx.on_disk() == a_bytes
    # A can still write with its current token
    fx.live.step()
    assert a.checkpoint(fx.live).write_sequence == 3


def test_write_admission_after_final(fx):
    """cpoc §6 row 10 exactly. After the admitted finality write (write_sequence 2), a checkpoint write with the
    current token 2 (so the sequence matches) refuses WRITE_AFTER_FINAL: standing, not sequence, refuses."""
    while fx.live.outcome is None:
        fx.live.step()
    final = fx.writer.finalize(fx.live)
    assert final.write_sequence == 2
    final_bytes = fx.on_disk()
    doc = json.loads(final_bytes)
    assert (doc["standing"], doc["write_sequence"]) == ("COMPLETED", 2) and "snapshot" not in doc
    running = second_engine(fx, 5)  # a RUNNING engine of the same Run holding the current token
    with pytest.raises(C.CheckpointRefusal) as info:
        C.write_checkpoint(fx.store, fx.live.execution, fx.live.run_identity, fx.live._config, fx.live._trace,
                           running, token=2)
    assert info.value.reason == "WRITE_AFTER_FINAL"
    assert fx.on_disk() == final_bytes  # the final document is byte-identical
    with pytest.raises(C.CheckpointRefusal) as second_final:  # a second finality write is no different
        C.write_finality(fx.store, fx.live.execution, fx.live.run_identity, fx.live._config, fx.live._trace,
                         fx.live, token=2)
    assert second_final.value.reason == "WRITE_AFTER_FINAL" and fx.on_disk() == final_bytes
    # and the writer object halts itself on the same refusal
    with pytest.raises(C.CheckpointRefusal) as via_writer:
        fx.writer.checkpoint(running)
    assert via_writer.value.reason == "WRITE_AFTER_FINAL" and fx.writer.halted is via_writer.value
    assert fx.on_disk() == final_bytes
    assert X.refusal(fx.store, fx.execution_id).reason == "EXECUTION_FINAL"  # and load refuses it as final


def test_other_write_refusals_are_named_and_never_overwrite(fx):
    engine = second_engine(fx, 13)
    original = fx.on_disk()
    common = (fx.store, fx.live.execution, fx.live.run_identity, fx.live._config, fx.live._trace, engine)
    # the writer has no token but a document exists; or the writer holds a token that is ahead of the document
    for token in (None, 5):
        with pytest.raises(C.CheckpointRefusal) as info:
            C.write_checkpoint(*common, token=token)
        assert info.value.reason == "STALE_WRITER" and fx.on_disk() == original
    # a document that belongs to another Execution
    doc = fx.doc()
    doc["execution_id"] = "someone-else"
    fx.put(doc)
    other = fx.on_disk()
    with pytest.raises(C.CheckpointRefusal) as info:
        C.write_checkpoint(*common, token=1)
    assert info.value.reason == "EXECUTION_MISMATCH" and fx.on_disk() == other
    # a document that does not parse is refused, not replaced
    fx.put(b"{ not json")
    with pytest.raises(C.CheckpointRefusal) as info:
        C.write_checkpoint(*common, token=1)
    assert info.value.reason == "MALFORMED" and fx.on_disk() == b"{ not json"
    # the first write of an Execution needs no token and starts at 1
    os.remove(fx.path)
    assert C.write_checkpoint(*common, token=None).write_sequence == 1
    # a token with no document at the path is the writer's view disagreeing with the path
    os.remove(fx.path)
    with pytest.raises(C.CheckpointRefusal) as info:
        C.write_checkpoint(*common, token=1)
    assert info.value.reason == "STALE_WRITER"


def test_receipt_hash_matches_path(fx):
    """The document's SHA-256 in CHECKPOINT_WRITTEN equals the bytes at the path (cpoc §3.2): it is the hash of
    the bytes read back after the rename, not of an object held before the write."""
    records = log_of(fx)
    receipt = next(r for r in records if r["kind"] == "CHECKPOINT_WRITTEN")
    doc = fx.doc()
    assert receipt["payload"]["document_sha256"] == X.sha(fx.on_disk())
    assert receipt["payload"]["snapshot_hash"] == doc["snapshot"]["snapshot_hash"] == X.snapshot_hash_of(doc)
    assert receipt["payload"]["history_hash"] == doc["simulation_history"]["history_hash"] == X.history_hash_of(doc)
    assert (receipt["payload"]["write_sequence"], receipt["tick"]) == (1, X.T)
    assert receipt["payload"]["code_identity"] == doc["code_identity"] and receipt["payload"]["pid"] == os.getpid()
    # receipt ordering: EXECUTION_STARTED (flushed at binding) precedes it; nothing follows it yet
    assert [r["kind"] for r in records] == ["EXECUTION_STARTED", "CHECKPOINT_WRITTEN"]
    # the finality receipt carries no snapshot hash (the snapshot is removed) and the final document's hash
    while fx.live.outcome is None:
        fx.live.step()
    fx.writer.finalize(fx.live)
    final = log_of(fx)[-1]
    assert final["kind"] == "FINALITY_WRITTEN" and final["payload"]["snapshot_hash"] is None
    assert final["payload"]["document_sha256"] == X.sha(fx.on_disk()) and final["payload"]["write_sequence"] == 2
    assert final["tick"] == json.loads(fx.on_disk())["final"]["final_tick"]


def test_a_failed_replace_leaves_the_previous_document_and_no_receipt(fx, monkeypatch):
    original, records = fx.on_disk(), len(log_of(fx))
    fx.live.step()
    real_replace = os.replace

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        fx.writer.checkpoint(fx.live)
    monkeypatch.setattr(os, "replace", real_replace)
    tmp = os.path.join(fx.store, fx.execution_id, "run.json.tmp")
    assert fx.on_disk() == original  # never a document that falsely claims a newer sequence
    assert os.path.exists(tmp) and len(log_of(fx)) == records  # bytes in flight, no receipt
    assert fx.writer.last_known == 1 and fx.writer.halted is None  # an I/O failure is not a refusal
    assert X.refusal(fx.store, fx.execution_id) is None  # the stray temp file is never loaded
    receipt = fx.writer.checkpoint(fx.live)  # the next admitted write succeeds and removes the temp file
    assert receipt.write_sequence == 2 and not os.path.exists(tmp)


def test_finality_on_completion_and_on_halt_and_never_without_a_document(fx, tmp_path):
    # completion
    while fx.live.outcome is None:
        fx.live.step()
    fx.writer.finalize(fx.live)
    doc = json.loads(fx.on_disk())
    assert (doc["standing"], doc["write_sequence"], doc["final"]) == ("COMPLETED", 2, {"final_tick": fx.live.outcome.final_tick})
    assert "snapshot" not in doc and doc["simulation_history"]["events"][-1]["kind"] == "COMPLETED"
    assert len(doc["simulation_history"]["tick_records"]) == fx.live.outcome.final_tick + 1  # complete History
    # halt: a horizon halt after a checkpoint
    store = os.path.join(str(tmp_path), "H")
    C.init_store(store)
    live = api.create_engine(X.trace_rows(), X.N, X.F, X.C, policy="cost_based", max_ticks=15)
    writer = C.CheckpointWriter(store, live.execution, live.run_identity, live._config, live._trace)
    outcome = C.drive(live, writer, C.Controls(checkpoint_at=4))
    assert outcome.standing == "HALTED" and writer.last_known == 2
    halted = json.loads(open(C.document_path(store, live.execution.execution_id), "rb").read())
    assert halted["standing"] == "HALTED" and "snapshot" not in halted
    assert halted["final"] == {"final_tick": 15, "halt_step": "TERMINATE", "halt_reason": "HORIZON_EXCEEDED",
                               "halt_passenger": None}
    assert halted["simulation_history"]["events"][-1]["kind"] == "HALTED"
    got = X.refusal(store, live.execution.execution_id)
    assert (got.reason, got.step) == ("EXECUTION_FINAL", 7)  # a HALTED Run is final and is never resumed
    with pytest.raises(C.CheckpointRefusal) as info:
        writer.checkpoint(second_engine(fx, 3))
    assert info.value.reason == "WRITE_AFTER_FINAL"
    # an Execution that never wrote a document writes nothing at finality
    store2 = os.path.join(str(tmp_path), "N")
    C.init_store(store2)
    quiet = api.create_engine(X.trace_rows(), X.N, X.F, X.C, policy="round_robin")
    writer2 = C.CheckpointWriter(store2, quiet.execution, quiet.run_identity, quiet._config, quiet._trace)
    C.drive(quiet, writer2, C.Controls(checkpoint_at=10**6))  # a boundary the Run never reaches
    assert not writer2.has_document and os.listdir(store2) == ["store.json"]


def test_the_document_has_exactly_the_admitted_fields(fx):
    doc = fx.doc()
    assert set(doc) == {"schema_version", "store_id", "execution_id", "run_id", "code_identity", "configuration_hash",
                        "trace_hash", "write_sequence", "configuration", "trace", "standing", "final", "snapshot",
                        "simulation_history"}
    assert set(doc["snapshot"]) == {"t", "elevators", "passengers", "snapshot_hash"}
    assert set(doc["simulation_history"]) == {"events", "tick_records", "history_hash"}
    assert doc["final"] is None and doc["standing"] == "RUNNING" and doc["schema_version"] == 1
    assert set(doc["snapshot"]["elevators"][0]) == {"id", "floor", "heading"}
    assert set(doc["snapshot"]["passengers"][0]) == {"passenger_id", "source_id", "standing", "assigned_elevator",
                                                     "assigned_at", "pickup_time", "dropoff_time"}
    # the full Trace is embedded, including Requests that are still in the future
    assert doc["trace"] == X.trace_rows() and any(r[0] > X.T for r in doc["trace"])
    # no hash of itself, no Operational Record, no provenance, no timestamp, no execution metadata
    text = fx.d12.decode()
    for word in ("document_sha256", "op_seq", "CHECKPOINT_WRITTEN", "provenance", "started_at", "pid", "timestamp",
                 "git_sha", "operational"):
        assert word not in text, word
    assert fx.d12 == X.canonical(doc)  # canonical bytes: sorted keys, no whitespace, integers only


def test_snapshot_bytes_are_deterministic_and_immutable(fx, tmp_path):
    twin = X.build_d12(tmp_path, store_name="S2")  # a second Execution of the same Run, same boundary
    a, b = fx.doc(), twin.doc()
    assert a["snapshot"] == b["snapshot"] and a["simulation_history"] == b["simulation_history"]
    assert a["execution_id"] != b["execution_id"]  # only the Execution's own identity differs
    loaded = C.load(fx.store, fx.execution_id)
    assert isinstance(loaded.state.elevators, tuple) and isinstance(loaded.state.passengers, tuple)
    with pytest.raises(Exception):
        loaded.state.t = 99  # type: ignore[misc]
    snap = C.parse_snapshot(a)
    assert type(snap) is C.Snapshot
    with pytest.raises(Exception):
        snap.t = 1  # type: ignore[misc]
    a["snapshot"]["t"] = 999  # the parsed value holds no reference to the caller's dictionaries
    assert snap.t == X.T


def test_a_write_needs_a_valid_store(tmp_path):
    live = api.create_engine(X.trace_rows(), X.N, X.F, X.C)
    with pytest.raises(C.CheckpointRefusal) as info:
        C.CheckpointWriter(str(tmp_path / "nowhere"), live.execution, live.run_identity, live._config, live._trace)
    assert info.value.reason == "STORE_NOT_FOUND"
