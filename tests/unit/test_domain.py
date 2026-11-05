"""Cut 1 unit tests (testing_contract §1). Each test function is named after
the contract's identifier with the pytest ``test_`` prefix."""

import dataclasses

import pytest

from elevator import api
from elevator.domain import (
    MAX_REQUEST_ROWS,
    MAX_REQUEST_TIME,
    Configuration,
    Passenger,
    Refusal,
    SimulationEvent,
    SimulationEventKind,
    Standing,
    default_max_ticks,
    normalize_requests,
)


def rows(*items):
    return [{"time": t, "id": i, "source": s, "dest": d} for (t, i, s, d) in items]


def test_same_floor_source_destination_refused():
    with pytest.raises(Refusal) as info:
        normalize_requests(rows((0, "a", 0, 3), (1, "b", 4, 4)), num_floors=6)
    assert info.value.reason == "SAME_FLOOR_REQUEST"
    assert info.value.positions == (1,)
    assert info.value.source_id == "b"


def test_missing_source_id_refused():
    with pytest.raises(Refusal) as info:
        normalize_requests(rows((0, "", 0, 3)), num_floors=6)
    assert info.value.reason == "MISSING_SOURCE_ID"
    assert info.value.positions == (0,)
    # A row without an id key at all is not a mapping of the admitted shape.
    with pytest.raises(Refusal) as info2:
        normalize_requests([{"time": 0, "source": 0, "dest": 3}], num_floors=6)
    assert info2.value.reason == "INPUT_INVALID"
    assert info2.value.positions == (0,)


def test_duplicate_source_id_refused():
    with pytest.raises(Refusal) as info:
        normalize_requests(rows((0, "p", 0, 3), (2, "q", 1, 2), (5, "p", 3, 0)), num_floors=6)
    assert info.value.reason == "DUPLICATE_SOURCE_ID"
    assert info.value.positions == (0, 2)
    assert info.value.source_id == "p"


def test_source_id_normalization_cases():
    # integer 1 and string "1" collide after normalisation
    with pytest.raises(Refusal) as info:
        normalize_requests(rows((0, 1, 0, 3), (0, "1", 1, 2)), num_floors=6)
    assert info.value.reason == "DUPLICATE_SOURCE_ID"
    assert info.value.positions == (0, 1)
    # "01" is distinct from "1"
    trace = normalize_requests(rows((0, "1", 0, 3), (0, "01", 1, 2)), num_floors=6)
    assert [r.source_id for r in trace.requests] == ["1", "01"]
    # equal timestamps keep input order: "z" before "a"
    trace = normalize_requests(rows((7, "z", 0, 3), (7, "a", 1, 2)), num_floors=6)
    assert [r.source_id for r in trace.requests] == ["z", "a"]
    assert [r.passenger_id for r in trace.requests] == [0, 1]
    assert [r.input_index for r in trace.requests] == [0, 1]
    # decimal-digit strings convert; other strings and bools refuse
    trace = normalize_requests([("3", "x", "0", "2")], num_floors=4)
    assert (trace.requests[0].request_time, trace.requests[0].origin, trace.requests[0].destination) == (3, 0, 2)
    for bad in [("3", "x", "zero", "2"), ("-1", "x", 0, 2), (True, "x", 0, 2), (0, True, 0, 2), (0, None, 0, 2)]:
        with pytest.raises(Refusal) as info:
            normalize_requests([bad], num_floors=4)
        assert info.value.reason == "INPUT_INVALID"
    # a bare string row, a three-element row and a mapping with extra keys are refused
    for bad_row in ["0,x,0,2", (0, "x", 0), {"time": 0, "id": "x", "source": 0, "dest": 2, "extra": 1}]:
        with pytest.raises(Refusal) as info:
            normalize_requests([bad_row], num_floors=4)
        assert info.value.reason == "INPUT_INVALID"


