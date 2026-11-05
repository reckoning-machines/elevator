"""Cut 5 projection-exactness tests (testing_contract §1 and §5; constitution P9).

For every elevator that receives no assignment after tick t, route.project
computed at t (the boundary state after tick t's assignments) must equal the
realized pickup and dropoff times, and its observation phase (capacity
deferrals, wrong-way passes) must equal what the History shows from tick t on.
Run against the real engine under every policy."""

import functools

import pytest

from elevator import route
from elevator.domain import Standing, SimulationEventKind as K
from elevator.policies import CostBased, NearestCar, RoundRobin
from tests.engine_fixtures import ByIdPolicy, HashPolicy, build, classify_deferrals, run_stepwise
from tests.invariants.test_engine_invariants import FIXTURES, _sweep

POLICY_FACTORIES = (lambda f: ByIdPolicy(), lambda f: HashPolicy(), lambda f: RoundRobin(),
                    lambda f: NearestCar(), CostBased.for_building)


def route_state_at(eng, trace, before, new_assignments, e):
    """The boundary state of elevator e at tick t after step 2: committed passengers from the
    state before the tick plus the passengers assigned to e at t."""
    t, elevators_before, passengers_before = before
    car = elevators_before[e]
    onboard = tuple(route.OnboardPassenger(p.passenger_id, p.destination) for p in passengers_before
                    if p.standing is Standing.ONBOARD and p.assigned_elevator == e)
    waiting = [route.WaitingPassenger(p.passenger_id, p.origin, p.destination) for p in passengers_before
               if p.standing is Standing.WAITING and p.assigned_elevator == e]
    for pid, elevator in new_assignments:
        if elevator == e:
            r = trace.requests[pid]
            waiting.append(route.WaitingPassenger(pid, r.origin, r.destination))
    return route.RouteState(floor=car.floor, heading=car.heading, onboard=onboard, waiting=tuple(waiting))


def mismatches(eng, trace, steps, capacity, *, ticks=None, project=route.project):
    """Compare project() with realization for every (tick, untouched elevator)."""
    final = {p.passenger_id: p for p in eng.passengers}
    assigned = [(e.tick, e.passenger_id, e.elevator_id) for e in eng.history.events if e.kind is K.ASSIGNED]
    bad, checked = [], 0
    for before, _after in steps:
        t = before[0]
        if ticks is not None and t not in ticks:
            continue
        new_here = [(pid, el) for tick, pid, el in assigned if tick == t]
        capacity_realized, wrong_realized = classify_deferrals(eng, steps, capacity, from_tick=t)
        for e in range(len(before[1])):
            if any(tick > t and el == e for tick, _pid, el in assigned):
                continue  # an assignment after t may change this car's route
            state = route_state_at(eng, trace, before, new_here, e)
            ids = [p.passenger_id for p in state.onboard] + [p.passenger_id for p in state.waiting]
            proj = project(state, capacity=capacity, now=t)
            checked += 1
            want_pickup = {p.passenger_id: final[p.passenger_id].pickup_time for p in state.waiting}
            want_dropoff = {pid: final[pid].dropoff_time for pid in ids}
            want_end = max(want_dropoff.values(), default=t)
            waiting_ids = {p.passenger_id for p in state.waiting}
            want_deferred = frozenset(pid for pid in waiting_ids if capacity_realized.get(pid, 0) > 0)
            want_wrong = {pid: n for pid, n in wrong_realized.items() if pid in waiting_ids}
            got = (proj.pickup_time, proj.dropoff_time, proj.end_time, proj.deferred, proj.wrong_way_passes)
            if got != (want_pickup, want_dropoff, want_end, want_deferred, want_wrong) or proj.max_load > capacity:
                bad.append((t, e, got, (want_pickup, want_dropoff, want_end, want_deferred, want_wrong)))
    return bad, checked


@functools.lru_cache(maxsize=1)
def runs():
    out = []
    for spec in FIXTURES + _sweep():
        for factory in POLICY_FACTORIES:
            args = dict(spec)
            eng, trace = build(args.pop("rows"), policy=factory(args["floors"]), **args)
            steps = run_stepwise(eng)
            out.append((eng, trace, steps, eng._config.capacity))
    return out


