"""Cut 7 reproducibility tests (testing_contract §6): the scenario generator."""

import ast
import hashlib
import json
import os
import random
import subprocess
import sys

import pytest

from elevator import scenarios as S
from elevator.domain import MAX_REQUEST_TIME
from elevator.scenarios import PATTERNS, Scenario, ScenarioRefusal, SplitMix64, generate

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURES = os.path.join(ROOT, "tests", "fixtures", "scenarios")
REASON = "INVALID_SCENARIO_PARAMETERS"

BASE = {"uniform": {"num_requests": 5, "horizon": 10}, "up_peak": {"num_requests": 5, "horizon": 10},
        "down_peak": {"num_requests": 5, "horizon": 10}, "bursty": {"num_requests": 5, "horizon": 10},
        "concentrated_origin": {"num_requests": 5, "horizon": 10},
        "concentrated_destination": {"num_requests": 5, "horizon": 10},
        "capacity_stress": {"num_requests": 5}, "sparse": {"num_requests": 5}, "adversarial": {"num_requests": 5}}


def build(pattern, params=None, *, F=6, N=1, C=1, seed=7):
    merged = dict(BASE[pattern]) if params is None else params
    return generate(Scenario(pattern, merged, seed), F, N, C)


def refused(pattern, params, names, *, F=6, N=1, C=1, seed=7):
    with pytest.raises(ScenarioRefusal) as info:
        build(pattern, params, F=F, N=N, C=C, seed=seed)
    assert info.value.reason == REASON and info.value.parameters == tuple(names), info.value
    assert all(n in str(info.value) for n in names)


def with_(pattern, **changes):
    params = dict(BASE[pattern])
    params.update(changes)
    return params


# --- the primitive ---------------------------------------------------------------------

def test_splitmix_reference_vector():
    with open(os.path.join(FIXTURES, "splitmix_vectors.json"), encoding="utf-8") as fh:
        vectors = json.load(fh)
    assert set(vectors) == {"0", str(2**64 - 1)}
    for seed, expected in vectors.items():
        rng = SplitMix64(int(seed))
        got = [f"{rng.next():016x}" for _ in range(16)]
        assert got == expected and len(got) == 16
    # anchors from outside this repository: the widely published first outputs for seed 0
    assert vectors["0"][:4] == ["e220a8397b1dcdaf", "6e789e6aa1b965f4", "06c45d188009454f", "f88bb8a8724c81ec"]
    # draw(k) = ((next() >> 11) * k) >> 53, in 0..k-1, and draw(1) still consumes one next()
    a, b = SplitMix64(7), SplitMix64(7)
    for k in (1, 2, 5, 6, 200, 10**6 + 1):
        assert a.draw(k) == ((b.next() >> 11) * k) >> 53 and 0 <= a.draw(k) < k
        b.next()
    one, two = SplitMix64(3), SplitMix64(3)
    one.draw(1)
    two.next()
    assert one.next() == two.next()
    for bad in (0, -1, 1.5, True, "3"):
        with pytest.raises(ValueError):
            SplitMix64(1).draw(bad)


def test_seed_domain_refused():
    for bad in (2**64, 2**64 + 1, -1, 2**70):
        with pytest.raises(ScenarioRefusal) as info:
            Scenario("adversarial", {"num_requests": 3}, bad)
        assert info.value.reason == REASON and info.value.parameters == ("seed",)
        with pytest.raises(ScenarioRefusal):
            SplitMix64(bad)
    for bad in (1.0, "7", None, True, b"7"):
        with pytest.raises(ScenarioRefusal):
            Scenario("adversarial", {"num_requests": 3}, bad)
    # the edges of the domain are accepted, and the two edge seeds name different Traces
    low = build("uniform", seed=0)
    high = build("uniform", seed=2**64 - 1)
    assert low.trace_hash != high.trace_hash and low.num_requests == high.num_requests == 5
    # a seed is never reduced: 2^64 does not alias 0
    with pytest.raises(ScenarioRefusal):
        build("uniform", seed=2**64)


# --- purity, committed expected Traces, fresh processes -------------------------------------

def test_generate_is_pure():
    twice = {}
    for pattern in PATTERNS:
        a, b = build(pattern, seed=11), build(pattern, seed=11)
        assert a == b and a.trace_hash == b.trace_hash and a.requests == b.requests
        assert build(pattern, seed=11).trace_hash == a.trace_hash
        twice[pattern] = a.trace_hash
    # the committed expected Trace per pattern for seed 7, produced by an independent C implementation
    # of the specification (tests/fixtures/scenarios/oracle.c), not by this generator
    with open(os.path.join(FIXTURES, "expected_traces_seed7.json"), encoding="utf-8") as fh:
        expected = json.load(fh)
    assert [e["pattern"] for e in expected] == list(PATTERNS)
    for e in expected:
        F, N, C = e["building"]
        trace = generate(Scenario(e["pattern"], e["parameters"], e["seed"]), F, N, C)
        assert trace.canonical_rows() == e["rows"], e["pattern"]
        assert trace.trace_hash == e["trace_hash"], e["pattern"]
        assert json.loads(json.dumps(trace.canonical_rows())) == e["rows"]


