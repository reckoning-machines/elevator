# Cut 5 Implementation Record: Cost-Based Scheduler

Status: **IMPLEMENTED / LOCAL VERIFY PASS. 2026-11-05.** Evidence record for plan cut 5 under the admitted plan against the admitted design baseline revision 7.2 ([decision 006](../decisions/owner_decision_006_revision_7_1_admission.md) as amended by [decision 008](../decisions/owner_decision_008_invariant_violation_halt.md)). Cut 6 was not started. Nothing is certified.

## 1. Baseline

- Governing design revision 7.2, digests re-verified unchanged before and
  after this cut: the seven unchanged files at record 006's digests;
  `docs/simulation_semantics.md`
  `821cb89dbbd49ac0c44080f0eddc817ae2f8fece211d5a43f37f8b355d8fbd9d`;
  `docs/testing_contract.md`
  `b0e78b99a824a0642f14adb45f9ac44e114fc40533ceae72259757b102d96001`.
- Plan: `26f6920ee56c9ef17e053db7ad1f6ed5d2f15e5606258d60069648790d64c24e`
  (record 008), unchanged.
- Starting standing: cuts 1 and 2 `IMPLEMENTED / LOCAL VERIFY PASS`; cut 3
  `IMPLEMENTED / LOCAL VERIFY PASS / CPOC PENDING`; cut 4 `IMPLEMENTED /
  LOCAL VERIFY PASS`; 109 tests passing.

## 2. Scope checklist (admitted cut-5 row)

| Item | Plan text | Realised |
| --- | --- | --- |
| Governing contracts | scheduler §1, §5, §6, §7, §8 | yes |
| Authority affected | none; the receipt is attached by the engine to `ASSIGNED` (row 21) | yes: pure, stateless policy; the engine commits and freezes the receipt |
| Expected files | `elevator/policies.py` (`cost_based`) | yes |
| Tests | `projection_exactness`; `projection_observation_phase`; `cost_based_tier1_before_tier2`; `cost_based_tier2_fallback`; `tier1_is_incremental`; `tier1_receipt_not_a_guarantee`; `cost_based_marginal_equals_projection_delta`; `cost_exact_integer`; `deterministic_tie_cost_based`; the three no-look-ahead tests for `cost_based`; `every_passenger_completes` and `liveness_bound_holds` for all three policies; `projection_exactness_property` | all (§5) |
| Evidence | pytest counts; the projection-exactness run across all fixtures | §7 |
| CPOC | NOT APPLICABLE (pure) | NOT APPLICABLE: no state to survive process death |
| Delta | NONE | NONE |

## 3. Files

| File | Change |
| --- | --- |
| `elevator/policies.py` | `CostBased` added (frozen dataclass of five integer parameters; `for_building`); imports `route` for the shared projection |
| `tests/unit/test_cost_based.py` | created: 15 tests |
| `tests/invariants/test_projection_exactness.py` | created: 4 tests |
| `tests/invariants/test_no_look_ahead.py` | changed: the witnesses now run for all three policies (factories take the number of floors) |
| `tests/invariants/test_engine_invariants.py` | changed: the sweep runs five policies per case, including `cost_based` |
| `tests/unit/test_engine.py`, `tests/unit/test_policies.py` | changed: the structural assertions now permit `route` as a policy dependency and require that the policies module use only `route.project` from it (§6, choice 2) |
| `tests/engine_fixtures.py` | changed: `classify_deferrals` takes `from_tick` |

No governing document, the plan, `engine.py`, `route.py` or `domain.py` changed.

## 4. Policy

### 4.1 Lawful input surface

`assign(view, request)` reads only the `SchedulerView` (time, building, per
elevator floor, heading, onboard and assigned-waiting passengers), the
`RevealedRequest`, and its five immutable integer parameters. It imports
`domain` and `route` only (AST-asserted) and uses nothing from `route`
except `route.project` and its result type. It has no access to the Trace,
the History, a clock, randomness, a demand model, a regime label or any
state across calls; no cache or memoisation exists (each elevator is
projected once without and once with the candidate per call).

### 4.2 Formula (scheduler §6.1 to §6.4, implemented literally)

For each elevator `E` in id order, with `base = route.project(E, (), C, t)`
and `with = route.project(E, (candidate,), C, t)`:

```text
wait_c   = with.pickup_time[c] - t
deferred_c = c in with.deferred
newly_deferred_others = sorted((with.deferred - base.deferred) & committed(E))
marginal = sum over waiting q of (age_scale + (t - request_time(q))) * (with.dropoff[q] - base.dropoff[q])
cost     = age_scale * (w_wait * wait_c + w_tail * max(0, wait_c - tail_threshold)) + w_marginal * marginal
tier     = 1 if (not deferred_c and newly_deferred_others is empty) else 2
chosen   = min over the tier-1 rows if any, else over all rows, of (cost, E)
```

Defaults (`CostBased.for_building(F)`): `w_wait = 1`, `w_marginal = 1`,
`w_tail = 3`, `tail_threshold = 2(F-1)`, `age_scale = F-1`. All integers; no
float appears anywhere; the marginal is signed and never clamped; a negative
cost is lawful. No `w_total` term. Direction deferral is outside the tier
rule: a wrong-way pass is priced in `wait_c` and reported as
`wrong_way_passes_c`.

