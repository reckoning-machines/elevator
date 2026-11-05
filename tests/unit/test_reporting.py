"""Cut 6 unit tests (testing_contract §1, §2 and §6 identifiers noted): reporting."""

import ast
import csv
import dataclasses
import io
import json
import math
import os
import sys
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, getcontext
from fractions import Fraction

import pytest

from elevator import reporting as R
from elevator.domain import SimulationEventKind as K, SimulationHistory, canonical_json
from tests.engine_fixtures import ByIdPolicy, classify_deferrals, run_stepwise
from tests.invariants.test_engine_invariants import FIXTURES, _sweep
from tests.report_fixtures import run_record

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
W_B = [(0, "p0", 0, 4), (0, "p1", 2, 4)]
W_F = [(0, "p0", 0, 4), (0, "p1", 2, 1)]
POLICIES = ("round_robin", "nearest_car", "cost_based")


def parse_csv(data: bytes):
    return list(csv.reader(io.StringIO(data.decode("utf-8"), newline="")))


def sweep_records(policies=POLICIES):
    for spec in FIXTURES + _sweep():
        args = dict(spec)
        rows = args.pop("rows")
        floors = args.pop("floors")
        for policy in policies:
            rec, eng = run_record(rows, floors, args.get("elevators", 1), args.get("capacity", 2),
                                  initial=args.get("initial"), policy=policy)
            yield rec, eng


# --- passenger table -------------------------------------------------------

def test_source_id_preserved_in_outputs():
    # output half: passengers.csv carries the supplied ids, quoted where needed, and the mapping to
    # passenger_id is the stable sort by (request_time, input_index)
    rows = [(5, "late", 0, 3), (0, "z", 1, 2), (0, 'q"uote,comma', 2, 0), (0, "01", 3, 1), (0, "1", 0, 2),
            (0, "ünï\ncode", 1, 3)]
    rec, _ = run_record(rows, 5, 2, 4, policy="round_robin")
    table = parse_csv(R.reproducible_surface(rec)["passengers.csv"])
    header, body = table[0], table[1:]
    assert header[:2] == ["passenger_id", "source_id"]
    assert [r[1] for r in body] == ["z", 'q"uote,comma', "01", "1", "ünï\ncode", "late"]
    assert [int(r[0]) for r in body] == list(range(6))
    assert [r[1] for r in body] == [q.source_id for q in rec.trace.requests]


def test_wait_total_and_travel_formulas():
    seen = 0
    for rec, _eng in sweep_records(("round_robin", "cost_based")):
        table = parse_csv(R.reproducible_surface(rec)["passengers.csv"])
        for r in table[1:]:
            req, pick, drop = int(r[2]), int(r[7]), int(r[8])
            assert (int(r[9]), int(r[10]), int(r[11])) == (pick - req, drop - pick, drop - req)
            assert int(r[10]) == abs(int(r[4]) - int(r[3]))  # travel equals distance (constitution P11)
            assert int(r[9]) + int(r[10]) == int(r[11])
            seen += 1
    assert seen > 1500


def test_same_floor_same_tick_wait_is_zero_and_gaps_are_counted():
    rec, _ = run_record([(6, "p", 4, 1)], 6, 1, 2, initial=[4], policy="round_robin")
    s = R.reproducible_surface(rec)
    (row,) = parse_csv(s["passengers.csv"])[1:]
    assert (row[7], row[9]) == ("6", "0")  # boarded at its request time: wait 0
    assert len(parse_csv(s["elevator_positions.csv"])) == 1 + (rec.history.events[-1].tick + 1)
    assert json.loads(s["summary.json"])["wait"]["min"] == 0


# --- aggregates, against independent implementations ---------------------------------

