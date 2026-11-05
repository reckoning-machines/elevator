# Cut 3 Implementation Record: Simulation Engine

Status: **IMPLEMENTED / LOCAL VERIFY PASS / CPOC PENDING. 2026-11-05.** Evidence record for plan cut 3 under the admitted plan ([decision 007](../decisions/owner_decision_007_implementation_plan_admission.md)) against the admitted design baseline revision 7.1 ([decision 006](../decisions/owner_decision_006_revision_7_1_admission.md)). Cut 4 was not started. Nothing is certified; the cut-10 witness does not exist.

## 1. Baseline

- Governing design revision 7.1: the nine digests of record 006, re-verified
  unchanged before and after this cut.
- Plan: `6254fffaea4c48582ae20733a5995ca6511a24f9d057de0e84efabfb82138d84`, unchanged.
- Starting standing: cut 1 and cut 2 `IMPLEMENTED / LOCAL VERIFY PASS`. The
  owner reports an independent cut-2 audit passed with no findings; no
  record of it is in the repository, so this record does not cite one.

## 2. Scope checklist (admitted cut-3 row)

| Item | Plan text | Realised |
| --- | --- | --- |
| Governing contracts | semantics §2, §3, §5, §7, §8; constitution §4.3, §4.4, §8, §9, P1 to P7, P10, P11, N1 to N9, N12, N15, N18 | yes |
| Authority affected | the engine becomes the writer of every runtime fact (rows 8 to 15, 17, 18) through the tick procedure; Simulation History emitted atomically; `engine.create` at `t = 0` | yes (§4) |
| Expected files | `elevator/engine.py` | yes; plus the decision-surface value types in `elevator/domain.py` (§7, choice 1) and the tests |
| Tests | the cut-3 list, with a stub policy, reading no written file | all 43 identifiers, §5 |
| Failure behaviour | `HALTED` with a named reason; never a default | `INVALID_PROPOSAL`, `POLICY_ERROR`, `LIVENESS_BOUND_EXCEEDED`, `HORIZON_EXCEEDED` |
| CPOC | REQUIRED: `CPOC PENDING` until cut 10 | `CPOC PENDING` |
| Delta | NONE | NONE |

## 3. Files

| File | Change |
| --- | --- |
| `elevator/engine.py` | created: `Engine` (`create`, `step`, `run`, read-only `t`, `standing`, `outcome`, `max_ticks`, `passengers`, `elevators`, `history`, `load`), `RunOutcome`, `SchedulerPolicy` protocol, halt reason constants, `EngineInvariantViolation` |
| `elevator/domain.py` | appended: `OnboardView`, `WaitingView`, `ElevatorView`, `SchedulerView`, `RevealedRequest`, `Proposal` (scheduler §2, §3). Cut-1 code unchanged |
| `tests/engine_fixtures.py` | created: stub policies, fixture builder, stepwise runner, test-side deferral classifier |
| `tests/unit/test_engine.py` | created: §1 behavioural tests and structural tests |
| `tests/invariants/test_engine_invariants.py` | created: §2 engine-local invariants and §3 `view_has_no_future` |

## 4. Engine authority and state

Engine-owned (written only in the tick procedure): `t`; every revealed
Passenger (standing, assignment, pickup, dropoff); every Elevator's floor
and heading; the Run outcome; the Simulation History (events with sequence
numbers from 0, TickRecords). Derived on demand, never stored: load,
onboard and waiting sets, committed stops. The departure direction lives
only in a local of one tick. There is no setter, no public mutable
collection, and no module-level mutable state; the public surface is
exactly `create`, `step`, `run` and the read-only properties
(`capacity_overflow_impossible` asserts this).

## 5. Tick procedure and tests

`Engine.step` executes the nine steps in order on working copies:

1. reveal (`REVEALED` per passenger in id order);
2. assign: for each revealed passenger, build a fresh `SchedulerView` from
   the working state (earlier same-tick assignments included, later ones
   absent), call `policy.assign(view, request)`, validate (`Proposal`
   instance, integer non-bool id in `0..N-1`, receipt a mapping or none),
   write the assignment, emit `ASSIGNED` with a copy of the receipt; an
   exception halts `POLICY_ERROR`, a bad proposal `INVALID_PROPOSAL`;
