"""Cut 8 tests for operations and the execution-output wrapper (cpoc §2.2a; architecture §1.1)."""

import ast
import json
import os
import re
import uuid

import pytest

from elevator import operations as O
from elevator import reporting as R
from elevator.domain import OperationalRecordKind as K, canonical_json
from tests.report_fixtures import run_record

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CODE = "c" * 64
W_B = [(0, "p0", 0, 4), (0, "p1", 2, 4)]


def lines(path):
    with open(path, "rb") as fh:
        return [json.loads(ln) for ln in fh.read().split(b"\n") if ln]


def test_execution_starts_with_execution_started_at_op_seq_one():
    ex = O.start_execution(CODE, pid=4242)
    (first,) = ex.log.records
    assert (first.op_seq, first.kind, first.execution_id) == (1, K.EXECUTION_STARTED, ex.execution_id)
    assert first.payload == {"code_identity": CODE, "pid": 4242} and first.tick is None
    assert not ex.log.bound and ex.log.path is None  # an in-memory buffer: no file, no root


def test_execution_id_is_a_random_uuid4_and_distinct_per_execution():
    ids = [O.start_execution(CODE).execution_id for _ in range(500)]
    assert len(set(ids)) == 500
    parsed = [uuid.UUID(i) for i in ids]
    assert all(u.version == 4 and str(u) == i for u, i in zip(parsed, ids))  # stdlib UUID v4, canonical text


def test_op_seq_is_contiguous_and_records_are_immutable():
    ex = O.start_execution(CODE)
    for n in range(5):
        ex.log.append(K.DIAGNOSTIC, tick=n, payload={"n": n})
    assert [r.op_seq for r in ex.log.records] == [1, 2, 3, 4, 5, 6] and ex.log.next_op_seq == 7
    record = ex.log.records[3]
    assert record.payload == {"code_identity": CODE, "pid": ex.pid, "n": 2} and record.tick == 2
    with pytest.raises(TypeError):
        record.payload["n"] = 9
    with pytest.raises(Exception):
        record.op_seq = 99
    # a record built elsewhere is accepted only as the log's very next record
    good = type(record)(ex.execution_id, 7, K.CODE_IDENTITY_DRIFT, None, {"x": 1})
    assert ex.log.append_record(good).op_seq == 7
    for bad in (type(record)(ex.execution_id, 7, K.DIAGNOSTIC), type(record)(ex.execution_id, 9, K.DIAGNOSTIC),
                type(record)("other", 8, K.DIAGNOSTIC)):
        with pytest.raises(O.OperationsError):
            ex.log.append_record(bad)


def test_flush_at_binding_writes_the_buffer_once_in_order(tmp_path):
    ex = O.start_execution(CODE)
    ex.log.append(K.DIAGNOSTIC, tick=0, payload={"i": 0})
    ex.log.append(K.DIAGNOSTIC, tick=1, payload={"i": 1})
    root = str(tmp_path / "run" / ex.execution_id)
    assert not os.path.exists(root)  # nothing exists until an evidence root is bound
    path = ex.log.bind_evidence_root(root)
    assert path == os.path.join(root, "operational.jsonl") and ex.log.bound and ex.log.evidence_root == root
    assert [(r["op_seq"], r["kind"]) for r in lines(path)] == [(1, "EXECUTION_STARTED"), (2, "DIAGNOSTIC"), (3, "DIAGNOSTIC")]
    ex.log.append(K.EXECUTION_ENDED)  # later records are appended directly
    ex.log.append(K.DIAGNOSTIC, payload={"late": True})
    written = lines(path)
    assert [r["op_seq"] for r in written] == [1, 2, 3, 4, 5]  # continuous, no duplicate, nothing twice
    assert all(r["execution_id"] == ex.execution_id and r["payload"]["pid"] == ex.pid for r in written)
    assert written[3]["kind"] == "EXECUTION_ENDED" and written[4]["payload"]["late"] is True
    # each line is the record's canonical JSON, byte for byte
    with open(path, "rb") as fh:
        assert fh.read() == b"".join(canonical_json(r) + b"\n" for r in ex.log.records)
    # the carrier changes once: a second binding is refused
    with pytest.raises(O.OperationsError):
        ex.log.bind_evidence_root(str(tmp_path / "elsewhere"))
    ex.log.close()


def test_never_bound_execution_has_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    before = sorted(os.listdir(tmp_path))
    ex = O.start_execution(CODE)
    for n in range(10):
        ex.log.append(K.DIAGNOSTIC, tick=n)
    ex.log.append(K.EXECUTION_ENDED)
    with pytest.raises(O.OperationsError):
        ex.log.flush_unflushed_prefix()  # there is nowhere to flush to
    assert sorted(os.listdir(tmp_path)) == before and not ex.log.bound and len(ex.log.records) == 12
    assert [r.op_seq for r in ex.log.records] == list(range(1, 13))  # the in-memory log is complete


def test_binding_never_overwrites_an_existing_log(tmp_path):
    ex = O.start_execution(CODE)
    root = tmp_path / "r"
    root.mkdir()
    (root / "operational.jsonl").write_bytes(b"evidence\n")
    with pytest.raises(FileExistsError):
        ex.log.bind_evidence_root(str(root))
    assert (root / "operational.jsonl").read_bytes() == b"evidence\n"


# --- the execution-output wrapper and the separation of representations ---------------------------

def make_surface_and_run():
    rec, eng = run_record(W_B, 5, 1, 1, policy="cost_based")
    return rec, eng, R.reproducible_surface(rec)


