"""Store, Continuation Document, write admission, loader and resume (plan cut 9; cpoc_design §2 to §5).

This module is the only writer and the only loader of Continuation Documents (authority row 23). It owns no
simulation fact: the engine remains the sole writer of runtime state, and the loader only *constructs* an
``EngineState`` from a typed ``Snapshot`` and hands it to ``Engine.restore``. Three boundaries are
structural, not conventions:

- ``Snapshot`` is produced only by ``parse_snapshot(document)``, which reads the document's snapshot section
  and nothing else; ``construct_state`` takes exactly one ``Snapshot`` and rejects any other type;
- ``HistoryPrefix`` (the evidence) and ``HistoryVerifier`` (an isolated replay that answers only "is the
  History internally lawful") are distinct types with no conversion to a ``Snapshot`` or an ``EngineState``;
- no function in the package takes a ``HistoryPrefix``, events, TickRecords or a ``HistoryVerifier`` and
  returns a ``Snapshot`` or an ``EngineState`` (constitution N14: no recovery by recomputation).

A document never contains a hash of itself, an Operational Record, a provenance block or a timestamp. Every
refusal is a named reason from cpoc §3.2 or §5; nothing is repaired, no bad artifact is overwritten, and no
step has an override. Atomic replace (temp file, fsync, rename) means the path never holds a torn document;
the bounded claim is exactly cpoc §3.3: nothing stronger about crash consistency is made.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from elevator import route
from elevator.domain import (
    CONTINUATION_SCHEMA_VERSION,
    STORE_SCHEMA_VERSION,
    Configuration,
    Heading,
    OperationalRecordKind as K,
    Refusal,
    RunIdentity,
    SimulationEvent,
    SimulationEventKind as E,
    SimulationHistory,
    Standing,
    TickEntry,
    TickRecord,
    Trace,
    bind_run,
    canonical_json,
    establish_code_identity,
    freeze,
    normalize_requests,
    sha256_hex,
)
from elevator.engine import (
    COMPLETED,
    HALTED,
    Engine,
    ElevatorState,
    EngineState,
    PassengerState,
)
from elevator.operations import Execution, resume_execution
from elevator.policies import make_policy

STORE_FILE = "store.json"
DOCUMENT_FILE = "run.json"
TEMP_FILE = "run.json.tmp"
RUNNING = "RUNNING"

_SIM_EVENT_KINDS = {k.value for k in E}
_HEADINGS = {h.value for h in Heading}
_STANDINGS = {s.value for s in Standing}


class CheckpointRefusal(Refusal):
    """A named refusal of a load or a write (cpoc §3.2, §5). ``step`` is the load verification at which it
    arose (1 to 11), or ``None`` for a write refusal. Nothing is partially loaded or written."""

    def __init__(self, reason: str, detail: str, *, step: int | None = None) -> None:
        self.step = step
        super().__init__(reason, detail)


# ---------------------------------------------------------------------------
# The Store (cpoc §2.2): one directory, one identity file
# ---------------------------------------------------------------------------

def init_store(path: str) -> str:
    """Create a Store at ``path``: ``store.json`` carries ``store_id`` (random 128-bit, UUID version 4) and
    the Store schema version. Never overwrites an existing Store."""
    os.makedirs(path, exist_ok=True)
    store_id = str(uuid.uuid4())
    with open(os.path.join(path, STORE_FILE), "xb") as fh:
        fh.write(canonical_json({"store_id": store_id, "store_schema_version": STORE_SCHEMA_VERSION}))
        fh.flush()
        os.fsync(fh.fileno())
    return store_id


def read_store(path: str) -> str:
    """Load verification 1: the Store directory and ``store.json`` exist, parse and carry this code's Store
    schema version. Returns ``store_id``."""
    if not os.path.isdir(path) or not os.path.isfile(os.path.join(path, STORE_FILE)):
        raise CheckpointRefusal("STORE_NOT_FOUND", f"{path} is not a Store", step=1)
    try:
        with open(os.path.join(path, STORE_FILE), "rb") as fh:
            meta = json.loads(fh.read())
    except (ValueError, OSError) as exc:
        raise CheckpointRefusal("STORE_MALFORMED", f"store.json does not parse: {exc}", step=1) from exc
    if not isinstance(meta, dict) or set(meta) != {"store_id", "store_schema_version"} \
            or not isinstance(meta["store_id"], str) or not meta["store_id"] \
            or not _is_int(meta["store_schema_version"]):
        raise CheckpointRefusal("STORE_MALFORMED", "store.json has the wrong shape", step=1)
    if meta["store_schema_version"] != STORE_SCHEMA_VERSION:
        raise CheckpointRefusal("STORE_SCHEMA_MISMATCH", f"Store schema {meta['store_schema_version']}, "
                                f"this code reads {STORE_SCHEMA_VERSION}", step=1)
    return meta["store_id"]


def execution_dir(store: str, execution_id: str) -> str:
    return os.path.join(store, execution_id)


def document_path(store: str, execution_id: str) -> str:
    return os.path.join(store, execution_id, DOCUMENT_FILE)


# ---------------------------------------------------------------------------
# The typed boundary (cpoc §5.1)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Snapshot:
    """The Checkpoint: the engine's state at a tick boundary, exactly the snapshot section of a document.
    Produced only by ``parse_snapshot``."""

    t: int
    elevators: tuple[ElevatorState, ...]
    passengers: tuple[PassengerState, ...]
    snapshot_hash: str


@dataclass(frozen=True)
class HistoryPrefix:
    """The Simulation History prefix of a document, as evidence: it is attached to the resumed engine
    without transformation and is never converted to, or used to build, a ``Snapshot`` or engine state."""

    events: tuple[SimulationEvent, ...]
    tick_records: tuple[TickRecord, ...]
    history_hash: str


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _fail_float(text: str) -> Any:
    raise ValueError(f"floats are not part of any document: {text}")


def _fail_constant(text: str) -> Any:
    raise ValueError(f"{text} is not valid JSON")


# ---------------------------------------------------------------------------
# Schema (load verification 2): every required section and field, right types, no unknown keys
# ---------------------------------------------------------------------------

def _malformed(detail: str) -> CheckpointRefusal:
    return CheckpointRefusal("MALFORMED", detail, step=2)


def _keys(node: Any, required: set[str], where: str, optional: frozenset[str] = frozenset()) -> dict[str, Any]:
    if not isinstance(node, dict):
        raise _malformed(f"{where} must be an object")
    missing = required - set(node)
    unknown = set(node) - required - optional
    if missing:
        raise _malformed(f"{where} lacks {sorted(missing)}")
    if unknown:
        raise _malformed(f"{where} has unknown fields {sorted(unknown)}")
    return node


def _int(node: Any, where: str, *, minimum: int | None = None, nullable: bool = False) -> int | None:
    if node is None and nullable:
        return None
    if not _is_int(node) or (minimum is not None and node < minimum):
        raise _malformed(f"{where} must be an integer" + (f" >= {minimum}" if minimum is not None else ""))
    return node


def _str(node: Any, where: str) -> str:
    if not isinstance(node, str):
        raise _malformed(f"{where} must be a string")
    return node


def _int_list(node: Any, where: str) -> list[int]:
    if not isinstance(node, list):
        raise _malformed(f"{where} must be a list")
    return [_int(x, f"{where}[{i}]") for i, x in enumerate(node)]  # type: ignore[misc]


def parse_document_bytes(raw: bytes) -> dict[str, Any]:
    """Parse and validate a Continuation Document against the schema. Returns the parsed document; raises
    ``MALFORMED`` at step 2 for anything the schema does not allow. A missing or mistyped field fails here,
    not later; the schema allows only Simulation Event kinds among the events."""
    try:
        doc = json.loads(raw, parse_float=_fail_float, parse_constant=_fail_constant)
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise _malformed(f"the document does not parse: {exc}") from exc
    _keys(doc, {"schema_version", "store_id", "execution_id", "run_id", "code_identity", "configuration_hash",
                "trace_hash", "write_sequence", "configuration", "trace", "standing", "final",
                "simulation_history"}, "the document", frozenset({"snapshot"}))
    _int(doc["schema_version"], "schema_version")
    for name in ("store_id", "execution_id", "run_id", "code_identity", "configuration_hash", "trace_hash"):
        _str(doc[name], name)
    _int(doc["write_sequence"], "write_sequence", minimum=1)
    if doc["standing"] not in {RUNNING, COMPLETED, HALTED}:
        raise _malformed("standing must be RUNNING, COMPLETED or HALTED")
    cfg = _keys(doc["configuration"], {"num_floors", "num_elevators", "capacity", "initial_floors", "max_ticks",
                                       "policy", "policy_params"}, "configuration")
    for name in ("num_floors", "num_elevators", "capacity"):
        _int(cfg[name], f"configuration.{name}")
    _int_list(cfg["initial_floors"], "configuration.initial_floors")
    _int(cfg["max_ticks"], "configuration.max_ticks", nullable=True)
    _str(cfg["policy"], "configuration.policy")
    params = cfg["policy_params"]
    if not isinstance(params, dict) or not all(isinstance(k, str) and _is_int(v) for k, v in params.items()):
        raise _malformed("configuration.policy_params must map names to integers")
    if not isinstance(doc["trace"], list):
        raise _malformed("trace must be a list")
    for i, row in enumerate(doc["trace"]):
        if not isinstance(row, list) or len(row) != 4 or not _is_int(row[0]) or not isinstance(row[1], str) \
                or not _is_int(row[2]) or not _is_int(row[3]):
            raise _malformed(f"trace[{i}] must be [time, source_id, origin, dest]")
    final = doc["final"]
    if final is not None:
        _keys(final, {"final_tick"}, "final", frozenset({"halt_step", "halt_reason", "halt_passenger"}))
        _int(final["final_tick"], "final.final_tick", minimum=0)
        for name in ("halt_step", "halt_reason"):
            if name in final:
                _str(final[name], f"final.{name}")
        if "halt_passenger" in final:
            _int(final["halt_passenger"], "final.halt_passenger", nullable=True)
    if "snapshot" in doc:
        snap = _keys(doc["snapshot"], {"t", "elevators", "passengers", "snapshot_hash"}, "snapshot")
        _int(snap["t"], "snapshot.t", minimum=0)
        _str(snap["snapshot_hash"], "snapshot.snapshot_hash")
        if not isinstance(snap["elevators"], list):
            raise _malformed("snapshot.elevators must be a list")
        for i, el in enumerate(snap["elevators"]):
            _keys(el, {"id", "floor", "heading"}, f"snapshot.elevators[{i}]")
            _int(el["id"], f"snapshot.elevators[{i}].id")
            _int(el["floor"], f"snapshot.elevators[{i}].floor")
            if el["heading"] not in _HEADINGS:
                raise _malformed(f"snapshot.elevators[{i}].heading must be UP, DOWN or NONE")
        if not isinstance(snap["passengers"], list):
            raise _malformed("snapshot.passengers must be a list")
        for i, p in enumerate(snap["passengers"]):
            _keys(p, {"passenger_id", "source_id", "standing", "assigned_elevator", "assigned_at", "pickup_time",
                      "dropoff_time"}, f"snapshot.passengers[{i}]")
            _int(p["passenger_id"], f"snapshot.passengers[{i}].passenger_id")
            _str(p["source_id"], f"snapshot.passengers[{i}].source_id")
            if p["standing"] not in _STANDINGS:
                raise _malformed(f"snapshot.passengers[{i}].standing is not a Passenger standing")
            _int(p["assigned_elevator"], f"snapshot.passengers[{i}].assigned_elevator")
            _int(p["assigned_at"], f"snapshot.passengers[{i}].assigned_at")
            _int(p["pickup_time"], f"snapshot.passengers[{i}].pickup_time", nullable=True)
            _int(p["dropoff_time"], f"snapshot.passengers[{i}].dropoff_time", nullable=True)
    hist = _keys(doc["simulation_history"], {"events", "tick_records", "history_hash"}, "simulation_history")
    _str(hist["history_hash"], "simulation_history.history_hash")
    if not isinstance(hist["events"], list) or not isinstance(hist["tick_records"], list):
        raise _malformed("simulation_history.events and tick_records must be lists")
    for i, ev in enumerate(hist["events"]):
        _keys(ev, {"seq", "kind", "tick", "passenger_id", "elevator_id", "floor", "receipt", "halt"},
              f"events[{i}]")
        if ev["kind"] not in _SIM_EVENT_KINDS:  # an Operational Record, or an unknown kind, is not an event
            raise _malformed(f"events[{i}].kind {ev['kind']!r} is not a Simulation Event kind")
        _int(ev["seq"], f"events[{i}].seq")
        _int(ev["tick"], f"events[{i}].tick")
        for name in ("passenger_id", "elevator_id", "floor"):
            _int(ev[name], f"events[{i}].{name}", nullable=True)
        for name in ("receipt", "halt"):
            if ev[name] is not None and not isinstance(ev[name], dict):
                raise _malformed(f"events[{i}].{name} must be an object or null")
    for i, tr in enumerate(hist["tick_records"]):
        _keys(tr, {"tick", "entries"}, f"tick_records[{i}]")
        _int(tr["tick"], f"tick_records[{i}].tick")
        if not isinstance(tr["entries"], list):
            raise _malformed(f"tick_records[{i}].entries must be a list")
        for j, en in enumerate(tr["entries"]):
            where = f"tick_records[{i}].entries[{j}]"
            _keys(en, {"elevator_id", "floor", "heading", "load", "boarded", "alighted"}, where)
            for name in ("elevator_id", "floor", "load"):
                _int(en[name], f"{where}.{name}")
            if en["heading"] not in _HEADINGS:
                raise _malformed(f"{where}.heading must be UP, DOWN or NONE")
            _int_list(en["boarded"], f"{where}.boarded")
            _int_list(en["alighted"], f"{where}.alighted")
    return doc


def parse_snapshot(document: Mapping[str, Any]) -> Snapshot:
    """The only constructor of a ``Snapshot``: it reads the document's snapshot section and nothing else. It
    accepts no events, tick records or ``HistoryPrefix``."""
    snap = document["snapshot"]
    return Snapshot(
        t=snap["t"],
        elevators=tuple(ElevatorState(e["id"], e["floor"], Heading(e["heading"])) for e in snap["elevators"]),
        passengers=tuple(PassengerState(p["passenger_id"], p["source_id"], Standing(p["standing"]),
                                        p["assigned_elevator"], p["assigned_at"], p["pickup_time"],
                                        p["dropoff_time"]) for p in snap["passengers"]),
        snapshot_hash=snap["snapshot_hash"])


def parse_history(document: Mapping[str, Any]) -> HistoryPrefix:
    """The document's Simulation History section as evidence (a ``HistoryPrefix``), never as state."""
    hist = document["simulation_history"]
    events = tuple(SimulationEvent(
        seq=e["seq"], kind=E(e["kind"]), tick=e["tick"], passenger_id=e["passenger_id"],
        elevator_id=e["elevator_id"], floor=e["floor"], receipt=e["receipt"], halt=e["halt"])
        for e in hist["events"])
    records = tuple(TickRecord(tick=r["tick"], entries=tuple(
        TickEntry(en["elevator_id"], en["floor"], Heading(en["heading"]), en["load"], tuple(en["boarded"]),
                  tuple(en["alighted"])) for en in r["entries"])) for r in hist["tick_records"])
    return HistoryPrefix(events, records, hist["history_hash"])