def test_configuration_domain_refusals():
    for kwargs in [dict(num_floors=1, num_elevators=1, capacity=1),
                   dict(num_floors=201, num_elevators=1, capacity=1),
                   dict(num_floors=10, num_elevators=0, capacity=1),
                   dict(num_floors=10, num_elevators=21, capacity=1),
                   dict(num_floors=10, num_elevators=1, capacity=0),
                   dict(num_floors=10, num_elevators=1, capacity=51)]:
        with pytest.raises(Refusal) as info:
            Configuration.create(**kwargs)
        assert info.value.reason == "INVALID_CONFIGURATION"
    # the boundary values are accepted
    Configuration.create(2, 1, 1)
    Configuration.create(200, 20, 50)
    # request-time domain: 10^9 accepted, 10^9 + 1 refused
    normalize_requests(rows((MAX_REQUEST_TIME, "a", 0, 1)), num_floors=2)
    with pytest.raises(Refusal) as info:
        normalize_requests(rows((MAX_REQUEST_TIME + 1, "a", 0, 1)), num_floors=2)
    assert info.value.reason == "INPUT_INVALID"
    # row count: 100000 accepted, 100001 refused
    many = [(0, str(i), 0, 1) for i in range(MAX_REQUEST_ROWS)]
    assert normalize_requests(many, num_floors=2).num_requests == MAX_REQUEST_ROWS
    with pytest.raises(Refusal) as info:
        normalize_requests(many + [(0, "last", 0, 1)], num_floors=2)
    assert info.value.reason == "INPUT_INVALID"
    # floors out of range, initial floors, policy name and parameters
    with pytest.raises(Refusal):
        normalize_requests(rows((0, "a", 0, 6)), num_floors=6)
    with pytest.raises(Refusal):
        Configuration.create(6, 2, 2, initial_floors=[0])
    with pytest.raises(Refusal):
        Configuration.create(6, 2, 2, initial_floors=[0, 6])
    with pytest.raises(Refusal):
        Configuration.create(6, 2, 2, policy="nearest")
    with pytest.raises(Refusal):
        Configuration.create(6, 2, 2, policy="cost_based", policy_params={"w_wait": 10**6 + 1})
    with pytest.raises(Refusal):
        Configuration.create(6, 2, 2, policy="cost_based", policy_params={"w_total": 1})
    with pytest.raises(Refusal):
        Configuration.create(6, 2, 2, policy="round_robin", policy_params={"w_wait": 1})
    # cost-based defaults depend on F and are fixed at creation
    cfg = Configuration.create(6, 2, 2)
    assert cfg.policy_params == {"age_scale": 5, "tail_threshold": 10, "w_marginal": 1, "w_tail": 3, "w_wait": 1}


def test_source_id_preserved_in_outputs():
    # mapping half: the Trace carries the supplied id on every Request and the
    # passenger_id is the stable-sort position by (time, input_index)
    trace = normalize_requests(rows((5, "late", 0, 3), (0, "early-b", 1, 2), (0, 7, 2, 0)), num_floors=4)
    assert [(r.passenger_id, r.source_id, r.input_index) for r in trace.requests] == [
        (0, "early-b", 1), (1, "7", 2), (2, "late", 0)]
    assert set(trace.by_source_id()) == {"late", "early-b", "7"}
    assert trace.by_source_id()["7"].passenger_id == 1


def test_horizon_halt_reasons_distinct():
    # refusal half: max_ticks above the default bound is INVALID_CONFIGURATION
    trace = normalize_requests(rows((4, "a", 0, 3), (9, "b", 1, 2)), num_floors=5)
    bound = default_max_ticks(5, trace)
    assert bound == 9 + 2 * 2 * 4
    assert Configuration.create(5, 1, 1, max_ticks=bound).validate_with_trace(trace) == bound
    assert Configuration.create(5, 1, 1, max_ticks=3).validate_with_trace(trace) == 3
    assert Configuration.create(5, 1, 1).validate_with_trace(trace) == bound
    with pytest.raises(Refusal) as info:
        Configuration.create(5, 1, 1, max_ticks=bound + 1).validate_with_trace(trace)
    assert info.value.reason == "INVALID_CONFIGURATION"
    # an empty Trace has T_last = 0 and bound 0
    assert default_max_ticks(5, normalize_requests([], num_floors=5)) == 0


def test_receipt_never_on_passenger():
    names = {f.name for f in dataclasses.fields(Passenger)}
    assert names == {"passenger_id", "source_id", "request_time", "origin", "destination",
                     "standing", "assigned_elevator", "assigned_at", "pickup_time", "dropoff_time"}
    assert not any("estimate" in n or "projected" in n or "receipt" in n or "cost" in n for n in names)
    # the ASSIGNED event is where a receipt lives
    event_fields = {f.name for f in dataclasses.fields(SimulationEvent)}
    assert "receipt" in event_fields
    e = SimulationEvent(seq=1, kind=SimulationEventKind.ASSIGNED, tick=0, passenger_id=0,
                        elevator_id=1, receipt={"tier": 1, "cost": 5})
    assert e.receipt == {"tier": 1, "cost": 5}
    p = Passenger(0, "a", 0, 0, 3, Standing.WAITING, 1, 0, None, None)
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.pickup_time = 4  # type: ignore[misc]


def test_public_boundary_is_normalize_requests():
    assert api.normalize_requests is normalize_requests
