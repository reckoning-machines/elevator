"""Cut 10: the CPOC witness (cpoc §4.2) for both policies, the negative witnesses marked cut 10 (§6 rows 29(a),
30, 31, 32, 34's qualification half), the negative controls, and the evidence record (§7). Every process is a
real operating-system process started under the supported execution contract (python -B)."""

import dataclasses
import json
import os
import shutil
import signal
import subprocess
import sys

import pytest

from elevator import api, checkpoint as C, operations
from elevator.domain import canonical_json
from tests.cpoc import fixture as X
from tests.cpoc import scan
from tests.cpoc.witness import harness as H

POLICIES = ["cost_based", "round_robin"]
EVIDENCE: dict = {}


@pytest.fixture(scope="module", params=POLICIES)
def ev(request, tmp_path_factory):
    e = H.run_witness(str(tmp_path_factory.mktemp(f"witness_{request.param}")), request.param)
    EVIDENCE[request.param] = e
    return e


def doc_of(ev):
    return json.loads(ev.d12)


def final_tick(ev):
    return int(ev.b_stdout["final_tick"])


# --- the fixture ----------------------------------------------------------------------------------------------

def test_fixture_is_the_committed_file_and_the_chosen_tick_satisfies_its_conditions(ev):
    assert H.sha(H.read(H.FIXTURE)) == H.FIXTURE_SHA256
    doc = doc_of(ev)
    t, trace = doc["snapshot"]["t"], doc["trace"]
    assert t == H.T == 12 and (doc["configuration"]["num_floors"], doc["configuration"]["num_elevators"],
                               doc["configuration"]["capacity"]) == (10, 3, 4)
    standing = [p["standing"] for p in doc["snapshot"]["passengers"]]
    assert "ONBOARD" in standing and "WAITING" in standing  # one ONBOARD, one WAITING
    assert any(r[0] > t for r in trace)  # a Request with request_time > t
    assert any(p["standing"] == "WAITING" and trace[p["passenger_id"]][0] + abs(
        trace[p["passenger_id"]][3] - trace[p["passenger_id"]][2]) < t for p in doc["snapshot"]["passengers"])  # row 24
    assert doc["configuration"]["policy"] == ev.policy and doc["trace"] == X.trace_rows()
    # the file and the generated Trace denote one Run
    assert api.simulate(X.trace_rows(), H.N, H.F, H.C, policy=ev.policy).run_id == ev.run_id == doc["run_id"]


# --- the witness, steps 1 to 7 ---------------------------------------------------------------------------------

def test_real_process_death_resume(ev):
    assert ev.a_returncode == -signal.SIGKILL and ev.a_gone  # death by signal 9, the PID gone
    assert ev.b_returncode == 0 and ev.b_stdout["standing"] == "COMPLETED" and ev.b_stdout["write_sequence"] == "2"
    pids = {ev.r_pid, ev.a_pid, ev.b_pid, os.getpid()}
    assert len(pids) == 4  # B is a fresh process: not A, not R, not the test
    d12 = doc_of(ev)
    assert H.sha(ev.d12) == ev.d_A  # the document read after the kill is the document the receipt names
    assert (d12["standing"], d12["snapshot"]["t"], d12["write_sequence"]) == ("RUNNING", 12, 1)
    assert ev.receipt["payload"]["write_sequence"] == 1 and ev.receipt["tick"] == 12
    assert ev.receipt["payload"]["snapshot_hash"] == X.snapshot_hash_of(d12)
    assert ev.receipt["payload"]["history_hash"] == X.history_hash_of(d12)
    assert H.qualify_witness(ev) == "CPOC_EVIDENCE"


def test_uninterrupted_vs_resumed_history_identical(ev):
    r, b = ev.run_dir(ev.r_id), ev.run_dir(ev.a_id)
    assert H.compare_history(r, b, ev.d12) == []
    # the three claims of cpoc §4.2 step 6 hold on real bytes, and the comparison is not vacuous
    ticks = H.read(os.path.join(r, "tick_records.jsonl")).splitlines()
    assert len(ticks) == final_tick(ev) + 1 and final_tick(ev) > 12
    assert H.read(os.path.join(r, "events.jsonl")) == H.read(os.path.join(b, "events.jsonl"))