def test_generate_is_identical_across_processes_and_hash_seeds():
    script = (
        "import hashlib, json\n"
        "from elevator.scenarios import Scenario, generate, PATTERNS\n"
        "B={'uniform':{'num_requests':40,'horizon':30},'up_peak':{'num_requests':40,'horizon':30},"
        "'down_peak':{'num_requests':40,'horizon':30},'bursty':{'num_requests':40,'horizon':30},"
        "'concentrated_origin':{'num_requests':40,'horizon':30},'concentrated_destination':{'num_requests':40,'horizon':30},"
        "'capacity_stress':{'num_requests':40},'sparse':{'num_requests':40},'adversarial':{'num_requests':40}}\n"
        "out=[]\n"
        "for seed in (0,7,2**64-1,123456789):\n"
        "    for p in PATTERNS:\n"
        "        out.append(generate(Scenario(p,B[p],seed),9,2,3).trace_hash)\n"
        "print(hashlib.sha256(','.join(out).encode()).hexdigest())\n")
    results = []
    for hash_seed in ("0", "12345", "random"):
        env = {**os.environ, "PYTHONPATH": ROOT, "PYTHONHASHSEED": hash_seed}
        results.append(subprocess.run([sys.executable, "-B", "-c", script], capture_output=True, text=True,
                                      cwd=ROOT, env=env, check=True).stdout.strip())
    assert len(set(results)) == 1 and len(results[0]) == 64
    local = []
    for seed in (0, 7, 2**64 - 1, 123456789):
        for p in PATTERNS:
            params = {k: (40 if k == "num_requests" else 30) for k in PATTERNS[p] if k in ("num_requests", "horizon")}
            local.append(generate(Scenario(p, params, seed), 9, 2, 3).trace_hash)
    assert hashlib.sha256(",".join(local).encode()).hexdigest() == results[0]


