# Testing Contract

Status: **OBLIGATION DOCUMENT. Revision 7.2 (owner decision 008: `detected_corruption_halts_the_run`, 2026-11-05). Admission standing is recorded in `docs/decisions/`, not here.**

Jurisdiction: the acceptance suite that must exist before any rule in the
governing documents is claimed verified. Each test names the rule it proves
and the document section that owns the rule. A test that does not prove
its named rule is a defect of this contract, found by the audit question
"what would pass this test and still violate the rule?". Tests are evidence,
never authority: an expected-output fixture that disagrees with a governing
document is a wrong fixture.

Conventions: all tests are deterministic; fixtures are committed Traces with
recorded hashes; Monte Carlo and CPOC tests may be slow and are marked so,
but are never excluded from the suite that a verification record cites.
"History" below means the Simulation History unless "Operational Log" is
written.

## 1. Unit and behavioural (`tests/unit/`)

Each test constructs a tiny Trace, runs the engine with a named policy, and
asserts exact Simulation Events and TickRecords (not just metrics).

| Test | Rule proved | Owner section |
| --- | --- | --- |
| `one_elevator_one_passenger_up` | W-A: `BOARDED` at 0, `ALIGHTED` at 3, positions 0,1,2,3, final tick 3, wait 0, travel 3 | semantics §2, §3 |
| `one_elevator_one_passenger_down` | mirror, elevator initial floor 5, request 5 to 2 | §3 |
| `same_floor_pickup_at_request_time` | elevator idle at 4, request at `t=6` from 4: boards at 6 with `wait = 0`; TickRecord 6 shows `boarded=[p]` | §2.1, §6 |
| `same_floor_source_destination_refused` | a row with `source == dest` is refused at load with its `input_index` and `source_id` | §6; evaluation §2 |
| `missing_source_id_refused`, `duplicate_source_id_refused` | rows without an id, or with a repeated id, refuse with the named reason and both positions | evaluation §2 |
| `source_id_preserved_in_outputs` | `passengers.csv` carries the supplied ids; the mapping to `passenger_id` is the stable sort | constitution §2; evaluation §2, §3 |
| `pickup_then_move_same_tick` | boarding at `t` and position `floor+1` at `t+1` (zero dwell) | §6 |
| `alight_before_board_frees_room` | `C=1`, passenger A alights at floor 5 at `t`, passenger B assigned to the same car boards at 5 at `t` | §2.1, §5 |
| `deferred_boarding_then_return` | W-B: `C=1`, car full passes floor 2 where a same-direction passenger waits; TickRecord shows the car at 2 with the passenger not boarded; the car returns and boards; `capacity_deferrals = 1` | §5 |
| `direction_deferral_then_return` | W-F: passenger 2 to 1 assigned to a car continuing up through 2; not boarded; boards on the return when the car is free; `wrong_way_passes = 1`; `travel_time = 1` | §5, §4.1 |
| `deferral_classification_direction_first` | W-F tick 2: a car that is full and departing the other way records one wrong-way pass and no capacity deferral (capacity not evaluated); a `FREE` full car records a capacity deferral for every waiting passenger; a compatible full continuing car records a capacity deferral | §4.2 |
| `free_car_oldest_sets_direction` | idle car, two passengers at its floor, older one down-bound, younger up-bound: the older boards, the car departs down, the younger waits and boards on the return | §4.1, §4.2 |
| `reversal_point_is_free` | W-G: car between an up-bound passenger above and a down-bound passenger below serves both; the run completes (the rejected rule oscillates) | §4.1 |
| `promised_direction_overrides_nearest` | idle car at 5 boards a passenger to 3 while a newly assigned waiting passenger is at 6: heading is `DOWN` (the promise), not `UP` (the nearer stop) | §4.1, step 5 |
| `reversal_only_when_nothing_ahead` | with stops above and below, the car continues its heading until the last stop ahead, then reverses in the same tick | §4 |
| `idle_tie_prefers_up` | idle car at 5 with stops at 3 and 7: heading `UP` | §4 |
| `departure_direction_cases` | unit tests of `departure_direction` for: `NONE`; `UP` with a stop above; `UP` with none above; `DOWN` likewise | §4.1 |
| `eligible_boarders_cases` | unit tests of `eligible_boarders`: `FREE` then first sets direction; direction before capacity; full `FREE` car boards nobody and stays `FREE` | §4.2 |
| `route_primitives_single_implementation` | the engine module calls `route.departure_direction`, `route.eligible_boarders` and `route.next_heading` by identity (the functions the engine's step-4 and step-5 code references are the same objects `route` exports), and `project` calls the same three objects; the engine and policy modules define no function whose name or body computes a departure direction, boarding eligibility or heading (AST assertion over the modules) | §4.3; scheduler §5 |
| `simultaneous_requests_sequential_assignment` | two requests at `t=0`; the second's `SchedulerView` contains the first's assignment; `ASSIGNED` events in id order | §2 step 2, §6 |
| `sparse_requests_idle_gaps` | requests at `t=0` and `t=40`; TickRecords exist for every tick 0..final; headings `NONE` throughout the gap | §6 |
| `request_time_skip_ticks_through` | Trace with times 0 and 100 only; the History has 101+ TickRecords | §6 |
| `multiple_elevators_independent_same_floor` | two cars at floor 2, passengers assigned to each; each boards only its own | §6 |
| `deterministic_tie_nearest_car` | two cars equidistant: lowest id chosen | scheduler §4.2 |
| `deterministic_tie_cost_based` | two cars with identical cost: lowest id | scheduler §6.4 |
| `round_robin_is_id_mod_n` | assignment equals `passenger_id mod N` for a 7-passenger Trace, `N=3` | scheduler §4.1 |
| `capacity_exactly_full` | `C=2`, two passengers board at one stop; a third assigned to the same car at the same floor is deferred | §5 |
| `capacity_overflow_impossible` | there is no API to set load; constructing `C+1` onboard passengers through the engine's API is impossible | constitution N6 |
| `halt_discards_partial_tick` | two requests at `t=0`; a stub policy accepts the first and returns `N` for the second: `HALTED` at tick 0 step 2 for passenger 1; no `ASSIGNED` for passenger 0 survives; no TickRecord 0 | constitution §4.3 |
| `policy_invalid_proposal_halts` | W-E: a stub policy returning `N` halts with `INVALID_PROPOSAL`; History is the `HALTED` event only | §6 |
| `policy_exception_halts` | a stub raising halts with `POLICY_ERROR` | §6 |
| `detected_corruption_halts_the_run` | a shared primitive patched for one tick to produce (a) a wrong-way boarding, (b) a load above `C`, (c) a heading that leaves the building: each halts `INVARIANT_VIOLATION` at the failing step with the violated invariant in the diagnostic; the failing tick is discarded and every earlier tick kept; exactly one `HALTED` event is appended; the Run is final and, after the primitive is restored, `step()` performs no work | §2, §6 (owner decision 008) |
| `termination_waits_for_unrevealed_requests` | all passengers complete at `t=5`, a request exists at `t=9`: the run continues; final tick > 9 | §8 |
| `empty_trace_completes_at_zero` | one TickRecord, outcome `COMPLETED`, the empty-population summary of evaluation §4.3 byte-exact, the single-line observations | §6; evaluation §4.3 |
| `normalization_shared_by_batch_and_live` | `simulate` and `create_engine` produce the same Trace hash from the same rows; `create_engine` returns a `RUNNING` engine at `t = 0` whose first step matches tick 0 of `simulate`'s History | evaluation §2 |
| `source_id_normalization_cases` | integer `1` and string `"1"` collide (`DUPLICATE_SOURCE_ID`); `"01"` is distinct; rows `"z"` then `"a"` at equal times keep input order | evaluation §2 |
| `configuration_domain_refusals` | `F = 1`, `F = 201`, `N = 0`, `N = 21`, `C = 0`, `C = 51`, `time = 10^9 + 1`, `100001` rows: each refuses with the named reason | evaluation §2 |
| `horizon_halt_reasons_distinct` | a run under an explicit small `max_ticks` halts `HORIZON_EXCEEDED` with `unserved > 0`; `LIVENESS_BOUND_EXCEEDED` is reserved for exceeding the default bound; a `max_ticks` above the default is refused `INVALID_CONFIGURATION` | §8.3 |
| `projection_exactness` | for every elevator that receives no assignment after tick `t` in a fixture, `project` at `t` equals realized times (constitution P9) | scheduler §5 |
| `projection_observation_phase` | the projection's `deferred` and `wrong_way_passes` for a fixture equal the realized `capacity_deferrals` and `wrong_way_passes` from the History for untouched elevators | scheduler §5 |
| `cost_based_tier1_before_tier2` | a state where one car is Tier 1 and another is cheaper but Tier 2: the Tier 1 car is chosen with `tier = 1` | scheduler §6.2 |
| `cost_based_tier2_fallback` | every car is Tier 2: the cheapest is chosen and the receipt says `tier = 2` (W-B) | §6.2 |
| `tier1_is_incremental` | the audit's case: `F=5, C=1`, requests `0->4`, `2->4`, `4->3` at `t=0`: the third candidate is Tier 1 although the second is already projected capacity-deferred; the receipt's `newly_deferred_others` is empty | §6.2 |
| `tier1_receipt_not_a_guarantee` | a Tier 1 passenger is later capacity-deferred by a subsequent Tier 2 assignment to the same car; the first receipt still says `tier = 1` and is not rewritten | §6.2, constitution N10 |
| `cost_based_marginal_equals_projection_delta` | for random small states, `marginal` equals the age-weighted sum of `with.dropoff - base.dropoff` over committed passengers; includes the audit's negative case (`F=8, C=1`: `5->0`, `5->6` at 0, candidate `6->7` at 4: marginal `-66`, cost `-52`, Tier 1) | §6.1 |
| `cost_exact_integer` | costs are `int` for all candidates in a fixture | constitution N16 |
| `receipt_never_on_passenger` | the Passenger record type has no estimate field; the `ASSIGNED` event carries the receipt | constitution N10 |
| `checkpoint_at_zero_reconstructs_initial_floors` | write a Continuation Document before tick 0 (in-process, not CPOC), load it: elevators at configured initial floors, headings `NONE`, no TickRecords, no events | cpoc §5 step 11 |

## 2. Invariants (`tests/invariants/`)

Run over every committed fixture Trace and every policy, and over the
property-generated Traces of §5. Each asserts over the full Simulation
History.

| Test | Invariant |
| --- | --- |
| `one_floor_per_tick` | P1 |
| `floor_in_bounds` | P2 |
| `load_never_exceeds_capacity` | P3 (count `ONBOARD` per car per tick from events) |
| `order_of_life` | P4 |
| `assignment_written_once_at_request_time` | P5, N2 |
| `one_pickup_one_dropoff_per_completed` | P6 |
| `at_most_one_elevator_per_passenger` | P5 |
| `one_tick_record_per_tick_per_elevator` | P7 (and for a `HALTED` fixture, exactly the completed ticks) |
| `travel_equals_distance` | P11 |
| `never_picked_up_before_request` | N4 |
| `never_dropped_before_pickup` | N5 |
| `never_boarded_wrong_way` | N7 (every `BOARDED` matches the car's recorded heading at that tick) |
| `no_operational_record_in_history` | N18 (the Simulation History type cannot hold an Operational Record; the serialised History contains none) |
| `destination_never_changes` | N3 (the only destination in any event equals the Trace's) |
| `tick_record_floor_consistent_with_motion` | floor(t+1) = floor(t) + delta(heading(t)) |
| `events_and_fields_agree` | every `ASSIGNED`/`BOARDED`/`ALIGHTED` matches the Passenger field and vice versa |
| `every_passenger_completes` | P10 for every fixture and generated Trace under all three policies |
| `liveness_bound_holds` | final tick `<= T_last + 2 P (F-1)` for every fixture and generated Trace; a failure is reported as an invariant failure and the proof in semantics §8.2 is re-examined; the bound is not loosened |
| `heading_none_iff_no_committed_stops` | §4 |

The two export checks below belong to the reporting cut, not the engine
cut, because they read written files:

| Test | Invariant |
| --- | --- |
| `position_exports_are_projections_of_tick_records` | regenerate both `elevator_positions.csv` and `position_log_long.csv` from TickRecords and compare with the written files, byte-equal |
| `wide_export_one_row_per_timestamp` | `elevator_positions.csv` has exactly `final + 1` rows and `N + 1` columns; for a `HALTED` run, one row per committed tick (header only when none) | evaluation §3 |

## 3. No-look-ahead (`tests/invariants/test_no_look_ahead.py`)

The compared surface (constitution N1): for two Traces `T` and `T'` that
agree on every Request with `request_time <= t*`, let `end = min(t*,
final_T, final_T')`. The **decision and motion prefix** is: every
`REVEALED`, `ASSIGNED` (with receipt), `BOARDED` and `ALIGHTED` event with
tick `<= end`, and every TickRecord with tick `<= end`. Run-standing events
(`COMPLETED`, `HALTED`) and any record after `end` are excluded: termination
lawfully depends on whether unrevealed Requests remain.

| Test | Rule |
| --- | --- |
| `view_has_no_future` | for every `SchedulerView` built during a run, every passenger in it has `request_time <= t`; the view type has no attribute referencing the Trace or engine (checked by inspecting its fields) |
| `future_mutation_does_not_change_prefix` (negative witness) | run `T` to completion, recording every Proposal by `(t, passenger_id)`. Build `T'` identical for `request_time <= t*` and arbitrary (random, several variants, including removing and adding Requests) for `request_time > t*`. Run `T'`. Assert the decision and motion prefixes are identical and every Proposal at `<= end` is identical. Repeat for several `t*` and all three policies |
| `future_mutation_both_active` | as above, with `T` and `T'` each containing a Request at a time `> t*` so that neither terminates before `t*`; then `end = t*` and the full prefix through `t*` must be identical, including idle TickRecords |
| `sentinel_future_request` | add one extra Request at `request_time = t* + 1` to a fixture; the decision and motion prefix through `end` is identical |
| `policy_cannot_import_trace` | the policies module imports nothing from the engine module and has no access path to a Trace (import graph assertion) |

What would pass a weaker test and still violate the rule: a policy that
reads a module-level global the engine populates; the import-graph and
view-field tests close that path. A policy that peeks at `len(view...)`
to infer future count: the view holds only revealed passengers, so there is
nothing to infer. What the old universal equality got wrong: it required
identical `COMPLETED` events and identical tick counts, which a correct
engine cannot provide when one Trace legitimately ends earlier.

## 4. Comparative scheduler (`tests/comparative/`)

| Test | Rule |
| --- | --- |
| `same_trace_hash_across_policies` | in a small Experiment, every `(scenario, seed)` row has one Trace hash across all policies | evaluation §7.2 |
| `experiment_reexecution_identical` | execute a 3-pattern, 3-seed Experiment twice under the same code; `experiment_results.json` byte-identical with the same experiment execution id; `experiment_execution.json` differs in per-Run `execution_id`s, paths and timestamps and nowhere else | §7.3, §7.4 |
| `experiment_results_surface_excludes_execution_facts` | a scan of `experiment_results.json` for any per-Run `execution_id`, path, timestamp or pid finds none | §7.4 |
| `committed_experiment_evidence` | a fixed Experiment's committed results match a fresh execution (evidence that behaviour did not change silently; a change requires updating the fixture in the same change with a note) | §8 |
| `paired_difference_arithmetic` | paired differences, win/tie/loss counts computed correctly on a hand-built results set | §7.4 |
| `cost_based_not_worse_on_capacity_stress_fixture` | on the committed `capacity_stress` fixture, `cost_based` p95 wait `<=` each baseline (a regression guard on one fixture, not a claim) | §7.5 |

## 5. Property-based (`tests/property/`, `hypothesis`)

Generated Configurations (`F` in 2..12, `N` in 1..4, `C` in 1..6) and Traces
(up to 40 requests, times up to 60, valid floors, unique ids). Each
generated case runs all three policies and applies every invariant of §2
and §3's `view_has_no_future`. Shrunk failures are committed as fixtures.

Additional properties:

- `projection_exactness_property`: for a random `t`, for every car with no
  later assignment, projection equals realization;
- `checkpoint_roundtrip_property` (not CPOC): write a Continuation Document
  at random `t`, load it in the same process, continue, equal Simulation
  History. This is a cheap guard; it does not count as CPOC evidence and is
  labelled so.

## 6. Reproducibility and reporting (`tests/reproducibility/`)

| Test | Rule |
| --- | --- |
| `splitmix_reference_vector` | the generator primitive reproduces a committed vector of the first 16 outputs for seed 0 and seed 2^64 - 1 | evaluation §6.1 |
| `generate_is_pure` | `generate(scenario, seed)` twice: identical Trace and hash, for every pattern; a committed expected Trace per pattern for seed 7 | evaluation §6 |
| `generate_refuses_invalid_parameters` | each refusal rule of evaluation §6.2 and §6.3: every parameter at each domain edge and one past it (`m = F` accepted, `m = F + 1` refused; `k = 1000` accepted, `1001` refused; `w`, `g`, `j`, `horizon`, `num_requests`, `origin` likewise); `num_requests <= N*C` for capacity stress; an unknown parameter for a pattern; `p_lobby` supplied at all | §6.2, §6.3 |
| `same_inputs_same_history` | simulate the same `(config, trace, policy)` twice in separate processes; Simulation History and every file of the Reproducible Output Surface byte-identical, including `run_identity.json`; `execution_metadata.json` differs in `execution_id`, pid and timestamps | P8 |
| `reproducible_surface_excludes_execution_facts` | a scan of every surface file for `execution_id`, `store_id`, the Git SHA, a timestamp or a scenario label finds none; two Executions with different Git provenance (a README-only commit between them) have byte-identical surfaces | constitution N18; evaluation §3.1 |
| `seed_domain_refused` | `seed = 2^64` refuses `INVALID_SCENARIO_PARAMETERS`; `seed = 2^64 - 1` is accepted | evaluation §6.1 |
| `experiment_null_aggregation` | a hand-built results set with null `wrong_way.mean_extra`, an empty-population run and a halted run: aggregates report `n_defined`, `n_pairs`, `halted_count`; nulls are excluded, never zero; the empty run contributes `deferred.count = 0` and `wrong_way.count = 0` as defined values and `tail_share = null` as undefined (`n_defined` excludes it); paired differences only over defined completed pairs | evaluation §4.3, §7.4 |
| `sparse_cross_parameter_refused` | `num_requests = 1002, g = 10^6, j = 0` refuses `INVALID_SCENARIO_PARAMETERS` naming `num_requests, g, j` before any draw; `num_requests = 1001, g = 10^6, j = 0` is accepted and its last time is `10^9`; the emitted-time guard never fires on any accepted default scenario | evaluation §6.3 |
| `run_id_changes_with_params` | changing any cost weight changes `run_id`; changing nothing does not | constitution §12 |
| `code_identity_tracks_package_bytes` | adding one comment byte to a copy of the simulation package changes its code identity; the Git SHA is recorded as provenance and does not participate | constitution §2; authority row 4 |
| `execution_environment_contract` | a governed entry point started without `-B` (bytecode writing enabled), or with a `__pycache__` directory inside the package, refuses `UNSUPPORTED_EXECUTION_ENVIRONMENT`; started under the contract it proceeds; a source file modified after start is reported as `CODE_IDENTITY_DRIFT` at exit | constitution §12 |
| `canonical_serialisation_stable` | serialise, parse, serialise: identical bytes | architecture §4 |
| `numeric_rendering_pinned` | hand-built populations: `[0,0,1]` renders `std` as `0.471`; mean of `[1,2]` renders `1.500`; `p95` of `n=1..20` matches the nearest-rank table; half-away-from-zero rounding at `x.xxx5` | evaluation §4.2 |
| `empty_population_summary` | the exact `summary.json` bytes and `observations.md` line of evaluation §4.3: counts 0, `tail_share` and every distribution field `null` | §4.3 |
| `zero_mean_tail_ratio_suppressed` | W-A's summary has `tail_ratio: null` and no rule-1 observation | §4.3, §5 |
| `observations_preconditions` | each rule fires only when its precondition holds, on constructed fixtures | §5 |

## 7. CPOC (`tests/cpoc/`)

Exactly the witness and the negative witnesses of
[cpoc_design.md](cpoc_design.md) §4 and §6. The rows marked cut 9 in cpoc
§6 are local continuity-negative tests under `tests/cpoc/local/`,
executable with the checkpoint and store modules and an in-process engine
and needing no process orchestration; the rows marked cut 10 are the
witness tests under `tests/cpoc/witness/`, orchestrated with
`subprocess`, real PIDs and `SIGKILL`, in a fresh Store the test creates,
writing the evidence record of cpoc §7; row 29(b) is a UI test (§8). The
in-process round-trip of §5 is not in this directory and may not be cited
as CPOC evidence.

Structural obligations the CPOC tests also assert (the bounded assurance
standard of cpoc §4.1):

- `construct_state` takes exactly one argument of type `Snapshot` and
  rejects any other type at runtime; `Snapshot` is produced only by
  `parse_snapshot(document)`; `HistoryPrefix` and `HistoryVerifier` are
  distinct types with no conversion to `Snapshot` or `EngineState`;
- `no_history_to_state_path_in_package`: a scan of every module in the
  simulation package and the web package (import graph, call graph and
  annotations) finds no function that accepts a `HistoryPrefix`, a list
  of events or tick records, or a `HistoryVerifier` and returns a
  `Snapshot`, an `EngineState` or a value passed to `construct_state`;
  a deliberately cheating fixture module under `tests/cpoc/cheats/` that
  builds a `Snapshot` from events is detected by the same scan (the test
  asserts detection, then excludes the fixture from the real package);
- `history_verifier_isolated`: the verifier type has no attribute or
  method returning a `Snapshot` or `EngineState`, and the loader discards
  it (no reference survives the load);
- the loader's eleven verifications run in the stated order: one fixture
  per negative witness of cpoc §6, constructed exactly as its row says
  (mutation, recomputed integrity fields, preserved bindings), asserting
  the named reason and that every earlier step passed;
- `write_admission_stale_writer`: cpoc §6 row 9 exactly: a `RUNNING`
  document at `write_sequence = 1`; writer A's admitted checkpoint write
  advances it to `write_sequence = 2` and A now holds token 2; a write
  with token 1 against the still-`RUNNING` document refuses
  `STALE_WRITER` and leaves A's document intact;
- `write_admission_after_final`: cpoc §6 row 10 exactly: after the
  admitted finality write (`write_sequence = 2`), a checkpoint write with
  the current token 2 refuses `WRITE_AFTER_FINAL`;
- `receipt_hash_matches_path`: the document's SHA-256 in
  `CHECKPOINT_WRITTEN` equals the bytes at the path (cpoc §3.2);
- Component mapping for these existing lifecycle tests (revision 7.1):
  `operations` depends only on domain/stdlib; API invokes it for Execution
  creation and never imports checkpoint; reporting's execution-output
  wrapper invokes it for output-only binding; checkpoint uses the same
  handle for Store binding and receipts. The import/call-graph checks
  assert these paths when their cuts exist (API/output paths in cut 8,
  checkpoint integration in cut 9). No log buffer/append implementation
  moves into checkpoint, and operations cannot interpret Store identity,
  Continuation Documents or simulation state. These assertions extend
  the existing lifecycle obligations; no earlier cut needs a later module.
- `operational_log_flush_at_binding`: cpoc §6 row 33; and
  `never_bound_execution_has_no_file`: row 34 (its CPOC-refusal half runs
  in cut 10);
- `operational_log_op_seq_continuous`: `op_seq` starts at 1, is
  contiguous across the in-memory period, the flush, two checkpoints and a
  resume (in-process), with no duplicate record;
- `independent_executions_same_run`: cpoc §6 row 7 (two Executions of one
  `run_id` in one Store, one final, the other resumable; identical
  Simulation Histories);
- `LOAD_ADMITTED.constructed_state_hash` equals `snapshot_hash` and the
  record's document SHA-256 equals the receipt's, on a successful load
  (value-equality evidence, not provenance).

## 8. UI (`tests/web/`)

Minimal: `POST /runs` creates a session; `step` with a stale `from_time`
returns the unchanged state with a notice and executes no tick (engine `t`
unchanged, History length unchanged); `step_on_final_run_is_noop`; the
history view obeys the lawful range of [ui_design.md](ui_design.md) §2.2:

- `history_at_creation`: a new session at `t = 0` has no TickRecord;
  `GET .../tick/0` returns `NO_HISTORY` (the governing result of ui §2.2
  when no record exists);
- `history_current_tick_refused`: after one step (`t = 1`), `tick/1` returns
  `HISTORY_TICK_NOT_AVAILABLE` and does not render current state; `tick/0`
  renders from TickRecord 0;
- `history_row_after_advancing`: after another step, `tick/1` renders from
  TickRecord 1 and `tick/0` is unchanged;
- `history_final_tick_completed`: on a `COMPLETED` run, `tick/final` renders
  and `tick/final+1` is refused;
- `history_halted_range`: on a run halted at tick `k` (W-E-style halt at a
  later tick), `tick/k-1` renders and `tick/k` is refused
  (`HISTORY_TICK_NOT_AVAILABLE`); on W-E itself (halt at tick 0, no
  TickRecord), every `tick/*` returns `NO_HISTORY`;
- `ui_new_run_creates_engine_not_simulate`: `POST /runs` yields a session
  at `t = 0` with standing `RUNNING` and no outputs written; the server's
  call graph for that route reaches `create_engine` and not `simulate`;
- `ui_projection_matches_engine`: cpoc §6 row 29(b): the shaft projection
  rendered for a session equals the engine's floors, headings and loads
  at the same `t`;
- `ui_first_checkpoint_flushes_log`: a session stepped to tick 5 then
  checkpointed has `EXECUTION_STARTED` as `op_seq` 1 in the Store's log
  before its first `CHECKPOINT_WRITTEN`;

the evaluate page returns the paired-difference table for a tiny
Experiment; a second client on the same session sees the same `t`; a
session is reopened by Store and `execution_id`, never by a file path.
Rendering details are not tested.

## 9. What is not tested, and why

- Performance beyond "the default Experiment completes within a few
  minutes" (one timing assertion, whose measured value the plan's cut 8
  records).
- Visual layout.
- Behaviour under unbounded adversarial demand (outside the liveness claim;
  measured in the Experiment, not asserted).
- Deliberate overwrite of a Continuation Document inside its own Store
  (cpoc §6 row 6 records the limit).
- Malicious replacement of executing instructions after process start, or
  a loader that violates its typed boundary through means the call-graph
  scan cannot see (cpoc §4.1 records the bounded assurance standard).
