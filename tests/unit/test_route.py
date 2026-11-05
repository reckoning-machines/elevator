"""Cut 2 unit tests (testing_contract §1): the Route Policy primitives.
Each contract identifier is the function name's suffix after ``test_``."""

import ast
import os

from elevator.domain import Heading
from elevator.route import (
    Departure,
    OnboardPassenger,
    RouteState,
    WaitingPassenger,
    departure_direction,
    eligible_boarders,
    next_heading,
    project,
)

UP, DOWN, NONE = Heading.UP, Heading.DOWN, Heading.NONE


def W(pid, origin, dest):
    return WaitingPassenger(pid, origin, dest)


def test_idle_tie_prefers_up():
    # idle car at 5 with stops at 3 and 7: equal distance, UP wins the tie
    assert next_heading(5, NONE, [3, 7]) is UP
    # a nearer stop below wins; a nearer stop above wins
    assert next_heading(5, NONE, [4, 7]) is DOWN
    assert next_heading(5, NONE, [3, 6]) is UP
    # no stops: NONE; stops only on one side from idle
    assert next_heading(5, NONE, []) is NONE
    assert next_heading(5, NONE, [5]) is NONE  # the current floor is never ahead
    assert next_heading(5, NONE, [8]) is UP
    assert next_heading(5, NONE, [1]) is DOWN
    # canonicalised input: order and duplicates do not matter
    assert next_heading(5, NONE, {7, 3, 3}) is UP


def test_reversal_only_when_nothing_ahead():
    # continuing UP while a stop lies above, even with stops below
    assert next_heading(4, UP, [2, 9]) is UP
    assert next_heading(8, UP, [2, 9]) is UP
    # at 9 nothing is above: reverse toward the stop below, in the same call
    assert next_heading(9, UP, [2, 9]) is DOWN
    assert next_heading(9, UP, [2]) is DOWN
    # continuing DOWN symmetrically
    assert next_heading(6, DOWN, [2, 9]) is DOWN
    assert next_heading(2, DOWN, [2, 9]) is UP
    assert next_heading(2, DOWN, [9]) is UP
    # a car that has reached its only stop and has none left is idle
    assert next_heading(9, UP, [9]) is NONE
    # reversal from UP with stops on both sides below: nearest is irrelevant, it goes DOWN
    assert next_heading(9, UP, [1, 8]) is DOWN


def test_departure_direction_cases():
    # NONE (idle) is FREE regardless of stops elsewhere
    assert departure_direction(5, NONE, []) is Departure.FREE
    assert departure_direction(5, NONE, [3, 7]) is Departure.FREE
    # UP with a stop above: continue UP; with none above: FREE (reversal point)
    assert departure_direction(5, UP, [7]) is Departure.UP
    assert departure_direction(5, UP, [3, 7]) is Departure.UP
    assert departure_direction(5, UP, [3]) is Departure.FREE
    assert departure_direction(5, UP, []) is Departure.FREE
    # DOWN likewise
    assert departure_direction(5, DOWN, [3]) is Departure.DOWN
    assert departure_direction(5, DOWN, [3, 7]) is Departure.DOWN
    assert departure_direction(5, DOWN, [7]) is Departure.FREE
    # the current floor is never ahead (S_other excludes it)
    assert departure_direction(5, UP, [5]) is Departure.FREE
    assert departure_direction(5, DOWN, [5, 5]) is Departure.FREE


def test_eligible_boarders_cases():
    # FREE: the first (lowest id) boarder sets the direction; later boarders must match
    up_a, down_b, up_c = W(1, 5, 9), W(2, 5, 1), W(3, 5, 7)
    r = eligible_boarders([down_b, up_a, up_c], Departure.FREE, load=0, capacity=4)
    assert [p.passenger_id for p in r.boarders] == [1, 3]
    assert r.departure is Departure.UP
    assert [p.passenger_id for p in r.direction_deferred] == [2]
    assert r.capacity_deferred == ()
    # an established departure admits only compatible passengers
    r = eligible_boarders([up_a, down_b], Departure.DOWN, load=0, capacity=4)
    assert [p.passenger_id for p in r.boarders] == [2]
    assert r.departure is Departure.DOWN
    assert [p.passenger_id for p in r.direction_deferred] == [1]
    # direction before capacity: wrong-way + full is a direction deferral only
    r = eligible_boarders([down_b], Departure.UP, load=4, capacity=4)
    assert r.boarders == () and r.capacity_deferred == ()
    assert [p.passenger_id for p in r.direction_deferred] == [2]
    assert r.departure is Departure.UP
    # compatible + full is a capacity deferral
    r = eligible_boarders([up_a], Departure.UP, load=4, capacity=4)
    assert r.boarders == () and r.direction_deferred == ()
    assert [p.passenger_id for p in r.capacity_deferred] == [1]
    # a full FREE car boards nobody, stays FREE, and everyone is a capacity deferral
    r = eligible_boarders([up_a, down_b], Departure.FREE, load=2, capacity=2)
    assert r.boarders == () and r.departure is Departure.FREE
    assert [p.passenger_id for p in r.capacity_deferred] == [1, 2]
    assert r.direction_deferred == ()
    # capacity counts boarders taken this tick: room for one of two compatible
    r = eligible_boarders([up_a, up_c], Departure.UP, load=3, capacity=4)
    assert [p.passenger_id for p in r.boarders] == [1]
    assert [p.passenger_id for p in r.capacity_deferred] == [3]
    # alighting-created room is the caller's load input: load after alighting admits
    r = eligible_boarders([up_a], Departure.UP, load=3, capacity=4)
    assert [p.passenger_id for p in r.boarders] == [1]
    # the two deferral classes never overlap and the input is sorted by id
    r = eligible_boarders([up_c, down_b, up_a], Departure.FREE, load=1, capacity=2)
    assert [p.passenger_id for p in r.boarders] == [1]
    assert [p.passenger_id for p in r.direction_deferred] == [2]
    assert [p.passenger_id for p in r.capacity_deferred] == [3]
    assert not set(r.direction_deferred) & set(r.capacity_deferred)


