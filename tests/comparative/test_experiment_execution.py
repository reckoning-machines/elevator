"""Cut 8 executed-Experiment tests (testing_contract §4). The Experiment below is a small test fixture for
the mechanics (paired Traces, re-execution, separation of execution facts, failed Runs); it is not the
default Experiment and its results are not evidence of anything about the policies."""

import json
import os
import re
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

import pytest

from elevator import api, cli, harness as H
from elevator.domain import establish_code_identity, normalize_requests
from elevator.scenarios import Scenario, generate

FIXTURE = dict(scenarios=[("uniform", {"num_requests": 12, "horizon": 20}),
                          ("bursty", {"num_requests": 12, "horizon": 20}),
                          ("capacity_stress", {"num_requests": 9})], seeds=[0, 1, 2])


def definition():
    return H.ExperimentDefinition.create(6, 2, 3, FIXTURE["scenarios"], seeds=FIXTURE["seeds"])


def execute(d=None, out=None):
    identity = establish_code_identity().identity
    return H.execute_experiment(d or definition(), identity, cli.run_executor(identity), output_dir=out)


def test_same_trace_hash_across_policies():
    d = definition()
    ex = execute(d)
    assert len(ex.results) == 3 * 3 * 3
    F, N, C = d.building
    for s, scenario in enumerate(d.document["scenarios"]):
        for seed in d.seeds:
            rows = [r for r in ex.results if (r.scenario, r.seed) == (s, seed)]
            assert len(rows) == 3 and len({r.trace_hash for r in rows}) == 1  # one Trace hash for every policy
            expected = generate(Scenario(scenario["pattern"], dict(scenario["parameters"]), seed), F, N, C)
            assert rows[0].trace_hash == expected.trace_hash  # and it is the generated Trace's hash
            assert len({r.run_id for r in rows}) == 3  # three distinct Runs: the policy is in the run_id
    H.check_complete_and_paired(d, ex.results)


def test_experiment_reexecution_identical(tmp_path):
    d = definition()
    a, b = execute(d, str(tmp_path / "a")), execute(d, str(tmp_path / "b"))
    # experiment_results.json: byte-identical, with the same experiment execution id
    assert a.results_bytes() == b.results_bytes() and a.experiment_execution_id == b.experiment_execution_id
    assert json.loads(a.results_bytes())["experiment_execution_id"] == a.experiment_execution_id
    assert [r.run_id for r in a.results] == [r.run_id for r in b.results]
    # experiment_execution.json differs in per-Run execution_ids, paths and timestamps, and nowhere else
    ma = json.loads(a.execution_metadata_bytes(pid=101, started_at="2026-11-05T10:00:00Z", ended_at="2026-11-05T10:00:01Z"))
    mb = json.loads(b.execution_metadata_bytes(pid=202, started_at="2026-11-06T09:00:00Z", ended_at="2026-11-06T09:00:07Z"))
    assert ma != mb
    assert all(x["execution_id"] != y["execution_id"] and x["output_path"] != y["output_path"]
               for x, y in zip(ma["runs"], mb["runs"]))
    for m in (ma, mb):
        for run in m["runs"]:
            run.pop("execution_id"), run.pop("output_path")
        m.pop("pid"), m.pop("started_at"), m.pop("ended_at")
    assert ma == mb
    # every Run's Reproducible Output Surface is byte-identical across the two executions
    for fa, fb in zip(a.run_facts, b.run_facts):
        assert fa["output_path"] != fb["output_path"] and fa["execution_id"] != fb["execution_id"]
        for name in ("elevator_positions.csv", "position_log_long.csv", "passengers.csv", "summary.json",
                     "observations.md", "run_identity.json", "events.jsonl", "tick_records.jsonl"):
            with open(os.path.join(fa["output_path"], name), "rb") as x, open(os.path.join(fb["output_path"], name), "rb") as y:
                assert x.read() == y.read(), (fa, name)


def test_experiment_results_surface_excludes_execution_facts(tmp_path):
    ex = execute(out=str(tmp_path / "runs"))
    results = ex.results_bytes().decode()
    forbidden = [f["execution_id"] for f in ex.run_facts] + [f["output_path"] for f in ex.run_facts] + [str(tmp_path)]
    assert len(forbidden) > 27 and all(w not in results for w in forbidden)  # no execution_id, path or tmp location
    assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", results) and f'"pid":{os.getpid()}' not in results
    keys = set(re.findall(r'"([a-z_]+)":', results))
    assert not keys & {"execution_id", "output_path", "pid", "started_at", "ended_at", "operational"}
    # negative control: the same scan finds a leak if one is planted
    leaked = results[:-1] + ',"execution_id":"' + ex.run_facts[0]["execution_id"] + '"}'
    assert any(w in leaked for w in forbidden)
    # the facts exist, but only in the separate metadata
    meta = ex.execution_metadata_bytes(pid=os.getpid(), started_at="2026-11-05T10:00:00Z").decode()
    assert all(f["execution_id"] in meta for f in ex.run_facts)


