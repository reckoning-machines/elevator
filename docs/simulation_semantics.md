# Simulation Semantics

Status: **GOVERNING DOCUMENT for discrete-time mechanics. Revision 7.2 (owner decision 008: the `INVARIANT_VIOLATION` halt reason, 2026-11-05). Admission standing is recorded in `docs/decisions/`, not here.**

Jurisdiction: the exact tick procedure, what the position log means, request
visibility, boarding and alighting, direction and reversal, capacity and
deferred boarding, idle behaviour, termination, the liveness bound, and the
resolution of every edge case the take-home left open. Subordinate to
[constitution.md](constitution.md). The scheduler's decision is owned by
[scheduler_design.md](scheduler_design.md); this document only says when it
is invoked and what the engine does with its answer.

## 1. Definitions

- `t`: current simulation time, an integer starting at 0.
- `F`, `N`, `C`: floors `0..F-1`, elevators `0..N-1`, capacity, within the
  domain `2 <= F <= 200`, `1 <= N <= 20`, `1 <= C <= 50`
  ([evaluation_design.md](evaluation_design.md) §2).
- `passenger_id`: the Request's position in the Trace after a stable sort
  by `(request_time, input_index)`; `source_id`: the identifier the input
  supplied for that Request, carried everywhere the passenger is named.
- `floor_E(t)`: the floor elevator `E` occupies at the **start** of tick `t`,
  before any motion in tick `t`. `floor_E(0)` is the configured initial
  floor (default 0 for every elevator).
- `heading_E`: `UP`, `DOWN` or `NONE`. The direction `E` is committed to
  travel. `NONE` means idle.
- `committed stops of E`: the set of floors `{origin(p) : p WAITING,
  assigned to E} ∪ {destination(p) : p ONBOARD E}`. Derived, never stored.
- `stops ahead`: committed stops strictly above `floor_E` when
  `heading = UP`, strictly below when `heading = DOWN`.
- `load_E`: number of passengers `ONBOARD` `E`. Derived.
- `age(p, t) = t - request_time(p)` for a revealed passenger.
- `dir(p)`: `UP` if `destination(p) > origin(p)`, else `DOWN`.
- `departure_E`: the direction `E` leaves its current floor in during
  this tick, as established in step 4: `UP`, `DOWN`, or `FREE` (not yet
  determined by a boarder). An intra-tick ephemeral value (authority row
  16): never stored, never a heading.

## 2. The tick procedure

Tick `t` executes these steps, in this order, exactly once. No step may be
skipped, merged or reordered. Within a step, elevators are processed in
ascending `elevator_id` and passengers in ascending `passenger_id`.

```text
Step 1  REVEAL     Every Request with request_time == t becomes a revealed
                   Passenger (standing: revealed, unassigned; transient).
                   Emit REVEALED(p, t) for each, in passenger_id order.

Step 2  ASSIGN     For each newly revealed passenger p in passenger_id order:
                   build the SchedulerView as of the current state (which
                   includes assignments already committed earlier in this
                   step); call the policy; validate the returned elevator id;
                   write assigned_elevator and assigned_at = t; standing
                   becomes WAITING; emit ASSIGNED(p, E, t, receipt).
                   An invalid proposal or a policy exception HALTS the run.

Step 3  ALIGHT     For each elevator E: every passenger ONBOARD E with
                   destination == floor_E(t) alights: dropoff_time = t,
                   standing COMPLETED, emit ALIGHTED(p, E, floor, t).

Step 4  BOARD      For each elevator E at floor f = floor_E(t):
                   D := departure_direction(f, heading_E, S_other)   (§4.1)
                   (boarders, D) := eligible_boarders(waiting at f assigned
                   to E in ascending passenger_id, D, load_E, C)   (§4.2)
                   Each boarder in order: pickup_time = t, standing ONBOARD,
                   emit BOARDED(p, E, floor, t). A passenger who does not fit
                   remains WAITING (capacity deferral); a passenger whose
                   direction is incompatible remains WAITING (direction
                   deferral). departure_E := D (ephemeral, this tick only).

Step 5  HEAD       For each elevator E: heading_E := departure_E if it is UP
                   or DOWN; otherwise heading_E := next_heading(floor_E,
                   heading_E, committed stops of E)  (§4). This is the
                   motion E will perform during tick t. The three functions
                   named in steps 4 and 5 are the Route Policy; the engine
                   and the projection call the same function objects (§4.3).

Step 6  RECORD     Emit TickRecord(t): for each E, (floor_E(t), heading_E,
                   load_E after step 4, boarded ids at t, alighted ids at t).

Step 7  TERMINATE? If every Request has been revealed (no request_time > t
                   remains) and every passenger is COMPLETED: the run is
                   COMPLETED with final tick t. Stop; do not execute step 8
                   or 9. Else if t + 1 > max_ticks: HALT with the reason
                   of §8.3 (LIVENESS_BOUND_EXCEEDED for the default bound,
                   HORIZON_EXCEEDED for an explicit smaller horizon).
                   Else continue.

Step 8  MOVE       For each elevator E: floor_E := floor_E + 1 if heading UP,
                   floor_E - 1 if DOWN, unchanged if NONE.

Step 9  ADVANCE    t := t + 1.
```

