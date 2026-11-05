"""Cut 8 reproducibility tests: separate processes, the CLI, and Experiment re-execution across processes."""

import json
import os
import subprocess
import sys

from elevator import cli, harness as H
from elevator.domain import establish_code_identity
from elevator.scenarios import Scenario, generate
from tests.comparative.test_experiment_execution import FIXTURE

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV = {**os.environ, "PYTHONPATH": ROOT}
SURFACE = ("elevator_positions.csv", "position_log_long.csv", "passengers.csv", "summary.json", "observations.md",
           "run_identity.json", "events.jsonl", "tick_records.jsonl")


def run_cli(*args, flags=("-B",), env=None):
    done = subprocess.run([sys.executable, *flags, "-m", "elevator.cli", *args], capture_output=True, text=True,
                          cwd=ROOT, env=env or ENV)
    out = dict(ln.split(": ", 1) for ln in done.stdout.splitlines() if ": " in ln)
    return done.returncode, out, done.stderr


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def test_same_inputs_same_history(tmp_path):
    """The same (config, trace, policy) simulated in two separate processes: the Simulation History and every
    file of the Reproducible Output Surface are byte-identical, including run_identity.json;
    execution_metadata.json differs in execution_id, pid and timestamps and nowhere else."""
    script = (
        "import hashlib, json, sys\n"
        "from elevator import api\n"
        "from elevator.domain import canonical_json\n"
        "rows=[(0,'a',0,5),(0,'b',4,1),(2,'c',3,0),(5,'d',1,5),(5,'e',5,2)]\n"
        "r=api.simulate(rows,3,6,2,policy='cost_based',initial_floors=[0,3,5],output_dir=sys.argv[1])\n"
        "print(json.dumps({'run_id':r.run_id,'history':hashlib.sha256(canonical_json(r.record.history)).hexdigest(),"
        "'path':r.output_path,'execution_id':r.execution_id}))\n")
    outs = []
    for name in ("a", "b"):
        done = subprocess.run([sys.executable, "-B", "-c", script, str(tmp_path / name)], capture_output=True,
                              text=True, cwd=ROOT, env=ENV, check=True)
        outs.append(json.loads(done.stdout))
    a, b = outs
    assert a["run_id"] == b["run_id"] and a["history"] == b["history"] and a["execution_id"] != b["execution_id"]
    for name in SURFACE:
        assert read(os.path.join(a["path"], name)) == read(os.path.join(b["path"], name)), name
    ma = json.loads(read(os.path.join(a["path"], "execution_metadata.json")))
    mb = json.loads(read(os.path.join(b["path"], "execution_metadata.json")))
    assert {k for k in ma if ma[k] != mb[k]} <= {"execution_id", "pid", "started_at", "ended_at"}
    assert ma["execution_id"] != mb["execution_id"] and ma["pid"] != mb["pid"] and ma["run_id"] == mb["run_id"]
    la = [json.loads(x) for x in read(os.path.join(a["path"], "operational.jsonl")).splitlines()]
    lb = [json.loads(x) for x in read(os.path.join(b["path"], "operational.jsonl")).splitlines()]
    assert [r["op_seq"] for r in la] == [r["op_seq"] for r in lb] == [1, 2]
    assert la[0]["payload"]["pid"] != lb[0]["payload"]["pid"] and la[0]["payload"]["code_identity"] == lb[0]["payload"]["code_identity"]