def dec_round(q: Fraction) -> str:
    getcontext().prec = 80
    return str((Decimal(q.numerator) / Decimal(q.denominator)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def dec_std(values) -> str:
    getcontext().prec = 80
    n = len(values)
    var = Decimal(sum(x * x for x in values)) / n - (Decimal(sum(values)) / n) ** 2
    return str(var.sqrt().quantize(Decimal("0.001"), rounding=ROUND_DOWN))


def test_min_max_mean_median_p95_std_match_independent_computation():
    checked = 0
    for rec, _eng in sweep_records(("nearest_car",)):
        s = json.loads(R.reproducible_surface(rec)["summary.json"])
        if s.get("no_passengers"):
            continue
        table = parse_csv(R.reproducible_surface(rec)["passengers.csv"])[1:]
        for key, col in (("wait", 9), ("total", 11)):
            values = sorted(int(r[col]) for r in table)
            n = len(values)
            d = s[key]
            assert (d["min"], d["max"]) == (values[0], values[-1])
            assert d["mean"] == dec_round(Fraction(sum(values), n))
            mid = Fraction(values[n // 2]) if n % 2 else Fraction(values[n // 2 - 1] + values[n // 2], 2)
            assert d["median"] == dec_round(mid)
            assert d["p95"] == values[math.ceil(Fraction(95 * n, 100)) - 1]
            assert d["std"] == dec_std(values)
        travels = [int(r[10]) for r in table]
        assert s["travel"]["mean"] == dec_round(Fraction(sum(travels), len(travels)))
        assert s["n"] == s["completed"] == len(table) and s["unserved"] == 0
        assert s["makespan"] == s["final_tick"]
        checked += 1
    assert checked > 200


def test_summary_of_a_hand_checked_run():
    # W-B (hand-derived): waits 0 and 6, totals 4 and 8, one capacity deferral, car moving on
    # ticks 0 to 7 of 0 to 8, tail threshold 2 * (5 - 1) = 8
    rec, _ = run_record(W_B, 5, 1, 1)
    assert json.loads(R.reproducible_surface(rec)["summary.json"]) == {
        "standing": "COMPLETED", "final_tick": 8, "n": 2, "completed": 2, "unserved": 0, "makespan": 8,
        "wait": {"min": 0, "max": 6, "mean": "3.000", "median": "3.000", "p95": 6, "std": "3.000"},
        "total": {"min": 4, "max": 8, "mean": "6.000", "median": "6.000", "p95": 8, "std": "2.000"},
        "travel": {"mean": "3.000"}, "deferred": {"count": 1}, "wrong_way": {"count": 0, "mean_extra": None},
        "tail_share": "0.000", "tail_ratio": "2.000", "elevator_utilisation": ["0.889"]}
    assert [x.capacity_deferrals for x in R._analyse(rec).facts] == [0, 1]


def test_wrong_way_metrics_on_w_f():
    # W-F: p1 (2->1) is passed going up at t=2 and boards on the return at t=6: one wrong-way pass,
    # extra wait 6 - 2 = 4
    rec, _ = run_record(W_F, 5, 1, 1)
    s = json.loads(R.reproducible_surface(rec)["summary.json"])
    assert s["wrong_way"] == {"count": 1, "mean_extra": "4.000"} and s["deferred"] == {"count": 0}
    row = parse_csv(R.reproducible_surface(rec)["passengers.csv"])[2]
    assert (row[12], row[13]) == ("0", "1")


def test_deferrals_derived_from_tick_records_match_the_engine_classification():
    compared = cap_total = wrong_total = 0
    for spec in FIXTURES + _sweep():
        args = dict(spec)
        rows = args.pop("rows")
        floors = args.pop("floors")
        for policy in ("round_robin", "cost_based"):
            rec, eng = run_record(rows, floors, args.get("elevators", 1), args.get("capacity", 2),
                                  initial=args.get("initial"), policy=policy)
            table = parse_csv(R.reproducible_surface(rec)["passengers.csv"])[1:]
            # an independent classification: replay the same engine run stepwise
            from tests.engine_fixtures import build
            from tests.report_fixtures import policy_for
            eng2, _ = build(rows, floors=floors, elevators=args.get("elevators", 1),
                            capacity=args.get("capacity", 2), initial=args.get("initial"),
                            policy=policy_for(policy, floors))
            steps = run_stepwise(eng2)
            cap, wrong = classify_deferrals(eng2, steps, args.get("capacity", 2))
            for r in table:
                pid = int(r[0])
                assert (int(r[12]), int(r[13])) == (cap.get(pid, 0), wrong.get(pid, 0))
                cap_total += int(r[12])
                wrong_total += int(r[13])
                compared += 1
    assert compared > 1000 and cap_total > 50 and wrong_total > 50


# --- calibration -----------------------------------------------------------------

CAL_ROWS = [(3, "r0", 1, 2), (3, "r1", 0, 5)]  # F=6, C=1, one car idle at floor 4


def test_calibration_witness_later_assignment_changes_the_realized_route():
    """Why calibration exists. r0 (1->2) is assigned first: alone, the car would go down from 4 and
    pick it up at floor 1 at t=6 and drop it at floor 2 at t=7, and that projection is committed in
    its receipt. r1 (0->5) is then assigned to the same car. The car now serves floor 0 first: it
    reaches 1 at t=6 going down (r0 wants up: a wrong-way pass), boards r1 at 0 at t=7 filling the
    car (C=1), passes r0 at 1 at t=8 full, rides to 5 (dropoff 12) and only then returns, boarding r0
    at t=16 and dropping it at t=17: errors +10 and +10. r1, with no later assignment, is exact."""
    rec, eng = run_record(CAL_ROWS, 6, 1, 1, initial=[4])
    r0, r1 = R.calibration(rec)
    assert (r0.projected_pickup, r0.projected_dropoff, r0.tier) == (6, 7, 1)
    assert (r0.realized_pickup, r0.realized_dropoff) == (16, 17)
    assert (r0.pickup_error, r0.dropoff_error, r0.later_assignment_to_same_elevator) == (10, 10, True)
    assert (r1.projected_pickup, r1.projected_dropoff, r1.tier) == (7, 12, 2)
    assert (r1.pickup_error, r1.dropoff_error, r1.later_assignment_to_same_elevator) == (0, 0, False)
    assert R.calibration_summary((r0, r1)) == {"assignments": 2, "exact": 1, "pickup_error_min": 0,
                                               "pickup_error_max": 10, "dropoff_error_min": 0,
                                               "dropoff_error_max": 10}
    # the same numbers appear in the observations, rule 7
    assert "1 of 2 assignments were realized exactly as projected, pickup error min 0 max 10" in R.observations(rec)
    # the receipt itself is untouched: the original projection is still what History says
    (assigned0,) = [e for e in rec.history.events if e.kind is K.ASSIGNED and e.passenger_id == 0]
    assert (assigned0.receipt["projected_pickup"], assigned0.receipt["tier"]) == (6, 1)


def test_calibration_zero_error_for_untouched_elevators():
    untouched = touched = nonzero_touched = 0
    for rec, _eng in sweep_records(("cost_based",)):
        for row in R.calibration(rec):
            if not row.later_assignment_to_same_elevator:
                assert (row.pickup_error, row.dropoff_error) == (0, 0), row
                untouched += 1
            else:
                touched += 1
                nonzero_touched += (row.pickup_error, row.dropoff_error) != (0, 0)
    # measured on this sweep: 977 rows, 374 untouched, 603 touched, 30 of those with a nonzero error;
    # the floors keep the property from being vacuous
    assert untouched >= 300 and touched >= 500 and nonzero_touched >= 20


def test_calibration_uses_the_original_receipt_not_a_recomputed_projection(monkeypatch):
    rec, _ = run_record(W_B, 5, 1, 1)
    # replace the committed receipts with other numbers: the report follows the receipt exactly
    events = []
    for e in rec.history.events:
        if e.kind is K.ASSIGNED:
            e = dataclasses.replace(e, receipt={**dict(e.receipt), "projected_pickup": 100 + e.passenger_id,
                                                "projected_dropoff": 200 + e.passenger_id})
        events.append(e)
    forged = dataclasses.replace(rec, history=SimulationHistory(tuple(events), rec.history.tick_records))
    rows = R.calibration(forged)
    assert [(r.projected_pickup, r.pickup_error) for r in rows] == [(100, 0 - 100), (101, 6 - 101)]
    assert [(r.projected_dropoff, r.dropoff_error) for r in rows] == [(200, 4 - 200), (201, 8 - 201)]
    # and no projection is ever computed: reporting works with the shared projection disabled
    from elevator import route

    def boom(*a, **k):
        raise AssertionError("reporting must not re-run the projection")

    monkeypatch.setattr(route, "project", boom)
    assert len(R.calibration(rec)) == 2 and set(R.reproducible_surface(rec)) == set(R.SURFACE_FILES)


def test_baselines_have_no_calibration_and_nothing_is_fabricated():
    for policy in ("round_robin", "nearest_car"):
        rec, _ = run_record(W_B, 5, 1, 1, policy=policy)
        assert R.calibration(rec) == () and R.calibration_summary(()) is None
        assert "Cost-based" not in R.observations(rec) and "calibration" not in R.observations(rec)


def test_calibration_on_a_halted_run_has_no_realized_values_for_incomplete_passengers():
    rec, eng = run_record([(0, "a", 0, 4), (0, "b", 2, 4)], 5, 1, 1, max_ticks=3)
    assert eng.outcome.standing == "HALTED"
    rows = R.calibration(rec)
    assert [(r.realized_pickup, r.pickup_error, r.dropoff_error) for r in rows] == [(0, 0, None), (None, None, None)]
    assert R.calibration_summary(rows)["assignments"] == 2


# --- HALTED runs -------------------------------------------------------------------

def test_halted_run_outputs():
    # invalid proposal at tick 3: ticks 0 to 2 are committed, passenger a completed at t=2
    rec, eng = run_record([(0, "a", 0, 2), (3, "b", 1, 2)], 3, 1, 2, policy="round_robin",
                          policy_object=ByIdPolicy(mapping={1: 5}))
    assert (eng.outcome.standing, eng.outcome.halt_reason, eng.outcome.final_tick) == ("HALTED", "INVALID_PROPOSAL", 3)
    s = R.reproducible_surface(rec)
    assert s["summary.json"] == canonical_json({"standing": "HALTED", "final_tick": 3, "halt_reason": "INVALID_PROPOSAL",
                                                "n": 2, "completed": 1, "unserved": 1})
    assert s["observations.md"] == b"Run halted; no observation rules apply.\n"
    assert len(parse_csv(s["elevator_positions.csv"])) == 1 + 3  # header and ticks 0 to 2
    assert len(parse_csv(s["passengers.csv"])) == 1 + 1  # only the committed passenger
    ident = json.loads(s["run_identity.json"])["outcome"]
    assert ident == {"standing": "HALTED", "final_tick": 3, "halt_step": "ASSIGN", "halt_reason": "INVALID_PROPOSAL"}
    assert s["events.jsonl"].splitlines()[-1].startswith(b'{"elevator_id":null,"floor":null,"halt":{')


def test_halted_run_with_no_committed_ticks_and_incomplete_passengers():
    rec, _ = run_record([(0, "a", 0, 2)], 3, 1, 2, policy="round_robin", policy_object=ByIdPolicy(mapping={0: 9}))
    s = R.reproducible_surface(rec)
    assert s["elevator_positions.csv"] == b"t,elevator_0\n" and s["tick_records.jsonl"] == b""
    assert s["passengers.csv"].count(b"\n") == 1 and s["position_log_long.csv"].count(b"\n") == 1
    assert json.loads(s["summary.json"]) == {"standing": "HALTED", "final_tick": 0, "halt_reason": "INVALID_PROPOSAL",
                                             "n": 1, "completed": 0, "unserved": 1}
    # a horizon halt leaves a passenger onboard: its unrealized time cells are empty, never zero
    rec, eng = run_record([(0, "a", 0, 4)], 5, 1, 2, policy="round_robin", max_ticks=2)
    assert eng.outcome.halt_reason == "HORIZON_EXCEEDED"
    (row,) = parse_csv(R.reproducible_surface(rec)["passengers.csv"])[1:]
    assert row[7:12] == ["0", "", "0", "", ""] and row[14] == "ONBOARD"
    assert json.loads(R.reproducible_surface(rec)["summary.json"])["unserved"] == 1


# --- fail closed, no mutation, structure -------------------------------------------------

def test_contradictory_records_are_refused_not_repaired():
    rec, _ = run_record(W_B, 5, 1, 1)
    ev, ps = rec.history.events, rec.passengers
    tampered = {
        "missing alight": dataclasses.replace(rec, history=SimulationHistory(
            tuple(e for e in ev if not (e.kind is K.ALIGHTED and e.passenger_id == 1)), rec.history.tick_records)),
        "pickup field": dataclasses.replace(rec, passengers=(ps[0], dataclasses.replace(ps[1], pickup_time=5))),
        "request time": dataclasses.replace(rec, passengers=(dataclasses.replace(ps[0], request_time=1), ps[1])),
        "dropped passenger": dataclasses.replace(rec, passengers=(ps[0],)),
        "not final": dataclasses.replace(rec, history=SimulationHistory(ev[:-1], rec.history.tick_records)),
        "tick gap": dataclasses.replace(rec, history=SimulationHistory(
            ev, rec.history.tick_records[:3] + rec.history.tick_records[4:])),
        "other trace": dataclasses.replace(rec, trace=run_record(W_F, 5, 1, 1)[0].trace),
    }
    for name, bad in tampered.items():
        with pytest.raises(R.ReportError):
            R.reproducible_surface(bad)
    # the untouched record still reports
    R.reproducible_surface(rec)


def test_reporting_does_not_mutate_the_history():
    for policy in POLICIES:
        rec, eng = run_record(W_B, 5, 1, 1, policy=policy)
        before = (canonical_json(rec.history), rec.passengers)
        R.reproducible_surface(rec), R.summary(rec), R.observations(rec), R.calibration(rec)
        assert (canonical_json(rec.history), rec.passengers) == before
        assert eng.history == rec.history and eng.standing == "COMPLETED"


def test_reporting_module_structure():
    with open(os.path.join(ROOT, "elevator", "reporting.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            imported.add(n.module or "")
    # depends on domain, and on operations for the execution-output wrapper (architecture §1: reporting
    # depends on `domain; operations`), and on nothing else
    assert {m for m in imported if m.startswith("elevator")} == {"elevator.domain", "elevator.operations"}
    assert not imported & {"random", "time", "datetime", "subprocess", "socket", "secrets", "uuid", "sys"}
    # no second simulation: it never names the engine, a policy, the route functions or the projection
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree)
                                                                           if isinstance(n, ast.Attribute)}
    assert not names & {"Engine", "step", "run", "assign", "project", "next_heading", "departure_direction",
                        "eligible_boarders", "RoundRobin", "NearestCar", "CostBased"}
    # a fresh interpreter imports it without loading the engine, the route or the policies
    import subprocess
    out = subprocess.run([sys.executable, "-B", "-c",
                          "import sys, elevator.reporting; print(any(m in sys.modules for m in "
                          "('elevator.engine','elevator.route','elevator.policies','elevator.api')))"],
                         capture_output=True, text=True, cwd=ROOT, env={**os.environ, "PYTHONPATH": ROOT}, check=True)
    assert out.stdout.strip() == "False"


def test_write_files_never_overwrites_and_rejects_paths(tmp_path):
    rec, _ = run_record(W_B, 5, 1, 1)
    files = R.reproducible_surface(rec)
    target = str(tmp_path / "run" / "exec")
    R.write_files(target, files)
    assert {p.name for p in (tmp_path / "run" / "exec").iterdir()} == set(R.SURFACE_FILES)
    assert all((tmp_path / "run" / "exec" / k).read_bytes() == v for k, v in files.items())
    with pytest.raises(FileExistsError):
        R.write_files(target, files)
    with pytest.raises(ValueError):
        R.write_files(str(tmp_path / "x"), {"../evil": b"x"})