3. alight (ascending elevator, then passenger id);
4. board: `route.departure_direction`, then `route.eligible_boarders` over
   the waiting passengers at the floor in id order with the post-alighting
   load;
5. head: the promised departure if `UP`/`DOWN`, else `route.next_heading`
   over the post-boarding committed stops;
6. record (beginning-of-tick floor, post-step-5 heading, post-boarding load,
   boarded and alighted ids);
7. terminate when every request is revealed and every passenger completed
   (emit `COMPLETED`, keep the tick, no move); else halt when `t + 1 >
   max_ticks` with `LIVENESS_BOUND_EXCEEDED` if the effective horizon is
   the default bound `T_last + 2P(F-1)`, else `HORIZON_EXCEEDED`;
8. move one floor by heading;
9. advance.

Tests (contract identifier = function name after `test_`):

- `tests/unit/test_engine.py` (23 contract tests): `one_elevator_one_passenger_up`,
  `one_elevator_one_passenger_down`, `same_floor_pickup_at_request_time`,
  `pickup_then_move_same_tick`, `alight_before_board_frees_room`,
  `deferred_boarding_then_return`, `direction_deferral_then_return`,
  `deferral_classification_direction_first`, `free_car_oldest_sets_direction`,
  `reversal_point_is_free`, `promised_direction_overrides_nearest`,
  `simultaneous_requests_sequential_assignment`, `sparse_requests_idle_gaps`,
  `request_time_skip_ticks_through`, `multiple_elevators_independent_same_floor`,
  `capacity_exactly_full`, `capacity_overflow_impossible`,
  `halt_discards_partial_tick`, `policy_invalid_proposal_halts`,
  `policy_exception_halts`, `termination_waits_for_unrevealed_requests`,
  `horizon_halt_reasons_distinct` (halt half), `route_primitives_single_implementation`;
  plus two supporting tests outside the cut-3 row: `empty_trace_completes_at_zero`
  (engine half only; the contract test's summary half is cut 6's) and
  `engine_imports_no_later_cut_module`.
- `tests/invariants/test_engine_invariants.py` (20): `one_floor_per_tick`,
  `floor_in_bounds`, `load_never_exceeds_capacity`, `order_of_life`,
  `assignment_written_once_at_request_time`, `one_pickup_one_dropoff_per_completed`,
  `at_most_one_elevator_per_passenger`, `one_tick_record_per_tick_per_elevator`,
  `travel_equals_distance`, `never_picked_up_before_request`,
  `never_dropped_before_pickup`, `never_boarded_wrong_way`,
  `no_operational_record_in_history`, `destination_never_changes`,
  `tick_record_floor_consistent_with_motion`, `events_and_fields_agree`,
  `every_passenger_completes`, `liveness_bound_holds`,
  `heading_none_iff_no_committed_stops`, `view_has_no_future`.

The worked examples are pinned exactly: W-A (floors, headings, loads,
event sequence 0 to 4), W-B, W-E, W-F, W-G; the W-B run also reproduces
W-D's event sequence (`BOARDED p1` at seq 6, `COMPLETED` at seq 8).

The invariants run over 9 hand fixtures and a 240-case deterministic sweep
(`F` 2 to 7, `N` 1 to 3, `C` 1 to 3, up to 8 requests at times 0 to 11,
random initial floors), each under two stub policies: 498 runs, 1954
passengers, 322 multi-elevator runs, 198 capacity deferrals, 200 wrong-way
passes, 1326 reversals. Every run completed within the proved bound.

## 6. Atomicity, boundary and route sharing

