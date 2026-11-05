"""Cut 6 reproducibility and reporting tests (testing_contract §6)."""

import ast
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from fractions import Fraction

from elevator import reporting as R
from tests.report_fixtures import run_record

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURE_DIR = os.path.join(ROOT, "tests", "fixtures", "reporting", "w_b_cost_based")
W_B = [(0, "p0", 0, 4), (0, "p1", 2, 4)]
W_F = [(0, "p0", 0, 4), (0, "p1", 2, 1)]
W_A = [(0, "p0", 0, 3)]


def test_numeric_rendering_pinned():
    # std of [0, 0, 1]: variance 2/9, sqrt(2/9) = 0.4714...: truncated root 0.471
    assert R.render_std([0, 0, 1]) == "0.471"
    # the root is truncated, not rounded: variance 27/16 for [0, 0, 0, 3] has root 1.29903...
    assert R.render_std([0, 0, 0, 3]) == "1.299"
    assert R.render_std([1, 2]) == "0.500" and R.render_std([5]) == "0.000" and R.render_std([0, 2]) == "1.000"
    # mean and median are exact rationals rendered with three digits
    assert R.render_rational(Fraction(1 + 2, 2)) == "1.500"
    assert R.distribution([1, 2])["mean"] == "1.500" and R.distribution([1, 2, 3, 10])["median"] == "2.500"
    assert R.distribution([7])["median"] == "7.000" and R.distribution([7])["std"] == "0.000"
    # p95 is nearest-rank for n = 1..20: the ceil(95 n / 100)-th smallest, never interpolated
    for n in range(1, 21):
        assert R.nearest_rank(list(range(1, n + 1)), 95) == math.ceil(Fraction(95 * n, 100))
    assert [R.nearest_rank(list(range(1, n + 1)), 95) for n in (1, 2, 19, 20)] == [1, 2, 19, 19]
    assert R.nearest_rank([3, 9, 27], 95) == 27 and R.distribution([0, 0, 0, 0, 100])["p95"] == 100
    # half away from zero at x.xxx5, decided on the exact rational
    cases = {Fraction(10005, 10000): "1.001", Fraction(10004, 10000): "1.000", Fraction(5, 10000): "0.001",
             Fraction(4, 10000): "0.000", Fraction(24995, 10000): "2.500", Fraction(1, 3): "0.333",
             Fraction(2, 3): "0.667", Fraction(0): "0.000", Fraction(7): "7.000", Fraction(1, 8): "0.125",
             Fraction(-10005, 10000): "-1.001", Fraction(-5, 10000): "-0.001", Fraction(-4, 10000): "0.000"}
    for q, text in cases.items():
        assert R.render_rational(q) == text, (q, text)
    # an exact tie to three digits: 0.0625 is not a tie (0.063 by half-up), 0.0005 is
    assert R.render_rational(Fraction(1, 16)) == "0.063" and R.render_rational(Fraction(1, 2000)) == "0.001"
    # no floating point anywhere in the module: no float literal, no float/round call, no libm function
    with open(os.path.join(ROOT, "elevator", "reporting.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, float)]
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree)
                                                                           if isinstance(n, ast.Attribute)}
    assert not names & {"float", "round", "sqrt", "ceil", "Decimal", "random"}  # (`floor` is the domain field)
    math_imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module == "math"
                    for a in n.names}
    assert math_imports == {"isqrt"} and not any(isinstance(n, ast.Import) and any(a.name == "math" for a in n.names)
                                                 for n in ast.walk(tree))


EMPTY_SUMMARY = (
    b'{"completed":0,"deferred":{"count":0},"elevator_utilisation":["0.000","0.000"],"final_tick":0,'
    b'"makespan":0,"n":0,"no_passengers":true,"standing":"COMPLETED","tail_ratio":null,"tail_share":null,'
    b'"total":{"max":null,"mean":null,"median":null,"min":null,"p95":null,"std":null},"travel":{"mean":null},'
    b'"unserved":0,"wait":{"max":null,"mean":null,"median":null,"min":null,"p95":null,"std":null},'
    b'"wrong_way":{"count":0,"mean_extra":null}}')


