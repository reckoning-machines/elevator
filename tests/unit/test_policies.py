"""Cut 4 unit tests (testing_contract §1): the baseline policies."""

import ast
import dataclasses
import hashlib
import os
import subprocess
import sys

import pytest

from elevator.domain import (
    Configuration,
    ElevatorView,
    Heading,
    OnboardView,
    Proposal,
    RevealedRequest,
    SchedulerView,
    SimulationEventKind as K,
    WaitingView,
    canonical_json,
    normalize_requests,
)
from elevator.engine import Engine
from elevator.policies import NearestCar, RoundRobin
from tests.engine_fixtures import ByIdPolicy, build

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def view(floors, *, t=0, num_floors=10, capacity=4, extra=None):
    """A SchedulerView with one idle elevator per entry of ``floors``."""
    elevators = tuple(ElevatorView(id=i, floor=f, heading=Heading.NONE, onboard=(), waiting=())
                      for i, f in enumerate(floors))
    if extra:
        elevators = tuple(dataclasses.replace(e, **extra.get(e.id, {})) for e in elevators)
    return SchedulerView(t=t, floors=num_floors, num_elevators=len(floors), capacity=capacity,
                         elevators=elevators)


def req(pid, origin, dest=0, t=0):
    return RevealedRequest(passenger_id=pid, origin=origin, destination=dest, request_time=t)


# --- round_robin ---------------------------------------------------------

def test_round_robin_is_id_mod_n():
    eng, trace = build([(i, f"p{i}", 0, 1) for i in range(7)], floors=3, elevators=3, policy=RoundRobin())
    eng.run()
    assigned = [(e.passenger_id, e.elevator_id) for e in eng.history.events if e.kind is K.ASSIGNED]
    assert assigned == [(i, i % 3) for i in range(7)]
    assert [p.assigned_elevator for p in eng.passengers] == [0, 1, 2, 0, 1, 2, 0]
    # a direct call: the rule is passenger_id mod N, with no receipt, whatever the view says
    rr = RoundRobin()
    for n in (1, 2, 5):
        for pid in range(12):
            p = rr.assign(view([0] * n), req(pid, 3))
            assert p == Proposal(pid % n, None)
    # it ignores position, heading, load and committed work
    busy = view([9, 0, 4], extra={0: dict(heading=Heading.UP, onboard=(OnboardView(8, 9, 0),)),
                                  2: dict(waiting=(WaitingView(7, 4, 5, 0),))})
    assert rr.assign(busy, req(4, 9)) == Proposal(1, None)


def test_round_robin_is_stateless():
    rr = RoundRobin()
    v = view([0, 0, 0, 0])
    forward = [rr.assign(v, req(i, 1)) for i in range(10)]
    backward = [rr.assign(v, req(i, 1)) for i in reversed(range(10))][::-1]
    shuffled_order = [3, 9, 0, 7, 1, 5, 2, 8, 4, 6]
    shuffled = {i: RoundRobin().assign(v, req(i, 1)) for i in shuffled_order}
    assert forward == backward == [shuffled[i] for i in range(10)]
    assert rr.assign(v, req(6, 1)) == RoundRobin().assign(v, req(6, 1)) == forward[6]  # reused == fresh
    assert not vars(rr) and dataclasses.fields(rr) == ()
    with pytest.raises(dataclasses.FrozenInstanceError):
        rr.cursor = 1  # type: ignore[attr-defined]


# --- nearest_car ---------------------------------------------------------

def test_deterministic_tie_nearest_car():
    nc = NearestCar()
    # two cars equidistant (3 and 7 from 5): the lowest id wins, whichever order they are listed
    assert nc.assign(view([3, 7]), req(0, 5)) == Proposal(0, {"distance": 2})
    assert nc.assign(view([7, 3]), req(0, 5)) == Proposal(0, {"distance": 2})
    # three-way and same-floor ties
    assert nc.assign(view([4, 6, 4, 6]), req(0, 5)).elevator_id == 0
    assert nc.assign(view([6, 5, 5]), req(0, 5)) == Proposal(1, {"distance": 0})
    # no ids are skipped for being busy, and listing order does not decide the tie
    v = view([7, 3])
    shuffled = dataclasses.replace(v, elevators=tuple(reversed(v.elevators)))
    assert nc.assign(shuffled, req(0, 5)).elevator_id == 0


