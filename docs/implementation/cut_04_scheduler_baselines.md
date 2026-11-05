# Cut 4 Implementation Record: Scheduler Interface and Baselines

Status: **IMPLEMENTED / LOCAL VERIFY PASS. 2026-11-05.** Evidence record for plan cut 4 under the admitted plan against the admitted design baseline revision 7.2 ([decision 006](../decisions/owner_decision_006_revision_7_1_admission.md) as amended by [decision 008](../decisions/owner_decision_008_invariant_violation_halt.md)). Cut 5 was not started. Nothing is certified.

## 1. Baseline

- Governing design revision 7.2. Digests re-verified unchanged before and
  after this cut: the seven unchanged files at record 006's digests,
  `docs/simulation_semantics.md`
  `821cb89dbbd49ac0c44080f0eddc817ae2f8fece211d5a43f37f8b355d8fbd9d`,
  `docs/testing_contract.md`
  `b0e78b99a824a0642f14adb45f9ac44e114fc40533ceae72259757b102d96001`.
- Plan: `26f6920ee56c9ef17e053db7ad1f6ed5d2f15e5606258d60069648790d64c24e`
  (record 008), unchanged.
- Starting standing: cuts 1 and 2 `IMPLEMENTED / LOCAL VERIFY PASS`; cut 3
  `IMPLEMENTED / LOCAL VERIFY PASS / CPOC PENDING`, independent re-audit
  reported PASS by the owner (no audit record is in the repository, so
  none is cited); 90 tests passing.

## 2. Scope checklist (admitted cut-4 row)

| Item | Plan text | Realised |
| --- | --- | --- |
| Governing contracts | scheduler §2, §3, §4 | yes |
| Authority affected | none; policies are pure | yes: no state, I/O, clock or randomness; no module-level state |
| Expected files | `elevator/policies.py` (interface, `round_robin`, `nearest_car`) | yes (§3) |
| Tests | `round_robin_is_id_mod_n`; `deterministic_tie_nearest_car`; `policy_cannot_import_trace`; `future_mutation_does_not_change_prefix`, `future_mutation_both_active`, `sentinel_future_request` for both baselines; the §2 engine-local invariants under both baselines | all (§4) |
| Failure behaviour | invalid proposal halts (engine) | engine-owned, pinned in cut 3, unchanged |
| CPOC | NOT APPLICABLE (pure) | NOT APPLICABLE: pure stateless functions; nothing persists |
| Delta | NONE | NONE |

## 3. Files

| File | Change |
| --- | --- |
| `elevator/policies.py` | created: `RoundRobin`, `NearestCar` |
| `tests/unit/test_policies.py` | created: 10 tests |
| `tests/invariants/test_no_look_ahead.py` | created: 9 tests |
| `tests/invariants/test_engine_invariants.py` | changed: the sweep now also runs under `RoundRobin` and `NearestCar` (four policies per case) |
| `tests/unit/test_engine.py` | changed: the cut-3 placeholder in `route_primitives_single_implementation` that asserted `policies.py` did not exist is replaced by the policy-module half the contract describes (§6, choice 3) |

No governing document, the plan, `engine.py`, `route.py` or `domain.py` changed.

## 4. Interface and rules

**Interface.** The one the engine already calls, defined by the engine's
`SchedulerPolicy` protocol: `assign(view: SchedulerView, request:
RevealedRequest) -> Proposal`. The value types (`SchedulerView`,
`ElevatorView`, `RevealedRequest`, `Proposal`) were added to `domain.py` in
cut 3. `policies.py` defines no protocol of its own and no registry
(architecture lists a registry as deliberately absent); the two policies are
frozen dataclasses with no fields and a class-level `name`. Configuration's
`policy` name selects nothing here: constructing the policy object is the
caller's act, and the public API that does so is cut 8's.

**`round_robin`**: `elevator_id = request.passenger_id % view.num_elevators`;
`receipt = None`. No pointer, counter or cursor; ignores position, heading,
load and committed work.

**`nearest_car`**: `min over elevators of (abs(floor - origin), elevator id)`;
`receipt = {"distance": d}` with `d` an `int`. Ties go to the lowest id
by construction of the key, so the listing order of the view's elevators
cannot decide a tie. Ignores load, direction, committed stops, capacity and
route projection.

## 5. Tests

`tests/unit/test_policies.py`:

| Test | Covers |
| --- | --- |
| `test_round_robin_is_id_mod_n` | contract `round_robin_is_id_mod_n`: 7-passenger Trace, `N = 3`, through the real engine; direct calls for `N` in 1, 2, 5; ignores a busy, moving view |
| `test_round_robin_is_stateless` | forward, reversed and shuffled call orders agree; reused equals fresh instance; no fields, no attributes, frozen |
| `test_deterministic_tie_nearest_car` | contract `deterministic_tie_nearest_car`: two, three and four cars equidistant, same-floor ties, reversed listing order |
| `test_nearest_car_is_the_naive_baseline` | nearest wins though full, heading away or busy; a farther idle car is never preferred; receipt shape; repeat calls identical; no state |
| `test_policies_do_not_mutate_the_view` | view unchanged after `assign`; view and its parts frozen |
| `test_baselines_with_simultaneous_requests_and_engine_commit` | second call sees the first's committed assignment; baselines still decide from their defined fields; engine commits the proposals |
| `test_receipts_survive_history_freezing_and_are_canonical` | `ASSIGNED` carries the receipt, frozen; two runs serialise identically |
| `test_policy_cannot_import_trace` | contract `policy_cannot_import_trace`: AST import graph (only `elevator.domain`; no engine, route, API, I/O or randomness imports), no `Trace`, engine or history name or attribute, and `import elevator.policies` in a fresh interpreter does not load the engine |
| `test_policies_hold_no_module_level_state_and_define_no_route_mechanics` | module body is imports, classes and docstring only; class bodies hold constants only; no function named for departure, boarding or heading |
| `test_baseline_runs_are_identical_across_processes` | two fresh interpreters and an in-process run give the same History hash under both baselines |

