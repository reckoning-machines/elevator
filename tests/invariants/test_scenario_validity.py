"""Cut 7 validity and no-leakage tests (testing_contract §2/§3 spirit): every generated Trace is
valid, the pattern rules hold, large same-tick groups and long gaps run through the engine, and
scenario metadata cannot reach a policy. No policy is compared against another here."""

import ast
import dataclasses
import inspect
import os

import pytest

from elevator import domain, engine, policies, reporting, route
from elevator.domain import (
    Configuration,
    ElevatorView,
    RevealedRequest,
    SchedulerView,
    SimulationEventKind as K,
    Standing,
    canonical_json,
    default_max_ticks,
)
from elevator.engine import Engine
from elevator.policies import CostBased, NearestCar, RoundRobin
from elevator.scenarios import PATTERNS, Scenario, ScenarioRefusal, generate, provenance, resolve_parameters

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SEEDS = (0, 1, 7, 123456789, 2**64 - 1)
FLOORS = (2, 3, 6, 13, 50, 200)


def param_sets(pattern, F):
    """Two parameter sets per pattern: small, and larger with every optional parameter set."""
    small = {"uniform": {"num_requests": 6, "horizon": 9}, "up_peak": {"num_requests": 6, "horizon": 9},
             "down_peak": {"num_requests": 6, "horizon": 9}, "bursty": {"num_requests": 6, "horizon": 9},
             "concentrated_origin": {"num_requests": 6, "horizon": 9},
             "concentrated_destination": {"num_requests": 6, "horizon": 9},
             "capacity_stress": {"num_requests": 7}, "sparse": {"num_requests": 6}, "adversarial": {"num_requests": 6}}
    big = {"uniform": {"num_requests": 80, "horizon": 400}, "up_peak": {"num_requests": 80, "horizon": 400},
           "down_peak": {"num_requests": 80, "horizon": 400},
           "bursty": {"num_requests": 80, "horizon": 400, "k": 5, "w": 11},
           "concentrated_origin": {"num_requests": 80, "horizon": 400, "m": min(F, 4)},
           "concentrated_destination": {"num_requests": 80, "horizon": 400, "m": min(F, 4)},
           "capacity_stress": {"num_requests": 80, "origin": F - 1},
           "sparse": {"num_requests": 80, "g": 9, "j": 4}, "adversarial": {"num_requests": 80}}
    return small[pattern], big[pattern]


def check_trace(pattern, trace, F, params, N, C):
    n = params["num_requests"]
    assert trace.num_requests == n  # the count is exact
    eff = resolve_parameters(Scenario(pattern, params, 0), F)
    rows = trace.requests
    assert [r.passenger_id for r in rows] == list(range(n))
    assert len({r.source_id for r in rows}) == n
    index = [int(r.source_id[1:]) for r in rows]
    assert all(r.source_id == f"g{i}" for r, i in zip(rows, index)) and sorted(index) == list(range(n))
    keys = [(r.request_time, i) for r, i in zip(rows, index)]
    assert keys == sorted(keys)  # canonical order: stable by (time, generation index)
    assert all(0 <= r.origin < F and 0 <= r.destination < F and r.origin != r.destination for r in rows)
    assert all(0 <= r.request_time <= 10**9 for r in rows)
    if "horizon" in eff:
        assert all(r.request_time <= eff["horizon"] for r in rows)
    if pattern == "up_peak":
        assert all(r.destination >= 1 for r in rows if r.origin == 0)
    if pattern == "down_peak":
        assert all(r.origin >= 1 for r in rows if r.destination == 0)
    if pattern == "concentrated_origin":
        assert len({r.origin for r in rows}) <= eff["m"]
    if pattern == "concentrated_destination":
        assert len({r.destination for r in rows}) <= eff["m"]
    if pattern == "capacity_stress":
        assert n > N * C and all(r.request_time == 0 and r.origin == eff["origin"] for r in rows)
    if pattern == "sparse":
        g, j = eff["g"], eff["j"]
        assert index == list(range(n))  # strictly increasing times: trace order is generation order
        assert all(i * g <= r.request_time <= i * g + j for r, i in zip(rows, index))
        assert all(b.request_time - a.request_time >= g - j >= 1 for a, b in zip(rows, rows[1:]))
    if pattern == "adversarial":
        assert [(r.request_time, r.origin, r.destination) for r in rows] == \
            [(i, 0, F - 1) if i % 2 == 0 else (i, F - 1, 0) for i in range(n)]


