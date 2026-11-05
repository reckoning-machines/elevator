"""Operations: Execution identity and the Operational Log lifecycle (plan cut 8; architecture §1.1).

This module implements only the existing process-owned boundaries: ``execution_id``, the Operational
Log with its ``op_seq``, ``append``, ``bind_evidence_root`` and ``flush_unflushed_prefix`` (cpoc §2.2a,
authority rows 26 and 37). It is neutral. It holds operational identity and the log, never the engine,
a Passenger field, a Run outcome, Store identity, a write-admission token or a durable Execution
standing, and it makes no continuation or admission decision. It depends on ``domain`` and the
standard library only; the API, reporting's execution-output wrapper and (from cut 9) checkpoint call
it, and it imports none of them. Nothing here is reachable from the engine, a policy or the History:
operational evidence cannot influence a simulation fact.

Lifecycle implemented in cut 8 (no Store): from creation the log is an in-memory buffer (``EPHEMERAL``)
whose first record is ``EXECUTION_STARTED`` with ``op_seq`` 1. When an evidence root exists the whole
unflushed buffer is written once, in order, to ``<root>/operational.jsonl`` and every later record is
appended there directly, so nothing is written twice and ``op_seq`` is continuous. An Execution that is
never given a root keeps its log in memory only and creates no file. Store binding, receipts and resume
continue this same log in cut 9; none of that is here.
"""

from __future__ import annotations

import datetime
import json
import os
import subprocess
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from elevator.domain import (
    OperationalRecord,
    OperationalRecordKind,
    canonical_json,
    freeze,
)

LOG_FILENAME = "operational.jsonl"


class OperationsError(Exception):
    """A misuse of the log lifecycle (a second binding, an out-of-sequence record). Never repaired."""


class OperationalLog:
    """One Execution's ordered Operational Records. In memory until an evidence root is bound, then
    a file; one log per Execution, never a second. Every record carries ``execution_id``, ``op_seq``
    (from 1, contiguous), the tick where one applies, and in its payload the process id and code
    identity (authority row 26) plus whatever the kind adds."""

    def __init__(self, execution_id: str, code_identity: str, pid: int, *, first_op_seq: int = 1) -> None:
        self._first_op_seq = first_op_seq  # 1 for a new Execution; one past the file's last record on a resume
        self._execution_id = execution_id
        self._code_identity = code_identity
        self._pid = pid
        self._records: list[OperationalRecord] = []
        self._flushed = 0
        self._root: str | None = None
        self._handle: Any = None

    @property
    def execution_id(self) -> str:
        return self._execution_id

    @property
    def records(self) -> tuple[OperationalRecord, ...]:
        return tuple(self._records)

    @property
    def next_op_seq(self) -> int:
        return self._first_op_seq + len(self._records)

    @property
    def bound(self) -> bool:
        return self._root is not None

    @property
    def evidence_root(self) -> str | None:
        return self._root

    @property
    def path(self) -> str | None:
        return None if self._root is None else os.path.join(self._root, LOG_FILENAME)

    def append(self, kind: OperationalRecordKind, *, tick: int | None = None,
               payload: Mapping[str, Any] | None = None) -> OperationalRecord:
        """Append one record with the next ``op_seq``. Once bound it is also written and flushed."""
        body = {"code_identity": self._code_identity, "pid": self._pid}
        body.update(payload or {})
        record = OperationalRecord(self._execution_id, self.next_op_seq, kind, tick, freeze(body))
        return self._add(record)

    def append_record(self, record: OperationalRecord) -> OperationalRecord:
        """Append a record built elsewhere (for example the drift record of the code-identity check),
        refusing one that is not this log's next record."""
        if record.execution_id != self._execution_id or record.op_seq != self.next_op_seq:
            raise OperationsError(f"record ({record.execution_id}, {record.op_seq}) is not this log's next "
                                  f"record ({self._execution_id}, {self.next_op_seq})")
        body = {"code_identity": self._code_identity, "pid": self._pid}
        body.update(record.payload or {})
        return self._add(OperationalRecord(record.execution_id, record.op_seq, record.kind, record.tick,
                                           freeze(body)))

    def _add(self, record: OperationalRecord) -> OperationalRecord:
        self._records.append(record)
        if self._handle is not None:
            self.flush_unflushed_prefix()
        return record

    def bind_evidence_root(self, root: str) -> str:
        """Give the log its evidence root: create ``<root>/operational.jsonl`` (never over an existing
        file) and flush the whole unflushed buffer to it once, in order. A log is bound at most once."""
        if self._root is not None:
            raise OperationsError("the log already has an evidence root; its carrier changes once")
        os.makedirs(root, exist_ok=True)
        handle = open(os.path.join(root, LOG_FILENAME), "xb")
        self._root, self._handle = root, handle
        self.flush_unflushed_prefix()
        return self.path  # type: ignore[return-value]

    def bind_existing_root(self, root: str) -> str:
        """Continue an existing ``<root>/operational.jsonl`` (a resumed Execution): open it for append and
        flush any records held in memory after it, in order. Never creates a second file."""
        if self._root is not None:
            raise OperationsError("the log already has an evidence root; its carrier changes once")
        self._handle = open(os.path.join(root, LOG_FILENAME), "ab")
        self._root = root
        self.flush_unflushed_prefix()
        return self.path  # type: ignore[return-value]

    def copy_to(self, root: str) -> str:
        """Copy the whole durable log, as it stands, to ``<root>/operational.jsonl`` (the output-location
        copy of a Store-bound Execution at ``EXECUTION_ENDED``; the Store file remains the log). Never
        overwrites."""
        if self._root is None:
            raise OperationsError("the log has no evidence root: there is no file to copy")
        self.flush_unflushed_prefix()
        os.makedirs(root, exist_ok=True)
        with open(os.path.join(self._root, LOG_FILENAME), "rb") as src, \
                open(os.path.join(root, LOG_FILENAME), "xb") as dst:
            dst.write(src.read())
        return os.path.join(root, LOG_FILENAME)

    def flush_unflushed_prefix(self) -> None:
        """Append every not-yet-written record to the file, in ``op_seq`` order, and flush."""
        if self._handle is None:
            raise OperationsError("the log has no evidence root yet: nothing to flush to")
        for record in self._records[self._flushed:]:
            self._handle.write(canonical_json(record) + b"\n")
        self._flushed = len(self._records)
        self._handle.flush()
        os.fsync(self._handle.fileno())

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None


