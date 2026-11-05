# Cut 8 Implementation Record: Evaluation Harness, Public API and Operations

Status: **IMPLEMENTED / LOCAL VERIFY PASS. 2026-11-05.** Completed under owner decisions 009 (revision 7.3) and 010 (the fixed Experiment); §2 records the original stop, §9 the resumption, §10 the completion. Cut 9 was not started. Nothing is certified.

## 1. Baseline

- Governing design revision 7.2, digests re-verified unchanged before and after: the seven unchanged
  files at record 006's digests; `docs/simulation_semantics.md`
  `821cb89dbbd49ac0c44080f0eddc817ae2f8fece211d5a43f37f8b355d8fbd9d`; `docs/testing_contract.md`
  `b0e78b99a824a0642f14adb45f9ac44e114fc40533ceae72259757b102d96001`.
- Plan: `26f6920ee56c9ef17e053db7ad1f6ed5d2f15e5606258d60069648790d64c24e` (record 008), unchanged.
- Starting standing: cuts 1, 2, 4, 5, 6, 7 `IMPLEMENTED / LOCAL VERIFY PASS`; cut 3 `IMPLEMENTED / LOCAL
  VERIFY PASS / CPOC PENDING`; 173 tests passing.

## 2. The stop: no lawful component may resolve a policy name

**The requirement.** Evaluation §2 gives the public functions as `simulate(request_rows, num_elevators,
num_floors, capacity, policy="cost_based", policy_params=None, ...)` and `create_engine(...)`: both take a
policy **name**. Evaluation §7.1 gives an Experiment's policies as a list of `(name, params)`. Something must
turn a name into a policy object, and the engine takes an object.

**What the governing documents say.** A search of every governing document and the plan finds no rule that
assigns that resolution to a component. The only related text is the architecture's section 7 ("What is
deliberately absent"), which lists "a plugin or registry framework for policies: a dict of three names" and
does not say where the dict lives.

**What the dependency table (architecture §1) permits.**