def test_every_generated_trace_is_valid_and_obeys_its_pattern():
    checked = 0
    for pattern in PATTERNS:
        for F in FLOORS:
            for params in param_sets(pattern, F):
                for seed in SEEDS:
                    N, C = (2, 3) if pattern == "capacity_stress" else (1, 2)
                    trace = generate(Scenario(pattern, params, seed), F, N, C)
                    check_trace(pattern, trace, F, params, N, C)
                    checked += 1
    assert checked == 9 * 6 * 2 * 5


def test_minimum_building_and_empty_scenarios():
    for pattern in PATTERNS:
        small, _ = param_sets(pattern, 2)
        trace = generate(Scenario(pattern, small, 3), 2, 1, 1)
        check_trace(pattern, trace, 2, small, 1, 1)
        assert {(r.origin, r.destination) for r in trace.requests} <= {(0, 1), (1, 0)}
        empty = dict(small, num_requests=0) if pattern != "capacity_stress" else None
        if empty is not None:
            t = generate(Scenario(pattern, empty, 3), 2, 1, 1)
            assert t.num_requests == 0 and t.last_request_time == 0 and t.canonical_rows() == []
    # capacity stress cannot be empty: num_requests must exceed N * C
    with pytest.raises(ScenarioRefusal):
        generate(Scenario("capacity_stress", {"num_requests": 0}, 3), 2, 1, 1)


def run_all_policies(trace, F, N, C):
    outcomes = []
    for name, policy in (("round_robin", RoundRobin()), ("nearest_car", NearestCar()),
                         ("cost_based", CostBased.for_building(F))):
        eng = Engine.create(Configuration.create(F, N, C, policy=name), trace, policy)
        eng.run()
        outcomes.append((name, eng))
    return outcomes


def test_large_same_tick_groups_and_long_gaps_run_through_the_engine():
    # a burst: one centre, width 1, so every request lands on one timestamp (a large same-tick group)
    burst = generate(Scenario("bursty", {"num_requests": 40, "horizon": 10, "k": 1, "w": 1}, 5), 8, 2, 3)
    assert len({r.request_time for r in burst.requests}) == 1 and burst.num_requests == 40
    ties = [int(r.source_id[1:]) for r in burst.requests]
    assert ties == sorted(ties)  # same-tick requests keep generation order
    # a capacity-stress burst larger than N * C at time 0
    stress = generate(Scenario("capacity_stress", {"num_requests": 30, "origin": 0}, 5), 6, 2, 3)
    assert {r.request_time for r in stress.requests} == {0} and stress.num_requests > 2 * 3
    # sparse: gaps are ticked through, none filled with invented requests
    sparse = generate(Scenario("sparse", {"num_requests": 6, "g": 40, "j": 3}, 5), 6, 2, 3)
    for trace, F, N, C in ((burst, 8, 2, 3), (stress, 6, 2, 3), (sparse, 6, 2, 3)):
        for name, eng in run_all_policies(trace, F, N, C):
            assert eng.outcome.standing == "COMPLETED", name
            assert all(p.standing is Standing.COMPLETED for p in eng.passengers)
            assert eng.outcome.final_tick <= default_max_ticks(F, trace)
            revealed = [e for e in eng.history.events if e.kind is K.REVEALED]
            assert len(revealed) == trace.num_requests
            assert [r.tick for r in eng.history.tick_records] == list(range(eng.outcome.final_tick + 1))
    # in the sparse run the cars idle through the long gaps: tick records exist for every tick of them
    eng = run_all_policies(sparse, 6, 2, 3)[0][1]
    assert eng.outcome.final_tick >= sparse.last_request_time
    idle_ticks = sum(1 for r in eng.history.tick_records if all(e.load == 0 and e.heading.value == "NONE" for e in r.entries))
    assert idle_ticks >= 100


def test_one_trace_serves_every_policy_unchanged():
    sig = list(inspect.signature(generate).parameters)
    assert sig == ["scenario", "num_floors", "num_elevators", "capacity"]  # no policy in the signature
    trace = generate(Scenario("up_peak", {"num_requests": 30, "horizon": 25}, 11), 9, 2, 3)
    before = (trace.trace_hash, trace.requests, canonical_json(trace))
    first = run_all_policies(trace, 9, 2, 3)
    second = run_all_policies(trace, 9, 2, 3)
    assert (trace.trace_hash, trace.requests, canonical_json(trace)) == before
    assert trace.requests is before[1] or trace.requests == before[1]
    for (name_a, a), (name_b, b) in zip(first, second):
        assert name_a == name_b and canonical_json(a.history) == canonical_json(b.history)
    # regenerating gives the very same Trace: no policy-specific variation can creep in
    assert generate(Scenario("up_peak", {"num_requests": 30, "horizon": 25}, 11), 9, 2, 3) == trace


