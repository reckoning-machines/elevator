# Evaluation Design

Status: **GOVERNING DOCUMENT for scenarios, metrics, outputs and Monte Carlo evaluation. DRAFT, NOT ADMITTED. Revision 7.1 (bounded component-mapping and reference repairs, 2026-11-05).**

Jurisdiction: the public input boundary and the source-facing function,
the Scenario generator (exact algorithms), the required outputs of a single
run, the metrics and their exact numeric definitions including empty and
degenerate populations, the generated observations, the Monte Carlo harness,
experiment identity, fair comparison between policies, and the boundary of
any empirical claim. Subordinate to [constitution.md](constitution.md). The
harness owns Scenarios and Experiments (authority model rows 30 to 35) and
nothing inside a Run. Monte Carlo is evaluation; it never feeds the
scheduler.

## 1. Two layers

- **Single run**: one Configuration, one Trace, one policy. Produces the
  outputs of §3. This is what the UI animates and what the take-home's
  required output refers to.
- **Monte Carlo evaluation**: many Scenarios, many seeds, every policy on
  every generated Trace. Produces the comparison of §6. The harness is not
  the scheduler and does not run in real time; it is a batch over the engine.

## 2. Public input boundary, the source-facing function and the live engine

The take-home asks for a function that accepts request rows of the form
`time, id, source, dest` and simulates them. Three public boundaries share
one engine implementation; none is a second simulation path:

```text
normalize_requests(request_rows, num_floors) -> Trace
simulate(request_rows, num_elevators, num_floors, capacity,
         policy="cost_based", policy_params=None, initial_floors=None,
         max_ticks=None, output_dir=None) -> SimulationResult
create_engine(request_rows, num_elevators, num_floors, capacity,
              policy="cost_based", policy_params=None, initial_floors=None,
              max_ticks=None) -> Engine            # RUNNING at t = 0
```

- `normalize_requests` is the shared input boundary: it validates rows,
  assigns `input_index`, normalises ids, and returns the Trace (authority
  row 41). Both `simulate` and `create_engine` call it, as do the CLI and
  the UI; nothing else parses request rows.
- Operational bookkeeping uses the neutral `operations` component
  (architecture §1.1): both public functions create one process-owned
  Execution handle and its log through it. Reporting's execution-output
  wrapper binds an output-only batch log to its output root. Neither
  public function imports checkpoint, and metric reporting never reads
  operational evidence. These calls use the existing lifecycle, not a
  second engine or an additional owner.
- `simulate` (the source-facing batch function): normalise; validate the
  Configuration; create the engine; run to the Run outcome; produce the
  outputs of §3 in memory and, if `output_dir` is given, write them. It
  never writes a Continuation Document; checkpointing is a CLI and UI
  concern. It mints an `execution_id` like any Execution; its Operational
  Log lives in memory until an output directory gives it an evidence root,
  and with `output_dir=None` it stays in memory and is discarded with the
  result ([cpoc_design.md](cpoc_design.md) §2.2a).
- `create_engine` (the interactive boundary): the same normalisation and
  validation; returns a `RUNNING` engine at tick boundary 0 that the caller
  steps one tick at a time; its Execution's Operational Log is in memory
  until the first explicit checkpoint binds it to a Store, which flushes
  the buffer there (cpoc §2.2a). The UI's "New run" calls `create_engine`,
  never `simulate`; the UI's Step calls the engine's tick; its Checkpoint
  and Reopen delegate to the checkpoint module.

Input rules:

- `request_rows`: an iterable of rows; each row is a mapping with keys
  `time`, `id`, `source`, `dest`, or a sequence of four values in that
  order. Accepted types: `time`, `source`, `dest` are integers (or strings
  of decimal digits, converted); `id` is a string or an integer (an integer
  is converted to its decimal string, so `1` and `"1"` collide and `"01"`
  is distinct). Anything else refuses `INPUT_INVALID` with the row's
  position.
- Validation, in row order, then across rows: `0 <= time <= 10^9`;
  `0 <= source, dest < num_floors`; `source != dest`
  (`SAME_FLOOR_REQUEST`); `id` non-empty (`MISSING_SOURCE_ID`); `id` unique
  across all rows (`DUPLICATE_SOURCE_ID`, reporting both positions); at
  most `100000` rows (`INPUT_INVALID`).