def test_projection_exactness():
    total = 0
    for eng, trace, steps, capacity in runs():
        bad, checked = mismatches(eng, trace, steps, capacity)
        assert not bad, bad[:2]
        total += checked
    assert total > 5000


def test_projection_observation_phase():
    # the same comparison, restricted to the t = 0 fixtures whose requests all arrive together
    # (so every elevator is untouched after tick 0): deferred and wrong_way_passes equal the
    # realized capacity_deferrals and wrong_way_passes from the History
    checked = deferred = wrong = 0
    for spec in FIXTURES:
        args = dict(spec)
        rows = args.pop("rows")
        for factory in POLICY_FACTORIES:
            eng, trace = build(rows, policy=factory(args["floors"]), **args)
            steps = run_stepwise(eng)
            bad, n = mismatches(eng, trace, steps, eng._config.capacity, ticks={0})
            assert not bad, bad[:2]
            checked += n
    # W-B and W-F by name: the capacity deferral and the wrong-way pass are observed
    for rows, want_deferred, want_wrong in (([(0, "a", 0, 4), (0, "b", 2, 4)], {1}, {}),
                                            ([(0, "a", 0, 4), (0, "b", 2, 1)], set(), {1: 1})):
        eng, trace = build(rows, floors=5, capacity=1, policy=RoundRobin())
        steps = run_stepwise(eng)
        state = route_state_at(eng, trace, steps[0][0], [(0, 0), (1, 0)], 0)
        proj = route.project(state, capacity=1, now=0)
        assert proj.deferred == frozenset(want_deferred) and proj.wrong_way_passes == want_wrong
        deferred += len(proj.deferred)
        wrong += sum(proj.wrong_way_passes.values())
    assert checked > 0 and deferred == 1 and wrong == 1


def test_projection_exactness_property():
    """For random buildings, traces, t and cars: projection equals realization. Larger and
    sparser than the shared sweep; a seeded LCG, not a framework."""
    state = 2026

    def nxt(k):
        nonlocal state
        state = (state * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        return (state >> 33) % k

    total = 0
    for case in range(120):
        f, n, c = 3 + nxt(8), 1 + nxt(4), 1 + nxt(4)
        rows = []
        for i in range(2 + nxt(14)):
            o = nxt(f)
            d = (o + 1 + nxt(f - 1)) % f
            rows.append((nxt(30), f"r{i}", o, d))
        factory = POLICY_FACTORIES[case % len(POLICY_FACTORIES)]
        eng, trace = build(rows, floors=f, elevators=n, capacity=c, initial=[nxt(f) for _ in range(n)],
                           policy=factory(f))
        steps = run_stepwise(eng)
        assert eng.outcome.standing == "COMPLETED"
        picks = {nxt(max(1, eng.outcome.final_tick + 1)) for _ in range(6)}
        bad, checked = mismatches(eng, trace, steps, c, ticks=picks)
        assert not bad, (case, bad[:1])
        total += checked
    assert total > 300


def test_exactness_comparison_detects_a_wrong_projection():
    """Negative control: the comparison above can fail. A projection that is off by one tick
    is flagged for every fixture."""
    def off_by_one(state, *, capacity, now):
        real = route.project(state, capacity=capacity, now=now)
        return type(real)(pickup_time={k: v + 1 for k, v in real.pickup_time.items()},
                          dropoff_time={k: v + 1 for k, v in real.dropoff_time.items()},
                          first_compatible_arrival=real.first_compatible_arrival, deferred=real.deferred,
                          wrong_way_passes=real.wrong_way_passes, max_load=real.max_load,
                          end_time=real.end_time + 1)

    eng, trace = build([(0, "a", 0, 4), (0, "b", 2, 4)], floors=5, capacity=1, policy=RoundRobin())
    steps = run_stepwise(eng)
    bad, checked = mismatches(eng, trace, steps, 1, ticks={0}, project=off_by_one)
    assert checked == 1 and len(bad) == 1
    assert mismatches(eng, trace, steps, 1, ticks={0})[0] == []
