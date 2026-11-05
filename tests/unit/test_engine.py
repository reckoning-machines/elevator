"""Cut 3 unit and behavioural tests (testing_contract §1)."""

import ast
import dataclasses
import os

import pytest

from elevator import route
from elevator.domain import Configuration, Proposal, SimulationEventKind as K, Standing, normalize_requests
from elevator.engine import (
    HALTED,
    HORIZON_EXCEEDED,
    INVALID_PROPOSAL,
    LIVENESS_BOUND_EXCEEDED,
    POLICY_ERROR,
    Engine,
)
from tests.engine_fixtures import (
    DOWN,
    NONE,
    UP,
    ByIdPolicy,
    build,
    classify_deferrals,
    floors_headings_loads,
    run_stepwise,
)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def kinds(engine):
    return [(e.kind, e.tick, e.passenger_id) for e in engine.history.events]


def test_one_elevator_one_passenger_up():
    eng, _ = build([(0, "p0", 0, 3)], floors=4, capacity=2)
    out = eng.run()
    assert out.standing == "COMPLETED" and out.final_tick == 3
    floors, headings, loads = floors_headings_loads(eng)
    assert floors == [0, 1, 2, 3] and headings == [UP, UP, UP, NONE] and loads == [1, 1, 1, 0]
    assert kinds(eng) == [(K.REVEALED, 0, 0), (K.ASSIGNED, 0, 0), (K.BOARDED, 0, 0),
                          (K.ALIGHTED, 3, 0), (K.COMPLETED, 3, None)]
    assert [e.seq for e in eng.history.events] == [0, 1, 2, 3, 4]
    p = eng.passengers[0]
    assert (p.pickup_time - p.request_time, p.dropoff_time - p.pickup_time) == (0, 3)


def test_one_elevator_one_passenger_down():
    eng, _ = build([(0, "p0", 5, 2)], floors=6, initial=[5])
    out = eng.run()
    assert out.final_tick == 3
    floors, headings, _ = floors_headings_loads(eng)
    assert floors == [5, 4, 3, 2] and headings == [DOWN, DOWN, DOWN, NONE]
    p = eng.passengers[0]
    assert (p.pickup_time, p.dropoff_time) == (0, 3)


def test_same_floor_pickup_at_request_time():
    eng, _ = build([(6, "p", 4, 1)], floors=6, initial=[4])
    eng.run()
    p = eng.passengers[0]
    assert p.pickup_time == 6 and p.pickup_time - p.request_time == 0
    rec6 = eng.history.tick_records[6].entries[0]
    assert rec6.floor == 4 and rec6.boarded == (0,)
    assert all(r.entries[0].heading is NONE for r in eng.history.tick_records[:6])


def test_pickup_then_move_same_tick():
    eng, _ = build([(0, "p0", 0, 3)], floors=4)
    eng.run()
    recs = eng.history.tick_records
    assert recs[0].entries[0].boarded == (0,) and recs[0].entries[0].floor == 0
    assert recs[1].entries[0].floor == 1  # zero dwell: board and move in one tick


def test_alight_before_board_frees_room():
    eng, _ = build([(0, "A", 0, 5), (0, "B", 5, 7)], floors=8, capacity=1)
    eng.run()
    a, b = eng.passengers
    assert a.dropoff_time == 5 and b.pickup_time == 5
    rec = eng.history.tick_records[5].entries[0]
    assert rec.alighted == (0,) and rec.boarded == (1,) and rec.load == 1


def test_deferred_boarding_then_return():
    # W-B
    eng, _ = build([(0, "p0", 0, 4), (0, "p1", 2, 4)], floors=5, capacity=1)
    steps = run_stepwise(eng)
    floors, headings, loads = floors_headings_loads(eng)
    assert floors == [0, 1, 2, 3, 4, 3, 2, 3, 4]
    assert headings == [UP, UP, UP, UP, DOWN, DOWN, UP, UP, NONE]
    assert loads == [1, 1, 1, 1, 0, 0, 1, 1, 0]
    rec2 = eng.history.tick_records[2].entries[0]
    assert rec2.floor == 2 and rec2.boarded == () and rec2.load == 1
    assert eng.passengers[1].pickup_time == 6 and eng.passengers[1].dropoff_time == 8
    capacity, wrong_way = classify_deferrals(eng, steps, 1)
    assert capacity == {1: 1} and wrong_way == {}