- **Atomicity.** A tick works on a copy of the passenger map, a list of
  the elevators and a local event buffer. Only after step 7 (completion) or
  step 9 (advance) do the copies replace engine state and the buffer get
  sequence numbers. A halt in step 2 or step 7 discards the working tick
  and appends one `HALTED` event (step, reason, passenger, unserved count
  from the committed state) at the next sequence number.
  `halt_discards_partial_tick` pins both a tick-0 halt (no `ASSIGNED`
  survives; no TickRecord) and a tick-3 halt (TickRecords 0 to 2 survive).
  A halt in step 7 discards that tick's TickRecord too, as constitution
  §4.3 and the UI's halted history range require.
- **No look-ahead.** The view is built from the working passenger map,
  which holds only assigned revealed passengers; requests are indexed by
  time and read only in step 1. `SchedulerView` and its parts are frozen
  values whose fields are ints and tuples; they reference no Trace, engine
  or History. `view_has_no_future` checks every view built in 89 runs.
- **Route sharing.** `engine.py` imports `route` as a module and calls
  `route.departure_direction`, `route.eligible_boarders` and
  `route.next_heading` by attribute; it defines no function computing a
  departure, boarding or heading (AST-checked), and `project` calls the
  same three names. The policy-module half of
  `route_primitives_single_implementation` runs in cut 4.

## 7. Realisation choices (no rule changed)

1. **Decision-surface values live in `domain.py`, not `engine.py`.** The
   engine constructs them, but cut 4's `policy_cannot_import_trace`
   forbids the policies module from importing the engine, so the
   policies' input types cannot live there. They are scheduler §3's
   values verbatim (`num_elevators` names the count field the design
   calls `elevators`, because `elevators` is the tuple of views).
2. **Impossible double writes fail closed by exception.** A second
   assignment, pickup or dropoff, a wrong-way boarding, an over-capacity
   car or a car leaving the building raises `EngineInvariantViolation`
   rather than producing a `HALTED` event, because the governing documents
   name no halt reason for corruption and the case is unreachable. No
   reason name was invented.
3. **`step()` on a final Run is a no-op** returning the outcome.
4. **The receipt is copied** into the `ASSIGNED` event so a policy cannot
   alter it after the fact.
5. **Every `HALTED` payload records `unserved`**, which §8.3 requires for
   horizon halts; it is the count of requests not completed in committed
   state.
6. **The `LIVENESS_BOUND_EXCEEDED` path is exercised by fault injection**
   (a broken `next_heading` monkeypatched onto `route`), since a correct
   engine cannot reach it; an explicit `max_ticks` equal to the default
   bound is the bound itself and yields the same reason.
7. **The FREE-and-full classification case is pinned at the primitive**,
   because no engine state reaches it (semantics §8.2 Lemma 1).
8. **Deferral counts in the tests are derived by a test-side classifier**
   from observed state and the shared primitives; the authoritative
   derivation from History is reporting's (cut 6, authority row 22).

## 8. Verification

```text
python3 -B -m pytest -q tests/unit/test_engine.py tests/invariants/test_engine_invariants.py
  -> 45 passed in 0.41s
python3 -B -m pytest -q
  -> 64 passed in 1.00s
```

Counts: cut 3, 45 passed, 0 failed, 0 skipped, 0 errors. Full suite (cuts
1 to 3), 64 passed, 0 failed, 0 skipped, 0 errors; cuts 1 and 2 remain
green. No `__pycache__` under `elevator/` or `tests/`. Code identity at this
standing: `56461014a56f477ef3ef09b1c3b438e004a94228fbc0ac62a447dd29515569cb`.

## 9. Delta and applicability

`ΔO = NONE / ΔS = NONE / ΔA = NONE`. OSA `REQUIRED` (the engine writes
governed facts); evidence §5. CPOC `REQUIRED`, `PENDING` until cut 10.

## 10. Worktree

Everything untracked; no HEAD commit; nothing committed (owner direction).

## 11. Standing

```text
CUT 3: IMPLEMENTED / LOCAL VERIFY PASS / CPOC PENDING
```

Next eligible cut: cut 4 (scheduler interface and baselines). Not started.


## 12. Repair after the independent cut-3 audit (2026-11-05)