def write_execution(tmp_path, rec, surface, *, extra_records=0, stamp="2026-11-05T10:00:00Z"):
    ex = O.start_execution(rec.identity.code_identity)
    for n in range(extra_records):
        ex.log.append(K.DIAGNOSTIC, tick=n, payload={"extra": n})
    meta = R.execution_metadata(execution_id=ex.execution_id, run_id=rec.identity.run_id, standing="COMPLETED",
                                pid=ex.pid, started_at=stamp, ended_at=stamp, git_sha="a" * 40)
    root = R.write_execution_output(str(tmp_path), rec.identity.run_id, ex, surface, meta)
    ex.log.append(K.EXECUTION_ENDED)
    ex.log.close()
    return ex, root


def test_execution_output_layout_and_separate_log(tmp_path):
    rec, _eng, surface = make_surface_and_run()
    ex, root = write_execution(tmp_path, rec, surface)
    assert root == os.path.join(str(tmp_path), rec.identity.run_id, ex.execution_id)
    assert sorted(os.listdir(root)) == sorted(set(R.SURFACE_FILES) | {"execution_metadata.json", "operational.jsonl"})
    for name, data in surface.items():  # the eight files are written exactly as generated
        with open(os.path.join(root, name), "rb") as fh:
            assert fh.read() == data
    log = lines(os.path.join(root, "operational.jsonl"))
    assert [r["kind"] for r in log] == ["EXECUTION_STARTED", "EXECUTION_ENDED"] and log[0]["op_seq"] == 1
    with pytest.raises(ValueError):  # the surface must be exactly the eight files
        R.write_execution_output(str(tmp_path), "x", O.start_execution(CODE), {"summary.json": b"{}"}, b"{}")


def test_changing_execution_identity_and_operational_events_changes_no_simulation_surface(tmp_path):
    """Separation negative control: two Executions of one Run, with different execution ids, pids and
    timestamps and different operational events, leave run_id, the Simulation History and every
    reproducible file byte-identical."""
    rec, eng, surface = make_surface_and_run()
    history_before = canonical_json(rec.history)
    a, root_a = write_execution(tmp_path / "a", rec, surface, extra_records=0, stamp="2026-11-05T10:00:00Z")
    b, root_b = write_execution(tmp_path / "b", rec, surface, extra_records=7, stamp="2026-11-06T23:59:59Z")
    assert a.execution_id != b.execution_id and len(a.log.records) != len(b.log.records)
    assert os.path.basename(root_a) != os.path.basename(root_b)
    assert canonical_json(rec.history) == history_before == canonical_json(eng.history)
    assert R.reproducible_surface(rec) == surface
    for name in R.SURFACE_FILES:
        with open(os.path.join(root_a, name), "rb") as fa, open(os.path.join(root_b, name), "rb") as fb:
            assert fa.read() == fb.read() == surface[name], name
    for name in ("execution_metadata.json", "operational.jsonl"):  # the execution facts live only here
        with open(os.path.join(root_a, name), "rb") as fa, open(os.path.join(root_b, name), "rb") as fb:
            assert fa.read() != fb.read()
    # run_id does not contain the execution id and does not depend on it
    assert a.execution_id not in rec.identity.run_id and rec.identity.run_id == json.loads(
        surface["run_identity.json"])["run_id"]


EXECUTION_FACT = re.compile(rb"execution_id|operational|op_seq|EXECUTION_STARTED|EXECUTION_ENDED|\bpid\b|store_id|git_sha")


def scan(surface, execution_id):
    return [name for name, data in surface.items()
            if EXECUTION_FACT.search(data) or execution_id.encode() in data]


def test_a_leaking_surface_would_be_caught(tmp_path):
    """Negative control for the scan used above: if an execution fact leaked into a reproducible file
    the scan finds it, so its silence on the real surface means something."""
    rec, _eng, surface = make_surface_and_run()
    ex = O.start_execution(rec.identity.code_identity)
    assert scan(surface, ex.execution_id) == []
    leaky = dict(surface)
    leaky["summary.json"] = surface["summary.json"][:-1] + b',"execution_id":"' + ex.execution_id.encode() + b'"}'
    leaky["observations.md"] = surface["observations.md"] + b"- run by pid 123\n"
    assert scan(leaky, ex.execution_id) == ["summary.json", "observations.md"]
    # simulation records cannot hold an operational record at all (constitution N18, type half)
    from elevator.domain import SimulationHistory
    with pytest.raises(TypeError):
        SimulationHistory(events=(ex.log.records[0],), tick_records=())  # type: ignore[arg-type]


def test_operational_log_cannot_influence_the_engine():
    """The engine, policies, route, scenarios and domain never import operations; reporting and (later)
    api and checkpoint may. Operations imports domain and the standard library only."""
    def imports(name):
        with open(os.path.join(ROOT, "elevator", name), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom):
                mods.add(n.module or "")
                mods |= {f"{n.module}.{a.name}" for a in n.names}
        return mods

    assert {m for m in imports("operations.py") if m.startswith("elevator")} <= {
        "elevator.domain", "elevator.domain.OperationalRecord", "elevator.domain.OperationalRecordKind",
        "elevator.domain.canonical_json", "elevator.domain.freeze"}
    for module in ("engine.py", "policies.py", "route.py", "scenarios.py", "domain.py"):
        assert not [m for m in imports(module) if "operations" in m], module
    banned = {"elevator.engine", "elevator.route", "elevator.policies", "elevator.reporting", "elevator.api",
              "elevator.scenarios", "elevator.harness", "elevator.cli", "elevator.checkpoint", "web"}
    assert not imports("operations.py") & banned