def test_uninterrupted_vs_resumed_output_identical(ev):
    r, b = ev.run_dir(ev.r_id), ev.run_dir(ev.a_id)
    assert H.compare_surface(r, b) == []  # every file of the Reproducible Output Surface, run_identity.json included
    assert sorted(os.listdir(b)) == sorted(H.SURFACE + ["execution_metadata.json", "operational.jsonl"])
    # execution_metadata.json: shape only; it differs where an Execution differs and nowhere else
    mr, mb = json.loads(H.read(os.path.join(r, "execution_metadata.json"))), \
        json.loads(H.read(os.path.join(b, "execution_metadata.json")))
    assert set(mr) == set(mb) and mr["run_id"] == mb["run_id"] and mr["standing"] == mb["standing"] == "COMPLETED"
    assert (mr["execution_id"], mr["pid"]) == (ev.r_id, ev.r_pid) and (mb["execution_id"], mb["pid"]) == (ev.a_id, ev.b_pid)
    assert mr["store_id"] is None and mb["store_id"] == ev.store_id
    assert {k for k in mr if mr[k] != mb[k]} <= {"execution_id", "pid", "store_id", "started_at", "ended_at"}
    # the surface carries no execution fact (constitution N18)
    forbidden = [ev.r_id, ev.a_id, ev.store_id, '"execution_id"', '"store_id"', '"pid"', "git_sha", "started_at", "ended_at"]
    assert H.surface_leaks(ev.run_dir(ev.a_id), forbidden) == [] and H.surface_leaks(ev.run_dir(ev.r_id), forbidden) == []
    assert json.loads(H.read(os.path.join(b, "run_identity.json")))["code_identity"] == doc_of(ev)["code_identity"]


def test_resume_starts_after_checkpoint(ev):
    log = ev.store_log()
    assert H.check_anti_recomputation(log, ev.b_pid, 12, final_tick(ev)) == []
    b_ticks = [r["tick"] for r in log if r["kind"] == "DIAGNOSTIC" and r["payload"]["pid"] == ev.b_pid]
    assert b_ticks[0] == 12 and len(b_ticks) == final_tick(ev) - 12 + 1
    a_ticks = [r["tick"] for r in log if r["kind"] == "DIAGNOSTIC" and r["payload"]["pid"] == ev.a_pid]
    assert a_ticks == list(range(12))  # A executed 0..11
    r_log = H.jsonl(os.path.join(ev.run_dir(ev.r_id), "operational.jsonl"))
    assert [r["tick"] for r in r_log if r["kind"] == "DIAGNOSTIC"] == list(range(final_tick(ev) + 1))  # R: every tick from 0
    assert set(a_ticks).isdisjoint(b_ticks)  # no tick is executed by both: nothing is replayed, nothing re-run


def test_load_admitted_equalities_and_transient_authority(ev):
    log, d12 = ev.store_log(), doc_of(ev)
    loaded = next(r for r in log if r["kind"] == "LOAD_ADMITTED")["payload"]
    assert loaded["document_sha256"] == ev.d_A == H.sha(ev.d12)  # B loaded the bytes A wrote
    assert loaded["snapshot_hash"] == ev.receipt["payload"]["snapshot_hash"] == loaded["constructed_state_hash"]
    assert loaded["history_hash"] == ev.receipt["payload"]["history_hash"]
    assert (loaded["store_id"], loaded["execution_id"]) == (ev.store_id, ev.a_id) == (d12["store_id"], d12["execution_id"])
    # row 30: B was started with nothing but --store, --resume, --witness-instrumentation and an output directory
    assert ev.b_argv[4:] == ["resume", "--store", ev.store, "--resume", ev.a_id, "--witness-instrumentation", "--out", ev.out]
    assert not [a for a in ev.b_argv if a in ("--requests", "--scenario", "--seed", "--policy", "--floors", "--param")]
    assert ev.b_env == {"PATH": ev.b_env["PATH"]}
    started = [r for r in log if r["kind"] == "EXECUTION_STARTED" and r["payload"]["pid"] == ev.b_pid]
    assert len(started) == 1 and set(started[0]["payload"]) == {"code_identity", "pid"}  # no argv, path or environment
    assert started[0]["payload"]["code_identity"] == d12["code_identity"]


