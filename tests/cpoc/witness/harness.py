"""Cut 10: the witness orchestration, its comparators and its evidence qualifier (cpoc §4.2, §6, §7). Test-side
only: everything here drives the production CLI as real operating-system processes and reads the files it
wrote. Nothing in this module constructs or continues a simulation; it never imports the code under test to
produce an expected value (hashes and files are compared as bytes)."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FIXTURE = os.path.join(ROOT, "tests", "cpoc", "witness", "fixtures", "bursty_seed7_F10_N3_C4.csv")
#: sha256 of the committed fixture file (cpoc §4.2: "committed as a fixture file with its hash")
FIXTURE_SHA256 = "d6f98ed53f03c212b68a2c443678af4a28cea0da16eb1011f2d7447a2803da0d"
T = 12
F, N, C = 10, 3, 4
SURFACE = ["elevator_positions.csv", "position_log_long.csv", "passengers.csv", "summary.json", "observations.md",
           "run_identity.json", "events.jsonl", "tick_records.jsonl"]
CLEAN_ENV = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}  # nothing inherited from A, the test or the shell


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def jsonl(path: str) -> list[dict]:
    return [json.loads(line) for line in read(path).decode().splitlines()]


def cli(*args: str, env: dict | None = None):
    done = subprocess.run([sys.executable, "-B", "-m", "elevator.cli", *args], capture_output=True, text=True,
                          cwd=ROOT, env=CLEAN_ENV if env is None else env)
    out = dict(ln.split(": ", 1) for ln in done.stdout.splitlines() if ": " in ln)
    return done.returncode, out, done.stderr


def common(policy: str) -> list[str]:
    return ["--requests", FIXTURE, "--floors", str(F), "--elevators", str(N), "--capacity", str(C),
            "--policy", policy]


def pid_gone(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    return False


def wait_for(path: str, text: str, timeout: float = 60.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if os.path.exists(path) and text in read(path).decode():
            return True
        time.sleep(0.03)
    return False


def store_execution(store: str) -> str:
    names = [n for n in os.listdir(store) if n != "store.json"]
    assert len(names) == 1, names
    return names[0]


@dataclass
class Evidence:
    policy: str
    out: str
    store: str
    store_id: str
    run_id: str
    r_id: str = ""
    a_id: str = ""
    r_pid: int = 0
    a_pid: int = 0
    b_pid: int = 0
    a_returncode: int | None = None
    a_gone: bool = False
    b_returncode: int | None = None
    b_argv: list = field(default_factory=list)
    b_env: dict = field(default_factory=dict)
    d12: bytes = b""
    d_A: str = ""
    receipt: dict = field(default_factory=dict)
    r_stdout: dict = field(default_factory=dict)
    b_stdout: dict = field(default_factory=dict)

    def run_dir(self, eid: str) -> str:
        return os.path.join(self.out, self.run_id, eid)

    def store_log(self) -> list[dict]:
        return jsonl(os.path.join(self.store, self.a_id, "operational.jsonl"))

    def document(self) -> str:
        return os.path.join(self.store, self.a_id, "run.json")


def run_witness(tmp: str, policy: str, *, kill_a: bool = True, do_b: bool = True) -> Evidence:
    """Steps 1 to 5 of cpoc §4.2: R to completion; A to its checkpoint then SIGKILL; B fresh. Comparison and
    evidence checks are separate functions."""
    out, store = os.path.join(tmp, "out"), os.path.join(tmp, "S")
    code, init, err = cli("store", "init", store)
    assert code == 0, err
    ev = Evidence(policy, out, store, init["store_id"], run_id="")
    # 1. Reference Execution R: no Store, outputs to out/
    code, r, err = cli("simulate", *common(policy), "--witness-instrumentation", "--out", out)
    assert code == 0, err
    ev.r_id, ev.run_id, ev.r_stdout = r["execution_id"], r["run_id"], r
    ev.r_pid = jsonl(os.path.join(ev.run_dir(ev.r_id), "operational.jsonl"))[0]["payload"]["pid"]
    # 2. Execution A: checkpoint at 12, pause, hold its in-memory state
    a = subprocess.Popen([sys.executable, "-B", "-m", "elevator.cli", "simulate", *common(policy), "--store", store,
                          "--checkpoint-at", str(T), "--pause-after-checkpoint", "--witness-instrumentation",
                          "--out", out], cwd=ROOT, env=CLEAN_ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ev.a_pid = a.pid
    deadline = time.time() + 60
    while time.time() < deadline and not [n for n in os.listdir(store) if n != "store.json"]:
        time.sleep(0.03)
    ev.a_id = store_execution(store)
    assert wait_for(os.path.join(store, ev.a_id, "operational.jsonl"), "CHECKPOINT_WRITTEN"), "A never checkpointed"
    assert a.poll() is None  # A is alive and blocked
    ev.receipt = next(r for r in ev.store_log() if r["kind"] == "CHECKPOINT_WRITTEN")
    ev.d_A = ev.receipt["payload"]["document_sha256"]
    if kill_a:
        # 3. SIGKILL, wait, confirm death by signal 9 and that the PID is gone; re-read the document
        a.send_signal(signal.SIGKILL)
        a.wait()
        ev.a_returncode, ev.a_gone = a.returncode, pid_gone(a.pid)
    ev.d12 = read(ev.document())
    # 4./5. Process B: a fresh interpreter with only --store --resume --witness-instrumentation and an output dir
    ev.b_argv = [sys.executable, "-B", "-m", "elevator.cli", "resume", "--store", store, "--resume", ev.a_id,
                 "--witness-instrumentation", "--out", out]
    ev.b_env = dict(CLEAN_ENV)
    if do_b:
        done = subprocess.run(ev.b_argv, capture_output=True, text=True, cwd=ROOT, env=ev.b_env)
        ev.b_returncode = done.returncode
        ev.b_stdout = dict(ln.split(": ", 1) for ln in done.stdout.splitlines() if ": " in ln)
    if not kill_a:
        a.send_signal(signal.SIGKILL)  # cleanup only; this variant is never CPOC evidence
        a.wait()
        ev.a_returncode = None
    pids = [r["payload"]["pid"] for r in ev.store_log() if r["kind"] == "LOAD_ADMITTED"]
    ev.b_pid = pids[0] if pids else 0
    return ev


# --- comparators: each returns a list of failure strings; [] means the check passed -----------------------------

def compare_history(ev_run_dir_r: str, ev_run_dir_b: str, d12: bytes) -> list[str]:
    failures = []
    t = json.loads(d12)["snapshot"]["t"]
    r_events, b_events = read(os.path.join(ev_run_dir_r, "events.jsonl")).splitlines(), \
        read(os.path.join(ev_run_dir_b, "events.jsonl")).splitlines()
    r_ticks, b_ticks = read(os.path.join(ev_run_dir_r, "tick_records.jsonl")).splitlines(), \
        read(os.path.join(ev_run_dir_b, "tick_records.jsonl")).splitlines()
    split = len(json.loads(d12)["simulation_history"]["events"])
    if b_ticks[t:] != r_ticks[t:]:
        failures.append("tick_records for t >= checkpoint differ")
    if [e for e in b_events[split:]] != [e for e in r_events[split:]]:
        failures.append("events after the last event of the checkpoint prefix differ")
    prefix = json.loads(d12)["simulation_history"]
    canon = lambda o: json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    if [canon(e) for e in prefix["events"]] + b_events[split:] != r_events:
        failures.append("document prefix + continuation events != reference events")
    if [canon(x) for x in prefix["tick_records"]] + b_ticks[t:] != r_ticks:
        failures.append("document prefix + continuation tick_records != reference tick_records")
    if read(os.path.join(ev_run_dir_r, "events.jsonl")) != read(os.path.join(ev_run_dir_b, "events.jsonl")) or \
            read(os.path.join(ev_run_dir_r, "tick_records.jsonl")) != read(os.path.join(ev_run_dir_b, "tick_records.jsonl")):
        failures.append("complete Simulation History files differ")
    return failures


def compare_surface(r_dir: str, b_dir: str) -> list[str]:
    failures = []
    for name in SURFACE:
        if read(os.path.join(r_dir, name)) != read(os.path.join(b_dir, name)):
            failures.append(f"{name} differs")
    return failures


def surface_leaks(directory: str, forbidden: list[str]) -> list[str]:
    """N18: no execution fact in any Reproducible Output Surface file."""
    found = []
    for name in SURFACE:
        text = read(os.path.join(directory, name)).decode()
        found += [f"{name} contains {w}" for w in forbidden if w in text]
    return found


def check_anti_recomputation(records: list[dict], pid: int, t: int, final_tick: int) -> list[str]:
    """cpoc §4.2 step 7: this process's DIAGNOSTIC records name no tick below t, the first names t, and their
    count equals final - t + 1."""
    ticks = [r["tick"] for r in records if r["kind"] == "DIAGNOSTIC" and r["payload"]["pid"] == pid]
    failures = []
    if not ticks:
        return ["no DIAGNOSTIC records"]
    if min(ticks) < t:
        failures.append(f"names tick {min(ticks)} below {t}")
    if ticks[0] != t:
        failures.append(f"first names {ticks[0]}, not {t}")
    if len(ticks) != final_tick - t + 1:
        failures.append(f"count {len(ticks)} != {final_tick - t + 1}")
    if ticks != list(range(ticks[0], ticks[0] + len(ticks))):
        failures.append("ticks are not contiguous and in order")
    return failures


def kinds(records: list[dict], pid: int) -> list[str]:
    return [r["kind"] for r in records if r["payload"]["pid"] == pid]


def qualify(*, store_bound: bool, first_pid: int, first_returncode: int | None, first_gone: bool, cont_pid: int,
            log: list[dict], d12_present: bool) -> str:
    """The harness's evidence qualifier (cpoc §6 rows 31, 32, 34; plan cut 10): the label a run may carry."""
    if not store_bound:
        return "REFUSED_NEVER_BOUND"
    receipts = {r["kind"] for r in log}
    if cont_pid == first_pid or "LOAD_ADMITTED" not in receipts:
        return "REFUSED_PROCESS_LOCAL"
    if first_returncode != -signal.SIGKILL or not first_gone:
        return "REFUSED_FIRST_PROCESS_NOT_KILLED"
    if "CHECKPOINT_WRITTEN" not in receipts or not d12_present:
        return "EVIDENCE_INCOMPLETE"
    if not {"RESUMED", "FINALITY_WRITTEN"} <= receipts:
        return "EVIDENCE_INCOMPLETE"
    return "CPOC_EVIDENCE"


def qualify_witness(ev: Evidence) -> str:
    log = ev.store_log()
    return qualify(store_bound=True, first_pid=ev.a_pid, first_returncode=ev.a_returncode, first_gone=ev.a_gone,
                   cont_pid=ev.b_pid, log=log, d12_present=bool(ev.d12))