def construct_state(snapshot: Snapshot) -> EngineState:
    """The only function in the package that produces engine state during a resume, called only by ``load``.
    It takes exactly one ``Snapshot`` and rejects anything else at runtime, so a ``HistoryPrefix``, a list of
    events or a ``HistoryVerifier`` cannot be passed where state is built."""
    if type(snapshot) is not Snapshot:
        raise TypeError(f"construct_state needs a Snapshot, not {type(snapshot).__name__}")
    return EngineState(t=snapshot.t, elevators=snapshot.elevators, passengers=snapshot.passengers)


def state_hash(state: EngineState) -> str:
    """The canonical hash of an engine state: the value ``snapshot_hash`` is, over the same canonical form."""
    return sha256_hex(canonical_json(state))


# ---------------------------------------------------------------------------
# The isolated history verifier (cpoc §5.2; authority row 38)
# ---------------------------------------------------------------------------

def _history_bad(detail: str) -> CheckpointRefusal:
    return CheckpointRefusal("HISTORY_INCONSISTENT", detail, step=10)


class HistoryVerifier:
    """An isolated replay of ticks ``0..t-1`` that answers one question: is the History internally lawful?
    It starts from the configured initial floors with no passengers, takes the ``ASSIGNED`` events as the
    given assignments (the scheduler's decisions are receipts and are not re-decided), and recomputes
    everything else with the shared Route Policy functions, checking every consequential TickRecord field.
    It is a distinct type with no conversion to a ``Snapshot`` or an ``EngineState``; its result may never
    be used as resumed present state, only compared with the snapshot (step 11); it is then discarded."""

    def __init__(self, configuration: Configuration, trace: Trace) -> None:
        self._cfg = configuration
        self._requests = trace.requests
        self._floor = list(configuration.initial_floors)
        self._heading = [Heading.NONE] * configuration.num_elevators
        self._assigned: dict[int, int] = {}
        self._assigned_tick: dict[int, int] = {}
        self._pickup: dict[int, int] = {}
        self._dropoff: dict[int, int] = {}

    # -- replay --------------------------------------------------------------------------------------

    def replay(self, history: HistoryPrefix, t: int) -> None:
        cfg, requests = self._cfg, self._requests
        n_elev = cfg.num_elevators
        events, records = history.events, history.tick_records
        if [r.tick for r in records] != list(range(t)):
            raise _history_bad(f"tick_records must be exactly ticks 0..{t - 1}")
        for r in records:
            if [en.elevator_id for en in r.entries] != list(range(n_elev)):
                raise _history_bad(f"tick {r.tick} must have exactly the elevators 0..{n_elev - 1}")
        if [e.seq for e in events] != list(range(len(events))):
            raise _history_bad("events must be in sequence from 0 with no gaps")
        by_tick: dict[int, list[SimulationEvent]] = {k: [] for k in range(t)}
        previous = 0
        for e in events:
            if e.kind not in (E.REVEALED, E.ASSIGNED, E.BOARDED, E.ALIGHTED):
                raise _history_bad(f"event {e.seq}: {e.kind.value} is a run-standing event")
            if not (0 <= e.tick < t) or e.tick < previous:
                raise _history_bad(f"event {e.seq}: tick {e.tick} is outside 0..{t - 1} or out of order")
            if e.passenger_id is None or not (0 <= e.passenger_id < len(requests)):
                raise _history_bad(f"event {e.seq}: unknown passenger {e.passenger_id}")
            previous = e.tick
            by_tick[e.tick].append(e)
        revealed: set[int] = set()
        status: dict[int, str] = {}
        for k in range(t):
            self._reveal_and_assign(k, by_tick[k], revealed, status, {p.passenger_id for p in requests
                                                                       if p.request_time == k})
            for el in range(n_elev):
                self._tick_elevator(k, el, records[k].entries[el], by_tick[k], status)
            for el in range(n_elev):
                self._floor[el] += records[k].entries[el].heading.delta
                self._heading[el] = records[k].entries[el].heading
                if not (0 <= self._floor[el] < cfg.num_floors):
                    raise _history_bad(f"tick {k}: elevator {el} would leave the building")

    def _reveal_and_assign(self, k: int, events: list[SimulationEvent], revealed: set[int],
                           status: dict[int, str], due: set[int]) -> None:
        revealed_now: set[int] = set()
        assigned_now: set[int] = set()
        for e in events:
            pid = e.passenger_id
            if e.kind is E.REVEALED:
                if pid in revealed or self._requests[pid].request_time != k:
                    raise _history_bad(f"event {e.seq}: REVEALED twice, or not at the passenger's request_time")
                revealed.add(pid)
                revealed_now.add(pid)
            elif e.kind is E.ASSIGNED:
                if pid not in revealed_now or pid in self._assigned:
                    raise _history_bad(f"event {e.seq}: ASSIGNED without exactly one preceding REVEALED, or twice")
                if e.elevator_id is None or not (0 <= e.elevator_id < self._cfg.num_elevators):
                    raise _history_bad(f"event {e.seq}: ASSIGNED to an elevator that does not exist")
                self._assigned[pid] = e.elevator_id
                self._assigned_tick[pid] = e.tick
                assigned_now.add(pid)
                status[pid] = "W"
        if revealed_now != due or assigned_now != due:
            raise _history_bad(f"tick {k} must reveal and assign exactly the requests due at {k}")

    def _tick_elevator(self, k: int, el: int, rec: TickEntry, events: list[SimulationEvent],
                       status: dict[int, str]) -> None:
        cfg, req = self._cfg, self._requests
        floor = self._floor[el]
        if rec.floor != floor:
            raise _history_bad(f"tick {k}, elevator {el}: recorded floor {rec.floor}, replay {floor}")
        mine = [pid for pid, e in self._assigned.items() if e == el]
        # alight
        onboard = sorted(p for p in mine if status.get(p) == "B")
        alighting = [p for p in onboard if req[p].destination == floor]
        ev_alight = [e.passenger_id for e in events if e.kind is E.ALIGHTED and e.elevator_id == el]
        if list(rec.alighted) != alighting or ev_alight != alighting:
            raise _history_bad(f"tick {k}, elevator {el}: alighted {list(rec.alighted)} / events {ev_alight}, "
                               f"replay {alighting}")
        for e in events:
            if e.kind is E.ALIGHTED and e.elevator_id == el and e.floor != floor:
                raise _history_bad(f"event {e.seq}: ALIGHTED at floor {e.floor}, the car is at {floor}")
        for p in alighting:
            status[p] = "C"
            self._dropoff[p] = k
            if self._dropoff[p] - self._pickup[p] != abs(req[p].destination - req[p].origin):
                raise _history_bad(f"passenger {p}: travel does not equal its distance")
        # board
        onboard = [p for p in onboard if p not in alighting]
        waiting = sorted(p for p in mine if status.get(p) == "W")
        stops = {req[p].origin for p in waiting} | {req[p].destination for p in onboard}
        departure = route.departure_direction(floor, self._heading[el], stops)
        here = [route.WaitingPassenger(p, req[p].origin, req[p].destination) for p in waiting
                if req[p].origin == floor]
        result = route.eligible_boarders(here, departure, len(onboard), cfg.capacity)
        boarders = [p.passenger_id for p in result.boarders]
        ev_board = [e.passenger_id for e in events if e.kind is E.BOARDED and e.elevator_id == el]
        if list(rec.boarded) != boarders or ev_board != boarders:
            raise _history_bad(f"tick {k}, elevator {el}: boarded {list(rec.boarded)} / events {ev_board}, "
                               f"replay {boarders}")
        for e in events:
            if e.kind is E.BOARDED and e.elevator_id == el and e.floor != floor:
                raise _history_bad(f"event {e.seq}: BOARDED at floor {e.floor}, the car is at {floor}")
        for p in boarders:
            direction = Heading.UP if req[p].destination > req[p].origin else Heading.DOWN
            if direction is not rec.heading:
                raise _history_bad(f"passenger {p} boarded going {direction.value} under recorded heading "
                                   f"{rec.heading.value} at tick {k}")
            status[p] = "B"
            self._pickup[p] = k
        onboard = onboard + boarders
        # heading and load
        waiting_after = [p for p in waiting if p not in boarders]
        stops_after = {req[p].origin for p in waiting_after} | {req[p].destination for p in onboard}
        if result.departure is route.Departure.FREE:
            expected = route.next_heading(floor, self._heading[el], stops_after)
        else:
            expected = result.departure.as_heading
        if rec.heading is not expected:
            raise _history_bad(f"tick {k}, elevator {el}: recorded heading {rec.heading.value}, replay {expected.value}")
        if rec.load != len(onboard) or rec.load > cfg.capacity:
            raise _history_bad(f"tick {k}, elevator {el}: recorded load {rec.load}, replay {len(onboard)} "
                               f"(capacity {cfg.capacity})")

    # -- comparison with the snapshot (step 11): the verifier's end state is a *check*, never a source --

    def end_floors(self) -> list[int]:
        return list(self._floor)

    def end_onboard(self, elevator: int) -> set[int]:
        return {p for p, e in self._assigned.items() if e == elevator and p in self._pickup and p not in self._dropoff}

    def passenger_facts(self, passenger_id: int) -> tuple[int | None, int | None, int | None, int | None]:
        """``(assigned_elevator, assigned_at, pickup, dropoff)`` as the replay saw them (for comparison)."""
        return (self._assigned.get(passenger_id), self._assigned_tick.get(passenger_id),
                self._pickup.get(passenger_id), self._dropoff.get(passenger_id))


