"""Shared reporting test helpers: build a RunRecord from a finished engine."""

from __future__ import annotations

from elevator.domain import Configuration, bind_run, normalize_requests
from elevator.engine import Engine
from elevator.policies import CostBased, NearestCar, RoundRobin
from elevator.reporting import RunRecord


def policy_for(name, floors, params=None):
    if name == "cost_based":
        return CostBased.for_building(floors, **(params or {}))
    return {"round_robin": RoundRobin, "nearest_car": NearestCar}[name]()


def run_record(rows, floors, elevators=1, capacity=2, *, initial=None, policy="cost_based", params=None,
               policy_object=None, max_ticks=None):
    """Run the real engine to its outcome and wrap the result for reporting."""
    trace = normalize_requests(rows, floors)
    cfg = Configuration.create(floors, elevators, capacity, initial_floors=initial, policy=policy,
                               policy_params=params, max_ticks=max_ticks)
    eng = Engine.create(cfg, trace, policy_object or policy_for(policy, floors, params))
    eng.run()
    identity = bind_run(cfg, trace, "0" * 64)
    return RunRecord(cfg, trace, identity, eng.history, eng.passengers), eng
