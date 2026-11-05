"""Domain value types, validation, canonical serialisation and code identity.

This module realises implementation plan cut 1 against the admitted
revision-7.1 governing documents:

- constitution §2 (canonical objects), §4.1 (passenger standing), §12
  (reproducibility and the supported execution contract);
- simulation_semantics §1 (definitions), §6 (invalid requests), §8.3 (the
  default liveness horizon);
- evaluation_design §2 (public input boundary: accepted row shapes,
  normalisation, validation order, configuration domain) and §6.4 (Trace
  identity);
- architecture §4 (determinism machinery: canonical serialisation, code
  identity, the execution contract).

Everything here is a value: frozen dataclasses with no writer of runtime
state. Nothing here persists, schedules, routes or logs. The continuation
types (Snapshot, HistoryPrefix, HistoryVerifier) belong to the checkpoint
module (cut 9) and are deliberately absent.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields
from enum import Enum
from types import MappingProxyType
from typing import Any

# ---------------------------------------------------------------------------
# Domain constants (evaluation_design §2, §6; scheduler_design §6.3)
# ---------------------------------------------------------------------------

MIN_FLOORS = 2
MAX_FLOORS = 200
MIN_ELEVATORS = 1
MAX_ELEVATORS = 20
MIN_CAPACITY = 1
MAX_CAPACITY = 50
MAX_REQUEST_TIME = 10**9
MAX_REQUEST_ROWS = 100_000
MAX_POLICY_PARAM = 10**6

POLICY_NAMES = ("round_robin", "nearest_car", "cost_based")

#: Cost-based policy parameter names (scheduler_design §6.3). Defaults that
#: depend on the building are filled at Configuration creation so that the
#: Configuration, and therefore run_id, is fully determined by its fields.
COST_BASED_PARAMS = ("w_wait", "w_marginal", "w_tail", "tail_threshold", "age_scale")

#: Schema version constants (authority model row 5). They live in the
#: governed package so that code identity covers them.
CONTINUATION_SCHEMA_VERSION = 1
STORE_SCHEMA_VERSION = 1

_DIGITS = re.compile(r"^[0-9]+$")


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------

class Refusal(Exception):
    """A named refusal at a governed boundary (constitution N17).

    ``reason`` is one of the names the governing documents use. ``positions``
    are the input row positions (``input_index``) the refusal concerns, when
    any. ``source_id`` is the offending request's supplied id when known.
    Nothing is substituted or normalised into validity.
    """

    def __init__(self, reason: str, detail: str, *, positions: tuple[int, ...] = (),
                 source_id: str | None = None) -> None:
        self.reason = reason
        self.detail = detail
        self.positions = positions
        self.source_id = source_id
        where = f" at positions {list(positions)}" if positions else ""
        who = f" (source_id {source_id!r})" if source_id is not None else ""
        super().__init__(f"{reason}{where}{who}: {detail}")


# ---------------------------------------------------------------------------
# Canonical serialisation (architecture §4)
# ---------------------------------------------------------------------------

def _canonical_value(value: Any) -> Any:
    """Convert a domain value into plain JSON-serialisable structure."""
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {f.name: _canonical_value(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, tuple) or isinstance(value, list):
        return [_canonical_value(v) for v in value]
    if isinstance(value, Mapping):
        return {str(k): _canonical_value(v) for k, v in value.items()}
    if isinstance(value, bool):
        return value
    if isinstance(value, int) or value is None or isinstance(value, str):
        return value
    raise TypeError(f"not canonically serialisable: {type(value).__name__}")


def canonical_json(value: Any) -> bytes:
    """Canonical JSON bytes: sorted keys, no insignificant whitespace, ASCII.

    Integers only for simulation quantities; floats are refused so that no
    platform-dependent rendering can enter a hash or an equality witness.
    """
    plain = _canonical_value(value)
    text = json.dumps(plain, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False)
    return text.encode("ascii")


def parse_canonical_json(data: bytes) -> Any:
    return json.loads(data.decode("ascii"))


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _exact_str(value: str) -> str:
    """A genuine built-in ``str`` with the same characters, so a ``str``
    subclass carrying other state cannot be retained."""
    exact = str.__str__(value)
    if type(exact) is not str:
        exact = "".join(list(value))
    return exact


@dataclass(frozen=True)
class FrozenEnum:
    """The committed form of an Enum member inside a frozen payload. An Enum
    member's identity is stable but its ``.value`` may be a mutable object,
    so the member itself is never kept: only its qualified type name, member
    name and a recursively frozen copy of its value. Equivalent members
    freeze, and therefore serialise, identically."""

    type_name: str
    member_name: str
    value: Any

    def __post_init__(self) -> None:
        # The constructor enforces the invariant itself, however the instance
        # is created: the metadata must be genuine immutable ``str`` objects
        # (not subclasses, lists or anything else the annotation merely
        # claims) and the value is re-frozen, so no caller-owned reference
        # can change this value's canonical bytes.
        for name in ("type_name", "member_name"):
            if type(getattr(self, name)) is not str:
                raise TypeError(f"FrozenEnum.{name} must be a str, not "
                                f"{type(getattr(self, name)).__name__}")
        object.__setattr__(self, "value", freeze(self.value))


def freeze(value: Any) -> Any:
    """Deep-freeze a canonical payload so that no reference held by its
    author can mutate it afterwards: mappings become read-only mappings over
    fresh dicts with string keys in sorted order, sequences become tuples,
    Enum members become ``FrozenEnum`` (type, name, frozen value), and
    integers, strings, booleans and ``None`` pass through. Anything else
    (floats, sets, arbitrary objects, an Enum whose value is one of those)
    is refused with ``TypeError``, since it could not be serialised
    canonically either. Fails closed: nothing mutable survives."""
    if isinstance(value, FrozenEnum):
        return FrozenEnum(value.type_name, value.member_name, value.value)
    if isinstance(value, Enum):
        cls = type(value)
        return FrozenEnum(_exact_str(f"{cls.__module__}.{cls.__qualname__}"), _exact_str(value.name),
                          value.value)
    if value is None:
        return None
    # Scalars are returned as exact built-in objects, never as caller
    # subclasses that could carry mutable state or override behaviour.
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, int):
        return int.__int__(value)
    if isinstance(value, str):
        return _exact_str(value)
    if isinstance(value, Mapping):
        keys = sorted((_exact_str(str(k)), k) for k in value)
        return MappingProxyType({name: freeze(value[k]) for name, k in keys})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(v) for v in value)
    raise TypeError(f"not a freezable canonical value: {type(value).__name__}")


# ---------------------------------------------------------------------------
# Requests and the Trace (constitution §2; evaluation_design §2, §6.4)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Request:
    """One normalised request row.

    ``source_id`` is the supplied id, preserved; ``input_index`` is the row's
    position in the input (stable tie order); ``passenger_id`` is the
    position in the sorted Trace and is assigned by ``Trace``.
    """

    input_index: int
    source_id: str
    request_time: int
    origin: int
    destination: int
    passenger_id: int

    @property
    def distance(self) -> int:
        return abs(self.destination - self.origin)

    @property
    def direction(self) -> "Heading":
        return Heading.UP if self.destination > self.origin else Heading.DOWN


@dataclass(frozen=True)
class Trace:
    """The ordered, finite list of all Requests for a run, sorted stably by
    ``(request_time, input_index)``; immutable; content-addressed."""

    requests: tuple[Request, ...]
    num_floors: int

    @property
    def num_requests(self) -> int:
        return len(self.requests)

    @property
    def last_request_time(self) -> int:
        """``T_last``: 0 for an empty Trace (simulation_semantics §8)."""
        return self.requests[-1].request_time if self.requests else 0

    def canonical_rows(self) -> list[list[Any]]:
        """``[time, source_id, origin, dest]`` rows in Trace order
        (evaluation_design §6.4)."""
        return [[r.request_time, r.source_id, r.origin, r.destination] for r in self.requests]

    @property
    def trace_hash(self) -> str:
        return sha256_hex(canonical_json(self.canonical_rows()))

    def by_source_id(self) -> dict[str, Request]:
        return {r.source_id: r for r in self.requests}


def _convert_nonnegative_int(value: Any, what: str, position: int) -> int:
    """Integers, or strings of ASCII decimal digits; nothing else
    (evaluation_design §2). ``bool`` is refused: it is not an integer input."""
    if isinstance(value, bool):
        raise Refusal("INPUT_INVALID", f"{what} must be an integer or a string of decimal digits",
                      positions=(position,))
    if isinstance(value, int):
        return value
    if isinstance(value, str) and _DIGITS.match(value):
        return int(value)
    raise Refusal("INPUT_INVALID", f"{what} must be an integer or a string of decimal digits",
                  positions=(position,))


def _convert_source_id(value: Any, position: int) -> str:
    if isinstance(value, bool):
        raise Refusal("INPUT_INVALID", "id must be a string or an integer", positions=(position,))
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value
    raise Refusal("INPUT_INVALID", "id must be a string or an integer", positions=(position,))


def _row_fields(row: Any, position: int) -> tuple[Any, Any, Any, Any]:
    """A mapping with exactly the keys time, id, source, dest; or a sequence
    of exactly four values in that order. Anything else is INPUT_INVALID."""
    if isinstance(row, Mapping):
        keys = set(row.keys())
        if keys != {"time", "id", "source", "dest"}:
            raise Refusal("INPUT_INVALID",
                          "a mapping row must have exactly the keys time, id, source, dest",
                          positions=(position,))
        return row["time"], row["id"], row["source"], row["dest"]
    if isinstance(row, (str, bytes, bytearray)):
        raise Refusal("INPUT_INVALID", "a row must be a mapping or a sequence of four values",
                      positions=(position,))
    if isinstance(row, Sequence):
        if len(row) != 4:
            raise Refusal("INPUT_INVALID", "a sequence row must have exactly four values",
                          positions=(position,))
        return row[0], row[1], row[2], row[3]
    raise Refusal("INPUT_INVALID", "a row must be a mapping or a sequence of four values",
                  positions=(position,))


def normalize_requests(request_rows: Any, num_floors: int) -> Trace:
    """The shared public input boundary (evaluation_design §2; authority row 41).

    Validation runs in row order, then across rows, exactly as the governing
    text orders it: time domain; floor domain; origin != destination; id
    present; then id uniqueness and the row count. The first failure refuses
    with its reason and position(s); nothing is normalised into validity.
    """
    if not isinstance(num_floors, int) or isinstance(num_floors, bool) \
            or not (MIN_FLOORS <= num_floors <= MAX_FLOORS):
        raise Refusal("INVALID_CONFIGURATION",
                      f"num_floors must be an integer in {MIN_FLOORS}..{MAX_FLOORS}")
    if isinstance(request_rows, (str, bytes, bytearray, Mapping)):
        raise Refusal("INPUT_INVALID", "request_rows must be an iterable of rows")

    normalised: list[tuple[int, str, int, int, int]] = []
    seen: dict[str, int] = {}
    for position, row in enumerate(request_rows):
        raw_time, raw_id, raw_source, raw_dest = _row_fields(row, position)
        time = _convert_nonnegative_int(raw_time, "time", position)
        source = _convert_nonnegative_int(raw_source, "source", position)
        dest = _convert_nonnegative_int(raw_dest, "dest", position)
        source_id = _convert_source_id(raw_id, position)
        if not (0 <= time <= MAX_REQUEST_TIME):
            raise Refusal("INPUT_INVALID", f"time must be in 0..{MAX_REQUEST_TIME}",
                          positions=(position,), source_id=source_id)
        if not (0 <= source < num_floors) or not (0 <= dest < num_floors):
            raise Refusal("INPUT_INVALID", f"source and dest must be in 0..{num_floors - 1}",
                          positions=(position,), source_id=source_id)
        if source == dest:
            raise Refusal("SAME_FLOOR_REQUEST", "source equals dest",
                          positions=(position,), source_id=source_id)
        if source_id == "":
            raise Refusal("MISSING_SOURCE_ID", "id must be non-empty", positions=(position,))
        if source_id in seen:
            raise Refusal("DUPLICATE_SOURCE_ID", "id must be unique across rows",
                          positions=(seen[source_id], position), source_id=source_id)
        seen[source_id] = position
        normalised.append((time, position, source_id, source, dest))

    if len(normalised) > MAX_REQUEST_ROWS:
        raise Refusal("INPUT_INVALID", f"at most {MAX_REQUEST_ROWS} rows are accepted")

    # Stable sort by (request_time, input_index); passenger_id is the sorted
    # position (constitution §2 Passenger; semantics §1).
    normalised.sort(key=lambda r: (r[0], r[1]))
    requests = tuple(
        Request(input_index=position, source_id=source_id, request_time=time,
                origin=source, destination=dest, passenger_id=passenger_id)
        for passenger_id, (time, position, source_id, source, dest) in enumerate(normalised)
    )
    return Trace(requests=requests, num_floors=num_floors)


# ---------------------------------------------------------------------------
# Configuration (constitution §2; evaluation_design §2; semantics §8.3)
# ---------------------------------------------------------------------------

def _check_int(value: Any, name: str, lo: int, hi: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not (lo <= value <= hi):
        raise Refusal("INVALID_CONFIGURATION", f"{name} must be an integer in {lo}..{hi}")
    return value


def default_max_ticks(num_floors: int, trace: Trace) -> int:
    """The proved liveness bound ``T_last + 2 * P * (F - 1)``
    (constitution P10; simulation_semantics §8.1, §8.3)."""
    return trace.last_request_time + 2 * trace.num_requests * (num_floors - 1)


@dataclass(frozen=True)
class Configuration:
    """``F``, ``N``, ``C``, initial floor per elevator, ``max_ticks`` (an
    explicit horizon, or ``None`` for the default bound computed against the
    Trace), scheduler policy name and parameters. Immutable; content-addressed.
    ``max_ticks`` above the default bound is refused when the Configuration is
    bound to a Trace (``validate_with_trace``)."""

    num_floors: int
    num_elevators: int
    capacity: int
    initial_floors: tuple[int, ...]
    max_ticks: int | None
    policy: str
    policy_params: Mapping[str, int] = field(default_factory=dict)

    @staticmethod
    def create(num_floors: int, num_elevators: int, capacity: int, *,
               initial_floors: Sequence[int] | None = None, max_ticks: int | None = None,
               policy: str = "cost_based",
               policy_params: Mapping[str, int] | None = None) -> "Configuration":
        f = _check_int(num_floors, "num_floors", MIN_FLOORS, MAX_FLOORS)
        n = _check_int(num_elevators, "num_elevators", MIN_ELEVATORS, MAX_ELEVATORS)
        c = _check_int(capacity, "capacity", MIN_CAPACITY, MAX_CAPACITY)
        if initial_floors is None:
            floors = tuple(0 for _ in range(n))
        else:
            if isinstance(initial_floors, (str, bytes)) or len(initial_floors) != n:
                raise Refusal("INVALID_CONFIGURATION",
                              "initial_floors must have one entry per elevator")
            floors = tuple(_check_int(v, "initial_floors entry", 0, f - 1) for v in initial_floors)
        if max_ticks is not None:
            max_ticks = _check_int(max_ticks, "max_ticks", 0, 2**62)
        if policy not in POLICY_NAMES:
            raise Refusal("INVALID_CONFIGURATION", f"policy must be one of {POLICY_NAMES}")
        params = dict(policy_params or {})
        if policy == "cost_based":
            defaults = {"w_wait": 1, "w_marginal": 1, "w_tail": 3,
                        "tail_threshold": 2 * (f - 1), "age_scale": f - 1}
            unknown = set(params) - set(COST_BASED_PARAMS)
            if unknown:
                raise Refusal("INVALID_CONFIGURATION",
                              f"unknown cost_based parameters: {sorted(unknown)}")
            merged = {k: params.get(k, defaults[k]) for k in COST_BASED_PARAMS}
            for k, v in merged.items():
                _check_int(v, f"policy parameter {k}", 0, MAX_POLICY_PARAM)
            params = merged
        elif params:
            raise Refusal("INVALID_CONFIGURATION", f"policy {policy} takes no parameters")
        return Configuration(num_floors=f, num_elevators=n, capacity=c, initial_floors=floors,
                             max_ticks=max_ticks, policy=policy,
                             policy_params=dict(sorted(params.items())))

    def validate_with_trace(self, trace: Trace) -> int:
        """Bind-time check: the Trace was normalised for this building, and
        ``max_ticks`` is absent or at most the default bound. Returns the
        effective horizon."""
        if trace.num_floors != self.num_floors:
            raise Refusal("INVALID_CONFIGURATION",
                          "the Trace was normalised for a different number of floors")
        bound = default_max_ticks(self.num_floors, trace)
        if self.max_ticks is None:
            return bound
        if self.max_ticks > bound:
            raise Refusal("INVALID_CONFIGURATION",
                          f"max_ticks {self.max_ticks} exceeds the default bound {bound}")
        return self.max_ticks

    @property
    def configuration_hash(self) -> str:
        return sha256_hex(canonical_json(self))


# ---------------------------------------------------------------------------
# Passengers and elevators (constitution §2, §4.1, §4.2)
# ---------------------------------------------------------------------------

class Standing(Enum):
    WAITING = "WAITING"
    ONBOARD = "ONBOARD"
    COMPLETED = "COMPLETED"


class Heading(Enum):
    UP = "UP"
    DOWN = "DOWN"
    NONE = "NONE"

    @property
    def delta(self) -> int:
        return {"UP": 1, "DOWN": -1, "NONE": 0}[self.value]


@dataclass(frozen=True)
class Passenger:
    """The lifecycle record of one Request. It carries no estimate of any
    kind (constitution N10): projections live only in the ``ASSIGNED`` event's
    receipt."""

    passenger_id: int
    source_id: str
    request_time: int
    origin: int
    destination: int
    standing: Standing
    assigned_elevator: int | None
    assigned_at: int | None
    pickup_time: int | None
    dropoff_time: int | None


@dataclass(frozen=True)
class Elevator:
    """Exactly two authoritative fields (constitution §4.2)."""

    elevator_id: int
    floor: int
    heading: Heading


# ---------------------------------------------------------------------------
# Simulation History value types (constitution §2; N18)
# ---------------------------------------------------------------------------

class SimulationEventKind(Enum):
    REVEALED = "REVEALED"
    ASSIGNED = "ASSIGNED"
    BOARDED = "BOARDED"
    ALIGHTED = "ALIGHTED"
    COMPLETED = "COMPLETED"
    HALTED = "HALTED"


@dataclass(frozen=True)
class SimulationEvent:
    """One passenger or run-standing transition. ``receipt`` is present only
    on ``ASSIGNED`` (the policy's estimates, never an outcome); ``halt`` only
    on ``HALTED`` (step, reason, passenger)."""

    seq: int
    kind: SimulationEventKind
    tick: int
    passenger_id: int | None = None
    elevator_id: int | None = None
    floor: int | None = None
    receipt: Mapping[str, Any] | None = None
    halt: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        # Committed history is immutable all the way down: payloads are
        # deep-frozen copies, so the policy's receipt or a caller's halt dict
        # cannot change the event after construction.
        object.__setattr__(self, "receipt", freeze(self.receipt))
        object.__setattr__(self, "halt", freeze(self.halt))


@dataclass(frozen=True)
class TickEntry:
    elevator_id: int
    floor: int
    heading: Heading
    load: int
    boarded: tuple[int, ...]
    alighted: tuple[int, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "boarded", tuple(self.boarded))
        object.__setattr__(self, "alighted", tuple(self.alighted))


@dataclass(frozen=True)
class TickRecord:
    tick: int
    entries: tuple[TickEntry, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "entries", tuple(self.entries))


class OperationalRecordKind(Enum):
    EXECUTION_STARTED = "EXECUTION_STARTED"
    CHECKPOINT_WRITTEN = "CHECKPOINT_WRITTEN"
    LOAD_ADMITTED = "LOAD_ADMITTED"
    RESUMED = "RESUMED"
    FINALITY_WRITTEN = "FINALITY_WRITTEN"
    EXECUTION_ENDED = "EXECUTION_ENDED"
    CODE_IDENTITY_DRIFT = "CODE_IDENTITY_DRIFT"
    DIAGNOSTIC = "DIAGNOSTIC"


@dataclass(frozen=True)
class OperationalRecord:
    """An execution fact as a value (authority row 26). The log that carries
    it is cut 8's ``operations`` module; nothing here appends or persists."""

    execution_id: str
    op_seq: int
    kind: OperationalRecordKind
    tick: int | None = None
    payload: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class SimulationHistory:
    """Simulation Events and TickRecords only. The type refuses anything
    else at construction, so an Operational Record cannot be held
    (constitution N18)."""

    events: tuple[SimulationEvent, ...]
    tick_records: tuple[TickRecord, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "events", tuple(self.events))
        object.__setattr__(self, "tick_records", tuple(self.tick_records))
        for e in self.events:
            if not isinstance(e, SimulationEvent):
                raise TypeError(f"SimulationHistory.events cannot hold {type(e).__name__}")
        for r in self.tick_records:
            if not isinstance(r, TickRecord):
                raise TypeError(f"SimulationHistory.tick_records cannot hold {type(r).__name__}")

    @property
    def history_hash(self) -> str:
        return sha256_hex(canonical_json({"events": self.events, "tick_records": self.tick_records}))


# ---------------------------------------------------------------------------
# Code identity and the supported execution contract (constitution §2, §12;
# architecture §4; authority row 4)
# ---------------------------------------------------------------------------

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))


