"""Cut 9: behaviour across real operating-system processes (fresh-process resume, a different code identity, an
unsupported environment) and the CLI's Store commands. This is a local test of the machinery, not the cut-10
witness: it does not compare the continuation with an uninterrupted Execution and may not be cited as CPOC
evidence."""

import inspect
import json
import os
import shutil
import signal
import subprocess
import sys
import time

import pytest

from elevator import checkpoint as C, operations
from tests.cpoc import fixture as X
from tests.cpoc.fixture import fx  # noqa: F401

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ENV = {**os.environ, "PYTHONPATH": ROOT}
SCENARIO = ["--scenario", "bursty", "--seed", "7", "--param", "num_requests=25", "--param", "horizon=20",
            "--floors", "10", "--elevators", "3", "--capacity", "4"]


def cli(*args, flags=("-B",), env=None):
    done = subprocess.run([sys.executable, *flags, "-m", "elevator.cli", *args], capture_output=True, text=True,
                          cwd=ROOT, env=env or ENV)
    out = dict(ln.split(": ", 1) for ln in done.stdout.splitlines() if ": " in ln)
    return done.returncode, out, done.stderr


def test_fresh_process_resume(tmp_path):
    """Process A runs partially and persists; A is killed; a fresh process B (a different pid) opens the Store,
    reconstructs, and advances at least one tick."""
    store, out = str(tmp_path / "S"), str(tmp_path / "out")
    assert cli("store", "init", store)[0] == 0
    a = subprocess.Popen([sys.executable, "-B", "-m", "elevator.cli", "simulate", *SCENARIO, "--store", store,
                          "--checkpoint-at", "8", "--pause-after-checkpoint", "--witness-instrumentation",
                          "--out", out], cwd=ROOT, env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + 60
        eid = None
        while time.time() < deadline and eid is None:
            for name in os.listdir(store):
                log = os.path.join(store, name, "operational.jsonl")
                if name != "store.json" and os.path.exists(log) and "CHECKPOINT_WRITTEN" in open(log).read():
                    eid = name
            time.sleep(0.05)
        assert eid is not None, "process A never wrote its checkpoint"
        assert a.poll() is None  # A is alive and blocked, holding its in-memory state
        a_pid = a.pid
    finally:
        a.send_signal(signal.SIGKILL)
        a.wait()
    assert a.returncode == -signal.SIGKILL  # A's death was a signal, not an orderly exit
    document = C.document_path(store, eid)
    before = open(document, "rb").read()
    assert json.loads(before)["standing"] == "RUNNING" and json.loads(before)["snapshot"]["t"] == 8
    code, b_out, err = cli("resume", "--store", store, "--resume", eid, "--witness-instrumentation", "--out", out)
    assert code == 0, err
    assert b_out["standing"] == "COMPLETED" and int(b_out["final_tick"]) > 8 and b_out["write_sequence"] == "2"
    records = operations.read_log(os.path.join(store, eid, "operational.jsonl"))
    pids = [r["payload"]["pid"] for r in records]
    b_pid = next(p for p in pids if p != a_pid)
    assert b_pid != a_pid and b_pid != os.getpid()  # a fresh process, not the object graph of A or of this test
    by_pid = lambda pid: [r for r in records if r["payload"]["pid"] == pid]
    a_ticks = [r["tick"] for r in by_pid(a_pid) if r["kind"] == "DIAGNOSTIC"]
    b_ticks = [r["tick"] for r in by_pid(b_pid) if r["kind"] == "DIAGNOSTIC"]
    assert a_ticks == list(range(8)) and b_ticks[0] == 8 and min(b_ticks) == 8  # B names no tick below 8
    assert b_ticks == list(range(8, int(b_out["final_tick"]) + 1))  # and advanced, tick by tick, to the end
    kinds_b = [r["kind"] for r in by_pid(b_pid)]
    assert kinds_b[:3] == ["EXECUTION_STARTED", "LOAD_ADMITTED", "RESUMED"] and kinds_b[-2:] == ["FINALITY_WRITTEN", "EXECUTION_ENDED"]
    assert [r["op_seq"] for r in records] == list(range(1, len(records) + 1))
    # B reused A's execution_id and its document: no new identity was minted
    assert {r["execution_id"] for r in records} == {eid}
    # and a final Execution is never reopened
    code, _, err = cli("resume", "--store", store, "--resume", eid)
    assert code == 3 and "EXECUTION_FINAL" in err


def package_copy(tmp_path, *, extra_comment=False, with_pycache=False):
    root = tmp_path / "copy"
    shutil.copytree(os.path.join(ROOT, "elevator"), root / "elevator", ignore=shutil.ignore_patterns("__pycache__"))
    if extra_comment:
        with open(root / "elevator" / "domain.py", "ab") as fh:
            fh.write(b"#")  # one comment byte
    if with_pycache:
        os.makedirs(root / "elevator" / "__pycache__")
    return str(root)


LOAD_SNIPPET = ("import sys\nfrom elevator import checkpoint as C\n"
                "try:\n    C.load(sys.argv[1], sys.argv[2])\nexcept C.Refusal as r:\n"
                "    print(r.reason, getattr(r, 'step', None))\nelse:\n    print('ADMITTED')\n")


def run_load(pkg_root, store, eid, *, flags=("-B",), extra_env=None, cache_prefix=None):
    env = {**os.environ, "PYTHONPATH": pkg_root, **(extra_env or {})}
    if cache_prefix:
        env["PYTHONPYCACHEPREFIX"] = cache_prefix
    return subprocess.run([sys.executable, *flags, "-c", LOAD_SNIPPET, store, eid], capture_output=True, text=True,
                          cwd=pkg_root, env=env, check=True).stdout.strip()


def test_row_15_different_code(fx, tmp_path):
    """cpoc §6 row 15: D12 loaded by a process whose governed package differs by one comment byte, under the
    execution contract: CODE_IDENTITY_MISMATCH at step 4, and no flag or environment variable changes this."""
    assert run_load(ROOT, fx.store, fx.execution_id) == "ADMITTED"  # the same bytes under the same code are admitted
    pkg = package_copy(tmp_path, extra_comment=True)
    assert run_load(pkg, fx.store, fx.execution_id) == "CODE_IDENTITY_MISMATCH 4"
    for override in ({"ELEVATOR_ALLOW_CODE_MISMATCH": "1"}, {"PYTHONDONTWRITEBYTECODE": "1", "FORCE": "1"}):
        assert run_load(pkg, fx.store, fx.execution_id, extra_env=override) == "CODE_IDENTITY_MISMATCH 4"
    assert list(inspect.signature(C.load).parameters) == ["store", "execution_id"]  # there is nothing to pass
    assert fx.on_disk() == fx.d12


def test_row_16_unsupported_environment(fx, tmp_path):
    """cpoc §6 row 16: bytecode writing enabled, or a __pycache__ inside the package: UNSUPPORTED_EXECUTION_ENVIRONMENT
    before any load. It precedes even the Store check, so a missing Store still reports the environment."""
    caches = str(tmp_path / "caches")  # keeps this negative run from writing bytecode into the real package
    env_clean = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
    refused = subprocess.run([sys.executable, "-c", LOAD_SNIPPET, fx.store, fx.execution_id], capture_output=True,
                             text=True, cwd=ROOT, env={**env_clean, "PYTHONPATH": ROOT, "PYTHONPYCACHEPREFIX": caches},
                             check=True).stdout.strip()
    assert refused.startswith("UNSUPPORTED_EXECUTION_ENVIRONMENT")
    missing = subprocess.run([sys.executable, "-c", LOAD_SNIPPET, str(tmp_path / "no-store"), "x"], capture_output=True,
                             text=True, cwd=ROOT, env={**env_clean, "PYTHONPATH": ROOT, "PYTHONPYCACHEPREFIX": caches},
                             check=True).stdout.strip()
    assert missing.startswith("UNSUPPORTED_EXECUTION_ENVIRONMENT")  # not STORE_NOT_FOUND: nothing was loaded
    dirty = package_copy(tmp_path, with_pycache=True)
    assert run_load(dirty, fx.store, fx.execution_id).startswith("UNSUPPORTED_EXECUTION_ENVIRONMENT")
    assert not os.path.isdir(os.path.join(ROOT, "elevator", "__pycache__"))


def test_execution_environment_contract(fx, tmp_path):
    """The entry-point half: the CLI's Store commands refuse outside the supported contract, and proceed under it."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
    env.update(PYTHONPATH=ROOT, PYTHONPYCACHEPREFIX=str(tmp_path / "caches"))
    store = str(tmp_path / "S2")
    assert cli("store", "init", store)[0] == 0
    code, _, err = cli("resume", "--store", fx.store, "--resume", fx.execution_id, flags=(), env=env)
    assert code == 6 and "UNSUPPORTED_EXECUTION_ENVIRONMENT" in err
    code, _, err = cli("simulate", *SCENARIO, "--store", store, "--checkpoint-at", "3", flags=(), env=env)
    assert code == 6 and "UNSUPPORTED_EXECUTION_ENVIRONMENT" in err
    assert os.listdir(store) == ["store.json"]  # nothing was written
    code, out, _ = cli("resume", "--store", fx.store, "--resume", fx.execution_id)  # under the contract it proceeds
    assert code == 0 and out["standing"] == "COMPLETED"
    assert not os.path.isdir(os.path.join(ROOT, "elevator", "__pycache__"))


def test_cli_store_commands_and_exit_codes(tmp_path):
    store = str(tmp_path / "S")
    code, out, _ = cli("store", "init", store)
    assert code == 0 and len(out["store_id"]) == 36
    assert json.loads(open(os.path.join(store, "store.json")).read()) == {"store_id": out["store_id"], "store_schema_version": 1}
    code, _, err = cli("store", "init", store)  # a Store is never overwritten
    assert code == 5 and "store.json" in err
    # usage: controls need a Store and a Store needs controls (an Execution with none never touches a Store)
    assert cli("simulate", *SCENARIO, "--store", store)[0] == 2
    assert cli("simulate", *SCENARIO, "--checkpoint-at", "3")[0] == 2
    assert cli("simulate", *SCENARIO, "--store", store, "--checkpoint-every", "0")[0] == 2
    # refusals from the loader are named and map to the refusal exit code
    code, _, err = cli("resume", "--store", str(tmp_path / "nowhere"), "--resume", "x")
    assert code == 3 and err.startswith("refused: STORE_NOT_FOUND")
    code, _, err = cli("resume", "--store", store, "--resume", "not-an-execution")
    assert code == 3 and err.startswith("refused: EXECUTION_NOT_FOUND")
    # checkpoint-every writes at every positive multiple, then the finality write
    code, out, _ = cli("simulate", *SCENARIO, "--store", store, "--checkpoint-every", "5", "--out", str(tmp_path / "o"))
    assert code == 0 and out["standing"] == "COMPLETED"
    final_tick = int(out["final_tick"])
    assert int(out["write_sequence"]) == len([t for t in range(5, final_tick + 1, 5) if t <= final_tick]) + 1
    eid = out["execution_id"]
    records = operations.read_log(os.path.join(store, eid, "operational.jsonl"))
    kinds = [r["kind"] for r in records]
    assert kinds[0] == "EXECUTION_STARTED" and kinds[-2:] == ["FINALITY_WRITTEN", "EXECUTION_ENDED"]
    assert [r["tick"] for r in records if r["kind"] == "CHECKPOINT_WRITTEN"] == list(range(5, final_tick + 1, 5))
    # the Store-bound Execution's evidence root is the Store; the output location holds a copy made at the end
    copy = os.path.join(out["output"], "operational.jsonl")
    assert open(copy, "rb").read() == open(os.path.join(store, eid, "operational.jsonl"), "rb").read()
    assert sorted(os.listdir(out["output"])) == sorted([
        "elevator_positions.csv", "position_log_long.csv", "passengers.csv", "summary.json", "observations.md",
        "run_identity.json", "events.jsonl", "tick_records.jsonl", "execution_metadata.json", "operational.jsonl"])
    # a checkpoint boundary the Run never reaches writes no document and so no finality
    code, out2, _ = cli("simulate", *SCENARIO, "--store", store, "--checkpoint-at", "100000")
    assert code == 0 and "write_sequence" not in out2
    assert not os.path.exists(os.path.join(store, out2["execution_id"], "run.json"))
    assert os.path.exists(os.path.join(store, out2["execution_id"], "operational.jsonl"))


def test_a_halted_run_is_persisted_final_and_never_resumed(tmp_path):
    store = str(tmp_path / "S")
    cli("store", "init", store)
    code, out, _ = cli("simulate", *SCENARIO, "--store", store, "--checkpoint-at", "4", "--max-ticks", "10")
    assert code == 4 and out["standing"] == "HALTED" and out["halt_reason"] == "HORIZON_EXCEEDED"
    doc = json.loads(open(C.document_path(store, out["execution_id"]), "rb").read())
    assert doc["standing"] == "HALTED" and doc["final"]["halt_reason"] == "HORIZON_EXCEEDED" and "snapshot" not in doc
    code, _, err = cli("resume", "--store", store, "--resume", out["execution_id"])
    assert code == 3 and "EXECUTION_FINAL" in err