def test_empty_population_summary():
    rec, eng = run_record([], 4, 2, 3, initial=[1, 2], policy="round_robin")
    s = R.reproducible_surface(rec)
    assert s["summary.json"] == EMPTY_SUMMARY
    assert s["observations.md"] == b"No passengers; no observation rules apply.\n"
    summary = json.loads(s["summary.json"])
    assert all(v is None for v in summary["wait"].values()) and all(v is None for v in summary["total"].values())
    assert summary["tail_share"] is None and summary["tail_ratio"] is None and summary["travel"]["mean"] is None
    assert (summary["n"], summary["completed"], summary["unserved"], summary["deferred"]["count"],
            summary["wrong_way"]["count"]) == (0, 0, 0, 0, 0)
    # no division was performed: the other empty files are just the one record
    assert s["elevator_positions.csv"] == b"t,elevator_0,elevator_1\n0,1,2\n"
    assert s["passengers.csv"].count(b"\n") == 1  # header only


def test_empty_trace_completes_at_zero():
    # summary half (the engine half is in the cut-3 tests): one TickRecord, COMPLETED at t = 0
    rec, eng = run_record([], 4, 2, 3, policy="cost_based")
    assert (eng.outcome.standing, eng.outcome.final_tick, len(rec.history.tick_records)) == ("COMPLETED", 0, 1)
    s = R.reproducible_surface(rec)
    assert s["summary.json"] == EMPTY_SUMMARY
    assert s["observations.md"] == b"No passengers; no observation rules apply.\n"
    assert json.loads(s["run_identity.json"])["outcome"] == {"standing": "COMPLETED", "final_tick": 0,
                                                             "halt_step": None, "halt_reason": None}
    assert len(s["events.jsonl"].splitlines()) == 1 and len(s["tick_records.jsonl"].splitlines()) == 1


def test_zero_mean_tail_ratio_suppressed():
    rec, _ = run_record(W_A, 4, 1, 2, policy="round_robin")
    summary = json.loads(R.reproducible_surface(rec)["summary.json"])
    assert summary["wait"]["mean"] == "0.000" and summary["tail_ratio"] is None
    assert "Tail ratio" not in R.observations(rec)
    # the other rules still fire: rule 3 and rule 6 apply to any non-empty run
    assert "Longest wait" in R.observations(rec) and "Idle gap" in R.observations(rec)


def line(rec, prefix):
    return [ln for ln in R.observations(rec).split("\n") if ln.startswith(f"- {prefix}")]


