"""Cut 9: resume and reconstruction, in-process (the continuity machinery and local reconstruction correctness).
Nothing here is the cut-10 witness and none of it may be cited as CPOC evidence: it does not cross a process
boundary, and an uninterrupted-versus-resumed comparison inside one interpreter is only a cheap guard."""

import gc
import inspect
import json
import os
import weakref

import pytest

from elevator import api, checkpoint as C, operations
from elevator.domain import Configuration, canonical_json
from elevator.engine import Engine, EngineState
from elevator.policies import make_policy
from tests.cpoc import fixture as X
from tests.cpoc.fixture import fx  # noqa: F401


def run_uninterrupted(rows, floors, elevators, capacity, **kw):
    return api.simulate(rows, elevators, floors, capacity, **kw)


def log_of(store, eid):
    return operations.read_log(os.path.join(store, eid, "operational.jsonl"))


def test_reconstruction_equals_the_pre_checkpoint_state(fx):
    """Snapshot, current state and reconstructed state are value-equivalent at the boundary (a local check)."""
    live_state, live_passengers, live_history = fx.live.state, fx.live.passengers, fx.live.history
    loaded = C.load(fx.store, fx.execution_id)
    assert loaded.state == live_state and loaded.state.t == X.T and loaded.constructed_state_hash == loaded.snapshot_hash
    resumed = C.resume(fx.store, fx.execution_id)
    e = resumed.engine
    assert (e.t, e.standing, e.outcome) == (X.T, "RUNNING", None)
    assert e.state == live_state and e.passengers == live_passengers and e.elevators == fx.live.elevators
    assert canonical_json(e.history) == canonical_json(live_history)  # attached without transformation
    # deterministic next behaviour: the same next ticks from both engines
    for _ in range(3):
        fx.live.step()
        e.step()
        assert e.state == fx.live.state and e.history.tick_records[-1] == fx.live.history.tick_records[-1]
        assert e.history.events == fx.live.history.events
    assert type(resumed.writer) is C.CheckpointWriter and resumed.writer.last_known == 1


def test_checkpoint_at_zero_reconstructs_initial_floors(tmp_path):
    store = os.path.join(str(tmp_path), "S")
    C.init_store(store)
    live = api.create_engine(X.trace_rows(), X.N, X.F, X.C, initial_floors=[0, 4, 9], policy="round_robin")
    writer = C.CheckpointWriter(store, live.execution, live.run_identity, live._config, live._trace)
    outcome = C.drive(live, writer, C.Controls(checkpoint_at=0))
    doc = json.loads(open(C.document_path(store, live.execution.execution_id), "rb").read())
    assert outcome.standing == "COMPLETED" and doc["standing"] == "COMPLETED"  # finality followed the t = 0 write
    # recreate the t = 0 document and reconstruct from it
    other = api.create_engine(X.trace_rows(), X.N, X.F, X.C, initial_floors=[0, 4, 9], policy="round_robin")
    w2 = C.CheckpointWriter(store, other.execution, other.run_identity, other._config, other._trace)
    w2.checkpoint(other)
    d0 = json.loads(open(C.document_path(store, other.execution.execution_id), "rb").read())
    assert d0["snapshot"]["t"] == 0 and d0["simulation_history"]["events"] == [] == d0["simulation_history"]["tick_records"]
    assert [(e["floor"], e["heading"]) for e in d0["snapshot"]["elevators"]] == [(0, "NONE"), (4, "NONE"), (9, "NONE")]
    assert d0["snapshot"]["passengers"] == []
    resumed = C.resume(store, other.execution.execution_id)
    assert [(e.floor, e.heading.value) for e in resumed.engine.elevators] == [(0, "NONE"), (4, "NONE"), (9, "NONE")]
    assert resumed.engine.t == 0 and resumed.engine.passengers == ()
    C.drive(resumed.engine, resumed.writer, C.Controls(), skip_boundary=0)
    ref = run_uninterrupted(X.trace_rows(), X.F, 3, X.C, policy="round_robin", initial_floors=[0, 4, 9])
    assert canonical_json(resumed.engine.history) == canonical_json(ref.record.history)


