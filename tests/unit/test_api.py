"""Cut 8 tests for the public boundaries (evaluation §2): simulate, create_engine, normalize_requests."""

import ast
import json
import os
import subprocess
import sys

import pytest

from elevator import api, operations, reporting
from elevator.domain import (
    OperationalRecord,
    OperationalRecordKind as K,
    Refusal,
    SimulationEventKind as E,
    canonical_json,
)
from elevator.engine import Engine
from tests.engine_fixtures import ByIdPolicy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
W_B = [(0, "p0", 0, 4), (0, "p1", 2, 4)]


def lines(path):
    with open(path, "rb") as fh:
        return [json.loads(ln) for ln in fh.read().split(b"\n") if ln]


def test_normalization_shared_by_batch_and_live():
    result = api.simulate(W_B, 1, 5, 1)
    live = api.create_engine(W_B, 1, 5, 1)
    # the same rows give the same Trace hash and the same Run identity through both boundaries
    assert live.run_identity.trace_hash == result.identity.trace_hash == result.record.trace.trace_hash
    assert live.run_identity.run_id == result.run_id
    # create_engine returns a RUNNING engine at t = 0 whose first step matches tick 0 of simulate's History
    assert isinstance(live, Engine) and (live.t, live.standing) == (0, "RUNNING")
    assert live.history.events == () and live.history.tick_records == ()
    live.step()
    assert live.history.tick_records[0] == result.record.history.tick_records[0]
    tick0 = [e for e in result.record.history.events if e.tick == 0]
    assert [(e.kind, e.passenger_id, e.elevator_id, e.floor) for e in live.history.events] == \
        [(e.kind, e.passenger_id, e.elevator_id, e.floor) for e in tick0]
    live.run()
    assert canonical_json(live.history) == canonical_json(result.record.history)  # one engine, two boundaries
    # row shapes, identical meaning: mappings, sequences, decimal-digit strings, integer ids
    mapped = [{"time": 0, "id": "p0", "source": 0, "dest": 4}, {"time": 0, "id": "p1", "source": 2, "dest": 4}]
    strings = [("0", "p0", "0", "4"), ("0", "p1", "2", "4")]
    assert api.simulate(mapped, 1, 5, 1).run_id == api.simulate(strings, 1, 5, 1).run_id == result.run_id
    assert api.normalize_requests(W_B, 5).trace_hash == result.identity.trace_hash


def test_simulate_returns_the_reproducible_surface_and_summary():
    result = api.simulate(W_B, 1, 5, 1)
    assert (result.standing, result.final_tick, result.halt_reason) == ("COMPLETED", 8, None)
    assert tuple(result.surface) == reporting.SURFACE_FILES and result.output_path is None
    assert result.surface == reporting.reproducible_surface(result.record)
    assert result.summary["wait"]["max"] == 6 and result.summary["n"] == 2
    # the defaults: cost_based with the defaults of scheduler §6.3, initial floors 0
    ident = json.loads(result.surface["run_identity.json"])
    assert ident["policy"]["name"] == "cost_based" and ident["configuration"]["initial_floors"] == [0]
    assert ident["policy"]["params"] == {"age_scale": 4, "tail_threshold": 8, "w_marginal": 1, "w_tail": 3, "w_wait": 1}
    # each policy by name, through the one resolver
    for name in ("round_robin", "nearest_car", "cost_based"):
        r = api.simulate(W_B, 2, 5, 1, policy=name)
        assert r.standing == "COMPLETED" and json.loads(r.surface["run_identity.json"])["policy"]["name"] == name
    custom = api.simulate(W_B, 1, 5, 1, policy_params={"w_tail": 9})
    assert custom.run_id != result.run_id and json.loads(custom.surface["run_identity.json"])["policy"]["params"]["w_tail"] == 9


