"""Cut 3 engine-local invariants (testing_contract §2) and the structural
no-look-ahead test (§3 ``view_has_no_future``), checked on in-memory History
under stub policies over hand fixtures and a small deterministic sweep."""

import dataclasses
import functools

from elevator.domain import (
    ElevatorView,
    Heading,
    OperationalRecordKind,
    RevealedRequest,
    SchedulerView,
    SimulationEventKind as K,
    SimulationHistory,
    Standing,
    canonical_json,
    default_max_ticks,
)
from elevator.policies import CostBased, NearestCar, RoundRobin
from tests.engine_fixtures import ByIdPolicy, HashPolicy, build, run_stepwise

FIXTURES = [
    dict(rows=[(0, "p0", 0, 3)], floors=4, capacity=2),
    dict(rows=[(0, "p0", 5, 2)], floors=6, initial=[5]),
    dict(rows=[(0, "p0", 0, 4), (0, "p1", 2, 4)], floors=5, capacity=1),
    dict(rows=[(0, "p0", 0, 4), (0, "p1", 2, 1)], floors=5, capacity=1),
    dict(rows=[(0, "p0", 5, 6), (0, "p1", 3, 0)], floors=7, initial=[4], capacity=2),
    dict(rows=[(0, "A", 0, 5), (0, "B", 5, 7)], floors=8, capacity=1),
    dict(rows=[(0, "a", 0, 3), (0, "b", 0, 4), (0, "c", 0, 2)], floors=5, capacity=2),
    dict(rows=[(0, "a", 0, 2), (40, "b", 1, 0)], floors=4),
    dict(rows=[], floors=4, elevators=2),
]