def test_generation_uses_no_ambient_randomness():
    state = random.getstate()
    for pattern in PATTERNS:
        build(pattern, seed=5)
    assert random.getstate() == state  # the interpreter's global generator is untouched
    random.seed(1)
    first = build("uniform", {"num_requests": 20, "horizon": 50}, seed=9).trace_hash
    random.seed(99999)
    assert build("uniform", {"num_requests": 20, "horizon": 50}, seed=9).trace_hash == first
    with open(os.path.join(ROOT, "elevator", "scenarios.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert "random" not in imported and not imported & {"time", "datetime", "os", "secrets", "uuid", "hashlib"}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert not names & {"hash", "id", "set", "frozenset", "float", "random", "time"}  # no hash-ordered or float paths


# --- refusals ---------------------------------------------------------------------------

def test_generate_refuses_invalid_parameters():
    F = 6
    # every parameter at each edge and one past it
    edges = {  # parameter: (patterns naming it, lowest valid, below it, highest valid, past it)
        "num_requests": (list(PATTERNS), 0, -1, 100000, 100001),
        "horizon": ([p for p in PATTERNS if "horizon" in PATTERNS[p]], 0, -1, 10**6, 10**6 + 1),
        "k": (["bursty"], 1, 0, 1000, 1001),
        "w": (["bursty"], 1, 0, 10**6, 10**6 + 1),
        "m": (["concentrated_origin", "concentrated_destination"], 1, 0, F, F + 1),
        "origin": (["capacity_stress"], 0, -1, F - 1, F),
        "g": (["sparse"], 1, 0, 10**6, 10**6 + 1),
        "j": (["sparse"], 0, -1, None, None),  # j's upper edge depends on g: below
    }
    cheap_top = {"num_requests": ("uniform", "adversarial", "capacity_stress")}
    for name, (patterns, lo, below, hi, past) in edges.items():
        for pattern in patterns:
            extra = {"num_requests": 3} if name == "num_requests" else {}
            if pattern == "sparse" and name == "g":
                extra = {"num_requests": 3}
            low_params = with_(pattern, **{name: lo}) if pattern != "capacity_stress" or name != "num_requests" \
                else {"num_requests": 2}
            assert build(pattern, low_params, F=F, N=1, C=1).num_requests == low_params["num_requests"]
            refused(pattern, with_(pattern, **{name: below}), (name,), F=F)
            if hi is not None and not (name == "num_requests" and pattern not in cheap_top[name]):
                top_params = with_(pattern, **{name: hi})
                if name == "g":
                    top_params["num_requests"] = 3
                assert build(pattern, top_params, F=F).num_requests == top_params["num_requests"]
            if past is not None:
                refused(pattern, with_(pattern, **{name: past}), (name,), F=F)
    # j: g - 1 accepted, g refused; also against the F-dependent default g = 2 * (F - 1)
    assert build("sparse", {"num_requests": 4, "g": 7, "j": 6}).num_requests == 4
    refused("sparse", {"num_requests": 4, "g": 7, "j": 7}, ("j",))
    assert build("sparse", {"num_requests": 4, "j": 2 * (F - 1) - 1}, F=F).num_requests == 4
    refused("sparse", {"num_requests": 4, "j": 2 * (F - 1)}, ("j",), F=F)
    # m <= F and origin < F are building-dependent: the same value is valid in a larger building
    assert build("concentrated_origin", {"num_requests": 4, "horizon": 9, "m": 7}, F=7).num_requests == 4
    refused("concentrated_origin", {"num_requests": 4, "horizon": 9, "m": 7}, ("m",), F=6)
    assert build("capacity_stress", {"num_requests": 4, "origin": 6}, F=7).num_requests == 4
    refused("capacity_stress", {"num_requests": 4, "origin": 6}, ("origin",), F=6)
    # capacity stress needs num_requests > N * C
    for n, ok in ((5, False), (6, False), (7, True), (3, False), (0, False)):
        if ok:
            assert build("capacity_stress", {"num_requests": n}, N=2, C=3).num_requests == n
        else:
            refused("capacity_stress", {"num_requests": n}, ("num_requests",), N=2, C=3)
    # the full edges for the cheap patterns: 100000 accepted
    for pattern in ("uniform", "adversarial"):
        assert build(pattern, with_(pattern, num_requests=100000)).num_requests == 100000
    # an unknown parameter for any pattern, a parameter a pattern does not name, p_lobby at all
    for pattern in PATTERNS:
        refused(pattern, {**BASE[pattern], "bogus": 1}, ("bogus",))
        for other in ("horizon", "k", "w", "m", "origin", "g", "j"):
            if other not in PATTERNS[pattern]:
                refused(pattern, {**BASE[pattern], other: 1}, (other,))
    for pattern in ("up_peak", "down_peak"):
        refused(pattern, {**BASE[pattern], "p_lobby": 4}, ("p_lobby",))
        refused(pattern, {**BASE[pattern], "p_lobby": 0}, ("p_lobby",))
    # a missing required parameter, a wrong type, an unknown pattern
    refused("uniform", {"horizon": 5}, ("num_requests",))
    refused("uniform", {"num_requests": 5}, ("horizon",))
    for bad in (2.0, "5", True, None, [5]):
        refused("uniform", {"num_requests": bad, "horizon": 5}, ("num_requests",))
    with pytest.raises(ScenarioRefusal) as info:
        Scenario("poisson", {"num_requests": 1}, 0)
    assert info.value.parameters == ("pattern",) and info.value.reason == REASON
    # the building must be in the configuration domain of evaluation §2
    from elevator.domain import Refusal
    for floors, elevators, cap in ((1, 1, 1), (201, 1, 1), (6, 0, 1), (6, 21, 1), (6, 1, 0), (6, 1, 51)):
        with pytest.raises(Refusal) as info2:
            generate(Scenario("adversarial", {"num_requests": 2}, 0), floors, elevators, cap)
        assert info2.value.reason == "INVALID_CONFIGURATION"


def test_sparse_cross_parameter_refused():
    refused("sparse", {"num_requests": 1002, "g": 10**6, "j": 0}, ("num_requests", "g", "j"))
    refused("sparse", {"num_requests": 1001, "g": 10**6, "j": 1}, ("num_requests", "g", "j"))
    # n = 100000: g = 10000 puts the last time at 999,990,000 (accepted); g = 10001 at 1,000,089,999 (refused)
    assert build("sparse", {"num_requests": 100000, "g": 10**4, "j": 0}).last_request_time == 999_990_000
    refused("sparse", {"num_requests": 100000, "g": 10001, "j": 0}, ("num_requests", "g", "j"))
    # refused before any draw: with the primitive disabled the refusal is still the cross-parameter one
    original = SplitMix64.next

    def boom(self):
        raise AssertionError("a draw happened before the refusal")

    SplitMix64.next = boom
    try:
        refused("sparse", {"num_requests": 1002, "g": 10**6, "j": 0}, ("num_requests", "g", "j"))
    finally:
        SplitMix64.next = original
    # the boundary is accepted: the last time is exactly 10^9, never clipped, the count never reduced
    edge = build("sparse", {"num_requests": 1001, "g": 10**6, "j": 0})
    assert edge.num_requests == 1001 and edge.last_request_time == MAX_REQUEST_TIME == 10**9
    assert [r.request_time for r in edge.requests][:3] == [0, 10**6, 2 * 10**6]
    # the emitted-time guard never fires on any accepted default scenario
    for F in (2, 3, 6, 50, 200):
        for n in (0, 1, 7, 200):
            t = generate(Scenario("sparse", {"num_requests": n}, 3), F, 1, 1)
            assert t.num_requests == n and (n == 0 or t.last_request_time <= (n - 1) * 2 * (F - 1) + 0)
    assert S._REDRAW_CAP >= 10_000  # the redraw guard is a never-fires bound, not a behavioural limit
