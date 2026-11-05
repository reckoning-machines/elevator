# Cut 2 Implementation Record: Route Policy

Status: **IMPLEMENTED / LOCAL VERIFY PASS. 2026-11-05.** Evidence record for plan cut 2 under the admitted plan ([decision 007](../decisions/owner_decision_007_implementation_plan_admission.md)) against the admitted design baseline revision 7.1 ([decision 006](../decisions/owner_decision_006_revision_7_1_admission.md)). Cut 3 was not started. Nothing is certified.

## 1. Baseline

- Governing design revision 7.1: the nine digests of record 006, re-verified
  unchanged before and after this cut.
- Plan: `6254fffaea4c48582ae20733a5995ca6511a24f9d057de0e84efabfb82138d84`, unchanged.
- Starting standing: cut 1 `IMPLEMENTED / LOCAL VERIFY PASS`
  ([cut_01_domain_input_boundary.md](cut_01_domain_input_boundary.md)).

## 2. Scope checklist (admitted cut-2 row)

| Item | Plan text | Realised |
| --- | --- | --- |
| Governing contracts | semantics §4, §4.1, §4.2, §4.3; scheduler §5 | yes |
| Authority affected | none (pure functions; the single implementation) | yes: no state, no I/O, no clock, no randomness, no module-level mutable state |
| Expected files | `elevator/route.py` | yes; plus `tests/unit/test_route.py` |
| Tests | `departure_direction_cases`; `eligible_boarders_cases`; `idle_tie_prefers_up`, `reversal_only_when_nothing_ahead`; `project` written here, `projection_exactness` in cut 5 | yes (§4) |
| CPOC | NOT APPLICABLE (pure) | NOT APPLICABLE: pure functions; no persistence, continuation or history read |
| Delta | NONE | NONE |

## 3. Primitives implemented (`elevator/route.py`)

- `Departure` (`UP`, `DOWN`, `FREE`): the intra-tick departure value; `FREE`
  has no heading conversion, so it cannot be stored as a heading.
- `next_heading(floor, heading, stops) -> Heading`: LOOK exactly as semantics
  §4, including the `UP` tie rule; stops canonicalised (sorted, deduplicated).
- `departure_direction(floor, heading, stops) -> Departure`: semantics §4.1;
  excludes the current floor from the stops (`S_other`).
- `eligible_boarders(waiting, departure, load, capacity) -> BoardingResult`:
  semantics §4.2, direction first, then capacity; the first boarder of a
  `FREE` car sets the departure; waiting passengers sorted by `passenger_id`;
  returns boarders, resulting departure, direction-deferred and
  capacity-deferred, which never overlap.
- `project(elevator_view, extra_waiting=(), *, capacity, now) -> Projection`:
  scheduler §5; iterates engine steps 3, 4, 5, 8 by calling the three
  primitives above (no second implementation); returns `pickup_time`,
  `dropoff_time`, `first_compatible_arrival`, `deferred`, `wrong_way_passes`,
  `max_load`, `end_time`. Value types `RouteState`, `OnboardPassenger`,
  `WaitingPassenger` describe the minimal elevator view it reads.

## 4. Tests (`tests/unit/test_route.py`)

| Contract identifier | Function |
| --- | --- |
| `idle_tie_prefers_up` | `test_idle_tie_prefers_up` |
| `reversal_only_when_nothing_ahead` | `test_reversal_only_when_nothing_ahead` |
| `departure_direction_cases` | `test_departure_direction_cases` |
| `eligible_boarders_cases` | `test_eligible_boarders_cases` (FREE first-boarder; direction before capacity; wrong-way + full is direction only; compatible + full is capacity; full FREE car stays FREE; room counted with this tick's boarders; post-alighting load admits) |

Two supporting tests, not contract identifiers:
`test_project_matches_worked_examples` checks `project` by hand against W-B,
W-C, W-F and W-G (the contract's `projection_exactness` against the engine
remains cut 5's); `test_route_module_depends_only_on_domain_and_stdlib`
asserts by AST that `route` imports only `elevator.domain` and the standard
library modules it needs, and nothing that performs I/O. The cut-3 contract
test `route_primitives_single_implementation` (engine and policy side)
remains cut 3's; this cut supplies the one implementation it checks.

## 5. Verification

```text
python3 -B -m pytest -v tests/unit/test_route.py   -> 6 passed in 0.04s
python3 -B -m pytest -q                            -> 19 passed in 0.61s
```

Counts: cut 2, 6 passed, 0 failed, 0 skipped, 0 errors. Full suite (cuts 1
and 2), 19 passed, 0 failed, 0 skipped, 0 errors; cut 1 remains green. No
`__pycache__` under `elevator/` or `tests/`. Code identity at this standing:
`bcb85a141c6487100e692d7492d9d404848d3cd8e2eb9aab79e46cbcb6a58eed`.

## 6. Realisation choices (no rule changed)

- `next_heading` and `departure_direction` accept any iterable of stops and
  canonicalise it (sorted set) before deciding, so set iteration order
  cannot affect a result.
- `departure_direction` excludes the current floor itself, so callers may
  pass all committed stops; semantics §4.1 defines `S_other` that way.
- `eligible_boarders` returns the two deferral classes explicitly, for the
  projection's observation phase and later reporting.
- `project` stops at the tick in which no committed stop remains (after
  step 5, as the engine's step 7 would for this car) and carries a guard
  derived from the liveness bound that can fire only on an invariant
  violation.

## 7. Delta

`ΔO = NONE / ΔS = NONE / ΔA = NONE`. No governing ambiguity was found.

## 8. Worktree

Everything untracked; no HEAD commit; nothing committed (owner direction).

## 9. Standing

```text
CUT 2: IMPLEMENTED / LOCAL VERIFY PASS
```

Next eligible cut: cut 3 (simulation engine). Not started.