def test_invalid_input_and_configuration_refuse_before_any_execution(monkeypatch):
    def no_execution(*a, **k):
        raise AssertionError("an Execution was created for an invalid request")

    monkeypatch.setattr(api, "start_execution", no_execution)
    cases = [
        (dict(request_rows=[(0, "a", 2, 2)], num_elevators=1, num_floors=5, capacity=1), "SAME_FLOOR_REQUEST"),
        (dict(request_rows=[(0, "", 0, 1)], num_elevators=1, num_floors=5, capacity=1), "MISSING_SOURCE_ID"),
        (dict(request_rows=[(0, "a", 0, 1), (1, "a", 1, 0)], num_elevators=1, num_floors=5, capacity=1), "DUPLICATE_SOURCE_ID"),
        (dict(request_rows=[(0, "a", 0, 9)], num_elevators=1, num_floors=5, capacity=1), "INPUT_INVALID"),
        (dict(request_rows=[(0, "a", 0)], num_elevators=1, num_floors=5, capacity=1), "INPUT_INVALID"),
        (dict(request_rows=W_B, num_elevators=0, num_floors=5, capacity=1), "INVALID_CONFIGURATION"),
        (dict(request_rows=W_B, num_elevators=1, num_floors=1, capacity=1), "INVALID_CONFIGURATION"),
        (dict(request_rows=W_B, num_elevators=1, num_floors=5, capacity=51), "INVALID_CONFIGURATION"),
        (dict(request_rows=W_B, num_elevators=1, num_floors=5, capacity=1, policy="lookahead"), "INVALID_CONFIGURATION"),
        (dict(request_rows=W_B, num_elevators=1, num_floors=5, capacity=1, policy="round_robin",
              policy_params={"w_wait": 1}), "INVALID_CONFIGURATION"),
        (dict(request_rows=W_B, num_elevators=1, num_floors=5, capacity=1, max_ticks=10**6), "INVALID_CONFIGURATION"),
        (dict(request_rows=W_B, num_elevators=1, num_floors=5, capacity=1, initial_floors=[9]), "INVALID_CONFIGURATION"),
    ]
    for kwargs, reason in cases:
        for fn in (api.simulate, api.create_engine):  # both boundaries refuse alike
            with pytest.raises(Refusal) as info:
                fn(**{k: v for k, v in kwargs.items() if fn is api.simulate or k != "output_dir"})
            assert info.value.reason == reason, (kwargs, info.value)
    # the refusal of a duplicate id names both row positions
    with pytest.raises(Refusal) as info:
        api.simulate([(0, "a", 0, 1), (1, "a", 1, 0)], 1, 5, 1)
    assert info.value.positions == (0, 1)


def test_a_halted_run_is_reported_as_halted_not_completed(monkeypatch):
    horizon = api.simulate([(0, "a", 0, 4)], 1, 5, 2, max_ticks=2)
    assert (horizon.standing, horizon.halt_reason) == ("HALTED", "HORIZON_EXCEEDED")
    assert horizon.summary == {"standing": "HALTED", "final_tick": 2, "halt_reason": "HORIZON_EXCEEDED",
                               "n": 1, "completed": 0, "unserved": 1}
    assert horizon.record.history.events[-1].kind is E.HALTED and horizon.surface["observations.md"].startswith(b"Run halted")

    class Raises:
        def assign(self, view, request):
            raise RuntimeError("boom")

    monkeypatch.setattr(api, "make_policy", lambda name, params=None: Raises())
    failed = api.simulate(W_B, 1, 5, 1)  # a policy error halts the Run; the function returns, it does not raise
    assert (failed.standing, failed.halt_reason) == ("HALTED", "POLICY_ERROR")
    kinds = [r.kind for r in failed.execution.log.records]
    assert kinds[0] is K.EXECUTION_STARTED and kinds[-1] is K.EXECUTION_ENDED  # the Execution still ended cleanly


def test_output_is_written_exactly_and_never_over_existing_evidence(tmp_path):
    a = api.simulate(W_B, 1, 5, 1, output_dir=str(tmp_path))
    root = os.path.join(str(tmp_path), a.run_id, a.execution_id)
    assert a.output_path == root
    assert sorted(os.listdir(root)) == sorted(set(reporting.SURFACE_FILES) | {"execution_metadata.json", "operational.jsonl"})
    for name, data in a.surface.items():
        with open(os.path.join(root, name), "rb") as fh:
            assert fh.read() == data  # exactly as generated: no line-ending change, no timestamp, no id
    log = lines(os.path.join(root, "operational.jsonl"))
    assert [r["op_seq"] for r in log] == [1, 2] and [r["kind"] for r in log] == ["EXECUTION_STARTED", "EXECUTION_ENDED"]
    meta = json.loads(open(os.path.join(root, "execution_metadata.json"), "rb").read())
    assert meta["execution_id"] == a.execution_id and meta["run_id"] == a.run_id and meta["standing"] == "COMPLETED"
    assert meta["pid"] == os.getpid() and meta["started_at"] <= meta["ended_at"]
    # a second Execution of the same Run lands beside the first and leaves it untouched
    snapshot = {n: open(os.path.join(root, n), "rb").read() for n in os.listdir(root)}
    b = api.simulate(W_B, 1, 5, 1, output_dir=str(tmp_path))
    assert b.run_id == a.run_id and b.execution_id != a.execution_id and b.output_path != a.output_path
    assert {n: open(os.path.join(root, n), "rb").read() for n in os.listdir(root)} == snapshot
    for name in reporting.SURFACE_FILES:
        with open(os.path.join(root, name), "rb") as fa, open(os.path.join(b.output_path, name), "rb") as fb:
            assert fa.read() == fb.read(), name


