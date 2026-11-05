# Cut 7 Implementation Record: Scenario Generator

Status: **IMPLEMENTED / LOCAL VERIFY PASS. 2026-11-05.** Evidence record for plan cut 7 under the admitted plan against the admitted design baseline revision 7.2 ([decision 006](../decisions/owner_decision_006_revision_7_1_admission.md) as amended by [decision 008](../decisions/owner_decision_008_invariant_violation_halt.md)). Cut 8 was not started. Nothing is certified.

## 1. Baseline

- Governing design revision 7.2, digests re-verified unchanged before and
  after this cut: the seven unchanged files at record 006's digests;
  `docs/simulation_semantics.md`
  `821cb89dbbd49ac0c44080f0eddc817ae2f8fece211d5a43f37f8b355d8fbd9d`;
  `docs/testing_contract.md`
  `b0e78b99a824a0642f14adb45f9ac44e114fc40533ceae72259757b102d96001`.
- Plan: `26f6920ee56c9ef17e053db7ad1f6ed5d2f15e5606258d60069648790d64c24e`
  (record 008), unchanged.
- Starting standing: cuts 1, 2, 4, 5, 6 `IMPLEMENTED / LOCAL VERIFY PASS`; cut
  3 `IMPLEMENTED / LOCAL VERIFY PASS / CPOC PENDING`; 160 tests passing.

## 2. Scope checklist (admitted cut-7 row)

| Item | Plan text | Realised |
| --- | --- | --- |
| Governing contracts | evaluation §6 (primitive, domains, patterns, cross-parameter precondition, refusals, trace identity) | yes |
| Authority affected | Scenario definitions (row 30); seed (row 31) | the `Scenario` value and the generator; the generated Trace is DERIVED; generator state is EPHEMERAL inside one call; no seed exists inside a Run |
| Expected files | `elevator/scenarios.py` | yes |
| Tests | `splitmix_reference_vector`; `generate_is_pure` with the committed expected Traces; `generate_refuses_invalid_parameters`; `seed_domain_refused`; `sparse_cross_parameter_refused` (generator half); validity of every generated Trace including the emitted-time guard | all (§5) |
| Failure behaviour | invalid parameters refuse with the parameter name | `ScenarioRefusal` (reason `INVALID_SCENARIO_PARAMETERS`) with `.parameters` naming them |
| Evidence | pytest counts | §7 |
| CPOC | NOT APPLICABLE | NOT APPLICABLE: pure, nothing persists |
| Delta | NONE | NONE |

## 3. Files

| File | Change |
| --- | --- |
| `elevator/scenarios.py` | created |
| `tests/reproducibility/test_scenarios.py` | created: 7 tests |
| `tests/invariants/test_scenario_validity.py` | created: 6 tests |
| `tests/fixtures/scenarios/splitmix_vectors.json` | created: the first 16 outputs for seeds 0 and 2^64-1 |
| `tests/fixtures/scenarios/expected_traces_seed7.json` | created: one expected Trace per pattern for seed 7 |
| `tests/fixtures/scenarios/oracle.c` | created: the independent oracle that produced the two fixtures above (§6) |

No governing document, the plan, or any other source file changed.

## 4. The generator

**API.** `Scenario(pattern, parameters, seed)` (immutable) and `generate(scenario,
num_floors, num_elevators, capacity) -> Trace`; helpers `resolve_parameters(scenario,
F)` (effective parameters with defaults) and `provenance(scenario, F)`
(`{pattern, parameters, seed}`, authority row 31); `SplitMix64(seed)` with
`next()` and `draw(k)`; `PATTERNS`. The signature has no policy: one Trace serves
every policy. `generate` imports only `elevator.domain` and the standard library;
it does not import the interpreter's `random` module, a clock, `hashlib` or `os`.