def test_observations_preconditions():
    # rule 1: tail ratio needs mean wait > 0; flagged only above 2 (W-B is exactly 2.000: not flagged)
    rec, _ = run_record(W_B, 5, 1, 1, policy="round_robin")
    assert line(rec, "Tail ratio") == ["- Tail ratio (95th-percentile wait / mean wait): 2.000 (p95 6, mean 3.000)."]
    rec, _ = run_record([(0, "a", 0, 1), (0, "b", 0, 1), (0, "c", 4, 0)], 5, 1, 4, initial=[0], policy="round_robin")
    assert line(rec, "Tail ratio") == [
        "- Tail ratio (95th-percentile wait / mean wait): 3.000 (p95 4, mean 1.333). Flagged: above 2."]
    assert line(run_record(W_A, 4, 1, 2, policy="round_robin")[0], "Tail ratio") == []
    # rule 2: capacity deferrals only when deferred.count >= 1, with the floors
    assert line(run_record(W_B, 5, 1, 1, policy="round_robin")[0], "Capacity") == [
        "- Capacity deferrals: 1 passenger(s) were refused boarding for capacity at least once, at floor(s) 2."]
    assert line(run_record(W_F, 5, 1, 1, policy="round_robin")[0], "Capacity") == []
    # rule 3: the maximum-wait passenger, what its car was doing, ties to the lowest passenger_id
    assert line(run_record(W_B, 5, 1, 1, policy="round_robin")[0], "Longest wait") == [
        '- Longest wait: passenger 1 (source_id "p1") at floor 2, requested at t=0, assigned to elevator 0, '
        "waited 6 tick(s); when the request arrived elevator 0 was at floor 0 heading UP with load 1."]
    tie, _ = run_record([(0, "x", 0, 1), (0, "y", 3, 4)], 5, 2, 2, initial=[0, 0], policy="nearest_car")
    assert 'passenger 1 (source_id "y")' in line(tie, "Longest wait")[0]  # waits 0 and 3: the larger wins
    tie2, _ = run_record([(0, "a", 0, 1), (0, "b", 0, 2)], 5, 1, 2, policy="round_robin")
    assert 'passenger 0 (source_id "a")' in line(tie2, "Longest wait")[0]  # both wait 0: the lowest id
    # rule 4: wrong-way passes only when wrong_way.count >= 1
    assert line(run_record(W_F, 5, 1, 1, policy="round_robin")[0], "Wrong-way") == [
        "- Wrong-way passes: 1 passenger(s) were passed by their car going the other way first; "
        "mean extra wait 4.000 tick(s)."]
    assert line(run_record(W_B, 5, 1, 1, policy="round_robin")[0], "Wrong-way") == []
    # rule 5: utilisation imbalance needs N >= 2; flagged only above 1/2 (exactly 1/2 is not flagged)
    assert line(run_record(W_B, 5, 1, 1, policy="round_robin")[0], "Utilisation") == []
    edge, _ = run_record([(0, "r0", 2, 1), (1, "r1", 0, 1)], 5, 2, 2, initial=[0, 0], policy="round_robin")
    assert line(edge, "Utilisation") == ["- Utilisation imbalance: busiest elevator 0.750 minus least busy "
                                         "0.250 = 0.500."]
    flagged, _ = run_record([(0, "r0", 2, 0)], 5, 2, 2, initial=[0, 0], policy="round_robin")
    assert line(flagged, "Utilisation") == ["- Utilisation imbalance: busiest elevator 0.800 minus least busy "
                                            "0.000 = 0.800. Flagged: above 1/2."]
    # rule 6: idle gaps for any non-empty run
    assert line(run_record(W_B, 5, 1, 1, policy="round_robin")[0], "Idle gap") == [
        "- Idle gap: the longest run of ticks with every elevator idle is 1 tick(s), from t=8 to t=8."]
    gap, _ = run_record([(0, "a", 0, 1), (6, "b", 0, 1)], 3, 1, 2, policy="round_robin")
    assert line(gap, "Idle gap") == ["- Idle gap: the longest run of ticks with every elevator idle is 5 tick(s), "
                                     "from t=1 to t=5."]
    # rule 7: cost_based only; not for the baselines, not for an empty or halted run
    cost, _ = run_record(W_B, 5, 1, 1, policy="cost_based")
    assert line(cost, "Cost-based") == [
        "- Cost-based assignment: 1 of 2 used the Tier 2 fallback (0.500); calibration: 2 of 2 assignments were "
        "realized exactly as projected, pickup error min 0 max 0, dropoff error min 0 max 0."]
    for policy in ("round_robin", "nearest_car"):
        assert line(run_record(W_B, 5, 1, 1, policy=policy)[0], "Cost-based") == []
    # no rule fires for an empty run; a halted run has its own single line
    assert R.observations(run_record([], 4, 1, 1)[0]) == "No passengers; no observation rules apply.\n"
    halted, eng = run_record([(0, "a", 0, 4)], 5, 1, 2, policy="cost_based", max_ticks=2)
    assert eng.outcome.standing == "HALTED" and R.observations(halted) == "Run halted; no observation rules apply.\n"


FORBIDDEN = (b"execution_id", b"store_id", b"git", b"timestamp", b"scenario", b"pid", b"started_at", b"ended_at",
             b"worktree", b"provenance")


