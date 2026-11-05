"""Reporting: derived outputs over a finished Run (plan cut 6).

Realises evaluation_design §3 (the Reproducible Output Surface and the
execution evidence split), §4 (metrics and the pinned numeric rendering), §5
(rule-generated observations), scheduler_design §9 (calibration) and
authority rows 22, 35, 39 and 40.

Everything here is DERIVED or a RECEIPT and owns no simulation fact. The input
is a ``RunRecord``: the Configuration, the Trace, the Run identity, the
Simulation History and the final Passenger records, all domain values. This
module never runs, steps or re-simulates anything, never calls a scheduler
or the route functions, and never reads a clock, a random source or the
environment; every figure comes from the recorded History, and every
contradiction between the History and the Passenger records is a
``ReportError`` (fail closed, nothing repaired). All arithmetic is exact
(integers and ``Fraction``); no floating point is used (evaluation §4.2).

Rendering conventions the governing text leaves open (recorded in the cut-6
record): CSV and markdown lines end in ``\\n``; JSON documents are canonical
bytes with no trailing newline; ``.jsonl`` files are one canonical object per
line.
"""

from __future__ import annotations

import csv
import io
import json
import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from math import isqrt
from typing import Any

from elevator.domain import (
    Configuration,
    Heading,
    Passenger,
    RunIdentity,
    SimulationEvent,
    SimulationEventKind as K,
    SimulationHistory,
    Standing,
    TickRecord,
    Trace,
    canonical_json,
)
from elevator.operations import Execution

SURFACE_FILES = ("elevator_positions.csv", "position_log_long.csv", "passengers.csv", "summary.json",
                 "observations.md", "run_identity.json", "events.jsonl", "tick_records.jsonl")

NO_PASSENGERS_LINE = "No passengers; no observation rules apply.\n"
HALTED_LINE = "Run halted; no observation rules apply.\n"


class ReportError(Exception):
    """The recorded History, the Passenger records and the Trace contradict
    each other, or the History is malformed. Reporting never repairs or
    guesses: it refuses."""


@dataclass(frozen=True)
class RunRecord:
    """Everything reporting reads, all domain values: the Run's inputs, its
    identity, its Simulation History and its final Passenger records."""

    configuration: Configuration
    trace: Trace
    identity: RunIdentity
    history: SimulationHistory
    passengers: tuple[Passenger, ...]


# ---------------------------------------------------------------------------
# Pinned numeric rendering (evaluation §4.2): exact, no floating point
# ---------------------------------------------------------------------------