- Configuration domain (owner decision proposed as D-21; the practical
  take-home domain over which every algorithm in this document is
  defined): `2 <= num_floors <= 200`, `1 <= num_elevators <= 20`,
  `1 <= capacity <= 50`, `initial_floors` of length `num_elevators` with
  every entry in range (default all 0), `max_ticks` absent or `<=` the
  default bound, policy name one of the three with parameters valid for
  it (integers in `0..10^6`). Violations refuse `INVALID_CONFIGURATION`.
- Ordering: rows become Requests with `input_index` = row position; the
  Trace is the stable sort by `(time, input_index)`; `passenger_id` is the
  sorted position. The supplied `id` is the Passenger's `source_id` and
  appears in every output that names a passenger; the mapping is in
  `passengers.csv`.
- No look-ahead: every boundary materialises the whole Trace, as any input
  path must; the engine reveals Requests one tick at a time and policies
  see only the `SchedulerView` (constitution N1).
- Defaults: `policy="cost_based"` with the defaults of
  [scheduler_design.md](scheduler_design.md) §6.3.

## 3. Required outputs of a single run

Written to `<output_dir>/<run_id>/<execution_id>/` as `DERIVED` outputs
of the Simulation History and Passenger records, plus the Execution's own
evidence. The output directory is a storage location (authority row 28);
nothing is ever read back from it.

### 3.1 The Reproducible Output Surface (identical for every Execution of a Run)

| File | Content |
| --- | --- |
| `elevator_positions.csv` | **the source-facing position log**: header `t,elevator_0,...,elevator_{N-1}`; one row per timestamp `t` from 0 to the final tick; each cell is `floor_E(t)` (constitution P7). For a `HALTED` run, rows for the completed ticks only (possibly none: header only) |
| `position_log_long.csv` | the analysis form: `t, elevator_id, floor, heading, load` for every `t` and elevator |
| `passengers.csv` | `passenger_id, source_id, request_time, origin, destination, elevator, assigned_at, pickup_time, dropoff_time, wait_time, travel_time, total_time, capacity_deferrals, wrong_way_passes, standing`; for a `HALTED` run, incomplete passengers have empty time cells |
| `summary.json` | the metrics of §4 |
| `observations.md` | the rule-generated observations of §5, derived solely from the Run |
| `run_identity.json` | `run_id`, Configuration (with hash), Trace hash, policy name and params, code identity, Run outcome (`COMPLETED`/`HALTED`, final tick, halt step and reason). Nothing execution-specific |
| `events.jsonl`, `tick_records.jsonl` | the Simulation History, serialised |

Constitution P8 and P12 quantify over exactly these files. No file in this
surface may contain an `execution_id`, `store_id`, Git SHA, timestamp,
pid, scenario label or any other execution fact (constitution N18).

### 3.2 Execution evidence (may differ between Executions)

| File | Content |
| --- | --- |
| `execution_metadata.json` | `execution_id`, `run_id`, `store_id` if any, Git SHA and worktree standing as provenance, `provenance` (scenario pattern, parameters, seed) if the Trace was generated, checkpoint controls, pid, start and end timestamps, Execution standing as reported |
| `operational.jsonl` | the Execution's Operational Log, present only when the Execution had an evidence root: for an Execution bound to no Store this directory is its root and the file is the log itself; for a Store-bound Execution it is a copy of `<store>/<execution_id>/operational.jsonl` made at `EXECUTION_ENDED` (cpoc §2.2a) |

The take-home's three required outputs are `elevator_positions.csv`,
`summary.json` (min, max, average of wait and total, among others) and
`observations.md`. The rest are this project's additions.

## 4. Metrics (exact definitions)

### 4.1 Population

Over the set of `COMPLETED` passengers of a `COMPLETED` run. A `HALTED` run
has no summary: `summary.json` holds `{standing, final_tick, halt_reason,
n, completed, unserved}` only.

