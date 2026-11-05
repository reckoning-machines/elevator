"""Command line (plan cut 8): ``simulate`` and ``experiment``. (``store init`` and ``resume`` arrive with the
checkpoint module in cut 9.) The CLI only parses arguments, validates, calls the public API and the harness,
and renders results; it contains no simulation mechanics, parses no request rows beyond splitting CSV cells
(every semantic rule belongs to ``normalize_requests``) and adds no default the governing documents do not
state: the building (``--floors``, ``--elevators``, ``--capacity``) is required, the policy defaults to
``cost_based`` with the defaults of scheduler §6.3, and initial floors default to 0.

``store init`` creates a Store; ``simulate`` with ``--store`` and a checkpoint control (``--checkpoint-at`` or
``--checkpoint-every``) writes Continuation Documents at tick boundaries (never by default); ``resume`` continues
an Execution from its document alone. ``api.simulate`` is unchanged: the Store path composes ``create_engine``
with the checkpoint module.

Run under the supported execution contract: ``python -B -m elevator.cli ...``.

Exit codes (distinct for each failure class):

    0  the Run completed (or the Experiment executed)
    2  command-line usage error
    3  invalid input, request file, Configuration, scenario or Experiment definition (a refusal)
    4  the simulation HALTED (a named reason is printed; it is never reported as success)
    5  an output could not be written
    6  unsupported execution environment (not run with ``-B``, or a ``__pycache__`` in the package)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections.abc import Sequence
from typing import Any

from elevator import api, checkpoint, harness, reporting
from elevator.domain import (
    Configuration,
    OperationalRecordKind,
    Refusal,
    Trace,
    detect_code_identity_drift,
    establish_code_identity,
)
from elevator.operations import Execution, git_provenance, utc_timestamp
from elevator.reporting import RunRecord
from elevator.scenarios import Scenario, generate

EXIT_OK, EXIT_USAGE, EXIT_REFUSED, EXIT_HALTED, EXIT_OUTPUT, EXIT_ENVIRONMENT = 0, 2, 3, 4, 5, 6
CSV_HEADER = ["time", "id", "source", "dest"]


def _kv(text: str) -> tuple[str, int]:
    name, sep, value = text.partition("=")
    if not sep or not name or not value.lstrip("-").isdigit():
        raise argparse.ArgumentTypeError(f"expected NAME=INTEGER, got {text!r}")
    return name, int(value)


def _read_requests(path: str) -> list[list[str]]:
    """Split a CSV file into rows of cells for ``normalize_requests`` (the one parser of row semantics).
    A first row that is exactly the header ``time,id,source,dest`` is skipped."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = [row for row in csv.reader(fh)]
    return rows[1:] if rows and rows[0] == CSV_HEADER else rows