def test_reproducible_surface_excludes_execution_facts():
    for policy in ("round_robin", "nearest_car", "cost_based"):
        rec, _ = run_record(W_B + [(3, "p2", 4, 0)], 5, 2, 2, policy=policy)
        surface = R.reproducible_surface(rec)
        assert tuple(surface) == R.SURFACE_FILES
        for name, data in surface.items():
            assert not [w for w in FORBIDDEN if w in data.lower()], name
            assert not re.search(rb"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", data), name  # no timestamp
            assert not re.search(rb"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])", data), name  # no Git-SHA-shaped token
            assert b"a" * 40 not in data and b"b" * 40 not in data and b"exec-" not in data, name
        # the surface is a function of the Run alone: two Executions with different Git provenance
        # (a README-only commit between them) yield byte-identical surfaces, whatever metadata they wrote
        meta_a = R.execution_metadata(execution_id="exec-a", run_id=rec.identity.run_id, standing="COMPLETED",
                                      git_sha="a" * 40, worktree_standing="clean", pid=111,
                                      started_at="2026-11-05T10:00:00Z", ended_at="2026-11-05T10:00:01Z")
        again = R.reproducible_surface(rec)
        meta_b = R.execution_metadata(execution_id="exec-b", run_id=rec.identity.run_id, standing="COMPLETED",
                                      git_sha="b" * 40, worktree_standing="dirty", pid=222,
                                      started_at="2026-11-05T11:00:00Z", ended_at="2026-11-05T11:00:03Z",
                                      provenance={"pattern": "uniform", "seed": 7})
        assert again == surface and meta_a != meta_b
        # the execution facts live only in the metadata document, which is not a surface file
        doc = json.loads(meta_b)
        assert doc["execution_id"] == "exec-b" and doc["git_sha"] == "b" * 40 and doc["pid"] == 222
        assert doc["provenance"] == {"pattern": "uniform", "seed": 7} and doc["store_id"] is None
        assert "execution_metadata.json" not in R.SURFACE_FILES and "operational.jsonl" not in R.SURFACE_FILES
        assert meta_a == R.execution_metadata(execution_id="exec-a", run_id=rec.identity.run_id, standing="COMPLETED",
                                              git_sha="a" * 40, worktree_standing="clean", pid=111,
                                              started_at="2026-11-05T10:00:00Z", ended_at="2026-11-05T10:00:01Z")


def test_committed_fixture_outputs_are_byte_exact():
    """One committed fixture (W-B under cost_based) whose seven code-independent surface files
    are stored under tests/fixtures/reporting. run_identity.json carries the code identity, which
    changes with every edit to the package, so it is checked for shape instead."""
    rec, _ = run_record(W_B, 5, 1, 1, policy="cost_based")
    surface = R.reproducible_surface(rec)
    stored = sorted(os.listdir(FIXTURE_DIR))
    assert stored == sorted(set(R.SURFACE_FILES) - {"run_identity.json"})
    for name in stored:
        with open(os.path.join(FIXTURE_DIR, name), "rb") as fh:
            assert surface[name] == fh.read(), name
    ident = json.loads(surface["run_identity.json"])
    assert set(ident) == {"run_id", "configuration", "configuration_hash", "trace_hash", "policy", "code_identity",
                          "outcome"}
    assert ident["policy"] == {"name": "cost_based", "params": {"age_scale": 4, "tail_threshold": 8, "w_marginal": 1,
                                                                "w_tail": 3, "w_wait": 1}}
    assert ident["run_id"] == rec.identity.run_id and ident["configuration_hash"] == rec.configuration.configuration_hash


def test_surface_is_identical_across_processes_and_executions():
    script = (
        "import hashlib\n"
        "from tests.report_fixtures import run_record\n"
        "from elevator import reporting as R\n"
        "rec,_=run_record([(0,'a',0,5),(0,'b',4,1),(2,'c',3,0),(5,'d',1,5),(5,'e',5,2)],6,3,2,initial=[0,3,5],policy='cost_based')\n"
        "s=R.reproducible_surface(rec)\n"
        "print(hashlib.sha256(b''.join(s[k] for k in R.SURFACE_FILES)).hexdigest())\n")
    env = {**os.environ, "PYTHONPATH": ROOT}
    runs = [subprocess.run([sys.executable, "-B", "-c", script], capture_output=True, text=True, cwd=ROOT, env=env,
                           check=True).stdout.strip() for _ in range(2)]
    assert runs[0] == runs[1] and len(runs[0]) == 64
    rec, _ = run_record([(0, "a", 0, 5), (0, "b", 4, 1), (2, "c", 3, 0), (5, "d", 1, 5), (5, "e", 5, 2)], 6, 3, 2,
                        initial=[0, 3, 5], policy="cost_based")
    s = R.reproducible_surface(rec)
    assert hashlib.sha256(b"".join(s[k] for k in R.SURFACE_FILES)).hexdigest() == runs[0]
