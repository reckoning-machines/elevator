# Scheduler Design

Status: **GOVERNING DOCUMENT for assignment policy. DRAFT, NOT ADMITTED. Revision 7.1 (bounded component-mapping and reference repairs, 2026-11-05).**

Jurisdiction: the assignment decision, the information lawfully available to
it, the policy interface, the baseline policies, the cost-based policy, the
route projection, capacity admissibility, tie-breaking, fairness and
starvation. Subordinate to [constitution.md](constitution.md) and
[simulation_semantics.md](simulation_semantics.md). The engine's handling of
the proposal is owned by the latter (tick step 2).

## 1. The decision, framed as a decision

The one decision a policy makes:

> Which elevator should receive this passenger request, given only the
> information lawfully available at this time?

Applied Information Economics (AIE) is the framing the owner's project
brief asked for; it is not part of the take-home. It asks of any decision:
what is uncertain, what would it be worth to know, and what does it cost to
find out. Here:

| Quantity | Status at decision time | Lawfully reducible? | Cost to reduce | Worth it? |
| --- | --- | --- | --- | --- |
| The candidate's pickup delay on elevator `E` | **Derived estimate**, exact if no later assignment touches `E` | Yes: project `E`'s route under LOOK (§5) | `O(route length)` per candidate, `N` candidates | **Yes.** Cheap, exact for the committed world, and the single largest driver of wait. |
| The candidate's total time on `E` | `wait + |destination - origin|`; travel is fixed by the request (constitution P11) | n/a | none | **Not separately.** It differs across candidates only through wait. |
| Marginal delay imposed on `E`'s already-committed passengers | Derived estimate from the same projection, with and without the candidate | Yes | one extra projection per candidate | **Yes.** It is what distinguishes system cost from passenger cost. |
| Route disruption (extra reversals, wrong-way passes that defer a boarding) | Fully captured by the two projections above as extra wait ticks | n/a | none extra | **Not separately.** A separate penalty would double-count. |
| Direction compatibility | A mechanical boarding rule (semantics §5); its cost is the extra wait when the car first passes the origin the wrong way, captured by the projection | n/a | none | **Not separately.** |
| Capacity feasibility (will the candidate be capacity-deferred; will anyone already committed be newly deferred) | Observed from the projection's load profile | Yes | none extra | **Yes**, as a hard constraint (§6.2). |
| Tail risk of excessive wait for the candidate | Observed from the projected pickup | Yes | none | **Yes**, as a soft penalty (§6.3). |
| Fairness to already-waiting passengers | Age of each committed passenger is observed | Yes | none | **Yes**, as a weight on marginal delay (§6.3). |
| Future requests | **Unknowable by rule** (constitution N1) | **No.** | infinite | **Forbidden.** |
| Future assignments to `E` by this same policy | Unknown; depends on future requests | Only by forecasting demand from the past | a demand model | **Not in scope.** No demand model is built; the calibration report (§9) measures the projection error this source causes, which is one input to deciding whether such a model would be worth building. |
| Global reassignment to repair earlier choices | Prohibited (constitution N2) | n/a | n/a | **Forbidden.** |

The conclusion is a policy that computes one exact route projection per
candidate elevator (two, with and without the candidate), reads cost from it,
and stops. That is the whole "AIE engine". The four strata the owner's
brief asks to keep distinct:

- **observed state**: the `SchedulerView` (§3);
- **derived estimates**: projections and costs (`EPHEMERAL`, row 21 of the
  authority model);
- **committed decisions**: the engine's `ASSIGNED` write, with the chosen
  candidate's estimate attached as a `RECEIPT`;
- **realized outcomes**: `pickup_time`, `dropoff_time`, written later by the
  engine, never from an estimate.

## 2. Policy interface

```text
SchedulerPolicy
  name: str                       # 'round_robin' | 'nearest_car' | 'cost_based'
  params: mapping                 # part of the Configuration; part of run_id
  assign(view: SchedulerView, request: RevealedRequest) -> Proposal

Proposal
  elevator_id: int
  receipt: mapping | None         # the chosen candidate's estimates, if any

Determinism contract: for identical (view, request, params), assign returns
an identical Proposal. No wall-clock, no randomness, no retained state, no
I/O. A policy class holds params only; it has no mutable attributes.
```

The engine calls `assign` once per newly revealed passenger, in
`passenger_id` order, each call seeing a view that includes the assignments
committed by earlier calls in the same tick. The engine validates
`0 <= elevator_id < N` and commits; anything else halts the run
([simulation_semantics.md](simulation_semantics.md) §2 step 2).