def _package_sources(package_dir: str) -> list[tuple[str, bytes]]:
    out: list[tuple[str, bytes]] = []
    for root, dirs, files in os.walk(package_dir):
        dirs.sort()
        for name in sorted(files):
            if name.endswith(".py"):
                path = os.path.join(root, name)
                rel = os.path.relpath(path, package_dir).replace(os.sep, "/")
                with open(path, "rb") as fh:
                    out.append((rel, fh.read()))
    out.sort(key=lambda item: item[0])
    return out


def code_identity(package_dir: str = PACKAGE_DIR) -> str:
    """SHA-256 over the sorted sequence of (relative path, file bytes) of every
    ``.py`` file in the governed package. Encoding, fixed so that two
    implementations agree: for each file in sorted path order, the UTF-8
    path, a newline, the decimal byte length, a newline, the bytes, a newline.
    It changes with any byte of any source file, committed or not; the Git
    SHA never participates."""
    h = hashlib.sha256()
    for rel, data in _package_sources(package_dir):
        h.update(rel.encode("utf-8"))
        h.update(b"\n")
        h.update(str(len(data)).encode("ascii"))
        h.update(b"\n")
        h.update(data)
        h.update(b"\n")
    return h.hexdigest()


def check_execution_environment(package_dir: str = PACKAGE_DIR) -> None:
    """The supported execution contract (constitution §12). Refuses
    ``UNSUPPORTED_EXECUTION_ENVIRONMENT`` unless bytecode writing is
    disabled for this interpreter and no ``__pycache__`` directory exists
    inside the governed package. Governed entry points call this before
    computing code identity and before any Run begins."""
    if not sys.flags.dont_write_bytecode:
        raise Refusal("UNSUPPORTED_EXECUTION_ENVIRONMENT",
                      "bytecode writing must be disabled (python -B or PYTHONDONTWRITEBYTECODE=1)")
    for root, dirs, _files in os.walk(package_dir):
        if "__pycache__" in dirs:
            raise Refusal("UNSUPPORTED_EXECUTION_ENVIRONMENT",
                          f"a __pycache__ directory exists inside the governed package at {root}")


