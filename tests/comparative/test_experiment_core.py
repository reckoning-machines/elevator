"""Cut 8 comparative tests (testing_contract §4, §6): the Experiment definition, paired comparison,
null-aware aggregation and the result documents, on hand-built result sets. The Run-execution loop is
not part of this revision (see the cut-8 record), so nothing here runs an Experiment."""

import json
import random
import re

import pytest

from elevator import harness as H
from elevator.domain import Refusal, canonical_json
from elevator.scenarios import Scenario, ScenarioRefusal, generate

CODE = "c" * 64


def S(*, n=3, wait=None, total=None, tail="0.000", ratio=None, deferred=0, wrong=0, extra=None, makespan=10,
      util=("0.500",), travel="2.000", unserved=0):
    """A hand-built ``summary.json`` document (values exactly as reported)."""
    if n == 0:
        nulls = {k: None for k in ("min", "max", "mean", "median", "p95", "std")}
        return {"standing": "COMPLETED", "final_tick": 0, "n": 0, "completed": 0, "unserved": 0, "no_passengers": True,
                "wait": dict(nulls), "total": dict(nulls), "travel": {"mean": None}, "deferred": {"count": 0},
                "wrong_way": {"count": 0, "mean_extra": None}, "tail_share": None, "tail_ratio": None,
                "makespan": 0, "elevator_utilisation": ["0.000"] * len(util)}
    return {"standing": "COMPLETED", "final_tick": makespan, "n": n, "completed": n, "unserved": unserved,
            "wait": wait, "total": total or {"min": 1, "max": 9, "mean": "4.000", "median": "4.000", "p95": 9, "std": "1.000"},
            "travel": {"mean": travel}, "deferred": {"count": deferred},
            "wrong_way": {"count": wrong, "mean_extra": extra}, "tail_share": tail, "tail_ratio": ratio,
            "makespan": makespan, "elevator_utilisation": list(util)}


def W(p95, mean):
    return {"min": 0, "max": p95 + 1, "mean": mean, "median": mean, "p95": p95, "std": "1.000"}


def run(scenario, seed, policy, summary, *, trace="T", standing="COMPLETED", reason=None):
    return H.RunResult(scenario, seed, policy, f"run-{scenario}-{seed}-{policy}", f"{trace}{scenario}-{seed}",
                       standing, summary.get("final_tick", 0), reason, summary)


def halted(unserved, reason):
    return {"standing": "HALTED", "final_tick": 7, "halt_reason": reason, "n": 5, "completed": 5 - unserved,
            "unserved": unserved}


# --- paired differences, by hand ---------------------------------------------------------------

def test_paired_difference_arithmetic():
    # cost_based p95 wait per seed [3, 5, 4, 6, 2] against a baseline's [5, 5, 7, 3, 2] on the same seeds:
    # differences cost - baseline = [-2, 0, -3, +3, 0]: mean -2/5, median 0, better 2, equal 2, worse 1
    cost_p95, base_p95 = [3, 5, 4, 6, 2], [5, 5, 7, 3, 2]
    cost_mean, base_mean = ["1.500", "2.000", "1.250", "3.000", "0.500"], ["2.250", "2.000", "2.500", "1.000", "0.500"]
    cost = [run(0, i, 1, S(wait=W(p, m))) for i, (p, m) in enumerate(zip(cost_p95, cost_mean))]
    base = [run(0, i, 0, S(wait=W(p, m))) for i, (p, m) in enumerate(zip(base_p95, base_mean))]
    paired = H.paired_cell(cost, base)
    assert paired["wait.p95"] == {"n_pairs": 5, "mean": "-0.400", "median": "0.000", "better": 2, "equal": 2, "worse": 1}
    # decimal-string metrics are exact: differences 1.5-2.25, 0, 1.25-2.5, 3-1, 0 = -.75, 0, -1.25, +2, 0
    assert paired["wait.mean"] == {"n_pairs": 5, "mean": "0.000", "median": "0.000", "better": 2, "equal": 2, "worse": 1}
    # the sign convention is cost_based minus the baseline, reversed roles flip every sign and the counts
    reverse = H.paired_cell(base, cost)
    assert reverse["wait.p95"] == {"n_pairs": 5, "mean": "0.400", "median": "0.000", "better": 1, "equal": 2, "worse": 2}
    # pairing is by seed, not by position: shuffling one side changes nothing
    shuffled = list(reversed(base))
    assert H.paired_cell(cost, shuffled) == paired
    # an even number of pairs: the median is the mean of the two middle differences, rendered half away from zero
    c2 = [run(0, i, 1, S(wait=W(v, "1.000"))) for i, v in enumerate([1, 2, 3, 10])]
    b2 = [run(0, i, 0, S(wait=W(v, "1.000"))) for i, v in enumerate([2, 2, 5, 13])]
    assert H.paired_cell(c2, b2)["wait.p95"] == {"n_pairs": 4, "mean": "-1.500", "median": "-1.500", "better": 3,
                                                 "equal": 1, "worse": 0}
    # an average-first computation would not equal the paired one: the paired median is 0, the median
    # of the two unpaired medians (4 and 5) differs by 1; pairing is what removes between-trace variance
    assert sorted(cost_p95)[2] - sorted(base_p95)[2] == -1 != 0