## 3. The lawful decision surface: `SchedulerView`

An immutable value built by the engine, containing exactly:

```text
SchedulerView
  t: int
  floors: int, elevators: int, capacity: int
  elevators: tuple of ElevatorView, by id
     id, floor, heading
     onboard: tuple of (passenger_id, destination, pickup_time)   # ONBOARD E
     waiting: tuple of (passenger_id, origin, destination, request_time)  # WAITING, assigned to E
RevealedRequest
  passenger_id, origin, destination, request_time (== t)

(`source_id` is not in the view: it carries no decision content.)
```

Nothing else. No Trace, no engine reference, no History, no future, no
other policies' state. Every passenger visible in the view has
`request_time <= t`. Passengers revealed in the same tick but not yet
assigned (later in the step-2 order) are not in the view: they belong to
no elevator yet, and the view lists passengers only under elevators. The view is constructed fresh per call; the policy
cannot mutate it (frozen dataclasses or equivalent). This is how constitution
N1 is enforced structurally; the witness is
[testing_contract.md](testing_contract.md) §3.

Load is not a field; it is `len(onboard)`. Routes are not fields; a policy
that wants one calls the shared projection function (§5) on the view.

## 4. Baseline policies

### 4.1 Round Robin (`round_robin`)

```text
elevator_id = passenger_id mod N
```

Stateless. Because `passenger_id` is the stable Trace order, this is exactly
"the next elevator in rotation" without a pointer. (A pointer would be hidden
policy state, constitution N15; the initial audit removed it.) Ignores position,
load, direction. `receipt = None`.

### 4.2 Nearest Car (`nearest_car`)

```text
elevator_id = argmin over E of |floor_E - origin|, ties to lowest id
```

Stateless. Ignores load, direction and committed work: the classic naive
baseline, deliberately. `receipt = {distance}`. The evaluation reports it as
defined here; no claim is made against a smarter "nearest" variant.

## 5. Route projection (shared with the engine)

`project(elevator_view, extra_waiting=(), capacity, now) -> Projection` is a
pure function in the route module. It simulates one elevator forward from
`now` under exactly the engine's steps 3, 4, 5 and 8, by calling the same
three Route Policy function objects the engine calls
(`departure_direction`, `eligible_boarders`, `next_heading`,
[simulation_semantics.md](simulation_semantics.md) §4.1 to §4.3), with the
committed passengers plus any `extra_waiting` candidates, until no
committed stops remain, and returns:

```text
Projection
  pickup_time:  {passenger_id: t}     for every waiting passenger (incl. candidates)
  dropoff_time: {passenger_id: t}     for every passenger
  first_compatible_arrival: {passenger_id: t}   first tick the elevator was at the origin with a departure
                                                direction compatible with the passenger while the passenger
                                                waited (after the first boarder, if any, set it)
  deferred:     set of passenger_id   pickup_time > first_compatible_arrival (capacity deferral at least once)
  wrong_way_passes: {passenger_id: n} arrivals at the origin at which the passenger was refused for
                                      direction (direction deferrals; a route cost, not a capacity fact)
  max_load:     int                    always <= capacity by construction
  end_time:     t at which the elevator becomes idle
```

Observation phase: the projection records, at each simulated tick, the
outcome of `eligible_boarders` for every waiting passenger at the floor
under the single classification rule of
[simulation_semantics.md](simulation_semantics.md) §4.2: boarded; refused
for direction (a wrong-way pass, counted in `wrong_way_passes`; capacity
not evaluated); or refused for capacity (compatible, would have boarded,
no room; counted toward `deferred`). The two counts never overlap.

Rules:

- One implementation. The engine's steps 4 and 5 and the projection call
  the same function objects; neither reimplements any of them. Constitution
  P9 (projection exactness) is the behavioural test that the engine's
  realized times equal the projection when no further assignment is made to
  that elevator; `route_primitives_single_implementation` is the structural
  test ([testing_contract.md](testing_contract.md) §1).
- It never reads anything but its arguments. It cannot see other elevators,
  future requests or the Trace.
- It terminates because the passenger set is finite: the liveness proof of
  [simulation_semantics.md](simulation_semantics.md) §8.2 applies to one
  elevator and bounds the projection's length by `2 * P_E * (F - 1)` ticks
  beyond `now`.
