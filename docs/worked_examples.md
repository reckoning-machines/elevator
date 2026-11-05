# Worked Examples

Status: **ILLUSTRATION. DRAFT. Revision 7.1 (W-D resume sequence corrected), 2026-11-05. Governs nothing; where an example and a governing rule disagree, the example is wrong and is repaired. Each example is the hand-computed expected output of a test named in [testing_contract.md](testing_contract.md), and the audit checklist cites them.**

Conventions: floors `0..F-1`; `floor(t)` is the beginning-of-tick position;
a TickRecord row is `(t, elevator, floor, heading, load, boarded, alighted)`;
the tick steps are those of [simulation_semantics.md](simulation_semantics.md) §2;
`D` is the departure direction of §4.1 (`FREE` until a boarder sets it).
Passengers are written `p0, p1, ...` by `passenger_id`; in every example
the supplied `source_id` is the same string (`"p0"`, `"p1"`, ...), so the
two ids coincide. Events listed are Simulation Events; Operational Records
appear only in W-D and are marked as such.

## W-A. One elevator, one passenger, upward

Configuration `F = 4, N = 1, C = 2`, elevator 0 at floor 0. Trace: `p0`
at `t = 0`, origin 0, destination 3. Policy: any (one elevator).

| t | Steps | TickRecord |
| --- | --- | --- |
| 0 | reveal `p0`; assign `p0 -> E0` (`assigned_at = 0`); alight none; heading `NONE` so `D = FREE`; board `p0` (`pickup = 0`, load 1, `D := UP`); heading `UP`; record; not terminal; move to 1 | `(0, E0, 0, UP, 1, [p0], [])` |
| 1 | no stops at 1; stop ahead (3): `D = UP`; heading `UP`; move to 2 | `(1, E0, 1, UP, 1, [], [])` |
| 2 | heading `UP`; move to 3 | `(2, E0, 2, UP, 1, [], [])` |
| 3 | alight `p0` (`dropoff = 3`); no stops: `D = FREE`, nobody boards; heading `next_heading(3, UP, {}) = NONE`; record; terminal; `COMPLETED`, final tick 3 | `(3, E0, 3, NONE, 0, [], [p0])` |

`p0`: wait 0, travel 3 = distance, total 3. `elevator_positions.csv`:
`t,elevator_0` then `0,0`, `1,1`, `2,2`, `3,3`. Simulation Events, with
sequence numbers: `0 REVEALED p0 @0`, `1 ASSIGNED p0 E0 @0`, `2 BOARDED p0
E0 floor 0 @0`, `3 ALIGHTED p0 E0 floor 3 @3`, `4 COMPLETED @3`. The
summary has `mean wait = 0`, so the tail-ratio observation is suppressed
(`tail_ratio: null`). Test: `one_elevator_one_passenger_up`.

## W-B. Capacity deferral, reversal, Tier 2 fallback

Configuration `F = 5, N = 1, C = 1`, elevator 0 at floor 0. Trace: `p0` at
`t = 0`, 0 to 4 (up); `p1` at `t = 0`, 2 to 4 (up).

Assignment at `t = 0`, in id order. `round_robin`: `0 mod 1 = 0` for both.
`cost_based`: `p0` has one candidate, Tier 1. `p1`: projection of `E0`
with `p1` added: `E0` reaches floor 2 at `t = 2` continuing `UP` (compatible)
with load 1 = `C`, so `p1` is capacity-deferred (`first_compatible_arrival
= 2`, `pickup = 6`); `deferred_c` is true, so Tier 1 is empty; Tier 2
chooses the only candidate; receipt `tier = 2`, `newly_deferred_others`
empty. With default `age_scale = 4`, `p1`'s cost is `4 * 6 = 24`, marginal
0.