def test_checkpoint_roundtrip_property_NOT_CPOC_EVIDENCE(tmp_path):
    """A cheap in-process guard (testing_contract §5): for random boundaries, policies and Traces, resuming from
    a document and continuing reproduces the uninterrupted Simulation History. Not CPOC evidence."""
    state = 31337

    def nxt(k):
        nonlocal state
        state = (state * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        return (state >> 33) % k

    cases = 0
    for case in range(40):
        floors, elevators, capacity = 3 + nxt(8), 1 + nxt(3), 1 + nxt(3)
        rows = []
        for i in range(2 + nxt(12)):
            o = nxt(floors)
            rows.append((nxt(20), f"r{i}", o, (o + 1 + nxt(floors - 1)) % floors))
        policy = ("round_robin", "nearest_car", "cost_based")[case % 3]
        ref = run_uninterrupted(rows, floors, elevators, capacity, policy=policy)
        t = nxt(ref.final_tick + 1)
        store = os.path.join(str(tmp_path), f"S{case}")
        C.init_store(store)
        live = api.create_engine(rows, elevators, floors, capacity, policy=policy)
        writer = C.CheckpointWriter(store, live.execution, live.run_identity, live._config, live._trace)
        while live.t < t and live.outcome is None:
            live.step()
        if live.outcome is not None:
            continue
        writer.checkpoint(live)
        resumed = C.resume(store, live.execution.execution_id)
        C.drive(resumed.engine, resumed.writer, C.Controls(), skip_boundary=t)
        assert canonical_json(resumed.engine.history) == canonical_json(ref.record.history), (case, t)
        assert resumed.engine.passengers == ref.record.passengers
        cases += 1
    assert cases >= 25


def executed_ticks(monkeypatch):
    seen: list[int] = []
    original = Engine._tick

    def spy(self, t, passengers, elevators, events):
        seen.append(t)
        return original(self, t, passengers, elevators, events)

    monkeypatch.setattr(Engine, "_tick", spy)
    return seen


def replay_from_zero_resume(store, execution_id):
    """A deliberately CHEATING resume: it ignores the snapshot's authority and re-runs the Run from tick 0 until
    the checkpointed tick. This is what constitution N14 prohibits, built here only to prove it is detected."""
    loaded = C.load(store, execution_id)
    cfg = loaded.configuration
    engine = Engine.create(cfg, loaded.trace, make_policy(cfg.policy, cfg.policy_params))
    while engine.t < loaded.state.t:
        engine.step()
    return engine


def test_resume_does_not_replay_from_tick_zero(fx, monkeypatch):
    seen = executed_ticks(monkeypatch)
    resumed = C.resume(fx.store, fx.execution_id)
    assert seen == []  # reconstruction executes no tick at all
    resumed.engine.step()
    resumed.engine.step()
    assert seen == [X.T, X.T + 1]  # the first tick executed is the checkpointed tick, never an earlier one
    # negative control: a replay-from-zero resume executes ticks 0..11, and the same spy sees it
    seen.clear()
    replay_from_zero_resume(fx.store, fx.execution_id)
    assert seen == list(range(X.T)) and min(seen) == 0
    assert any(t < X.T for t in seen)  # this is exactly what the assertion above forbids for the real resume


def test_resume_does_not_touch_the_scheduler_or_reveal_path_before_the_boundary(fx, monkeypatch):
    calls: list[int] = []
    real = make_policy("cost_based", Configuration.create(X.F, X.N, X.C, policy="cost_based").policy_params)
    original_assign = type(real).assign

    def spy(self, view, request):
        calls.append(view.t)
        return original_assign(self, view, request)

    monkeypatch.setattr(type(real), "assign", spy)
    resumed = C.resume(fx.store, fx.execution_id)
    assert calls == []  # no request was re-revealed or re-assigned during reconstruction
    C.drive(resumed.engine, resumed.writer, C.Controls(), skip_boundary=X.T)
    assert calls and min(calls) >= X.T  # only requests revealed at or after the boundary are ever assigned


def test_policy_is_rebuilt_through_the_one_resolver(tmp_path, monkeypatch):
    for policy, params in (("cost_based", {"w_tail": 5, "age_scale": 2}), ("cost_based", None), ("round_robin", None),
                           ("nearest_car", None)):
        store = os.path.join(str(tmp_path), f"S-{policy}-{bool(params)}")
        C.init_store(store)
        live = api.create_engine(X.trace_rows(), X.N, X.F, X.C, policy=policy, policy_params=params)
        writer = C.CheckpointWriter(store, live.execution, live.run_identity, live._config, live._trace)
        while live.t < 6:
            live.step()
        writer.checkpoint(live)
        calls = []
        real = C.make_policy
        monkeypatch.setattr(C, "make_policy", lambda name, p=None: calls.append((name, dict(p or {}))) or real(name, p))
        resumed = C.resume(store, live.execution.execution_id)
        monkeypatch.setattr(C, "make_policy", real)
        cfg = live._config
        assert calls == [(cfg.policy, dict(cfg.policy_params))]  # exactly one construction, from name and parameters
        assert resumed.engine._policy == live._policy  # an identical pure, stateless object: nothing to restore


# --- the Operational Log across binding, checkpoints and resumes -------------------------------------------

def test_operational_log_flush_at_binding(tmp_path):
    """cpoc §6 row 33: a live Execution (no output directory) steps to tick 5 with witness instrumentation, then
    takes its first explicit checkpoint into a Store: the buffer is flushed once, in order, before the receipt."""
    store = os.path.join(str(tmp_path), "S")
    C.init_store(store)
    live = api.create_engine(X.trace_rows(), X.N, X.F, X.C)
    C.instrument(live, live.execution)
    for _ in range(5):
        live.step()
    root = os.path.join(store, live.execution.execution_id)
    assert not os.path.exists(root) and not live.execution.log.bound  # in memory until the first checkpoint
    assert [r.op_seq for r in live.execution.log.records] == [1, 2, 3, 4, 5, 6]
    writer = C.CheckpointWriter(store, live.execution, live.run_identity, live._config, live._trace)
    writer.checkpoint(live)
    records = log_of(store, live.execution.execution_id)
    assert [(r["op_seq"], r["kind"], r["tick"]) for r in records] == [
        (1, "EXECUTION_STARTED", None), (2, "DIAGNOSTIC", 0), (3, "DIAGNOSTIC", 1), (4, "DIAGNOSTIC", 2),
        (5, "DIAGNOSTIC", 3), (6, "DIAGNOSTIC", 4), (7, "CHECKPOINT_WRITTEN", 5)]
    assert len({r["op_seq"] for r in records}) == len(records)  # no record duplicated
    # a repeated binding does not duplicate the flushed prefix
    with pytest.raises(operations.OperationsError):
        live.execution.log.bind_evidence_root(root)
    assert [r["op_seq"] for r in log_of(store, live.execution.execution_id)] == [1, 2, 3, 4, 5, 6, 7]
    # a later resume continues op_seq from the file
    live.execution.log.close()
    resumed = C.resume(store, live.execution.execution_id)
    assert resumed.execution.log.next_op_seq == 11
    assert [r["op_seq"] for r in log_of(store, live.execution.execution_id)] == list(range(1, 11))


def test_operational_log_op_seq_continuous(tmp_path):
    """op_seq starts at 1 and is contiguous across the in-memory period, the flush, two checkpoints and two
    resumes (in-process), with no duplicate record."""
    store = os.path.join(str(tmp_path), "S")
    C.init_store(store)
    live = api.create_engine(X.trace_rows(), X.N, X.F, X.C)
    C.instrument(live, live.execution)
    eid = live.execution.execution_id
    writer = C.CheckpointWriter(store, live.execution, live.run_identity, live._config, live._trace)
    for _ in range(3):
        live.step()  # in-memory period
    writer.checkpoint(live)  # flush + first checkpoint
    for _ in range(4):
        live.step()
    writer.checkpoint(live)  # second checkpoint
    live.execution.log.close()
    first = C.resume(store, eid)  # first resume
    C.instrument(first.engine, first.execution)
    for _ in range(3):
        first.engine.step()
    first.writer.checkpoint(first.engine)  # third write, by the resumed process
    first.execution.log.close()
    second = C.resume(store, eid)  # a second death and a second resume: the same procedure again
    C.instrument(second.engine, second.execution)
    C.drive(second.engine, second.writer, C.Controls(), skip_boundary=second.loaded.state.t)
    second.execution.log.append(__import__("elevator.domain", fromlist=["x"]).OperationalRecordKind.EXECUTION_ENDED)
    second.execution.log.close()
    records = log_of(store, eid)
    assert [r["op_seq"] for r in records] == list(range(1, len(records) + 1))  # contiguous, no gap, no duplicate
    kinds = [r["kind"] for r in records]
    assert kinds[0] == "EXECUTION_STARTED" and kinds.count("EXECUTION_STARTED") == 3  # one per process
    assert kinds.count("CHECKPOINT_WRITTEN") == 3 and kinds.count("LOAD_ADMITTED") == 2 == kinds.count("RESUMED")
    assert kinds[-2:] == ["FINALITY_WRITTEN", "EXECUTION_ENDED"]
    # write_sequence advanced exactly once per admitted write, through every resume
    seqs = [r["payload"]["write_sequence"] for r in records if r["kind"] in ("CHECKPOINT_WRITTEN", "FINALITY_WRITTEN")]
    assert seqs == [1, 2, 3, 4]
    # ticks are never executed twice: the diagnostics name each tick once, in order
    ticks = [r["tick"] for r in records if r["kind"] == "DIAGNOSTIC"]
    assert ticks == sorted(set(ticks)) and ticks[0] == 0


def test_load_admitted_receipt_evidence(fx):
    receipt = next(r for r in log_of(fx.store, fx.execution_id) if r["kind"] == "CHECKPOINT_WRITTEN")
    resumed = C.resume(fx.store, fx.execution_id)
    resumed.execution.log.close()
    records = log_of(fx.store, fx.execution_id)
    tail = records[-3:]
    assert [r["kind"] for r in tail] == ["EXECUTION_STARTED", "LOAD_ADMITTED", "RESUMED"]
    loaded = next(r for r in records if r["kind"] == "LOAD_ADMITTED")
    p = loaded["payload"]
    assert p["document_sha256"] == receipt["payload"]["document_sha256"] == X.sha(fx.d12)  # the loaded bytes were written
    assert p["snapshot_hash"] == p["constructed_state_hash"] == receipt["payload"]["snapshot_hash"]  # value equality
    assert p["history_hash"] == receipt["payload"]["history_hash"]
    assert (p["execution_id"], p["store_id"]) == (fx.execution_id, fx.store_id)
    assert loaded["tick"] == X.T and records[-1]["tick"] == X.T  # RESUMED(t)
    assert p["code_identity"] == receipt["payload"]["code_identity"] and p["pid"] == os.getpid()


def test_independent_executions_same_run(fx, tmp_path):
    """cpoc §6 row 7: two Executions of one run_id in one Store, one final, the other resumable, with identical
    Simulation Histories."""
    other = X.build_d12(tmp_path)  # same Store, same inputs: a new Execution with its own document and log
    assert other.store == fx.store and other.execution_id != fx.execution_id
    assert fx.doc()["run_id"] == other.doc()["run_id"] and fx.doc()["execution_id"] != other.doc()["execution_id"]
    a = C.resume(fx.store, fx.execution_id)
    C.drive(a.engine, a.writer, C.Controls(), skip_boundary=X.T)  # e_A completes and is final
    assert X.refusal(fx.store, fx.execution_id).reason == "EXECUTION_FINAL"
    assert X.refusal(other.store, other.execution_id) is None  # e_C is untouched and resumable
    c = C.resume(other.store, other.execution_id)
    C.drive(c.engine, c.writer, C.Controls(), skip_boundary=X.T)
    assert canonical_json(a.engine.history) == canonical_json(c.engine.history)
    for ex in (fx, other):  # separate documents and separate logs
        assert os.path.isfile(C.document_path(ex.store, ex.execution_id))
        assert os.path.isfile(os.path.join(ex.store, ex.execution_id, "operational.jsonl"))
    assert [r["op_seq"] for r in log_of(fx.store, fx.execution_id)] != [] and \
        {r["execution_id"] for r in log_of(fx.store, fx.execution_id)} == {fx.execution_id}


def test_history_verifier_isolated(fx, monkeypatch):
    for name, member in inspect.getmembers(C.HistoryVerifier):
        if name.startswith("__") or not callable(member):
            continue
        ret = inspect.signature(member).return_annotation
        assert "Snapshot" not in str(ret) and "EngineState" not in str(ret) and "Engine" not in str(ret), name
        assert not any(w in name.lower() for w in ("snapshot", "construct", "to_state", "engine_state")), name
    assert not issubclass(C.HistoryVerifier, (C.Snapshot, EngineState, C.HistoryPrefix))
    # the loader discards it: no reference survives the load
    instances: list = []

    class Tracked(C.HistoryVerifier):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            instances.append(weakref.ref(self))

    monkeypatch.setattr(C, "HistoryVerifier", Tracked)
    loaded = C.load(fx.store, fx.execution_id)
    gc.collect()
    assert len(instances) == 1 and instances[0]() is None
    assert not any(isinstance(v, C.HistoryVerifier) for v in vars(loaded).values())
    assert not any(isinstance(o, C.HistoryVerifier) for o in gc.get_objects())


def test_construct_state_takes_exactly_one_snapshot(fx):
    sig = inspect.signature(C.construct_state)
    assert list(sig.parameters) == ["snapshot"] and "Snapshot" in str(sig.parameters["snapshot"].annotation)
    doc = fx.doc()
    snapshot = C.parse_snapshot(doc)
    state = C.construct_state(snapshot)
    assert isinstance(state, EngineState) and state.t == X.T
    history = C.parse_history(doc)
    for wrong in (history, list(history.events), tuple(history.tick_records), C.HistoryVerifier(
            Configuration.create(X.F, X.N, X.C), api.normalize_requests([], X.F)), state, doc, None):
        with pytest.raises(TypeError):
            C.construct_state(wrong)  # type: ignore[arg-type]
    # distinct types with no conversion
    assert type(snapshot) is C.Snapshot and type(history) is C.HistoryPrefix and C.Snapshot is not C.HistoryPrefix
    assert not hasattr(snapshot, "events") and not hasattr(history, "elevators") and not hasattr(history, "passengers")
    with pytest.raises(TypeError):
        Engine.restore(fx.live._config, fx.live._trace, fx.live._policy, history, fx.live.history)  # type: ignore[arg-type]
    # parse_snapshot reads the snapshot section and nothing else
    only = {"snapshot": doc["snapshot"]}
    assert C.parse_snapshot(only) == snapshot
    with pytest.raises(KeyError):
        C.parse_snapshot({"simulation_history": doc["simulation_history"]})
