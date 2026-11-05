"""The scenario generator (plan cut 7; evaluation_design §6).

A Scenario is ``(pattern, parameters, seed)`` and ``generate(scenario, F, N, C)``
is a pure function of its arguments that returns a ``Trace``. The generator
is specified exactly so that two implementations produce the same Trace, and
uses no language or library random facility: the primitive is SplitMix64 on
unsigned 64-bit arithmetic (§6.1), one explicit instance per ``generate``
call, so there is no module-level, ambient or OS-entropy randomness and the
interpreter's own ``random`` module is never imported (architecture §1).

Scenario generation is exogenous input construction. It builds a whole Trace
before any simulation, which does not let a scheduler see future demand: the
engine still reveals requests tick by tick, and nothing here is reachable from
a policy, a ``SchedulerView`` or a Request. This module imports only ``domain``.

Authority: the Scenario (``pattern``, ``parameters``, ``seed``) is authority
row 30/31 and belongs to the harness (cut 8); the generated Trace is DERIVED
from it. The generator state is EPHEMERAL inside one ``generate`` call.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from elevator.domain import (
    MAX_REQUEST_ROWS,
    MAX_REQUEST_TIME,
    Configuration,
    Refusal,
    Trace,
    normalize_requests,
)

INVALID_SCENARIO_PARAMETERS = "INVALID_SCENARIO_PARAMETERS"

MAX_SEED = 2**64
_MASK = MAX_SEED - 1
_GAMMA = 0x9E3779B97F4A7C15
_MIX1 = 0xBF58476D1CE4E5B9
_MIX2 = 0x94D049BB133111EB

#: Upper bound on consecutive redraws of an endpoint. ``draw(F)`` reaches every floor and ``F >= 2``,
#: so a run of this length is a probability-zero event; the cap turns a would-be infinite loop into
#: an error (a guard that must never fire).
_REDRAW_CAP = 100_000

#: The pattern table (§6.3): each pattern's parameters and their defaults. ``None`` marks a required
#: parameter; ``"g"`` has a default that depends on F and is resolved in ``resolve_parameters``.
PATTERNS: Mapping[str, Mapping[str, int | None]] = MappingProxyType({
    "uniform": MappingProxyType({"num_requests": None, "horizon": None}),
    "up_peak": MappingProxyType({"num_requests": None, "horizon": None}),
    "down_peak": MappingProxyType({"num_requests": None, "horizon": None}),
    "bursty": MappingProxyType({"num_requests": None, "horizon": None, "k": 3, "w": 3}),
    "concentrated_origin": MappingProxyType({"num_requests": None, "horizon": None, "m": 2}),
    "concentrated_destination": MappingProxyType({"num_requests": None, "horizon": None, "m": 2}),
    "capacity_stress": MappingProxyType({"num_requests": None, "origin": 0}),
    "sparse": MappingProxyType({"num_requests": None, "g": None, "j": 0}),
    "adversarial": MappingProxyType({"num_requests": None}),
})

#: Parameters whose F-independent domain is checked when a Scenario is built (§6.2): inclusive bounds.
_STATIC_DOMAINS = {"num_requests": (0, MAX_REQUEST_ROWS), "horizon": (0, 10**6), "k": (1, 1000),
                   "w": (1, 10**6), "m": (1, None), "origin": (0, None), "g": (1, 10**6), "j": (0, None)}


class ScenarioRefusal(Refusal):
    """``INVALID_SCENARIO_PARAMETERS``, naming the offending parameter(s) in ``parameters``
    (evaluation §6.2). Nothing is clipped, coerced or adjusted."""

    def __init__(self, parameters: tuple[str, ...], detail: str) -> None:
        self.parameters = parameters
        super().__init__(INVALID_SCENARIO_PARAMETERS, f"{', '.join(parameters)}: {detail}")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


# ---------------------------------------------------------------------------
# The generator primitive (§6.1)
# ---------------------------------------------------------------------------

class SplitMix64:
    """SplitMix64 on unsigned 64-bit arithmetic. The seed must be an integer with
    ``0 <= seed < 2^64``; anything else is refused rather than reduced, so two seeds never name
    one state. State is the instance's only field: one instance serves one ``generate`` call."""

    __slots__ = ("_state",)

    def __init__(self, seed: int) -> None:
        if not _is_int(seed) or not (0 <= seed < MAX_SEED):
            raise ScenarioRefusal(("seed",), f"must be an integer with 0 <= seed < 2^64, got {seed!r}")
        self._state = seed

    def next(self) -> int:
        self._state = (self._state + _GAMMA) & _MASK
        z = self._state
        z = ((z ^ (z >> 30)) * _MIX1) & _MASK
        z = ((z ^ (z >> 27)) * _MIX2) & _MASK
        return z ^ (z >> 31)

    def draw(self, k: int) -> int:
        """An integer in ``0..k-1`` (``k >= 1``): ``((next() >> 11) * k) >> 53``."""
        if not _is_int(k) or k < 1:
            raise ValueError(f"draw needs an integer k >= 1, got {k!r}")
        return ((self.next() >> 11) * k) >> 53