@dataclass(frozen=True)
class EstablishedCodeIdentity:
    """Code identity as established before a Run began, with what is needed
    to detect drift at exit."""

    package_dir: str
    identity: str


def establish_code_identity(package_dir: str = PACKAGE_DIR) -> EstablishedCodeIdentity:
    """The 'Code identity establishment' transition (constitution §4.5):
    check the execution contract, then hash the package."""
    check_execution_environment(package_dir)
    return EstablishedCodeIdentity(package_dir=package_dir, identity=code_identity(package_dir))


def detect_code_identity_drift(established: EstablishedCodeIdentity, *, execution_id: str,
                               op_seq: int) -> OperationalRecord | None:
    """Re-hash at exit (constitution §12). Returns a ``CODE_IDENTITY_DRIFT``
    Operational Record value if the package's sources changed since
    establishment, else ``None``. Appending the record to a log is the
    ``operations`` module's concern (cut 8)."""
    now = code_identity(established.package_dir)
    if now == established.identity:
        return None
    return OperationalRecord(execution_id=execution_id, op_seq=op_seq,
                             kind=OperationalRecordKind.CODE_IDENTITY_DRIFT, tick=None,
                             payload={"established": established.identity, "at_exit": now})


# ---------------------------------------------------------------------------
# Run identity (constitution §2 Run; authority row 6)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RunIdentity:
    run_id: str
    configuration_hash: str
    trace_hash: str
    code_identity: str
    max_ticks: int