# ---------------------------------------------------------------------------
# Load verifications 3 to 11 (cpoc §5); each refuses with its named reason and step
# ---------------------------------------------------------------------------

def _state_bad(detail: str) -> CheckpointRefusal:
    return CheckpointRefusal("STATE_INCONSISTENT", detail, step=9)


def _check_snapshot(snap: Mapping[str, Any], configuration: Configuration, trace: Trace) -> None:
    """Verification 9, in the stated order."""
    cfg, req = configuration, trace.requests
    t = snap["t"]
    body = {k: v for k, v in snap.items() if k != "snapshot_hash"}
    if t < 0 or snap["snapshot_hash"] != sha256_hex(canonical_json(body)):
        raise _state_bad("t is negative or snapshot_hash does not match the snapshot section")
    elevators = snap["elevators"]
    if [e["id"] for e in elevators] != list(range(cfg.num_elevators)):
        raise _state_bad(f"elevators must be exactly the ids 0..{cfg.num_elevators - 1}, each once, ascending")
    if any(not (0 <= e["floor"] < cfg.num_floors) for e in elevators):
        raise _state_bad("an elevator floor is outside 0..F-1")
    passengers = snap["passengers"]
    due = [p.passenger_id for p in req if p.request_time < t]
    if [p["passenger_id"] for p in passengers] != due:
        raise _state_bad("passengers must be exactly the revealed set {p : request_time < t}, ascending")
    load = [0] * cfg.num_elevators
    for p in passengers:
        r = req[p["passenger_id"]]
        if p["source_id"] != r.source_id:
            raise _state_bad(f"passenger {p['passenger_id']}: source_id differs from the Trace")
        if not (0 <= p["assigned_elevator"] < cfg.num_elevators) or p["assigned_at"] != r.request_time:
            raise _state_bad(f"passenger {p['passenger_id']}: invalid assignment")
        pick, drop, stand = p["pickup_time"], p["dropoff_time"], p["standing"]
        ok = ((stand == "WAITING" and pick is None and drop is None)
              or (stand == "ONBOARD" and pick is not None and drop is None)
              or (stand == "COMPLETED" and pick is not None and drop is not None))
        if not ok:
            raise _state_bad(f"passenger {p['passenger_id']}: standing {stand} disagrees with its pickup and dropoff")
        if pick is not None and (pick < r.request_time or pick >= t):
            raise _state_bad(f"passenger {p['passenger_id']}: pickup_time out of order or not before t")
        if drop is not None and (drop <= pick or drop >= t or drop - pick != abs(r.destination - r.origin)):
            raise _state_bad(f"passenger {p['passenger_id']}: dropoff_time impossible")
        if stand == "ONBOARD":
            load[p["assigned_elevator"]] += 1
    if any(x > cfg.capacity for x in load):
        raise _state_bad("an elevator carries more than its capacity")