Receipt (scheduler §6.5): `{policy, tier, chosen, cost, projected_pickup,
projected_dropoff, candidates}`, `candidates` a tuple in elevator-id order of
`{E, tier, cost, wait_c, marginal, deferred_c, newly_deferred_others,
wrong_way_passes_c}`. Only ints, a bool, strings and tuples; the engine
freezes it on commit.

### 4.3 The onboard-age observation (not a gap, recorded for the auditor)

§6.1 sums over every passenger "committed to E" with weight `age_scale +
age(q, t)` and `age(q, t) = t - request_time(q)`, but §3 gives onboard
passengers in the view only `(passenger_id, destination, pickup_time)`;
`request_time` is not in the lawful decision surface. Taken at its word the
two sections disagree. In effect they cannot, because for an onboard
passenger the term is identically zero:

- An onboard passenger travels in the car's heading toward its destination
  until it alights (a car never reverses while a stop lies ahead), so its
  projected dropoff is `t + |destination - floor|` whatever else is
  assigned (constitution P11). Adding a candidate cannot change it, so its
  delta, and its term whatever age is used, is exactly zero.
- Verified, not only argued. In the suite,
  `test_onboard_projected_dropoff_never_depends_on_the_candidate` probes the
  394 elevator states with onboard passengers (421 onboard passengers) met in
  the 977 assignment calls with 3 random candidates each (1263 pairs), and
  `test_cost_based_marginal_equals_projection_delta` checks every onboard
  passenger's delta in every call; all are zero and equal `t + distance`. A
  larger one-off probe outside the suite (1500 random runs, 8,593
  onboard-bearing states, 59,124 pairs) also found 0 nonzero deltas.

So the policy sums only waiting passengers (whose `request_time` is in the
view) and, for onboard passengers, asserts the delta is zero and raises
(engine halt `POLICY_ERROR`) if it ever is not: that would be a violation of
P11 and must not be guessed around. No formula, view field or document
changed. Suggested optional clarification for a later revision, not
required for this cut: state in §6.1 that the sum ranges over waiting
passengers because onboard terms are zero.

## 5. Tests

`tests/unit/test_cost_based.py`:

| Test | Contract identifier / covers |
| --- | --- |
| `test_cost_formula_matches_worked_example_w_c` | W-C by hand: costs 35 and 5, `E1` chosen, pickup 5, dropoff 8 |
| `test_cost_exact_integer` | `cost_exact_integer`: a non-default parameter case by hand (48); every number in every receipt of every fixture and sweep run is a built-in `int` (a bool for `deferred_c`): 1982 candidate rows |
| `test_marginal_can_be_negative_and_so_can_cost` | the audit's case, exact: `F = 8, C = 1`, `5->0`, `5->6` at 0, candidate `6->7` at 4: marginal `-66`, wait 2, cost `-52`, Tier 1. By hand: `p1` is accelerated from dropoff 16 to 6 (`11 * -10 = -110`), `p0` delayed from 10 to 14 (`11 * +4 = +44`), `-110 + 44 = -66`, `7 * 2 - 66 = -52` |
| `test_cost_based_tier1_before_tier2` | `cost_based_tier1_before_tier2`: the Tier-2 car costs 10, the Tier-1 car 15; Tier 1 chosen, `tier = 1` |
| `test_cost_based_tier2_fallback` | `cost_based_tier2_fallback`: W-B through the real engine (`tier = 2`, cost 24, pickup 6, dropoff 8); all cars Tier 2, cheapest (16) chosen, `tier = 2` |
| `test_tier1_is_incremental` | `tier1_is_incremental`: `F = 5, C = 1`, `0->4`, `2->4`, `4->3`: tiers 1, 2, 1; the third has empty `newly_deferred_others`; plus direction deferral without capacity deferral stays Tier 1 (`wrong_way_passes_c = 1`) |
| `test_tier1_receipt_not_a_guarantee` | `tier1_receipt_not_a_guarantee`: a Tier-1 passenger is realised capacity-deferred after a later Tier-2 assignment to the same car; the first receipt still says `tier = 1`; the Passenger has no estimate field |
| `test_cost_based_marginal_equals_projection_delta` | `cost_based_marginal_equals_projection_delta`: for all 977 assignment calls of the fixtures and sweep, every candidate row's `wait_c`, `marginal` and `cost` equal an independent recomputation from `route.project`; onboard terms zero |
| `test_onboard_projected_dropoff_never_depends_on_the_candidate` | §4.3 |
| `test_deterministic_tie_cost_based` | `deterministic_tie_cost_based`: identical cars, mirror-image cars, reversed listing order, three-way tie: lowest id |
| `test_cost_based_is_deterministic_and_stateless` | repeat calls, fresh versus reused, interleaving, frozen parameters, no attribute can be added, view unchanged |
| `test_cost_based_runs_are_identical_across_processes` | two fresh interpreters give one History hash |
| `test_cost_based_parameters_are_validated_and_immutable` | integers 0 to 10^6 only; defaults for a building; unknown parameter refused; a Configuration's `policy_params` build the same policy |
| `test_cost_based_uses_the_shared_projection_at_runtime` | spy on `route.project`: exactly base then with-candidate per elevator; a patched projection changes the decision, so no second projection exists |
| `test_receipt_shape_order_and_freezing_through_the_engine` | §6.5 shape, id order, `chosen` equals the passenger's elevator, frozen in History, identical across runs |

