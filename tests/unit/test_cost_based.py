"""Cut 5 tests (testing_contract §1): the cost-based scheduler."""

import dataclasses
import hashlib
import os
import subprocess
import sys

import pytest

from elevator import route
from elevator.domain import (
    ElevatorView,
    Heading,
    OnboardView,
    RevealedRequest,
    SchedulerView,
    SimulationEventKind as K,
    WaitingView,
    canonical_json,
)
from elevator.policies import CostBased
from tests.engine_fixtures import build, classify_deferrals, run_stepwise
from tests.invariants.test_engine_invariants import FIXTURES, _sweep

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UP, DOWN, NONE = Heading.UP, Heading.DOWN, Heading.NONE


def sv(floors, capacity, cars, t=0):
    return SchedulerView(t=t, floors=floors, num_elevators=len(cars), capacity=capacity, elevators=tuple(cars))


def req(pid, origin, dest, t=0):
    return RevealedRequest(passenger_id=pid, origin=origin, destination=dest, request_time=t)


def idle(i, floor):
    return ElevatorView(i, floor, NONE, (), ())


def assigned_receipts(eng):
    return {e.passenger_id: e.receipt for e in eng.history.events if e.kind is K.ASSIGNED}


class Capture:
    """Test-side wrapper: records (view, request, receipt) for every call."""

    def __init__(self, inner):
        self.inner, self.calls = inner, []

    def assign(self, view, request):
        proposal = self.inner.assign(view, request)
        self.calls.append((view, request, proposal))
        return proposal


def sweep_calls():
    calls = []
    for spec in FIXTURES + _sweep():
        args = dict(spec)
        rows = args.pop("rows")
        cap = Capture(CostBased.for_building(args["floors"]))
        eng, _ = build(rows, policy=cap, **args)
        eng.run()
        assert eng.outcome.standing == "COMPLETED"
        calls += cap.calls
    return calls


# --- the formula, by hand -------------------------------------------------

def test_cost_formula_matches_worked_example_w_c():
    # W-C: F=6, N=2, C=2, t=4; E0 at 2 heading UP with p1 onboard (dest 5, picked up 3);
    # E1 idle at 0; candidate p3 1->4. Nearest Car would tie and take E0.
    cars = [ElevatorView(0, 2, UP, (OnboardView(1, 5, 3),), ()), idle(1, 0)]
    p = CostBased.for_building(6).assign(sv(6, 2, cars, t=4), req(3, 1, 4, t=4))
    r = p.receipt
    assert p.elevator_id == 1 and (r["tier"], r["cost"], r["chosen"]) == (1, 5, 1)
    assert (r["projected_pickup"], r["projected_dropoff"]) == (5, 8)
    e0, e1 = r["candidates"]
    assert (e0["E"], e0["wait_c"], e0["marginal"], e0["tier"], e0["cost"]) == (0, 7, 0, 1, 35)
    assert (e1["E"], e1["wait_c"], e1["marginal"], e1["tier"], e1["cost"]) == (1, 1, 0, 1, 5)


def test_cost_exact_integer():
    # non-default parameters, by hand: idle car at 0, candidate 3->4: wait 3;
    # cost = 3 * (2*3 + 5*max(0, 3-1)) + 3*0 = 48
    policy = CostBased(w_wait=2, w_marginal=3, w_tail=5, tail_threshold=1, age_scale=3)
    r = policy.assign(sv(5, 2, [idle(0, 0)]), req(0, 3, 4)).receipt
    assert r["cost"] == 48 and r["candidates"][0]["wait_c"] == 3
    # every number in every receipt of every fixture and sweep run is a real int
    seen = 0
    for _view, _request, proposal in sweep_calls():
        rc = proposal.receipt
        for key in ("tier", "chosen", "cost", "projected_pickup", "projected_dropoff"):
            assert type(rc[key]) is int
        for row in rc["candidates"]:
            for key in ("E", "tier", "cost", "wait_c", "marginal", "wrong_way_passes_c"):
                assert type(row[key]) is int, (key, row)
            assert type(row["deferred_c"]) is bool
            assert all(type(x) is int for x in row["newly_deferred_others"])
            seen += 1
    assert seen > 500