def _check_history(configuration: Configuration, trace: Trace, history: HistoryPrefix, t: int) -> HistoryVerifier:
    """Verification 10: the history hash, then the isolated verifier's replay. Returns the verifier so that
    step 11 can compare it; the caller discards it."""
    if SimulationHistory(history.events, history.tick_records).history_hash != history.history_hash:
        raise _history_bad("history_hash does not match the history section")
    verifier = HistoryVerifier(configuration, trace)
    verifier.replay(history, t)
    return verifier


def _check_snapshot_against_history(snap: Mapping[str, Any], configuration: Configuration, trace: Trace,
                                    history: HistoryPrefix, verifier: HistoryVerifier) -> None:
    """Verification 11 (``STATE_HISTORY_MISMATCH``)."""
    def bad(detail: str) -> CheckpointRefusal:
        return CheckpointRefusal("STATE_HISTORY_MISMATCH", detail, step=11)

    t = snap["t"]
    elevators = snap["elevators"]
    if t == 0:
        if history.tick_records or history.events:
            raise bad("t = 0 but the History is not empty")
        if any(e["floor"] != f or e["heading"] != "NONE" for e, f in zip(elevators, configuration.initial_floors)):
            raise bad("t = 0 but a floor is not its initial floor or a heading is not NONE")
    else:
        last = history.tick_records[t - 1]
        for e, rec in zip(elevators, last.entries):
            if e["floor"] != rec.floor + rec.heading.delta or e["heading"] != rec.heading.value:
                raise bad(f"elevator {e['id']}: snapshot floor/heading differ from tick_records[{t - 1}]")
    by_pid: dict[int, dict[str, list[SimulationEvent]]] = {}
    snapshot_ids = {p["passenger_id"] for p in snap["passengers"]}
    for ev in history.events:
        if ev.passenger_id not in snapshot_ids:
            raise bad(f"event {ev.seq} refers to passenger {ev.passenger_id}, absent from the snapshot")
        by_pid.setdefault(ev.passenger_id, {}).setdefault(ev.kind.value, []).append(ev)
    for p in snap["passengers"]:
        pid, evs = p["passenger_id"], by_pid.get(p["passenger_id"], {})
        for kind, set_value, tick in (("ASSIGNED", p["assigned_elevator"] is not None, p["assigned_at"]),
                                      ("BOARDED", p["pickup_time"] is not None, p["pickup_time"]),
                                      ("ALIGHTED", p["dropoff_time"] is not None, p["dropoff_time"])):
            found = evs.get(kind, [])
            if bool(found) != set_value or len(found) > 1:
                raise bad(f"passenger {pid}: {kind} event presence disagrees with its fields")
            if found and (found[0].tick != tick or found[0].elevator_id != p["assigned_elevator"]):
                raise bad(f"passenger {pid}: {kind} event tick or elevator disagrees with its fields")
        want = "COMPLETED" if "ALIGHTED" in evs else "ONBOARD" if "BOARDED" in evs else "WAITING"
        if p["standing"] != want:
            raise bad(f"passenger {pid}: standing {p['standing']} disagrees with its events ({want})")
    if verifier.end_floors() != [e["floor"] for e in elevators]:
        raise bad("the verifier's final floors differ from the snapshot")
    for e in elevators:
        snap_onboard = {p["passenger_id"] for p in snap["passengers"]
                        if p["standing"] == "ONBOARD" and p["assigned_elevator"] == e["id"]}
        if verifier.end_onboard(e["id"]) != snap_onboard:
            raise bad(f"elevator {e['id']}: the verifier's onboard set differs from the snapshot")


