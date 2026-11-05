"""Cut 8: the fixed Experiment of owner decision 010 and its committed evidence (testing_contract §4).

The fixed Experiment is a reproducible comparison fixture (floors 20, elevators 4, capacity 8; all nine
patterns; seeds 0..19; three policies; num_requests 100, and horizon 1000 for the six patterns that have
one). It is not a claim about real elevator traffic and these tests assert nothing about which policy is
better. It executes once per test session and every test below reads that one execution."""

import hashlib
import json
import os
import re
import subprocess
import sys
import time

import pytest

from elevator import cli, harness as H
from elevator.domain import Configuration, canonical_json, establish_code_identity, sha256_hex
from elevator.scenarios import PATTERNS, Scenario, generate

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFINITION_FILE = os.path.join(ROOT, "experiments", "default.json")
EVIDENCE_FILE = os.path.join(ROOT, "experiments", "default_experiment_results.json")
# pinned by decision record 010: the definition is fixed, so any edit to it is visible in review
DEFINITION_FILE_SHA256 = "1638535528720292505904982ee9042a51649226ca91786e422ba0cb6c4e9c1e"
DEFINITION_HASH = "6f1ba88ad116b124e5d1f03c78add35086e2d90c8cf3e552c59768e891729bdd"
PATTERN_ORDER = ["uniform", "up_peak", "down_peak", "bursty", "concentrated_origin", "concentrated_destination",
                 "capacity_stress", "sparse", "adversarial"]
WITH_HORIZON = {"uniform", "up_peak", "down_peak", "bursty", "concentrated_origin", "concentrated_destination"}


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def load_definition():
    return H.ExperimentDefinition.from_document(json.loads(read(DEFINITION_FILE)))


@pytest.fixture(scope="module")
def executed():
    definition = load_definition()
    identity = establish_code_identity().identity
    started = time.perf_counter()
    execution = H.execute_experiment(definition, identity, cli.run_executor(identity))
    return execution, time.perf_counter() - started


def test_fixed_experiment_definition_is_the_admitted_one():
    assert hashlib.sha256(read(DEFINITION_FILE)).hexdigest() == DEFINITION_FILE_SHA256
    d = load_definition()
    assert d.definition_hash == DEFINITION_HASH
    assert d.building == (20, 4, 8) and list(d.document["configuration"]["initial_floors"]) == [0, 0, 0, 0]
    assert d.seeds == tuple(range(20)) and [p["name"] for p in d.document["policies"]] == [
        "round_robin", "nearest_car", "cost_based"]
    assert [s["pattern"] for s in d.document["scenarios"]] == PATTERN_ORDER and set(PATTERN_ORDER) == set(PATTERNS)
    assert (d.num_scenarios, len(d.seeds), d.num_policies) == (9, 20, 3)
    for s in d.document["scenarios"]:
        params = dict(s["parameters"])
        assert params["num_requests"] == 100
        assert params.get("horizon") == (1000 if s["pattern"] in WITH_HORIZON else None)  # only where a pattern has one
    # every other parameter is the already-admitted default (evaluation §6.3)
    eff = {s["pattern"]: dict(s["parameters"]) for s in d.document["scenarios"]}
    assert (eff["bursty"]["k"], eff["bursty"]["w"]) == (3, 3)
    assert eff["concentrated_origin"]["m"] == eff["concentrated_destination"]["m"] == 2
    assert eff["capacity_stress"]["origin"] == 0 and (eff["sparse"]["g"], eff["sparse"]["j"]) == (2 * 19, 0)


def test_fixed_experiment_runs_all_540_with_paired_traces(executed):
    ex, _elapsed = executed
    d = ex.definition
    assert len(ex.results) == 540 and len({(r.scenario, r.seed, r.policy) for r in ex.results}) == 540
    H.check_complete_and_paired(d, ex.results)
    F, N, C = d.building
    units = 0
    for s, scenario in enumerate(d.document["scenarios"]):
        for seed in d.seeds:
            rows = [r for r in ex.results if (r.scenario, r.seed) == (s, seed)]
            assert len(rows) == 3 and len({r.trace_hash for r in rows}) == 1  # one Trace for all three policies
            expected = generate(Scenario(scenario["pattern"], dict(scenario["parameters"]), seed), F, N, C)
            assert rows[0].trace_hash == expected.trace_hash  # generated once, by the Cut-7 generator
            assert len({r.run_id for r in rows}) == 3
            units += 1
    assert units == 180
    # every Run completed: no halted Run, every passenger served
    assert all(r.standing == "COMPLETED" and r.summary["n"] == 100 and r.summary["completed"] == 100 and
               r.summary["unserved"] == 0 for r in ex.results)
    doc = json.loads(ex.results_bytes())
    assert len(doc["aggregates"]) == 27 and all(a["K"] == 20 and a["halted_count"] == 0 for a in doc["aggregates"])


