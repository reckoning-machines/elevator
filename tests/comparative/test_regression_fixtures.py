"""Cut 8 regression fixtures (testing_contract §4). A guard on one fixture, not a claim."""

from elevator import reporting as R
from elevator.scenarios import Scenario, generate
from tests.report_fixtures import run_record

# The committed capacity_stress fixture: 40 requests at t = 0 from the lobby in a 12-floor, 3-car,
# capacity-4 building, seed 0. Its Trace hash pins the fixture itself; the generator is pinned by the
# independent oracle in tests/fixtures/scenarios.
F, N, C = 12, 3, 4
FIXTURE_TRACE_HASH = "568510391afca5c119891e82d751ebb8cc6172e959c84564550d0729da5b6203"


def test_cost_based_not_worse_on_capacity_stress_fixture():
    trace = generate(Scenario("capacity_stress", {"num_requests": 40}, 0), F, N, C)
    assert trace.trace_hash == FIXTURE_TRACE_HASH and trace.num_requests == 40
    rows = [(r.request_time, r.source_id, r.origin, r.destination) for r in trace.requests]
    p95 = {}
    for policy in ("round_robin", "nearest_car", "cost_based"):
        record, _eng = run_record(rows, F, N, C, policy=policy)  # the same Trace for every policy
        assert record.trace.trace_hash == FIXTURE_TRACE_HASH
        summary = R.summary(record)
        assert summary["standing"] == "COMPLETED" and summary["unserved"] == 0
        p95[policy] = summary["wait"]["p95"]
    # p95 wait of cost_based is no greater than each baseline's (measured: 48 against 56 and 166)
    assert p95["cost_based"] <= p95["round_robin"] and p95["cost_based"] <= p95["nearest_car"], p95
    assert p95 == {"round_robin": 56, "nearest_car": 166, "cost_based": 48}  # a change shows up in review
