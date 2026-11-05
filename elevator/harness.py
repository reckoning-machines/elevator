"""The evaluation harness core (plan cut 8; evaluation §7): Experiment definition and identity, paired
comparison, null-aware aggregation, and the two result documents.

Executing a Run. ``execute_experiment`` runs the procedure of §7.2 and takes the Run executor as a
parameter: for each scenario and seed it generates the Trace **once** and hands that one immutable Trace to
the executor for every policy. The executor is the public ``simulate`` (composed by ``cli``, and later
``web``, which may depend on ``api``), so a Run is an ordinary Execution with its own ``execution_id`` and
the one policy resolver, ``policies.make_policy``, stays the only place a name becomes a policy. The
harness itself imports ``domain``, ``scenarios`` and ``reporting`` only: it needs no ``api`` or
``operations`` edge, which the dependency table does not list. Everything else here is a pure function of
its arguments.

Authority: the Experiment definition and its hash (authority row 32), the experiment execution id
(row 33) and the result documents (row 34) belong to the harness. The result surface is DERIVED from
the Runs' Reproducible Output Surfaces and carries no per-Run ``execution_id``, path, timestamp or
process fact; the execution metadata is the only place those appear.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from elevator.domain import Configuration, Refusal, Trace, canonical_json, freeze, sha256_hex
from elevator.reporting import render_rational
from elevator.scenarios import Scenario, ScenarioRefusal, generate, resolve_parameters

DEFAULT_SEEDS = tuple(range(20))
DEFAULT_POLICY_NAMES = ("round_robin", "nearest_car", "cost_based")

#: The metrics aggregated across seeds (evaluation §4.1, §7.4), by path into ``summary.json``.
#: ``elevator_utilisation`` is a vector with one entry per elevator and is aggregated per elevator.
SCALAR_METRICS = ("n", "completed", "unserved", "makespan", "deferred.count", "wrong_way.count",
                  "tail_share", "tail_ratio", "wait.min", "wait.max", "wait.mean", "wait.median", "wait.p95",
                  "wait.std", "total.min", "total.max", "total.mean", "total.median", "total.p95", "total.std",
                  "travel.mean", "wrong_way.mean_extra")

#: The metrics compared pairwise against each baseline (evaluation §7.4 names "metric" without
#: listing them; these are the performance metrics, all of which are better when lower).
PAIRED_METRICS = ("wait.mean", "wait.median", "wait.p95", "wait.max", "total.mean", "total.median",
                  "total.p95", "total.max", "tail_share", "makespan", "deferred.count", "wrong_way.count")


class ExperimentIntegrityError(Exception):
    """A result set breaks the fair-comparison guarantee or silently lacks a run: two policies saw
    different Traces for one (scenario, seed), or a (scenario, seed, policy) cell is missing or
    duplicated. Never repaired and never averaged over."""


# ---------------------------------------------------------------------------
# The Experiment definition (§7.1)
# ---------------------------------------------------------------------------

def _refuse(parameter: str, detail: str) -> Refusal:
    return Refusal("INVALID_CONFIGURATION", f"{parameter}: {detail}")


@dataclass(frozen=True)
class ExperimentDefinition:
    """Everything consequential about an Experiment, in its effective (default-filled) form, so that
    ``definition_hash`` covers every parameter: the building, the scenarios with their effective
    parameters, the seeds and the policies with their effective parameters. ``max_ticks`` is not part of
    it: every Run uses the default bound, never an override."""

    document: Mapping[str, Any]

    @staticmethod
    def create(num_floors: int, num_elevators: int, capacity: int, scenarios: Sequence[Any], *,
               initial_floors: Sequence[int] | None = None, seeds: Sequence[int] | None = None,
               policies: Sequence[Any] | None = None) -> "ExperimentDefinition":
        """Validate and normalise a definition. Every refusal happens here, before any Run could
        execute: the building's configuration domain; every scenario's parameters (including the sparse
        cross-parameter precondition, checked by generating its first Trace); the seed domain; the
        policies' names and parameters. Empty lists and repeated seeds or policy names are refused,
        because they would leave a result cell empty or ambiguous."""
        building = Configuration.create(num_floors, num_elevators, capacity, initial_floors=initial_floors)
        seed_list = list(DEFAULT_SEEDS if seeds is None else seeds)
        if not seed_list:
            raise _refuse("seeds", "at least one seed is required")
        if len(set(seed_list)) != len(seed_list):
            raise ScenarioRefusal(("seeds",), "a seed may appear once: results are keyed by (scenario, seed, policy)")
        policy_specs = [(n, None) for n in DEFAULT_POLICY_NAMES] if policies is None else \
            [(p, None) if isinstance(p, str) else (p[0], p[1]) for p in policies]
        if not policy_specs:
            raise _refuse("policies", "at least one policy is required")
        names = [name for name, _ in policy_specs]
        if len(set(names)) != len(names):
            raise _refuse("policies", "a policy name may appear once: results are keyed by policy")
        scenario_specs = list(scenarios)
        if not scenario_specs:
            raise _refuse("scenarios", "at least one scenario is required")
        policy_docs = []
        for name, params in policy_specs:
            cfg = Configuration.create(num_floors, num_elevators, capacity, initial_floors=initial_floors,
                                       policy=name, policy_params=params)
            policy_docs.append({"name": name, "params": dict(cfg.policy_params)})
        scenario_docs = []
        for spec in scenario_specs:
            pattern, params = (spec["pattern"], spec.get("parameters", {})) if isinstance(spec, Mapping) else spec
            for seed in seed_list:
                Scenario(pattern, params, seed)  # the seed domain and every building-independent rule
            first = Scenario(pattern, params, seed_list[0])
            generate(first, num_floors, num_elevators, capacity)  # the building-dependent rules, before any Run
            scenario_docs.append({"pattern": pattern, "parameters": resolve_parameters(first, num_floors)})
        document = {"configuration": {"num_floors": num_floors, "num_elevators": num_elevators,
                                      "capacity": capacity, "initial_floors": list(building.initial_floors)},
                    "scenarios": scenario_docs, "seeds": seed_list, "policies": policy_docs}
        return ExperimentDefinition(freeze(document))

    @staticmethod
    def from_document(doc: Mapping[str, Any]) -> "ExperimentDefinition":
        """Build a definition from the JSON document form (``configuration``, ``scenarios``, optional
        ``seeds`` and ``policies``). Unknown keys are refused, never ignored."""
        allowed = {"configuration", "scenarios", "seeds", "policies"}
        if not isinstance(doc, Mapping) or set(doc) - allowed:
            raise _refuse("definition", f"keys must be among {sorted(allowed)}")
        cfg = doc.get("configuration")
        if not isinstance(cfg, Mapping) or set(cfg) - {"num_floors", "num_elevators", "capacity", "initial_floors"} \
                or not {"num_floors", "num_elevators", "capacity"} <= set(cfg):
            raise _refuse("configuration", "needs num_floors, num_elevators, capacity (and optionally initial_floors)")
        policies = doc.get("policies")
        if policies is not None:
            policies = [p if isinstance(p, str) else (p["name"], p.get("params"))
                        for p in policies]
        return ExperimentDefinition.create(cfg["num_floors"], cfg["num_elevators"], cfg["capacity"],
                                           doc.get("scenarios", []), initial_floors=cfg.get("initial_floors"),
                                           seeds=doc.get("seeds"), policies=policies)

    @property
    def definition_hash(self) -> str:
        """SHA-256 of the canonical JSON of the definition."""
        return sha256_hex(canonical_json(self.document))

    def experiment_execution_id(self, code_identity: str) -> str:
        """SHA-256 of ``(definition_hash, code_identity)``: a hash, not a random id, because an Experiment
        is reproducible from its definition under the same code."""
        return sha256_hex(canonical_json([self.definition_hash, code_identity]))

    @property
    def building(self) -> tuple[int, int, int]:
        c = self.document["configuration"]
        return c["num_floors"], c["num_elevators"], c["capacity"]

    @property
    def seeds(self) -> tuple[int, ...]:
        return tuple(self.document["seeds"])

    @property
    def num_scenarios(self) -> int:
        return len(self.document["scenarios"])

    @property
    def num_policies(self) -> int:
        return len(self.document["policies"])

    def policy_index(self, name: str) -> int | None:
        for i, p in enumerate(self.document["policies"]):
            if p["name"] == name:
                return i
        return None


# ---------------------------------------------------------------------------
# Results: one row per (scenario, seed, policy)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RunResult:
    """One Run of an Experiment: its identity, outcome and the summary of evaluation §4. ``summary`` is
    the Run's ``summary.json`` document, so every value is exactly as reported (an integer, a
    three-digit decimal string or ``None``). It holds no execution fact."""

    scenario: int
    seed: int
    policy: int
    run_id: str
    trace_hash: str
    standing: str
    final_tick: int
    halt_reason: str | None
    summary: Mapping[str, Any]

    def document(self) -> dict[str, Any]:
        return {"scenario": self.scenario, "seed": self.seed, "policy": self.policy, "run_id": self.run_id,
                "trace_hash": self.trace_hash,
                "outcome": {"standing": self.standing, "final_tick": self.final_tick,
                            "halt_reason": self.halt_reason},
                "summary": self.summary}


def check_complete_and_paired(definition: ExperimentDefinition, results: Sequence[RunResult]) -> None:
    """The fair-comparison witness (evaluation §7.2) and the completeness check. Every
    (scenario, seed, policy) cell must appear exactly once, so a failed Run can never be dropped and bias
    an aggregate, and every policy of one (scenario, seed) must have run on one Trace hash."""
    expected = {(s, seed, p) for s in range(definition.num_scenarios) for seed in definition.seeds
                for p in range(definition.num_policies)}
    keys = [(r.scenario, r.seed, r.policy) for r in results]
    if len(keys) != len(set(keys)):
        raise ExperimentIntegrityError("a (scenario, seed, policy) cell appears more than once")
    if set(keys) != expected:
        missing = sorted(expected - set(keys))[:3]
        raise ExperimentIntegrityError(f"{len(expected - set(keys))} cell(s) missing or foreign, for example {missing}")
    hashes: dict[tuple[int, int], set[str]] = {}
    for r in results:
        hashes.setdefault((r.scenario, r.seed), set()).add(r.trace_hash)
    broken = sorted(k for k, v in hashes.items() if len(v) != 1)
    if broken:
        raise ExperimentIntegrityError(f"policies saw different Traces for (scenario, seed) {broken[:3]}: "
                                       "the comparison is not paired")


# ---------------------------------------------------------------------------
# Aggregation (§7.4): null-aware, exact
# ---------------------------------------------------------------------------

def reported(summary: Mapping[str, Any], path: str) -> Any:
    """The value of a metric exactly as ``summary.json`` reports it, or ``None`` where it is null or the
    summary has no such field (a halted run's summary has no metrics)."""
    node: Any = summary
    for part in path.split("."):
        if isinstance(node, list):
            node = node[int(part)] if int(part) < len(node) else None
        elif isinstance(node, Mapping):
            node = node.get(part)
        else:
            return None
        if node is None:
            return None
    return node


def _exact(value: Any) -> Fraction | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError(f"not a reported metric value: {value!r}")
    return Fraction(value)


def _median(values: Sequence[Fraction]) -> Fraction:
    ordered = sorted(values)
    n = len(ordered)
    return ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2


def metric_names(num_elevators: int) -> tuple[str, ...]:
    return SCALAR_METRICS + tuple(f"elevator_utilisation.{i}" for i in range(num_elevators))


def aggregate_cell(results: Sequence[RunResult], num_elevators: int) -> dict[str, Any]:
    """The aggregates of one (scenario, policy) cell across seeds, from its Runs in seed order. A
    ``HALTED`` Run contributes only to ``halted_count`` and to the listing of its ``unserved`` count and
    halt reason; a null value is excluded, never counted as zero; each aggregate reports ``n_defined``,
    and its mean and median are ``null`` when ``n_defined`` is 0. The full per-seed vector is published
    (``null`` for a halted or undefined seed) so a reader can judge the spread."""
    halted = [r for r in results if r.standing == "HALTED"]
    out: dict[str, Any] = {"K": len(results), "halted_count": len(halted),
                           "halted": [{"seed": r.seed, "unserved": r.summary.get("unserved"),
                                       "halt_reason": r.halt_reason} for r in halted]}
    metrics: dict[str, Any] = {}
    for name in metric_names(num_elevators):
        vector = [None if r.standing == "HALTED" else reported(r.summary, name) for r in results]
        defined = [_exact(v) for v in vector if v is not None]
        metrics[name] = {"n_defined": len(defined),
                         "mean": render_rational(sum(defined, Fraction(0)) / len(defined)) if defined else None,
                         "median": render_rational(_median(defined)) if defined else None,
                         "per_seed": vector}
    out["metrics"] = metrics
    return out


def paired_cell(policy_runs: Sequence[RunResult], baseline_runs: Sequence[RunResult]) -> dict[str, Any]:
    """Paired differences ``metric(policy) - metric(baseline)`` on the same Trace, seed by seed, over the
    seeds where both Runs are ``COMPLETED`` and both values are defined. Negative means the policy's
    value was lower, which is better for every paired metric. ``n_pairs`` is reported beside each
    aggregate, and the mean, median and the better/equal/worse counts are ``null`` when it is 0."""
    by_seed = {r.seed: r for r in baseline_runs}
    out: dict[str, Any] = {}
    for name in PAIRED_METRICS:
        diffs = []
        for r in policy_runs:
            b = by_seed.get(r.seed)
            if b is None or r.standing != "COMPLETED" or b.standing != "COMPLETED":
                continue
            x, y = _exact(reported(r.summary, name)), _exact(reported(b.summary, name))
            if x is not None and y is not None:
                diffs.append(x - y)
        out[name] = {"n_pairs": len(diffs),
                     "mean": render_rational(sum(diffs, Fraction(0)) / len(diffs)) if diffs else None,
                     "median": render_rational(_median(diffs)) if diffs else None,
                     "better": sum(1 for d in diffs if d < 0) if diffs else None,
                     "equal": sum(1 for d in diffs if d == 0) if diffs else None,
                     "worse": sum(1 for d in diffs if d > 0) if diffs else None}
    return out


def results_document(definition: ExperimentDefinition, code_identity: str,
                     results: Sequence[RunResult]) -> dict[str, Any]:
    """The Reproducible Experiment Result Surface (evaluation §7.4, authority row 34): the definition,
    its hash, the experiment execution id, the code identity, every Run's identity, outcome and
    summary in (scenario, seed, policy) order, and per (scenario, policy) the aggregates and, for the
    ``cost_based`` policy, the paired differences against each baseline. A pure function of the Runs'
    summaries: it can contain no execution id, path, timestamp or process fact."""
    check_complete_and_paired(definition, results)
    ordered = sorted(results, key=lambda r: (r.scenario, definition.seeds.index(r.seed), r.policy))
    n_elev = definition.building[1]
    cost = definition.policy_index("cost_based")
    aggregates = []
    for s in range(definition.num_scenarios):
        cell = {p: [r for r in ordered if r.scenario == s and r.policy == p] for p in range(definition.num_policies)}
        for p in range(definition.num_policies):
            entry = {"scenario": s, "policy": p, **aggregate_cell(cell[p], n_elev)}
            if cost is not None and p == cost:
                entry["paired_against"] = {str(b): paired_cell(cell[cost], cell[b])
                                           for b in range(definition.num_policies) if b != cost}
            aggregates.append(entry)
    return {"definition": definition.document, "definition_hash": definition.definition_hash,
            "experiment_execution_id": definition.experiment_execution_id(code_identity),
            "code_identity": code_identity, "runs": [r.document() for r in ordered], "aggregates": aggregates}


def results_bytes(definition: ExperimentDefinition, code_identity: str, results: Sequence[RunResult]) -> bytes:
    return canonical_json(results_document(definition, code_identity, results))


def experiment_execution_metadata(*, experiment_execution_id: str, definition_hash: str,
                                  runs: Sequence[Mapping[str, Any]], pid: int | None = None,
                                  started_at: str | None = None, ended_at: str | None = None) -> bytes:
    """``experiment_execution.json`` (authority row 34, a RECEIPT of the execution): the experiment
    execution id and, per Run, its own random ``execution_id`` and output path, the process and the
    timestamps. Supplied by the caller; outside every equality claim."""
    return canonical_json({"experiment_execution_id": experiment_execution_id, "definition_hash": definition_hash,
                           "runs": [dict(r) for r in runs], "pid": pid, "started_at": started_at,
                           "ended_at": ended_at})


# ---------------------------------------------------------------------------
# Execution (§7.2): one Trace per (scenario, seed), the same Trace for every policy
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RunExecution:
    """What the Run executor returns for one Run: the Run's identity and outcome, its ``summary.json``
    document, and the execution facts (its own ``execution_id`` and output path), which go to the
    execution metadata and never to the result surface."""

    run_id: str
    trace_hash: str
    standing: str
    final_tick: int
    halt_reason: str | None
    summary: Mapping[str, Any]
    execution_id: str
    output_path: str | None


#: ``(trace, configuration, output_dir) -> RunExecution``: one Run on the given Trace under the policy the
#: Configuration names. A ``HALTED`` Run is a result, not an exception.
RunExecutor = Callable[[Trace, Configuration, "str | None"], RunExecution]


@dataclass(frozen=True)
class ExperimentExecution:
    """An executed Experiment: the Runs in (scenario, seed, policy) order and, per Run, its execution
    facts."""

    definition: ExperimentDefinition
    code_identity: str
    results: tuple[RunResult, ...]
    run_facts: tuple[Mapping[str, Any], ...]

    @property
    def experiment_execution_id(self) -> str:
        return self.definition.experiment_execution_id(self.code_identity)

    def results_bytes(self) -> bytes:
        """``experiment_results.json``: byte-identical for every execution of the same definition under
        the same code (evaluation §7.3)."""
        return results_bytes(self.definition, self.code_identity, self.results)

    def execution_metadata_bytes(self, *, pid: int | None = None, started_at: str | None = None,
                                 ended_at: str | None = None) -> bytes:
        """``experiment_execution.json``: the per-Run ``execution_id``s and paths, the process and the
        timestamps. May differ between executions."""
        return experiment_execution_metadata(
            experiment_execution_id=self.experiment_execution_id, definition_hash=self.definition.definition_hash,
            runs=self.run_facts, pid=pid, started_at=started_at, ended_at=ended_at)


def execute_experiment(definition: ExperimentDefinition, code_identity: str, execute_run: RunExecutor, *,
                       output_dir: str | None = None) -> ExperimentExecution:
    """Execute an Experiment: for each scenario, for each seed, generate the Trace once and run every
    policy of the definition on that one Trace. Nothing is tuned per seed and nothing is regenerated per
    policy; a Run whose Trace hash differs from the shared Trace's is an integrity error, as is any
    missing or duplicated cell. A Run that halts is recorded as ``HALTED`` with its reason and the
    Experiment continues; it is reported under ``halted_count`` and never dropped from the aggregates."""
    floors, elevators, capacity = definition.building
    initial = list(definition.document["configuration"]["initial_floors"])
    seeds = definition.seeds
    results: list[RunResult] = []
    facts: list[dict[str, Any]] = []
    for s, scenario in enumerate(definition.document["scenarios"]):
        for seed in seeds:
            trace = generate(Scenario(scenario["pattern"], dict(scenario["parameters"]), seed),
                             floors, elevators, capacity)  # once per (scenario, seed)
            for p, policy in enumerate(definition.document["policies"]):
                configuration = Configuration.create(floors, elevators, capacity, initial_floors=initial,
                                                     policy=policy["name"], policy_params=dict(policy["params"]))
                run = execute_run(trace, configuration, output_dir)
                if run.trace_hash != trace.trace_hash:
                    raise ExperimentIntegrityError(
                        f"scenario {s}, seed {seed}, policy {p} ran on Trace {run.trace_hash}, not the shared "
                        f"Trace {trace.trace_hash}")
                results.append(RunResult(s, seed, p, run.run_id, run.trace_hash, run.standing, run.final_tick,
                                         run.halt_reason, run.summary))
                facts.append({"scenario": s, "seed": seed, "policy": p, "execution_id": run.execution_id,
                              "output_path": run.output_path})
    check_complete_and_paired(definition, results)
    return ExperimentExecution(definition, code_identity, tuple(results), tuple(facts))