| Metric | Definition |
| --- | --- |
| `n` | number of Requests in the Trace |
| `completed` | number `COMPLETED` (equals `n` for a `COMPLETED` run) |
| `unserved` | `n - completed` |
| `wait.min / max / mean / median / p95 / std` | over `wait_time` |
| `total.min / max / mean / median / p95 / std` | over `total_time` |
| `travel.mean` | over `travel_time` (equal to mean trip distance, constitution P11) |
| `deferred.count` | passengers refused boarding for capacity at least once (authority row 22: from TickRecords and events, the car at the origin with a departure heading compatible with the passenger, `load = C` after boarding, and the passenger still waiting) |
| `wrong_way.count`, `wrong_way.mean_extra` | passengers whose car was at their origin with an incompatible recorded heading before pickup; the mean over those passengers of `pickup_time - first such tick` |
| `tail_share` | share of passengers with `wait_time > 2 * (F - 1)` |
| `makespan` | final tick |
| `elevator_utilisation` | per elevator, share of ticks `0..final` with recorded heading `!= NONE` |

### 4.2 Numeric rendering

All inputs are integers. Rendering is deterministic and the same in every
implementation:

- `min`, `max`, `p95`: integers from the data. `p95` is nearest-rank: the
  `ceil(95 * n / 100)`-th smallest value (computed in integers as
  `(95 * n + 99) // 100`), never interpolated.
- `mean`, `median`: exact rationals (`median` of an even population is the
  mean of the two middle values). Rendered as decimal strings with exactly
  three fractional digits, rounding **half away from zero** on the exact
  rational: `render(q) = sign(q) * ((|q| * 1000 * 2 + 1) // 2) / 1000`,
  evaluated in integers, formatted with a trailing `.ddd`.
- `std`: population standard deviation. Variance `v` is computed as the
  exact rational `(Σ x_i^2) / n - (Σ x_i / n)^2`. `std` is rendered as the
  integer square root of the scaled variance:
  `std_milli = isqrt((v.numerator * 10^6) // v.denominator)`, rendered as
  `std_milli / 1000` with three fractional digits (truncation of the exact
  root; `isqrt` is exact integer arithmetic). No floating point is used
  anywhere in reporting.
- `tail_share`, `elevator_utilisation`, `wrong_way.mean_extra`: exact
  rationals rendered as above.
- Canonical `summary.json`: keys sorted, no insignificant whitespace,
  numbers as integers or as the decimal strings above (never floats), so
  that two executions produce identical bytes.

### 4.3 Empty and degenerate populations

- `n = 0` (empty Trace; owner decision proposed as D-27): counts are
  defined and zero; shares and distributions with a zero denominator are
  `null`. `summary.json` is `{standing: "COMPLETED", final_tick: 0, n: 0,
  completed: 0, unserved: 0, no_passengers: true, makespan: 0,
  deferred: {count: 0}, wrong_way: {count: 0, mean_extra: null},
  tail_share: null, tail_ratio: null, elevator_utilisation: ["0.000", ...]}`
  and every distribution field (`wait.*`, `total.*`, `travel.mean`) is
  `null`. `observations.md` contains the single line "No passengers; no
  observation rules apply." No division is performed. `tail_share` is
  conditional (defined iff `n >= 1`) everywhere, including §7.4.
- `wrong_way.count = 0`: `wrong_way.mean_extra` is `null`.
- `mean wait = 0` with `n > 0`: the tail-ratio observation (§5 rule 1) is
  suppressed; the summary field `tail_ratio` is `null`. No other metric
  divides by a data value.
- Equality witnesses between runs compare `passengers.csv` and the
  Simulation History, which are integers, and `summary.json` as canonical
  bytes.

## 5. Observations

`observations.md` is generated by a fixed rule set so that the "notable
observations" output is reproducible and not prose written after the fact.
Each rule fires with a sentence and the numbers behind it, and each rule
states its precondition; a rule whose precondition fails is omitted
silently:

1. tail ratio: `p95 wait / mean wait` as an exact rational rendered to three
   decimals, flagged when `> 2`; precondition `n >= 1` and `mean wait > 0`;
2. capacity deferrals: count and the floors where they happened;
   precondition `deferred.count >= 1`;
3. the passenger with the maximum wait: `source_id`, floor, request time,
   assigned elevator, and what that elevator was doing (from TickRecords)
   when the request arrived; ties to the lowest `passenger_id`;
   precondition `n >= 1`;
4. wrong-way passes: count of passengers whose car passed their origin the
   other way first, and the mean extra wait it cost them; precondition
   `wrong_way.count >= 1`;
5. utilisation imbalance: max minus min elevator utilisation, flagged when
   `> 1/2`; precondition `N >= 2`;
6. idle gaps: longest run of ticks with every elevator idle; precondition
   `n >= 1`;