def test_nearest_car_is_the_naive_baseline():
    nc = NearestCar()
    # nearest wins even if it is full, heading away, or has more committed work
    full = tuple(OnboardView(10 + i, 9, 0) for i in range(4))
    v = view([4, 5, 9], extra={1: dict(heading=Heading.DOWN, onboard=full), 0: dict(heading=Heading.UP)})
    assert nc.assign(v, req(0, 5, 9)) == Proposal(1, {"distance": 0})
    # a farther idle car is never preferred
    assert nc.assign(view([0, 8]), req(0, 7)) == Proposal(1, {"distance": 1})
    # receipt: a plain mapping of one integer
    receipt = nc.assign(view([2]), req(0, 9)).receipt
    assert receipt == {"distance": 7} and set(receipt) == {"distance"} and type(receipt["distance"]) is int
    # stateless: same view and request, same proposal, any number of times, fresh or reused
    first = nc.assign(view([3, 7]), req(0, 5))
    assert [nc.assign(view([3, 7]), req(0, 5)) for _ in range(5)] == [first] * 5
    assert NearestCar().assign(view([3, 7]), req(0, 5)) == first
    assert not vars(nc) and dataclasses.fields(nc) == ()


def test_policies_do_not_mutate_the_view():
    for policy in (RoundRobin(), NearestCar()):
        v = view([2, 8], extra={0: dict(onboard=(OnboardView(1, 4, 0),))})
        snapshot = repr(v)
        policy.assign(v, req(3, 5))
        assert repr(v) == snapshot
        with pytest.raises(dataclasses.FrozenInstanceError):
            v.t = 9  # type: ignore[misc]
        with pytest.raises(dataclasses.FrozenInstanceError):
            v.elevators[0].floor = 9  # type: ignore[misc]


def test_baselines_with_simultaneous_requests_and_engine_commit():
    # two requests at t=0: the second call's view already holds the first assignment,
    # but each baseline's decision depends only on the fields it is defined to read
    seen = []

    class Spy:
        def __init__(self, inner):
            self.inner = inner

        def assign(self, v, r):
            seen.append((v, r))
            return self.inner.assign(v, r)

    rows = [(0, "a", 3, 5), (0, "b", 3, 1)]
    cfg = Configuration.create(6, 2, 2, initial_floors=[0, 4], policy="nearest_car")
    eng = Engine.create(cfg, normalize_requests(rows, 6), Spy(NearestCar()))
    eng.step()
    (v0, r0), (v1, r1) = seen
    assert (r0.passenger_id, r1.passenger_id) == (0, 1)
    assert [w.passenger_id for e in v0.elevators for w in e.waiting] == []
    assert [w.passenger_id for w in v1.elevators[1].waiting] == [0]  # the first assignment is visible
    assigned = [(e.passenger_id, e.elevator_id, dict(e.receipt)) for e in eng.history.events if e.kind is K.ASSIGNED]
    assert assigned == [(0, 1, {"distance": 1}), (1, 1, {"distance": 1})]  # ignores committed work

    seen.clear()
    eng = Engine.create(Configuration.create(6, 2, 2, policy="round_robin"), normalize_requests(rows, 6),
                        Spy(RoundRobin()))
    eng.step()
    assert [(e.passenger_id, e.elevator_id, e.receipt) for e in eng.history.events if e.kind is K.ASSIGNED] == \
        [(0, 0, None), (1, 1, None)]


def test_receipts_survive_history_freezing_and_are_canonical():
    eng, _ = build([(0, "a", 4, 2)], floors=6, elevators=2, initial=[0, 5], policy=NearestCar())
    eng.run()
    (assigned,) = [e for e in eng.history.events if e.kind is K.ASSIGNED]
    assert assigned.receipt == {"distance": 1}
    with pytest.raises(TypeError):
        assigned.receipt["distance"] = 0
    first = canonical_json(eng.history)
    eng2, _ = build([(0, "a", 4, 2)], floors=6, elevators=2, initial=[0, 5], policy=NearestCar())
    eng2.run()
    assert canonical_json(eng2.history) == first


# --- structure -----------------------------------------------------------