def test_operational_log_continuity_and_expected_differences(ev):
    log = ev.store_log()
    assert [r["op_seq"] for r in log] == list(range(1, len(log) + 1))  # monotonic, contiguous, no gap, no duplicate
    assert {r["execution_id"] for r in log} == {ev.a_id}
    f = final_tick(ev)
    assert H.kinds(log, ev.a_pid) == ["EXECUTION_STARTED"] + ["DIAGNOSTIC"] * 12 + ["CHECKPOINT_WRITTEN"]
    assert H.kinds(log, ev.b_pid) == ["EXECUTION_STARTED", "LOAD_ADMITTED", "RESUMED"] + ["DIAGNOSTIC"] * (f - 12 + 1) + [
        "FINALITY_WRITTEN", "EXECUTION_ENDED"]
    r_log = H.jsonl(os.path.join(ev.run_dir(ev.r_id), "operational.jsonl"))
    assert H.kinds(r_log, ev.r_pid) == ["EXECUTION_STARTED"] + ["DIAGNOSTIC"] * (f + 1) + ["EXECUTION_ENDED"]
    # A's prefix is present once and first; B's records follow it; nothing of A's was re-appended
    n_a = len(H.kinds(log, ev.a_pid))
    assert [r["payload"]["pid"] for r in log] == [ev.a_pid] * n_a + [ev.b_pid] * (len(log) - n_a)
    assert log[n_a]["kind"] == "EXECUTION_STARTED" and log[n_a]["op_seq"] == n_a + 1  # B's own start, after A's last
    assert [r["payload"]["write_sequence"] for r in log if r["kind"] in ("CHECKPOINT_WRITTEN", "FINALITY_WRITTEN")] == [1, 2]
    # the output-location log is a copy of the Store's, made at EXECUTION_ENDED
    assert H.read(os.path.join(ev.run_dir(ev.a_id), "operational.jsonl")) == H.read(
        os.path.join(ev.store, ev.a_id, "operational.jsonl"))
    # the logs differ from R's (they must) and none of it touches the History comparison
    assert H.kinds(log, ev.b_pid) != H.kinds(r_log, ev.r_pid)
    forbidden_in_history = ("CHECKPOINT_WRITTEN", "LOAD_ADMITTED", "RESUMED", "FINALITY_WRITTEN", "op_seq")
    text = H.read(os.path.join(ev.run_dir(ev.a_id), "events.jsonl")).decode() + H.read(
        os.path.join(ev.run_dir(ev.a_id), "tick_records.jsonl")).decode()
    assert not [w for w in forbidden_in_history if w in text]


def test_projection_agreement_row_29a(ev):
    """Regenerate the position export from B's TickRecords, independently of the reporting module, and compare
    with the reference's file."""
    ticks = H.jsonl(os.path.join(ev.run_dir(ev.a_id), "tick_records.jsonl"))
    lines = ["t," + ",".join(f"elevator_{i}" for i in range(H.N))]
    for rec in ticks:
        floors = {e["elevator_id"]: e["floor"] for e in rec["entries"]}
        lines.append(f"{rec['tick']}," + ",".join(str(floors[i]) for i in range(H.N)))
    regenerated = ("\n".join(lines) + "\n").encode()
    assert regenerated == H.read(os.path.join(ev.run_dir(ev.r_id), "elevator_positions.csv"))
    assert regenerated == H.read(os.path.join(ev.run_dir(ev.a_id), "elevator_positions.csv"))