def _sweep():
    """A small deterministic sweep: a linear congruential sequence picks
    building sizes and request rows. Not a property-testing framework."""
    state = 12345
    def nxt(k):
        nonlocal state
        state = (state * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        return (state >> 33) % k
    cases = []
    for _ in range(240):
        f, n, c = 2 + nxt(6), 1 + nxt(3), 1 + nxt(3)
        rows = []
        for i in range(nxt(9)):
            o = nxt(f)
            d = (o + 1 + nxt(f - 1)) % f
            rows.append((nxt(12), f"r{i}", o, d))
        init = [nxt(f) for _ in range(n)]
        cases.append(dict(rows=rows, floors=f, elevators=n, capacity=c, initial=init))
    return cases


@functools.lru_cache(maxsize=1)
def runs():
    out = []
    for spec in FIXTURES + _sweep():
        for policy_factory in (lambda f: ByIdPolicy(), lambda f: HashPolicy(), lambda f: RoundRobin(),
                               lambda f: NearestCar(), CostBased.for_building):
            args = dict(spec)
            eng, trace = build(args.pop("rows"), policy=policy_factory(args["floors"]), **args)
            steps = run_stepwise(eng)
            out.append((eng, trace, steps))
    return out


def _onboard_by_tick(eng):
    """Onboard set per (tick, elevator) after boarding, from events only."""
    onboard, result = {}, {}
    by_tick = {}
    for e in eng.history.events:
        by_tick.setdefault(e.tick, []).append(e)
    for rec in eng.history.tick_records:
        for e in by_tick.get(rec.tick, []):
            if e.kind is K.ALIGHTED:
                onboard.pop(e.passenger_id)
            elif e.kind is K.BOARDED:
                onboard[e.passenger_id] = e.elevator_id
        for entry in rec.entries:
            result[(rec.tick, entry.elevator_id)] = {p for p, el in onboard.items() if el == entry.elevator_id}
    return result


def test_one_floor_per_tick():
    for eng, _, _ in runs():
        recs = eng.history.tick_records
        for a, b in zip(recs, recs[1:]):
            for x, y in zip(a.entries, b.entries):
                assert abs(y.floor - x.floor) <= 1


def test_floor_in_bounds():
    for eng, trace, _ in runs():
        for r in eng.history.tick_records:
            assert all(0 <= x.floor < trace.num_floors for x in r.entries)


def test_load_never_exceeds_capacity():
    for eng, _, _ in runs():
        cap = eng._config.capacity
        onboard = _onboard_by_tick(eng)
        for r in eng.history.tick_records:
            for x in r.entries:
                assert x.load == len(onboard[(r.tick, x.elevator_id)]) <= cap


def test_order_of_life():
    for eng, _, _ in runs():
        for p in eng.passengers:
            if p.standing is Standing.COMPLETED:
                assert p.assigned_at == p.request_time <= p.pickup_time < p.dropoff_time


def test_assignment_written_once_at_request_time():
    for eng, trace, _ in runs():
        assigned = [e for e in eng.history.events if e.kind is K.ASSIGNED]
        assert len({e.passenger_id for e in assigned}) == len(assigned)
        for e in assigned:
            assert e.tick == trace.requests[e.passenger_id].request_time


def test_one_pickup_one_dropoff_per_completed():
    for eng, trace, _ in runs():
        for p in eng.passengers:
            if p.standing is Standing.COMPLETED:
                ev = [e for e in eng.history.events if e.passenger_id == p.passenger_id
                      and e.kind in (K.BOARDED, K.ALIGHTED)]
                assert [e.kind for e in ev] == [K.BOARDED, K.ALIGHTED]
                assert all(e.elevator_id == p.assigned_elevator for e in ev)
                assert ev[0].floor == p.origin and ev[1].floor == p.destination


def test_at_most_one_elevator_per_passenger():
    for eng, _, _ in runs():
        seen = {}
        for e in eng.history.events:
            if e.elevator_id is not None and e.passenger_id is not None:
                assert seen.setdefault(e.passenger_id, e.elevator_id) == e.elevator_id


def test_one_tick_record_per_tick_per_elevator():
    for eng, _, _ in runs():
        recs = eng.history.tick_records
        n = eng._config.num_elevators
        assert [r.tick for r in recs] == list(range(len(recs)))
        assert all([x.elevator_id for x in r.entries] == list(range(n)) for r in recs)
        if eng.outcome.standing == "COMPLETED":
            assert len(recs) == eng.outcome.final_tick + 1
        else:
            assert len(recs) == eng.outcome.final_tick  # exactly the completed ticks


def test_travel_equals_distance():
    for eng, _, _ in runs():
        for p in eng.passengers:
            if p.standing is Standing.COMPLETED:
                assert p.dropoff_time - p.pickup_time == abs(p.destination - p.origin)


def test_never_picked_up_before_request():
    for eng, trace, _ in runs():
        for e in eng.history.events:
            if e.kind is K.BOARDED:
                assert e.tick >= trace.requests[e.passenger_id].request_time


def test_never_dropped_before_pickup():
    for eng, _, _ in runs():
        boarded = set()
        for e in eng.history.events:
            if e.kind is K.BOARDED:
                boarded.add(e.passenger_id)
            if e.kind is K.ALIGHTED:
                assert e.passenger_id in boarded


def test_never_boarded_wrong_way():
    for eng, trace, _ in runs():
        recs = {r.tick: r for r in eng.history.tick_records}
        for e in eng.history.events:
            if e.kind is K.BOARDED:
                r = trace.requests[e.passenger_id]
                want = Heading.UP if r.destination > r.origin else Heading.DOWN
                assert recs[e.tick].entries[e.elevator_id].heading is want


def test_no_operational_record_in_history():
    for eng, _, _ in runs():
        h = eng.history
        assert isinstance(h, SimulationHistory)
        text = canonical_json(h).decode()
        assert not any(k.value in text for k in OperationalRecordKind)
        assert "execution_id" not in text and "store_id" not in text


def test_destination_never_changes():
    for eng, trace, _ in runs():
        for e in eng.history.events:
            if e.kind is K.ALIGHTED:
                assert e.floor == trace.requests[e.passenger_id].destination
        for p in eng.passengers:
            assert p.destination == trace.requests[p.passenger_id].destination


def test_tick_record_floor_consistent_with_motion():
    for eng, _, _ in runs():
        recs = eng.history.tick_records
        for a, b in zip(recs, recs[1:]):
            for x, y in zip(a.entries, b.entries):
                assert y.floor == x.floor + x.heading.delta


def test_events_and_fields_agree():
    for eng, _, _ in runs():
        ev = {}
        for e in eng.history.events:
            if e.kind in (K.ASSIGNED, K.BOARDED, K.ALIGHTED):
                ev[(e.kind, e.passenger_id)] = e
        for p in eng.passengers:
            a = ev.get((K.ASSIGNED, p.passenger_id))
            assert a is not None and (a.elevator_id, a.tick) == (p.assigned_elevator, p.assigned_at)
            b = ev.get((K.BOARDED, p.passenger_id))
            assert (b is None) == (p.pickup_time is None) and (b is None or b.tick == p.pickup_time)
            c = ev.get((K.ALIGHTED, p.passenger_id))
            assert (c is None) == (p.dropoff_time is None) and (c is None or c.tick == p.dropoff_time)
        assert {pid for _, pid in ev} == {p.passenger_id for p in eng.passengers}


def test_every_passenger_completes():
    for eng, trace, _ in runs():
        assert eng.outcome.standing == "COMPLETED"
        assert len(eng.passengers) == trace.num_requests
        assert all(p.standing is Standing.COMPLETED for p in eng.passengers)


def test_liveness_bound_holds():
    for eng, trace, _ in runs():
        assert eng.outcome.final_tick <= default_max_ticks(trace.num_floors, trace)


def test_heading_none_iff_no_committed_stops():
    for eng, _, steps in runs():
        recs = {r.tick: r for r in eng.history.tick_records}
        for (t, _elevators, _before), after in steps:
            if t not in recs:
                continue
            for x in recs[t].entries:
                stops = {p.origin for p in after if p.standing is Standing.WAITING and p.assigned_elevator == x.elevator_id}
                stops |= {p.destination for p in after if p.standing is Standing.ONBOARD and p.assigned_elevator == x.elevator_id}
                assert (x.heading is Heading.NONE) == (not stops)


def test_view_has_no_future():
    names = {f.name for f in dataclasses.fields(SchedulerView)}
    assert names == {"t", "floors", "num_elevators", "capacity", "elevators"}
    assert {f.name for f in dataclasses.fields(ElevatorView)} == {"id", "floor", "heading", "onboard", "waiting"}
    assert {f.name for f in dataclasses.fields(RevealedRequest)} == {"passenger_id", "origin", "destination", "request_time"}
    for spec in FIXTURES + _sweep()[:80]:
        spec = dict(spec)
        policy = ByIdPolicy(record=True)
        eng, trace = build(spec.pop("rows"), policy=policy, **spec)
        eng.run()
        for view, request in policy.views:
            assert request.request_time == view.t
            for ev in view.elevators:
                for p in ev.waiting:
                    assert p.request_time <= view.t
                for p in ev.onboard:
                    assert trace.requests[p.passenger_id].request_time <= view.t
            # no field of the view holds anything but plain values
            for f in dataclasses.fields(view):
                v = getattr(view, f.name)
                assert isinstance(v, (int, tuple)), f.name