The independent audit returned `FAIL — CUT 3` with three findings (supplied
by the owner; no audit record is in the repository). Everything else
passed (43 identifiers present, 45/45 and 64/64 green, tick atomicity under
four rollback probes, no-look-ahead closure, observed runtime calls to the
shared primitives, deterministic History across 498 fixtures in separate
processes, no later-cut code). The original sections above are kept as
written.

| Finding | Severity | Disposition |
| --- | --- | --- |
| C3-I-01 committed History externally mutable | HIGH | **Repaired** |
| C3-I-02 detected corruption raises while the Run stays RUNNING | MEDIUM | **STOPPED: missing governing contract** (§12.2) |
| C3-I-03 structural test does not prove primitive use | MEDIUM | **Repaired** |

### 12.1 C3-I-01: immutability at the representation boundary

- `elevator/domain.py`: new `freeze(value)` deep-freezes a canonical
  payload (mappings to read-only `MappingProxyType` over fresh dicts with
  sorted string keys, lists and tuples to tuples, int/str/bool/None/Enum
  unchanged; anything else `TypeError`). `SimulationEvent.__post_init__`
  freezes `receipt` and `halt`; `TickEntry` coerces `boarded`/`alighted` to
  tuples; `TickRecord` coerces `entries`; `SimulationHistory` coerces
  `events`/`tick_records`. Every construction path is covered, so no call
  site needs its own copy.
- `elevator/engine.py`: the receipt's shallow `dict(...)` copy is removed;
  the receipt is frozen at commit, and a receipt that cannot be frozen
  canonically (for example a float) halts `INVALID_PROPOSAL`, an admitted
  reason: such a proposal cannot be committed to canonical History.
- Canonical serialisation is unchanged in bytes for every existing payload
  (all 64 prior tests and the 498-run sweep pass unchanged).

### 12.2 C3-I-02: stopped, pending an owner-named reason