7. for `cost_based`: the share of Tier 2 assignments and the calibration
   summary ([scheduler_design.md](scheduler_design.md) §9); precondition
   `n >= 1`.

Human commentary on behaviour belongs in the README and the walkthrough, and
cites these generated numbers.

## 6. Scenario generator (exact algorithms)

A Scenario is `(pattern, parameters, seed)`. `generate(scenario, F, N, C)
-> Trace` is a pure function of its arguments. Two implementations must
produce the same Trace, so the generator is specified exactly and uses no
language or library random facility.

### 6.1 Generator primitive

SplitMix64, with 64-bit unsigned arithmetic (`mod 2^64`):

```text
state := seed                              (seed: an integer parameter with 0 <= seed < 2^64;
                                            a seed outside this range refuses INVALID_SCENARIO_PARAMETERS
                                            rather than being reduced, so two seeds never name one state)
next():
    state := (state + 0x9E3779B97F4A7C15) mod 2^64
    z := state
    z := ((z xor (z >> 30)) * 0xBF58476D1CE4E5B9) mod 2^64
    z := ((z xor (z >> 27)) * 0x94D049BB133111EB) mod 2^64
    return z xor (z >> 31)
draw(k):                                    (k >= 1; an integer in 0..k-1)
    return ((next() >> 11) * k) >> 53
```

Every random choice below is one `draw`, consumed in the stated order.
The one probability in the patterns, the lobby share of `up_peak` and
`down_peak`, is fixed at `4/5` and drawn as `draw(5) < 4`; it is not a
parameter (removing tunability keeps one algorithm per pattern). Nothing
depends on the interpreter's version. Over the configuration domain of §2
(`F <= 200`), `draw(F)` reaches every floor, so every set construction
below terminates.

### 6.2 Common rules

- Parameters common to all patterns: `0 <= num_requests <= 100000`,
  `0 <= horizon <= 10^6` (the last possible request time, used where
  stated). Pattern-specific domains: `1 <= k <= 1000`, `1 <= w <= 10^6`,
  `1 <= m <= F`, `0 <= origin < F`, `1 <= g <= 10^6`, `0 <= j < g`. Every
  advertised parameter is used exactly once, in the row below that names
  it; a pattern refuses a parameter it does not name
  (`INVALID_SCENARIO_PARAMETERS`).
- A destination draw equal to the origin is redrawn (each redraw consumes
  one `draw(F)`) until it differs; `F >= 2` guarantees termination.
- Requests are generated in index order `i = 0..num_requests-1`; for each
  request the draws are consumed in the order: time, origin, destination
  (with pattern-specific exceptions stated below). `source_id` is `"g" +
  str(i)` (generation index).
- The emitted Trace is the stable sort of the generated rows by `(time,
  i)`.
- Invalid parameters refuse with `INVALID_SCENARIO_PARAMETERS` naming the
  parameter; nothing is clipped or adjusted silently except where a rule
  below says "clamp".

### 6.3 Patterns

| Pattern | Parameters (defaults) | Algorithm per request `i` |
| --- | --- | --- |
| `uniform` | `num_requests`, `horizon` | `time = draw(horizon + 1)`; `origin = draw(F)`; `dest = draw(F)` redrawn while `== origin` |
| `up_peak` | `num_requests`, `horizon` | `time = draw(horizon + 1)`; `lobby = draw(5) < 4` (fixed share 4/5); if `lobby`: `origin = 0`, `dest = 1 + draw(F - 1)`; else `origin = draw(F)`, `dest = draw(F)` redrawn while `== origin` |
| `down_peak` | as `up_peak` | mirror: if `lobby`: `dest = 0`, `origin = 1 + draw(F - 1)`; else uniform as above (origin drawn first) |
| `bursty` | `num_requests`, `horizon`, `k = 3` bursts, `w = 3` width | before any request: centres `c_j = draw(horizon + 1)` for `j = 0..k-1` in order; per request: `j = draw(k)`; `offset = draw(w)`; `time = clamp(c_j + offset - w // 2, 0, horizon)` (clamp, not redraw); floors uniform as `uniform` |
| `concentrated_origin` | `num_requests`, `horizon`, `m = 2` | before any request: the origin set is built by repeated `draw(F)` appending each floor not already in the set until it has `m` members (`1 <= m <= F <= 200`, so this terminates); per request: `time = draw(horizon + 1)`; `origin = set[draw(m)]`; `dest = draw(F)` redrawn while `== origin` |
| `concentrated_destination` | as above | mirror: the set is a destination set; `time`; `dest = set[draw(m)]`; `origin = draw(F)` redrawn while `== dest` |
| `capacity_stress` | `num_requests` (must be `> N * C`), `origin = 0` | `time = 0` (no draw); `origin` as given (`0 <= origin < F`); `dest = draw(F)` redrawn while `== origin` |
| `sparse` | `num_requests`, `g = 2 * (F - 1)` gap (`g >= 1`), `j = 0` jitter (`0 <= j < g`) | `time = i * g + draw(j + 1)` (so consecutive times differ by at least `g - j >= 1`); `horizon` is not used; floors uniform as `uniform`. Cross-parameter precondition (owner decision proposed as D-25): the largest possible time `(num_requests - 1) * g + j` must be `<= 10^9` when `num_requests >= 1`; otherwise the Scenario refuses `INVALID_SCENARIO_PARAMETERS` naming `num_requests, g, j` before any draw. Times are never clipped and the count is never reduced |
| `adversarial` | `num_requests` | no draws: `time = i`; if `i` even: `origin = 0`, `dest = F - 1`; else `origin = F - 1`, `dest = 0` |