`tests/invariants/test_projection_exactness.py`:

| Test | Contract identifier / covers |
| --- | --- |
| `test_projection_exactness` | `projection_exactness`: 1245 engine runs (249 cases times five policies, `cost_based` included); for every tick and every elevator with no assignment after that tick, `project` at the tick boundary equals the realized pickup times, dropoff times and idle time: 16420 (tick, car) pairs, 0 mismatches |
| `test_projection_observation_phase` | `projection_observation_phase`: `deferred` and `wrong_way_passes` equal the realised capacity deferrals and wrong-way passes counted from the History (W-B: one capacity deferral; W-F: one wrong-way pass) |
| `test_projection_exactness_property` | `projection_exactness_property`: 120 larger seeded cases, random ticks and cars |
| `test_exactness_comparison_detects_a_wrong_projection` | negative control: an off-by-one projection is flagged |

`tests/invariants/test_no_look_ahead.py` now parametrises over all three
policies: `future_mutation_does_not_change_prefix` (640 comparisons per
policy), `future_mutation_both_active` (120 per policy),
`sentinel_future_request`, and the revealed-only view check, with the
negative control kept. `tests/invariants/test_engine_invariants.py` runs all
its invariants, including `every_passenger_completes` and
`liveness_bound_holds`, over 249 cases times five policies: 1245 runs, 4885
passengers, all `COMPLETED` within `T_last + 2P(F-1)`.

Coverage of the 977 `cost_based` assignment calls in the shared fixtures and
sweep: 103 Tier-2 candidate rows (55 chosen), 61 nonzero marginals, 94
candidates with a wrong-way pass, 10 rows with newly deferred others; the
random sweep produced no negative marginal, so the negative case is pinned
by its exact fixture, not by random coverage.

## 6. Realisation choices (no rule changed)

1. **Construction.** `CostBased` is a frozen dataclass of five integers.
   `for_building(F, **overrides)` fills the documented defaults; Cut 8's API
   builds it from a Configuration with `CostBased(**dict(policy_params))`
   (shown by a test). No registry or factory, as for the baselines.
2. **Structural tests widened, not weakened.** Policies may depend on
   `domain` and `route` (architecture §1). The tests now assert exactly that
   import set and that the module touches `route` only through `project` and
   `Projection`, so it cannot compute a departure, boarding or heading.
3. **Onboard passengers** (§4.3): omitted from the sum because their delta is
   provably zero, with a fail-closed assertion instead of an invented age.
4. **`newly_deferred_others`** is a sorted tuple of passenger ids (empty tuple
   when none); `deferred_c` a bool.
5. **No memoisation.** Each elevator is projected once without and once with
   the candidate per call; the cost is `O(N)` projections per assignment. No
   performance claim is made.
6. **Tie-break** applies inside the admissible tier: `(cost, elevator id)`.

## 7. Verification

```text
python3 -B -m pytest -q tests/unit/test_cost_based.py tests/invariants/test_projection_exactness.py
  -> 19 passed in 3.64s
python3 -B -m pytest -q tests/unit/test_cost_based.py tests/invariants/test_projection_exactness.py tests/invariants/test_no_look_ahead.py
  -> 32 passed in 7.56s
python3 -B -m pytest -q
  -> 132 passed in 10.65s
```

Counts: 23 new tests (15 + 4 + four more witness runs from the third
policy); full suite (cuts 1 to 5) 132 passed, 0 failed, 0 skipped, 0 errors,
0 expected failures. Cuts 1 to 4 remain green. No `__pycache__`. Code identity:
`ab156ddb11e85eeaee7cfc44871542c90e3b23e4714a3563bb7586616315337d`.

## 8. Dependency evidence

`policies` imports `elevator.domain` and `elevator.route` only; no engine,
API, reporting, checkpoint, operations, harness, CLI or web import; no
`os`, `sys`, `io`, `json`, `random`, `time`, `datetime`, `pathlib` or
`secrets`; no `Trace`, engine, history or request-list name or attribute;
`import elevator.policies` in a fresh interpreter does not load the engine.
The engine imports no policy module.

## 9. Delta and applicability

`ΔO = NONE / ΔS = NONE / ΔA = NONE`. OSA `REQUIRED` (a policy proposes, the
engine commits; evidence §5). CPOC `NOT APPLICABLE` (pure and stateless).

## 10. Worktree

Everything untracked; no HEAD commit; nothing committed.

## 11. Standing

```text
CUT 5: IMPLEMENTED / LOCAL VERIFY PASS
```

Next eligible cut: cut 6 (reporting and calibration). Not started.