- Cost: `O(end_time - now)` simulated ticks, each `O(committed passengers)`.
  No timing is claimed until measured; the plan's cut 8 records one
  measurement of the default Experiment.

The engine does **not** call `project` to move; it calls the three
primitives. The projection exists for policies and for the UI route strip.

## 6. Cost-based destination dispatch (`cost_based`)

A heuristic. No optimality is claimed.

### 6.1 Evaluation of candidates

For each elevator `E` in id order:

1. `base := project(E_view, (), C, t)` (the committed world without the
   candidate; may be memoised within the call, keyed by `E`).
2. `with := project(E_view, (candidate,), C, t)`.
3. From `with`: `wait_c = with.pickup_time[c] - t`, `deferred_c = c in with.deferred`.
   (`total_c = wait_c + |destination - origin|` is reported in the receipt
   but is not a cost term: travel is fixed by the request.)
4. Marginal delay to committed passengers:
   `marginal = Σ_{q committed to E} (age_scale + age(q, t)) * (with.dropoff_time[q] - base.dropoff_time[q])`,
   where `age(q, t) = t - request_time(q)`. A term is usually `>= 0`
   (adding a stop adds ticks) but can be negative: a new stop beyond a
   reversal point makes the car continue instead of turning, which can
   board a waiting same-direction passenger earlier and an opposite one
   later. The sum is the age-weighted net change in others' completion
   times, scaled by `age_scale` to stay integral.
5. Newly deferred others: `others_deferred = (with.deferred - base.deferred) ∩ committed(E)`:
   the committed passengers of `E` whose projected boarding is capacity-
   deferred with the candidate but was not without it.

### 6.2 Hard constraints (admissibility tiers)

```text
Tier 1:   not deferred_c  and  others_deferred is empty
Tier 2:   otherwise
```

Choose from Tier 1 if it is non-empty; otherwise from Tier 2. Exactly what
Tier 1 means (owner decision D-04 as repaired by I-09):

- the candidate is not capacity-deferred in the current projection of `E`
  with the candidate added; and
- assigning the candidate causes no **new** capacity deferral among the
  passengers already committed to `E`, relative to the base projection.

Tier 1 is a statement about this assignment decision under the current
committed world. It is **not** a claim that no committed passenger of `E`
is already projected to be capacity-deferred (a candidate may be Tier 1 on
a car that already carries a deferral the candidate does not worsen), and
it is **not** a guarantee about execution: a later assignment to `E` can
change the route and defer a passenger whose receipt said Tier 1. The
receipt is a conditional projection, not a durable capacity promise.
Direction deferral is outside capacity tiering entirely.

Capacity infeasibility in this sense is therefore a hard rejection whenever
any non-worsening elevator exists. The fallback exists only because the
assignment requires that every passenger be assigned immediately and
forbids rejection; in Tier 2 the deferral is real, lawful
([simulation_semantics.md](simulation_semantics.md) §5), already priced in
`wait_c` and `marginal` by the projection, and recorded in the receipt as
`tier = 2`.

Tier 2 is never empty: every projection terminates (§5), so every candidate
has a finite projected pickup.

### 6.3 Cost

```text
cost(E) = age_scale * ( w_wait * wait_c
                      + w_tail * max(0, wait_c - tail_threshold) )
        + w_marginal * marginal
```

Exact integer arithmetic (every factor is an integer; `age_scale` is applied
to the first group so the `marginal` term, already scaled, is commensurate).
Constitution N16.

Defaults (integers; all are Configuration parameters and part of `run_id`):

| Parameter | Default | Meaning |
| --- | --- | --- |
| `w_wait` | 1 | weight on the candidate's own projected wait (the only part of its total time the assignment can change) |
| `w_marginal` | 1 | weight on age-weighted net delay imposed on others |
| `w_tail` | 3 | extra weight on projected wait beyond the threshold |
| `tail_threshold` | `2 * (F - 1)` | one full sweep; a projected wait longer than this is a tail event |
| `age_scale` | `F - 1` | an already-waiting passenger who has waited one full traversal counts double |

The cost is **system-centric with passenger-centric corrections**: the
`w_wait` term is the candidate's cost, the `marginal` term is the net cost
the candidate imposes on everyone else, and together they approximate the
increase in total passenger-ticks across the system. The tail and age terms
are the fairness corrections (§8).

### 6.4 Selection and ties

```text
chosen = min over admissible tier of (cost(E), E.id)
```

Lexicographic: lowest cost, then lowest elevator id. No randomness. Two
candidates with equal cost always resolve the same way for the same view.

