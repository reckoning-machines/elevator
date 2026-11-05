# Cut 6 Implementation Record: Reporting, Metrics, Observations, Calibration

Status: **IMPLEMENTED / LOCAL VERIFY PASS. 2026-11-05.** Evidence record for plan cut 6 under the admitted plan against the admitted design baseline revision 7.2 ([decision 006](../decisions/owner_decision_006_revision_7_1_admission.md) as amended by [decision 008](../decisions/owner_decision_008_invariant_violation_halt.md)). Cut 7 was not started. Nothing is certified.

## 1. Baseline

- Governing design revision 7.2, digests re-verified unchanged before and
  after this cut: the seven unchanged files at record 006's digests;
  `docs/simulation_semantics.md`
  `821cb89dbbd49ac0c44080f0eddc817ae2f8fece211d5a43f37f8b355d8fbd9d`;
  `docs/testing_contract.md`
  `b0e78b99a824a0642f14adb45f9ac44e114fc40533ceae72259757b102d96001`.
- Plan: `26f6920ee56c9ef17e053db7ad1f6ed5d2f15e5606258d60069648790d64c24e`
  (record 008), unchanged.
- Starting standing: cuts 1, 2, 4, 5 `IMPLEMENTED / LOCAL VERIFY PASS`; cut 3
  `IMPLEMENTED / LOCAL VERIFY PASS / CPOC PENDING`; 132 tests passing. The
  owner reports an independent cut-5 audit `PASS`; no record of it is in the
  repository, so none is cited.

## 2. Scope checklist (admitted cut-6 row)

| Item | Plan text | Realised |
| --- | --- | --- |
| Governing contracts | evaluation §3, §4, §5; scheduler §9; semantics §3; constitution N18 | yes |
| Authority affected | none; everything `DERIVED` or `RECEIPT` (rows 22, 35, 39, 40) | yes: reporting reads a finished Run and writes nothing back |
| Expected files | `elevator/reporting.py` | yes |
| Tests | `position_exports_are_projections_of_tick_records`; `wide_export_one_row_per_timestamp`; `source_id_preserved_in_outputs` (output half); `numeric_rendering_pinned`; `empty_population_summary`; `empty_trace_completes_at_zero` (summary half); `zero_mean_tail_ratio_suppressed`; `observations_preconditions`; `reproducible_surface_excludes_execution_facts`; calibration zero-error property for untouched elevators | all (§5) |
| Evidence | pytest counts; one committed fixture's outputs | §7; `tests/fixtures/reporting/w_b_cost_based/` |
| CPOC | NOT APPLICABLE (derived) | NOT APPLICABLE: nothing persists or is reconstructed |
| Delta | NONE | NONE |

## 3. Files

| File | Change |
| --- | --- |
| `elevator/reporting.py` | created |
| `tests/report_fixtures.py` | created: `run_record` runs the real engine and wraps the result for reporting |
| `tests/unit/test_reporting.py` | created: 18 tests |
| `tests/invariants/test_exports.py` | created: 2 tests |
| `tests/reproducibility/test_reporting_surface.py` | created: 8 tests |
| `tests/fixtures/reporting/w_b_cost_based/` | created: the committed fixture, seven files |

No governing document, the plan, `engine.py`, `route.py`, `policies.py` or
`domain.py` changed.

## 4. The reporting surface

**Input.** `RunRecord(configuration, trace, identity, history, passengers)`:
domain values only. The Run outcome is read from the History's final
run-standing event (`COMPLETED` or `HALTED`), so reporting never imports the
engine. `reporting` imports only `elevator.domain` and the standard library;
it never names the engine, a policy, `route.project` or the three route
functions (AST-asserted), and a fresh interpreter importing it loads none of
those modules.

**Verification before any figure.** `_analyse` joins the History, the
Passenger records and the Trace by passenger id and refuses
(`ReportError`, nothing repaired) on any contradiction: out-of-order ticks or
sequence numbers, a History that does not end in a run-standing event, a
passenger assigned, boarded or alighted twice or out of order, a boarding at
the wrong car or floor, a Passenger field or standing that disagrees with its
events, a request that disagrees with the Trace, a `COMPLETED` run with an
uncompleted passenger, a halted run whose `unserved` count disagrees.

**Reproducible Output Surface** (`reproducible_surface(record)`, a pure function of
the Run that takes no execution fact): the eight files of evaluation §3.1, in
order.

| File | Content |
| --- | --- |
| `elevator_positions.csv` | `t,elevator_0,...,elevator_{N-1}`; one row per committed tick from `t = 0` to the final tick (idle ticks and request-time gaps included); each cell the floor at the start of the tick, read from the TickRecords; the final tick's row is the last record, with no post-final move. A halted run has the committed ticks only (header only when none) |
| `position_log_long.csv` | `t,elevator_id,floor,heading,load` per tick per elevator in id order |
| `passengers.csv` | the fifteen columns of §3.1 in order, by ascending `passenger_id`; CSV quoted by the standard library; supplied `source_id`s preserved |
| `summary.json` | §4 (below) |
| `observations.md` | §5 (below) |
| `run_identity.json` | `run_id`, Configuration, `configuration_hash`, `trace_hash`, policy name and parameters, `code_identity`, outcome (`standing`, `final_tick`, `halt_step`, `halt_reason`) |
| `events.jsonl`, `tick_records.jsonl` | one canonical JSON object per line, in order |