| t | Steps | TickRecord |
| --- | --- | --- |
| 0 | reveal `p0, p1`; assign both to `E0`; `D = FREE`; board `p0` (`D := UP`, load 1 = `C`); `p1` is not at floor 0; heading `UP`; move to 1 | `(0, E0, 0, UP, 1, [p0], [])` |
| 1 | stop ahead (4): `D = UP`; nothing at 1; move to 2 | `(1, E0, 1, UP, 1, [], [])` |
| 2 | at `p1`'s origin; alight none; `S_other = {4}` above so `D = UP`, compatible with `p1`; load 1 = `C`: **capacity deferral**; heading `UP`; move to 3 | `(2, E0, 2, UP, 1, [], [])` |
| 3 | heading `UP`; move to 4 | `(3, E0, 3, UP, 1, [], [])` |
| 4 | alight `p0` (`dropoff = 4`); `S_other = {2}`, nothing above: `D = FREE`; nobody at 4; heading `next_heading(4, UP, {2}) = DOWN` (reversal, same tick); move to 3 | `(4, E0, 4, DOWN, 0, [], [p0])` |
| 5 | stop ahead below (2): `D = DOWN`; move to 2 | `(5, E0, 3, DOWN, 0, [], [])` |
| 6 | `S_other = {}`: `D = FREE`; board `p1` (`pickup = 6`, `D := UP`); heading `UP`; move to 3 | `(6, E0, 2, UP, 1, [p1], [])` |
| 7 | heading `UP`; move to 4 | `(7, E0, 3, UP, 1, [], [])` |
| 8 | alight `p1` (`dropoff = 8`); `D = FREE`; heading `NONE`; terminal; `COMPLETED`, final tick 8 | `(8, E0, 4, NONE, 0, [], [p1])` |

`p0`: wait 0, travel 4, total 4. `p1`: wait 6, travel 2, total 8,
`capacity_deferrals = 1` (the TickRecord at `t = 2` shows `E0` at floor 2
heading `UP` with `load = C` and `p1` not boarded), `wrong_way_passes = 0`.
Liveness bound: `0 + 2 * 2 * 4 = 16 >= 8`. Tests:
`deferred_boarding_then_return`, `capacity_exactly_full`,
`cost_based_tier2_fallback`, `reversal_only_when_nothing_ahead`.

## W-C. Cost-based versus Nearest Car on one request

Configuration `F = 6, N = 2, C = 2`; defaults `w_wait = w_marginal = 1,
w_tail = 3, tail_threshold = 2(F-1) = 10, age_scale = F-1 = 5`. State at
`t = 4`: `E0` at floor 2, heading `UP`, onboard `p1` (destination 5,
picked up at 3, requested at 3); `E1` at floor 0, idle. New request `p3`
at `t = 4`: origin 1, destination 4 (up).

Nearest Car: `|2 - 1| = 1` and `|0 - 1| = 1`: tie, lowest id, **`E0`**,
the car heading away.

Cost-based, candidate `E0`:

- `base`: stops `{5}`; floors 3, 4, 5 at `t = 5, 6, 7`; `p1` alights at 7.
- `with p3`: stops `{1, 5}`; `D = UP` at 2, 3, 4 (stop ahead); `p1`
  alights at 7; at 5 `S_other = {1}`, nothing above: `D = FREE`, nobody
  there, heading `DOWN`; floors 4, 3, 2, 1 at `t = 8..11`; at 1
  `S_other = {}`: `FREE`, `p3` boards (`D := UP`) at 11; floors 2, 3, 4 at
  `t = 12..14`; `p3` alights at 14.
- `wait_c = 11 - 4 = 7`; `marginal = (5 + 1) * (7 - 7) = 0`; not deferred;
  Tier 1.
- `cost = 5 * (7 + 3 * max(0, 7 - 10)) + 0 = 35`.

Candidate `E1`:

- `with p3`: stops `{1}`; heading `NONE` so `next_heading(0, NONE, {1}) =
  UP`; floor 1 at `t = 5`; `S_other = {}`: `FREE`, `p3` boards (`D := UP`)
  at 5; floors 2, 3, 4 at `t = 6..8`; alights at 8.
