"""Cut 4 no-look-ahead witnesses (testing_contract §3), for both baselines.

Compared surface (constitution N1): for traces T and T' that agree on every
request with request_time <= t*, with end = min(t*, final_T, final_T'), the
decision and motion prefix is every REVEALED, ASSIGNED (with receipt), BOARDED
and ALIGHTED event with tick <= end and every TickRecord with tick <= end.
Run-standing events and anything after end are excluded: termination lawfully
depends on whether unrevealed requests remain. All three policies are covered."""

import dataclasses

import pytest

from elevator.domain import Configuration, SimulationEventKind as K, normalize_requests
from elevator.engine import Engine
from elevator.policies import CostBased, NearestCar, RoundRobin

# factories take the number of floors (cost_based's defaults depend on it)
POLICIES = [("round_robin", lambda floors: RoundRobin()), ("nearest_car", lambda floors: NearestCar()),
            ("cost_based", CostBased.for_building)]
PREFIX_KINDS = {K.REVEALED, K.ASSIGNED, K.BOARDED, K.ALIGHTED}


class Recorder:
    """Test-side wrapper: delegates to a baseline and records each Proposal by
    (t, passenger_id)."""

    def __init__(self, inner):
        self.inner = inner
        self.proposals = {}

    def assign(self, view, request):
        proposal = self.inner.assign(view, request)
        self.proposals[(view.t, request.passenger_id)] = (proposal.elevator_id, proposal.receipt)
        return proposal


def run(rows, floors, elevators, capacity, initial, name, factory):
    rec = Recorder(factory(floors))
    cfg = Configuration.create(floors, elevators, capacity, initial_floors=initial, policy=name)
    eng = Engine.create(cfg, normalize_requests(rows, floors), rec)
    eng.run()
    return eng, rec


def prefix(eng, end):
    events = [(e.kind, e.tick, e.passenger_id, e.elevator_id, e.floor,
               None if e.receipt is None else dict(e.receipt))
              for e in eng.history.events if e.kind in PREFIX_KINDS and e.tick <= end]
    return events, [r for r in eng.history.tick_records if r.tick <= end]