# ---------------------------------------------------------------------------
# The Scenario value
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Scenario:
    """``(pattern, parameters, seed)``, immutable: ``parameters`` is copied into a read-only
    mapping, so a caller's dictionary cannot change a Scenario (or its generated Trace) afterwards.
    Everything that does not depend on the building is validated here; the building-dependent
    rules (``m <= F``, ``origin < F``, the capacity-stress count, ``j < g``, the sparse
    cross-parameter precondition) are checked by ``generate``."""

    pattern: str
    parameters: Mapping[str, int]
    seed: int

    def __post_init__(self) -> None:
        if not isinstance(self.pattern, str) or self.pattern not in PATTERNS:
            raise ScenarioRefusal(("pattern",), f"unknown pattern {self.pattern!r}; one of {sorted(PATTERNS)}")
        if not isinstance(self.parameters, Mapping) or not all(isinstance(k, str) for k in self.parameters):
            raise ScenarioRefusal(("parameters",), "must be a mapping with string names")
        spec = PATTERNS[self.pattern]
        for name in sorted(self.parameters):
            if name not in spec:  # a pattern refuses a parameter it does not name (p_lobby, horizon on sparse...)
                raise ScenarioRefusal((name,), f"is not a parameter of pattern {self.pattern}")
        SplitMix64(self.seed)  # validates the seed domain
        frozen = {}
        for name in spec:
            if name in self.parameters:
                value = self.parameters[name]
                if not _is_int(value):
                    raise ScenarioRefusal((name,), f"must be an integer, got {value!r}")
                lo, hi = _STATIC_DOMAINS[name]
                if value < lo or (hi is not None and value > hi):
                    raise ScenarioRefusal((name,), f"{value} is outside its domain "
                                                   f"{lo}..{'F-dependent' if hi is None else hi}")
                frozen[name] = value
            elif spec[name] is None and name != "g":
                raise ScenarioRefusal((name,), "is required")
        object.__setattr__(self, "parameters", MappingProxyType(dict(sorted(frozen.items()))))


def resolve_parameters(scenario: Scenario, num_floors: int) -> dict[str, int]:
    """The effective parameters for a building of ``num_floors`` floors: supplied values and
    defaults, in the pattern's order (``g`` defaults to ``2 * (F - 1)``). Checks the building-dependent
    domains. This is the ``parameters`` of a Run's provenance."""
    spec = PATTERNS[scenario.pattern]
    out: dict[str, int] = {}
    for name, default in spec.items():
        if name in scenario.parameters:
            out[name] = scenario.parameters[name]
        elif name == "g":
            out[name] = 2 * (num_floors - 1)
        else:
            out[name] = default
    if "m" in out and out["m"] > num_floors:
        raise ScenarioRefusal(("m",), f"{out['m']} exceeds the number of floors {num_floors}")
    if "origin" in out and out["origin"] >= num_floors:
        raise ScenarioRefusal(("origin",), f"{out['origin']} is not a floor of a {num_floors}-floor building")
    if "j" in out and out["j"] >= out["g"]:
        raise ScenarioRefusal(("j",), f"{out['j']} must be below g = {out['g']}")
    return out


def provenance(scenario: Scenario, num_floors: int) -> dict[str, Any]:
    """``{pattern, parameters, seed}`` with the effective parameters (authority row 31): a DERIVED
    label for a Run of the generated Trace, never a Run input."""
    return {"pattern": scenario.pattern, "parameters": resolve_parameters(scenario, num_floors),
            "seed": scenario.seed}


# ---------------------------------------------------------------------------
# Patterns (§6.3): each yields (time, origin, dest) in generation order, consuming draws in the stated order
# ---------------------------------------------------------------------------

def _differing(rng: SplitMix64, floors: int, other: int) -> int:
    """``draw(F)`` redrawn while it equals ``other`` (each redraw consumes one ``draw(F)``)."""
    for _ in range(_REDRAW_CAP):
        x = rng.draw(floors)
        if x != other:
            return x
    raise RuntimeError("endpoint redraw cap reached: impossible for F >= 2")


