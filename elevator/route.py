"""The Route Policy: pure, stateless elevator mechanics (plan cut 2).

This module is the single implementation of the three primitives the
engine's steps 4 and 5 call and the projection iterates
(simulation_semantics §4, §4.1, §4.2, §4.3; scheduler_design §5):

- ``next_heading(floor, heading, stops)``: LOOK;
- ``departure_direction(floor, heading, stops)``: the intra-tick departure
  decision, ``UP``, ``DOWN`` or ``FREE``;
- ``eligible_boarders(waiting, departure, load, capacity)``: direction-first
  boarding with the single deferral classification;
- ``project(elevator_view, extra_waiting, capacity, now)``: those three,
  iterated over one elevator's future until it is idle.

Nothing here owns state. Inputs are values; outputs are values. The engine
(cut 3) applies results to authoritative state; this module never mutates a
Passenger or an Elevator, never reads a Trace, History or clock, and
performs no I/O. ``FREE`` is a departure value, never a stored heading.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from elevator.domain import Heading


class Departure(Enum):
    """The departure direction established at a stop (semantics §4.1).
    ``FREE`` means not yet committed to leave the floor either way; it is
    intra-tick and ephemeral (authority row 16), never a heading."""

    UP = "UP"
    DOWN = "DOWN"
    FREE = "FREE"

    @property
    def as_heading(self) -> Heading:
        if self is Departure.UP:
            return Heading.UP
        if self is Departure.DOWN:
            return Heading.DOWN
        raise ValueError("FREE is not a heading")


def _direction_of(passenger: Any) -> Departure:
    """``dir(p)``: UP if destination > origin else DOWN (semantics §1)."""
    return Departure.UP if passenger.destination > passenger.origin else Departure.DOWN


def _canonical_stops(stops: Iterable[int]) -> tuple[int, ...]:
    return tuple(sorted(set(int(s) for s in stops)))


def next_heading(floor: int, heading: Heading, stops: Iterable[int]) -> Heading:
    """LOOK, exactly as simulation_semantics §4:

    continue in the current heading while any committed stop lies ahead;
    otherwise turn toward the nearest committed stop, preferring ``UP`` on a
    tie; ``NONE`` when there are no committed stops. A stop at the current
    floor is never ahead."""
    canonical = _canonical_stops(stops)
    above = [s for s in canonical if s > floor]
    below = [s for s in canonical if s < floor]
    if not above and not below:
        return Heading.NONE
    if heading is Heading.UP and above:
        return Heading.UP
    if heading is Heading.DOWN and below:
        return Heading.DOWN
    if not above:
        return Heading.DOWN
    if not below:
        return Heading.UP
    d_up = min(above) - floor
    d_down = floor - max(below)
    return Heading.UP if d_up <= d_down else Heading.DOWN


def departure_direction(floor: int, heading: Heading, stops: Iterable[int]) -> Departure:
    """The departure direction at ``floor`` before any boarding
    (simulation_semantics §4.1). ``stops`` are the committed stops; the
    current floor is excluded here (``S_other``), so callers may pass either
    all committed stops or the stops other than ``floor``."""
    s_other = [s for s in _canonical_stops(stops) if s != floor]
    if heading is Heading.NONE:
        return Departure.FREE
    if heading is Heading.UP and any(s > floor for s in s_other):
        return Departure.UP
    if heading is Heading.DOWN and any(s < floor for s in s_other):
        return Departure.DOWN
    return Departure.FREE


@dataclass(frozen=True)
class BoardingResult:
    """The outcome of ``eligible_boarders``: the boarders in boarding order,
    the resulting departure, and the two deferral classes, which never
    overlap (semantics §4.2)."""

    boarders: tuple[Any, ...]
    departure: Departure
    direction_deferred: tuple[Any, ...]
    capacity_deferred: tuple[Any, ...]


def eligible_boarders(waiting: Sequence[Any], departure: Departure, load: int,
                      capacity: int) -> BoardingResult:
    """Direction-first boarding, exactly as simulation_semantics §4.2.

    ``waiting`` holds the WAITING passengers assigned to this car at this
    floor (any objects with ``passenger_id``, ``origin`` and ``destination``);
    they are considered in ascending ``passenger_id``. ``load`` is the
    onboard count after alighting. A passenger whose direction is
    incompatible with the departure (a FREE car would adopt their
    direction) is a direction deferral and capacity is not evaluated; a
    compatible passenger who does not fit is a capacity deferral; the first
    boarder of a FREE car sets the departure."""
    ordered = sorted(waiting, key=lambda p: p.passenger_id)
    boarders: list[Any] = []
    direction_deferred: list[Any] = []
    capacity_deferred: list[Any] = []
    current = departure
    for p in ordered:
        d_p = _direction_of(p)
        d_eff = current if current is not Departure.FREE else d_p
        if d_p is not d_eff:
            direction_deferred.append(p)
            continue
        if load + len(boarders) >= capacity:
            capacity_deferred.append(p)
            continue
        if current is Departure.FREE:
            current = d_p
        boarders.append(p)
    return BoardingResult(boarders=tuple(boarders), departure=current,
                          direction_deferred=tuple(direction_deferred),
                          capacity_deferred=tuple(capacity_deferred))


# ---------------------------------------------------------------------------
# Projection (scheduler_design §5): the three primitives, iterated.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OnboardPassenger:
    passenger_id: int
    destination: int


@dataclass(frozen=True)
class WaitingPassenger:
    passenger_id: int
    origin: int
    destination: int


@dataclass(frozen=True)
class RouteState:
    """The minimal view of one elevator the projection needs: floor, heading,
    onboard passengers (id, destination) and waiting passengers assigned to
    it (id, origin, destination). The scheduler's ``ElevatorView`` (cut 4)
    carries these same fields."""

    floor: int
    heading: Heading
    onboard: tuple[OnboardPassenger, ...]
    waiting: tuple[WaitingPassenger, ...]


@dataclass(frozen=True)
class Projection:
    pickup_time: dict[int, int]
    dropoff_time: dict[int, int]
    first_compatible_arrival: dict[int, int]
    deferred: frozenset[int]
    wrong_way_passes: dict[int, int]
    max_load: int
    end_time: int


def _committed_stops(onboard: Sequence[OnboardPassenger],
                     waiting: Sequence[WaitingPassenger]) -> tuple[int, ...]:
    return _canonical_stops([p.destination for p in onboard] + [p.origin for p in waiting])


def project(elevator_view: Any, extra_waiting: Sequence[Any] = (), *, capacity: int,
            now: int) -> Projection:
    """Simulate one elevator forward from ``now`` under exactly the engine's
    steps 3, 4, 5 and 8, calling the same three primitives, with the
    committed passengers plus ``extra_waiting`` candidates, until no
    committed stop remains (scheduler_design §5). Pure: reads only its
    arguments.

    ``elevator_view`` exposes ``floor``, ``heading``, ``onboard`` (items with
    ``passenger_id`` and ``destination``) and ``waiting`` (items with
    ``passenger_id``, ``origin`` and ``destination``); ``extra_waiting`` items
    have the waiting shape."""
    floor = int(elevator_view.floor)
    heading = elevator_view.heading
    onboard: dict[int, OnboardPassenger] = {
        p.passenger_id: OnboardPassenger(p.passenger_id, p.destination) for p in elevator_view.onboard}
    waiting: dict[int, WaitingPassenger] = {
        p.passenger_id: WaitingPassenger(p.passenger_id, p.origin, p.destination)
        for p in list(elevator_view.waiting) + list(extra_waiting)}

    pickup_time: dict[int, int] = {}
    dropoff_time: dict[int, int] = {}
    first_compatible_arrival: dict[int, int] = {}
    wrong_way_passes: dict[int, int] = {}
    max_load = len(onboard)

    # Termination is guaranteed by the liveness proof (semantics §8.2); the
    # guard below can only fire on an invariant violation.
    all_floors = [floor] + [p.destination for p in onboard.values()] + \
        [f for p in waiting.values() for f in (p.origin, p.destination)]
    span = max(all_floors) - min(all_floors)
    population = len(onboard) + len(waiting)
    guard = now + 2 * population * (span + 1) + 2

    t = now
    while True:
        # step 3: alight
        for pid in sorted(onboard):
            if onboard[pid].destination == floor:
                dropoff_time[pid] = t
                del onboard[pid]
        # step 4: departure and boarding
        stops = _committed_stops(list(onboard.values()), list(waiting.values()))
        departure = departure_direction(floor, heading, stops)
        at_floor = sorted((p for p in waiting.values() if p.origin == floor),
                          key=lambda p: p.passenger_id)
        result = eligible_boarders(at_floor, departure, len(onboard), capacity)
        for p in result.boarders:
            pickup_time[p.passenger_id] = t
            first_compatible_arrival.setdefault(p.passenger_id, t)
            del waiting[p.passenger_id]
            onboard[p.passenger_id] = OnboardPassenger(p.passenger_id, p.destination)
        for p in result.capacity_deferred:
            first_compatible_arrival.setdefault(p.passenger_id, t)
        for p in result.direction_deferred:
            wrong_way_passes[p.passenger_id] = wrong_way_passes.get(p.passenger_id, 0) + 1
        max_load = max(max_load, len(onboard))
        # step 5: heading
        stops = _committed_stops(list(onboard.values()), list(waiting.values()))
        if result.departure is Departure.FREE:
            heading = next_heading(floor, heading, stops)
        else:
            heading = result.departure.as_heading
        if not stops:
            end_time = t
            break
        # step 8: move
        floor += heading.delta
        t += 1
        if t > guard:
            raise RuntimeError("projection exceeded the liveness guard: invariant violation")

    deferred = frozenset(pid for pid, arrival in first_compatible_arrival.items()
                         if pid in pickup_time and pickup_time[pid] > arrival)
    return Projection(pickup_time=pickup_time, dropoff_time=dropoff_time,
                      first_compatible_arrival=first_compatible_arrival, deferred=deferred,
                      wrong_way_passes=wrong_way_passes, max_load=max_load, end_time=end_time)