def _parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(prog="python -B -m elevator.cli", description=__doc__.split("\n\n")[0])
    sub = top.add_subparsers(dest="command", required=True)
    sim = sub.add_parser("simulate", help="run one simulation from a requests file or a generated scenario")
    source = sim.add_mutually_exclusive_group(required=True)
    source.add_argument("--requests", metavar="FILE.csv", help="rows of time,id,source,dest")
    source.add_argument("--scenario", metavar="PATTERN", help="a scenario pattern of evaluation §6.3")
    sim.add_argument("--seed", type=int, help="scenario seed (required with --scenario)")
    sim.add_argument("--param", action="append", default=[], type=_kv, metavar="NAME=INT",
                     help="a scenario parameter (repeatable), for example num_requests=40")
    sim.add_argument("--floors", type=int, required=True)
    sim.add_argument("--elevators", type=int, required=True)
    sim.add_argument("--capacity", type=int, required=True)
    sim.add_argument("--policy", default="cost_based")
    sim.add_argument("--policy-param", action="append", default=[], type=_kv, metavar="NAME=INT")
    sim.add_argument("--initial-floors", metavar="A,B,...", help="one floor per elevator (default all 0)")
    sim.add_argument("--max-ticks", type=int)
    sim.add_argument("--out", metavar="DIR", help="write the Reproducible Output Surface and evidence here")
    sim.add_argument("--store", metavar="DIR", help="a Store (see `store init`); needs a checkpoint control")
    sim.add_argument("--checkpoint-at", type=int, metavar="T", help="write a checkpoint at the start of tick T")
    sim.add_argument("--checkpoint-every", type=int, metavar="K", help="write a checkpoint every K ticks")
    sim.add_argument("--pause-after-checkpoint", action="store_true",
                     help="witness-only: block after the first checkpoint write, holding in-memory state")
    sim.add_argument("--witness-instrumentation", action="store_true",
                     help="append a DIAGNOSTIC record per emitted TickRecord to the Operational Log")
    store = sub.add_parser("store", help="Store administration")
    store_sub = store.add_subparsers(dest="store_command", required=True)
    init = store_sub.add_parser("init", help="create a Store")
    init.add_argument("path", metavar="DIR")
    res = sub.add_parser("resume", help="continue an Execution from its Continuation Document alone")
    res.add_argument("--store", metavar="DIR", required=True)
    res.add_argument("--resume", metavar="EXECUTION_ID", required=True)
    res.add_argument("--out", metavar="DIR", help="write the Reproducible Output Surface and evidence here")
    res.add_argument("--witness-instrumentation", action="store_true")
    exp = sub.add_parser("experiment", help="execute an Experiment definition (evaluation §7)")
    exp.add_argument("--config", metavar="FILE.json", required=True)
    exp.add_argument("--out", metavar="DIR", required=True)
    exp.add_argument("--summary-only", action="store_true",
                     help="write only the two experiment files, not each Run's directory")
    return top


def _refuse_float(text: str) -> Any:
    raise Refusal("INVALID_CONFIGURATION", f"definition: numbers must be integers, got {text}")


def _pause_forever() -> None:
    while True:
        time.sleep(3600)