`execution_metadata(...)` serialises the Execution's own RECEIPT
(authority row 40) from values the caller supplies (it reads no clock, process or
Git state); `write_files(directory, files)` writes files and never overwrites. The
execution-output wrapper that binds the Operational Log, and `operational.jsonl`,
are cut 8's (they need `operations`).

## 5. Formulas and representations

Passenger rows (from the realized events, never from a projection):
`wait_time = pickup_time - request_time`; `travel_time = dropoff_time - pickup_time`;
`total_time = dropoff_time - request_time` (so `wait + travel = total`, and
`travel` equals the trip distance, constitution P11). A same-floor same-tick
boarding gives wait 0. `capacity_deferrals` and `wrong_way_passes` are
derived from the TickRecords alone under the direction-first rule: at a tick
where the passenger waits and its car is at its origin, the recorded heading
is the departure direction (a car with anyone onboard is never `FREE`, and a
`FREE` car with anyone waiting boards), so an opposite heading is a wrong-way
pass and a compatible heading with the passenger still waiting is a capacity
deferral, for which the recorded load must equal `C`; anything else is a
`ReportError`.

Summary (`summary.json`, canonical bytes, sorted keys, no trailing newline):
`n`, `completed`, `unserved`, `wait` and `total` each `{min, max, mean, median,
p95, std}`, `travel.mean`, `deferred.count`, `wrong_way.count` and
`wrong_way.mean_extra` (mean of `pickup_time - first wrong-way tick`),
`tail_share` (share with `wait > 2(F-1)`), `tail_ratio` (`p95 wait / mean
wait`), `makespan`, `elevator_utilisation` (per elevator, share of ticks `0..final` with
heading `!= NONE`).

Numeric representation (evaluation §4.2, exact, no floating point; an AST test
forbids float literals, `float`, `round` and `math` beyond `isqrt`): `min`,
`max`, `p95` integers, `p95` nearest-rank `(95n + 99) // 100`; `mean` and
`median` exact `Fraction`s rendered to three digits half away from zero by
`(2000|q| + 1) // 2`; `std` the `isqrt` of the exact variance scaled by 10^6
(truncation). All averages are decimal strings, never floats. Tests compare
the aggregates against an independent `decimal` implementation across 747
runs and pin `[0,0,1] -> 0.471`, `[1,2]` mean `1.500`, the `n = 1..20`
nearest-rank table and half-away rounding at `x.xxx5`, including negatives.

Observations (`observations.md`): the seven rules of §5, each emitted as one
`- ` line when its precondition holds: 1 tail ratio (`n >= 1`, mean wait > 0;
`Flagged: above 2.` when the ratio exceeds 2); 2 capacity deferrals (count of
passengers and the floors); 3 the maximum-wait passenger (ties to the lowest
id) and what its car was doing at the request tick, from its TickRecord; 4
wrong-way passes (`wrong_way.count >= 1`); 5 utilisation imbalance (`N >= 2`;
`Flagged: above 1/2.` when strictly above, so exactly 1/2 is not flagged);
6 the longest all-idle run of ticks (earliest on ties); 7 for `cost_based`
only, the Tier 2 share and the calibration summary.

Calibration (`calibration(record)`, scheduler §9): for each assignment whose
own ASSIGNED receipt carries `projected_pickup` and `projected_dropoff`,
one `CalibrationRow` with `pickup_error = realized_pickup - projected_pickup`
and `dropoff_error = realized_dropoff - projected_dropoff`: signed, never
clamped (positive means later than projected); `None` where the realized
time does not exist (a halted run); plus
`later_assignment_to_same_elevator` (any ASSIGNED event on the same elevator
with a higher sequence number, so a later same-tick assignment counts).
Assignments without projections (`round_robin`, `nearest_car`) yield no row:
nothing is fabricated and `route.project` is never re-run (the test disables
it). The report measures one thing: the effect of later lawful assignments on
a projection that was exact for the state known at the time. It is not
scheduler correctness and not a demand forecast.

Empty and halted (evaluation §4.3): see §6 for the readings taken.

## 6. Where the governing text left a choice (no rule changed)

These are rendering or reading choices, listed so the auditor can see each
one. None changes a metric definition, an authority row or a lifecycle rule;
each is one localized line if the owner reads the text differently.

1. **Empty-population `summary.json`.** §4.3 lists an object that omits
   `wait`, `total` and `travel`, and says in prose that every distribution
   field (`wait.*`, `total.*`, `travel.mean`) is `null`. I read the prose as
   governing: the keys exist and each field is `null`
   (`"wait":{"max":null,...}`, `"travel":{"mean":null}`), alongside the listed
   keys including `no_passengers: true`. The bytes are pinned in
   `empty_population_summary`. The other reading (keys omitted) is a
   one-line change. **This is the choice most worth the owner's check.**
