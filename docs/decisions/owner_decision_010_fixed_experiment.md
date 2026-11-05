# Owner Decision Record 010: The Fixed Experiment and the Harness Dependency

Status: **DECIDED 2026-11-05 by the owner; the fixed Experiment is admitted subject to the validation of §3, which passed.** No governing document's bytes change: revision 7.3 ([record 009](owner_decision_009_policy_construction_edges.md)) stays the admitted baseline at its digests. Records 006 to 009 are not rewritten.

## 1. Source

The two remaining gaps of the cut-8 record (§5 and §9.4): the dependency question for executing Runs from the
harness, and the values of the "default Experiment" of evaluation §7.6 ("9 patterns, 20 seeds, 3 policies = 540
runs"), which the documents name but never define.

## 2. Decisions

**2.1 Harness dependency.** Keep the executor-injection design. Do not add `harness -> api`. The harness owns the
Experiment definition, pairing, aggregation and the completeness checks; it receives the lawful Run executor from
its caller, and the CLI supplies `simulate`. This is consistent with the admitted dependency graph and needs no
architecture edge. `ΔO = NONE / ΔS = NONE / ΔA = NONE`.

**2.2 The fixed Experiment.** For committed evaluation evidence, admit:

| Element | Value |
| --- | --- |
| floors, elevators, capacity | `20`, `4`, `8` |
| initial elevator floors | all `0` |
| patterns | all nine admitted scenario patterns |
| seeds | the integers `0..19` |
| policies | `round_robin`, `nearest_car`, `cost_based` |
| `num_requests` | `100` for every pattern |
| `horizon` | `1000` for every pattern (see §3.2 for what "every pattern" means) |
| every other pattern parameter | the already-admitted defaults of evaluation §6.3 |

That is 9 patterns, 20 seeds per pattern, 180 paired scenario and seed units, 3 policies per unit, 540 Runs.
Each Trace is generated **once per pattern and seed** and that exact Trace is reused for all three policies; there
is no policy-specific scenario tuning.

**2.3 What the benchmark is.** The fixed Experiment is a reproducible comparison fixture. It is not a claim that
these parameters represent real-world elevator traffic, and its results support only the permitted claim form of
evaluation §7.5 (a regime, a building, `K` seeded Traces, a count and a median), never "better" in general.

## 3. Mandatory pre-admission validation (performed before any document or evidence was produced)

The existing Cut-7 validation (`generate`, which checks every refusal of evaluation §6.2 and §6.3) was run for
`num_floors = 20`, `num_elevators = 4`, `capacity = 8`, `num_requests = 100`, `horizon = 1000`.

**3.1 Cross-parameter constraints: none violated.** `capacity_stress` needs `num_requests > N * C`, and `100 > 32`.
`sparse` needs `(num_requests - 1) * g + j <= 10^9`, and with the default `g = 2 * (F - 1) = 38` the last time is
`99 * 38 + 0 = 3762`. `concentrated_*` need `m <= F` (`2 <= 20`) and `capacity_stress` needs `origin < F`
(`0 < 20`). Every parameter value is inside its §6.2 domain.

**3.2 One point of reading, for the owner to confirm or overturn.** Supplying `horizon` literally to every
pattern is refused for three of them (`capacity_stress`, `sparse`, `adversarial`) with
`INVALID_SCENARIO_PARAMETERS: horizon: is not a parameter of pattern ...`. This is not a cross-parameter
constraint: it is evaluation §6.2's rule that "a pattern refuses a parameter it does not name", and those three
patterns have no horizon (so no "minimum lawful horizon" exists for them). Evaluation §6.2 calls `horizon` common
but "used where stated". This record therefore reads "`horizon: 1000` for every pattern" as "for every pattern
that has a horizon" (`uniform`, `up_peak`, `down_peak`, `bursty`, `concentrated_origin`,
`concentrated_destination`) and supplies it to no other. No pattern-specific value was chosen. With that reading
all nine patterns accept the values for every seed tried (`0`, `1`, `19`, `2^64 - 1`).

## 4. The definition file and its identity

The definition is `experiments/default.json` (the form read by `python -B -m elevator.cli experiment --config`).
Its identities:

| Item | SHA-256 |
| --- | --- |
| the file `experiments/default.json` | `1638535528720292505904982ee9042a51649226ca91786e422ba0cb6c4e9c1e` |
| its `definition_hash` (evaluation §7.1, over the effective, default-filled definition) | `6f1ba88ad116b124e5d1f03c78add35086e2d90c8cf3e552c59768e891729bdd` |

Effective pattern parameters (defaults filled): `bursty` `k = 3, w = 3`; `concentrated_*` `m = 2`;
`capacity_stress` `origin = 0`; `sparse` `g = 38, j = 0`.

## 5. Committed evidence

After this record, the Experiment is executed and its `experiment_results.json` is committed as
`experiments/default_experiment_results.json`. It is evidence, not authority.

- It contains no execution fact: no `execution_id`, path, pid, timestamp or operational-log sequencing; those
  belong only to the separate `experiment_execution.json` and the operational logs.
- The file records the `code_identity` it was produced under, and with it the experiment execution id and every
  Run's `run_id`, all of which change with any edit to the package. The test `committed_experiment_evidence`
  therefore compares a fresh execution with the committed file on **behavioural content** (the definition, every
  Run's Trace hash, outcome and summary, and every aggregate), and checks the code-identity-derived fields only
  for internal consistency (the experiment execution id is the hash of `(definition_hash, code_identity)`, and
  each `run_id` is the hash of its Configuration hash, Trace hash and the recorded code identity). When the
  fresh code identity equals the recorded one, the two files must be byte-identical. A change in behaviour
  requires updating the committed file in the same change with a note, as the testing contract states.

## 6. Timing

The plan and testing contract say the default Experiment "completes within a few minutes" and that the plan's
cut 8 records the measured value. That is not a numeric threshold, so none is invented and no wall-clock
threshold is asserted. Two things are kept apart: the **correctness requirement** is that the fixed Experiment
completes successfully (all 540 Runs executed, paired, none missing); the **observed performance evidence** is the
elapsed time on the machine and environment that ran it, recorded with that context in the cut-8 record. A slower
machine does not fail correctness.

## 7. What this record does not change

No governing document, no scenario semantics, no scheduler semantics, no architecture edge. `ΔO = NONE / ΔS = NONE /
ΔA = NONE`. The revision-7.3 digests of record 009 remain the admitted baseline.
