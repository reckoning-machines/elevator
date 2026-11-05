"""Public boundaries (evaluation_design §2): ``normalize_requests``, ``simulate`` and ``create_engine``.

Three boundaries share one engine implementation; none is a second simulation path. This module only
composes existing components: the shared input boundary and Configuration validation (``domain``), the
policy a Configuration names (``policies.make_policy``, the one resolver, construction only; owner
decision 009), the engine, the Reproducible Output Surface (``reporting``) and the Execution handle and
Operational Log (``operations``). It contains no simulation mechanics and never imports ``checkpoint``.

Failure behaviour is distinct for each failure:

- invalid input, an invalid Configuration or an unsupported execution environment: a ``Refusal`` raised
  before any Execution exists (reason ``INPUT_INVALID``, ``SAME_FLOOR_REQUEST``, ``MISSING_SOURCE_ID``,
  ``DUPLICATE_SOURCE_ID``, ``INVALID_CONFIGURATION`` or ``UNSUPPORTED_EXECUTION_ENVIRONMENT``);
- a policy error, an invalid proposal, a horizon or an invariant violation: the Run is ``HALTED`` and the
  result says so (a halted Run is never reported as completed); it is returned, not raised;
- an output write failure: ``OutputWriteError``; nothing is overwritten.
"""

from __future__ import annotations

import functools
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from elevator import reporting
from elevator.domain import (
    PACKAGE_DIR,
    Configuration,
    OperationalRecordKind,
    RunIdentity,
    Trace,
    bind_run,
    detect_code_identity_drift,
    establish_code_identity,
    normalize_requests,
)
from elevator.engine import Engine, SchedulerPolicy
from elevator.operations import Execution, git_provenance, start_execution, utc_timestamp
from elevator.policies import make_policy
from elevator.reporting import RunRecord

__all__ = ["normalize_requests", "simulate", "create_engine", "SimulationResult", "LiveEngine",
           "OutputWriteError", "utc_timestamp"]


class OutputWriteError(Exception):
    """The Reproducible Output Surface or the execution evidence could not be written. The cause is
    chained. Nothing already on disk is overwritten or removed."""


@dataclass(frozen=True)
class SimulationResult:
    """The result of ``simulate``: the Run's identity, its Simulation History and Passenger records, the
    eight-file Reproducible Output Surface as bytes, the Execution that ran it (its Operational Log is in
    memory unless an output directory gave it an evidence root) and the output location, if any."""

    identity: RunIdentity
    record: RunRecord
    surface: Mapping[str, bytes]
    execution: Execution
    output_path: str | None

    @property
    def run_id(self) -> str:
        return self.identity.run_id

    @property
    def execution_id(self) -> str:
        return self.execution.execution_id

    @property
    def summary(self) -> dict[str, Any]:
        return json.loads(self.surface["summary.json"])

    @property
    def standing(self) -> str:
        """``COMPLETED`` or ``HALTED``: read from the History's run-standing event."""
        return self.summary["standing"]

    @property
    def final_tick(self) -> int:
        return self.record.history.events[-1].tick

    @property
    def halt_reason(self) -> str | None:
        return self.summary.get("halt_reason")


class LiveEngine(Engine):
    """The engine ``create_engine`` returns: an ordinary ``Engine`` (the engine module knows nothing of
    operations) that also carries its process-owned Execution handle and Run identity, read-only. The
    Execution's log stays in memory until a later cut gives it an evidence root."""

    def __init__(self, configuration: Configuration, trace: Trace, policy: SchedulerPolicy, *,
                 execution: Execution, identity: RunIdentity) -> None:
        super().__init__(configuration, trace, policy)
        self._execution = execution
        self._identity = identity

    @property
    def execution(self) -> Execution:
        return self._execution

    @property
    def run_identity(self) -> RunIdentity:
        return self._identity