# --- null aggregation, by hand ---------------------------------------------------------------------

def null_aggregation_cells():
    cost = [run(0, 10, 1, S(n=4, wait=W(4, "2.000"), tail="0.250", deferred=1, wrong=2, extra="1.500")),
            run(0, 11, 1, S(n=3, wait=W(2, "1.000"), tail="0.000", deferred=0, wrong=0, extra=None)),
            run(0, 12, 1, S(n=0)),
            run(0, 13, 1, S(n=5, wait=W(6, "3.000"), tail="0.200", deferred=2, wrong=1, extra="2.000"))]
    base = [run(0, 10, 0, S(n=4, wait=W(5, "2.500"), tail="0.500", deferred=2, wrong=3, extra="2.000")),
            run(0, 11, 0, S(n=3, wait=W(2, "1.000"), tail="0.000", deferred=0, wrong=0, extra=None)),
            run(0, 12, 0, S(n=0)),
            run(0, 13, 0, halted(3, "HORIZON_EXCEEDED"), standing="HALTED", reason="HORIZON_EXCEEDED")]
    return cost, base


def test_experiment_null_aggregation():
    cost, base = null_aggregation_cells()
    a = H.aggregate_cell(cost, 1)
    assert (a["K"], a["halted_count"], a["halted"]) == (4, 0, [])
    p95 = a["metrics"]["wait.p95"]  # the empty run is undefined: excluded, never zero
    assert p95 == {"n_defined": 3, "mean": "4.000", "median": "4.000", "per_seed": [4, 2, None, 6]}
    tail = a["metrics"]["tail_share"]  # n_defined excludes the empty run: mean (0.25 + 0 + 0.2) / 3
    assert tail == {"n_defined": 3, "mean": "0.150", "median": "0.200", "per_seed": ["0.250", "0.000", None, "0.200"]}
    # the empty run contributes its always-defined zeros: deferred.count and wrong_way.count are defined values
    assert a["metrics"]["deferred.count"] == {"n_defined": 4, "mean": "0.750", "median": "0.500", "per_seed": [1, 0, 0, 2]}
    assert a["metrics"]["wrong_way.count"]["n_defined"] == 4 and a["metrics"]["wrong_way.count"]["per_seed"] == [2, 0, 0, 1]
    assert a["metrics"]["n"]["per_seed"] == [4, 3, 0, 5] and a["metrics"]["makespan"]["per_seed"][2] == 0
    # wrong_way.mean_extra is null when there were no wrong-way passes: excluded, not zero
    extra = a["metrics"]["wrong_way.mean_extra"]
    assert extra == {"n_defined": 2, "mean": "1.750", "median": "1.750", "per_seed": ["1.500", None, None, "2.000"]}
    # a halted run contributes only to halted_count and to the listing of its unserved count and reason
    b = H.aggregate_cell(base, 1)
    assert (b["K"], b["halted_count"]) == (4, 1)
    assert b["halted"] == [{"seed": 13, "unserved": 3, "halt_reason": "HORIZON_EXCEEDED"}]
    assert b["metrics"]["wait.p95"] == {"n_defined": 2, "mean": "3.500", "median": "3.500", "per_seed": [5, 2, None, None]}
    assert b["metrics"]["deferred.count"] == {"n_defined": 3, "mean": "0.667", "median": "0.000", "per_seed": [2, 0, 0, None]}
    # elevator_utilisation is aggregated per elevator
    assert set(k for k in a["metrics"] if k.startswith("elevator_utilisation")) == {"elevator_utilisation.0"}
    # paired: only seeds where both Runs are COMPLETED and both values are defined
    paired = H.paired_cell(cost, base)
    assert paired["wait.p95"] == {"n_pairs": 2, "mean": "-0.500", "median": "-0.500", "better": 1, "equal": 1, "worse": 0}
    assert paired["deferred.count"] == {"n_pairs": 3, "mean": "-0.333", "median": "0.000", "better": 1, "equal": 2, "worse": 0}
    assert paired["tail_share"] == {"n_pairs": 2, "mean": "-0.125", "median": "-0.125", "better": 1, "equal": 1, "worse": 0}
    # with no defined pair the paired aggregate is null and reports n_pairs = 0
    nothing = H.paired_cell([run(0, 0, 1, S(n=0))], [run(0, 0, 0, S(n=0))])
    assert nothing["wait.mean"] == {"n_pairs": 0, "mean": None, "median": None, "better": None, "equal": None,
                                    "worse": None}
    assert nothing["deferred.count"]["n_pairs"] == 1 and nothing["deferred.count"]["equal"] == 1
    # a cell whose every value is undefined has n_defined 0 and null aggregates
    empty_cell = H.aggregate_cell([run(0, 0, 1, S(n=0)), run(0, 1, 1, S(n=0))], 1)
    assert empty_cell["metrics"]["wait.p95"] == {"n_defined": 0, "mean": None, "median": None, "per_seed": [None, None]}
    assert empty_cell["metrics"]["tail_share"]["n_defined"] == 0