- `wait_c = 1`; `marginal = 0`; Tier 1.
- `cost = 5 * 1 = 5`.

Chosen: **`E1`**, cost 5, `tier = 1`, receipt `projected_pickup = 5,
projected_dropoff = 8`. If no later assignment touches `E1`, the realized
times are 5 and 8 exactly (constitution P9). Tests:
`deterministic_tie_nearest_car`, `cost_based_tier1_before_tier2`,
`projection_exactness`.

## W-D. Process death between ticks and lawful continuation

Take W-B under `round_robin`, in a fresh Store `S` (`store_id = s1`), as
Execution `e_A`, with `--checkpoint-at 3`: the Continuation Document is
written after tick 2's step 9, before tick 3's step 1.

`S/e_A/run.json` (abridged):

```text
schema_version: 1; store_id: s1; execution_id: e_A; run_id, code_identity, configuration_hash, trace_hash
write_sequence: 1
configuration, trace (both p0 and p1)
standing: RUNNING; final: null
snapshot:
  t: 3
  elevators: [ {id: 0, floor: 3, heading: UP} ]
  passengers: [ {passenger_id: 0, source_id: "p0", standing: ONBOARD, assigned_elevator: 0,
                 assigned_at: 0, pickup_time: 0, dropoff_time: null},
                {passenger_id: 1, source_id: "p1", standing: WAITING, assigned_elevator: 0,
                 assigned_at: 0, pickup_time: null, dropoff_time: null} ]
  snapshot_hash: H_s
simulation_history:
  tick_records: t = 0, 1, 2 (as in W-B)
  events: 0 REVEALED p0 @0; 1 REVEALED p1 @0; 2 ASSIGNED p0 E0 @0; 3 ASSIGNED p1 E0 @0; 4 BOARDED p0 E0 floor 0 @0
  history_hash: H_h
```

`S/e_A/operational.jsonl` after A's write (a separate file; the document
contains no receipt and no hash of itself):

```text
{execution_id: e_A, op_seq: 1, kind: EXECUTION_STARTED, pid: A, code_identity, argv, checkpoint_at: 3}
{execution_id: e_A, op_seq: 2, kind: CHECKPOINT_WRITTEN, tick: 3, write_sequence: 1, document_sha256: d_A, snapshot_hash: H_s, history_hash: H_h}
```

where `d_A` is the SHA-256 of the bytes at `S/e_A/run.json` after the
rename. Because A was started with `--checkpoint-at 3`, its Execution was
Store-bound at creation, so `EXECUTION_STARTED` went to the file directly;
a live session checkpointed for the first time at tick 3 would instead
flush its in-memory buffer (`op_seq` 1 onward) to the same file at that
moment (cpoc §2.2a). No `CHECKPOINT_WRITTEN` or `RESUMED` appears among the events:
those are Operational Records, and the events end with the last event of
tick 2 (the `BOARDED` at tick 0 is the last passenger transition before
tick 3; ticks 1 and 2 produced TickRecords only).

Process A pauses holding this state; it is killed with `SIGKILL`. Process
B is started with `--store S --resume e_A --witness-instrumentation`.
Its `EXECUTION_STARTED` is appended to the same Execution log as `op_seq`
3 (pid B, retaining `execution_id = e_A`), before the load receipts:

| Verification (cpoc §5) | Result |
| --- | --- |
| 1, 2 Store (schema, `s1`) and document (schema-complete) | found; parses |
| 3, 4 schema, code identity | equal |
| 5 `store_id = s1`; `execution_id = e_A` equals the path | equal |
| 6 hashes, `run_id` | equal |
| 7 standing `RUNNING`; snapshot present, final null | ok |
| 8 inputs valid | yes |
| 9 snapshot: `snapshot_hash = H_s`; ids `{0}`; floor 3 in range; `UP` in domain; passengers exactly `{p : request_time < 3} = {p0, p1}`; assignment ids in range; standings versus fields (`p0` `ONBOARD` with pickup 0 and no dropoff; `p1` `WAITING` with assignment and no pickup); load 1 `<= C = 1` | consistent |
| 10 history, by the isolated verifier: `history_hash = H_h`; TickRecords exactly `0..2`; events 0..4 in sequence; replay from floor 0 heading `NONE`: tick 0 `FREE`, boards `p0` (`UP`), load 1, floor 0; tick 1 continues `UP`, load 1, floor 1; tick 2 `p1` is compatible (`UP`) but the car is full: a capacity deferral, nobody boards, load 1, floor 2; every recorded `floor`, `heading`, `load`, `boarded`, `alighted` equals the replay | consistent |
| 11 snapshot versus history: `floor = 2 + delta(UP) = 3`; `heading = UP = tick_records[2].heading`; `p0` has `ASSIGNED` and `BOARDED` and no `ALIGHTED`; `p1` has `ASSIGNED` only; the verifier's boundary state equals the snapshot | consistent; the verifier is used through this step and discarded before state construction |