def test_paired_differences_in_an_executed_experiment_match_an_independent_computation():
    d = definition()
    ex = execute(d)
    doc = json.loads(ex.results_bytes())
    runs = {(r["scenario"], r["seed"], r["policy"]): r for r in doc["runs"]}
    cost = d.policy_index("cost_based")
    for s in range(d.num_scenarios):
        entry = next(a for a in doc["aggregates"] if (a["scenario"], a["policy"]) == (s, cost))
        for b in (0, 1):
            diffs = [Fraction(runs[(s, seed, cost)]["summary"]["wait"]["p95"]) - Fraction(runs[(s, seed, b)]["summary"]["wait"]["p95"])
                     for seed in d.seeds if runs[(s, seed, cost)]["summary"].get("wait", {}).get("p95") is not None
                     and runs[(s, seed, b)]["summary"].get("wait", {}).get("p95") is not None]
            block = entry["paired_against"][str(b)]["wait.p95"]
            assert block["n_pairs"] == len(diffs) == 3
            assert (block["better"], block["equal"], block["worse"]) == (
                sum(x < 0 for x in diffs), sum(x == 0 for x in diffs), sum(x > 0 for x in diffs))
            mean = sum(diffs) / len(diffs)
            independent = str((Decimal(mean.numerator) / Decimal(mean.denominator)).quantize(
                Decimal("0.001"), rounding=ROUND_HALF_UP))
            assert block["mean"] == independent, (block, independent)
            med = sorted(diffs)[1]  # three pairs: the middle difference
            assert block["median"] == str((Decimal(med.numerator) / Decimal(med.denominator)).quantize(
                Decimal("0.001"), rounding=ROUND_HALF_UP)), block
    # every cell reports K, halted_count and the per-seed vectors
    for a in doc["aggregates"]:
        assert a["K"] == 3 and a["halted_count"] == 0 and len(a["metrics"]["wait.p95"]["per_seed"]) == 3


def test_a_failed_run_inside_an_experiment_is_recorded_halted_and_the_experiment_continues(monkeypatch):
    class Raises:
        def assign(self, view, request):
            raise RuntimeError("boom")

    real = api.make_policy
    monkeypatch.setattr(api, "make_policy", lambda name, params=None: Raises() if name == "cost_based" else real(name, params))
    d = definition()
    ex = execute(d)
    assert len(ex.results) == 27  # nothing dropped
    doc = json.loads(ex.results_bytes())
    cost = d.policy_index("cost_based")
    for r in ex.results:
        if r.policy == cost:
            assert (r.standing, r.halt_reason) == ("HALTED", "POLICY_ERROR")
            assert r.summary["unserved"] == r.summary["n"] and r.summary["completed"] == 0
        else:
            assert r.standing == "COMPLETED"
    for a in doc["aggregates"]:
        if a["policy"] == cost:
            assert (a["K"], a["halted_count"]) == (3, 3) and len(a["halted"]) == 3
            assert all(h["halt_reason"] == "POLICY_ERROR" for h in a["halted"])
            assert a["metrics"]["wait.p95"]["n_defined"] == 0 and a["metrics"]["wait.p95"]["mean"] is None
            for b in ("0", "1"):  # no paired value over halted runs
                assert a["paired_against"][b]["wait.p95"]["n_pairs"] == 0
        else:
            assert a["halted_count"] == 0 and a["metrics"]["wait.p95"]["n_defined"] == 3
    # the Traces were still shared across policies: the halted Runs ran on the same Trace
    H.check_complete_and_paired(d, ex.results)


def test_per_policy_regeneration_is_caught_during_execution():
    """Negative control on the real path: an executor that hands one policy a different Trace is caught by
    the harness's own pairing guard, so the proper path's silence means something."""
    d = definition()
    identity = establish_code_identity().identity
    proper = cli.run_executor(identity)

    def regenerating(trace, configuration, output_dir):
        if configuration.policy == "cost_based":
            trace = normalize_requests([(0, "x", 0, 1)], configuration.num_floors)  # another Trace for this policy
        return proper(trace, configuration, output_dir)

    with pytest.raises(H.ExperimentIntegrityError, match="not the shared"):
        H.execute_experiment(d, identity, regenerating)


def test_default_seeds_and_policies_execute_all_cells():
    d = H.ExperimentDefinition.create(6, 2, 3, [("adversarial", {"num_requests": 4})])  # seeds 0..19, three policies
    ex = execute(d)
    assert len(ex.results) == 20 * 3 and d.seeds == tuple(range(20))
    doc = json.loads(ex.results_bytes())
    assert all(len(a["metrics"]["n"]["per_seed"]) == 20 for a in doc["aggregates"])