def _policies_tree():
    with open(os.path.join(ROOT, "elevator", "policies.py"), encoding="utf-8") as fh:
        return ast.parse(fh.read())


def test_policy_cannot_import_trace():
    tree = _policies_tree()
    imported = set()
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            imported.add(n.module or "")
            names |= {a.name for a in n.names}
        elif isinstance(n, ast.Name):
            names.add(n.id)
    # project imports: domain, and route for the shared projection (architecture §1: policies depend
    # on domain and route); nothing from the engine, and no Trace or engine type is named
    assert {m for m in imported if m.startswith("elevator")} == {"elevator", "elevator.domain"}
    assert names >= {"route"} and "engine" not in names
    assert not imported & {"elevator.engine", "elevator.api", "elevator.reporting", "elevator.checkpoint",
                           "elevator.operations", "elevator.harness", "elevator.cli", "web"}
    route_attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
                   and isinstance(n.value, ast.Name) and n.value.id == "route"}
    assert route_attrs <= {"project", "Projection"}, route_attrs
    assert not imported & {"os", "sys", "io", "json", "random", "time", "datetime", "pathlib", "secrets"}
    assert not names & {"Trace", "Engine", "SimulationHistory", "Request", "Passenger", "Configuration"}
    # no attribute path to a trace or engine either
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not attrs & {"trace", "_trace", "history", "engine", "requests", "_passengers"}
    # the module imports cleanly without loading the engine
    out = subprocess.run([sys.executable, "-B", "-c",
                          "import sys; import elevator.policies; print('elevator.engine' in sys.modules)"],
                         capture_output=True, text=True, cwd=ROOT, env={**os.environ, "PYTHONPATH": ROOT}, check=True)
    assert out.stdout.strip() == "False"


def test_policies_hold_no_module_level_state_and_define_no_route_mechanics():
    tree = _policies_tree()
    for node in tree.body:
        assert isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef, ast.Expr)) or (
            isinstance(node, ast.FunctionDef)), ast.dump(node)[:80]
    # the engine/policy half of route_primitives_single_implementation: no function defined
    # here computes a departure direction, boarding eligibility or heading
    defs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert not {d for d in defs if any(k in d for k in ("departure", "boarder", "heading", "look"))}
    # class bodies hold constants only: a string name, no mutable defaults
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        for stmt in cls.body:
            if isinstance(stmt, ast.Assign):
                assert isinstance(stmt.value, ast.Constant)


def test_baseline_runs_are_identical_across_processes():
    script = (
        "import hashlib\n"
        "from elevator.domain import Configuration, normalize_requests, canonical_json\n"
        "from elevator.engine import Engine\n"
        "from elevator.policies import RoundRobin, NearestCar\n"
        "rows=[(0,'a',0,5),(0,'b',4,1),(2,'c',3,0),(5,'d',1,5),(5,'e',5,2)]\n"
        "out=[]\n"
        "for name,p in (('round_robin',RoundRobin()),('nearest_car',NearestCar())):\n"
        "    e=Engine.create(Configuration.create(6,3,2,initial_floors=[0,3,5],policy=name),normalize_requests(rows,6),p); e.run()\n"
        "    out.append(hashlib.sha256(canonical_json(e.history)).hexdigest())\n"
        "print(','.join(out))\n")
    env = {**os.environ, "PYTHONPATH": ROOT}
    runs = [subprocess.run([sys.executable, "-B", "-c", script], capture_output=True, text=True, cwd=ROOT,
                           env=env, check=True).stdout.strip() for _ in range(2)]
    assert runs[0] == runs[1] and len(runs[0].split(",")) == 2
    # and equal to an in-process run
    from elevator.domain import canonical_json as cj
    rows = [(0, 'a', 0, 5), (0, 'b', 4, 1), (2, 'c', 3, 0), (5, 'd', 1, 5), (5, 'e', 5, 2)]
    local = []
    for name, p in (("round_robin", RoundRobin()), ("nearest_car", NearestCar())):
        e = Engine.create(Configuration.create(6, 3, 2, initial_floors=[0, 3, 5], policy=name),
                          normalize_requests(rows, 6), p)
        e.run()
        local.append(hashlib.sha256(cj(e.history)).hexdigest())
    assert ",".join(local) == runs[0]