def test_committed_experiment_evidence(executed):
    """The committed results match a fresh execution on behavioural content. The fields derived from the code
    identity (the experiment execution id and every run_id) change with any edit to the package, so they are
    checked for internal consistency with the recorded code identity instead; when the code identity is
    unchanged the two files must be byte-identical. A change in behaviour requires updating the committed
    file in the same change with a note."""
    ex, _elapsed = executed
    committed = json.loads(read(EVIDENCE_FILE))
    fresh = json.loads(ex.results_bytes())
    assert set(committed) == set(fresh) == {"aggregates", "code_identity", "definition", "definition_hash",
                                            "experiment_execution_id", "runs"}
    assert committed["definition_hash"] == DEFINITION_HASH == fresh["definition_hash"]
    assert committed["definition"] == fresh["definition"]
    # behavioural content: every Run's Trace hash, outcome and summary, and every aggregate
    assert len(committed["runs"]) == len(fresh["runs"]) == 540
    for c, f in zip(committed["runs"], fresh["runs"]):
        assert (c["scenario"], c["seed"], c["policy"]) == (f["scenario"], f["seed"], f["policy"])
        assert c["trace_hash"] == f["trace_hash"] and c["outcome"] == f["outcome"] and c["summary"] == f["summary"]
    assert committed["aggregates"] == fresh["aggregates"]
    # the code-identity-derived fields are consistent with the code identity the file records
    d = ex.definition
    assert committed["experiment_execution_id"] == sha256_hex(canonical_json([DEFINITION_HASH, committed["code_identity"]]))
    F, N, C = d.building
    configs = [Configuration.create(F, N, C, initial_floors=list(d.document["configuration"]["initial_floors"]),
                                    policy=p["name"], policy_params=dict(p["params"])) for p in d.document["policies"]]
    for c in committed["runs"]:
        want = sha256_hex(canonical_json([configs[c["policy"]].configuration_hash, c["trace_hash"],
                                          committed["code_identity"]]))
        assert c["run_id"] == want
    # unchanged code identity: byte-identical
    if fresh["code_identity"] == committed["code_identity"]:
        assert ex.results_bytes() == read(EVIDENCE_FILE)


def test_committed_evidence_holds_no_execution_fact():
    raw = read(EVIDENCE_FILE)
    text = raw.decode()
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", text)  # no execution_id
    assert not re.search(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", text)  # no wall-clock timestamp
    keys = set(re.findall(r'"([A-Za-z_.0-9]+)":', text))
    assert not keys & {"execution_id", "output_path", "pid", "started_at", "ended_at", "op_seq", "operational"}
    assert "experiment_execution_id" in keys  # the admitted, hash-derived identity, not a per-Run execution fact
    assert "/private" not in text and "/tmp" not in text and "/Users" not in text  # no path


def test_fixed_experiment_results_exclude_execution_facts(executed):
    ex, _ = executed
    raw = ex.results_bytes().decode()
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-", raw) and not re.search(r"\d{4}-\d{2}-\d{2}T", raw)
    assert not set(re.findall(r'"([a-z_]+)":', raw)) & {"execution_id", "output_path", "pid", "started_at", "ended_at"}


def test_fixed_experiment_reexecution_is_byte_identical_in_a_fresh_process(executed, tmp_path):
    ex, _ = executed
    env = {**os.environ, "PYTHONPATH": ROOT}
    done = subprocess.run([sys.executable, "-B", "-m", "elevator.cli", "experiment", "--config", DEFINITION_FILE,
                           "--out", str(tmp_path), "--summary-only"], capture_output=True, text=True, cwd=ROOT, env=env)
    assert done.returncode == 0, done.stderr
    out = dict(ln.split(": ", 1) for ln in done.stdout.splitlines() if ": " in ln)
    assert out["runs"] == "540" and out["halted_count"] == "0"
    assert out["experiment_execution_id"] == ex.experiment_execution_id and out["definition_hash"] == DEFINITION_HASH
    assert read(os.path.join(tmp_path, ex.experiment_execution_id, "experiment_results.json")) == ex.results_bytes()
    meta = json.loads(read(os.path.join(tmp_path, ex.experiment_execution_id, "experiment_execution.json")))
    assert len(meta["runs"]) == 540 and len({r["execution_id"] for r in meta["runs"]}) == 540  # own id per Run


def test_fixed_experiment_completes_and_its_elapsed_time_is_observed_not_required(executed, record_property):
    """The correctness requirement is that the fixed Experiment completes successfully; the elapsed time is
    observed performance evidence on this machine and is deliberately not a pass/fail threshold (decision 010
    §6). It is recorded here and in the cut-8 record with its environment."""
    ex, elapsed = executed
    assert len(ex.results) == 540 and all(r.standing == "COMPLETED" for r in ex.results)
    record_property("fixed_experiment_elapsed_seconds", round(elapsed, 1))
    print(f"\nfixed Experiment: 540 Runs in {elapsed:.1f} s (in-process, {sys.version.split()[0]})")