`tests/invariants/test_no_look_ahead.py` (each of the first four is
parametrised over both baselines):

| Test | Covers |
| --- | --- |
| `test_future_mutation_does_not_change_prefix` | 40 random buildings and traces; for `t*` in 0, 3, 8, 14 four variants (all later requests removed, arbitrary later requests, a burst, a single sentinel); every Proposal by `(t, passenger_id)` and the decision and motion prefix through `end` identical: 640 comparisons per baseline |
| `test_future_mutation_both_active` | 120 pairs per baseline where each trace has a request after `t*`; `end = t*` asserted; the prefix includes every tick through `t*` with idle ticks |
| `test_sentinel_future_request` | 3 fixtures, `t*` in 0 to 7: one extra request at `t* + 1`; prefix and Proposals identical |
| `test_policy_sees_only_revealed_passengers` | every view built has `request_time <= t` and the closed field set |
| `test_witness_detects_a_policy_that_peeks_at_the_future` | negative control: a policy reading the full trace through a global produces a different prefix, so the comparison can fail |

Compared surface exactly as testing contract §3: `REVEALED`, `ASSIGNED`
(with receipt), `BOARDED`, `ALIGHTED` events and TickRecords with tick `<=
end`, `end = min(t*, final_T, final_T')`; `COMPLETED` and `HALTED` events
and anything after `end` excluded. Event sequence numbers are not compared
(they shift when a later `COMPLETED` is excluded); every other field is.

Engine-local invariants under both baselines: the existing 20 tests now run
over 249 cases times four policies (the two cut-3 stubs and the two
baselines): 996 runs, 3908 passengers, all complete within the proved bound.

## 6. Realisation choices (no rule changed)

1. **The interface stays the engine's protocol.** Architecture says the
   engine depends on "the policy interface" and policies on `domain` and
   `route`; the policies module may not import the engine, so it implements
   the protocol structurally. No second protocol was defined.
2. **No registry, no factory.** Architecture §6 lists "a dict of three
   names" as deliberately absent; the policy object is constructed by its
   caller (cut 8's API will do so from `Configuration.policy`).
3. **Cut-3 placeholder replaced.** `test_route_primitives_single_implementation`
   contained `assert not os.path.exists(policies.py)` with a comment that
   its policy half would run in cut 4. That half now exists and is
   asserted (no route-mechanics function in policies; only `domain` imported).
4. **Class-level `name` is a plain string constant** (a dataclass with no
   fields, so equality is by class), kept for the evaluation and reporting
   cuts that print policy names.
5. **`nearest_car` ties by the key `(distance, id)`**, not by list order,
   so the rule holds for any ordering of `view.elevators`.
6. **Baselines import neither `route` nor anything else.** Neither needs
   route mechanics.

## 7. Verification

```text
python3 -B -m pytest -q tests/unit/test_policies.py tests/invariants/test_no_look_ahead.py
  -> 19 passed in 2.20s
python3 -B -m pytest -q  (cut-4 files + engine invariants + test_engine.py)
  -> 64 passed
python3 -B -m pytest -q
  -> 109 passed in 3.55s
```

Counts: cut 4 new tests 19 passed; full suite (cuts 1 to 4) 109 passed, 0
failed, 0 skipped, 0 errors, 0 expected failures. Cuts 1 to 3 remain green.
No `__pycache__`. Negative control confirmed by hand and kept as a test. One
interim full-suite failure (the cut-3 placeholder in §6 choice 3) was
resolved by completing the contract's policy half, not by weakening any
assertion. Code identity: `f4ade7779edeee20c0835c1ab624be77659f4dc28e0b032384deebea5c2cb2dd`.

## 8. Dependency evidence

`policies` imports only `elevator.domain` (AST-asserted); no engine, route,
API, reporting, checkpoint, operations, harness, CLI or web import; no
`os`, `sys`, `io`, `json`, `random`, `time`, `datetime`, `pathlib` or
`secrets`; no `Trace`, engine, history or request-list name or attribute;
importing it does not import the engine. The engine imports no policy
module (cut-3 structural test unchanged).

## 9. Delta and applicability

`ΔO = NONE / ΔS = NONE / ΔA = NONE`. OSA `REQUIRED` for the decision
surface (a policy proposes, the engine commits): evidence §5. CPOC `NOT
APPLICABLE` (pure and stateless; there is no policy state to survive process
death).

## 10. Worktree

Everything untracked; no HEAD commit; nothing committed.

## 11. Standing

```text
CUT 4: IMPLEMENTED / LOCAL VERIFY PASS
```

Next eligible cut: cut 5 (cost-based scheduler). Not started.