def test_final_resume_refused_and_write_after_final_refused(ev, tmp_path):
    final = H.read(ev.document())
    d = json.loads(final)
    assert (d["standing"], d["write_sequence"]) == ("COMPLETED", 2) and "snapshot" not in d and d["final"]["final_tick"] == final_tick(ev)
    code, _, err = H.cli("resume", "--store", ev.store, "--resume", ev.a_id)
    assert code == 3 and "EXECUTION_FINAL" in err
    code, _, err = H.cli("resume", "--store", ev.store, "--resume", ev.a_id, "--out", str(tmp_path / "other"))
    assert code == 3 and "EXECUTION_FINAL" in err and not os.path.exists(tmp_path / "other")  # outputs never consulted
    assert H.read(ev.document()) == final  # the final document is unchanged by both refusals
    # write after final, on a copy of the Store, with the current token (so the sequence matches)
    copy = str(tmp_path / "S_copy")
    shutil.copytree(ev.store, copy)
    identity = api.create_engine(X.trace_rows(), H.N, H.F, H.C, policy=ev.policy)
    execution = operations.resume_execution(ev.a_id, d["code_identity"], os.path.join(copy, ev.a_id))
    with pytest.raises(C.CheckpointRefusal) as info:
        C.write_checkpoint(copy, execution, identity.run_identity, identity._config, identity._trace, identity, token=2)
    assert info.value.reason == "WRITE_AFTER_FINAL"
    assert H.read(os.path.join(copy, ev.a_id, "run.json")) == final
    execution.log.close()


def test_architecture_obligations_hold_at_this_code_identity():
    """cpoc §4.2 step 7: the structural obligations (no History-to-state path) hold for the package under test,
    and the planted History-cheating fixture is still detected."""
    assert scan.scan_package(H.ROOT) == {}
    assert len(scan.scan_file(os.path.join(H.ROOT, "tests", "cpoc", "cheats", "history_cheat.py"))) >= 5


# --- negative controls: each deliberately wrong continuation must fail the witness --------------------------------

def spawn_killed_a(tmp_path, policy):
    return H.run_witness(str(tmp_path), policy, do_b=False)


REPLAY_CHEAT = """
import sys
from elevator import checkpoint as C
from elevator.engine import Engine
from elevator.policies import make_policy
store, eid = sys.argv[1:3]
resumed = C.resume(store, eid)  # a lawful load, then the snapshot is ignored and the Run replays from tick 0
cfg, trace = resumed.loaded.configuration, resumed.loaded.trace
fresh = Engine.create(cfg, trace, make_policy(cfg.policy, cfg.policy_params))
C.instrument(fresh, resumed.execution)
while fresh.outcome is None:
    fresh.step()
resumed.execution.log.close()
print(fresh.outcome.final_tick)
"""


def test_planted_replay_cheat_fails(ev, tmp_path):
    """A continuation that reloads and then re-runs from tick 0 reaches the same History, so only the
    anti-recomputation evidence can catch it; it does."""
    e = spawn_killed_a(tmp_path, ev.policy)
    done = subprocess.run([sys.executable, "-B", "-c", REPLAY_CHEAT, e.store, e.a_id], capture_output=True, text=True,
                          cwd=H.ROOT, env=H.CLEAN_ENV)
    assert done.returncode == 0, done.stderr
    log = e.store_log()
    cheat_pid = next(r["payload"]["pid"] for r in log if r["kind"] == "LOAD_ADMITTED")
    failures = H.check_anti_recomputation(log, cheat_pid, 12, int(done.stdout))
    assert any("below 12" in f for f in failures) and any("count" in f for f in failures), failures
    assert H.check_anti_recomputation(ev.store_log(), ev.b_pid, 12, final_tick(ev)) == []  # the honest B passes


def mutated_tick_files(ev, tmp_path, mutate):
    work = tmp_path / "mut"
    shutil.copytree(ev.run_dir(ev.a_id), work)
    lines = H.read(str(work / "tick_records.jsonl")).splitlines()
    lines = mutate(lines)
    (work / "tick_records.jsonl").write_bytes(b"\n".join(lines) + b"\n")
    return str(work)