# --- the fair-comparison witness and completeness --------------------------------------------------------

def definition():
    return H.ExperimentDefinition.create(6, 2, 3, [("uniform", {"num_requests": 10, "horizon": 20}),
                                                    ("adversarial", {"num_requests": 6})], seeds=[0, 1, 2])


def full_results(d, *, hash_for=None):
    out = []
    for s in range(d.num_scenarios):
        for seed in d.seeds:
            for p in range(d.num_policies):
                out.append(run(s, seed, p, S(wait=W(s + seed + p, "1.000")),
                               trace=(hash_for(s, seed, p) if hash_for else "T")))
    return out


def test_same_trace_hash_across_policies():
    d = definition()
    H.check_complete_and_paired(d, full_results(d))  # one Trace hash per (scenario, seed) across all policies
    # a doctored result where one policy saw another Trace is caught
    bad = full_results(d, hash_for=lambda s, seed, p: "X" if (s, seed, p) == (1, 2, 2) else "T")
    with pytest.raises(H.ExperimentIntegrityError, match="not paired"):
        H.check_complete_and_paired(d, bad)


def test_paired_identity_witness_catches_per_policy_regeneration():
    """Negative control. A local helper that accidentally regenerates the Trace per policy, giving one
    policy a different seed, produces different Trace hashes; the witness fails on it, so its silence on
    the proper one-Trace-per-(scenario, seed) path means something."""
    d = H.ExperimentDefinition.create(6, 2, 3, [("uniform", {"num_requests": 12, "horizon": 25})], seeds=[0, 1, 2, 3])
    F, N, C = d.building

    def results(regenerate_per_policy):
        out = []
        for seed in d.seeds:
            shared = generate(Scenario("uniform", dict(d.document["scenarios"][0]["parameters"]), seed), F, N, C)
            for p in range(d.num_policies):
                trace = shared
                if regenerate_per_policy and p == 2:  # the bug: the third policy's Trace uses another seed
                    trace = generate(Scenario("uniform", dict(d.document["scenarios"][0]["parameters"]), seed + 100),
                                     F, N, C)
                out.append(H.RunResult(0, seed, p, f"r{seed}{p}", trace.trace_hash, "COMPLETED", 9,
                                       None, S(wait=W(3, "1.000"))))
        return out

    H.check_complete_and_paired(d, results(False))
    with pytest.raises(H.ExperimentIntegrityError, match="different Traces"):
        H.check_complete_and_paired(d, results(True))