def render_rational(q: Fraction) -> str:
    """Three fractional digits, half away from zero, on the exact rational:
    ``sign * ((|q| * 1000 * 2 + 1) // 2) / 1000`` evaluated in integers."""
    scaled = int((Fraction(2000) * abs(q) + 1) // 2)
    signed = -scaled if q < 0 else scaled
    text = f"{abs(signed) // 1000}.{abs(signed) % 1000:03d}"
    return f"-{text}" if signed < 0 else text


def nearest_rank(sorted_values: Sequence[int], percent: int) -> int:
    """Nearest-rank percentile: the ``ceil(percent * n / 100)``-th smallest
    value, in integers; never interpolated."""
    n = len(sorted_values)
    return sorted_values[(percent * n + 99) // 100 - 1]


def median(sorted_values: Sequence[int]) -> Fraction:
    n = len(sorted_values)
    if n % 2:
        return Fraction(sorted_values[n // 2])
    return Fraction(sorted_values[n // 2 - 1] + sorted_values[n // 2], 2)


def render_std(values: Sequence[int]) -> str:
    """Population standard deviation: exact variance
    ``(sum x^2)/n - (sum x / n)^2``, then ``isqrt`` of the variance scaled by
    10^6 (truncation of the exact root), rendered with three digits."""
    n = len(values)
    v = Fraction(sum(x * x for x in values), n) - Fraction(sum(values), n) ** 2
    milli = isqrt((v.numerator * 10**6) // v.denominator)
    return f"{milli // 1000}.{milli % 1000:03d}"


def distribution(values: Sequence[int]) -> dict[str, Any]:
    ordered = sorted(values)
    n = len(ordered)
    return {"min": ordered[0], "max": ordered[-1], "mean": render_rational(Fraction(sum(ordered), n)),
            "median": render_rational(median(ordered)), "p95": nearest_rank(ordered, 95),
            "std": render_std(ordered)}


NULL_DISTRIBUTION = {"min": None, "max": None, "mean": None, "median": None, "p95": None, "std": None}


# ---------------------------------------------------------------------------
# Reading the History: one verified analysis shared by every output
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _PassengerFacts:
    passenger: Passenger
    capacity_deferrals: int
    wrong_way_passes: int
    first_wrong_way_tick: int | None
    wait_time: int | None
    travel_time: int | None
    total_time: int | None
    receipt: Mapping[str, Any] | None
    assigned_seq: int


@dataclass(frozen=True)
class _Analysis:
    record: RunRecord
    ticks: tuple[TickRecord, ...]
    standing: str                       # "COMPLETED" or "HALTED"
    final_tick: int
    halt: Mapping[str, Any] | None
    facts: tuple[_PassengerFacts, ...]  # ascending passenger_id
    assigned: tuple[SimulationEvent, ...]


def _direction_up(p: Passenger) -> bool:
    return p.destination > p.origin


def _analyse(record: RunRecord) -> _Analysis:
    cfg, trace, history = record.configuration, record.trace, record.history
    ident = record.identity
    if ident.configuration_hash != cfg.configuration_hash or ident.trace_hash != trace.trace_hash:
        raise ReportError("run identity does not match its Configuration and Trace")
    n_elev = cfg.num_elevators
    ticks = history.tick_records
    for i, tr in enumerate(ticks):
        if tr.tick != i or [e.elevator_id for e in tr.entries] != list(range(n_elev)):
            raise ReportError(f"TickRecord {i} is out of order or has the wrong elevators")
    events = history.events
    if [e.seq for e in events] != list(range(len(events))):
        raise ReportError("event sequence numbers are not 0..n-1")
    if not events or events[-1].kind not in (K.COMPLETED, K.HALTED):
        raise ReportError("the History does not end in a run-standing event: the Run is not final")
    final_event = events[-1]
    if any(e.kind in (K.COMPLETED, K.HALTED) for e in events[:-1]):
        raise ReportError("a run-standing event is not the last event")
    if final_event.kind is K.COMPLETED:
        standing, halt = "COMPLETED", None
        if final_event.tick != len(ticks) - 1:
            raise ReportError("COMPLETED tick does not match the last TickRecord")
    else:
        standing, halt = "HALTED", final_event.halt
        if halt is None or final_event.tick != len(ticks):
            raise ReportError("HALTED event is malformed or not directly after the completed ticks")
    final_tick = final_event.tick

    # join assignment, boarding and alighting by passenger id
    revealed: dict[int, int] = {}
    assigned: dict[int, SimulationEvent] = {}
    boarded: dict[int, SimulationEvent] = {}
    alighted: dict[int, SimulationEvent] = {}
    for e in events:
        pid = e.passenger_id
        if e.kind is K.REVEALED:
            if pid in revealed:
                raise ReportError(f"passenger {pid} revealed twice")
            revealed[pid] = e.tick
        elif e.kind is K.ASSIGNED:
            if pid in assigned or pid not in revealed:
                raise ReportError(f"passenger {pid} assigned twice or before reveal")
            assigned[pid] = e
        elif e.kind is K.BOARDED:
            if pid in boarded or pid not in assigned:
                raise ReportError(f"passenger {pid} boarded twice or unassigned")
            boarded[pid] = e
        elif e.kind is K.ALIGHTED:
            if pid in alighted or pid not in boarded:
                raise ReportError(f"passenger {pid} alighted twice or never boarded")
            alighted[pid] = e
    passengers = tuple(sorted(record.passengers, key=lambda p: p.passenger_id))
    if [p.passenger_id for p in passengers] != sorted(assigned):
        raise ReportError("Passenger records and ASSIGNED events cover different passengers")
    requests = trace.requests
    facts: list[_PassengerFacts] = []
    for p in passengers:
        r = requests[p.passenger_id]
        if (p.source_id, p.request_time, p.origin, p.destination) != (r.source_id, r.request_time,
                                                                      r.origin, r.destination):
            raise ReportError(f"passenger {p.passenger_id} contradicts the Trace")
        a, b, c = assigned[p.passenger_id], boarded.get(p.passenger_id), alighted.get(p.passenger_id)
        if (p.assigned_elevator, p.assigned_at) != (a.elevator_id, a.tick) or a.tick != r.request_time:
            raise ReportError(f"passenger {p.passenger_id}: assignment contradicts its event")
        if (p.pickup_time, p.dropoff_time) != (None if b is None else b.tick, None if c is None else c.tick):
            raise ReportError(f"passenger {p.passenger_id}: pickup or dropoff contradicts its events")
        if b is not None and (b.elevator_id, b.floor) != (a.elevator_id, p.origin):
            raise ReportError(f"passenger {p.passenger_id}: boarded the wrong car or floor")
        if c is not None and (c.elevator_id, c.floor) != (a.elevator_id, p.destination):
            raise ReportError(f"passenger {p.passenger_id}: alighted the wrong car or floor")
        want = Standing.COMPLETED if c else Standing.ONBOARD if b else Standing.WAITING
        if p.standing is not want:
            raise ReportError(f"passenger {p.passenger_id}: standing contradicts its events")
        facts.append(_deferral_facts(p, a, ticks, cfg.capacity))
    completed = sum(1 for p in passengers if p.standing is Standing.COMPLETED)
    if standing == "COMPLETED":
        if len(passengers) != trace.num_requests or completed != len(passengers):
            raise ReportError("a COMPLETED run must have every Request completed")
    elif halt.get("unserved") != trace.num_requests - completed:
        raise ReportError("HALTED unserved count contradicts the Passenger records")
    return _Analysis(record, ticks, standing, final_tick, halt, tuple(facts),
                     tuple(assigned[pid] for pid in sorted(assigned)))


def _deferral_facts(p: Passenger, a: SimulationEvent, ticks: tuple[TickRecord, ...],
                    capacity: int) -> _PassengerFacts:
    """Realized capacity deferrals and wrong-way passes of one passenger, from the
    TickRecords under the single classification rule of semantics §4.2: direction
    decides first. At a tick where the passenger waits and its car is at its origin,
    the recorded heading is the departure direction (a car with anyone onboard is
    never FREE, and a FREE car with anyone waiting boards), so an opposite heading is
    a wrong-way pass and a compatible heading with the passenger still waiting is a
    capacity deferral (the car must then be full)."""
    last_wait = (p.pickup_time - 1) if p.pickup_time is not None else len(ticks) - 1
    cap = wrong = 0
    first_wrong: int | None = None
    for t in range(p.assigned_at, min(last_wait, len(ticks) - 1) + 1):
        entry = ticks[t].entries[p.assigned_elevator]
        if entry.floor != p.origin:
            continue
        if entry.heading is Heading.NONE:
            raise ReportError(f"passenger {p.passenger_id} left waiting at an idle car at t={t}")
        if (entry.heading is Heading.UP) == _direction_up(p):
            if entry.load != capacity:
                raise ReportError(f"passenger {p.passenger_id} not boarded at t={t} with room and a "
                                  "compatible heading")
            cap += 1
        else:
            wrong += 1
            first_wrong = t if first_wrong is None else first_wrong
    wait = None if p.pickup_time is None else p.pickup_time - p.request_time
    travel = None if p.dropoff_time is None else p.dropoff_time - p.pickup_time
    total = None if p.dropoff_time is None else p.dropoff_time - p.request_time
    return _PassengerFacts(p, cap, wrong, first_wrong, wait, travel, total, a.receipt, a.seq)


# ---------------------------------------------------------------------------
# Position exports and the passenger table (evaluation §3.1)
# ---------------------------------------------------------------------------

def _csv(rows: Iterable[Sequence[Any]]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    for row in rows:
        writer.writerow(["" if cell is None else cell for cell in row])
    return buf.getvalue().encode("utf-8")


def elevator_positions_csv(ticks: Sequence[TickRecord], num_elevators: int) -> bytes:
    """The source-facing position log: ``t,elevator_0,...``; one row per
    committed tick, each cell the floor at the start of that tick (constitution P7)."""
    header = ["t"] + [f"elevator_{i}" for i in range(num_elevators)]
    return _csv([header] + [[tr.tick] + [e.floor for e in tr.entries] for tr in ticks])


def position_log_long_csv(ticks: Sequence[TickRecord]) -> bytes:
    rows: list[Sequence[Any]] = [["t", "elevator_id", "floor", "heading", "load"]]
    for tr in ticks:
        rows += [[tr.tick, e.elevator_id, e.floor, e.heading.value, e.load] for e in tr.entries]
    return _csv(rows)


def passengers_csv(analysis: _Analysis) -> bytes:
    rows: list[Sequence[Any]] = [["passenger_id", "source_id", "request_time", "origin", "destination",
                                  "elevator", "assigned_at", "pickup_time", "dropoff_time", "wait_time",
                                  "travel_time", "total_time", "capacity_deferrals", "wrong_way_passes",
                                  "standing"]]
    for f in analysis.facts:
        p = f.passenger
        rows.append([p.passenger_id, p.source_id, p.request_time, p.origin, p.destination,
                     p.assigned_elevator, p.assigned_at, p.pickup_time, p.dropoff_time, f.wait_time,
                     f.travel_time, f.total_time, f.capacity_deferrals, f.wrong_way_passes, p.standing.value])
    return _csv(rows)


# ---------------------------------------------------------------------------
# Summary (evaluation §4)
# ---------------------------------------------------------------------------

def _utilisation(analysis: _Analysis) -> list[Fraction]:
    ticks = analysis.ticks
    return [Fraction(sum(1 for tr in ticks if tr.entries[i].heading is not Heading.NONE), len(ticks))
            for i in range(analysis.record.configuration.num_elevators)]


def _metrics(analysis: _Analysis) -> dict[str, Any]:
    """The exact metric values of a COMPLETED run, before rendering to a document."""
    cfg = analysis.record.configuration
    f = analysis.facts
    n = len(f)
    waits = [x.wait_time for x in f]
    totals = [x.total_time for x in f]
    deferred = sum(1 for x in f if x.capacity_deferrals)
    wrong = [x for x in f if x.wrong_way_passes]
    return {"n": n, "waits": waits, "totals": totals, "travels": [x.travel_time for x in f],
            "deferred": deferred,
            "wrong_count": len(wrong),
            "wrong_mean_extra": (Fraction(sum(x.passenger.pickup_time - x.first_wrong_way_tick for x in wrong),
                                          len(wrong)) if wrong else None),
            "tail_count": sum(1 for w in waits if w > 2 * (cfg.num_floors - 1)),
            "utilisation": _utilisation(analysis)}


def summary_document(analysis: _Analysis) -> dict[str, Any]:
    n = analysis.record.trace.num_requests
    completed = sum(1 for x in analysis.facts if x.passenger.standing is Standing.COMPLETED)
    if analysis.standing == "HALTED":
        return {"standing": "HALTED", "final_tick": analysis.final_tick, "halt_reason": analysis.halt["reason"],
                "n": n, "completed": completed, "unserved": n - completed}
    m = _metrics(analysis)
    util = [render_rational(u) for u in m["utilisation"]]
    if n == 0:
        return {"standing": "COMPLETED", "final_tick": 0, "n": 0, "completed": 0, "unserved": 0,
                "no_passengers": True, "wait": dict(NULL_DISTRIBUTION), "total": dict(NULL_DISTRIBUTION),
                "travel": {"mean": None}, "deferred": {"count": 0},
                "wrong_way": {"count": 0, "mean_extra": None}, "tail_share": None, "tail_ratio": None,
                "makespan": 0, "elevator_utilisation": util}
    wait, total = distribution(m["waits"]), distribution(m["totals"])
    mean_wait = Fraction(sum(m["waits"]), n)
    return {"standing": "COMPLETED", "final_tick": analysis.final_tick, "n": n, "completed": completed,
            "unserved": n - completed, "wait": wait, "total": total,
            "travel": {"mean": render_rational(Fraction(sum(m["travels"]), n))},
            "deferred": {"count": m["deferred"]},
            "wrong_way": {"count": m["wrong_count"],
                          "mean_extra": None if m["wrong_mean_extra"] is None
                          else render_rational(m["wrong_mean_extra"])},
            "tail_share": render_rational(Fraction(m["tail_count"], n)),
            "tail_ratio": None if mean_wait == 0 else render_rational(Fraction(wait["p95"]) / mean_wait),
            "makespan": analysis.final_tick, "elevator_utilisation": util}


def summary(record: RunRecord) -> dict[str, Any]:
    """The summary document of a final Run (evaluation §4) as plain values."""
    return summary_document(_analyse(record))


def observations(record: RunRecord) -> str:
    """The rule-generated observations of a final Run (evaluation §5)."""
    return observations_text(_analyse(record))


# ---------------------------------------------------------------------------
# Calibration (scheduler_design §9): realized minus projected, from the receipt
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CalibrationRow:
    """One ``cost_based`` assignment: the projection committed in its own ASSIGNED
    receipt against what the History realized. Errors are signed and unclamped:
    ``realized - projected``; positive means later than projected. ``None`` where the
    realized time does not exist yet (a halted run)."""

    passenger_id: int
    source_id: str
    elevator: int
    assigned_at: int
    tier: int | None
    projected_pickup: int
    projected_dropoff: int
    realized_pickup: int | None
    realized_dropoff: int | None
    pickup_error: int | None
    dropoff_error: int | None
    later_assignment_to_same_elevator: bool


def calibration(record: RunRecord) -> tuple[CalibrationRow, ...]:
    """Calibration rows for every assignment whose own receipt carries projections
    (``projected_pickup`` and ``projected_dropoff``). Assignments whose receipt has
    none (round robin, nearest car) yield no row: nothing is fabricated and the route
    projection is never re-run."""
    analysis = _analyse(record)
    rows = []
    for f in analysis.facts:
        rc = f.receipt
        if not isinstance(rc, Mapping) or "projected_pickup" not in rc or "projected_dropoff" not in rc:
            continue
        p = f.passenger
        later = any(a.seq > f.assigned_seq and a.elevator_id == p.assigned_elevator for a in analysis.assigned)
        rows.append(CalibrationRow(
            p.passenger_id, p.source_id, p.assigned_elevator, p.assigned_at, rc.get("tier"),
            rc["projected_pickup"], rc["projected_dropoff"], p.pickup_time, p.dropoff_time,
            None if p.pickup_time is None else p.pickup_time - rc["projected_pickup"],
            None if p.dropoff_time is None else p.dropoff_time - rc["projected_dropoff"], later))
    return tuple(rows)


def calibration_summary(rows: Sequence[CalibrationRow]) -> dict[str, Any] | None:
    """Counts and extremes of the signed errors; ``None`` when no assignment carries
    a projection (calibration is not applicable)."""
    if not rows:
        return None
    pe = [r.pickup_error for r in rows if r.pickup_error is not None]
    de = [r.dropoff_error for r in rows if r.dropoff_error is not None]
    return {"assignments": len(rows),
            "exact": sum(1 for r in rows if r.pickup_error == 0 and r.dropoff_error == 0),
            "pickup_error_min": min(pe) if pe else None, "pickup_error_max": max(pe) if pe else None,
            "dropoff_error_min": min(de) if de else None, "dropoff_error_max": max(de) if de else None}


# ---------------------------------------------------------------------------
# Observations (evaluation §5): a fixed rule set, each with its precondition
# ---------------------------------------------------------------------------

def observations_text(analysis: _Analysis) -> str:
    if analysis.standing == "HALTED":
        return HALTED_LINE
    n = analysis.record.trace.num_requests
    if n == 0:
        return NO_PASSENGERS_LINE
    cfg = analysis.record.configuration
    m = _metrics(analysis)
    f = analysis.facts
    lines: list[str] = []
    # 1. tail ratio (precondition: n >= 1 and mean wait > 0); flagged when > 2
    p95 = nearest_rank(sorted(m["waits"]), 95)
    mean_wait = Fraction(sum(m["waits"]), n)
    if mean_wait > 0:
        ratio = Fraction(p95) / mean_wait
        line = (f"- Tail ratio (95th-percentile wait / mean wait): {render_rational(ratio)} "
                f"(p95 {p95}, mean {render_rational(mean_wait)}).")
        lines.append(line + (" Flagged: above 2." if ratio > 2 else ""))
    # 2. capacity deferrals
    if m["deferred"] >= 1:
        floors = sorted({x.passenger.origin for x in f if x.capacity_deferrals})
        lines.append(f"- Capacity deferrals: {m['deferred']} passenger(s) were refused boarding for capacity "
                     f"at least once, at floor(s) {', '.join(str(x) for x in floors)}.")
    # 3. the passenger with the maximum wait (ties to the lowest passenger_id)
    worst = min((x for x in f), key=lambda x: (-x.wait_time, x.passenger.passenger_id))
    p = worst.passenger
    state = analysis.ticks[p.request_time].entries[p.assigned_elevator]
    doing = (f"idle at floor {state.floor}" if state.heading is Heading.NONE else
             f"at floor {state.floor} heading {state.heading.value} with load {state.load}")
    lines.append(f"- Longest wait: passenger {p.passenger_id} (source_id {json.dumps(p.source_id)}) at floor "
                 f"{p.origin}, requested at t={p.request_time}, assigned to elevator {p.assigned_elevator}, "
                 f"waited {worst.wait_time} tick(s); when the request arrived elevator "
                 f"{p.assigned_elevator} was {doing}.")
    # 4. wrong-way passes
    if m["wrong_count"] >= 1:
        lines.append(f"- Wrong-way passes: {m['wrong_count']} passenger(s) were passed by their car going the "
                     f"other way first; mean extra wait {render_rational(m['wrong_mean_extra'])} tick(s).")
    # 5. utilisation imbalance (precondition: N >= 2); flagged when > 1/2
    util = m["utilisation"]
    if cfg.num_elevators >= 2:
        spread = max(util) - min(util)
        lines.append(f"- Utilisation imbalance: busiest elevator {render_rational(max(util))} minus least busy "
                     f"{render_rational(min(util))} = {render_rational(spread)}."
                     + (" Flagged: above 1/2." if spread > Fraction(1, 2) else ""))
    # 6. idle gaps: the longest run of ticks with every elevator idle (earliest on ties)
    best_len = best_start = run_len = 0
    run_start = 0
    for tr in analysis.ticks:
        if all(e.heading is Heading.NONE for e in tr.entries):
            if run_len == 0:
                run_start = tr.tick
            run_len += 1
            if run_len > best_len:
                best_len, best_start = run_len, run_start
        else:
            run_len = 0
    lines.append("- Idle gap: no tick had every elevator idle." if best_len == 0 else
                 f"- Idle gap: the longest run of ticks with every elevator idle is {best_len} tick(s), from "
                 f"t={best_start} to t={best_start + best_len - 1}.")
    # 7. cost_based: share of Tier 2 assignments and the calibration summary
    if cfg.policy == "cost_based":
        tier2 = sum(1 for x in f if isinstance(x.receipt, Mapping) and x.receipt.get("tier") == 2)
        rows = calibration(analysis.record)
        cs = calibration_summary(rows)
        line = f"- Cost-based assignment: {tier2} of {n} used the Tier 2 fallback ({render_rational(Fraction(tier2, n))})"
        if cs is not None:
            line += (f"; calibration: {cs['exact']} of {cs['assignments']} assignments were realized exactly as "
                     f"projected, pickup error min {cs['pickup_error_min']} max {cs['pickup_error_max']}, "
                     f"dropoff error min {cs['dropoff_error_min']} max {cs['dropoff_error_max']}")
        lines.append(line + ".")
    return "".join(line + "\n" for line in lines)


# ---------------------------------------------------------------------------
# The Reproducible Output Surface and the execution evidence (evaluation §3)
# ---------------------------------------------------------------------------

def _run_identity_document(analysis: _Analysis) -> bytes:
    rec = analysis.record
    ident = rec.identity
    halt = analysis.halt
    return canonical_json({
        "run_id": ident.run_id,
        "configuration": rec.configuration,
        "configuration_hash": ident.configuration_hash,
        "trace_hash": ident.trace_hash,
        "policy": {"name": rec.configuration.policy, "params": rec.configuration.policy_params},
        "code_identity": ident.code_identity,
        "outcome": {"standing": analysis.standing, "final_tick": analysis.final_tick,
                    "halt_step": None if halt is None else halt["step"],
                    "halt_reason": None if halt is None else halt["reason"]}})


def reproducible_surface(record: RunRecord) -> dict[str, bytes]:
    """The eight files of the Reproducible Output Surface, as bytes, in the documented
    order. A pure function of the Run: it takes no execution fact, so none can appear
    in it (constitution N18). Reads the record; changes nothing."""
    a = _analyse(record)
    history = record.history
    n_elev = record.configuration.num_elevators
    surface = {
        "elevator_positions.csv": elevator_positions_csv(a.ticks, n_elev),
        "position_log_long.csv": position_log_long_csv(a.ticks),
        "passengers.csv": passengers_csv(a),
        "summary.json": canonical_json(summary_document(a)),
        "observations.md": observations_text(a).encode("utf-8"),
        "run_identity.json": _run_identity_document(a),
        "events.jsonl": b"".join(canonical_json(e) + b"\n" for e in history.events),
        "tick_records.jsonl": b"".join(canonical_json(t) + b"\n" for t in history.tick_records),
    }
    assert tuple(surface) == SURFACE_FILES
    return surface


def execution_metadata(*, execution_id: str, run_id: str, standing: str, store_id: str | None = None,
                       git_sha: str | None = None, worktree_standing: str | None = None,
                       provenance: Mapping[str, Any] | None = None,
                       checkpoint_controls: Mapping[str, Any] | None = None, pid: int | None = None,
                       started_at: str | None = None, ended_at: str | None = None) -> bytes:
    """``execution_metadata.json``: the Execution's own RECEIPT (authority row 40). Every
    value is supplied by the caller, which owns the clock, the process and the Git query;
    nothing here reads the environment. It lives outside the Reproducible Output Surface
    and outside every equality claim."""
    return canonical_json({
        "execution_id": execution_id, "run_id": run_id, "standing": standing, "store_id": store_id,
        "git_sha": git_sha, "worktree_standing": worktree_standing, "provenance": provenance,
        "checkpoint_controls": checkpoint_controls, "pid": pid, "started_at": started_at,
        "ended_at": ended_at})


def write_files(directory: str, files: Mapping[str, bytes]) -> None:
    """Write files into ``directory`` (created if absent). Never overwrites: an existing
    file is an error, because an output directory is one Execution's evidence."""
    os.makedirs(directory, exist_ok=True)
    for name, data in files.items():
        if os.path.basename(name) != name:
            raise ValueError(f"not a plain file name: {name!r}")
        with open(os.path.join(directory, name), "xb") as fh:
            fh.write(data)


def write_execution_output(output_dir: str, run_id: str, execution: Execution, surface: Mapping[str, bytes],
                           metadata: bytes) -> str:
    """The execution-output wrapper (cpoc §2.2a, architecture §1.1): an output-only batch Execution's
    evidence root is ``<output_dir>/<run_id>/<execution_id>/``. Bind the Execution's own log there through
    ``operations`` (its buffered records are flushed once, in order, to ``operational.jsonl``), then write
    the Reproducible Output Surface exactly as generated and ``execution_metadata.json`` beside it. The
    log is a separate file: reporting acquires no log authority, reads no operational record to compute
    a metric, and embeds no execution fact in any surface file. Returns the root. Nothing is overwritten:
    an existing file is an error."""
    if set(surface) != set(SURFACE_FILES):
        raise ValueError("the surface must be exactly the eight Reproducible Output Surface files")
    root = os.path.join(output_dir, run_id, execution.execution_id)
    execution.log.bind_evidence_root(root)
    write_files(root, {**surface, "execution_metadata.json": metadata})
    return root