Each pattern is a few lines; the set is deliberately small. Adding a pattern
is an Experiment-definition change, not a semantic one, and requires its
exact algorithm and parameter domain here. Refusals, all
`INVALID_SCENARIO_PARAMETERS` naming the parameter: any parameter outside
its domain; an unknown parameter for the pattern; `num_requests <= N * C`
for `capacity_stress`; `seed` outside `0..2^64-1`; the sparse
cross-parameter precondition. Every other pattern's generated times are
bounded by `horizon <= 10^6` (uniform, peaks, concentrated, bursty by
clamp) or by `num_requests - 1 <= 10^5` (adversarial), so no other
combination can leave the request-time domain; the generator asserts
`time <= 10^9` on every emitted row as a guard that must never fire.

### 6.4 Trace identity and provenance

The Trace hash is the SHA-256 of the canonical JSON array of
`[time, source_id, origin, dest]` rows in Trace order. Every Run of a
generated Trace records `provenance = {pattern, parameters, seed}`
(authority row 31) as a `DERIVED` label; the harness re-derives the Trace
from the provenance when it reads results and reports `PROVENANCE_MISMATCH`
if the hash differs. Provenance never loads a Run.

## 7. Monte Carlo evaluation

### 7.1 Experiment definition and identity

```text
ExperimentDefinition
  configuration: F, N, C, initial floors            (within the domain of §2; max_ticks: the default bound, never overridden)
  scenarios: list of (pattern, parameters)          (within the domains of §6.2 and §6.3)
  seeds: list of integers in 0..2^64-1 (default 0..K-1, K = 20)
  policies: list of (name, params)                  # default: round_robin, nearest_car, cost_based
definition_hash          = SHA-256 of the canonical JSON of the definition
experiment_execution_id  = SHA-256 of (definition_hash, code_identity)   # computed at execution start
```

Every consequential parameter is inside the definition, so it is in
`definition_hash`. The code identity is the running package's
(authority row 4), read once at execution start; it is part of the
experiment execution id and of every Run's `run_id`. Each Run inside the
Experiment is an Execution with its own random `execution_id`; the
experiment execution id is a hash, not a random id, because the Experiment
is reproducible from its definition under the same code. No environment identity is
needed: the generator is version-independent by construction (§6.1) and
the engine uses integers only.

### 7.2 Procedure

```text
for each scenario, for each seed:
    trace := generate(scenario, seed, F, N, C)        # once
    for each policy:
        run := simulate(configuration, trace, policy)  # same trace, same hash
        record run.identity, run.summary
```

Every policy sees the identical Trace (verified by hash equality in the
results). This is the whole of "fair comparison": same building, same
demand, same seed, different decision rule. Nothing is tuned per seed.

### 7.3 Reproducibility

An Experiment execution is reproducible from its definition under the same
code identity: re-executing the same definition under the same code
produces the same experiment execution id, every Run's `run_id`, every
Run's Reproducible Output Surface and a byte-identical
`experiment_results.json` (constitution P8 applied `K * |scenarios| *
|policies|` times). The per-Run `execution_id`s differ and appear only in
`experiment_execution.json`. The results file records every `run_id`, so a
drift is located to a Run. Under different code, the experiment execution
id differs and no equality is claimed.