def test_a_failed_run_cannot_be_silently_dropped():
    d = definition()
    full = full_results(d)
    with pytest.raises(H.ExperimentIntegrityError, match="missing"):
        H.check_complete_and_paired(d, full[:-1])  # a Run left out of the results
    with pytest.raises(H.ExperimentIntegrityError, match="more than once"):
        H.check_complete_and_paired(d, full + [full[0]])
    foreign = full[:-1] + [run(9, 0, 0, S(wait=W(1, "1.000")))]
    with pytest.raises(H.ExperimentIntegrityError):
        H.check_complete_and_paired(d, foreign)
    with pytest.raises(H.ExperimentIntegrityError):
        H.results_document(d, CODE, full[:-1])  # the document cannot be built from an incomplete set
    # a halted Run is present and counted, not omitted
    withheld = [run(r.scenario, r.seed, r.policy, halted(2, "POLICY_ERROR"), standing="HALTED", reason="POLICY_ERROR")
                if (r.scenario, r.seed, r.policy) == (0, 1, 2) else r for r in full]
    doc = H.results_document(d, CODE, withheld)
    assert len(doc["runs"]) == len(full)
    cell = next(a for a in doc["aggregates"] if (a["scenario"], a["policy"]) == (0, 2))
    assert (cell["K"], cell["halted_count"], cell["halted"]) == (3, 1, [{"seed": 1, "unserved": 2, "halt_reason": "POLICY_ERROR"}])


# --- the definition and its identity ----------------------------------------------------------------

def test_definition_identity_is_over_effective_parameters():
    a = H.ExperimentDefinition.create(8, 2, 3, [("sparse", {"num_requests": 5})], seeds=[0, 1])
    # defaults omitted or written out give one definition, one hash
    b = H.ExperimentDefinition.create(8, 2, 3, [("sparse", {"num_requests": 5, "g": 14, "j": 0})], seeds=[0, 1],
                                      initial_floors=[0, 0], policies=["round_robin", "nearest_car", "cost_based"])
    assert a.definition_hash == b.definition_hash and a.document == b.document
    assert a.document["scenarios"][0]["parameters"] == {"g": 14, "j": 0, "num_requests": 5}
    assert a.document["policies"][2] == {"name": "cost_based", "params": {
        "age_scale": 7, "tail_threshold": 14, "w_marginal": 1, "w_tail": 3, "w_wait": 1}}
    assert a.definition_hash == __import__("hashlib").sha256(canonical_json(a.document)).hexdigest()
    # every consequential parameter is inside the hash
    variants = [
        H.ExperimentDefinition.create(9, 2, 3, [("sparse", {"num_requests": 5})], seeds=[0, 1]),
        H.ExperimentDefinition.create(8, 3, 3, [("sparse", {"num_requests": 5})], seeds=[0, 1]),
        H.ExperimentDefinition.create(8, 2, 4, [("sparse", {"num_requests": 5})], seeds=[0, 1]),
        H.ExperimentDefinition.create(8, 2, 3, [("sparse", {"num_requests": 5})], seeds=[0, 2]),
        H.ExperimentDefinition.create(8, 2, 3, [("sparse", {"num_requests": 6})], seeds=[0, 1]),
        H.ExperimentDefinition.create(8, 2, 3, [("sparse", {"num_requests": 5})], seeds=[0, 1], initial_floors=[0, 3]),
        H.ExperimentDefinition.create(8, 2, 3, [("sparse", {"num_requests": 5})], seeds=[0, 1],
                                      policies=[("cost_based", {"w_tail": 4})]),
        H.ExperimentDefinition.create(8, 2, 3, [("sparse", {"num_requests": 5})], seeds=[1, 0]),
    ]
    hashes = {v.definition_hash for v in variants} | {a.definition_hash}
    assert len(hashes) == len(variants) + 1
    # the experiment execution id is the hash of (definition hash, code identity)
    assert a.experiment_execution_id(CODE) == a.experiment_execution_id(CODE)
    assert a.experiment_execution_id(CODE) != a.experiment_execution_id("d" * 64)
    assert a.experiment_execution_id(CODE) == __import__("hashlib").sha256(
        canonical_json([a.definition_hash, CODE])).hexdigest()
    # defaults of the definition: seeds 0..19 and the three policies
    d = H.ExperimentDefinition.create(6, 2, 3, [("adversarial", {"num_requests": 4})])
    assert d.seeds == tuple(range(20)) and [p["name"] for p in d.document["policies"]] == [
        "round_robin", "nearest_car", "cost_based"]
    with pytest.raises(AttributeError):
        d.document["seeds"].append(1)  # type: ignore[attr-defined]  (a tuple)
    with pytest.raises(TypeError):
        d.document["configuration"]["capacity"] = 9  # type: ignore[index]  (a read-only mapping)