def test_marginal_can_be_negative_and_so_can_cost():
    # the audit's case: F=8, C=1, N=1; 5->0 and 5->6 at t=0, candidate 6->7 at t=4.
    # p1 (5->6) is accelerated from dropoff 16 to 6 (-10, weight 7 + 4 = 11), p0 is delayed
    # from 10 to 14 (+4, weight 11): marginal = 11 * (-10 + 4) = -66; wait_c = 2;
    # cost = 7 * 2 - 66 = -52; Tier 1.
    eng, _ = build([(0, "p0", 5, 0), (0, "p1", 5, 6), (4, "p2", 6, 7)], floors=8, capacity=1,
                   policy=CostBased.for_building(8))
    eng.run()
    r = assigned_receipts(eng)[2]
    (row,) = r["candidates"]
    assert (row["marginal"], row["cost"], row["tier"], row["wait_c"]) == (-66, -52, 1, 2)
    assert (r["cost"], r["tier"], r["chosen"]) == (-52, 1, 0)
    assert not row["deferred_c"] and row["newly_deferred_others"] == ()


# --- tiers ------------------------------------------------------------------

def test_cost_based_tier1_before_tier2():
    # F=6, C=1. E0 idle at 5: Tier 1, cost 15 (wait 3). E1 at 2 heading UP with p0 waiting at 3
    # (3->5): adding the candidate (2->4) boards it at once and fills the car, so p0 is newly
    # capacity-deferred: Tier 2, and cheaper (cost 10). Tier 1 is chosen anyway.
    e1 = ElevatorView(1, 2, UP, (), (WaitingView(0, 3, 5, 0),))
    p = CostBased.for_building(6).assign(sv(6, 1, [idle(0, 5), e1]), req(1, 2, 4))
    t1, t2 = p.receipt["candidates"]
    assert (t1["E"], t1["tier"], t1["cost"]) == (0, 1, 15)
    assert (t2["E"], t2["tier"], t2["cost"], t2["newly_deferred_others"]) == (1, 2, 10, (0,))
    assert t2["cost"] < t1["cost"]
    assert p.elevator_id == 0 and p.receipt["tier"] == 1


def test_cost_based_tier2_fallback():
    # W-B through the real engine: F=5, C=1; p0 0->4 and p1 2->4 at t=0, one car.
    eng, _ = build([(0, "p0", 0, 4), (0, "p1", 2, 4)], floors=5, capacity=1, policy=CostBased.for_building(5))
    eng.run()
    r = assigned_receipts(eng)
    assert r[0]["tier"] == 1 and r[0]["cost"] == 0
    (row,) = r[1]["candidates"]
    assert (r[1]["tier"], r[1]["cost"], r[1]["projected_pickup"], r[1]["projected_dropoff"]) == (2, 24, 6, 8)
    assert row["deferred_c"] is True and row["newly_deferred_others"] == () and row["marginal"] == 0
    # every car Tier 2: the cheapest is chosen and the receipt says tier = 2
    e0 = ElevatorView(0, 0, UP, (), (WaitingView(0, 0, 4, 0),))
    e1 = ElevatorView(1, 0, UP, (), (WaitingView(1, 0, 3, 0),))
    p = CostBased.for_building(5).assign(sv(5, 1, [e0, e1]), req(2, 2, 4))
    c0, c1 = p.receipt["candidates"]
    assert (c0["tier"], c0["cost"], c1["tier"], c1["cost"]) == (2, 24, 2, 16)
    assert p.elevator_id == 1 and p.receipt["tier"] == 2 and p.receipt["cost"] == 16