**Seed and RNG contract (§6.1).** SplitMix64 on unsigned 64-bit arithmetic, one
`SplitMix64` instance per `generate` call (state is the instance's only field):
`state += 0x9E3779B97F4A7C15`; two xor-shift-multiply rounds with `0xBF58476D1CE4E5B9`
and `0x94D049BB133111EB`; `draw(k) = ((next() >> 11) * k) >> 53`. A seed must be an
integer with `0 <= seed < 2^64`; anything else (including `2^64`, a negative, a
bool, a float or a string) is refused, never reduced, so two seeds never name one
state. `draw(1)` still consumes one `next()`.

**Patterns (§6.3), implemented as specified and no others.** Draw order per
request is time, origin, destination, with the pattern's stated exceptions;
a destination equal to its origin is redrawn, each redraw one `draw(F)`.

| Pattern | Parameters (defaults) | Rule |
| --- | --- | --- |
| `uniform` | `num_requests`, `horizon` | `time = draw(h+1)`, `origin = draw(F)`, `dest` redrawn |
| `up_peak` | `num_requests`, `horizon` | `time`; `draw(5) < 4` (fixed 4/5): lobby `origin = 0, dest = 1 + draw(F-1)`, else uniform floors |
| `down_peak` | as `up_peak` | mirror: lobby `dest = 0, origin = 1 + draw(F-1)` |
| `bursty` | `num_requests`, `horizon`, `k = 3`, `w = 3` | `k` centres drawn first; per request `j = draw(k)`, `offset = draw(w)`, `time = clamp(c_j + offset - w//2, 0, h)`; uniform floors |
| `concentrated_origin` | `num_requests`, `horizon`, `m = 2` | `m`-member origin set built first by repeated `draw(F)`; `time`, `origin = set[draw(m)]`, `dest` redrawn |
| `concentrated_destination` | as above | mirror |
| `capacity_stress` | `num_requests` (`> N*C`), `origin = 0` | `time = 0` with no draw; `dest` redrawn |
| `sparse` | `num_requests`, `g = 2(F-1)`, `j = 0` | `time = i*g + draw(j+1)`; uniform floors; `horizon` not used |
| `adversarial` | `num_requests` | no draws: `time = i`, alternating `0 -> F-1` and `F-1 -> 0` |

**Canonical ordering and ids.** Requests are generated in index order; the
`source_id` is `"g" + str(i)`; rows go through the shared input boundary
`normalize_requests`, which sorts stably by `(time, i)` and assigns
`passenger_id` as the sorted position. The Trace hash is therefore the standard
`[time, source_id, origin, dest]` hash. No dictionary or set iteration order
influences a result (the origin and destination sets are insertion-ordered lists).

**Refusals** (`ScenarioRefusal`, all naming the parameter): any parameter outside
its domain (`num_requests 0..100000`, `horizon 0..10^6`, `k 1..1000`, `w 1..10^6`,
`1 <= m <= F`, `0 <= origin < F`, `1 <= g <= 10^6`, `0 <= j < g`); an unknown
parameter for the pattern (including every parameter a pattern does not name,
and `p_lobby` at all); `num_requests <= N*C` for `capacity_stress`; the seed
domain; the sparse cross-parameter precondition `(num_requests - 1)*g + j <= 10^9`,
refused naming `num_requests, g, j` before any draw; times are never clipped and the
count is never reduced. The emitted-time guard (`time <= 10^9` on every row) is
asserted and never fires on an accepted scenario. A building outside the
configuration domain refuses `INVALID_CONFIGURATION`.

**Edge cases.** Every pattern works in a 2-floor building (lobby patterns
`1 + draw(1)`, `m <= 2`, adversarial `0 <-> 1`); `num_requests = 0` yields an
empty Trace for every pattern except `capacity_stress`, which needs more than `N*C`.
The admitted set has no inter-floor-above-lobby family, so no admitted pattern is
impossible in a small building.

## 5. Tests

`tests/reproducibility/test_scenarios.py` (7): `splitmix_reference_vector` (committed
vectors for seeds 0 and 2^64-1, plus the widely published seed-0 outputs as an
anchor outside this repository, the `draw` formula, `draw(1)` consuming a
`next()`); `seed_domain_refused`; `generate_is_pure` (twice, and the committed
expected Trace per pattern for seed 7); identical hashes in fresh processes under
three hash-randomization settings; no ambient randomness (the global `random`
state is untouched and irrelevant; no `random`, clock or hash-ordered path in the
module); `generate_refuses_invalid_parameters` (every parameter at each edge and
one past it, `m = F` accepted and `F + 1` refused, `k = 1000`, `w`, `g`, `j`,
`horizon`, `num_requests`, `origin`; `N*C` boundary; every unknown and un-named
parameter; `p_lobby`; missing and mistyped parameters; unknown pattern; building
domain); `sparse_cross_parameter_refused` (`1002` refused naming
`num_requests, g, j` with the primitive disabled, `1001` accepted with last time
exactly `10^9`, the `n = 100000` boundary at `g = 10000` and `10001`).

`tests/invariants/test_scenario_validity.py` (6): a sweep of 540 Traces (9 patterns,
6 building sizes from 2 to 200 floors, 2 parameter sets, 5 seeds including `0` and
`2^64-1`) checking exact counts, unique `g`-ids, canonical `(time, index)` order,
valid endpoints, time bounds and every pattern's own rule (lobby rows, at most `m`
distinct origins or destinations, capacity stress at one time and one origin,
sparse spacing and jitter bounds, the adversarial alternation); the 2-floor
building and empty scenarios; large same-tick groups (a 40-request burst on one
timestamp, a 30-request capacity-stress burst) and sparse gaps run through the real
engine under all three policies, all completing within the liveness bound with a
TickRecord for every tick; one Trace serving every policy unchanged (no policy in the
signature, Trace bytes identical before and after, regeneration equal); Scenario
immutability against caller mutation and `provenance` with effective defaults;
structural no-leakage: the generator imports `domain` only, nothing in the engine,
policies, route, reporting, domain or API imports it, no field of any value a
policy can see or any History record names a scenario, and a Run's History and all
eight reporting files contain no pattern name, seed or provenance. No test compares
policy quality.