def _finish(engine: Any, execution: Execution, identity: Any, configuration: Configuration, trace: Trace,
            established: Any, out: str | None, store_root: str | None) -> None:
    """Common end of a Store-path Execution: the surface from the final History, the output location (which
    holds the surface and a copy of the Operational Log, the Store file remaining the log), the code-identity
    drift check and ``EXECUTION_ENDED``."""
    record = RunRecord(configuration, trace, identity, engine.history, engine.passengers)
    surface = reporting.reproducible_surface(record)
    root = None
    try:
        if out is not None:
            git = git_provenance(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            root = os.path.join(out, identity.run_id, execution.execution_id)
            reporting.write_files(root, {**surface, "execution_metadata.json": reporting.execution_metadata(
                execution_id=execution.execution_id, run_id=identity.run_id, standing=engine.outcome.standing,
                store_id=None if store_root is None else checkpoint.read_store(store_root),
                git_sha=git.git_sha, worktree_standing=git.worktree_standing, pid=execution.pid,
                ended_at=utc_timestamp())})
    except OSError as exc:
        raise api.OutputWriteError(f"could not write the output for run {identity.run_id}: {exc}") from exc
    finally:
        drift = detect_code_identity_drift(established, execution_id=execution.execution_id,
                                           op_seq=execution.log.next_op_seq)
        if drift is not None:
            execution.log.append_record(drift)
        execution.log.append(OperationalRecordKind.EXECUTION_ENDED)
        if root is not None and execution.log.bound:
            execution.log.copy_to(root)
        execution.log.close()


def _report(execution: Execution, identity: Any, outcome: Any, writer: Any, out: str | None) -> int:
    print(f"run_id: {identity.run_id}")
    print(f"execution_id: {execution.execution_id}")
    print(f"standing: {outcome.standing}")
    print(f"final_tick: {outcome.final_tick}")
    if outcome.halt_reason is not None:
        print(f"halt_reason: {outcome.halt_reason}")
    if writer is not None and writer.has_document:
        print(f"write_sequence: {writer.last_known}")
    print(f"output: {os.path.join(out, identity.run_id, execution.execution_id) if out else '(none)'}")
    return EXIT_OK if outcome.standing == "COMPLETED" else EXIT_HALTED


def _run_simulate_with_store(args: argparse.Namespace, rows: Any, initial: Any) -> int:
    established = establish_code_identity()
    engine = api.create_engine(rows, args.elevators, args.floors, args.capacity, policy=args.policy,
                               policy_params=dict(args.policy_param) or None, initial_floors=initial,
                               max_ticks=args.max_ticks)
    execution, identity = engine.execution, engine.run_identity
    checkpoint.bind_store(args.store, execution)  # checkpoint controls are set: bound to the Store at creation
    if args.witness_instrumentation:
        checkpoint.instrument(engine, execution)
    writer = checkpoint.CheckpointWriter(args.store, execution, identity, engine._config, engine._trace)
    controls = checkpoint.Controls(args.checkpoint_at, args.checkpoint_every, args.pause_after_checkpoint)
    outcome = checkpoint.drive(engine, writer, controls, pause=_pause_forever)
    _finish(engine, execution, identity, engine._config, engine._trace, established, args.out, args.store)
    return _report(execution, identity, outcome, writer, args.out)


def _run_resume(args: argparse.Namespace) -> int:
    resumed = checkpoint.resume(args.store, args.resume)
    execution, loaded = resumed.execution, resumed.loaded
    if args.witness_instrumentation:
        checkpoint.instrument(resumed.engine, execution)
    outcome = checkpoint.drive(resumed.engine, resumed.writer, checkpoint.Controls(),
                               skip_boundary=loaded.state.t)
    _finish(resumed.engine, execution, loaded.identity, loaded.configuration, loaded.trace, loaded.established,
            args.out, args.store)
    return _report(execution, loaded.identity, outcome, resumed.writer, args.out)


def _run_simulate_instrumented(args: argparse.Namespace, rows: Any, initial: Any) -> int:
    """``simulate --witness-instrumentation`` with no Store: the same Execution as ``api.simulate`` (no document,
    the log bound to the output location only when one is given) with the flag's DIAGNOSTIC record per emitted
    TickRecord, so the reference Execution of the witness has an Operational Log comparable with the others."""
    established = establish_code_identity()
    engine = api.create_engine(rows, args.elevators, args.floors, args.capacity, policy=args.policy,
                               policy_params=dict(args.policy_param) or None, initial_floors=initial,
                               max_ticks=args.max_ticks)
    execution, identity = engine.execution, engine.run_identity
    checkpoint.instrument(engine, execution)
    started_at = utc_timestamp()
    outcome = engine.run()
    record = RunRecord(engine._config, engine._trace, identity, engine.history, engine.passengers)
    try:
        if args.out is not None:
            git = git_provenance(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            reporting.write_execution_output(args.out, identity.run_id, execution, reporting.reproducible_surface(record),
                                             reporting.execution_metadata(
                                                 execution_id=execution.execution_id, run_id=identity.run_id,
                                                 standing=outcome.standing, git_sha=git.git_sha,
                                                 worktree_standing=git.worktree_standing, pid=execution.pid,
                                                 started_at=started_at, ended_at=utc_timestamp()))
    except OSError as exc:
        raise api.OutputWriteError(f"could not write the output for run {identity.run_id}: {exc}") from exc
    finally:
        drift = detect_code_identity_drift(established, execution_id=execution.execution_id,
                                           op_seq=execution.log.next_op_seq)
        if drift is not None:
            execution.log.append_record(drift)
        execution.log.append(OperationalRecordKind.EXECUTION_ENDED)
        execution.log.close()
    return _report(execution, identity, outcome, None, args.out)


def _run_simulate(args: argparse.Namespace) -> int:
    controls_set = args.checkpoint_at is not None or args.checkpoint_every is not None
    if (args.store is not None) != controls_set or (args.pause_after_checkpoint and not controls_set):
        print("error: --store needs --checkpoint-at or --checkpoint-every, and they need --store "
              "(an Execution with no checkpoint controls never touches a Store)", file=sys.stderr)
        return EXIT_USAGE
    if args.checkpoint_every is not None and args.checkpoint_every < 1:
        print("error: --checkpoint-every must be at least 1", file=sys.stderr)
        return EXIT_USAGE
    initial = None if args.initial_floors is None else [int(x) for x in args.initial_floors.split(",")]
    if args.scenario is not None:
        if args.seed is None:
            print("error: --seed is required with --scenario", file=sys.stderr)
            return EXIT_USAGE
        trace = generate(Scenario(args.scenario, dict(args.param), args.seed), args.floors, args.elevators,
                         args.capacity)
        rows: Any = trace.canonical_rows()
    else:
        rows = _read_requests(args.requests)
    if args.store is not None:
        return _run_simulate_with_store(args, rows, initial)
    if args.witness_instrumentation:
        return _run_simulate_instrumented(args, rows, initial)
    result = api.simulate(rows, args.elevators, args.floors, args.capacity, policy=args.policy,
                          policy_params=dict(args.policy_param) or None, initial_floors=initial,
                          max_ticks=args.max_ticks, output_dir=args.out)
    print(f"run_id: {result.run_id}")
    print(f"execution_id: {result.execution_id}")
    print(f"standing: {result.standing}")
    print(f"final_tick: {result.final_tick}")
    if result.halt_reason is not None:
        print(f"halt_reason: {result.halt_reason}")
    print(f"output: {result.output_path if result.output_path else '(none)'}")
    return EXIT_OK if result.standing == "COMPLETED" else EXIT_HALTED


def run_executor(code_identity: str) -> harness.RunExecutor:
    """The Run executor the harness receives: the public ``simulate`` on the harness's one Trace."""
    def execute(trace: Trace, configuration: Configuration, output_dir: str | None) -> harness.RunExecution:
        result = api.simulate(trace.canonical_rows(), configuration.num_elevators, configuration.num_floors,
                              configuration.capacity, policy=configuration.policy,
                              policy_params=dict(configuration.policy_params),
                              initial_floors=list(configuration.initial_floors), output_dir=output_dir)
        if result.identity.code_identity != code_identity:
            raise harness.ExperimentIntegrityError("the code identity changed during the Experiment")
        return harness.RunExecution(result.run_id, result.identity.trace_hash, result.standing, result.final_tick,
                                    result.halt_reason, result.summary, result.execution_id, result.output_path)
    return execute


def _run_experiment(args: argparse.Namespace) -> int:
    established = establish_code_identity()
    with open(args.config, encoding="utf-8") as fh:
        document = json.load(fh, parse_float=_refuse_float)
    definition = harness.ExperimentDefinition.from_document(document)
    root = os.path.join(args.out, definition.experiment_execution_id(established.identity))
    if os.path.exists(os.path.join(root, "experiment_results.json")):  # refuse before running anything
        raise api.OutputWriteError(f"{root} already holds this Experiment's results; evidence is never "
                                   "overwritten, so use a different --out")
    started_at = api.utc_timestamp()
    run_output = None if args.summary_only else args.out
    execution = harness.execute_experiment(definition, established.identity, run_executor(established.identity),
                                           output_dir=run_output)
    try:
        reporting.write_files(root, {
            "experiment_results.json": execution.results_bytes(),
            "experiment_execution.json": execution.execution_metadata_bytes(
                pid=os.getpid(), started_at=started_at, ended_at=api.utc_timestamp())})
    except OSError as exc:
        raise api.OutputWriteError(f"could not write the experiment files to {root}: {exc}") from exc
    halted = sum(1 for r in execution.results if r.standing == "HALTED")
    print(f"experiment_execution_id: {execution.experiment_execution_id}")
    print(f"definition_hash: {definition.definition_hash}")
    print(f"runs: {len(execution.results)}")
    print(f"halted_count: {halted}")
    print(f"output: {root}")
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "simulate":
            return _run_simulate(args)
        if args.command == "resume":
            return _run_resume(args)
        if args.command == "store":
            print(f"store_id: {checkpoint.init_store(args.path)}")
            return EXIT_OK
        return _run_experiment(args)
    except Refusal as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return EXIT_ENVIRONMENT if refusal.reason == "UNSUPPORTED_EXECUTION_ENVIRONMENT" else EXIT_REFUSED
    except FileExistsError as exc:
        print(f"output error: {exc}", file=sys.stderr)
        return EXIT_OUTPUT
    except (FileNotFoundError, IsADirectoryError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"refused: cannot read the input: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    except harness.ExperimentIntegrityError as exc:
        print(f"experiment integrity error: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    except api.OutputWriteError as exc:
        print(f"output error: {exc}", file=sys.stderr)
        return EXIT_OUTPUT


if __name__ == "__main__":
    sys.exit(main())