def _uniform_floors(rng: SplitMix64, floors: int) -> tuple[int, int]:
    origin = rng.draw(floors)
    return origin, _differing(rng, floors, origin)


def _distinct_set(rng: SplitMix64, floors: int, size: int) -> list[int]:
    """Repeated ``draw(F)``, appending each floor not already present, until ``size`` members."""
    members: list[int] = []
    while len(members) < size:
        x = rng.draw(floors)
        if x not in members:
            members.append(x)
    return members


def _rows(pattern: str, rng: SplitMix64, floors: int, p: Mapping[str, int]) -> list[tuple[int, int, int]]:
    n = p["num_requests"]
    rows: list[tuple[int, int, int]] = []
    if pattern == "uniform":
        for _ in range(n):
            t = rng.draw(p["horizon"] + 1)
            rows.append((t, *_uniform_floors(rng, floors)))
    elif pattern in ("up_peak", "down_peak"):
        for _ in range(n):
            t = rng.draw(p["horizon"] + 1)
            lobby = rng.draw(5) < 4  # the fixed 4/5 lobby share
            if lobby:
                other = 1 + rng.draw(floors - 1)
                rows.append((t, 0, other) if pattern == "up_peak" else (t, other, 0))
            else:
                rows.append((t, *_uniform_floors(rng, floors)))
    elif pattern == "bursty":
        centres = [rng.draw(p["horizon"] + 1) for _ in range(p["k"])]
        for _ in range(n):
            j = rng.draw(p["k"])
            offset = rng.draw(p["w"])
            t = min(max(centres[j] + offset - p["w"] // 2, 0), p["horizon"])  # clamp, not redraw
            rows.append((t, *_uniform_floors(rng, floors)))
    elif pattern == "concentrated_origin":
        members = _distinct_set(rng, floors, p["m"])
        for _ in range(n):
            t = rng.draw(p["horizon"] + 1)
            origin = members[rng.draw(p["m"])]
            rows.append((t, origin, _differing(rng, floors, origin)))
    elif pattern == "concentrated_destination":
        members = _distinct_set(rng, floors, p["m"])
        for _ in range(n):
            t = rng.draw(p["horizon"] + 1)
            dest = members[rng.draw(p["m"])]
            rows.append((t, _differing(rng, floors, dest), dest))
    elif pattern == "capacity_stress":
        for _ in range(n):
            rows.append((0, p["origin"], _differing(rng, floors, p["origin"])))  # no draw for the time
    elif pattern == "sparse":
        for i in range(n):
            t = i * p["g"] + rng.draw(p["j"] + 1)
            rows.append((t, *_uniform_floors(rng, floors)))
    else:  # adversarial: no draws
        for i in range(n):
            rows.append((i, 0, floors - 1) if i % 2 == 0 else (i, floors - 1, 0))
    return rows


def generate(scenario: Scenario, num_floors: int, num_elevators: int, capacity: int) -> Trace:
    """The Trace of a Scenario for a building. Pure: the same arguments give the same Trace, in
    this process or any other. Requests are generated in index order ``i = 0..num_requests-1``;
    ``source_id`` is ``"g" + str(i)``; the Trace is the stable sort by ``(time, i)`` (the shared
    input boundary, ``normalize_requests``, which also validates every row). The Trace carries no
    scenario metadata and the generated rows are immutable domain values, so one Trace can serve
    every policy of an evaluation."""
    Configuration.create(num_floors, num_elevators, capacity)  # the configuration domain of evaluation §2
    p = resolve_parameters(scenario, num_floors)
    if scenario.pattern == "capacity_stress" and p["num_requests"] <= num_elevators * capacity:
        raise ScenarioRefusal(("num_requests",), f"{p['num_requests']} must exceed N * C = "
                                                 f"{num_elevators * capacity} for capacity_stress")
    if scenario.pattern == "sparse" and p["num_requests"] >= 1 \
            and (p["num_requests"] - 1) * p["g"] + p["j"] > MAX_REQUEST_TIME:
        raise ScenarioRefusal(("num_requests", "g", "j"),
                              f"the largest request time {(p['num_requests'] - 1) * p['g'] + p['j']} "
                              f"exceeds {MAX_REQUEST_TIME}")  # before any draw
    rng = SplitMix64(scenario.seed)
    rows = _rows(scenario.pattern, rng, num_floors, p)
    for when, _origin, _dest in rows:  # the emitted-time guard: it must never fire
        if when > MAX_REQUEST_TIME:
            raise RuntimeError(f"generated request time {when} exceeds {MAX_REQUEST_TIME}")
    return normalize_requests([(t, f"g{i}", o, d) for i, (t, o, d) in enumerate(rows)], num_floors)