### 6.5 Receipt

```text
receipt = { policy: 'cost_based', tier, chosen: E, cost,
            projected_pickup, projected_dropoff,
            candidates: [ {E, tier, cost, wait_c, marginal, deferred_c, newly_deferred_others, wrong_way_passes_c} ... ] }
```

Attached to the `ASSIGNED` event by the engine. Never written to the
Passenger. Read only by the calibration report (§9) and the UI's
"why this elevator" disclosure, which renders `tier = 1` as "no new
capacity deferral in the projection at assignment" and never as a
guarantee.

## 7. Capacity in the scheduler

- The scheduler never checks `load < C` directly against the present; it
  reads the projection's `deferred` sets, which already apply the engine's
  own boarding rule along the whole future route including alightings that
  free room and the departure-direction rule.
- Direction deferral is not capacity infeasibility: a car that first
  passes the origin the wrong way and boards on its return is Tier 1; the
  extra wait is in `wait_c`.
- Multiple waiting passengers assigned to the same stop are boarded by the
  projection in id order among those compatible with the departure
  direction, exactly as the engine will.
- A later assignment can change the load ordering on `E`; each candidate
  evaluation re-projects the entire committed set, so the tier is always
  judged against the current whole route at that moment. It is not revised
  afterwards.
- The engine's own boarding check (step 4) remains the mechanical
  guarantee. A Tier 1 receipt does not prevent a later capacity deferral of
  that passenger caused by a later assignment; the engine defers lawfully
  whenever the rule requires, under every policy. A load above `C` is
  impossible in every case.

## 8. Liveness, starvation and fairness

- **Hard liveness** comes from the Route Policy, not the scheduler: LOOK
  with direction-compatible boarding completes every passenger of a finite
  Trace regardless of assignment
  ([simulation_semantics.md](simulation_semantics.md) §8). All three
  policies inherit it. This is why "every request is eventually served" is
  a property of the engine, verified by the Invariants category of tests
  across all policies, and not a promise each policy must make separately.
- **Starvation scenarios under naive policies** (finite but long traces):
  Round Robin assigns a lobby passenger to a car at the top floor serving a
  long up-sweep; Nearest Car assigns to an adjacent car that is passing
  through the other way or full, costing a return trip. Both are
  bounded by the sweep structure but produce long tails. The harness's
  `capacity_stress` and `adversarial` patterns are designed to expose them.
- **Fairness mechanisms in the cost-based policy**: (1) `w_tail` escalates
  the cost of any candidate assignment whose projected wait exceeds one
  sweep; (2) the age weight makes delaying a long-waiting committed
  passenger expensive, so new work is steered away from cars carrying old
  obligations; (3) Tier 1 admissibility refuses to plan a capacity
  deferral for the candidate or a new one for anyone already committed.
  (4) In the engine, oldest-first boarding at a stop is the within-car
  fairness rule.
- **What fairness cannot do here**: because assignment is immutable
  (constitution N2, this project's rule; the take-home forbids changing the
  destination, and immediate assignment plus immutability is the stricter
  reading this project adopted), no mechanism can rescue a passenger from
  a bad assignment after the fact. Fairness acts only at assignment time.
  This is stated as a trade-off in
  [assumptions_and_tradeoffs.md](assumptions_and_tradeoffs.md).
- **Unbounded adversarial demand** can starve a passenger under any of these
  policies (a stream of younger same-direction passengers that refills the
  car before every compatible pass of one floor).
  No prevention is claimed; the `max_wait` and `p95` metrics and the
  `unserved` count under a horizon measure it.

## 9. Calibration: estimates versus outcomes

An ex-post report (`DERIVED`) computes, for every `cost_based` assignment,
`realized_pickup - projected_pickup` and `realized_dropoff -
projected_dropoff` from the receipt and the Passenger record. Under
constitution P9 the error is zero for every assignment after which the
elevator received no further assignment; the distribution of nonzero errors
measures one source of projection uncertainty, the one the policy chose
not to model (future assignments to the same car). Calibration error
estimates that source; whether a demand model would be valuable would
require a controlled evaluation of a candidate model against the same
Traces, which is outside this project. The report writes nothing back to
any authority.

## 10. Policies out of scope

No seeded stochastic policy, learned policy, lookahead policy or
reassignment policy is in scope. Adding one requires an owner decision and,
for a stochastic one, a new engine-owned fact (its random state) in the
authority model and the Checkpoint.