def test_skipped_and_duplicated_post_checkpoint_ticks_fail(ev, tmp_path):
    skipped = mutated_tick_files(ev, tmp_path / "a", lambda ls: ls[:15] + ls[16:])
    assert "tick_records for t >= checkpoint differ" in H.compare_history(ev.run_dir(ev.r_id), skipped, ev.d12)
    duplicated = mutated_tick_files(ev, tmp_path / "b", lambda ls: ls[:15] + [ls[15]] + ls[15:])
    assert "tick_records for t >= checkpoint differ" in H.compare_history(ev.run_dir(ev.r_id), duplicated, ev.d12)
    # and the diagnostics: a skipped or duplicated tick breaks contiguity or the count
    base = [{"kind": "DIAGNOSTIC", "tick": k, "payload": {"pid": 7}} for k in range(12, final_tick(ev) + 1)]
    assert H.check_anti_recomputation(base, 7, 12, final_tick(ev)) == []
    assert H.check_anti_recomputation(base[:3] + base[4:], 7, 12, final_tick(ev))
    assert H.check_anti_recomputation(base[:3] + [base[2]] + base[3:], 7, 12, final_tick(ev))


def finish_from(ev, mutate):
    """Resume in-process from D12 through production restore with a deliberately wrong state, run to the end, and
    return the TickRecord bytes (or the exception) the continuation produced."""
    from elevator import reporting
    from elevator.engine import Engine
    from elevator.policies import make_policy
    doc = doc_of(ev)
    state = mutate(C.construct_state(C.parse_snapshot(doc)))
    cfg = api.create_engine(X.trace_rows(), H.N, H.F, H.C, policy=ev.policy)
    engine = Engine.restore(cfg._config, cfg._trace, make_policy(ev.policy, cfg._config.policy_params), state,
                            _prefix_history(ev))
    try:
        while engine.outcome is None:
            engine.step()
        record = reporting.RunRecord(cfg._config, cfg._trace, cfg.run_identity, engine.history, engine.passengers)
        return reporting.reproducible_surface(record)["tick_records.jsonl"]
    except Exception as exc:  # an invariant, a halt or a report refusal is a detected failure of the continuation too
        return exc


def _prefix_history(ev):
    """A History prefix to attach: the lawful engine's, advanced to the boundary (the wrong state is what is under test)."""
    e = api.create_engine(X.trace_rows(), H.N, H.F, H.C, policy=ev.policy)
    while e.t < H.T:
        e.step()
    return e.history


def test_wrong_state_restores_fail(ev):
    reference = H.read(os.path.join(ev.run_dir(ev.r_id), "tick_records.jsonl"))
    assert finish_from(ev, lambda s: s) == reference  # the control: a faithful restore reproduces the reference
    wrong_floor = lambda s: dataclasses.replace(s, elevators=(dataclasses.replace(
        s.elevators[0], floor=s.elevators[0].floor + 1 if s.elevators[0].floor + 1 < H.F else s.elevators[0].floor - 1),) + s.elevators[1:])
    moving = lambda s: next(i for i, e in enumerate(s.elevators) if e.heading.value != "NONE")
    def wrong_heading(s):
        i = moving(s)
        flipped = type(s.elevators[i].heading)("DOWN" if s.elevators[i].heading.value == "UP" else "UP")
        return dataclasses.replace(s, elevators=tuple(dataclasses.replace(e, heading=flipped) if k == i else e
                                                      for k, e in enumerate(s.elevators)))
    def wrong_standing(s):
        waiting = next(i for i, p in enumerate(s.passengers) if p.standing.value == "WAITING")
        done = next(p.standing for p in s.passengers if p.standing.value == "COMPLETED")
        return dataclasses.replace(s, passengers=tuple(dataclasses.replace(p, standing=done) if k == waiting else p
                                                       for k, p in enumerate(s.passengers)))
    for name, mutate in (("floor", wrong_floor), ("heading", wrong_heading), ("passenger standing", wrong_standing)):
        got = finish_from(ev, mutate)
        assert isinstance(got, Exception) or got != reference, name  # diverges or is refused, never equal