def lcg(seed):
    state = seed

    def nxt(k):
        nonlocal state
        state = (state * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        return (state >> 33) % k
    return nxt


def random_rows(nxt, floors, count, lo, hi, tag):
    rows = []
    for i in range(count):
        o = nxt(floors)
        d = (o + 1 + nxt(floors - 1)) % floors
        rows.append((lo + nxt(hi - lo + 1), f"{tag}{i}", o, d))
    return rows


def building(nxt):
    f, n, c = 3 + nxt(5), 1 + nxt(3), 1 + nxt(3)
    return f, n, c, [nxt(f) for _ in range(n)]


def assert_same_prefix(eng_a, rec_a, eng_b, rec_b, end):
    assert prefix(eng_a, end) == prefix(eng_b, end)
    assert {k: v for k, v in rec_a.proposals.items() if k[0] <= end} == \
        {k: v for k, v in rec_b.proposals.items() if k[0] <= end}


@pytest.mark.parametrize("name,factory", POLICIES)
def test_future_mutation_does_not_change_prefix(name, factory):
    checked = 0
    for seed in range(40):
        nxt = lcg(1000 + seed)
        floors, n, c, initial = building(nxt)
        base = random_rows(nxt, floors, 3 + nxt(7), 0, 25, "r")
        eng_t, rec_t = run(base, floors, n, c, initial, name, factory)
        for t_star in (0, 3, 8, 14):
            kept = [r for r in base if r[0] <= t_star]
            variants = [
                kept,                                                                   # remove every later request
                kept + random_rows(lcg(seed * 7 + t_star), floors, 4, t_star + 1, t_star + 20, "x"),   # arbitrary
                kept + random_rows(lcg(seed * 13 + t_star), floors, 8, t_star + 1, t_star + 6, "y"),   # burst
                kept + [(t_star + 1, "z", 0, floors - 1)],                              # single sentinel
            ]
            for rows_b in variants:
                eng_b, rec_b = run(rows_b, floors, n, c, initial, name, factory)
                end = min(t_star, eng_t.outcome.final_tick, eng_b.outcome.final_tick)
                assert_same_prefix(eng_t, rec_t, eng_b, rec_b, end)
                checked += 1
    assert checked == 40 * 4 * 4


@pytest.mark.parametrize("name,factory", POLICIES)
def test_future_mutation_both_active(name, factory):
    checked = 0
    for seed in range(40):
        nxt = lcg(5000 + seed)
        floors, n, c, initial = building(nxt)
        for t_star in (2, 6, 11):
            shared = [r for r in random_rows(nxt, floors, 4, 0, t_star, "s")]
            # each trace has a request strictly after t*, so neither terminates before t*
            rows_t = shared + random_rows(nxt, floors, 3, t_star + 1, t_star + 15, "t") + [(t_star + 9, "ta", 0, 1)]
            rows_b = shared + random_rows(nxt, floors, 5, t_star + 1, t_star + 12, "u") + [(t_star + 2, "ub", 1, 0)]
            eng_t, rec_t = run(rows_t, floors, n, c, initial, name, factory)
            eng_b, rec_b = run(rows_b, floors, n, c, initial, name, factory)
            end = min(t_star, eng_t.outcome.final_tick, eng_b.outcome.final_tick)
            assert end == t_star  # both active: nothing ended early
            assert_same_prefix(eng_t, rec_t, eng_b, rec_b, end)
            # the prefix includes every tick through t*, idle ones too
            assert [r.tick for r in prefix(eng_t, end)[1]] == list(range(t_star + 1))
            checked += 1
    assert checked == 120


@pytest.mark.parametrize("name,factory", POLICIES)
def test_sentinel_future_request(name, factory):
    fixtures = [
        ([(0, "a", 0, 4), (0, "b", 2, 0), (3, "c", 4, 1)], 5, 2, 2, [0, 4]),
        ([(1, "a", 3, 0), (1, "b", 3, 4), (6, "c", 0, 4)], 5, 1, 1, [3]),
        ([(0, "a", 1, 2)], 4, 3, 3, [0, 1, 3]),
    ]
    for rows, floors, n, c, initial in fixtures:
        eng_t, rec_t = run(rows, floors, n, c, initial, name, factory)
        for t_star in range(0, 8):
            sentinel = rows + [(t_star + 1, "sentinel", 0, floors - 1)]
            eng_s, rec_s = run(sentinel, floors, n, c, initial, name, factory)
            end = min(t_star, eng_t.outcome.final_tick, eng_s.outcome.final_tick)
            assert prefix(eng_t, end) == prefix(eng_s, end)
            assert {k: v for k, v in rec_t.proposals.items() if k[0] <= end} == \
                {k: v for k, v in rec_s.proposals.items() if k[0] <= end}


@pytest.mark.parametrize("name,factory", POLICIES)
def test_policy_sees_only_revealed_passengers(name, factory):
    """view_has_no_future restated against the real baselines: every view the
    engine builds holds only passengers with request_time <= t."""
    seen = []

    class Spy:
        def __init__(self, inner):
            self.inner = inner

        def assign(self, view, request):
            seen.append((view, request))
            return self.inner.assign(view, request)

    nxt = lcg(77)
    floors, n, c, initial = building(nxt)
    rows = random_rows(nxt, floors, 9, 0, 12, "p")
    eng = Engine.create(Configuration.create(floors, n, c, initial_floors=initial, policy=name),
                        normalize_requests(rows, floors), Spy(factory(floors)))
    eng.run()
    assert len(seen) == len(rows)
    for view, request in seen:
        assert request.request_time == view.t
        assert all(w.request_time <= view.t for e in view.elevators for w in e.waiting)
        assert all(o.pickup_time <= view.t for e in view.elevators for o in e.onboard)
        assert {f.name for f in dataclasses.fields(view)} == {"t", "floors", "num_elevators", "capacity", "elevators"}


def test_witness_detects_a_policy_that_peeks_at_the_future():
    """Negative control: the comparison above can fail. A policy that reads the
    full trace through a global (the leak testing_contract §3 names) produces a
    different prefix when only unrevealed requests differ."""
    from elevator.domain import Proposal

    full_trace = []

    class Peeker:
        def assign(self, view, request):
            future = sum(1 for r in full_trace if r[0] > view.t)
            return Proposal(future % view.num_elevators, None)

    def go(rows):
        full_trace[:] = rows
        return run(rows, 5, 2, 2, [0, 4], "round_robin", lambda floors: Peeker())[0]

    rows_t = [(0, "a", 0, 3), (0, "b", 1, 4), (5, "c", 2, 0), (9, "d", 3, 1)]
    rows_b = [(0, "a", 0, 3), (0, "b", 1, 4), (9, "x", 3, 1), (10, "y", 2, 0), (11, "z", 1, 0)]
    et, eb = go(rows_t), go(rows_b)
    end = min(4, et.outcome.final_tick, eb.outcome.final_tick)
    assert prefix(et, end) != prefix(eb, end)