def test_cli_simulate_smoke_and_reproducibility(tmp_path):
    csv_path = tmp_path / "requests.csv"
    csv_path.write_text("time,id,source,dest\n0,p0,0,4\n0,p1,2,4\n")
    args = ("simulate", "--requests", str(csv_path), "--floors", "5", "--elevators", "1", "--capacity", "1")
    code1, out1, _ = run_cli(*args, "--out", str(tmp_path / "o1"))
    code2, out2, _ = run_cli(*args, "--out", str(tmp_path / "o2"))
    assert code1 == code2 == 0
    assert (out1["standing"], out1["final_tick"]) == ("COMPLETED", "8")
    assert out1["run_id"] == out2["run_id"] and out1["execution_id"] != out2["execution_id"]
    for name in SURFACE:
        assert read(os.path.join(out1["output"], name)) == read(os.path.join(out2["output"], name)), name
    # without a header row, the same file means the same Run
    csv_path.write_text("0,p0,0,4\n0,p1,2,4\n")
    code3, out3, _ = run_cli(*args)
    assert code3 == 0 and out3["run_id"] == out1["run_id"] and out3["output"] == "(none)"
    # a CSV and the Python function agree: one normalisation boundary
    from elevator import api
    assert api.simulate([(0, "p0", 0, 4), (0, "p1", 2, 4)], 1, 5, 1).run_id == out1["run_id"]


def test_cli_scenario_mode_matches_the_same_rows_as_a_file(tmp_path):
    scenario = Scenario("bursty", {"num_requests": 14, "horizon": 25}, 5)
    trace = generate(scenario, 7, 2, 3)
    csv_path = tmp_path / "gen.csv"
    csv_path.write_text("".join(f"{t},{i},{o},{d}\n" for t, i, o, d in trace.canonical_rows()))
    base = ("--floors", "7", "--elevators", "2", "--capacity", "3", "--policy", "nearest_car")
    c1, a, _ = run_cli("simulate", "--scenario", "bursty", "--seed", "5", "--param", "num_requests=14",
                       "--param", "horizon=25", *base)
    c2, b, _ = run_cli("simulate", "--requests", str(csv_path), *base)
    assert c1 == c2 == 0 and a["run_id"] == b["run_id"]


def test_cli_exit_codes_distinguish_each_failure_class(tmp_path):
    good = tmp_path / "ok.csv"
    good.write_text("0,p0,0,4\n")
    bad = tmp_path / "samefloor.csv"
    bad.write_text("0,p0,2,2\n")
    base = ("--floors", "5", "--elevators", "1", "--capacity", "1")
    code, out, err = run_cli("simulate", "--requests", str(good), *base)
    assert code == 0 and out["standing"] == "COMPLETED"
    # refusals: invalid input, unknown policy, unreadable file, invalid scenario parameter
    for args in (("simulate", "--requests", str(bad), *base), ("simulate", "--requests", str(good), *base, "--policy", "lookahead"),
                 ("simulate", "--requests", str(tmp_path / "missing.csv"), *base),
                 ("simulate", "--scenario", "uniform", "--seed", "1", "--param", "num_requests=4", *base),
                 ("simulate", "--scenario", "poisson", "--seed", "1", "--param", "num_requests=4", *base),
                 ("simulate", "--requests", str(good), "--floors", "1", "--elevators", "1", "--capacity", "1")):
        code, out, err = run_cli(*args)
        assert code == 3 and err.startswith("refused:"), (args, err)
    # a halted simulation is reported as halted, with its reason, and never as success
    code, out, err = run_cli("simulate", "--requests", str(good), *base, "--max-ticks", "2")
    assert code == 4 and out["standing"] == "HALTED" and out["halt_reason"] == "HORIZON_EXCEEDED"
    # an output that cannot be written
    blocker = tmp_path / "file"
    blocker.write_text("x")
    code, out, err = run_cli("simulate", "--requests", str(good), *base, "--out", str(blocker))
    assert code == 5 and err.startswith("output error:") and blocker.read_text() == "x"
    # usage errors
    assert run_cli("simulate", "--requests", str(good), "--elevators", "1", "--capacity", "1")[0] == 2
    assert run_cli("simulate", "--scenario", "uniform", *base)[0] == 2  # no --seed
    # an unsupported environment (no -B): caches are redirected so the negative run cannot pollute the package
    env = {**ENV, "PYTHONPYCACHEPREFIX": str(tmp_path / "caches")}
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    code, out, err = run_cli("simulate", "--requests", str(good), *base, flags=(), env=env)
    assert code == 6 and "UNSUPPORTED_EXECUTION_ENVIRONMENT" in err
    assert not os.path.isdir(os.path.join(ROOT, "elevator", "__pycache__"))