**Detected invariant violation** (owner decision 008). If the engine's own
checks detect, at any step of tick `t`, a violation of an admitted runtime
invariant (a second assignment, pickup or dropoff; a boarding against the
departure direction; a load above `C`; a floor outside `0..F-1`), the Run
is `HALTED` with reason `INVARIANT_VIOLATION`, exactly like the other
halts: the whole of tick `t` is discarded, every earlier tick is kept, one
`HALTED` event is committed with the tick, the failing step, the reason, the
passenger and elevator concerned where known, a diagnostic identifying the
violated invariant, and the unserved count, and the Run is final. There is
one canonical reason for every such violation; the specific invariant is in
the diagnostic, not in the reason. Under a correct implementation this halt
is unreachable.

A Checkpoint may be written only between step 9 of tick `t` and step 1 of
tick `t+1` (or before step 1 of tick 0). See [cpoc_design.md](cpoc_design.md).

### 2.1 Why this order (and the orders rejected)

- **Reveal and assign before alight and board.** A request that appears at
  `t` at the floor where its assigned elevator currently sits boards at `t`
  with `wait_time = 0`. Assigning after boarding would impose a one-tick
  wait for no reason.
- **Alight before board.** Alighting frees room; boarding at the same floor
  in the same tick may use it. This is the only interaction between the two
  steps. The ordering is what makes "elevator becomes full at a stop"
  well-defined.
- **Head after board.** The heading is the departure direction the
  boarders were promised (§5), or, when nobody set one, the LOOK choice
  over the post-boarding committed stops, so a reversal caused by an
  elevator emptying takes effect in the same tick with no time cost.
- **Record before move.** The TickRecord for `t` reports `floor_E(t)`, the
  floor at which the tick's stops were served, and the heading that is about
  to be executed. The alternative (record after move, "end-of-tick position")
  was rejected because it would make the row for `t` report a floor at which
  nothing happened at `t`, and `floor(0)` would no longer be the initial
  position.
- **Terminate before move.** When every passenger is complete, no elevator
  has committed stops, every heading is `NONE`, and a move would be a no-op.
  Stopping before step 8 makes the final TickRecord the tick of the last
  alighting, with every heading `NONE`.

The order "reveal, assign, dropoff, pickup, choose movement, move, record,
advance", suggested as a starting point in the owner's project brief (not
in the take-home itself, which prescribes no tick order), was considered.
Its only difference is record-after-move, rejected above.

## 3. Position semantics and exports

TickRecords are the canonical per-tick record. Two `DERIVED` exports are
produced from them ([evaluation_design.md](evaluation_design.md) §3):

- `elevator_positions.csv`, the source-facing export the take-home asks
  for: one row per timestamp `t` from `0` to the final tick inclusive, with
  one column per elevator holding `floor_E(t)` (beginning-of-tick position);
- `position_log_long.csv`, the analysis export: one row per
  `(t, elevator_id)` with `floor`, `heading` (the motion performed during
  `t`) and `load` (after boarding at `t`).

Both say the same thing about position; the first is the required
deliverable's shape, the second carries heading and load.

Consequences, which the tests pin:

- A passenger who boards at floor `o` at tick `t` alights at `t + |d - o|`:
  the car leaves in the passenger's direction and never reverses while
  the destination lies ahead, so `travel_time = |d - o|` always (§5).