2. **`observations.md` for a halted run** is unspecified. It is the single
   line `Run halted; no observation rules apply.`, parallel to the empty-run line.
3. **`passengers.csv` for a halted run** lists the committed Passenger
   records only (a passenger revealed in the failing tick was discarded; one
   not yet revealed has no record). Time cells that do not exist yet are
   empty, never zero; an onboard passenger therefore has pickup and wait
   filled and dropoff, travel and total empty.
4. **Line endings.** CSV and markdown lines end in `\n`; JSON documents are
   canonical bytes without a trailing newline; `.jsonl` is one canonical
   object per line.
5. **Observation wording.** §5 requires a sentence with the numbers behind it
   and states preconditions but not text; the templates are fixed strings pinned
   by `observations_preconditions`. "Flagged" is read as: the line is emitted
   whenever its precondition holds, with a flag sentence appended when the
   threshold is exceeded. Rule 2's "count" is the number of passengers
   (`deferred.count`). Rule 7's calibration summary is the number realized
   exactly and the min and max of each error.
6. **Deferral classification from recorded headings**: justified in §5; every
   case it cannot explain is a `ReportError` rather than a guess.
7. **`RunRecord` lives in `reporting`**, because the architecture gives it
   only `domain`; the API (cut 8) builds it from an engine.
8. **The committed fixture omits `run_identity.json`**, which contains the code
   identity and so changes with every edit; its shape is asserted instead.

## 7. Tests and verification

`tests/unit/test_reporting.py` (18): `source_id_preserved_in_outputs` (ids with
commas, quotes, newlines, unicode and leading zeros; stable-sort mapping);
wait, total and travel formulas over 1,500+ passengers; same-floor wait 0
and idle gaps; aggregates against an independent `decimal` implementation (200+
runs); a hand-checked W-B summary; wrong-way metrics on W-F; deferral columns
against the cut-3 test-side classifier over 1,000+ passengers; the calibration
witness; `calibration_zero_error_for_untouched_elevators` (977 rows: 374
untouched, all exactly zero; 603 touched, 30 nonzero); the calibration
reads the original receipt (forged receipts followed exactly, projection
disabled); baselines have no calibration; a halted run's calibration; halted
outputs (with and without committed ticks, onboard passenger); contradictory
records refused (seven tamperings); History not mutated; module structure;
`write_files`.

`tests/invariants/test_exports.py` (2): `position_exports_are_projections_of_tick_records`
and `wide_export_one_row_per_timestamp`: over 750 runs (249 cases times three
policies, plus three halted runs) the files are written to disk and compared
byte-for-byte with an independent regeneration from the TickRecords; rows `final + 1`
and columns `N + 1`; halted runs one row per committed tick.

`tests/reproducibility/test_reporting_surface.py` (8): `numeric_rendering_pinned`;
`empty_population_summary` (exact bytes); `empty_trace_completes_at_zero` (summary half);
`zero_mean_tail_ratio_suppressed` (W-A); `observations_preconditions` (each rule fires or
is omitted on constructed fixtures, including the exactly-1/2 imbalance boundary);
`reproducible_surface_excludes_execution_facts` (scan of all eight files, with a
negative control; two Executions with different Git provenance yield identical
surfaces); the committed fixture byte-exact; identical surfaces across two fresh
processes and an in-process run.

```text
python3 -B -m pytest -q tests/unit/test_reporting.py tests/invariants/test_exports.py tests/reproducibility/test_reporting_surface.py
  -> 28 passed
python3 -B -m pytest -q
  -> 160 passed in 10.04s
```

Counts: 28 new tests; full suite (cuts 1 to 6) 160 passed, 0 failed, 0 skipped, 0
errors, 0 expected failures. Cuts 1 to 5 remain green. No `__pycache__`. Code
identity: `705d82573789bc94980c5a4bb6f0a99c4e59e9938901953688e70dae946f63a3`.

The calibration witness (`CAL_ROWS`, `F = 6, C = 1`, one car idle at floor 4):
`r0` (1 to 2) is assigned first, projected pickup 6 and dropoff 7. `r1` (0 to 5)
joins the same car; the car serves floor 0 first, fills at floor 0 and returns
for `r0` only after delivering `r1`: `r0` realized 16 and 17, errors `+10` and
`+10`; `r1`, with no later assignment, projected 7 and 12 and realized 7 and 12,
errors 0. No worked calibration case exists in the governing documents; this one
was derived by hand and then confirmed by the run.

## 8. Delta and applicability

`ΔO = NONE / ΔS = NONE / ΔA = NONE`. OSA `REQUIRED` for the derived outputs
(rows 22, 35, 39, 40; evidence §7). CPOC `NOT APPLICABLE` (derived and
regenerated; nothing persists).

## 9. Worktree

Everything untracked; no HEAD commit; nothing committed.

## 10. Standing

```text
CUT 6: IMPLEMENTED / LOCAL VERIFY PASS
```

Next eligible cut: cut 7 (scenario generator). Not started.
