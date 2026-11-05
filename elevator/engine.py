"""The simulation engine (plan cut 3): the only writer of runtime facts.

Realises simulation_semantics §2 (the nine-step tick procedure), §5, §6,
§7, §8.3 and constitution §4.1 to §4.4, §8 to §11. The engine owns current
time, every revealed Passenger's fields, every Elevator's floor and heading,
the Run outcome and the Simulation History (authority rows 8 to 15, 17,
18). Load, onboard and waiting sets, committed stops and routes are derived
on demand and never stored.

Route mechanics are the Route Policy's single implementation: the engine
calls ``route.departure_direction``, ``route.eligible_boarders`` and
``route.next_heading`` by attribute and defines no equivalent of its own.

Tick atomicity (constitution §4.4): each tick works on copies of the
passenger map and elevator tuple and buffers its events; the copies and
buffers replace the engine's state only when the tick completes. A halt
discards the working tick and appends one ``HALTED`` event to the committed
history, so no partial tick ever becomes Simulation History.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Any, Protocol

from elevator import route
from elevator.domain import (
    Configuration,
    Elevator,
    ElevatorView,
    Heading,
    OnboardView,
    Passenger,
    Proposal,
    RevealedRequest,
    SchedulerView,
    SimulationEvent,
    SimulationEventKind,
    SimulationHistory,
    Standing,
    TickEntry,
    TickRecord,
    Trace,
    WaitingView,
    default_max_ticks,
    freeze,
)

COMPLETED = "COMPLETED"
HALTED = "HALTED"
RUNNING = "RUNNING"

INVALID_PROPOSAL = "INVALID_PROPOSAL"
POLICY_ERROR = "POLICY_ERROR"
LIVENESS_BOUND_EXCEEDED = "LIVENESS_BOUND_EXCEEDED"
HORIZON_EXCEEDED = "HORIZON_EXCEEDED"
INVARIANT_VIOLATION = "INVARIANT_VIOLATION"


class SchedulerPolicy(Protocol):
    def assign(self, view: SchedulerView, request: RevealedRequest) -> Proposal: ...


class EngineInvariantViolation(Exception):
    """A write the tick procedure can never lawfully perform (a second
    assignment, pickup or dropoff; a wrong-way boarding; a load above C; a
    floor outside the building). Raised inside a tick and converted by
    ``step`` into an ``INVARIANT_VIOLATION`` halt (simulation_semantics §2,
    owner decision 008): the tick is discarded and the Run is final.
    Unreachable under a correct implementation."""

    def __init__(self, step: str, invariant: str, detail: str, *,
                 passenger: int | None = None, elevator: int | None = None) -> None:
        super().__init__(f"{invariant}: {detail}")
        self.step, self.invariant, self.detail = step, invariant, detail
        self.passenger, self.elevator = passenger, elevator


@dataclass(frozen=True)
class ElevatorState:
    """One elevator's authoritative state at a tick boundary: exactly two fields (constitution §4.2)."""

    id: int
    floor: int
    heading: Heading


@dataclass(frozen=True)
class PassengerState:
    """One revealed Passenger's authoritative lifecycle fields at a tick boundary. The fields the Trace
    already owns (request time, origin, destination) are not repeated: they are joined from the Trace."""

    passenger_id: int
    source_id: str
    standing: Standing
    assigned_elevator: int
    assigned_at: int
    pickup_time: int | None
    dropoff_time: int | None


@dataclass(frozen=True)
class EngineState:
    """The engine's authoritative runtime state at a tick boundary: the tick about to execute, every
    elevator, and exactly the revealed passengers. Its canonical form is the snapshot section of a
    Continuation Document. Load, onboard and waiting sets, committed stops and routes are derived and
    never part of it."""

    t: int
    elevators: tuple[ElevatorState, ...]
    passengers: tuple[PassengerState, ...]


@dataclass(frozen=True)
class RunOutcome:
    standing: str                    # COMPLETED or HALTED
    final_tick: int
    halt_step: str | None = None
    halt_reason: str | None = None
    halt_passenger: int | None = None
    unserved: int = 0