B calls `parse_snapshot(document)` to obtain the typed `Snapshot`, then
`construct_state(snapshot)`, hashes the constructed state (`= H_s`),
appends `LOAD_ADMITTED(document_sha256 = d_A, H_s, H_h,
constructed_state_hash = H_s, s1, e_A, pid B, code identity)` (`op_seq`
4 in the Execution's file) and `RESUMED(t=3)` (`op_seq` 5), and executes ticks 3 to 8,
producing TickRecords identical to W-B's rows for `t = 3..8` and
Simulation Events `5 ALIGHTED p0 @4; 6 BOARDED p1 @6; 7 ALIGHTED p1 @8; 8
COMPLETED @8`, with sequence numbers continuing from the prefix. At the
Run outcome B performs the finality write under admission (the document at
the path has `write_sequence 1`, B's token): `standing: COMPLETED`,
`final: {final_tick: 8}`, `snapshot` removed, complete Simulation History,
`write_sequence: 2`; then `FINALITY_WRITTEN` with the new document's
SHA-256. Every file of the Reproducible Output Surface in
`out/<run_id>/e_A/` equals the uninterrupted reference R's in
`out/<run_id>/e_R/`; `execution_metadata.json` differs in `execution_id`,
pid and timestamps. B's `DIAGNOSTIC` records for ticks 3..8 have `op_seq`
6..11; `FINALITY_WRITTEN` follows as 12 and `EXECUTION_ENDED` as 13.
A's two-record prefix above was not instrumented; B's explicit flag makes
its six diagnostic records present without changing Simulation History.
R's Simulation History is exactly the prefix plus B's continuation,
sequence numbers included. Nothing was recomputed from History to
establish B's state: `p1`'s `WAITING` standing came from the typed
snapshot (verification 11 only confirmed it against the absence of a
`BOARDED`, in a verifier that was then discarded).

Negative variants, each constructed from a byte copy of the document above
and written back to `S/e_A/run.json` (the Operational Log is left as A
wrote it; the loader never reads it):

- **Mutated heading** (cpoc §6 row 17): set `elevators[0].heading` to
  `DOWN`, leaving `floor = 3`; **recompute `snapshot_hash`**; leave
  `simulation_history` and every identity untouched. Verifications 1 to
  10 pass (`DOWN` is in the domain; the recomputed hash matches; the
  History is internally lawful and unchanged). Verification 11 fails:
  snapshot heading `DOWN` differs from `tick_records[2].heading = UP`:
  `STATE_HISTORY_MISMATCH`. Without recomputing `snapshot_hash` the same
  mutation fails at 9 with `STATE_INCONSISTENT` (row 19), which pins the
  order. A loader that rebuilt state from the History would have continued
  with `UP` and never noticed the tampering; that is why row 17 is
  required.
- **Resurrection** (row 24): `p1` has `request_time = 0` and distance 2,
  so `0 + 2 < 3` and it qualifies; set `p1` to `COMPLETED` with
  `pickup_time = 0`, `dropoff_time = 2` (internally consistent: times
  ordered, both `< t = 3`, `dropoff - pickup = 2 = |4 - 2|`); recompute
  `snapshot_hash`. Verifications 1 to 10 pass. Verification 11 fails: `p1`
  has no `BOARDED` and no `ALIGHTED` event: `STATE_HISTORY_MISMATCH`.
- **Stale writer** (row 9): start from this document (`write_sequence =
  1`, A's token 1). A performs an admitted checkpoint write in-process at
  tick 4 (reads token 1, writes `RUNNING` with `write_sequence = 2`, holds
  token 2). A simulated old holder of token 1 then calls the write
  function against the `RUNNING` document: `STALE_WRITER`; the document
  still carries `write_sequence = 2`. Write after final (row 10) is a
  separate fixture: after the finality write (`write_sequence = 2`), a
  checkpoint write with the current token 2 refuses `WRITE_AFTER_FINAL`.
- **Forged recorded load** (row 25): set `tick_records[1][0].load` to 2
  (`C + 1`); recompute `history_hash`; leave the snapshot and events
  untouched. Verifications 1 to 9 pass. Verification 10 fails: the
  verifier's load at tick 1 is 1: `HISTORY_INCONSISTENT`.
- **Missing field** (row 1): delete `elevators[0].heading`; recompute
  nothing. Verification 2 fails: `MALFORMED` (the schema requires it).
- **Stale after finality** (rows 3 to 5, 8): after B's finality write,
  `load(S, e_A)` refuses `EXECUTION_FINAL`, whatever output directory is
  named; the pre-finality copy placed in a new Store `S2` at `S2/e_A/`
  refuses `STORE_MISMATCH`; placed in `S` under a fresh `e_X/` it refuses
  `EXECUTION_MISMATCH`.
- **Independent Execution** (row 7): the same inputs executed in `S` as
  `e_C` with `--checkpoint-at 3` produce a document with a different
  `execution_id` and identical snapshot, History prefix and `run_id`;
  `load(S, e_C)` is admitted regardless of `e_A`'s finality; `e_C`'s
  Simulation History equals `e_A`'s.

## W-E. Invalid proposal and halt

Configuration `F = 4, N = 1, C = 2`. Trace: `p0` at `t = 0`, 0 to 3. A stub
policy returns `1`.

Tick 0: reveal `p0`; step 2: proposal `1` is not in `0..0`: `HALTED`,
reason `INVALID_PROPOSAL`, tick 0, step 2, passenger 0. No `ASSIGNED` is
written. Tick 0's `REVEALED` event is discarded with the tick. Simulation
History: the single event `0 HALTED(t=0, step=ASSIGN,
reason=INVALID_PROPOSAL, passenger=0)`. No TickRecord exists. The Run is
final; if a Continuation Document had been written before tick 0, the
finality write sets its standing to `HALTED` and a later `load` refuses
`EXECUTION_FINAL`. `summary.json` is the halted form of evaluation §4.1
(`standing, final_tick, halt_reason, n, completed, unserved`); the output
`run_identity.json` reports the same outcome. Because no TickRecord exists, `elevator_positions.csv` is a header only,
and every history request on a UI session for this run returns
`NO_HISTORY` ([ui_design.md](ui_design.md) §2.2): `final_tick = 0` is the
tick of the failure, not an available record. Tests:
`policy_invalid_proposal_halts`, `halt_discards_partial_tick`,
`history_halted_range`, the `EXECUTION_FINAL` negative witness.

## W-F. Direction deferral

As W-B but `p1` is 2 to 1 (down). Assignment as before (`cost_based`:
`p1`'s projection shows a wrong-way pass at `t = 2` and no capacity
deferral at a compatible arrival, so Tier 1).

| t | Steps | TickRecord |
| --- | --- | --- |
| 0 | as W-B | `(0, E0, 0, UP, 1, [p0], [])` |
| 1 | as W-B | `(1, E0, 1, UP, 1, [], [])` |
| 2 | at `p1`'s origin; `S_other = {4}` above so `D = UP`; `p1` is down-bound: **direction deferral**; the car is also full, but under §4.2 direction decides first and capacity is not evaluated, so no capacity deferral is recorded; move to 3 | `(2, E0, 2, UP, 1, [], [])` |
| 3 | move to 4 | `(3, E0, 3, UP, 1, [], [])` |
| 4 | alight `p0`; `D = FREE`; heading `DOWN`; move to 3 | `(4, E0, 4, DOWN, 0, [], [p0])` |
| 5 | `D = DOWN` (stop ahead at 2); move to 2 | `(5, E0, 3, DOWN, 0, [], [])` |
| 6 | `S_other = {}`: `FREE`; board `p1` (`D := DOWN`, `pickup = 6`); heading `DOWN`; move to 1 | `(6, E0, 2, DOWN, 1, [p1], [])` |
| 7 | alight `p1` (`dropoff = 7`); heading `NONE`; terminal; final tick 7 | `(7, E0, 1, NONE, 0, [], [p1])` |

`p1`: wait 6, travel 1 = distance, total 7, `wrong_way_passes = 1`,
`capacity_deferrals = 0` (direction first; capacity not evaluated for a
wrong-way passenger). Liveness bound `16 >= 7`. Tests:
`direction_deferral_then_return`, `deferral_classification_direction_first`.

## W-G. Two passengers wanting away from each other (the oscillation case)

Configuration `F = 7, N = 1, C = 2`, elevator 0 at floor 4. Trace: `p0` at
`t = 0`, 5 to 6 (up); `p1` at `t = 0`, 3 to 0 (down). Both assigned to `E0`.

Under the rejected rule "at a floor with nothing ahead, depart toward the
remaining stops, then board only compatible passengers", the car at 5
would turn toward 3 and skip `p0`, then at 3 turn toward 5 and skip `p1`,
forever. Under §4.1 the reversal point is `FREE`:

| t | Steps | TickRecord |
| --- | --- | --- |
| 0 | reveal, assign both; heading `NONE`: `D = FREE`; nobody at 4; heading `next_heading(4, NONE, {5, 3})`: distances 1 and 1, tie: `UP`; move to 5 | `(0, E0, 4, UP, 0, [], [])` |
| 1 | at 5: `S_other = {3}`, nothing above: `D = FREE`; board `p0` (`D := UP`, `pickup = 1`); heading `UP`; move to 6 | `(1, E0, 5, UP, 1, [p0], [])` |
| 2 | alight `p0` (`dropoff = 2`); `S_other = {3}`: `FREE`, nobody; heading `DOWN`; move to 5 | `(2, E0, 6, DOWN, 0, [], [p0])` |
| 3 | `D = DOWN`; move to 4 | `(3, E0, 5, DOWN, 0, [], [])` |
| 4 | `D = DOWN`; move to 3 | `(4, E0, 4, DOWN, 0, [], [])` |
| 5 | at 3: `S_other = {}`: `FREE`; board `p1` (`D := DOWN`, `pickup = 5`); move to 2 | `(5, E0, 3, DOWN, 1, [p1], [])` |
| 6 | move to 1 | `(6, E0, 2, DOWN, 1, [], [])` |
| 7 | move to 0 | `(7, E0, 1, DOWN, 1, [], [])` |
| 8 | alight `p1` (`dropoff = 8`); heading `NONE`; terminal; final tick 8 | `(8, E0, 0, NONE, 0, [], [p1])` |

`p0`: wait 1, travel 1. `p1`: wait 5, travel 3. Both complete at tick 8;
liveness bound `0 + 2 * 2 * 6 = 24 >= 8`. Test: `reversal_point_is_free`.