def test_direction_deferral_then_return():
    # W-F
    eng, _ = build([(0, "p0", 0, 4), (0, "p1", 2, 1)], floors=5, capacity=1)
    steps = run_stepwise(eng)
    floors, headings, loads = floors_headings_loads(eng)
    assert floors == [0, 1, 2, 3, 4, 3, 2, 1]
    assert headings == [UP, UP, UP, UP, DOWN, DOWN, DOWN, NONE]
    p1 = eng.passengers[1]
    assert (p1.pickup_time, p1.dropoff_time) == (6, 7) and p1.dropoff_time - p1.pickup_time == 1
    capacity, wrong_way = classify_deferrals(eng, steps, 1)
    assert wrong_way == {1: 1} and capacity == {}


def test_deferral_classification_direction_first():
    # W-F tick 2: full and departing the other way: one wrong-way pass, no capacity deferral
    eng, _ = build([(0, "p0", 0, 4), (0, "p1", 2, 1)], floors=5, capacity=1)
    capacity, wrong_way = classify_deferrals(eng, run_stepwise(eng), 1)
    assert wrong_way.get(1) == 1 and 1 not in capacity
    # W-B tick 2: compatible and full continuing car: one capacity deferral
    eng, _ = build([(0, "p0", 0, 4), (0, "p1", 2, 4)], floors=5, capacity=1)
    capacity, wrong_way = classify_deferrals(eng, run_stepwise(eng), 1)
    assert capacity.get(1) == 1 and 1 not in wrong_way
    # A FREE full car: unreachable through the engine (a car with anyone onboard
    # after alighting is never FREE, semantics §8.2 Lemma 1), so it is pinned at
    # the shared primitive the engine calls.
    a, b = route.WaitingPassenger(0, 3, 5), route.WaitingPassenger(1, 3, 0)
    r = route.eligible_boarders([a, b], route.Departure.FREE, load=1, capacity=1)
    assert r.boarders == () and r.direction_deferred == () and len(r.capacity_deferred) == 2


def test_free_car_oldest_sets_direction():
    eng, _ = build([(0, "old", 3, 0), (0, "young", 3, 6)], floors=7, initial=[3], capacity=4)
    eng.run()
    old, young = eng.passengers
    assert old.pickup_time == 0 and eng.history.tick_records[0].entries[0].heading is DOWN
    assert eng.history.tick_records[0].entries[0].boarded == (0,)
    assert old.dropoff_time == 3 and young.pickup_time == 6 and young.dropoff_time == 9


def test_reversal_point_is_free():
    # W-G
    eng, _ = build([(0, "p0", 5, 6), (0, "p1", 3, 0)], floors=7, initial=[4], capacity=2)
    out = eng.run()
    assert out.standing == "COMPLETED" and out.final_tick == 8
    floors, headings, loads = floors_headings_loads(eng)
    assert floors == [4, 5, 6, 5, 4, 3, 2, 1, 0]
    assert headings == [UP, UP, DOWN, DOWN, DOWN, DOWN, DOWN, DOWN, NONE]
    assert loads == [0, 1, 0, 0, 0, 1, 1, 1, 0]


def test_promised_direction_overrides_nearest():
    eng, _ = build([(0, "p0", 5, 3), (0, "p1", 6, 9)], floors=10, initial=[5])
    eng.step()
    rec = eng.history.tick_records[0].entries[0]
    assert rec.boarded == (0,) and rec.heading is DOWN  # nearest stop (6) is UP; the promise wins
    assert route.next_heading(5, NONE, [3, 6]) is UP


def test_simultaneous_requests_sequential_assignment():
    policy = ByIdPolicy(mapping={0: 1, 1: 0}, record=True)
    eng, _ = build([(0, "a", 3, 5), (0, "b", 4, 1)], floors=6, elevators=2, policy=policy)
    eng.step()
    (view0, req0), (view1, req1) = policy.views
    assert (req0.passenger_id, req1.passenger_id) == (0, 1)
    assert all(not ev.waiting for ev in view0.elevators)  # later same-tick request not visible
    assert [w.passenger_id for w in view1.elevators[1].waiting] == [0]
    assigned = [e for e in eng.history.events if e.kind is K.ASSIGNED]
    assert [(e.passenger_id, e.elevator_id) for e in assigned] == [(0, 1), (1, 0)]


def test_sparse_requests_idle_gaps():
    eng, _ = build([(0, "a", 0, 2), (40, "b", 1, 0)], floors=4)
    out = eng.run()
    ticks = [r.tick for r in eng.history.tick_records]
    assert ticks == list(range(out.final_tick + 1))
    assert all(r.entries[0].heading is NONE for r in eng.history.tick_records[2:40])


def test_request_time_skip_ticks_through():
    eng, _ = build([(0, "a", 0, 1), (100, "b", 1, 0)], floors=3)
    eng.run()
    assert len(eng.history.tick_records) >= 101
    assert [r.tick for r in eng.history.tick_records] == list(range(len(eng.history.tick_records)))


