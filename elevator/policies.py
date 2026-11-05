"""Scheduler policies: the baselines (plan cut 4; scheduler_design §2 to §4).

A policy proposes; it owns nothing. ``assign(view, request) -> Proposal`` is
a pure function of its arguments and its immutable parameters: no clock, no
randomness, no I/O, no retained state, no module-level state. A policy
object holds only immutable parameters (these two baselines take none).
The engine validates and commits the proposal; a policy cannot write a
Passenger or an Elevator, read the Trace or the History, or revisit an
earlier assignment.

The interface is the one the engine calls (``engine.SchedulerPolicy``): any
object with ``assign(view, request)`` returning a ``Proposal`` satisfies it.
This module imports only ``domain`` and ``route`` (the shared projection):
nothing from the engine, no Trace type, no I/O.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from elevator import route
from elevator.domain import (
    COST_BASED_PARAMS,
    MAX_POLICY_PARAM,
    Proposal,
    Refusal,
    RevealedRequest,
    SchedulerView,
    WaitingView,
)


@dataclass(frozen=True)
class RoundRobin:
    """``round_robin``: ``elevator_id = passenger_id mod N``.

    ``passenger_id`` is the stable Trace order, so this is exactly "the next
    elevator in rotation" with no pointer (a pointer would be hidden policy
    state, constitution N15). Ignores position, load, direction and
    committed work. ``receipt = None``."""

    name = "round_robin"

    def assign(self, view: SchedulerView, request: RevealedRequest) -> Proposal:
        return Proposal(elevator_id=request.passenger_id % view.num_elevators, receipt=None)


@dataclass(frozen=True)
class NearestCar:
    """``nearest_car``: ``argmin over E of |floor_E - origin|``, ties to the
    lowest elevator id. Ignores load, direction and committed work: the
    classic naive baseline, deliberately. ``receipt = {"distance": d}``."""

    name = "nearest_car"

    def assign(self, view: SchedulerView, request: RevealedRequest) -> Proposal:
        distance, elevator_id = min((abs(e.floor - request.origin), e.id) for e in view.elevators)
        return Proposal(elevator_id=elevator_id, receipt={"distance": distance})


@dataclass(frozen=True)
class CostBased:
    """``cost_based``: a heuristic destination-dispatch policy (scheduler §6).

    For each elevator ``E`` in id order, ``route.project`` (the shared
    projection, never a copy) is called twice over the committed world: once
    without and once with the candidate. From those two projections:

        wait_c   = with.pickup_time[c] - t
        marginal = sum over committed q of (age_scale + age(q, t)) *
                   (with.dropoff_time[q] - base.dropoff_time[q])      (signed)
        cost     = age_scale * (w_wait * wait_c
                                + w_tail * max(0, wait_c - tail_threshold))
                   + w_marginal * marginal

    Tier 1: the candidate is not capacity-deferred in ``with`` and the
    candidate causes no new capacity deferral among the passengers already
    committed to ``E``; otherwise Tier 2. Choose from Tier 1 if non-empty,
    else Tier 2, by ``(cost, elevator id)``. All arithmetic is exact
    integer arithmetic; a negative cost is lawful. The receipt carries the
    full candidate table in elevator-id order. No state, no cache across
    calls, no clock, no randomness, no demand model."""

    w_wait: int
    w_marginal: int
    w_tail: int
    tail_threshold: int
    age_scale: int

    name = "cost_based"

    def __post_init__(self) -> None:
        for field_name in COST_BASED_PARAMS:
            value = getattr(self, field_name)
            if type(value) is not int or not (0 <= value <= MAX_POLICY_PARAM):
                raise ValueError(f"{field_name} must be an int in 0..{MAX_POLICY_PARAM}")

    @staticmethod
    def for_building(num_floors: int, **overrides: int) -> "CostBased":
        """The documented defaults for a building of ``num_floors`` floors
        (scheduler section 6.3), with optional integer overrides."""
        params = {"w_wait": 1, "w_marginal": 1, "w_tail": 3,
                  "tail_threshold": 2 * (num_floors - 1), "age_scale": num_floors - 1}
        unknown = set(overrides) - set(COST_BASED_PARAMS)
        if unknown:
            raise ValueError(f"unknown cost_based parameters: {sorted(unknown)}")
        params.update(overrides)
        return CostBased(**params)

    def assign(self, view: SchedulerView, request: RevealedRequest) -> Proposal:
        t, capacity = view.t, view.capacity
        candidate = WaitingView(request.passenger_id, request.origin, request.destination,
                                request.request_time)
        table: list[dict[str, Any]] = []
        for e in sorted(view.elevators, key=lambda ev: ev.id):
            base = route.project(e, capacity=capacity, now=t)
            with_c = route.project(e, (candidate,), capacity=capacity, now=t)
            committed = [w.passenger_id for w in e.waiting] + [o.passenger_id for o in e.onboard]
            wait_c = with_c.pickup_time[candidate.passenger_id] - t
            deferred_c = candidate.passenger_id in with_c.deferred
            newly_deferred = tuple(sorted((with_c.deferred - base.deferred) & set(committed)))
            marginal = self._marginal(e, t, base, with_c)
            tier = 1 if (not deferred_c and not newly_deferred) else 2
            cost = (self.age_scale * (self.w_wait * wait_c
                                      + self.w_tail * max(0, wait_c - self.tail_threshold))
                    + self.w_marginal * marginal)
            table.append({"E": e.id, "tier": tier, "cost": cost, "wait_c": wait_c,
                          "marginal": marginal, "deferred_c": deferred_c,
                          "newly_deferred_others": newly_deferred,
                          "wrong_way_passes_c": with_c.wrong_way_passes.get(candidate.passenger_id, 0),
                          "_pickup": with_c.pickup_time[candidate.passenger_id],
                          "_dropoff": with_c.dropoff_time[candidate.passenger_id]})
        admissible = [row for row in table if row["tier"] == 1] or table
        chosen = min(admissible, key=lambda row: (row["cost"], row["E"]))
        receipt = {"policy": self.name, "tier": chosen["tier"], "chosen": chosen["E"],
                   "cost": chosen["cost"], "projected_pickup": chosen["_pickup"],
                   "projected_dropoff": chosen["_dropoff"],
                   "candidates": tuple({k: v for k, v in row.items() if not k.startswith("_")}
                                       for row in table)}
        return Proposal(elevator_id=chosen["E"], receipt=receipt)

    def _marginal(self, e: Any, t: int, base: route.Projection, with_c: route.Projection) -> int:
        total = 0
        for w in e.waiting:
            delta = with_c.dropoff_time[w.passenger_id] - base.dropoff_time[w.passenger_id]
            total += (self.age_scale + (t - w.request_time)) * delta
        for o in e.onboard:
            # An onboard passenger travels toward its destination in the car's
            # heading until it alights (the car never reverses while a stop lies
            # ahead), so its projected dropoff is ``t + |destination - floor|``
            # whatever else is assigned (constitution P11): its delta is
            # identically zero and its age (``request_time`` is not in the
            # lawful view) cannot change the sum. A nonzero delta would be an
            # invariant violation, so fail closed rather than guess an age.
            delta = with_c.dropoff_time[o.passenger_id] - base.dropoff_time[o.passenger_id]
            if delta != 0:
                raise RuntimeError(f"projection moved onboard passenger {o.passenger_id}'s dropoff "
                                   f"by {delta:+d}: violates constitution P11")
        return total


def make_policy(name: str, params: Mapping[str, int] | None = None) -> RoundRobin | NearestCar | CostBased:
    """The one resolver from a policy name and its Configuration parameters to a policy object
    (architecture §1.2, owner decision 009): the architecture's "dict of three names", with no registry,
    plugin, hook, dynamic import or module-level state. ``params`` are the Configuration's default-filled
    ``policy_params``, so the API, the harness, the CLI and (later) checkpoint and web build exactly the
    same policy from the same Configuration. It supports ``round_robin``, ``nearest_car`` and
    ``cost_based`` and nothing else: any other name, or parameters a baseline does not take, refuse
    ``INVALID_CONFIGURATION``. Constructing a policy transfers no authority: a policy only proposes."""
    params = dict(params or {})
    if name == "cost_based":
        return CostBased(**params)
    if name == "round_robin":
        policy: RoundRobin | NearestCar = RoundRobin()
    elif name == "nearest_car":
        policy = NearestCar()
    else:
        raise Refusal("INVALID_CONFIGURATION", f"policy {name!r} is not one of round_robin, nearest_car, cost_based")
    if params:
        raise Refusal("INVALID_CONFIGURATION", f"policy {name} takes no parameters")
    return policy