CONFIG = {"configuration": {"num_floors": 6, "num_elevators": 2, "capacity": 3},
          "scenarios": [{"pattern": p, "parameters": q} for p, q in FIXTURE["scenarios"]], "seeds": FIXTURE["seeds"]}


def experiment_dir(out):
    (name,) = [n for n in os.listdir(out) if os.path.isfile(os.path.join(out, n, "experiment_results.json"))]
    return os.path.join(out, name)


def test_cli_experiment_is_reproducible_across_processes(tmp_path):
    config = tmp_path / "exp.json"
    config.write_text(json.dumps(CONFIG))
    c1, a, _ = run_cli("experiment", "--config", str(config), "--out", str(tmp_path / "e1"))
    c2, b, _ = run_cli("experiment", "--config", str(config), "--out", str(tmp_path / "e2"))
    assert c1 == c2 == 0 and a["runs"] == b["runs"] == "27" and a["halted_count"] == "0"
    assert a["experiment_execution_id"] == b["experiment_execution_id"] and a["definition_hash"] == b["definition_hash"]
    d1, d2 = experiment_dir(str(tmp_path / "e1")), experiment_dir(str(tmp_path / "e2"))
    assert read(os.path.join(d1, "experiment_results.json")) == read(os.path.join(d2, "experiment_results.json"))
    m1, m2 = (json.loads(read(os.path.join(d, "experiment_execution.json"))) for d in (d1, d2))
    assert m1 != m2 and m1["experiment_execution_id"] == m2["experiment_execution_id"]
    assert all(x["execution_id"] != y["execution_id"] for x, y in zip(m1["runs"], m2["runs"]))
    # a fresh process and this process agree byte for byte
    identity = establish_code_identity().identity
    local = H.execute_experiment(H.ExperimentDefinition.from_document(CONFIG), identity, cli.run_executor(identity))
    assert local.results_bytes() == read(os.path.join(d1, "experiment_results.json"))
    # evidence is never overwritten, and the refusal comes before anything runs
    before = sorted(os.listdir(tmp_path / "e1"))
    code, out, err = run_cli("experiment", "--config", str(config), "--out", str(tmp_path / "e1"))
    assert code == 5 and sorted(os.listdir(tmp_path / "e1")) == before


def test_cli_experiment_refuses_bad_definitions_before_running(tmp_path):
    cases = {
        "float": json.dumps(CONFIG).replace('"num_requests": 12', '"num_requests": 12.5', 1),
        "unknown key": json.dumps({**CONFIG, "max_ticks": 5}),
        "sparse cross-parameter": json.dumps({**CONFIG, "scenarios": [
            {"pattern": "sparse", "parameters": {"num_requests": 1002, "g": 10**6, "j": 0}}]}),
        "bad policy": json.dumps({**CONFIG, "policies": ["lookahead"]}),
        "not json": "{nope",
    }
    for label, text in cases.items():
        config = tmp_path / f"{label.replace(' ', '_')}.json"
        config.write_text(text)
        out = tmp_path / f"out_{label.replace(' ', '_')}"
        code, _, err = run_cli("experiment", "--config", str(config), "--out", str(out))
        assert code == 3, (label, err)
        assert not out.exists(), label  # nothing ran, nothing was written
    # summary-only writes the two experiment files and no per-Run directories
    config = tmp_path / "ok.json"
    config.write_text(json.dumps(CONFIG))
    code, out, _ = run_cli("experiment", "--config", str(config), "--out", str(tmp_path / "so"), "--summary-only")
    assert code == 0 and len(os.listdir(tmp_path / "so")) == 1
    assert sorted(os.listdir(out["output"])) == ["experiment_execution.json", "experiment_results.json"]