### 7.4 Results and comparison

An Experiment execution writes two files (owner decision proposed as
D-26):

- `experiment_results.json`, the **Reproducible Experiment Result
  Surface**: the definition, `definition_hash`, the experiment execution
  id, `code_identity`, and per `(scenario, seed, policy)` the Run's
  `run_id`, Trace hash, Run outcome and the summary of §4, and per
  `(scenario, policy)` the aggregates below. It is byte-identical for every
  execution of the same definition under the same code; it contains no
  per-Run `execution_id`, path, timestamp or process fact;
- `experiment_execution.json`, the execution metadata: the experiment
  execution id, per-Run `execution_id`s and output paths, pid, timestamps.
  It may differ between executions and is outside every equality claim.

`experiment_results.json` holds per `(scenario, policy)` the aggregates
across seeds:

- mean and median across seeds of each metric (rendered as §4.2);
- the full per-seed vector (so the distribution can be drawn);
- **paired differences** against each baseline: for each seed,
  `metric(cost_based) - metric(baseline)` on the same Trace; reported as
  mean paired difference, median paired difference, and the count of seeds
  where the cost-based policy was better, equal, worse. Pairing by seed
  removes the between-trace variance that an unpaired comparison would
  confound with policy effect.

**Aggregation over null and absent metrics** (owner decision proposed
with D-20). Every metric is classified:

- *always-defined* for a `COMPLETED` run (counts and ratios whose
  denominator can never be zero): `n`, `completed`, `unserved`,
  `makespan`, `deferred.count`, `wrong_way.count`,
  `elevator_utilisation` (its denominator, the number of ticks, is at
  least 1); for an empty run these are 0 (§4.3) and participate with
  value 0; aggregated over every `COMPLETED` run of the `(scenario,
  policy)` cell;
- *conditional*: `tail_share`, `wait.*`, `total.*`, `travel.mean` (defined
  iff `n >= 1`), `wrong_way.mean_extra` (defined iff `wrong_way.count >=
  1`), `tail_ratio` (defined iff `n >= 1` and `mean wait > 0`). A null
  value is excluded from numeric aggregation, never treated as zero; each
  aggregate reports `n_defined`; if `n_defined = 0` the aggregate is
  `null`.
- *paired differences* exist only for seeds where both runs are
  `COMPLETED` and both values are defined; each paired aggregate reports
  `n_pairs`; win, tie and loss counts are over defined pairs only; if
  `n_pairs = 0` the paired aggregate is `null`.
- a `HALTED` run contributes only to `halted_count` for its cell and to
  the listing of its `unserved` and halt reason; it is excluded from every
  distribution aggregate and every paired comparison, and the cell reports
  `halted_count` beside `K`.

The canonical rendering of a `null` is the JSON `null`; a reader sees
`n_defined` and `n_pairs` beside every aggregate.

No significance test is run or claimed. With `K = 20` seeds the paired
win-count and the paired median over defined pairs are the honest summary;
the per-seed vector is published so a reader can judge spread, and
`n_pairs` and `halted_count` are published so a reader can see what was
left out.

### 7.5 What may be claimed

Permitted form:

> In the `<pattern>` regime with `F = .., N = .., C = ..`, across `K` seeded
> traces, the cost-based policy reduced p95 wait relative to Nearest Car in
> `w` of `K` traces, by a median of `d` ticks.

Not permitted: "the cost-based policy is better", "optimal", any claim
about a regime or building not in the Experiment, any claim based on
average wait alone, any claim from a single seed, and any claim comparing
against a baseline defined differently from
[scheduler_design.md](scheduler_design.md) §4.

### 7.6 Scale

Default Experiment: 9 patterns, 20 seeds, 3 policies = 540 runs. No timing
is claimed until measured; the plan's cut 8 records one measurement. No
parallelism is introduced unless a measured execution exceeds a few
minutes; if it is, it is `multiprocessing` over independent Runs, which
changes no semantics.

## 8. Comparative tests

[testing_contract.md](testing_contract.md) §4 pins the comparative tests:
same Trace hash across policies in every Experiment row; the Experiment
re-execution equality; and a small fixed Experiment whose results are
committed as evidence (not authority) so that a change in any policy's
behaviour is visible in review.