@dataclass(frozen=True)
class LoadedExecution:
    """What a successful ``load`` hands back: the verified identity and inputs, the constructed engine
    state, the History prefix as evidence, and the receipt values. No ``HistoryVerifier`` survives."""

    store: str
    execution_id: str
    store_id: str
    configuration: Configuration
    trace: Trace
    identity: RunIdentity
    write_sequence: int
    state: EngineState
    history: SimulationHistory
    document_sha256: str
    snapshot_hash: str
    history_hash: str
    constructed_state_hash: str
    established: Any


def load(store: str, execution_id: str) -> LoadedExecution:
    """``load(store, execution_id)``: the ordered verifications of cpoc §5, each refusing on the first failure
    with its named reason and no override; nothing is partially loaded. It reads the document at
    ``<store>/<execution_id>/run.json`` and nothing else: never the Operational Log, an output directory, a
    file path, another Execution or different code. It starts by confirming the supported execution contract
    (``UNSUPPORTED_EXECUTION_ENVIRONMENT`` before any load) and computing the running code identity."""
    established = establish_code_identity()
    store_id = read_store(store)                                                         # 1
    path = document_path(store, execution_id)
    if not os.path.isfile(path):
        raise CheckpointRefusal("EXECUTION_NOT_FOUND", f"{path} does not exist", step=2)
    with open(path, "rb") as fh:
        raw = fh.read()
    doc = parse_document_bytes(raw)                                                      # 2
    if doc["schema_version"] != CONTINUATION_SCHEMA_VERSION:                             # 3
        raise CheckpointRefusal("SCHEMA_MISMATCH", f"document schema {doc['schema_version']}, this code reads "
                                f"{CONTINUATION_SCHEMA_VERSION}", step=3)
    if doc["code_identity"] != established.identity:                                     # 4
        raise CheckpointRefusal("CODE_IDENTITY_MISMATCH", "the document was written by different governed code",
                                step=4)
    if doc["store_id"] != store_id:                                                      # 5
        raise CheckpointRefusal("STORE_MISMATCH", "the document belongs to another Store", step=5)
    if doc["execution_id"] != execution_id:
        raise CheckpointRefusal("EXECUTION_MISMATCH", "the document belongs to another Execution", step=5)
    config_hash = sha256_hex(canonical_json(doc["configuration"]))                       # 6
    if config_hash != doc["configuration_hash"]:
        raise CheckpointRefusal("CONFIG_HASH_MISMATCH", "configuration_hash does not match the Configuration", step=6)
    trace_hash = sha256_hex(canonical_json(doc["trace"]))
    if trace_hash != doc["trace_hash"]:
        raise CheckpointRefusal("TRACE_HASH_MISMATCH", "trace_hash does not match the Trace", step=6)
    if sha256_hex(canonical_json([config_hash, trace_hash, doc["code_identity"]])) != doc["run_id"]:
        raise CheckpointRefusal("RUN_ID_MISMATCH", "run_id does not match its Configuration, Trace and code", step=6)
    if doc["standing"] != RUNNING:                                                       # 7
        raise CheckpointRefusal("EXECUTION_FINAL", f"the Execution is {doc['standing']} and is never resumed", step=7)
    if "snapshot" not in doc or doc["final"] is not None:
        raise CheckpointRefusal("MALFORMED", "a RUNNING document needs a snapshot and a null final", step=7)
    try:                                                                                 # 8
        c = doc["configuration"]
        configuration = Configuration.create(c["num_floors"], c["num_elevators"], c["capacity"],
                                             initial_floors=c["initial_floors"], max_ticks=c["max_ticks"],
                                             policy=c["policy"], policy_params=c["policy_params"])
        trace = normalize_requests(doc["trace"], configuration.num_floors)
        identity = bind_run(configuration, trace, doc["code_identity"])
    except Refusal as exc:
        raise CheckpointRefusal("INPUT_INVALID", f"the embedded inputs fail Trace-load validation: {exc}", step=8) from exc
    if json.loads(canonical_json(configuration)) != doc["configuration"] or trace.canonical_rows() != doc["trace"]:
        raise CheckpointRefusal("INPUT_INVALID", "the embedded inputs are not in canonical form", step=8)
    _check_snapshot(doc["snapshot"], configuration, trace)                               # 9
    history = parse_history(doc)
    verifier = _check_history(configuration, trace, history, doc["snapshot"]["t"])       # 10
    _check_snapshot_against_history(doc["snapshot"], configuration, trace, history, verifier)  # 11
    del verifier  # discarded before any state is constructed: no reference survives the load
    snapshot = parse_snapshot(doc)
    state = construct_state(snapshot)
    return LoadedExecution(
        store=store, execution_id=execution_id, store_id=store_id, configuration=configuration, trace=trace,
        identity=identity, write_sequence=doc["write_sequence"], state=state,
        history=SimulationHistory(history.events, history.tick_records),
        document_sha256=sha256_hex(raw), snapshot_hash=snapshot.snapshot_hash, history_hash=history.history_hash,
        constructed_state_hash=state_hash(state), established=established)