def test_mutated_snapshot_and_other_run_refuse_in_a_fresh_process(ev, tmp_path):
    """A mutated checkpoint, and a document of a different Trace or configuration, are refused by a real fresh
    resume; nothing continues and the mutated document is left as found."""
    for name, mutate, reason in (
            ("heading_rehashed", lambda d: (_flip_heading(d), X.recompute_snapshot_hash(d)), "STATE_HISTORY_MISMATCH"),
            ("heading_stale_hash", lambda d: _flip_heading(d), "STATE_INCONSISTENT"),
            ("trace", lambda d: d["trace"][0].__setitem__(3, (d["trace"][0][3] + 1) % H.F or 1), "TRACE_HASH_MISMATCH"),
            ("configuration", lambda d: d["configuration"].__setitem__("capacity", H.C + 1), "CONFIG_HASH_MISMATCH")):
        e = spawn_killed_a(tmp_path / name, ev.policy)
        d = json.loads(e.d12)
        mutate(d)
        mutated = X.canonical(d)
        with open(e.document(), "wb") as fh:
            fh.write(mutated)
        code, _, err = H.cli("resume", "--store", e.store, "--resume", e.a_id, "--out", str(tmp_path / name / "o"))
        assert code == 3 and reason in err, (name, err)
        assert H.read(e.document()) == mutated and not os.path.exists(tmp_path / name / "o")
        assert "LOAD_ADMITTED" not in {r["kind"] for r in e.store_log()}  # nothing was admitted or continued
    # a different Trace is a different Run: its surface cannot equal the reference's
    code, other, err = H.cli("simulate", *H.common(ev.policy)[:0], "--requests", str(_short_trace(tmp_path)), "--floors", "10",
                             "--elevators", "3", "--capacity", "4", "--policy", ev.policy, "--out", str(tmp_path / "x"))
    assert code == 0 and other["run_id"] != ev.run_id
    assert H.compare_surface(ev.run_dir(ev.r_id), os.path.join(tmp_path / "x", other["run_id"], other["execution_id"]))


def _flip_heading(d):
    e = next(e for e in d["snapshot"]["elevators"] if e["heading"] != "NONE")
    e["heading"] = "DOWN" if e["heading"] == "UP" else "UP"


def _short_trace(tmp_path):
    rows = H.read(H.FIXTURE).decode().splitlines()[:-1]
    path = tmp_path / "short.csv"
    path.write_text("\n".join(rows) + "\n")
    return path