class Execution:
    """The process-owned Execution handle: operational identity and the log, nothing else."""

    __slots__ = ("execution_id", "code_identity", "pid", "log")

    def __init__(self, execution_id: str, code_identity: str, pid: int, log: OperationalLog) -> None:
        self.execution_id, self.code_identity, self.pid, self.log = execution_id, code_identity, pid, log


def start_execution(code_identity: str, *, pid: int | None = None) -> Execution:
    """Execution creation: mint a random ``execution_id`` (UUID version 4, 128 random bits; operational
    identity, never scheduler randomness and never part of ``run_id`` or any output of the Reproducible
    Output Surface), open the in-memory log and append ``EXECUTION_STARTED`` as ``op_seq`` 1."""
    execution_id = str(uuid.uuid4())
    process_id = os.getpid() if pid is None else pid
    log = OperationalLog(execution_id, code_identity, process_id)
    log.append(OperationalRecordKind.EXECUTION_STARTED)
    return Execution(execution_id, code_identity, process_id, log)


def read_log(path: str) -> list[dict[str, Any]]:
    """The records of an Operational Log file, in order, as parsed JSON. Refuses (``OperationsError``) a
    file that is not a contiguous log of one Execution: a torn or malformed line, a foreign
    ``execution_id`` or a gap in ``op_seq``."""
    with open(path, "rb") as fh:
        raw = fh.read()
    records: list[dict[str, Any]] = []
    for number, line in enumerate(raw.split(b"\n")[:-1] if raw.endswith(b"\n") else raw.split(b"\n"), start=1):
        try:
            record = json.loads(line)
        except ValueError as exc:
            raise OperationsError(f"line {number} of {path} is not a complete record: {exc}") from exc
        if not isinstance(record, dict) or record.get("op_seq") != number:
            raise OperationsError(f"line {number} of {path} breaks the contiguous op_seq")
        if records and record.get("execution_id") != records[0].get("execution_id"):
            raise OperationsError(f"line {number} of {path} belongs to another Execution")
        records.append(record)
    if raw and not raw.endswith(b"\n"):
        raise OperationsError(f"{path} ends in an unterminated record")
    return records


def resume_execution(execution_id: str, code_identity: str, evidence_root: str, *, pid: int | None = None) -> Execution:
    """The Execution handle of a resumed process: it reuses the admitted ``execution_id`` (no new id is
    minted), opens the Execution's existing log at its evidence root, continues ``op_seq`` from the last
    record in the file, and appends this process's own ``EXECUTION_STARTED``. If the log file is missing
    (it is evidence, never authority) a fresh log is created at ``op_seq`` 1. It reads and writes the log
    only; it never reads a Continuation Document."""
    process_id = os.getpid() if pid is None else pid
    path = os.path.join(evidence_root, LOG_FILENAME)
    if os.path.exists(path):
        last = read_log(path)
        log = OperationalLog(execution_id, code_identity, process_id, first_op_seq=len(last) + 1)
        if last and last[0].get("execution_id") != execution_id:
            raise OperationsError(f"{path} belongs to another Execution")
        log.bind_existing_root(evidence_root)
    else:
        log = OperationalLog(execution_id, code_identity, process_id)
        log.bind_evidence_root(evidence_root)
    log.append(OperationalRecordKind.EXECUTION_STARTED)
    return Execution(execution_id, code_identity, process_id, log)


def utc_timestamp() -> str:
    """A wall-clock timestamp for execution metadata only (never for a reproducible surface)."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class GitProvenance:
    """Provenance of the source tree an Execution ran from: informational, outside every equality
    claim, never part of code identity (the Git SHA does not participate)."""

    git_sha: str | None
    worktree_standing: str | None


def git_provenance(cwd: str) -> GitProvenance:
    """``HEAD`` and whether the worktree is clean, or ``None`` where Git or a commit does not exist."""
    def run(*args: str) -> str | None:
        try:
            done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return None
        return done.stdout.strip() if done.returncode == 0 else None

    sha = run("rev-parse", "HEAD")
    status = run("status", "--porcelain")
    return GitProvenance(sha, None if status is None else ("dirty" if status else "clean"))