def test_sparse_cross_parameter_refused():
    """The harness half: a definition containing the cross-parameter violation refuses when it is built,
    before any Run could execute."""
    with pytest.raises(ScenarioRefusal) as info:
        H.ExperimentDefinition.create(6, 2, 3, [("sparse", {"num_requests": 1002, "g": 10**6, "j": 0})], seeds=[0])
    assert info.value.reason == "INVALID_SCENARIO_PARAMETERS" and info.value.parameters == ("num_requests", "g", "j")
    ok = H.ExperimentDefinition.create(6, 2, 3, [("sparse", {"num_requests": 1001, "g": 10**6, "j": 0})], seeds=[0])
    assert ok.document["scenarios"][0]["parameters"]["num_requests"] == 1001
    # a bad scenario anywhere in the list refuses the whole definition
    with pytest.raises(ScenarioRefusal):
        H.ExperimentDefinition.create(6, 2, 3, [("uniform", {"num_requests": 4, "horizon": 9}),
                                                ("capacity_stress", {"num_requests": 6})], seeds=[0])  # 6 <= N*C


def test_definitions_refuse_invalid_parts():
    base = dict(scenarios=[("adversarial", {"num_requests": 3})])
    for kwargs, reason in (
            (dict(seeds=[]), "INVALID_CONFIGURATION"), (dict(seeds=[2**64]), "INVALID_SCENARIO_PARAMETERS"),
            (dict(seeds=[1, 1]), "INVALID_SCENARIO_PARAMETERS"), (dict(seeds=[-1]), "INVALID_SCENARIO_PARAMETERS"),
            (dict(policies=[]), "INVALID_CONFIGURATION"), (dict(policies=["nearest_car", "nearest_car"]), "INVALID_CONFIGURATION"),
            (dict(policies=["lookahead"]), "INVALID_CONFIGURATION"),
            (dict(policies=[("round_robin", {"w_wait": 1})]), "INVALID_CONFIGURATION"),
            (dict(policies=[("cost_based", {"w_wait": 10**6 + 1})]), "INVALID_CONFIGURATION"),
            (dict(initial_floors=[0, 9]), "INVALID_CONFIGURATION"), (dict(scenarios=[]), "INVALID_CONFIGURATION")):
        with pytest.raises(Refusal) as info:
            H.ExperimentDefinition.create(6, 2, 3, **{**base, **kwargs})
        assert info.value.reason == reason, kwargs
    for floors, elevators, cap in ((1, 1, 1), (201, 1, 1), (6, 0, 1), (6, 21, 1), (6, 1, 0), (6, 1, 51)):
        with pytest.raises(Refusal) as info:
            H.ExperimentDefinition.create(floors, elevators, cap, **base)
        assert info.value.reason == "INVALID_CONFIGURATION"
    # the JSON document form refuses unknown keys instead of ignoring them
    doc = {"configuration": {"num_floors": 6, "num_elevators": 2, "capacity": 3},
           "scenarios": [{"pattern": "adversarial", "parameters": {"num_requests": 3}}], "seeds": [0, 1]}
    assert H.ExperimentDefinition.from_document(doc).seeds == (0, 1)
    for bad in ({**doc, "max_ticks": 5}, {**doc, "configuration": {**doc["configuration"], "max_ticks": 5}},
                {"scenarios": doc["scenarios"]}):
        with pytest.raises(Refusal):
            H.ExperimentDefinition.from_document(bad)