def test_project_matches_worked_examples():
    # W-C, candidate E0: at t=4 floor 2 UP with p1 onboard to 5; candidate p3 1->4
    e0 = RouteState(floor=2, heading=UP, onboard=(OnboardPassenger(1, 5),), waiting=())
    base = project(e0, capacity=2, now=4)
    assert base.dropoff_time == {1: 7} and base.end_time == 7 and base.max_load == 1
    with_p3 = project(e0, [W(3, 1, 4)], capacity=2, now=4)
    assert with_p3.dropoff_time[1] == 7
    assert with_p3.pickup_time[3] == 11 and with_p3.dropoff_time[3] == 14
    assert with_p3.first_compatible_arrival[3] == 11 and 3 not in with_p3.deferred
    assert with_p3.wrong_way_passes == {} and with_p3.end_time == 14
    # W-C, candidate E1: idle at 0
    e1 = RouteState(floor=0, heading=NONE, onboard=(), waiting=())
    r = project(e1, [W(3, 1, 4)], capacity=2, now=4)
    assert r.pickup_time[3] == 5 and r.dropoff_time[3] == 8 and r.end_time == 8
    # W-B: C=1, car at 0 idle at t=0 with p0 0->4 and p1 2->4 waiting
    wb = RouteState(floor=0, heading=NONE, onboard=(), waiting=(W(0, 0, 4), W(1, 2, 4)))
    r = project(wb, capacity=1, now=0)
    assert r.pickup_time == {0: 0, 1: 6} and r.dropoff_time == {0: 4, 1: 8}
    assert r.first_compatible_arrival[1] == 2 and r.deferred == frozenset({1})
    assert r.wrong_way_passes == {} and r.max_load == 1 and r.end_time == 8
    # W-F: p1 2->1 instead: a wrong-way pass at t=2, boards at 6, no capacity deferral
    wf = RouteState(floor=0, heading=NONE, onboard=(), waiting=(W(0, 0, 4), W(1, 2, 1)))
    r = project(wf, capacity=1, now=0)
    assert r.pickup_time == {0: 0, 1: 6} and r.dropoff_time == {0: 4, 1: 7}
    assert r.wrong_way_passes == {1: 1} and r.deferred == frozenset() and r.end_time == 7
    # W-G: F=7, car idle at 4, p0 5->6 and p1 3->0: both complete, final 8
    wg = RouteState(floor=4, heading=NONE, onboard=(), waiting=(W(0, 5, 6), W(1, 3, 0)))
    r = project(wg, capacity=2, now=0)
    assert r.pickup_time == {0: 1, 1: 5} and r.dropoff_time == {0: 2, 1: 8} and r.end_time == 8
    # an idle car with nothing to do ends now
    assert project(e1, capacity=2, now=9).end_time == 9
    # the projection never mutates its input
    assert e0.onboard == (OnboardPassenger(1, 5),) and wb.waiting == (W(0, 0, 4), W(1, 2, 4))


def test_route_module_depends_only_on_domain_and_stdlib():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "elevator", "route.py")
    with open(path, encoding="utf-8") as fh:
        source = fh.read()
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    forbidden = {"elevator.engine", "elevator.policies", "elevator.api", "elevator.checkpoint",
                 "elevator.reporting", "elevator.operations", "elevator.harness", "elevator.cli",
                 "web", "os", "sys", "io", "json", "random", "time", "datetime", "pathlib"}
    assert not (imported & forbidden), imported & forbidden
    assert {m for m in imported if m.startswith("elevator")} == {"elevator.domain"}
    assert "open(" not in source and "print(" not in source
