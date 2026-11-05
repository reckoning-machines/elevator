"""Cut 3 repair tests for the independent audit findings C3-I-01 to C3-I-03."""

import os
import sys
import types

import pytest

import elevator.engine as engine_module
from elevator import route
from elevator.domain import (
    Configuration,
    Heading,
    Proposal,
    SimulationEvent,
    SimulationEventKind as K,
    canonical_json,
    normalize_requests,
)
from elevator.engine import HALTED, INVARIANT_VIOLATION
from tests.engine_fixtures import build

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --- C3-I-01: committed Simulation History is immutable all the way down ---

class ReceiptPolicy:
    """Hands the engine a receipt it keeps a reference to and mutates later."""

    def __init__(self):
        self.receipts = []

    def assign(self, view, request):
        receipt = {"tier": 1, "candidates": [{"E": 0, "cost": 5}], "note": "orig"}
        self.receipts.append(receipt)
        return Proposal(0, receipt)


def test_history_survives_mutation_of_the_source_receipt():
    policy = ReceiptPolicy()
    eng, _ = build([(0, "a", 0, 2)], floors=3, policy=policy)
    eng.run()
    before = canonical_json(eng.history)
    src = policy.receipts[0]
    src["tier"] = 99
    src["candidates"].append({"E": 9})
    src["candidates"][0]["cost"] = -1
    src["injected"] = True
    assert canonical_json(eng.history) == before
    (assigned,) = [e for e in eng.history.events if e.kind is K.ASSIGNED]
    assert assigned.receipt == {"candidates": ({"E": 0, "cost": 5},), "note": "orig", "tier": 1}


def test_committed_payloads_cannot_be_mutated_through_history():
    eng, _ = build([(0, "a", 0, 2)], floors=3, policy=ReceiptPolicy())
    eng.run()
    before = canonical_json(eng.history)
    (assigned,) = [e for e in eng.history.events if e.kind is K.ASSIGNED]
    with pytest.raises(TypeError):
        assigned.receipt["tier"] = 2
    with pytest.raises(TypeError):
        assigned.receipt["candidates"][0]["cost"] = 0
    with pytest.raises(AttributeError):
        assigned.receipt["candidates"].append({})
    with pytest.raises(AttributeError):
        eng.history.events.append(assigned)
    with pytest.raises(AttributeError):
        eng.history.tick_records[0].entries[0].boarded.append(9)
    with pytest.raises(Exception):
        assigned.receipt = {}  # frozen dataclass
    assert canonical_json(eng.history) == before


def test_history_survives_mutation_of_a_halt_source_payload():
    halt = {"step": "ASSIGN", "reason": "INVALID_PROPOSAL", "passenger": 0, "unserved": 1, "path": [1, 2]}
    ev = SimulationEvent(seq=0, kind=K.HALTED, tick=0, passenger_id=0, halt=halt)
    frozen = canonical_json(ev)
    halt["reason"] = "TAMPERED"
    halt["path"].append(3)
    assert canonical_json(ev) == frozen and ev.halt["reason"] == "INVALID_PROPOSAL"
    # an engine-produced halt payload is frozen too
    eng, _ = build([(0, "a", 0, 2)], floors=3, policy=type("P", (), {"assign": lambda s, v, r: Proposal(7)})())
    eng.run()
    with pytest.raises(TypeError):
        eng.history.events[-1].halt["reason"] = "X"


def test_history_serialisation_deterministic_after_freezing():
    a, _ = build([(0, "a", 0, 2), (1, "b", 2, 0)], floors=3, policy=ReceiptPolicy())
    b, _ = build([(0, "a", 0, 2), (1, "b", 2, 0)], floors=3, policy=ReceiptPolicy())
    a.run(); b.run()
    assert canonical_json(a.history) == canonical_json(b.history)
    assert a.history == b.history
    # key order in the source receipt does not affect the committed bytes
    e1 = SimulationEvent(seq=0, kind=K.ASSIGNED, tick=0, receipt={"b": 1, "a": 2})
    e2 = SimulationEvent(seq=0, kind=K.ASSIGNED, tick=0, receipt={"a": 2, "b": 1})
    assert canonical_json(e1) == canonical_json(e2)
    # a receipt that cannot be frozen canonically is an invalid proposal
    class FloatReceipt:
        def assign(self, view, request):
            return Proposal(0, {"cost": 1.5})
    eng, _ = build([(0, "a", 0, 2)], floors=3, policy=FloatReceipt())
    assert eng.run().halt_reason == "INVALID_PROPOSAL"


# --- C3-I-03: the engine actually invokes the shared route primitives ---