# ---------------------------------------------------------------------------
# Write admission and the write path (cpoc §3.2, §3.4)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WriteReceipt:
    """What an admitted write produced: the new ``write_sequence`` (the writer's next admission token) and
    the values the Operational Log receipt carries. ``document_sha256`` is the hash of the bytes read back
    from the path after the rename, never of an object held before the write."""

    write_sequence: int
    document_sha256: str
    snapshot_hash: str | None
    history_hash: str
    path: str


def _admit(store: str, execution_id: str, token: int | None) -> int:
    """Write admission, step 1: read the document currently at the path, if any. It must parse, carry this
    ``execution_id``, be ``RUNNING`` and have ``write_sequence`` equal to the writer's last-known value;
    otherwise ``EXECUTION_MISMATCH``, ``WRITE_AFTER_FINAL`` or ``STALE_WRITER``, and nothing is written.
    Returns the ``write_sequence`` the new document will carry. There is no retry and no last-writer-wins."""
    path = document_path(store, execution_id)
    if not os.path.exists(path):
        if token is not None:  # the writer believes a document exists that the path does not hold
            raise CheckpointRefusal("STALE_WRITER", f"the writer holds token {token} but no document is at the path")
        return 1
    try:
        with open(path, "rb") as fh:
            current = json.loads(fh.read(), parse_float=_fail_float, parse_constant=_fail_constant)
        ok = isinstance(current, dict) and isinstance(current.get("execution_id"), str) \
            and isinstance(current.get("standing"), str) and _is_int(current.get("write_sequence"))
    except (ValueError, UnicodeDecodeError, OSError):
        ok = False
    if not ok:
        raise CheckpointRefusal("MALFORMED", "the document at the path does not parse; it is not overwritten")
    if current["execution_id"] != execution_id:
        raise CheckpointRefusal("EXECUTION_MISMATCH", "the document at the path belongs to another Execution")
    if current["standing"] != RUNNING:
        raise CheckpointRefusal("WRITE_AFTER_FINAL", f"the Execution is {current['standing']}: no write is admitted")
    if current["write_sequence"] != token:
        raise CheckpointRefusal("STALE_WRITER", f"the document is at write_sequence {current['write_sequence']}, "
                                f"the writer holds {token}")
    return token + 1