| Component | Depends on | May import `policies`? |
| --- | --- | --- |
| `api` | `domain`, `engine`, `reporting`, `operations` | no |
| `harness` | `engine` (as a black box), `scenarios`, `reporting` | no |
| `engine` | `domain`, `route`, "the policy interface" | not its internals (the table's "must not depend on" says "policies' internals") |
| `checkpoint` (cut 9; resume must rebuild the policy from `Configuration.policy`) | `domain`, `engine`, `route`, `operations` | no |
| `web` (cut 11; the compare link runs the Trace under three policies) | `api`, `engine`, `reporting`, `harness`, `checkpoint` | no |
| `cli` | "all of the above" | yes |

So `simulate`, the harness's Run loop, resume (cut 9) and the UI's compare each need a resolver that none of
them may import. `api` has no edge to `harness` either, so delegating to the harness does not help. The
engine-side reading ("the policy interface") names an interface, not a factory, and would also need an
engine to policies edge the table does not list.

**Options for the owner** (my classification; the owner decides):

| Option | What changes | Classification |
| --- | --- | --- |
| A. Add `policies` to the `Depends on` of `api`, `harness`, `checkpoint` and `web`, with one name-to-policy function living in `policies` ("the dict of three names") | `docs/architecture.md` §1 table only, so a revision-7.3 record with a new digest for that one file | `ΔO = NONE / ΔS = NONE / ΔA = NONE` in my reading (policies own nothing; no authority row, writer or carrier changes; `architecture.md` is descriptive and decides no semantic question), but the byte change needs the repository's decision process |
| B. Resolve in `cli` only and change the public functions to accept a policy object | the admitted signature `policy="cost_based"` in evaluation §2 | `ΔS` (the take-home's source-facing function changes) |
| C. Resolve inside the engine by name | an `engine -> policies` edge and an engine API change | `ΔA`-adjacent (the engine gains a dependency it is told not to have) |
| D. Put the name table in `domain` | `domain` depends on `policies` or imports them | not lawful: `domain` may depend on the standard library only |

**Recommendation: A.** It is the smallest, it matches what the code must do in cuts 8, 9 and 11, and it is
a correction of a descriptive table. I did not add the edge.

## 3. What I changed and then undid

Before reaching the stop I wrote two things I should not have: a `make_policy` factory appended to
`elevator/policies.py` (with the intent that `api.py` would call it), and a refactor of
`elevator/scenarios.py` extracting `validate_scenario` out of `generate`. The first had no lawful caller. The
second was not needed: the harness validates a scenario by calling the existing `generate` once. Both were
reverted in the same session.

Proof that the validated modules are untouched, rechecked against the code as it stands now: a copy of the
package with exactly the three Cut 8 additions removed (the new `operations.py`, the new `harness.py`, and from
`reporting.py` the one added import and the one added function) reproduces the code identity recorded at the end
of Cut 7, `bdd62c2752e9eaa6ce3db71266b5d0e0f0a66a8433ed3488e85c436cbde372b0`. So every Cut 1 to 7 production
file is byte-identical to its recorded state apart from those three additions. (A first attempt at this check
failed because my own stripping script left an extra trailing newline; the same slip had made the first revert of
`policies.py` differ by one newline. Both were found by the identity comparison and fixed.) The 13 Cut 7 tests
and the committed expected Traces pass unchanged.

## 4. Implemented and verified

### 4.1 `elevator/operations.py` (new)

The neutral component of architecture §1.1, depending on `domain` and the standard library only: `OperationalLog`
(`append`, `append_record`, `bind_evidence_root`, `flush_unflushed_prefix`, `close`), `Execution`,
`start_execution`, `utc_timestamp`, `git_provenance`.

- `execution_id` is minted with the standard library's `uuid.uuid4()` as architecture §6 states ("the standard
  library's UUID version 4 (128 random bits)"; constitution §2 says "UUID version 4 or equivalent"). Its
  representation is the library's canonical text form (`str(uuid4())`, hyphenated); the documents do not fix
  a text form, the only identity semantics are string equality (the loader compares the recorded value with the
  supplied one), and it is also the directory name. This is a bounded realisation choice and is flagged.
- `start_execution` appends `EXECUTION_STARTED` as `op_seq` 1. Every record carries `execution_id`, `op_seq`
  (contiguous from 1), the tick where one applies, and in its payload the process id and the code identity
  (authority row 26). Only the admitted kinds exist; the four that apply without a Store are
  `EXECUTION_STARTED`, `EXECUTION_ENDED`, `CODE_IDENTITY_DRIFT`, `DIAGNOSTIC`.
- Lifecycle (cpoc §2.2a): an in-memory buffer; binding an evidence root creates `<root>/operational.jsonl`
  (never over an existing file) and flushes the whole unflushed buffer once, in order; later records are
  appended directly; the carrier changes once (a second binding is refused); a log never bound creates no
  file. Records are frozen values and each line is the record's canonical JSON.
- It reads or writes the log only. It cannot reach the engine, a policy, route, scenarios, reporting or the
  API (AST-asserted), and none of those import it except reporting's wrapper.

### 4.2 `elevator/reporting.py`: `write_execution_output` (one function added)

The architecture's execution-output wrapper. Given an output directory, the `run_id`, the Execution, the
eight-file surface and the metadata bytes, it binds the Execution's own log to
`<output_dir>/<run_id>/<execution_id>/` through `operations`, then writes the eight files exactly as generated
plus `execution_metadata.json`, in the same directory as the separate `operational.jsonl`. It refuses a
surface that is not exactly the eight files and never overwrites. `reporting` now imports `operations`, as the
dependency table says. The Cut 6 structural test was updated to that import set (`{domain, operations}`) and
still asserts that reporting loads no engine, route, policy or API module.

### 4.3 `elevator/harness.py` (new): the pure core

Inside its table row (`domain`, `scenarios`, `reporting`); no Run-execution loop.

- `ExperimentDefinition`: normalised to effective values, so the hash covers every parameter; `definition_hash`
  is the SHA-256 of its canonical JSON; the experiment execution id is the SHA-256 of
  `(definition_hash, code_identity)`. Every refusal happens at construction, before any Run could execute,
  including the sparse cross-parameter precondition (it generates each scenario's first Trace).
- `RunResult`, `check_complete_and_paired` (the fair-comparison witness: one Trace hash per
  `(scenario, seed)`, and every `(scenario, seed, policy)` cell present exactly once, so a failed Run can
  never be dropped), `aggregate_cell` (null-aware: a halted Run only in `halted_count` and its listing; a null
  never counted as zero; `n_defined` beside each aggregate; mean and median null when it is 0; the full
  per-seed vector), `paired_cell` (cost minus baseline over seeds where both are completed and defined;
  `n_pairs`; better, equal, worse; null when 0), `results_document` and `results_bytes` (the Reproducible
  Experiment Result Surface), `experiment_execution_metadata` (the execution facts, separately).

### 4.4 Tests (22 new)

| File | Tests |
| --- | --- |
| `tests/unit/test_operations.py` (10) | `EXECUTION_STARTED` at `op_seq` 1; `execution_id` is a random UUID v4 and distinct over 500 Executions; contiguous `op_seq` and immutable records; flush at binding writes the buffer once, in order, byte-exact; `never_bound_execution_has_no_file`; no overwrite of an existing log; execution-output layout with the log as a separate file; the separation negative control; the leak-scan negative control; operations cannot reach, and is not reached by, the engine |
| `tests/comparative/test_experiment_core.py` (10) | `paired_difference_arithmetic`; `experiment_null_aggregation`; `same_trace_hash_across_policies` (the witness, on result sets, not an executed Experiment); a negative control that per-policy regeneration is caught; a dropped, duplicated or foreign run is caught; definition identity over effective parameters; `sparse_cross_parameter_refused` (harness half); refusals of every invalid part; results document determinism, ordering and freedom from execution facts; the harness stays in its dependency row |
| `tests/comparative/test_regression_fixtures.py` (1) | `cost_based_not_worse_on_capacity_stress_fixture` (fixed before running: capacity stress, 12 floors, 3 cars, capacity 4, 40 requests, seed 0; p95 wait 48 for `cost_based` against 56 and 166; a regression guard, not a claim) |
| `tests/reproducibility/test_run_identity.py` (1) | `run_id_changes_with_params` |

The separation negative control runs one Run in two Executions with different execution ids, pids,
timestamps and a different number of operational records: the `run_id`, the Simulation History and every one of
the eight surface files are byte-identical, while `execution_metadata.json` and `operational.jsonl` differ.

## 5. Not implemented, and why

All of the following need a policy resolved from a name, or run a Run through `simulate` (§2):

| Item | Plan identifier or deliverable |
| --- | --- |
| `api.simulate`, `api.create_engine` (and the Execution handle they create) | the cut-8 row; `normalization_shared_by_batch_and_live` |
| the harness Run-execution loop and the two result files written from a real Experiment | `experiment_reexecution_identical`; `experiment_results_surface_excludes_execution_facts` (the builder is tested, a real executed Experiment is not); the executed half of `same_trace_hash_across_policies` |
| `elevator/cli.py` (`simulate`, `experiment`) | CLI smoke and reproducibility |
| the default Experiment definition, its committed `experiment_results.json`, and the timing assertion with its measured duration | `committed_experiment_evidence`; the plan's one timing claim |
| `same_inputs_same_history` (two processes) | needs `simulate` |

Nothing from cuts 9 to 11 was started: no Store, checkpoint, continuation, finality persistence, CPOC witness or UI.
Two further matters are open for the owner when the stop is resolved, neither a blocker now: the governing
documents do not define the **default Experiment's** building or per-pattern parameters (a data choice, to be
confirmed), and the architecture's `harness -> api` edge for executing Runs (evaluation §7.2 says the harness
calls `simulate`) is equally absent from the table; option A would cover both.

## 6. Realisation choices (no rule changed)

1. `execution_id`: stdlib `uuid4`, canonical text form (§4.1), documented source, representation flagged.
2. The harness aggregates the values **as `summary.json` reports them** (integers and three-digit decimal
   strings, parsed exactly), so reporting is not changed to expose unrounded metrics. The consequence, stated
   plainly: an aggregate is of reported, already-rounded values.
3. `PAIRED_METRICS`: evaluation §7.4 says "metric" without listing them; the twelve compared are
   `wait.{mean,median,p95,max}`, `total.{mean,median,p95,max}`, `tail_share`, `makespan`,
   `deferred.count`, `wrong_way.count`, all better when lower. `elevator_utilisation` is aggregated per elevator.
4. A definition refuses an empty or repeated seed list, an empty or repeated policy list and an empty
   scenario list, because results are keyed by `(scenario, seed, policy)` and a cell must be neither empty
   nor ambiguous.
5. When `n_pairs` is 0 the paired mean, median and better, equal, worse counts are all null.
6. Operational payloads carry `pid` and `code_identity` on every record; `git_provenance` reads the worktree
   state only for execution metadata and is outside every equality claim.

## 7. Verification

```text
python3 -B -m pytest -q tests/unit/test_operations.py tests/comparative tests/reproducibility/test_run_identity.py
  -> 22 passed
python3 -B -m pytest -q
  -> 195 passed in 12.77s
```

0 failed, 0 skipped, 0 errors; cuts 1 to 7 remain green; no `__pycache__`. Code identity of the package as it
stands: `54771281d60488b7b9592036e021cc562e2e802fed1e00ed3a25f238069f6cec`. Governing and plan digests unchanged.

## 8. Delta and standing

No delta is asserted for the stop itself: option A is a decision for the owner (my reading: `NONE / NONE /
NONE`, with a revision-7.3 record for the changed bytes of one descriptive file). Nothing implemented here
changes ontology, semantics or authority.

```text
CUT 8: PARTIAL / STOPPED PENDING OWNER DECISION ON POLICY-NAME RESOLUTION
```

Cut 9 is not eligible. When the owner resolves §2, the remaining work is the items of §5.


## 9. Resumption under revision 7.3 (2026-11-05)

### 9.1 Revision 7.3: the architectural clarification

The owner adopted option A of §2 ([decision 009](../decisions/owner_decision_009_policy_construction_edges.md)).
`docs/architecture.md` changed (and only it): the dependency rows of `api`, `harness`, `checkpoint` and `web` gain
`policies` (`make_policy` only), `policies` is removed from `checkpoint`'s "must not depend on", the `policies`
row names `make_policy`, and a new §1.2 states that these edges permit policy construction only and transfer no
engine, assignment, runtime-state or scheduler-state authority. New digest
`a38da7e428678721b0cfaf7cee6dce42c028b35c880d83c4853200188b558272`; every other governing file and the plan are
at the digests of records 006 to 008, re-verified. `ΔO = NONE / ΔS = NONE / ΔA = NONE`. `AGENTS.md` and
`current_work.md` now name revision 7.3; no earlier decision record was rewritten.

### 9.2 The canonical resolver

`elevator/policies.py` gains `make_policy(name, params=None)`: the one resolver, with no registry, plugin, hook,
dynamic import or mutable global. It supports exactly `round_robin`, `nearest_car` and `cost_based`; any other
name refuses `INVALID_CONFIGURATION`; a baseline given parameters refuses; `cost_based` is built from the
Configuration's default-filled `policy_params` (`CostBased(**params)`). Callers pass `configuration.policy` and
`configuration.policy_params` (a plain-argument signature, so the policies module still names no domain type
such as `Configuration`). Only `api` calls it: no other module names a policy class or keeps a name table
(AST-asserted for `api`, `harness`, `cli`, `engine`, `reporting`, `operations` and `scenarios`). `api` imports
`make_policy` and nothing else from `policies`.

### 9.3 Implemented in this resumption

- **`elevator/api.py`**: `simulate` and `create_engine` with the exact admitted signatures, `SimulationResult`,
  `OutputWriteError`, and `LiveEngine`. Both functions refuse outside the supported execution contract, normalise
  through the one boundary, validate the Configuration, bind the Run identity and resolve the policy; only then is
  an Execution created. `simulate` runs to the outcome, builds the eight-file surface, and, with `output_dir`,
  writes it to `<output_dir>/<run_id>/<execution_id>/` through reporting's wrapper with
  `execution_metadata.json` and the separate `operational.jsonl`; it re-hashes the package at exit and records
  `CODE_IDENTITY_DRIFT` before `EXECUTION_ENDED`. With no output directory its log stays in memory and no file
  is created. `create_engine` returns a `RUNNING` engine at `t = 0`; it is an ordinary `Engine` subclass
  defined in `api` that also exposes its Execution and Run identity read-only, so the engine module knows
  nothing of operations. Failure classes are distinct: a `Refusal` before any Execution exists (input,
  Configuration, environment); a `HALTED` result (policy error, invalid proposal, horizon, invariant violation:
  returned, never reported as completed); `OutputWriteError` (nothing overwritten).
- **`elevator/harness.py`**: `execute_experiment`, `RunExecution`, `ExperimentExecution` added to the verified core
  (unchanged). For each scenario and seed the Trace is generated once and every policy runs on that one Trace; a
  Run on any other Trace is an `ExperimentIntegrityError`; completeness is checked; a halted Run is recorded and
  the Experiment continues. The Run executor is a parameter (§9.5).
- **`elevator/cli.py`**: `simulate` (from `--requests FILE.csv` or `--scenario PATTERN --seed N --param NAME=INT`,
  with `--floors/--elevators/--capacity`, `--policy`, `--policy-param`, `--initial-floors`, `--max-ticks`,
  `--out`) and `experiment` (`--config FILE.json --out DIR [--summary-only]`); no `store init`, no `resume`. Exit
  codes: 0 completed; 2 usage; 3 refusal (input, file, Configuration, scenario, definition); 4 simulation
  `HALTED`; 5 output failure; 6 unsupported environment. The CLI adds no default the documents do not state: the
  building is required, the policy defaults to `cost_based`, initial floors to 0.

### 9.4 Still open: the default Experiment (a separate owner decision)

Searched in the nine governing documents and the plan, value by value:

| Needed for the default Experiment | Defined? | Exact source |
| --- | --- | --- |
| the nine patterns; their non-numeric parameter defaults (`k = 3`, `w = 3`, `m = 2`, `origin = 0`, `g = 2(F-1)`, `j = 0`) | yes | evaluation §6.3 |
| the seeds | yes, `0..K-1`, `K = 20` | evaluation §7.1 |
| the policies | yes, the three | evaluation §7.1 |
| initial floors | yes, default 0 | semantics §6 |
| the building: floors, elevators, capacity | **no** | none (only illustrative worked-example buildings) |
| `num_requests` and `horizon` per pattern | **no** | listed without a default in the §6.3 table |
| the "fixed Experiment" for committed evidence | **no** | named in testing contract §4 and evaluation §8, never defined |

Not created, so that convenience does not choose evaluation evidence: `experiments/default.json`, the committed
default `experiment_results.json` (`committed_experiment_evidence`), and the plan's one timing assertion with its
measured duration. The Experiments used by the tests below are small test fixtures for mechanics only
(`uniform`, `bursty`, `capacity_stress` over seeds 0 to 2, building 6/2/3); they are not the default Experiment
and their results are not evidence of anything about the policies.

### 9.5 Realisation choices (no rule changed)

1. **The harness takes its Run executor as a parameter.** The dependency table, as amended by revision 7.3,
   gives `harness` an edge to `policies` but none to `api` or `operations`, and evaluation §7.2 has each Run be
   an Execution of the public `simulate`. Rather than add an edge, `execute_experiment` receives
   `(trace, configuration, output_dir) -> RunExecution`; `cli` (which may depend on everything) passes the
   public `simulate` through a small adapter that re-checks the Trace hash, and `web` (which depends on `api`
   and `harness`) can do the same. Policy resolution still happens in exactly one place. If the owner prefers a
   direct `harness -> api` edge it is a one-function change.
2. `LiveEngine` is a subclass defined in `api`, because `create_engine` must return an `Engine` and the
   Execution handle must not live in the engine.
3. The Experiment's two files are written to `<out>/<experiment_execution_id>/`; the per-Run directories keep
   `<out>/<run_id>/<execution_id>/`. Re-running the same definition under the same code into the same `--out` is
   refused before anything runs (evidence is never overwritten); use another `--out`. Because the experiment
   execution id includes the code identity, any edit to the package gives a new directory.
4. The CLI's CSV reader skips a first row that is exactly `time,id,source,dest` and otherwise only splits cells:
   every row rule belongs to `normalize_requests`. The experiment config refuses floats.
5. Execution metadata reads Git provenance once per process (`git rev-parse HEAD`, `git status --porcelain`);
   it is informational and outside every equality claim. With no commit it is `null`.
6. `simulate` re-normalises a generated Trace's canonical rows inside the CLI adapter; the Trace hash is
   verified equal to the harness's one Trace on every Run.

### 9.6 Verification

```text
python3 -B -m pytest -q tests/unit/test_policy_resolver.py tests/unit/test_api.py \
    tests/comparative/test_experiment_execution.py tests/reproducibility/test_cli_and_processes.py   -> 29 passed
python3 -B -m pytest -q                                                                            -> 224 passed in 16.32s
```

0 failed, 0 skipped, 0 errors; cuts 1 to 7 green; no `__pycache__`. New in this resumption (29): resolver 4;
API 12 (`normalization_shared_by_batch_and_live`, refusals before any Execution, halted not completed, exact
output and no overwrite, output failure, never-bound no file, separation through `simulate`, drift record,
`create_engine`, environment refusal, dependency table); executed Experiment 7
(`same_trace_hash_across_policies`, `experiment_reexecution_identical`,
`experiment_results_surface_excludes_execution_facts` with a planted-leak control, paired differences against an
independent `decimal` computation, a failed Run recorded `HALTED` with the Experiment continuing, per-policy
regeneration caught on the real path, default seeds and policies); fresh processes and CLI 6
(`same_inputs_same_history` in two processes, CLI smoke and reproducibility, scenario mode equals the same rows
as a file, every exit code, Experiment re-execution across processes and in-process byte-equal, definitions
refused before running).

Named identifiers: eleven of twelve in the cut-8 row have a same-named test; the twelfth,
`committed_experiment_evidence`, awaits the default Experiment (§9.4), as does the timing assertion.

Byte-equivalence of cuts 1 to 7, as required by decision 009: with the new `operations.py`, `harness.py` and
`cli.py` removed, `api.py` restored to its Cut 1 text, and the added import and function removed from
`reporting.py` and `policies.py` (the latter admitted by revision 7.3), the package reproduces the Cut 7 code
identity `bdd62c2752e9eaa6ce3db71266b5d0e0f0a66a8433ed3488e85c436cbde372b0`. `engine.py`, `route.py`,
`domain.py` and `scenarios.py` are untouched. Code identity now: `5e823d051102f49cfd3a2dfcb97720228962b780ab17e95828efd708079d3ffa`.

### 9.7 Delta and standing

No ontology, semantic or authority change: `ΔO = NONE / ΔS = NONE / ΔA = NONE`, including revision 7.3.

```text
CUT 8: PARTIAL / IN PROGRESS
```

Remaining for cut 8: the default Experiment definition, its committed `experiment_results.json`
(`committed_experiment_evidence`) and the timing assertion, all awaiting the owner's decision on the values of
§9.4. Cut 9 is not eligible and was not started.


## 10. Completion under owner decision 010 (2026-11-05)

### 10.1 The two decisions ([record 010](../decisions/owner_decision_010_fixed_experiment.md))

- **Harness dependency:** the executor-injection design is kept and no `harness -> api` edge is added. The
  harness owns the definition, pairing, aggregation and completeness checks and receives the Run executor from
  its caller; the CLI supplies `simulate`. `ΔO = NONE / ΔS = NONE / ΔA = NONE`.
- **The fixed Experiment:** floors 20, elevators 4, capacity 8, initial floors all 0; all nine patterns; seeds
  `0..19`; `round_robin`, `nearest_car`, `cost_based`; `num_requests = 100` and `horizon = 1000` for every
  pattern that has a horizon; every other parameter its admitted default. 9 patterns, 20 seeds, 180 paired
  units, 540 Runs; each Trace generated once per pattern and seed and shared by the three policies. It is a
  reproducible comparison fixture, not a claim about real elevator traffic.

### 10.2 Pre-admission validation (run before any document or evidence existed)

The existing Cut-7 validation (`generate`) was run for `F = 20, N = 4, C = 8, num_requests = 100,
horizon = 1000` over all nine patterns. No cross-parameter constraint is violated (capacity stress needs
`100 > N*C = 32`; sparse's last time is `99 * 38 = 3762`; `m <= F`, `origin < F`). **One reading, flagged for
the owner:** supplying `horizon` literally to every pattern is refused for `capacity_stress`, `sparse` and
`adversarial` by evaluation §6.2's rule that a pattern refuses a parameter it does not name; the validation was
therefore read as "`horizon: 1000` for every pattern that has one", with no pattern-specific value chosen. This
was not one of the two cases the instruction anticipated (it is not a cross-parameter constraint and no
"minimum lawful horizon" exists for patterns without a horizon), so it is stated in decision 010 §3.2 and
here rather than treated as a stop. The scenario generator is unchanged.

### 10.3 Definition and committed evidence

| File | Identity |
| --- | --- |
| `experiments/default.json` | SHA-256 `1638535528720292505904982ee9042a51649226ca91786e422ba0cb6c4e9c1e`; `definition_hash` `6f1ba88ad116b124e5d1f03c78add35086e2d90c8cf3e552c59768e891729bdd` |
| `experiments/default_experiment_results.json` | the exact `experiment_results.json` of one fresh-process CLI execution; 552,486 bytes; 540 runs, 27 aggregates, 0 halted; produced under code identity `5e823d051102f49cfd3a2dfcb97720228962b780ab17e95828efd708079d3ffa` |

The evidence holds no `execution_id`, path, pid, timestamp or operational sequencing (the only `execution_id`
substring is the key `experiment_execution_id`, the hash-derived identity the admitted result surface
includes); those exist only in the separate `experiment_execution.json` and operational logs. No governing
document's bytes changed.

### 10.4 Tests added (7, `tests/comparative/test_default_experiment.py`)

The definition file and hash are pinned; all 540 Runs execute with paired Traces (one Trace hash per pattern and
seed, equal to an independently generated Trace, 180 units, every Run `COMPLETED`);
**`committed_experiment_evidence`**; the committed file holds no execution fact; fresh results hold none either;
fresh-process re-execution is byte-identical to the in-process results and gives each of the 540 Runs its own
`execution_id` only in the metadata; and the completion test that records elapsed time. All twelve identifiers
named in the plan's cut-8 row now have same-named tests.

`committed_experiment_evidence` compares a fresh execution with the committed file on **behavioural content**
(definition, every Run's Trace hash, outcome and summary, every aggregate). The fields derived from the code
identity (the experiment execution id and every `run_id`) change with any package edit, so they are checked for
internal consistency with the code identity the file records (the id is the hash of `(definition_hash,
code_identity)`; each `run_id` is the hash of its Configuration hash, Trace hash and that code identity), and
when the fresh code identity equals the recorded one the two files must be byte-identical (it is, today). A
change in behaviour requires updating the committed file in the same change with a note.

### 10.5 Timing: observed, not required

The plan says the default Experiment "completes within a few minutes"; that is not a numeric threshold, so none
was invented and no wall-clock threshold is asserted (decision 010 §6). The correctness requirement, that the
fixed Experiment completes successfully, is asserted. Observed performance evidence, not a requirement:

| Measurement | Elapsed |
| --- | --- |
| fixed Experiment, in-process, 540 Runs (test) | 80.1 s |
| fixed Experiment, whole fresh CLI process, `--summary-only` (two timed runs) | 79.2 s and 79.5 s |

Environment: Apple M3 Pro, 12 logical CPUs, macOS (Darwin 27), CPython 3.12.3, a single process (no
parallelism, as evaluation §7.6 prescribes unless a measured execution exceeds a few minutes). These figures
describe this machine and are not a performance claim. A consequence worth knowing: the fixed Experiment runs
twice in the full suite (once in-process, once in a fresh process), so the full suite now takes about three
minutes.

### 10.6 Verification

```text
python3 -B -m pytest -q tests/comparative/test_default_experiment.py   -> 7 passed in 162.01s
python3 -B -m pytest -q                                                -> 231 passed in 180.70s
```

0 failed, 0 skipped, 0 errors; cuts 1 to 7 green and byte-equivalent apart from the additions admitted by
revision 7.3 (§9.6); no `__pycache__`. Fixed-Experiment re-execution (in-process and a fresh process), the
Cut-8 focused tests, the CLI smoke and exit-code tests, and the execution/reproducible-surface separation
checks (§4.4, §9.6) all pass. Code identity: `5e823d051102f49cfd3a2dfcb97720228962b780ab17e95828efd708079d3ffa` (unchanged since the evidence was generated). Governing and
plan digests are those of revision 7.3, unchanged.

### 10.7 Delta, applicability and standing

`ΔO = NONE / ΔS = NONE / ΔA = NONE`. OSA `REQUIRED` for the Execution identity and operational/reproducible
separation (evidence §4.4, §9.6, §10.4); CPOC `NOT APPLICABLE` per the plan (no Store; the function writes no
document).

```text
CUT 8: IMPLEMENTED / LOCAL VERIFY PASS
```

Next eligible cut: cut 9 (Store, Execution continuity, finality, loader and operational integration). Not started.