The admitted documents require detected runtime corruption to halt the Run
with a named reason (constitution §4.5 "Terminate or halt ... any step that
detects corruption ... or a named reason"; §14 "Any of the following is
corruption, halts the Run"), but no admitted document names that reason.
The admitted halt vocabulary is exactly `INVALID_PROPOSAL`, `POLICY_ERROR`
(step 2), `LIVENESS_BOUND_EXCEEDED` and `HORIZON_EXCEEDED` (step 7)
(semantics §2, §6, §8.3), and none describes a wrong-way boarding, a second
pickup, an over-capacity car or a car leaving the building. Mapping
corruption to one of them would misreport it; minting a new name is a
semantic change. Per the owner's instruction, the work stops here.

Concrete failing scenario (reproduced outside the suite): a 3-floor
building; `a` rides 0 to 1 in ticks 0 and 1; `b` (1 to 0) is revealed at
tick 2 with the idle car at floor 1. `route.eligible_boarders` is patched
for tick 2 only to board `b` with departure `UP`. The engine raises
`EngineInvariantViolation: passenger 1 boarding the wrong way`; the tick
rolls back (History byte-identical to after tick 1), but `outcome` is
`None` and, after the primitive is restored, `step()` resumes the Run.

Proposed delta for the owner (`ΔS`, no `ΔO` or `ΔA`): name one halt reason
for runtime corruption detected by the engine's own checks, for example
`INVARIANT_VIOLATION`, recorded like the other halts (`HALTED` event with
tick, step, reason, the passenger or elevator concerned and `unserved`),
the failing tick discarded and the Run final. It would be added to
semantics §2 (the steps that check) and §6, the halt vocabulary used by
the UI and evaluation (halted runs are already handled generically), and
the testing contract (a test such as `detected_corruption_halts_the_run`).
Until then `EngineInvariantViolation` remains the fail-closed behaviour.
The strict expected-failure test `test_detected_corruption_halts_the_run`
pins the current behaviour and will fail as soon as the halt is
implemented, forcing its marker to be removed with the repair.

### 12.3 C3-I-03: runtime proof of shared primitive use

The engine already calls the primitives as attributes of the `route`
module, so patching the module intercepts the engine's call path. The new
primary proof, `test_engine_invokes_shared_route_primitives_at_runtime`,
patches each primitive in turn with a spy that returns a distinctive result
and checks the engine's observable output follows it: `next_heading`
returning `DOWN` for an idle car with a stop above makes TickRecord 0's
heading `DOWN`; `departure_direction` returning `UP` leaves a down-bound
passenger at an idle car unboarded; `eligible_boarders` returning no
boarders leaves the passenger waiting. The guard test
`test_runtime_proof_detects_an_engine_that_bypasses_the_primitives` builds
a variant engine that binds its own copies of the three functions at import
(and still simulates correctly) and asserts the proof reports all three as
not used. The AST check in `test_route_primitives_single_implementation` is
kept as the secondary structural guard.

### 12.4 New tests (`tests/unit/test_engine_repairs.py`)

| Test | Finding |
| --- | --- |
| `test_history_survives_mutation_of_the_source_receipt` | C3-I-01 (source receipt, nested list and dict mutated after commit) |
| `test_committed_payloads_cannot_be_mutated_through_history` | C3-I-01 (receipt, nested receipt, event tuple, TickRecord tuples, frozen fields) |
| `test_history_survives_mutation_of_a_halt_source_payload` | C3-I-01 (halt source dict and engine halt payload) |
| `test_history_serialisation_deterministic_after_freezing` | C3-I-01 (equality, bytes, key-order independence, unfreezable receipt refused) |
| `test_engine_invokes_shared_route_primitives_at_runtime` | C3-I-03 (primary proof) |
| `test_runtime_proof_detects_an_engine_that_bypasses_the_primitives` | C3-I-03 (the proof fails a bypassing variant) |
| `test_detected_corruption_halts_the_run` (strict xfail) | C3-I-02 (open; pins current behaviour) |

### 12.5 Verification

```text
python3 -B -m pytest -q tests/unit/test_engine_repairs.py
  -> 6 passed, 1 xfailed
python3 -B -m pytest -q tests/unit/test_engine.py tests/unit/test_engine_repairs.py tests/invariants/test_engine_invariants.py
  -> 51 passed, 1 xfailed
python3 -B -m pytest -q
  -> 70 passed, 1 xfailed
```

0 failed, 0 skipped, 0 errors in every run; the one expected failure is the
open C3-I-02. Cuts 1 and 2 remain green. No `__pycache__`. Admitted
governing and plan digests unchanged. Code identity:
`91257ac9b8e98f1b98482ddede72ab54c8292f06530446aaa05eecd581d985da`.

### 12.6 Delta and standing

C3-I-01 and C3-I-03 implement existing rules (constitution §2, §7, N18 and
semantics §4.3): `ΔO = NONE / ΔS = NONE / ΔA = NONE`. C3-I-02 requires a
`ΔS` the owner has not decided, so no delta is asserted for it and it is
not repaired.

```text
CUT 3: IMPLEMENTED / C3-I-01 AND C3-I-03 REPAIRED / C3-I-02 STOPPED PENDING OWNER DECISION /
       INDEPENDENT RE-AUDIT PENDING / CPOC PENDING
```

Cut 4 is not eligible until C3-I-02 is decided and repaired and the
independent re-audit passes.


## 13. C3-I-02 repair under owner decision 008 (2026-11-05)

The owner decided the missing contract
([decision 008](../decisions/owner_decision_008_invariant_violation_halt.md)):
the canonical halt reason `INVARIANT_VIOLATION`, with the violated
invariant in a diagnostic. Revision 7.2 changes three files (semantics §2
and §6, the testing contract's new row `detected_corruption_halts_the_run`,
the plan's cut-3 test list); the other seven governing files are
byte-identical to revision 7.1. The §12.2 stop is resolved; §12 is kept as
written.

### 13.1 Code (`elevator/engine.py`)

- New constant `INVARIANT_VIOLATION`.
- `EngineInvariantViolation` carries the failing step, the invariant
  identifier in constitution numbering (`N2` second assignment, `P6` second
  pickup or dropoff, `N7` wrong-way boarding, `P3` load above `C`, `P2`
  floor outside the building), a detail string, and the passenger and
  elevator where known. It no longer escapes `step()`.
- `step()` converts it to a halt with reason `INVARIANT_VIOLATION` and the
  diagnostic `{invariant, detail, elevator}`, committed by the existing
  `_commit_halt` against committed state. The working tick is dropped, so
  the tick is discarded exactly as for the other halts.
- The step-8 bounds check commits the halt before anything of the tick is
  committed (previously it raised).
- Only invariant halts carry the diagnostic fields; the payload of the four
  other halt reasons is unchanged.

### 13.2 Tests (`tests/unit/test_engine_repairs.py`)

The strict expected-failure marker is removed.
`test_detected_corruption_halts_the_run` (the new contract identifier) now
asserts three corruptions, each injected by patching a shared primitive for
tick 2 only:

| Case | Injection | Step | Invariant |
| --- | --- | --- | --- |
| wrong-way boarding | `eligible_boarders` boards a down-bound passenger with departure `UP` | `BOARD` | `N7` |
| impossible load | `eligible_boarders` boards two passengers into a `C = 1` car | `BOARD` | `P3` |
| leaves the building | `next_heading` sends an idle car at the top floor `UP` | `MOVE` | `P2` |

Each case asserts all of the following:
- the outcome is `HALTED` with reason `INVARIANT_VIOLATION` and the right
  step, passenger and `unserved`;
- the TickRecords and events of ticks 0 and 1 are unchanged;
- exactly one `HALTED` event is appended at the next sequence number, with
  the diagnostic;
- no event from tick 2 survives (in the load case, neither passenger's
  `REVEALED` or `ASSIGNED`);
- passengers, elevators and `t` equal the committed state before tick 2;
- with the primitive restored, `step()` and `run()` return the same outcome
  and change nothing.

`test_invariant_violation_is_the_single_canonical_reason` asserts the
engine's halt vocabulary is exactly the five admitted reasons and that
ordinary halts keep their four-field payload.

### 13.3 Verification

```text
python3 -B -m pytest -q tests/unit/test_engine_repairs.py   -> 8 passed
python3 -B -m pytest -q tests/unit/test_engine.py tests/unit/test_engine_repairs.py tests/invariants/test_engine_invariants.py
                                                            -> 53 passed
python3 -B -m pytest -q                                     -> 72 passed in 1.04s
```

0 failed, 0 skipped, 0 errors, 0 expected failures. Cuts 1 and 2 green. No
`__pycache__`. The §12.2 counterexample, reproduced outside the suite, now
halts `INVARIANT_VIOLATION` at step `BOARD` with diagnostic `N7`, keeps
ticks 0 and 1, and stays final after the primitive is restored. Code
identity: `e655c06e973c0806105b272cf7473b1d9fcab18973bd3950fc2edf02ce1a0e78`.

### 13.4 Delta and standing

C3-I-01 and C3-I-03: `ΔO = NONE / ΔS = NONE / ΔA = NONE`. C3-I-02
implements decision 008's admitted `ΔS` and adds nothing beyond it.

```text
CUT 3: IMPLEMENTED / LOCAL VERIFY PASS / INDEPENDENT RE-AUDIT PENDING / CPOC PENDING
```

The re-audit covers C3-I-01, C3-I-02 and C3-I-03. Cut 4 is not started.


## 14. C3-I-01 residual: Enum payloads (2026-11-05)

The independent re-audit closed C3-I-02 and C3-I-03 and found C3-I-01
still partial (HIGH): committed Simulation History remained externally
mutable through Enum payloads. §12 to §13 are kept as written.

### 14.1 Defect

`freeze()` passed Enum members through unchanged, and canonical
serialisation of an Enum reads its `.value`. A member's identity is stable
but its `.value` may be a mutable object. A receipt containing, for example,
a member whose value is `{"cost": [1, 2]}` was committed by reference, so
mutating that value through the original member or through the member
exposed in History changed the committed canonical bytes with no engine
transition. Reproduced before the fix: the committed History's canonical
bytes changed after `Mode.A.value["cost"].append(99)`.

### 14.2 Fix (`elevator/domain.py`, `elevator/engine.py`)

Enum is now a freeze boundary. `freeze()` no longer keeps an Enum member:
it replaces it with `FrozenEnum(type_name, member_name, value)`, a frozen
dataclass holding the qualified type name, the member name and a
recursively frozen copy of the value, so no reference to the original
mutable value survives and nothing mutable is exposed. `FrozenEnum`
re-freezes its own value on construction and `freeze()` re-freezes a
`FrozenEnum`, so a caller-built instance around a mutable value is covered
too. Serialisation uses the existing canonical dataclass path (sorted keys,
mapping values sorted), so equivalent payloads serialise identically.
Unsupported Enum values (floats, sets, self-referential structures) are
refused rather than kept: `freeze` raises `TypeError` (or `RecursionError`
for a cycle) and the engine's existing guard converts either into
`INVALID_PROPOSAL` (an admitted reason) before the proposal is committed.
Enums are not rejected wholesale. Domain Enums that are dataclass fields
(`Heading`, event kinds) are not freeze payloads and are unchanged.

### 14.3 Tests (`tests/unit/test_history_enum_freeze.py`)

| Test | Covers |
| --- | --- |
| `test_enum_with_dict_value_mutation_leaves_history_unchanged` | dict-valued Enum receipt; original dict mutated (value, nested list, new key); History bytes unchanged |
| `test_enum_with_nested_list_value_mutation_leaves_history_unchanged` | nested list and dict inside lists |
| `test_committed_enum_payload_exposes_nothing_mutable` | exposed `FrozenEnum` is not an Enum; frozen fields; nested mapping and sequence immutable; caller-built `FrozenEnum` re-frozen |
| `test_enum_canonical_serialisation_deterministic_and_equivalent` | repeated bytes identical; equal payloads equal; key order irrelevant; different members differ; freeze idempotent |
| `test_ordinary_scalar_enum_keeps_identity_and_value` | scalar Enum keeps type, name and value deterministically |
| `test_unsupported_enum_values_fail_closed` | float, frozenset and cyclic values refused and halt `INVALID_PROPOSAL` |
| `test_existing_receipt_freeze_still_holds` | regression of the earlier receipt freeze |

The earlier `tests/unit/test_engine_repairs.py` tests pass unchanged.

### 14.4 Verification

```text
python3 -B -m pytest -q tests/unit/test_history_enum_freeze.py tests/unit/test_engine_repairs.py   -> 15 passed
python3 -B -m pytest -q  (cut-3 files, four)                                                      -> 60 passed
python3 -B -m pytest -q                                                                           -> 79 passed in 1.05s
```

0 failed, 0 skipped, 0 errors. Cuts 1 and 2 green. No `__pycache__`.
Governing and plan digests unchanged from record 008. The original
reproduction now leaves the History unchanged and refuses nested mutation
of the exposed value. Code identity: `c837da8bc3183317b8e5db8fd47a3b14b27229e744b175c707c6fdfed03ec7aa`.

### 14.5 Delta and standing

This implements the existing immutable-History contract:
`ΔO = NONE / ΔS = NONE / ΔA = NONE`.

```text
CUT 3: IMPLEMENTED / LOCAL VERIFY PASS / INDEPENDENT RE-AUDIT PENDING / CPOC PENDING
```

Awaiting the independent confirmation that C3-I-01 is closed. Cut 4 is
not started.


## 15. C3-I-01 residual: FrozenEnum metadata (2026-11-05)

The second independent re-audit returned `FAIL — C3-I-01`, narrowed to one
HIGH defect. §12 to §14 are kept as written; C3-I-02 and C3-I-03 were not
reopened.

### 15.1 Defect

`FrozenEnum` froze its `value` but kept `type_name` and `member_name` as
whatever the caller passed, because the `str` annotations were never
enforced at runtime. Reproduced exactly: `names = ["Mode"]`,
`FrozenEnum(type_name=names, member_name="A", value=1)` committed in an
event's receipt; `names.append("changed")` then changed the canonical History
bytes, and the exposed metadata could be mutated the same way.

### 15.2 Constructor invariant (`elevator/domain.py`)

- `FrozenEnum.__post_init__` now enforces `type(type_name) is str` and
  `type(member_name) is str`, raising `TypeError` otherwise. Nothing is
  stringified or coerced, so a list, dict, custom object, bytes, `None`, a
  number or a `str` subclass is refused. The invariant holds however the
  instance is made: `freeze(EnumMember)`, direct construction,
  `dataclasses.replace`, nesting in mappings or sequences, ordinary receipts
  and HALTED diagnostics. `freeze()` rebuilds a `FrozenEnum` through the
  constructor, so a malformed instance forced past the frozen dataclass with
  `object.__setattr__` is refused when committed.
- `.value` is still frozen recursively, as before.
- The same hole existed for scalar subclasses passing through `freeze()`
  (a `str` or `int` subclass is retained by reference and can carry
  mutable state). `freeze()` now returns exact built-in objects for
  `bool`, `int` and `str` values and for mapping keys (`_exact_str`,
  `int.__int__`), and the Enum path builds its metadata through
  `_exact_str`. This is the same existing immutability contract, applied to
  the neighbouring case rather than left for another audit.
- The engine needs no change: a malformed payload raises `TypeError` in
  `freeze()` and the existing guard halts `INVALID_PROPOSAL` before the
  tick is committed.

### 15.3 Tests (added to `tests/unit/test_history_enum_freeze.py`)

| Test | Covers |
| --- | --- |
| `test_frozen_enum_type_name_must_be_an_exact_str` | list, dict, custom object, tuple, int, `None`, bytes, `str` subclass refused |
| `test_frozen_enum_member_name_must_be_an_exact_str` | the same set for `member_name` |
| `test_codex_reproduction_is_refused_and_cannot_change_bytes` | the audit's exact case |
| `test_scalar_metadata_stays_stable_after_commit` | caller string rebinding cannot affect committed bytes; exact `str` types |
| `test_direct_construction_cannot_bypass_validation_through_freeze` | forced-malformed instance refused by `freeze` and by `SimulationEvent`; `dataclasses.replace` re-validates |
| `test_nested_frozen_enum_in_payload_stays_immutable` | nested in dict and list; source and exposed mutation attempts |
| `test_mutation_through_exposed_history_cannot_change_bytes` | every field of an exposed committed `FrozenEnum` |
| `test_ordinary_enum_conversion_keeps_qualified_names` | `module.qualname` and member name, exact `str` |
| `test_halted_payload_with_frozen_enum_is_immutable` | HALTED diagnostic containing a `FrozenEnum` |
| `test_malformed_frozen_enum_payload_fails_closed_without_partial_commit` | engine halts `INVALID_PROPOSAL` at tick 0; no REVEALED, ASSIGNED or TickRecord survives; Run final |
| `test_scalar_subclasses_are_frozen_to_exact_builtins` | `str` and `int` subclasses (values and keys) become exact built-ins |

### 15.4 Verification

```text
python3 -B -m pytest -q tests/unit/test_history_enum_freeze.py                      -> 18 passed
python3 -B -m pytest -q  (history-immutability files: freeze + engine_repairs)      -> 26 passed
python3 -B -m pytest -q  (cut-3 files, four)                                        -> 71 passed
python3 -B -m pytest -q                                                             -> 90 passed in 1.07s
```

0 failed, 0 skipped, 0 errors. Cuts 1 and 2 green. No `__pycache__`.
The audit's exact reproduction is now refused at construction
(`FrozenEnum.type_name must be a str, not list`). Governing and plan
digests unchanged from record 008. Code identity: `2510b04f75a8d28769196d4a51da5a39c801433d28ca7e2a5b4b1041edd04dd6`.

### 15.5 Delta and standing

This enforces the existing immutable-History contract:
`ΔO = NONE / ΔS = NONE / ΔA = NONE`.

```text
CUT 3: IMPLEMENTED / LOCAL VERIFY PASS / INDEPENDENT RE-AUDIT PENDING / CPOC PENDING
```

Awaiting independent confirmation that C3-I-01 is closed. Cut 4 is not
started.