def test_operational_facts_leaking_into_the_surface_fail(ev, tmp_path):
    work = tmp_path / "leak"
    shutil.copytree(ev.run_dir(ev.a_id), work)
    summary = json.loads((work / "summary.json").read_text())
    summary["execution_id"] = ev.a_id
    (work / "summary.json").write_text(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    assert H.compare_surface(ev.run_dir(ev.r_id), str(work)) == ["summary.json differs"]
    assert H.surface_leaks(str(work), [ev.a_id])  # and the leak scan names it on its own


# --- negative witnesses 31, 32 and 34 (the harness's evidence qualification) --------------------------------------------

def test_row_31_process_local_continuation_is_not_cpoc_evidence(tmp_path):
    # (a) no kill and no fresh process: one process checkpoints and carries on to completion
    store = str(tmp_path / "S")
    H.cli("store", "init", store)
    p = subprocess.Popen([sys.executable, "-B", "-m", "elevator.cli", "simulate", *H.common("cost_based"), "--store", store,
                          "--checkpoint-at", "12", "--witness-instrumentation"], cwd=H.ROOT, env=H.CLEAN_ENV,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert p.wait() == 0
    eid = H.store_execution(store)
    log = H.jsonl(os.path.join(store, eid, "operational.jsonl"))
    assert "LOAD_ADMITTED" not in {r["kind"] for r in log}
    label = H.qualify(store_bound=True, first_pid=p.pid, first_returncode=p.returncode, first_gone=True, cont_pid=p.pid,
                      log=log, d12_present=True)
    assert label == "REFUSED_PROCESS_LOCAL"
    # (b) a fresh process resumes while A is still alive: the first process was never killed
    alive = H.run_witness(str(tmp_path / "alive"), "cost_based", kill_a=False)
    assert alive.b_returncode == 0 and alive.a_returncode is None and not alive.a_gone
    assert H.qualify_witness(alive) == "REFUSED_FIRST_PROCESS_NOT_KILLED"


KILL_BEFORE_RECEIPT = """
import os, signal, sys
from elevator import cli, operations
from elevator.domain import OperationalRecordKind
original = operations.OperationalLog.append
def append(self, kind, **kw):
    if kind == OperationalRecordKind.CHECKPOINT_WRITTEN:
        os.kill(os.getpid(), signal.SIGKILL)  # after the rename and the read-back, before the receipt
    return original(self, kind, **kw)
operations.OperationalLog.append = append
sys.exit(cli.main(sys.argv[1:]))
"""


def test_row_32_receipt_missing_loads_lawfully_but_fails_certification(tmp_path):
    store, out = str(tmp_path / "S"), str(tmp_path / "out")
    H.cli("store", "init", store)
    a = subprocess.Popen([sys.executable, "-B", "-c", KILL_BEFORE_RECEIPT, "simulate", *H.common("cost_based"), "--store",
                          store, "--checkpoint-at", "12", "--witness-instrumentation", "--out", out], cwd=H.ROOT,
                         env=H.CLEAN_ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert a.wait() == -signal.SIGKILL
    eid = H.store_execution(store)
    document = H.read(os.path.join(store, eid, "run.json"))
    assert json.loads(document)["write_sequence"] == 1 and json.loads(document)["snapshot"]["t"] == 12  # durable
    assert "CHECKPOINT_WRITTEN" not in {r["kind"] for r in H.jsonl(os.path.join(store, eid, "operational.jsonl"))}
    code, b, err = H.cli("resume", "--store", store, "--resume", eid, "--witness-instrumentation", "--out", out)
    assert code == 0 and b["standing"] == "COMPLETED", err  # the document loads lawfully and the run completes
    log = H.jsonl(os.path.join(store, eid, "operational.jsonl"))
    b_pid = next(r["payload"]["pid"] for r in log if r["kind"] == "LOAD_ADMITTED")
    label = H.qualify(store_bound=True, first_pid=a.pid, first_returncode=a.returncode, first_gone=H.pid_gone(a.pid),
                      cont_pid=b_pid, log=log, d12_present=True)
    assert label == "EVIDENCE_INCOMPLETE"  # recorded as such: it fails certification, not the load


def test_row_34_never_bound_execution_is_not_cpoc_evidence(ev, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    before = set(os.listdir(tmp_path))
    result = api.simulate(X.trace_rows(), H.N, H.F, H.C, policy=ev.policy, output_dir=None)
    assert set(os.listdir(tmp_path)) == before and result.output_path is None  # no file is written anywhere
    assert not result.execution.log.bound and result.execution.log.evidence_root is None
    for name in H.SURFACE:  # its Reproducible Output Surface equals a bound Execution's, byte for byte
        assert result.surface[name] == H.read(os.path.join(ev.run_dir(ev.a_id), name)), name
    label = H.qualify(store_bound=result.execution.log.bound, first_pid=os.getpid(), first_returncode=None, first_gone=False,
                      cont_pid=os.getpid(), log=[], d12_present=False)
    assert label == "REFUSED_NEVER_BOUND"


# --- the evidence record (cpoc §7) ----------------------------------------------------------------------------------------

def render_record(evs: dict) -> str:
    from elevator.domain import canonical_json  # noqa: F401
    doc = json.loads(evs[POLICIES[0]].d12)
    lines = [f"# CPOC witness record: code identity {doc['code_identity']}", "",
             "Evidence only. It records one execution of the witness of [cpoc §4.2](../cpoc_design.md); it is not authority "
             "for anything it observed. Bounded claim: continuation from the durable Continuation Document in a fresh local "
             "process under the supported execution contract (cpoc §4.1). No general crash-consistency or distributed "
             "fault-tolerance claim is made.", "",
             f"- Date: 2026-11-05",
             f"- Code identity: `{doc['code_identity']}`",
             f"- Execution contract: `python -B`, no `__pycache__` in `elevator/` (confirmed by the suite)",
             f"- Fixture: `tests/cpoc/witness/fixtures/bursty_seed7_F10_N3_C4.csv`, sha256 `{H.FIXTURE_SHA256}`; "
             f"configuration F=10, N=3, C=4; checkpoint at t=12", ""]
    for policy, e in evs.items():
        d = json.loads(e.d12)
        log = e.store_log()
        loaded = next(r for r in log if r["kind"] == "LOAD_ADMITTED")["payload"]
        f = int(e.b_stdout["final_tick"])
        lines += [f"## Policy `{policy}`", "",
                  f"- Subject: continuation of Execution `{e.a_id}` of run `{e.run_id}` from t=12",
                  f"- Store: `{e.store_id}` (store schema version 1)",
                  f"- Configuration hash `{d['configuration_hash']}`; trace hash `{d['trace_hash']}`",
                  f"- Execution R: `{e.r_id}`, PID {e.r_pid}, exit code 0, operational records EXECUTION_STARTED, "
                  f"{f + 1} DIAGNOSTIC (ticks 0..{f}), EXECUTION_ENDED",
                  f"- Execution A: `{e.a_id}`, PID {e.a_pid}; CHECKPOINT_WRITTEN document sha256 `{e.d_A}`, write_sequence 1, "
                  f"snapshot_hash `{e.receipt['payload']['snapshot_hash']}`, history_hash `{e.receipt['payload']['history_hash']}`; "
                  f"killed by SIGKILL, exit by signal {-e.a_returncode} confirmed, PID gone, document sha256 re-read == d_A",
                  f"- Process B: PID {e.b_pid}, argv `{' '.join(e.b_argv[4:])}`, environment `PATH` only; LOAD_ADMITTED "
                  f"document sha256 `{loaded['document_sha256']}` (== d_A), snapshot_hash == constructed_state_hash "
                  f"`{loaded['constructed_state_hash']}`; RESUMED(t=12); FINALITY_WRITTEN write_sequence 2; final tick {f}",
                  "- Loader verifications 1..11: PASS in order (LOAD_ADMITTED present; verifier discarded before construction)",
                  "- Simulation History: tick_records (t >= 12) identical; events identical with sequence numbers; "
                  "document prefix + continuation == R's complete History",
                  "- Reproducible Output Surface: all eight files byte-identical to R's (run_identity.json included); "
                  "execution_metadata.json compared for shape only",
                  f"- Anti-recomputation: B's DIAGNOSTIC ticks 12..{f}, none below 12, count {f - 12 + 1}; A's 0..11; R's 0..{f}; "
                  "architecture scan green at this code identity",
                  f"- Operational Log: op_seq 1..{len(log)} contiguous; A's prefix once; B's records follow",
                  f"- Qualification: `{H.qualify_witness(e)}`", ""]
    lines += ["## Negative witnesses (cpoc §6)", "",
              "Rows 1 to 28 and 33: cut 9, `tests/cpoc/local/` (row 6 LIMIT, row 7 ADMITTED as designed). "
              "Rows 29(a), 30, 31, 32, 34 (qualification half): `tests/cpoc/witness/test_witness.py`, all PASS. "
              "Row 29(b): cut 11, not run here.", "",
              "Negative controls (each fails the witness): replay from tick 0; skipped tick; duplicated tick; wrong floor; "
              "wrong heading; wrong passenger standing; mutated Snapshot (hash recomputed and not); different Trace; "
              "different configuration; operational fact leaked into the surface.", "",
              "CPOC standing: **PASS** (both policies; subject to the counts recorded in "
              "`docs/implementation/cut_10_cpoc_witness.md`)", ""]
    return "\n".join(lines)


def test_evidence_record_is_renderable_from_a_clean_witness(ev, tmp_path):
    """Both policies must have a clean witness before a record can be rendered; it is written only when
    ELEVATOR_WITNESS_RECORD names a path (the committed record is produced once, from a green run)."""
    assert H.qualify_witness(ev) == "CPOC_EVIDENCE"
    if len(EVIDENCE) == len(POLICIES):
        text = render_record(EVIDENCE)
        assert "CPOC standing: **PASS**" in text
        target = os.environ.get("ELEVATOR_WITNESS_RECORD")
        if target:
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(text)