def bind_run(configuration: Configuration, trace: Trace, code_identity_value: str) -> RunIdentity:
    """The Trace-load binding: validate the Configuration against the Trace
    and mint ``run_id = sha256(canonical [configuration_hash, trace_hash,
    code_identity])``. No runtime state is created."""
    horizon = configuration.validate_with_trace(trace)
    ch, th = configuration.configuration_hash, trace.trace_hash
    run_id = sha256_hex(canonical_json([ch, th, code_identity_value]))
    return RunIdentity(run_id=run_id, configuration_hash=ch, trace_hash=th,
                       code_identity=code_identity_value, max_ticks=horizon)


# ---------------------------------------------------------------------------
# The scheduler decision surface (scheduler_design §2, §3). Added in cut 3:
# the engine constructs these values and the policies (cut 4) consume them;
# they live here, not in the engine module, because the policies module may
# import nothing from the engine (testing_contract §3 policy_cannot_import_trace).
# Plain immutable values with no reference to a Trace, an engine or a History.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OnboardView:
    passenger_id: int
    destination: int
    pickup_time: int


@dataclass(frozen=True)
class WaitingView:
    passenger_id: int
    origin: int
    destination: int
    request_time: int


@dataclass(frozen=True)
class ElevatorView:
    id: int
    floor: int
    heading: Heading
    onboard: tuple[OnboardView, ...]
    waiting: tuple[WaitingView, ...]


@dataclass(frozen=True)
class SchedulerView:
    """Exactly the lawful decision surface: time, building, and per elevator
    its floor, heading, onboard and assigned-waiting passengers. Nothing
    else; every passenger in it has ``request_time <= t``."""

    t: int
    floors: int
    num_elevators: int
    capacity: int
    elevators: tuple[ElevatorView, ...]


@dataclass(frozen=True)
class RevealedRequest:
    passenger_id: int
    origin: int
    destination: int
    request_time: int


@dataclass(frozen=True)
class Proposal:
    """A policy's answer: one elevator id and, optionally, the chosen
    candidate's estimates (a receipt, never an outcome)."""

    elevator_id: int
    receipt: Mapping[str, Any] | None = None