def _runtime_primitive_proof(engine_cls, monkeypatch):
    """Patch each shared primitive with a spy that returns a distinctive,
    lawful-shaped result, and check the engine's observable output follows
    it. Returns {primitive: proven}."""
    proven = {}

    def make(rows, floors, initial):
        trace = normalize_requests(rows, floors)
        cfg = Configuration.create(floors, 1, 4, initial_floors=initial, policy="round_robin")
        return engine_cls(cfg, trace, type("P", (), {"assign": lambda s, v, r: Proposal(0)})())

    # next_heading: idle car at 2, stop above at 4; the spy says DOWN.
    calls = []
    original = route.next_heading
    def spy_next(floor, heading, stops):
        calls.append((floor, heading, tuple(stops)))
        return Heading.DOWN if (floor, heading) == (2, Heading.NONE) else original(floor, heading, stops)
    monkeypatch.setattr(route, "next_heading", spy_next)
    eng = make([(0, "a", 4, 5)], floors=6, initial=[2])
    eng.step()
    proven["next_heading"] = bool(calls) and eng.history.tick_records[0].entries[0].heading is Heading.DOWN
    monkeypatch.setattr(route, "next_heading", original)

    # departure_direction: idle car at 2 with a down-bound passenger there would
    # be FREE and board; the spy says UP, so the passenger is direction-deferred.
    calls = []
    original_d = route.departure_direction
    def spy_dep(floor, heading, stops):
        calls.append(floor)
        return route.Departure.UP
    monkeypatch.setattr(route, "departure_direction", spy_dep)
    eng = make([(0, "a", 2, 0)], floors=4, initial=[2])
    eng.step()
    proven["departure_direction"] = bool(calls) and eng.history.tick_records[0].entries[0].boarded == ()
    monkeypatch.setattr(route, "departure_direction", original_d)

    # eligible_boarders: the spy boards nobody; the passenger stays waiting.
    calls = []
    original_e = route.eligible_boarders
    def spy_elig(waiting, departure, load, capacity):
        calls.append(len(waiting))
        return route.BoardingResult(boarders=(), departure=departure, direction_deferred=(), capacity_deferred=())
    monkeypatch.setattr(route, "eligible_boarders", spy_elig)
    eng = make([(0, "a", 2, 0)], floors=4, initial=[2])
    eng.step()
    proven["eligible_boarders"] = bool(calls) and eng.history.tick_records[0].entries[0].boarded == ()
    monkeypatch.setattr(route, "eligible_boarders", original_e)
    return proven


def test_engine_invokes_shared_route_primitives_at_runtime(monkeypatch):
    assert _runtime_primitive_proof(engine_module.Engine, monkeypatch) == {
        "next_heading": True, "departure_direction": True, "eligible_boarders": True}


def test_runtime_proof_detects_an_engine_that_bypasses_the_primitives(monkeypatch):
    """A variant engine that binds its own copies of the primitives at import
    (so patching the route module cannot reach them) must fail the proof."""
    with open(os.path.join(ROOT, "elevator", "engine.py"), encoding="utf-8") as fh:
        src = fh.read()
    for name in ("departure_direction", "eligible_boarders", "next_heading"):
        src = src.replace(f"route.{name}(", f"_dup_{name}(")
    src = src.replace("from elevator import route\n",
                      "from elevator import route\n"
                      "from elevator.route import departure_direction as _dup_departure_direction\n"
                      "from elevator.route import eligible_boarders as _dup_eligible_boarders\n"
                      "from elevator.route import next_heading as _dup_next_heading\n")
    variant = types.ModuleType("elevator._bypassing_engine_variant")
    monkeypatch.setitem(sys.modules, variant.__name__, variant)
    exec(compile(src, "<bypassing variant>", "exec"), variant.__dict__)
    # the variant still produces correct simulations ...
    eng, _ = build([(0, "p0", 0, 3)], floors=4)
    ref = canonical_json(eng.history) if eng.run() else None
    trace = normalize_requests([(0, "p0", 0, 3)], 4)
    cfg = Configuration.create(4, 1, 4, policy="round_robin")
    v = variant.Engine(cfg, trace, type("P", (), {"assign": lambda s, vw, r: Proposal(0)})())
    v.run()
    assert canonical_json(v.history) == ref
    # ... but the runtime proof catches every bypassed primitive
    assert _runtime_primitive_proof(variant.Engine, monkeypatch) == {
        "next_heading": False, "departure_direction": False, "eligible_boarders": False}


# --- C3-I-02: detected corruption halts the Run (owner decision 008) ---