def test_tier1_is_incremental():
    # F=5, C=1, one car; 0->4, 2->4, 4->3 at t=0. The second is projected capacity-deferred
    # (Tier 2); the third is Tier 1 although the car already carries that deferral, because it
    # causes no new one.
    eng, _ = build([(0, "a", 0, 4), (0, "b", 2, 4), (0, "c", 4, 3)], floors=5, capacity=1,
                   policy=CostBased.for_building(5))
    eng.run()
    r = assigned_receipts(eng)
    assert [r[i]["tier"] for i in (0, 1, 2)] == [1, 2, 1]
    (row,) = r[2]["candidates"]
    assert row["newly_deferred_others"] == () and row["deferred_c"] is False and row["cost"] == 16
    # direction deferral is not capacity infeasibility: a down-bound candidate behind an
    # up-sweep is a wrong-way pass priced in wait_c, and may still be Tier 1
    e0 = ElevatorView(0, 0, UP, (), (WaitingView(0, 0, 4, 0),))
    p = CostBased.for_building(5).assign(sv(5, 2, [e0]), req(1, 2, 1))
    (row,) = p.receipt["candidates"]
    assert row["tier"] == 1 and row["wrong_way_passes_c"] == 1 and row["deferred_c"] is False


def test_tier1_receipt_not_a_guarantee():
    # F=6, C=1, car at 4; 1->2 and 0->5 both at t=3. p0 is Tier 1; p1 is a Tier 2 assignment
    # to the same car whose route boards p1 first (at 0), so p0 is later capacity-deferred at 1.
    eng, _ = build([(3, "r0", 1, 2), (3, "r1", 0, 5)], floors=6, capacity=1, initial=[4],
                   policy=CostBased.for_building(6))
    steps = run_stepwise(eng)
    r = assigned_receipts(eng)
    assert (r[0]["tier"], r[0]["cost"]) == (1, 15) and (r[1]["tier"], r[1]["cost"]) == (2, 70)
    capacity, _wrong_way = classify_deferrals(eng, steps, 1)
    assert capacity.get(0, 0) >= 1  # p0 really was capacity-deferred
    # the first receipt still says tier 1 after the fact and is not rewritten: the event
    # in History is unchanged, and the Passenger carries no estimate of any kind
    assert r[0]["tier"] == 1
    assert not any("tier" in f.name or "receipt" in f.name for f in dataclasses.fields(eng.passengers[0]))


# --- marginal equals the projection delta -------------------------------------

def test_cost_based_marginal_equals_projection_delta():
    calls = sweep_calls()
    negative = tier2 = 0
    for view, request, proposal in calls:
        policy = CostBased.for_building(view.floors)
        cand = WaitingView(request.passenger_id, request.origin, request.destination, request.request_time)
        for e, row in zip(view.elevators, proposal.receipt["candidates"]):
            base = route.project(e, capacity=view.capacity, now=view.t)
            with_c = route.project(e, (cand,), capacity=view.capacity, now=view.t)
            expected = sum((policy.age_scale + view.t - w.request_time)
                           * (with_c.dropoff_time[w.passenger_id] - base.dropoff_time[w.passenger_id])
                           for w in e.waiting)
            assert row["marginal"] == expected
            # onboard passengers contribute exactly zero (constitution P11), so their age,
            # which the view does not carry, never matters
            assert all(with_c.dropoff_time[o.passenger_id] == base.dropoff_time[o.passenger_id]
                       == view.t + abs(o.destination - e.floor) for o in e.onboard)
            wait_c = with_c.pickup_time[cand.passenger_id] - view.t
            assert row["wait_c"] == wait_c
            assert row["cost"] == (policy.age_scale * (policy.w_wait * wait_c + policy.w_tail
                                   * max(0, wait_c - policy.tail_threshold)) + policy.w_marginal * expected)
            negative += row["marginal"] < 0
            tier2 += row["tier"] == 2
    assert len(calls) > 900 and tier2 > 0