def _document_bytes(store_id: str, execution: Execution, identity: RunIdentity, configuration: Configuration,
                    trace: Trace, engine: Engine, write_sequence: int, *, final: bool) -> tuple[bytes, str | None, str]:
    history = engine.history
    doc: dict[str, Any] = {
        "schema_version": CONTINUATION_SCHEMA_VERSION, "store_id": store_id, "execution_id": execution.execution_id,
        "run_id": identity.run_id, "code_identity": identity.code_identity,
        "configuration_hash": identity.configuration_hash, "trace_hash": identity.trace_hash,
        "write_sequence": write_sequence, "configuration": json.loads(canonical_json(configuration)),
        "trace": trace.canonical_rows(), "standing": RUNNING, "final": None,
        "simulation_history": {**json.loads(canonical_json({"events": history.events,
                                                            "tick_records": history.tick_records})),
                               "history_hash": history.history_hash}}
    snapshot_hash: str | None = None
    if final:
        outcome = engine.outcome
        doc["standing"] = outcome.standing
        doc["final"] = {"final_tick": outcome.final_tick}
        if outcome.standing == HALTED:
            doc["final"].update({"halt_step": outcome.halt_step, "halt_reason": outcome.halt_reason,
                                 "halt_passenger": outcome.halt_passenger})
    else:
        state = engine.state
        snapshot_hash = state_hash(state)
        doc["snapshot"] = {**json.loads(canonical_json(state)), "snapshot_hash": snapshot_hash}
    return canonical_json(doc), snapshot_hash, history.history_hash


def _write(store: str, execution: Execution, identity: RunIdentity, configuration: Configuration, trace: Trace,
           engine: Engine, token: int | None, *, final: bool) -> WriteReceipt:
    store_id = read_store(store)
    directory = execution_dir(store, execution.execution_id)
    next_sequence = _admit(store, execution.execution_id, token)                        # 1: admission
    payload, snapshot_hash, history_hash = _document_bytes(store_id, execution, identity, configuration, trace,
                                                           engine, next_sequence, final=final)
    os.makedirs(directory, exist_ok=True)
    temp = os.path.join(directory, TEMP_FILE)                                           # 2: tmp, fsync, rename
    with open(temp, "wb") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(temp, document_path(store, execution.execution_id))
    with open(document_path(store, execution.execution_id), "rb") as fh:               # 3: hash the bytes at the path
        digest = sha256_hex(fh.read())
    log = execution.log                                                                 # 4: receipt, then flush
    if not log.bound:
        log.bind_evidence_root(directory)  # first binding: the whole buffer is flushed once, in order
    elif log.evidence_root != directory:
        raise CheckpointRefusal("MALFORMED", "the Execution's log is bound to a location that is not its Store directory")
    log.append(K.FINALITY_WRITTEN if final else K.CHECKPOINT_WRITTEN,
               tick=engine.outcome.final_tick if final else engine.t,
               payload={"write_sequence": next_sequence, "document_sha256": digest,
                        "snapshot_hash": snapshot_hash, "history_hash": history_hash})
    return WriteReceipt(next_sequence, digest, snapshot_hash, history_hash, document_path(store, execution.execution_id))


def write_checkpoint(store: str, execution: Execution, identity: RunIdentity, configuration: Configuration,
                     trace: Trace, engine: Engine, *, token: int | None) -> WriteReceipt:
    """An admitted checkpoint write at the engine's current tick boundary. ``token`` is the writer's
    last-known ``write_sequence`` (``None`` before its first write)."""
    if engine.outcome is not None:
        raise ValueError("the engine is final: use write_finality")
    return _write(store, execution, identity, configuration, trace, engine, token, final=False)