# --- the result documents --------------------------------------------------------------------------------

def test_results_document_is_deterministic_ordered_and_free_of_execution_facts():
    d = H.ExperimentDefinition.create(6, 2, 3, [("uniform", {"num_requests": 10, "horizon": 20}),
                                                ("adversarial", {"num_requests": 6})], seeds=[3, 1, 2])
    results = full_results(d)
    doc = H.results_document(d, CODE, results)
    assert doc["definition_hash"] == d.definition_hash and doc["experiment_execution_id"] == d.experiment_execution_id(CODE)
    assert doc["code_identity"] == CODE and set(doc) == {"definition", "definition_hash", "experiment_execution_id",
                                                         "code_identity", "runs", "aggregates"}
    keys = [(r["scenario"], d.seeds.index(r["seed"]), r["policy"]) for r in doc["runs"]]
    assert keys == sorted(keys) and len(keys) == 2 * 3 * 3  # (scenario, seed in definition order, policy)
    shuffled = list(results)
    random.Random(5).shuffle(shuffled)
    assert H.results_bytes(d, CODE, shuffled) == H.results_bytes(d, CODE, results) == canonical_json(doc)
    # paired differences are recorded for the cost_based policy against each baseline, and only for it
    cost = d.policy_index("cost_based")
    for entry in doc["aggregates"]:
        assert ("paired_against" in entry) == (entry["policy"] == cost)
    paired = next(e for e in doc["aggregates"] if e["policy"] == cost)["paired_against"]
    assert set(paired) == {"0", "1"} and set(paired["0"]) == set(H.PAIRED_METRICS)
    # a definition without cost_based has no paired block
    d2 = H.ExperimentDefinition.create(6, 2, 3, [("adversarial", {"num_requests": 4})], seeds=[0, 1],
                                       policies=["round_robin", "nearest_car"])
    assert all("paired_against" not in e for e in H.results_document(d2, CODE, full_results(d2))["aggregates"])
    # no execution fact can be in the surface: nothing in its inputs carries one
    raw = canonical_json(doc).decode()
    assert not re.search(r"execution_id|started_at|ended_at|\"pid\"|/tmp|operational", raw.replace("experiment_execution_id", ""))
    assert not re.search(r"\d{4}-\d{2}-\d{2}T", raw)
    # the execution metadata is a separate document that carries those facts
    meta = json.loads(H.experiment_execution_metadata(
        experiment_execution_id=doc["experiment_execution_id"], definition_hash=d.definition_hash,
        runs=[{"scenario": 0, "seed": 3, "policy": 0, "execution_id": "e-1", "output_path": "/out/r/e-1"}],
        pid=77, started_at="2026-11-05T10:00:00Z", ended_at="2026-11-05T10:00:09Z"))
    assert meta["runs"][0]["execution_id"] == "e-1" and meta["pid"] == 77 and meta["started_at"].startswith("2026")


def test_the_harness_core_stays_inside_its_dependency_row():
    import ast
    import os
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(os.path.join(root, "elevator", "harness.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert {m for m in mods if m.startswith("elevator")} == {"elevator.domain", "elevator.reporting", "elevator.scenarios"}
    plain = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not plain & {"random", "time", "datetime", "os", "subprocess", "uuid", "secrets"}