def test_onboard_projected_dropoff_never_depends_on_the_candidate():
    # why the age of an onboard passenger is irrelevant: probe every elevator state met by the
    # runs below with random candidates; the onboard dropoff is always t + |dest - floor|
    state = 99

    def nxt(k):
        nonlocal state
        state = (state * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        return (state >> 33) % k

    pairs = 0
    for view, _request, _proposal in sweep_calls():
        for e in view.elevators:
            if not e.onboard:
                continue
            base = route.project(e, capacity=view.capacity, now=view.t)
            for _ in range(3):
                o = nxt(view.floors)
                d = (o + 1 + nxt(view.floors - 1)) % view.floors
                with_c = route.project(e, (WaitingView(10_000, o, d, view.t),), capacity=view.capacity, now=view.t)
                for q in e.onboard:
                    assert with_c.dropoff_time[q.passenger_id] == base.dropoff_time[q.passenger_id]
                    assert base.dropoff_time[q.passenger_id] == view.t + abs(q.destination - e.floor)
                    pairs += 1
    assert pairs > 100


# --- ties, determinism, parameters ----------------------------------------------

def test_deterministic_tie_cost_based():
    for floors in ([0, 0], [1, 3]):  # identical cars; and mirror-image cars about the origin
        cars = [idle(i, f) for i, f in enumerate(floors)]
        p = CostBased.for_building(6).assign(sv(6, 2, cars), req(0, 2, 5))
        costs = [row["cost"] for row in p.receipt["candidates"]]
        assert costs[0] == costs[1] and p.elevator_id == 0
        reversed_view = sv(6, 2, list(reversed(cars)))
        assert CostBased.for_building(6).assign(reversed_view, req(0, 2, 5)).elevator_id == 0
    # three-way tie, lowest id; and a tie broken only inside the admissible tier
    cars = [idle(0, 2), idle(1, 2), idle(2, 2)]
    assert CostBased.for_building(6).assign(sv(6, 2, cars), req(0, 2, 5)).elevator_id == 0


def test_cost_based_is_deterministic_and_stateless():
    policy = CostBased.for_building(6)
    cars = [ElevatorView(0, 2, UP, (OnboardView(1, 5, 3),), ()), idle(1, 0)]
    v, r = sv(6, 2, cars, t=4), req(3, 1, 4, t=4)
    first = policy.assign(v, r)
    assert [policy.assign(v, r) for _ in range(4)] == [first] * 4
    assert CostBased.for_building(6).assign(v, r) == first  # fresh equals reused
    assert canonical_json(first.receipt) == canonical_json(policy.assign(v, r).receipt)
    # interleaving with other calls changes nothing: no cache, no counter
    policy.assign(sv(6, 2, [idle(0, 4)], t=9), req(9, 0, 5, t=9))
    assert policy.assign(v, r) == first
    assert {f.name for f in dataclasses.fields(policy)} == {"w_wait", "w_marginal", "w_tail", "tail_threshold", "age_scale"}
    with pytest.raises(dataclasses.FrozenInstanceError):
        policy.w_wait = 9  # type: ignore[misc]
    with pytest.raises(AttributeError):
        policy.cache = {}  # type: ignore[attr-defined]
    snapshot = repr(v)
    policy.assign(v, r)
    assert repr(v) == snapshot


def test_cost_based_runs_are_identical_across_processes():
    script = (
        "import hashlib\n"
        "from elevator.domain import Configuration, normalize_requests, canonical_json\n"
        "from elevator.engine import Engine\n"
        "from elevator.policies import CostBased\n"
        "rows=[(0,'a',0,5),(0,'b',4,1),(2,'c',3,0),(5,'d',1,5),(5,'e',5,2),(9,'f',2,4)]\n"
        "cfg=Configuration.create(6,3,2,initial_floors=[0,3,5],policy='cost_based')\n"
        "e=Engine.create(cfg,normalize_requests(rows,6),CostBased(**dict(cfg.policy_params))); e.run()\n"
        "print(hashlib.sha256(canonical_json(e.history)).hexdigest(), e.outcome.standing)\n")
    env = {**os.environ, "PYTHONPATH": ROOT}
    runs = [subprocess.run([sys.executable, "-B", "-c", script], capture_output=True, text=True, cwd=ROOT,
                           env=env, check=True).stdout.strip() for _ in range(2)]
    assert runs[0] == runs[1] and runs[0].endswith("COMPLETED")


def test_cost_based_parameters_are_validated_and_immutable():
    assert CostBased.for_building(8) == CostBased(1, 1, 3, 14, 7)
    assert CostBased.for_building(8, w_wait=2, age_scale=0).w_wait == 2
    for bad in (1.5, True, -1, 10**6 + 1, "1", None):
        with pytest.raises(ValueError):
            CostBased(bad, 1, 3, 14, 7)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        CostBased.for_building(8, w_total=1)
    # Configuration's default-filled parameters build the same policy (cut 8 will do this)
    from elevator.domain import Configuration
    cfg = Configuration.create(8, 2, 3, policy="cost_based", policy_params={"w_tail": 4})
    assert CostBased(**dict(cfg.policy_params)) == CostBased.for_building(8, w_tail=4)


# --- shared projection, receipt ---------------------------------------------------

def test_cost_based_uses_the_shared_projection_at_runtime(monkeypatch):
    """The policy calls route.project twice per elevator (base, then with the candidate) and
    its numbers follow whatever that function returns: patching the shared function changes the
    decision, so no second projection exists in the policy module."""
    calls = []
    original = route.project

    def spy(view, extra=(), *, capacity, now):
        calls.append((view.id, tuple(w.passenger_id for w in extra), capacity, now))
        return original(view, extra, capacity=capacity, now=now)

    monkeypatch.setattr(route, "project", spy)
    cars = [idle(0, 0), idle(1, 4)]
    CostBased.for_building(6).assign(sv(6, 2, cars, t=3), req(7, 2, 5, t=3))
    assert calls == [(0, (), 2, 3), (0, (7,), 2, 3), (1, (), 2, 3), (1, (7,), 2, 3)]
    # distinctive result: pretend the candidate waits 40 ticks on car 0 only
    def skewed(view, extra=(), *, capacity, now):
        result = original(view, extra, capacity=capacity, now=now)
        if view.id == 0 and extra:
            pk = dict(result.pickup_time)
            pk[extra[0].passenger_id] += 40
            return dataclasses.replace(result, pickup_time=pk)
        return result

    monkeypatch.setattr(route, "project", skewed)
    p = CostBased.for_building(6).assign(sv(6, 2, [idle(0, 2), idle(1, 4)], t=3), req(7, 2, 5, t=3))
    assert p.elevator_id == 1  # car 0 (wait 0) would otherwise have won


def test_receipt_shape_order_and_freezing_through_the_engine():
    eng, _ = build([(0, "a", 3, 5), (0, "b", 1, 0)], floors=6, elevators=3, initial=[0, 4, 5], capacity=2,
                   policy=CostBased.for_building(6))
    eng.run()
    for pid, rc in assigned_receipts(eng).items():
        assert set(rc) == {"policy", "tier", "chosen", "cost", "projected_pickup", "projected_dropoff", "candidates"}
        assert rc["policy"] == "cost_based"
        assert [row["E"] for row in rc["candidates"]] == [0, 1, 2]
        assert all(set(row) == {"E", "tier", "cost", "wait_c", "marginal", "deferred_c",
                                "newly_deferred_others", "wrong_way_passes_c"} for row in rc["candidates"])
        assert rc["chosen"] == eng.passengers[pid].assigned_elevator
        with pytest.raises(TypeError):
            rc["cost"] = 0
        with pytest.raises(TypeError):
            rc["candidates"][0]["cost"] = 0
    first = canonical_json(eng.history)
    eng2, _ = build([(0, "a", 3, 5), (0, "b", 1, 0)], floors=6, elevators=3, initial=[0, 4, 5], capacity=2,
                    policy=CostBased.for_building(6))
    eng2.run()
    assert canonical_json(eng2.history) == first
    # no demand model, regime, trace, clock or random source is reachable from the policy module
    import elevator.policies as module
    assert not {"random", "time", "datetime", "os", "sys"} & set(vars(module))