def _prepare(request_rows: Any, num_elevators: int, num_floors: int, capacity: int, policy: str,
             policy_params: Mapping[str, int] | None, initial_floors: Sequence[int] | None,
             max_ticks: int | None, code_identity: str):
    """Shared by both public functions: normalise, validate the Configuration, bind the Run identity and
    resolve the policy the Configuration names. Raises a ``Refusal`` on the first problem."""
    trace = normalize_requests(request_rows, num_floors)
    configuration = Configuration.create(num_floors, num_elevators, capacity, initial_floors=initial_floors,
                                         max_ticks=max_ticks, policy=policy, policy_params=policy_params)
    identity = bind_run(configuration, trace, code_identity)
    return trace, configuration, identity, make_policy(configuration.policy, configuration.policy_params)


@functools.lru_cache(maxsize=1)
def _git() -> Any:
    """Source-tree provenance for execution metadata, read once per process: informational and outside
    every equality claim."""
    return git_provenance(os.path.dirname(PACKAGE_DIR))


def simulate(request_rows: Any, num_elevators: int, num_floors: int, capacity: int,
             policy: str = "cost_based", policy_params: Mapping[str, int] | None = None,
             initial_floors: Sequence[int] | None = None, max_ticks: int | None = None,
             output_dir: str | None = None) -> SimulationResult:
    """The source-facing batch function: normalise; validate the Configuration; create the engine; run to
    the Run outcome; produce the outputs of evaluation §3 in memory and, if ``output_dir`` is given, write
    them to ``<output_dir>/<run_id>/<execution_id>/`` together with the execution evidence. It mints an
    ``execution_id`` like any Execution; its Operational Log lives in memory until an output directory
    gives it an evidence root, and with ``output_dir=None`` it stays in memory and creates no file. It
    never writes a Continuation Document. It refuses to start outside the supported execution contract."""
    established = establish_code_identity()
    trace, configuration, identity, resolved = _prepare(
        request_rows, num_elevators, num_floors, capacity, policy, policy_params, initial_floors, max_ticks,
        established.identity)
    execution = start_execution(established.identity)  # after Trace load: EXECUTION_STARTED, op_seq 1
    started_at = utc_timestamp()
    engine = Engine.create(configuration, trace, resolved)
    outcome = engine.run()
    record = RunRecord(configuration, trace, identity, engine.history, engine.passengers)
    surface = reporting.reproducible_surface(record)
    path = None
    try:
        if output_dir is not None:
            git = _git()
            metadata = reporting.execution_metadata(
                execution_id=execution.execution_id, run_id=identity.run_id, standing=outcome.standing,
                git_sha=git.git_sha, worktree_standing=git.worktree_standing, pid=execution.pid,
                started_at=started_at, ended_at=utc_timestamp())
            path = reporting.write_execution_output(output_dir, identity.run_id, execution, surface, metadata)
    except OSError as exc:
        execution.log.append(OperationalRecordKind.DIAGNOSTIC, payload={"output_write_failed": str(exc)})
        raise OutputWriteError(f"could not write the output for run {identity.run_id}: {exc}") from exc
    finally:
        drift = detect_code_identity_drift(established, execution_id=execution.execution_id,
                                           op_seq=execution.log.next_op_seq)
        if drift is not None:
            execution.log.append_record(drift)
        execution.log.append(OperationalRecordKind.EXECUTION_ENDED)
        execution.log.close()
    return SimulationResult(identity, record, surface, execution, path)


def create_engine(request_rows: Any, num_elevators: int, num_floors: int, capacity: int,
                  policy: str = "cost_based", policy_params: Mapping[str, int] | None = None,
                  initial_floors: Sequence[int] | None = None, max_ticks: int | None = None) -> Engine:
    """The interactive boundary: the same normalisation and validation as ``simulate``; returns a
    ``RUNNING`` engine at tick boundary 0 that the caller steps one tick at a time. Its Execution (read it
    from ``engine.execution``) is created here with its in-memory Operational Log; it is never bound to a
    Store by this function."""
    established = establish_code_identity()
    trace, configuration, identity, resolved = _prepare(
        request_rows, num_elevators, num_floors, capacity, policy, policy_params, initial_floors, max_ticks,
        established.identity)
    execution = start_execution(established.identity)
    return LiveEngine(configuration, trace, resolved, execution=execution, identity=identity)