def test_scenarios_are_immutable_and_record_their_provenance():
    caller = {"num_requests": 4, "horizon": 9}
    scenario = Scenario("uniform", caller, 3)
    trace = generate(scenario, 6, 1, 1)
    caller["num_requests"] = 400
    caller["horizon"] = 0
    caller["extra"] = 1
    assert scenario.parameters == {"horizon": 9, "num_requests": 4} and generate(scenario, 6, 1, 1) == trace
    with pytest.raises(dataclasses.FrozenInstanceError):
        scenario.seed = 9  # type: ignore[misc]
    with pytest.raises(TypeError):
        scenario.parameters["horizon"] = 1  # type: ignore[index]
    with pytest.raises(dataclasses.FrozenInstanceError):
        trace.requests[0].origin = 3  # type: ignore[misc]
    assert isinstance(trace.requests, tuple)
    # provenance carries the effective parameters, defaults included; the default g depends on F
    assert provenance(Scenario("sparse", {"num_requests": 3}, 5), 6) == {
        "pattern": "sparse", "parameters": {"num_requests": 3, "g": 10, "j": 0}, "seed": 5}
    assert provenance(Scenario("bursty", {"num_requests": 3, "horizon": 9}, 5), 6)["parameters"] == {
        "num_requests": 3, "horizon": 9, "k": 3, "w": 3}
    assert provenance(Scenario("concentrated_origin", {"num_requests": 3, "horizon": 9}, 5), 6)["parameters"]["m"] == 2


def _imports(path):
    with open(os.path.join(ROOT, "elevator", path), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            mods.add(n.module or "")
            mods |= {f"{n.module}.{a.name}" for a in n.names}
    return mods


def test_scenario_metadata_cannot_reach_a_policy_or_the_history():
    # the generator depends on domain alone (and the standard library), never on an engine, policy or route
    mods = _imports("scenarios.py")
    assert {m for m in mods if m.startswith("elevator")} == {"elevator.domain", "elevator.domain.MAX_REQUEST_ROWS",
                                                             "elevator.domain.MAX_REQUEST_TIME",
                                                             "elevator.domain.Configuration",
                                                             "elevator.domain.Refusal", "elevator.domain.Trace",
                                                             "elevator.domain.normalize_requests"}
    # and nothing the simulation runs on depends on it
    for module in ("engine.py", "policies.py", "route.py", "reporting.py", "domain.py", "api.py"):
        assert not [m for m in _imports(module) if "scenarios" in m], module
    # no field of a value a policy can see, a Request, or a History record names a scenario
    for cls in (SchedulerView, ElevatorView, RevealedRequest, domain.Request, domain.Trace, domain.Passenger,
                domain.SimulationEvent, domain.TickRecord, domain.TickEntry, domain.Configuration):
        for f in dataclasses.fields(cls):
            assert not any(w in f.name for w in ("scenario", "pattern", "seed", "provenance")), (cls, f.name)
    assert list(inspect.signature(Engine.__init__).parameters) == ["self", "configuration", "trace", "policy"]
    # a Run of a generated Trace leaves no trace of the scenario in its History or its outputs
    scenario = Scenario("down_peak", {"num_requests": 20, "horizon": 20}, 424242)
    trace = generate(scenario, 7, 2, 3)
    eng = run_all_policies(trace, 7, 2, 3)[2][1]
    history = canonical_json(eng.history)
    for word in (b"down_peak", b"pattern", b"seed", b"424242", b"scenario", b"provenance"):
        assert word not in history
    from tests.report_fixtures import run_record  # reporting's surface carries none either
    rec = reporting.RunRecord(Configuration.create(7, 2, 3, policy="cost_based"), trace,
                              domain.bind_run(Configuration.create(7, 2, 3, policy="cost_based"), trace, "0" * 64),
                              eng.history, eng.passengers)
    for name, data in reporting.reproducible_surface(rec).items():
        assert b"down_peak" not in data and b"424242" not in data and b"scenario" not in data.lower(), name