- `floor_E(0)` is the configured initial floor.
- In a `COMPLETED` run the last row's heading is `NONE` for every elevator
  (a `HALTED` run's last row reports whatever headings were in force).
- Neither export contains a tick beyond the final tick, and neither omits
  one.

## 4. Direction and reversal

`next_heading(floor, heading, stops)` is a pure function:

```text
above := {s in stops : s > floor}
below := {s in stops : s < floor}
if above is empty and below is empty:            return NONE
if heading == UP   and above not empty:          return UP
if heading == DOWN and below not empty:          return DOWN
# reversal or start from idle:
if above is empty:                               return DOWN
if below is empty:                               return UP
d_up := min(above) - floor;  d_down := floor - max(below)
if d_up <= d_down:                               return UP
else:                                            return DOWN
```

This is LOOK: continue in the current heading while any committed stop lies
ahead; otherwise turn toward the nearest committed stop, preferring `UP` on a
tie. A stop at the current floor is never "ahead"; it is served in steps 3
and 4, or, if boarding was deferred, it remains committed and will be
reached again because LOOK sweeps to the extreme committed stop and back.

Properties:

- An elevator never reverses while a committed stop lies ahead.
- Reversal costs no time: the new heading is executed in the same tick.
- An idle elevator (`NONE`) becomes `UP` or `DOWN` in the tick in which it
  first has a committed stop elsewhere, or in which a passenger boards it.
- Direction **is** a boarding constraint (§5), through the departure
  direction. "Direction logic" in this project means both the elevator's
  motion discipline and the rule that a passenger enters only a car that
  will leave the floor the passenger's way.

### 4.1 Departure direction

At floor `f` in step 4, before any boarding:

```text
S_other := committed stops of E other than f
if heading == NONE:                                      D := FREE
elif heading == UP   and some s in S_other has s > f:    D := UP
elif heading == DOWN and some s in S_other has s < f:    D := DOWN
else:                                                    D := FREE   # reversal point
```

`FREE` means the car is not committed to leave `f` in either direction:
it was idle, or it has reached the end of its sweep. The first passenger
to board (lowest `passenger_id` among those at `f` who fit) sets `D` to
their direction; later boarders must match it. If nobody boards, step 5
falls back to `next_heading` over whatever committed stops remain.

When `D` was set from the heading (stops ahead), `next_heading` over the
post-boarding stops would return the same value, because boarders only add
stops in that direction. When `D` was set by a boarder from `FREE`,
`next_heading` could differ (an idle car with a nearer stop the other way
would turn toward it), which is why step 5 uses `departure_E` directly:
the car must leave in the direction it promised the passengers it just
took.

Why the reversal point is `FREE` rather than "turn toward the remaining
stops": with the latter rule a car between an up-bound passenger above it
and a down-bound passenger below it turns away from each one on arrival
and oscillates forever ([worked_examples.md](worked_examples.md) W-G).
`FREE` at the reversal point lets the oldest waiting passenger there set
the direction, so every sweep end boards someone when anyone is waiting
there with room.

### 4.2 Eligible boarders

`eligible_boarders(waiting, D, load, C) -> (boarders, D')` is a pure
function. `waiting` is the list of `WAITING` passengers assigned to this
car at this floor in ascending `passenger_id`; `load` is the onboard count
after alighting.

```text
boarders := []; D' := D
for p in waiting (ascending passenger_id):
    d_eff := D' if D' != FREE else dir(p)          # a FREE car would adopt p's direction
    if dir(p) != d_eff:                 continue    # direction deferral (wrong-way pass); capacity not evaluated
    if load + len(boarders) >= C:       continue    # capacity deferral: compatible, would board, no room
    if D' == FREE:                      D' := dir(p)  # the first boarder sets the direction
    boarders.append(p)
return (boarders, D')
```

The classification rule, used everywhere (semantics, projection, reporting,
tests; owner decision proposed as D-19): **direction decides first.** A
passenger whose direction is incompatible with the departure direction is a
direction deferral (a wrong-way pass), and capacity is not evaluated for
them. A capacity deferral is recorded only when the direction is compatible
(or the car is `FREE`, which would adopt the passenger's direction) and the
passenger would otherwise have boarded but the car has no room. A passenger
at a full car departing the other way is therefore a wrong-way pass only.
Mechanical safety is unchanged: load never exceeds `C`. A `FREE` car with
no room boards nobody and stays `FREE`; everyone waiting there is a capacity
deferral.

### 4.3 One implementation

`departure_direction`, `eligible_boarders` and `next_heading` are the Route
Policy. They live in one module. The engine's steps 4 and 5 call them; the
projection `project` ([scheduler_design.md](scheduler_design.md) §5) calls
the same function objects in the same order. No other code may compute a
departure direction, a boarding decision or a heading. The structural test
is [testing_contract.md](testing_contract.md) §1
`route_primitives_single_implementation`; the behavioural test is
constitution P9.

## 5. Boarding, capacity and deferred boarding

- A passenger boards only its assigned elevator, only at its origin floor,
  only when `load < C` at that moment in step 4, only when `dir(p)` is
  compatible with the departure direction `D` (§4.1), oldest
  (`passenger_id` ascending) first.
- **Direction-compatible boarding** (owner decision D-01): a passenger
  enters a car only if the car will leave the floor the passenger's way.
  Classification follows §4.2: direction first, capacity only when
  compatible.
  A car continuing its sweep takes only passengers travelling that way; a
  car at a reversal point or idle takes the oldest waiting passenger and
  leaves in that passenger's direction, taking everyone else at the floor
  who travels the same way and fits. A passenger whose assigned car
  arrives going the other way waits for its return (**direction
  deferral**). The origin stays committed, so LOOK returns.
- **Capacity deferral**: if the car arrives with a compatible departure
  direction (or `FREE`) but has no room for the passenger after step 3 and
  earlier boarders, the passenger remains `WAITING`, the origin remains
  committed, and the elevator continues under LOOK. Because
  every onboard passenger alights within one sweep, room becomes
  available and LOOK returns to the floor. Both deferrals are lawful and
  recorded: the TickRecord shows the elevator at the floor with the
  passenger not among the boarded; the projection distinguishes them
  ([scheduler_design.md](scheduler_design.md) §5).
- **Capacity is never exceeded**: step 4 is the only path to `ONBOARD` and
  it checks `load < C` before each boarding. An `ONBOARD` count above `C`
  cannot be produced; if observed, it is corruption (constitution N6).
- **Travel is never a detour**: a passenger boards only a car leaving in
  its direction, and LOOK never reverses while that passenger's
  destination lies ahead, so `travel_time = |destination - origin|`
  exactly (constitution P11).
- Multiple waiting passengers at one stop board in `passenger_id` order
  among those compatible with `D`, until full.
- Later assignments to the same elevator change its future route and may
  change when it next passes a floor in the right direction with room;
  this is why the scheduler re-projects the whole route on every candidate
  assignment ([scheduler_design.md](scheduler_design.md) §5) and why
  projection exactness (constitution P9) holds only for elevators receiving
  no further assignment.

## 6. Edge cases, resolved

| Case | Rule |
| --- | --- |
| Request at `t` at the floor where its assigned elevator sits at `t` | Assigned in step 2, boards in step 4 of the same tick if room and the departure direction is compatible: always, if the car is idle (`FREE`); `wait = 0`. If the car is passing through continuing the other way, the passenger waits for the return. |
| Pickup and dropoff at the same floor in the same tick | Step 3 then step 4. Alighters leave before boarders enter. A single passenger cannot do both (origin != destination). |
| Multiple elevators at the same floor | Independent. Each serves only its own assigned passengers. No passenger ever boards an unassigned elevator. |
| Simultaneous requests (same `request_time`) | Revealed and assigned in `passenger_id` order (stable Trace order). Each assignment sees the previously committed ones. |
| Empty gaps between request times | Every intermediate tick executes and produces a TickRecord. Idle elevators stay put with heading `NONE`. |
| Request time skips ahead | Same: the engine ticks through every `t`; it never jumps to the next request time. |
| `origin == destination` | Invalid Request. Trace load is refused with the offending `input_index` and `source_id`. Never generated by the Scenario generator. |
| Missing or duplicate `source_id` | Invalid input. Trace load is refused with the offending indices (`MISSING_SOURCE_ID`, `DUPLICATE_SOURCE_ID`). |
| Elevator full when reaching an assigned waiting passenger | Capacity deferral (§5). |
| Elevator reaches an assigned waiting passenger while departing the other way | Direction deferral (§5); the car returns within its sweep. |
| Two passengers at one floor, one up-bound and one down-bound, car free | The older one boards and sets the direction; the other waits for the return (W-G). |
| Several passengers board and alight at one stop | All eligible alight; then those compatible with the departure direction board in id order until full; all in one tick. |
| Direction reversal | §4: only when no committed stop is ahead; same tick; no time cost. |
| Idle elevator | Heading `NONE`, stays at its floor. No parking or return-to-lobby behaviour. |
| Doors / dwell time | **Zero.** Stops consume no time. An elevator can alight, board and move one floor in one tick. Recorded as an assumption in [assumptions_and_tradeoffs.md](assumptions_and_tradeoffs.md). |
| A policy proposes an elevator id outside `0..N-1`, or raises | The run HALTs with reason `INVALID_PROPOSAL` / `POLICY_ERROR` at tick `t`, step 2. The events of tick `t` so far (`REVEALED`, earlier `ASSIGNED`) are discarded with the tick; the History is the completed ticks plus the `HALTED` event (constitution §4.3, §4.4). The engine never substitutes. |
| The engine's own checks detect a violated runtime invariant | The run HALTs with reason `INVARIANT_VIOLATION` at the failing step; the tick is discarded; the `HALTED` event carries the violated invariant as a diagnostic (§2, owner decision 008). Never repaired, never continued. |
| Trace with zero requests | The run completes at `t = 0` with one TickRecord; the summary is the empty-population form of [evaluation_design.md](evaluation_design.md) §4.3; `T_last = 0`. |
| Initial floors | Configured per elevator; default 0. Must be in range. |

## 7. Request visibility

The engine holds the full Trace. It exposes, to anything outside itself,
only:

- `revealed(t)`: the Requests with `request_time <= t` (as Passengers);
- within step 2, the `SchedulerView` for one newly revealed passenger.

The `SchedulerView` is an immutable value built by the engine from the
current state and contains no reference to the Trace, the engine, or any
Request with `request_time > t`. There is no other interface. A policy that
needs anything else is out of contract. The invariant and its witness are
constitution N1 and [testing_contract.md](testing_contract.md) §3 and §5.

## 8. Termination and the liveness bound

The run is `COMPLETED` at the first tick `t` at which, after step 4, every
Request has been revealed and every Passenger is `COMPLETED`. If the Trace
is empty this is `t = 0`.

### 8.1 Liveness claim (constitution P10)

For every finite valid Trace, under the Route Policy of §4 and any
assignment of passengers to elevators (so for every Scheduler Policy),
every passenger reaches `COMPLETED` at a tick no later than

```text
T_last + 2 * P * (F - 1)
```

where `T_last` is the last request time (0 if `P = 0`) and `P` is the number
of Requests.

### 8.2 Proof

Elevators do not interact: a passenger is served only by its assigned car,
and a car's behaviour depends only on its own passengers. Fix one car `E`
with its finite set of assigned passengers.

**Lemma 1 (onboard destinations are weakly ahead at a boundary, strictly
ahead after alighting).** At every tick boundary, for every passenger
`ONBOARD E`, the destination lies weakly ahead of `floor_E` in `heading_E`:
ahead, or equal to the current floor (the passenger arrived during the
preceding movement and alights in step 3 of the coming tick). After step 3
of any tick, every remaining onboard destination lies strictly ahead, and
the car is never `FREE` while anyone remains onboard. Proof by induction
on ticks. Initially no one is onboard. A passenger boards in step 4 only
when `dir(p)` equals the departure direction `D'` (§4.2), and step 5 sets
`heading_E := D'`; the destination is in direction `dir(p)` from the
origin, so it is strictly ahead at the end of the tick and weakly ahead at
the next boundary after one floor of movement. For a passenger onboard at a
boundary with destination equal to the floor: step 3 alights them. For one
with destination strictly ahead after step 3: step 4 computes
`D := departure_direction`, which is `heading_E` whenever any committed
stop other than `f` lies ahead, and the destination is such a stop, so
`D = heading_E`, step 5 keeps the heading, and step 8 moves one floor
toward the destination. Hence a car with onboard passengers after step 3
is never `FREE` and never reverses while anyone is onboard.

**Lemma 2 (alighting within `F-1` ticks).** If at the start of tick `t` some
passenger is `ONBOARD E`, then some passenger alights from `E` at a tick in
`[t, t + F - 1]`. By Lemma 1 the nearest onboard destination is `d >= 0`
floors ahead; if `d = 0` the passenger alights at `t`; otherwise the car
keeps its heading and moves one floor per tick toward it, reaching it at
`t + d <= t + F - 1`, and alighting there in step 3.

**Lemma 3 (boarding within `F-1` ticks).** If at the start of tick `t` no
passenger is `ONBOARD E` but some passenger is `WAITING` assigned to `E`,
then some passenger boards `E` at a tick in `[t, t + F - 1]`. The committed
stops are exactly the origins of the waiting passengers. Case (a): the
car is at an origin `f` and `departure_direction` returns `FREE` (idle, or
no stop ahead): the car is empty, so the oldest waiting passenger at `f`
boards at `t` (§4.2). Case (b): `departure_direction` returns the heading
`h` because a committed stop lies ahead in `h`: let `x` be the farthest
committed stop ahead in `h`, at distance `<= F - 1`. The car moves one
floor per tick in `h` (heading is kept while a stop is ahead, by §4 and
§4.1) and reaches `x` at a tick `<= t + F - 1`. At `x`, no committed stop
lies beyond in `h`, so `departure_direction` returns `FREE`; the car is
empty (nobody boarded on the way, else we are done earlier) and `x` is an
origin with a waiting passenger, so the oldest boards. Case (c): no stop
ahead in `h` and the current floor is not an origin, or `heading = NONE`
at a non-origin floor: step 4 boards nobody; step 5 sets `heading :=
next_heading`, which points toward a committed stop (stops exist); from
tick `t + 1` the car is in case (b) with respect to the new heading, and
the farthest stop in that direction is at distance `<= F - 1` from the
current floor, so boarding occurs by `t + F - 1` (the car moves at tick `t`
already, in step 8, in the new heading).

**Progress events.** Each passenger boards at most once and alights at
most once, so `E` has at most `2 * P_E` progress events, where `P_E` is the
number of passengers assigned to `E`. Several progress events may occur
in one tick (a car can alight and board at the same stop); the bound
counts at most `2 * P_E` irreversible events, hence at most `2 * P_E`
distinct progress ticks. After `T_last`, no passenger is added. By Lemmas 2
and 3, whenever `E` has any passenger not yet `COMPLETED` at the start of a
tick `t >= T_last`, a progress event occurs at a tick in `[t, t + F - 1]`.
Let `t_1 < t_2 < ...` be the distinct ticks at which progress events of `E`
occur at or after `T_last`; there are at most `2 * P_E` of them;
`t_1 <= T_last + F - 1` and `t_{i+1} <= t_i + F - 1`. Hence the last event
occurs at a tick `<= T_last + 2 * P_E * (F - 1)`, and at that tick `E`'s
last passenger alights. Since `P_E <= P` for every car, every passenger
completes by `T_last + 2 * P * (F - 1)`. The termination check in step 7
fires at the tick of the last alighting, so the final tick obeys the same
bound. For `P = 0` the run completes at `t = 0 = T_last`. ∎

The bound is conservative: it charges a full `F - 1` ticks to every
progress event and ignores that boardings and alightings interleave.
Checks against the worked examples: W-B (`P = 2, F = 5`): bound 16, final
tick 8; W-G (`P = 2, F = 7`): bound 24, final tick 8; W-F: bound 16, final
tick 7.

### 8.3 The horizon

`max_ticks` defaults to `T_last + 2 * P * (F - 1)`, computed at Trace load.
A run that has not completed by then is `HALTED` with reason
`LIVENESS_BOUND_EXCEEDED` at step 7, reports the unserved count, and is an
invariant failure: by §8.2 it cannot occur under a correct implementation,
so its occurrence means the implementation (or this proof) is wrong and is
investigated, never averaged. The configuration may set a **smaller**
`max_ticks` for stress experiments; a halt under an explicit horizon is
reported as `HORIZON_EXCEEDED` with `unserved > 0` in the metrics and is
not an invariant failure. The two reasons are distinct so that the two
cases are never confused. A `max_ticks` larger than the default is refused
at load (`INVALID_CONFIGURATION`): nothing lawful can need it.

### 8.4 Outside the claim

Starvation under *unbounded* demand (an infinite stream of younger
same-direction passengers refilling the car before every compatible pass of
one floor) is possible and is outside the claim, which is about finite
Traces; it is discussed in [scheduler_design.md](scheduler_design.md) §8
and measured, not prevented, by the evaluation harness. The claim says
nothing about how long any individual passenger waits, only that every
passenger completes within the bound.

## 9. Passenger metrics

For a `COMPLETED` passenger:

```text
wait_time   = pickup_time  - request_time     (>= 0)
travel_time = dropoff_time - pickup_time      = |destination - origin|  (>= 1)
total_time  = dropoff_time - request_time     = wait_time + travel_time
```

All are integers. Because travel is fixed by the request, every difference
between policies is a difference in wait. Summary statistics over them are
defined in [evaluation_design.md](evaluation_design.md) §4.