def test_multiple_elevators_independent_same_floor():
    policy = ByIdPolicy(mapping={0: 0, 1: 1})
    eng, _ = build([(0, "a", 2, 5), (0, "b", 2, 0)], floors=6, elevators=2, initial=[2, 2], policy=policy)
    eng.step()
    e0, e1 = eng.history.tick_records[0].entries
    assert e0.boarded == (0,) and e1.boarded == (1,)
    eng.run()
    a, b = eng.passengers
    assert a.assigned_elevator == 0 and b.assigned_elevator == 1


def test_capacity_exactly_full():
    eng, _ = build([(0, "a", 0, 3), (0, "b", 0, 4), (0, "c", 0, 2)], floors=5, capacity=2)
    eng.step()
    rec = eng.history.tick_records[0].entries[0]
    assert rec.boarded == (0, 1) and rec.load == 2
    assert eng.passengers[2].standing is Standing.WAITING
    eng.run()
    assert eng.passengers[2].pickup_time is not None


def test_capacity_overflow_impossible():
    eng, _ = build([(0, "a", 0, 3)], floors=4, capacity=1)
    with pytest.raises(AttributeError):
        eng.passengers = ()  # type: ignore[misc]
    with pytest.raises(AttributeError):
        eng.elevators = ()  # type: ignore[misc]
    assert isinstance(eng.passengers, tuple) and isinstance(eng.elevators, tuple)
    public = {n for n in dir(eng) if not n.startswith("_")}
    # cut 9 adds the admitted continuation hooks: a read-only `state`, `restore` (the only way a resumed
    # state enters the engine) and `set_diagnostic`; there is still no setter for any runtime fact
    assert public == {"create", "elevators", "history", "load", "max_ticks", "outcome", "passengers",
                      "restore", "run", "set_diagnostic", "standing", "state", "step", "t"}
    eng.step()
    with pytest.raises(dataclasses.FrozenInstanceError):
        eng.passengers[0].standing = Standing.ONBOARD  # type: ignore[misc]


def test_halt_discards_partial_tick():
    policy = ByIdPolicy(mapping={0: 0, 1: 1})
    eng, _ = build([(0, "a", 0, 2), (0, "b", 1, 2)], floors=3, elevators=1, policy=policy)
    out = eng.run()
    assert (out.standing, out.final_tick, out.halt_step, out.halt_reason, out.halt_passenger) == \
        (HALTED, 0, "ASSIGN", INVALID_PROPOSAL, 1)
    assert [(e.seq, e.kind) for e in eng.history.events] == [(0, K.HALTED)]
    assert eng.history.tick_records == () and eng.passengers == ()
    # a halt at a later tick keeps every completed tick and discards only its own
    eng, _ = build([(0, "a", 0, 2), (3, "b", 1, 2)], floors=3, policy=ByIdPolicy(mapping={1: 5}))
    out = eng.run()
    assert out.final_tick == 3 and [r.tick for r in eng.history.tick_records] == [0, 1, 2]
    assert eng.history.events[-1].kind is K.HALTED and eng.history.events[-1].tick == 3
    assert not any(e.kind is K.REVEALED and e.passenger_id == 1 for e in eng.history.events)
    assert eng.step() is out and len(eng.history.tick_records) == 3  # final: step is a no-op


def test_policy_invalid_proposal_halts():
    # W-E
    eng, _ = build([(0, "p0", 0, 3)], floors=4, policy=ByIdPolicy(mapping={0: 1}))
    out = eng.run()
    assert out.halt_reason == INVALID_PROPOSAL and out.halt_step == "ASSIGN" and out.halt_passenger == 0
    (only,) = eng.history.events
    assert only.kind is K.HALTED and only.seq == 0 and only.tick == 0
    assert only.halt == {"step": "ASSIGN", "reason": INVALID_PROPOSAL, "passenger": 0, "unserved": 1}
    assert eng.history.tick_records == ()

    class NotAProposal:
        def assign(self, view, request):
            return 0
    eng, _ = build([(0, "p0", 0, 3)], floors=4, policy=NotAProposal())
    assert eng.run().halt_reason == INVALID_PROPOSAL

    class BoolId:
        def assign(self, view, request):
            return Proposal(True)  # type: ignore[arg-type]
    eng, _ = build([(0, "p0", 0, 3)], floors=4, policy=BoolId())
    assert eng.run().halt_reason == INVALID_PROPOSAL


def test_policy_exception_halts():
    class Raises:
        def assign(self, view, request):
            raise RuntimeError("boom")
    eng, _ = build([(0, "p0", 0, 3)], floors=4, policy=Raises())
    out = eng.run()
    assert (out.halt_reason, out.halt_step, out.halt_passenger) == (POLICY_ERROR, "ASSIGN", 0)
    assert [e.kind for e in eng.history.events] == [K.HALTED]