def write_finality(store: str, execution: Execution, identity: RunIdentity, configuration: Configuration,
                   trace: Trace, engine: Engine, *, token: int | None) -> WriteReceipt:
    """The admitted finality write: standing final, ``final`` filled, snapshot removed, the complete
    Simulation History, ``write_sequence + 1``, then the ``FINALITY_WRITTEN`` receipt."""
    if engine.outcome is None:
        raise ValueError("the engine has no Run outcome yet")
    return _write(store, execution, identity, configuration, trace, engine, token, final=True)


class CheckpointWriter:
    """One Execution's durable writer: it holds the writer's admission token (its last-known
    ``write_sequence``) and, after any refusal, halts itself, so that no later write can succeed or be retried
    around a stale or final standing."""

    def __init__(self, store: str, execution: Execution, identity: RunIdentity, configuration: Configuration,
                 trace: Trace, *, token: int | None = None) -> None:
        read_store(store)
        self._store, self._execution, self._identity = store, execution, identity
        self._configuration, self._trace = configuration, trace
        self._token = token
        self._halted: CheckpointRefusal | None = None

    @property
    def last_known(self) -> int | None:
        return self._token

    @property
    def has_document(self) -> bool:
        return self._token is not None

    @property
    def halted(self) -> CheckpointRefusal | None:
        return self._halted

    def _run(self, write: Callable[..., WriteReceipt], engine: Engine) -> WriteReceipt:
        if self._halted is not None:
            raise self._halted
        try:
            receipt = write(self._store, self._execution, self._identity, self._configuration, self._trace, engine,
                            token=self._token)
        except CheckpointRefusal as refusal:
            self._halted = refusal
            raise
        self._token = receipt.write_sequence
        return receipt

    def checkpoint(self, engine: Engine) -> WriteReceipt:
        return self._run(write_checkpoint, engine)

    def finalize(self, engine: Engine) -> WriteReceipt:
        return self._run(write_finality, engine)


def bind_store(store: str, execution: Execution) -> str:
    """Bind an Execution's log to its Store directory (checkpoint controls set at creation): the buffer is
    flushed once. Returns the evidence root."""
    read_store(store)
    directory = execution_dir(store, execution.execution_id)
    execution.log.bind_evidence_root(directory)
    return directory


# ---------------------------------------------------------------------------
# Resume (cpoc §5, then §2.4) and the checkpoint controls (cpoc §2.3)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ResumedExecution:
    """A resumed Execution: the engine at the checkpointed boundary, the Execution handle continuing the same
    log, the writer holding the loaded ``write_sequence`` as its token, and the verified load."""

    engine: Engine
    execution: Execution
    writer: CheckpointWriter
    loaded: LoadedExecution


def resume(store: str, execution_id: str) -> ResumedExecution:
    """Resume an Execution from its Continuation Document alone: ``load`` (all eleven verifications; a final
    Execution refuses ``EXECUTION_FINAL``), then open the Execution's existing log (same ``execution_id``,
    ``op_seq`` continuing, this process's ``EXECUTION_STARTED``), append ``LOAD_ADMITTED`` and ``RESUMED``,
    rebuild the policy through the one resolver from the Configuration's name and parameters, and restore the
    engine from the constructed state with the History prefix attached as it is. Tick ``t`` is the next to
    execute. Nothing is replayed from tick 0 and nothing is derived from the History."""
    loaded = load(store, execution_id)
    execution = resume_execution(execution_id, loaded.established.identity, execution_dir(store, execution_id))
    t = loaded.state.t
    execution.log.append(K.LOAD_ADMITTED, tick=t, payload={
        "document_sha256": loaded.document_sha256, "snapshot_hash": loaded.snapshot_hash,
        "history_hash": loaded.history_hash, "constructed_state_hash": loaded.constructed_state_hash,
        "store_id": loaded.store_id, "execution_id": execution_id})
    execution.log.append(K.RESUMED, tick=t)
    policy = make_policy(loaded.configuration.policy, loaded.configuration.policy_params)
    engine = Engine.restore(loaded.configuration, loaded.trace, policy, loaded.state, loaded.history)
    writer = CheckpointWriter(store, execution, loaded.identity, loaded.configuration, loaded.trace,
                              token=loaded.write_sequence)
    return ResumedExecution(engine, execution, writer, loaded)


@dataclass(frozen=True)
class Controls:
    """Checkpoint scheduling controls (authority row 27): ephemeral execution parameters that change nothing
    in the Simulation History. ``checkpoint_at`` writes once at that boundary; ``checkpoint_every`` writes at
    every positive multiple of ``k``; ``pause_after_checkpoint`` (witness only) blocks after the first write."""

    checkpoint_at: int | None = None
    checkpoint_every: int | None = None
    pause_after_checkpoint: bool = False

    def wants(self, t: int) -> bool:
        return t == self.checkpoint_at or (self.checkpoint_every is not None and t > 0 and t % self.checkpoint_every == 0)


def instrument(engine: Engine, execution: Execution) -> None:
    """``--witness-instrumentation``: the engine's single emission point appends one ``DIAGNOSTIC`` record
    per emitted TickRecord to the Execution's Operational Log. It changes nothing else."""
    engine.set_diagnostic(lambda record: execution.log.append(K.DIAGNOSTIC, tick=record.tick,
                                                              payload={"tick": record.tick}))


def drive(engine: Engine, writer: CheckpointWriter | None, controls: Controls, *,
          pause: Callable[[], None] | None = None, skip_boundary: int | None = None):
    """Run an engine to its Run outcome one tick at a time, writing a checkpoint at each boundary the controls
    ask for (never by default; the first boundary of a resumed process, ``skip_boundary``, is already durable).
    At the outcome, an Execution that has a document performs the finality write; one that never wrote a
    document writes nothing. Returns the Run outcome."""
    paused = False
    while engine.outcome is None:
        t = engine.t
        if writer is not None and controls.wants(t) and t != skip_boundary:
            writer.checkpoint(engine)
            if controls.pause_after_checkpoint and not paused:
                paused = True
                if pause is not None:
                    pause()
        engine.step()
    if writer is not None and writer.has_document:
        writer.finalize(engine)
    return engine.outcome