class _Halt(Exception):
    def __init__(self, step: str, reason: str, passenger: int | None,
                 diagnostic: Mapping[str, Any] | None = None) -> None:
        super().__init__(reason)
        self.step, self.reason, self.passenger = step, reason, passenger
        self.diagnostic = diagnostic


def _direction(p: Passenger) -> Heading:
    return Heading.UP if p.destination > p.origin else Heading.DOWN


class Engine:
    """One Simulation, stepped one tick at a time.

    Read-only views of state are exposed as properties returning immutable
    values; there is no API that writes a Passenger, an Elevator, a load or
    the History from outside the tick procedure."""

    def __init__(self, configuration: Configuration, trace: Trace, policy: SchedulerPolicy) -> None:
        self._config = configuration
        self._trace = trace
        self._policy = policy
        self._max_ticks = configuration.validate_with_trace(trace)
        self._default_bound = default_max_ticks(configuration.num_floors, trace)
        self._t = 0
        self._passengers: dict[int, Passenger] = {}
        self._elevators: tuple[Elevator, ...] = tuple(
            Elevator(elevator_id=i, floor=f, heading=Heading.NONE)
            for i, f in enumerate(configuration.initial_floors))
        self._events: tuple[SimulationEvent, ...] = ()
        self._tick_records: tuple[TickRecord, ...] = ()
        self._outcome: RunOutcome | None = None
        self._diagnostic: Callable[[TickRecord], None] | None = None
        # Requests indexed by request time, read only by step 1 (reveal).
        self._by_time: dict[int, tuple[int, ...]] = {}
        for r in trace.requests:
            self._by_time.setdefault(r.request_time, ())
            self._by_time[r.request_time] += (r.passenger_id,)

    # -- read-only projections of engine-owned state ------------------------

    @classmethod
    def create(cls, configuration: Configuration, trace: Trace, policy: SchedulerPolicy) -> "Engine":
        """``engine.create``: a RUNNING engine at the boundary before tick 0."""
        return cls(configuration, trace, policy)

    @property
    def t(self) -> int:
        return self._t

    @property
    def standing(self) -> str:
        return RUNNING if self._outcome is None else self._outcome.standing

    @property
    def outcome(self) -> RunOutcome | None:
        return self._outcome

    @property
    def max_ticks(self) -> int:
        return self._max_ticks

    @property
    def passengers(self) -> tuple[Passenger, ...]:
        return tuple(self._passengers[pid] for pid in sorted(self._passengers))

    @property
    def elevators(self) -> tuple[Elevator, ...]:
        return self._elevators

    @property
    def history(self) -> SimulationHistory:
        return SimulationHistory(events=self._events, tick_records=self._tick_records)

    @property
    def state(self) -> EngineState:
        """The engine's authoritative state at this tick boundary, as a value (read-only)."""
        return EngineState(
            t=self._t,
            elevators=tuple(ElevatorState(e.elevator_id, e.floor, e.heading) for e in self._elevators),
            passengers=tuple(PassengerState(p.passenger_id, p.source_id, p.standing, p.assigned_elevator,
                                            p.assigned_at, p.pickup_time, p.dropoff_time)
                             for p in self.passengers))

    @classmethod
    def restore(cls, configuration: Configuration, trace: Trace, policy: SchedulerPolicy, state: EngineState,
                history: SimulationHistory) -> "Engine":
        """The engine as it stood at the boundary ``state.t``: the only way a resumed state enters the
        engine. ``state`` is an ``EngineState`` (built by the checkpoint loader from a Snapshot alone) and
        ``history`` is the prefix attached without transformation. Nothing is replayed from tick 0 and no
        state is derived from the History. The Run is ``RUNNING`` and the next tick executed is ``state.t``."""
        if not isinstance(state, EngineState):
            raise TypeError("Engine.restore needs an EngineState")
        if state.t < 0 or [e.id for e in state.elevators] != list(range(configuration.num_elevators)):
            raise ValueError("the state does not match the Configuration's elevators")
        engine = cls(configuration, trace, policy)
        engine._t = state.t
        engine._elevators = tuple(Elevator(elevator_id=e.id, floor=e.floor, heading=e.heading)
                                  for e in state.elevators)
        passengers: dict[int, Passenger] = {}
        for ps in state.passengers:
            r = trace.requests[ps.passenger_id]
            passengers[ps.passenger_id] = Passenger(
                passenger_id=ps.passenger_id, source_id=ps.source_id, request_time=r.request_time,
                origin=r.origin, destination=r.destination, standing=ps.standing,
                assigned_elevator=ps.assigned_elevator, assigned_at=ps.assigned_at,
                pickup_time=ps.pickup_time, dropoff_time=ps.dropoff_time)
        engine._passengers = passengers
        engine._events = history.events
        engine._tick_records = history.tick_records
        return engine

    def set_diagnostic(self, hook: Callable[[TickRecord], None] | None) -> None:
        """Install (or clear) the optional diagnostic hook: called with each emitted TickRecord once its
        tick is fully committed. It is outside simulation state, the SchedulerView and snapshots, and
        changes nothing else (cpoc §2.3 ``--witness-instrumentation``)."""
        self._diagnostic = hook

    def _emit(self, record: TickRecord) -> None:
        """The engine's single emission point for a committed TickRecord."""
        if self._diagnostic is not None:
            self._diagnostic(record)

    def load(self, elevator_id: int) -> int:
        return sum(1 for p in self._passengers.values()
                   if p.standing is Standing.ONBOARD and p.assigned_elevator == elevator_id)

    # -- the tick procedure -------------------------------------------------

    def run(self) -> RunOutcome:
        while self._outcome is None:
            self.step()
        return self._outcome

    def step(self) -> RunOutcome | None:
        """Execute exactly one tick (simulation_semantics §2). On a final Run
        this is a no-op returning the outcome."""
        if self._outcome is not None:
            return self._outcome
        t = self._t
        passengers = dict(self._passengers)
        elevators = list(self._elevators)
        events: list[tuple[Any, ...]] = []
        try:
            record = self._tick(t, passengers, elevators, events)
        except _Halt as halt:
            self._commit_halt(t, halt)
            return self._outcome
        except EngineInvariantViolation as violation:
            self._commit_halt(t, self._invariant_halt(violation))
            return self._outcome
        # step 7: terminate?
        all_revealed = not any(time > t for time in self._by_time)
        all_completed = all(p.standing is Standing.COMPLETED for p in passengers.values())
        if all_revealed and all_completed and len(passengers) == self._trace.num_requests:
            events.append((SimulationEventKind.COMPLETED, {}))
            self._commit(passengers, tuple(elevators), events, record, t)
            self._outcome = RunOutcome(standing=COMPLETED, final_tick=t)
            self._emit(record)
            return self._outcome
        if t + 1 > self._max_ticks:
            reason = LIVENESS_BOUND_EXCEEDED if self._max_ticks == self._default_bound else HORIZON_EXCEEDED
            # The halt occurs in tick t: its records are discarded with it.
            self._commit_halt(t, _Halt("TERMINATE", reason, None))
            return self._outcome
        # step 8: move
        moved = tuple(replace(e, floor=e.floor + e.heading.delta) for e in elevators)
        for e in moved:
            if not (0 <= e.floor < self._config.num_floors):
                # The tick is discarded before anything is committed.
                self._commit_halt(t, self._invariant_halt(EngineInvariantViolation(
                    "MOVE", "P2", f"elevator {e.elevator_id} would move to floor {e.floor}",
                    elevator=e.elevator_id)))
                return self._outcome
        self._commit(passengers, moved, events, record, t)
        # step 9: advance
        self._t = t + 1
        self._emit(record)
        return None

    def _tick(self, t: int, passengers: dict[int, Passenger], elevators: list[Elevator],
              events: list[tuple[Any, ...]]) -> TickRecord:
        cfg = self._config
        requests = self._trace.requests
        # step 1: reveal
        revealed = list(self._by_time.get(t, ()))
        for pid in revealed:
            events.append((SimulationEventKind.REVEALED, {"passenger_id": pid}))
        # step 2: assign, in passenger_id order, each call seeing earlier commits
        for pid in revealed:
            r = requests[pid]
            view = self._view(t, passengers, elevators)
            request = RevealedRequest(passenger_id=pid, origin=r.origin,
                                      destination=r.destination, request_time=r.request_time)
            try:
                proposal = self._policy.assign(view, request)
            except Exception:
                raise _Halt("ASSIGN", POLICY_ERROR, pid) from None
            if not isinstance(proposal, Proposal) or isinstance(proposal.elevator_id, bool) \
                    or not isinstance(proposal.elevator_id, int) \
                    or not (0 <= proposal.elevator_id < cfg.num_elevators) \
                    or not (proposal.receipt is None or isinstance(proposal.receipt, Mapping)):
                raise _Halt("ASSIGN", INVALID_PROPOSAL, pid)
            try:
                # A receipt that cannot be frozen canonically cannot be
                # committed to History; the proposal is invalid.
                receipt = freeze(proposal.receipt)
            except (TypeError, RecursionError):
                raise _Halt("ASSIGN", INVALID_PROPOSAL, pid) from None
            if pid in passengers:
                raise EngineInvariantViolation("ASSIGN", "N2", f"passenger {pid} assigned twice",
                                               passenger=pid, elevator=proposal.elevator_id)
            passengers[pid] = Passenger(
                passenger_id=pid, source_id=r.source_id, request_time=r.request_time,
                origin=r.origin, destination=r.destination, standing=Standing.WAITING,
                assigned_elevator=proposal.elevator_id, assigned_at=t,
                pickup_time=None, dropoff_time=None)
            events.append((SimulationEventKind.ASSIGNED,
                           {"passenger_id": pid, "elevator_id": proposal.elevator_id, "receipt": receipt}))
        # step 3: alight
        alighted: dict[int, list[int]] = {e.elevator_id: [] for e in elevators}
        for e in elevators:
            for p in self._onboard(passengers, e.elevator_id):
                if p.destination == e.floor:
                    if p.dropoff_time is not None:
                        raise EngineInvariantViolation("ALIGHT", "P6", f"passenger {p.passenger_id} dropped twice",
                                                       passenger=p.passenger_id, elevator=e.elevator_id)
                    passengers[p.passenger_id] = replace(p, standing=Standing.COMPLETED, dropoff_time=t)
                    alighted[e.elevator_id].append(p.passenger_id)
                    events.append((SimulationEventKind.ALIGHTED,
                                   {"passenger_id": p.passenger_id, "elevator_id": e.elevator_id,
                                    "floor": e.floor}))
        # step 4: board (Route Policy primitives)
        boarded: dict[int, list[int]] = {e.elevator_id: [] for e in elevators}
        departures: dict[int, route.Departure] = {}
        for e in elevators:
            stops = self._committed_stops(passengers, e.elevator_id)
            departure = route.departure_direction(e.floor, e.heading, stops)
            at_floor = [p for p in self._waiting(passengers, e.elevator_id) if p.origin == e.floor]
            load = len(self._onboard(passengers, e.elevator_id))
            result = route.eligible_boarders(at_floor, departure, load, cfg.capacity)
            for p in result.boarders:
                if p.pickup_time is not None or p.standing is not Standing.WAITING:
                    raise EngineInvariantViolation("BOARD", "P6", f"passenger {p.passenger_id} picked up twice",
                                                   passenger=p.passenger_id, elevator=e.elevator_id)
                if _direction(p).value != result.departure.value:
                    raise EngineInvariantViolation("BOARD", "N7", f"passenger {p.passenger_id} boarding the wrong way",
                                                   passenger=p.passenger_id, elevator=e.elevator_id)
                passengers[p.passenger_id] = replace(p, standing=Standing.ONBOARD, pickup_time=t)
                boarded[e.elevator_id].append(p.passenger_id)
                events.append((SimulationEventKind.BOARDED,
                               {"passenger_id": p.passenger_id, "elevator_id": e.elevator_id,
                                "floor": e.floor}))
            if len(self._onboard(passengers, e.elevator_id)) > cfg.capacity:
                raise EngineInvariantViolation(
                    "BOARD", "P3", f"elevator {e.elevator_id} load {len(self._onboard(passengers, e.elevator_id))} "
                    f"exceeds capacity {cfg.capacity}", elevator=e.elevator_id)
            departures[e.elevator_id] = result.departure  # ephemeral: this tick only
        # step 5: head
        for i, e in enumerate(elevators):
            d = departures[e.elevator_id]
            if d is route.Departure.FREE:
                heading = route.next_heading(e.floor, e.heading,
                                             self._committed_stops(passengers, e.elevator_id))
            else:
                heading = d.as_heading
            elevators[i] = replace(e, heading=heading)
        # step 6: record
        return TickRecord(tick=t, entries=tuple(
            TickEntry(elevator_id=e.elevator_id, floor=e.floor, heading=e.heading,
                      load=len(self._onboard(passengers, e.elevator_id)),
                      boarded=tuple(boarded[e.elevator_id]), alighted=tuple(alighted[e.elevator_id]))
            for e in elevators))

    # -- derived values (never stored) ---------------------------------------

    @staticmethod
    def _onboard(passengers: Mapping[int, Passenger], elevator_id: int) -> list[Passenger]:
        return [passengers[pid] for pid in sorted(passengers)
                if passengers[pid].standing is Standing.ONBOARD
                and passengers[pid].assigned_elevator == elevator_id]

    @staticmethod
    def _waiting(passengers: Mapping[int, Passenger], elevator_id: int) -> list[Passenger]:
        return [passengers[pid] for pid in sorted(passengers)
                if passengers[pid].standing is Standing.WAITING
                and passengers[pid].assigned_elevator == elevator_id]

    def _committed_stops(self, passengers: Mapping[int, Passenger], elevator_id: int) -> list[int]:
        return sorted({p.origin for p in self._waiting(passengers, elevator_id)}
                      | {p.destination for p in self._onboard(passengers, elevator_id)})

    def _view(self, t: int, passengers: Mapping[int, Passenger],
              elevators: list[Elevator]) -> SchedulerView:
        return SchedulerView(
            t=t, floors=self._config.num_floors, num_elevators=self._config.num_elevators,
            capacity=self._config.capacity,
            elevators=tuple(
                ElevatorView(
                    id=e.elevator_id, floor=e.floor, heading=e.heading,
                    onboard=tuple(OnboardView(p.passenger_id, p.destination, p.pickup_time)
                                  for p in self._onboard(passengers, e.elevator_id)),
                    waiting=tuple(WaitingView(p.passenger_id, p.origin, p.destination, p.request_time)
                                  for p in self._waiting(passengers, e.elevator_id)))
                for e in elevators))

    # -- commits ----------------------------------------------------------------

    def _numbered(self, events: list[tuple[Any, ...]], t: int) -> tuple[SimulationEvent, ...]:
        base = len(self._events)
        return tuple(SimulationEvent(seq=base + i, kind=kind, tick=t, **fields)
                     for i, (kind, fields) in enumerate(events))

    def _commit(self, passengers: dict[int, Passenger], elevators: tuple[Elevator, ...],
                events: list[tuple[Any, ...]], record: TickRecord, t: int) -> None:
        self._events = self._events + self._numbered(events, t)
        self._tick_records = self._tick_records + (record,)
        self._passengers = passengers
        self._elevators = elevators

    @staticmethod
    def _invariant_halt(violation: EngineInvariantViolation) -> _Halt:
        return _Halt(violation.step, INVARIANT_VIOLATION, violation.passenger,
                     {"elevator": violation.elevator, "invariant": violation.invariant,
                      "detail": violation.detail})

    def _commit_halt(self, t: int, halt: _Halt) -> None:
        """Commit exactly one HALTED event against the committed state; the
        failing tick's working copies are simply dropped."""
        completed = sum(1 for p in self._passengers.values() if p.standing is Standing.COMPLETED)
        unserved = self._trace.num_requests - completed
        payload = {"step": halt.step, "reason": halt.reason, "passenger": halt.passenger,
                   "unserved": unserved}
        if halt.diagnostic is not None:
            payload.update(halt.diagnostic)
        self._events = self._events + (SimulationEvent(seq=len(self._events), kind=SimulationEventKind.HALTED,
                                                       tick=t, passenger_id=halt.passenger, halt=payload),)
        self._outcome = RunOutcome(standing=HALTED, final_tick=t, halt_step=halt.step,
                                   halt_reason=halt.reason, halt_passenger=halt.passenger,
                                   unserved=unserved)