def _corrupt_at_tick_2(monkeypatch, rows, floors, capacity, primitive, fake):
    """Run ticks 0 and 1 normally, patch one shared primitive for tick 2,
    step once, then restore it. Returns the engine and the committed state
    before tick 2."""
    eng, trace = build(rows, floors=floors, capacity=capacity)
    eng.step(); eng.step()
    prior = (canonical_json(eng.history), eng.history.events, eng.history.tick_records,
             eng.passengers, eng.elevators, eng.t)
    monkeypatch.setattr(route, primitive, fake)
    out = eng.step()
    monkeypatch.undo()
    return eng, trace, prior, out


def _assert_invariant_halt(eng, prior, out, *, step, invariant, passenger, elevator, unserved):
    _bytes, events, records, passengers, elevators, t = prior
    assert out is eng.outcome
    assert (out.standing, out.final_tick, out.halt_step, out.halt_reason, out.halt_passenger, out.unserved) == \
        (HALTED, t, step, INVARIANT_VIOLATION, passenger, unserved)
    # the failing tick is discarded entirely: no REVEALED, ASSIGNED, BOARDED or
    # TickRecord from it; earlier ticks are kept byte for byte
    assert eng.history.tick_records == records
    assert eng.history.events[:-1] == events
    (halted,) = eng.history.events[len(events):]
    assert halted.kind is K.HALTED and halted.seq == len(events) and halted.tick == t
    assert halted.passenger_id == passenger
    assert halted.halt["reason"] == INVARIANT_VIOLATION and halted.halt["step"] == step
    assert halted.halt["invariant"] == invariant and halted.halt["elevator"] == elevator
    assert halted.halt["passenger"] == passenger and halted.halt["unserved"] == unserved
    assert halted.halt["detail"]
    assert eng.passengers == passengers and eng.elevators == elevators and eng.t == t
    # the Run is final: with the primitive restored, step() does no work
    after = canonical_json(eng.history)
    assert eng.step() is out and eng.run() is out
    assert canonical_json(eng.history) == after and eng.t == t and eng.standing == HALTED


def test_detected_corruption_halts_the_run(monkeypatch):
    # (a) wrong-way boarding (N7): a rides 0->1 in ticks 0-1; the idle car is at
    # floor 1 when b (1->0, down-bound) is revealed at tick 2; the patched
    # primitive boards b with departure UP.
    def wrong_way(waiting, departure, load, capacity):
        return route.BoardingResult(boarders=tuple(waiting), departure=route.Departure.UP,
                                    direction_deferred=(), capacity_deferred=())
    eng, _, prior, out = _corrupt_at_tick_2(
        monkeypatch, [(0, "a", 0, 1), (2, "b", 1, 0)], 3, 4, "eligible_boarders", wrong_way)
    _assert_invariant_halt(eng, prior, out, step="BOARD", invariant="N7", passenger=1, elevator=0, unserved=1)

    # (b) capacity (P3): C=1; two up-bound passengers revealed at the car's floor
    # at tick 2; the patched primitive boards both.
    def overfill(waiting, departure, load, capacity):
        return route.BoardingResult(boarders=tuple(waiting), departure=route.Departure.UP,
                                    direction_deferred=(), capacity_deferred=())
    eng, _, prior, out = _corrupt_at_tick_2(
        monkeypatch, [(0, "a", 0, 1), (2, "b", 1, 2), (2, "c", 1, 2)], 3, 1, "eligible_boarders", overfill)
    _assert_invariant_halt(eng, prior, out, step="BOARD", invariant="P3", passenger=None, elevator=0, unserved=2)
    assert not any(e.kind in (K.REVEALED, K.ASSIGNED) and e.passenger_id in (1, 2) for e in eng.history.events)

    # (c) floor bounds (P2): F=2; the car is idle at the top floor at tick 2; the
    # patched next_heading sends it UP, out of the building, in step 8.
    eng, _, prior, out = _corrupt_at_tick_2(
        monkeypatch, [(0, "a", 0, 1), (9, "b", 1, 0)], 2, 4, "next_heading",
        lambda floor, heading, stops: Heading.UP)
    _assert_invariant_halt(eng, prior, out, step="MOVE", invariant="P2", passenger=None, elevator=0, unserved=1)


def test_invariant_violation_is_the_single_canonical_reason():
    import elevator.engine as em
    reasons = {v for k, v in vars(em).items() if k.isupper() and isinstance(v, str)} - {"COMPLETED", "HALTED", "RUNNING"}
    assert reasons == {"INVALID_PROPOSAL", "POLICY_ERROR", "LIVENESS_BOUND_EXCEEDED", "HORIZON_EXCEEDED",
                       "INVARIANT_VIOLATION"}
    # ordinary halts keep their admitted payload shape (no diagnostic fields)
    eng, _ = build([(0, "p0", 0, 3)], floors=4, policy=type("P", (), {"assign": lambda s, v, r: Proposal(5)})())
    eng.run()
    assert set(eng.history.events[-1].halt) == {"step", "reason", "passenger", "unserved"}