## 6. Independent evidence for the committed Traces

The specification requires that two implementations produce the same Trace, and
the plan requires committed expected Traces. Expected output produced by the code
under test would prove nothing, so `tests/fixtures/scenarios/oracle.c` implements
§6 independently, in C with native `uint64_t` arithmetic, written from the
specification text and sharing no code with `scenarios.py`. It generated
`splitmix_vectors.json` and `expected_traces_seed7.json`. Its seed-0 outputs equal
the widely published SplitMix64 values, and its adversarial output matches the hand
derivation. Evidence, all run once during this cut and not part of the test suite:

- the Python generator equals the oracle on **7,000** randomly parameterized
  scenarios (4,000, then 3,000 on a fresh stream): all nine patterns, buildings of 2
  to 200 floors, seeds including `0`, `2^64-1` and `2^63`, horizons up to 10^6,
  bursts with up to 12 centres, sparse with `g` up to 10^5;
- five deliberate mutations of the generator (the draw shift, the lobby share, the
  `h+1` horizon draw, the burst centring, the sparse jitter draw) were each detected
  by the committed expected Traces, and only for the patterns affected.

The oracle is not run by the suite (that would add a compiler dependency or a
skipped test). To re-derive the fixtures: `cc -O2 -o oracle oracle.c`, then
`./oracle vector SEED` and `./oracle gen PATTERN F N C SEED N H K W M ORIGIN G J`.

## 7. Verification

```text
python3 -B -m pytest -q tests/reproducibility/test_scenarios.py tests/invariants/test_scenario_validity.py
  -> 13 passed in 2.43s
python3 -B -m pytest -q
  -> 173 passed in 12.55s
```

Counts: 13 new tests; full suite (cuts 1 to 7) 173 passed, 0 failed, 0 skipped, 0
errors, 0 expected failures. Cuts 1 to 6 remain green. No `__pycache__`. Code
identity: `bdd62c2752e9eaa6ce3db71266b5d0e0f0a66a8433ed3488e85c436cbde372b0`.

## 8. Realisation choices (no rule changed)

1. **Required parameters.** The pattern table gives `num_requests` and `horizon`
   no default. A missing one is refused naming it.
2. **Strict types.** Parameters and the seed must be integers; a bool, float, string
   or `None` is refused, never coerced (the text says "integer parameter").
3. **Refusal order.** Pattern; unknown parameters in sorted order; the seed; then each
   parameter in the table's order; the building-dependent rules in `generate`
   after the configuration domain. A scenario with two faults reports the first.
4. **`ScenarioRefusal`** subclasses the domain `Refusal` and adds `parameters`, the
   names the refusal is about.
5. **`Scenario` lives in `scenarios`.** Authority row 30 gives the Scenario to the
   harness (cut 8), which will import it. No scenario identifier or digest is
   introduced: none is admitted; provenance is the label of §6.4.
6. **`g`'s default depends on F**, so it is resolved by `resolve_parameters` for a
   given building, and `provenance` records the effective value.
7. **Redraw cap.** The spec's redraw rule has probability-one termination, so the
   implementation caps consecutive redraws at 100,000 and raises `RuntimeError`,
   turning a would-be infinite loop into an error. It is a never-fires bound.
8. **Trace construction reuses `normalize_requests`**, so generated rows are
   validated and ordered by exactly the rules every other input obeys.
9. **The oracle is a fixture tool**, not a dependency of the simulator or the
   test run (§6).

## 9. Delta and applicability

`ΔO = NONE / ΔS = NONE / ΔA = NONE`. OSA `REQUIRED` for the Scenario and its
derived Trace (rows 30 and 31; evidence §5). CPOC `NOT APPLICABLE` (a pure
function of its arguments; nothing persists).

## 10. Worktree

Everything untracked; no HEAD commit; nothing committed.

## 11. Standing

```text
CUT 7: IMPLEMENTED / LOCAL VERIFY PASS
```

Next eligible cut: cut 8 (evaluation harness, public API and operations). Not started.
