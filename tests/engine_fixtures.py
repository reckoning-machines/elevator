"""Shared engine test fixtures: stub policies, fixture runs and the
history-derived deferral classifier. Test-only; no runtime code."""

from __future__ import annotations

from dataclasses import dataclass, field

from elevator import route
from elevator.domain import Configuration, Heading, Proposal, Standing, normalize_requests
from elevator.engine import Engine


@dataclass
class ByIdPolicy:
    """Stub: elevator = mapping[passenger_id], else passenger_id mod N. No
    retained decision state; ``views`` only records what it was shown."""

    mapping: dict[int, int] = field(default_factory=dict)
    record: bool = False
    views: list = field(default_factory=list)

    def assign(self, view, request):
        if self.record:
            self.views.append((view, request))
        return Proposal(self.mapping.get(request.passenger_id, request.passenger_id % view.num_elevators))


@dataclass
class HashPolicy:
    salt: int = 7

    def assign(self, view, request):
        return Proposal((request.passenger_id * self.salt + request.origin) % view.num_elevators)


def build(rows, floors, elevators=1, capacity=4, *, initial=None, policy=None, max_ticks=None):
    trace = normalize_requests(rows, floors)
    cfg = Configuration.create(floors, elevators, capacity, initial_floors=initial,
                               max_ticks=max_ticks, policy="round_robin")
    return Engine.create(cfg, trace, policy or ByIdPolicy()), trace


def run_stepwise(engine):
    """Run to the outcome, keeping the boundary state before each tick and
    the passengers after it (passengers do not change in steps 5 to 9)."""
    steps = []
    while engine.outcome is None:
        before = (engine.t, engine.elevators, engine.passengers)
        engine.step()
        steps.append((before, engine.passengers))
    return steps


def classify_deferrals(engine, steps, capacity, from_tick=0):
    """Per passenger, count capacity deferrals and wrong-way passes from
    observed state, applying the single classification rule of semantics
    §4.2 via the shared primitives (the reporting cut will derive the same
    counts from History)."""
    capacity_deferrals, wrong_way = {}, {}
    records = {r.tick: r for r in engine.history.tick_records}
    for (t, elevators_before, _passengers_before), passengers_after in steps:
        if t not in records or t < from_tick:
            continue
        for e in elevators_before:
            entry = records[t].entries[e.elevator_id]
            waiting_here = [p for p in passengers_after if p.standing is Standing.WAITING
                            and p.assigned_elevator == e.elevator_id and p.origin == e.floor]
            if not waiting_here:
                continue
            boarders = set(entry.boarded)
            pre_stops = {p.destination for p in passengers_after if p.standing is Standing.ONBOARD
                         and p.assigned_elevator == e.elevator_id and p.passenger_id not in boarders}
            pre_stops |= {p.origin for p in passengers_after if p.standing is Standing.WAITING
                          and p.assigned_elevator == e.elevator_id}
            departure = route.departure_direction(e.floor, e.heading, pre_stops)
            if boarders:
                first = min(boarders)
                p0 = next(p for p in passengers_after if p.passenger_id == first)
                departure = route.Departure.UP if p0.destination > p0.origin else route.Departure.DOWN
            for p in waiting_here:
                d = route.Departure.UP if p.destination > p.origin else route.Departure.DOWN
                if departure is not route.Departure.FREE and d is not departure:
                    wrong_way[p.passenger_id] = wrong_way.get(p.passenger_id, 0) + 1
                else:
                    capacity_deferrals[p.passenger_id] = capacity_deferrals.get(p.passenger_id, 0) + 1
    return capacity_deferrals, wrong_way


def rows_of(engine):
    return [(r.tick, [(x.floor, x.heading, x.load, x.boarded, x.alighted) for x in r.entries])
            for r in engine.history.tick_records]


def floors_headings_loads(engine, elevator_id=0):
    recs = engine.history.tick_records
    return ([r.entries[elevator_id].floor for r in recs],
            [r.entries[elevator_id].heading for r in recs],
            [r.entries[elevator_id].load for r in recs])


UP, DOWN, NONE = Heading.UP, Heading.DOWN, Heading.NONE