def test_an_output_failure_is_its_own_error(tmp_path):
    blocker = tmp_path / "not_a_directory"
    blocker.write_text("x")
    with pytest.raises(api.OutputWriteError):
        api.simulate(W_B, 1, 5, 1, output_dir=str(blocker))
    # nothing was created or overwritten by the failed attempt
    assert blocker.read_text() == "x" and os.listdir(tmp_path) == ["not_a_directory"]


def test_never_bound_simulate_creates_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = api.simulate(W_B, 1, 5, 1)
    assert os.listdir(tmp_path) == [] and result.output_path is None and not result.execution.log.bound
    assert [r.kind for r in result.execution.log.records] == [K.EXECUTION_STARTED, K.EXECUTION_ENDED]


def test_operational_identity_never_reaches_the_run(tmp_path):
    a = api.simulate(W_B, 1, 5, 1, output_dir=str(tmp_path / "a"))
    b = api.simulate(W_B, 1, 5, 1, output_dir=str(tmp_path / "b"))
    assert a.execution_id != b.execution_id
    assert a.run_id == b.run_id and a.surface == b.surface
    assert canonical_json(a.record.history) == canonical_json(b.record.history)
    assert a.execution_id not in a.run_id and a.execution_id.encode() not in b"".join(a.surface.values())
    for name in ("execution_metadata.json", "operational.jsonl"):
        assert open(os.path.join(a.output_path, name), "rb").read() != open(os.path.join(b.output_path, name), "rb").read()


def test_code_identity_drift_is_recorded_before_the_execution_ends(monkeypatch):
    monkeypatch.setattr(api, "detect_code_identity_drift", lambda established, *, execution_id, op_seq: OperationalRecord(
        execution_id, op_seq, K.CODE_IDENTITY_DRIFT, None, {"established": "a" * 64, "at_exit": "b" * 64}))
    result = api.simulate(W_B, 1, 5, 1)
    assert [r.kind for r in result.execution.log.records] == [K.EXECUTION_STARTED, K.CODE_IDENTITY_DRIFT, K.EXECUTION_ENDED]
    assert [r.op_seq for r in result.execution.log.records] == [1, 2, 3]


def test_create_engine_is_live_with_its_own_in_memory_execution():
    a, b = api.create_engine(W_B, 1, 5, 1), api.create_engine(W_B, 1, 5, 1)
    assert a.execution.execution_id != b.execution.execution_id
    assert [r.kind for r in a.execution.log.records] == [K.EXECUTION_STARTED] and not a.execution.log.bound
    with pytest.raises(AttributeError):
        a.execution = None  # type: ignore[misc]
    # the base Engine is untouched: it knows nothing of operations
    plain = Engine.create(a._config, a._trace, ByIdPolicy())
    assert not hasattr(plain, "execution") and not hasattr(plain, "run_identity")
    assert a.run_identity.run_id == b.run_identity.run_id


def test_unsupported_environment_refuses_to_start(tmp_path):
    cache = tmp_path / "caches"  # keep this negative run from writing bytecode into the package
    env = {**os.environ, "PYTHONPATH": ROOT, "PYTHONPYCACHEPREFIX": str(cache)}
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    code = ("from elevator import api\nfrom elevator.domain import Refusal\n"
            "try:\n    api.simulate([(0,'a',0,2)],1,3,1)\nexcept Refusal as r:\n    print(r.reason)\nelse:\n    print('RAN')\n")
    refused = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=ROOT, check=True)
    assert refused.stdout.strip() == "UNSUPPORTED_EXECUTION_ENVIRONMENT"
    ran = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, env=env, cwd=ROOT, check=True)
    assert ran.stdout.strip() == "RAN"
    assert not os.path.isdir(os.path.join(ROOT, "elevator", "__pycache__"))


def test_api_dependencies_follow_the_table():
    with open(os.path.join(ROOT, "elevator", "api.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    mods |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert {m for m in mods if m.startswith("elevator")} == {
        "elevator", "elevator.domain", "elevator.engine", "elevator.operations", "elevator.policies",
        "elevator.reporting"}  # architecture §1 as amended by revision 7.3; never checkpoint, harness or cli