def test_termination_waits_for_unrevealed_requests():
    eng, _ = build([(0, "a", 0, 5), (9, "b", 1, 0)], floors=6)
    out = eng.run()
    assert eng.passengers[0].dropoff_time == 5
    assert out.standing == "COMPLETED" and out.final_tick > 9


def test_empty_trace_completes_at_zero():
    # engine half: one TickRecord, outcome COMPLETED at t = 0
    eng, _ = build([], floors=4, elevators=2)
    out = eng.run()
    assert (out.standing, out.final_tick) == ("COMPLETED", 0)
    assert len(eng.history.tick_records) == 1 and eng.history.tick_records[0].tick == 0
    assert [e.kind for e in eng.history.events] == [K.COMPLETED]


def test_horizon_halt_reasons_distinct(monkeypatch):
    # halt half: an explicit smaller horizon halts HORIZON_EXCEEDED with unserved > 0
    eng, trace = build([(0, "a", 0, 3), (0, "b", 3, 0)], floors=4, max_ticks=2)
    out = eng.run()
    assert (out.standing, out.halt_reason, out.halt_step, out.final_tick) == (HALTED, HORIZON_EXCEEDED, "TERMINATE", 2)
    assert out.unserved > 0 and [r.tick for r in eng.history.tick_records] == [0, 1]
    # LIVENESS_BOUND_EXCEEDED is reserved for the default bound; it can only occur
    # if the route mechanics are wrong, so a broken next_heading is injected.
    monkeypatch.setattr(route, "next_heading", lambda floor, heading, stops: NONE)
    eng, trace = build([(0, "a", 2, 3)], floors=4)
    out = eng.run()
    assert out.halt_reason == LIVENESS_BOUND_EXCEEDED and out.final_tick == eng.max_ticks
    # an explicit horizon equal to the default bound is the bound itself
    eng, trace = build([(0, "a", 2, 3)], floors=4, max_ticks=6)
    assert eng.run().halt_reason == LIVENESS_BOUND_EXCEEDED


def _module_tree(name):
    with open(os.path.join(ROOT, "elevator", name), encoding="utf-8") as fh:
        return ast.parse(fh.read())


def test_route_primitives_single_implementation():
    engine_tree = _module_tree("engine.py")
    # the engine references the three primitives as attributes of the route module
    attrs = {(n.value.id, n.attr) for n in ast.walk(engine_tree)
             if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
    for name in ("departure_direction", "eligible_boarders", "next_heading"):
        assert ("route", name) in attrs, name
    import elevator.engine as engine_module
    assert engine_module.route is route
    # the engine defines no function that computes a departure, boarding or heading
    defs = {n.name for n in ast.walk(engine_tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert not {d for d in defs if any(k in d for k in ("departure", "boarder", "heading", "look"))}
    # project calls the same three primitives by name
    route_tree = _module_tree("route.py")
    project = next(n for n in ast.walk(route_tree) if isinstance(n, ast.FunctionDef) and n.name == "project")
    called = {c.func.id for c in ast.walk(project) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    assert {"departure_direction", "eligible_boarders", "next_heading"} <= called
    # the policy-module half (cut 4): the policies module defines no such function either,
    # and its only project import is domain, so it cannot reach the route mechanics at all
    policies_tree = _module_tree("policies.py")
    policy_defs = {n.name for n in ast.walk(policies_tree) if isinstance(n, ast.FunctionDef)}
    assert not {d for d in policy_defs if any(k in d for k in ("departure", "boarder", "heading", "look"))}
    policy_imports = {(n.module, a.name) for n in ast.walk(policies_tree) if isinstance(n, ast.ImportFrom)
                      for a in n.names if n.module and n.module.startswith("elevator")}
    assert {m for m, _ in policy_imports} <= {"elevator", "elevator.domain"}
    assert {name for m, name in policy_imports if m == "elevator"} <= {"route"}
    # with route imported, policies may use only the shared projection from it (cut 5): never the
    # three primitives directly, so it cannot compute a departure, boarding or heading itself
    route_attrs = {n.attr for n in ast.walk(policies_tree) if isinstance(n, ast.Attribute)
                   and isinstance(n.value, ast.Name) and n.value.id == "route"}
    assert route_attrs <= {"project", "Projection"}, route_attrs


def test_engine_imports_no_later_cut_module():
    imported = set()
    for n in ast.walk(_module_tree("engine.py")):
        if isinstance(n, ast.Import):
            imported |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            imported.add(n.module or "")
    assert {m for m in imported if m.startswith("elevator")} == {"elevator", "elevator.domain"}
    assert not imported & {"os", "sys", "io", "json", "random", "time", "datetime", "pathlib", "web"}
