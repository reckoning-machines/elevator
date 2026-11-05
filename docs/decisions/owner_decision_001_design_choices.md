# Owner Decision Record 001: Design Choices and Admission of the Governing Documents

Status: **DECIDED 2026-11-04 by the owner (D-01 to D-07, §1); propagated to the governing documents as revision 4; NOT YET ADMITTED: the admission text in §3 has not been written, and the independent audit of revision 4 has not run.** This record carries the owner's decisions, the dispositions as they now stand, and the admission text that would admit the design at exact digests. Its shape follows the sibling project's decision and admission records ([doctrine_adoption.md](../doctrine_adoption.md) §1).

Source: [current_work.md](../current_work.md) §5;
[initial_design_audit.md](../audits/initial_design_audit.md);
[assumptions_and_tradeoffs.md](../assumptions_and_tradeoffs.md).

## 1. Owner's decisions on review of revision 3 (2026-11-04)

These control where they differ from the dispositions proposed at
revision 3. The owner's reasons are kept in the owner's words.

| Decision | Owner's call | Owner's reason |
| --- | --- | --- |
| D-01 direction-agnostic boarding | **Override** | Too artificial; creates an avoidable challenge to comparison fairness. "The current rule intentionally permits a passenger going 5 to 9 to board a car moving downward, ride the wrong way, and come back up; the docs explicitly acknowledge that this makes the naive baselines look worse. That is exactly the kind of thing an interviewer may challenge." Directed rule: an assigned passenger boards when the car is at the origin with capacity and its planned departure direction from that floor is compatible with the passenger's destination; an idle car may depart toward the passenger's destination; the immutable assignment remains; if the assigned elevator reaches the origin going the wrong way, the passenger waits for its return. |
| D-02 zero dwell | Accept | Exactly the right simplification. |
| D-03 refuse `origin == destination` | Accept | Reasonable domain validation; document it clearly. |
| D-04 Tier 1 / Tier 2 capacity | Accept | Resolves immediate-assignment versus capacity without transferring policy authority into the engine. |
| D-05 cost defaults | Accept provisionally | They are configuration, not doctrine; Monte Carlo and sensitivity runs can evaluate them. |
| D-06 checkpoint every UI tick | **Override** | CPOC should not distort normal UI execution: at a 500 ms stepping cadence the default would force temp-file, fsync and rename twice a second for a durability nobody asked for. Directed rule: interactive runs support explicit checkpointing and an optional configurable interval; the dedicated CPOC witness proves lawful continuation. |
| D-07 include documents time | Accept | Otherwise the reported effort is misleading. |

The owner also found two stale admission references (constitution §15 and
the plan's final section still pointed at `current_work.md`); both are
repaired (audit F-32, F-33). The owner's sequence: repair, override D-01
and D-06, propagate as revision 4, regenerate digests, run the independent
audit, resolve its findings, then admit the exact bytes; the
implementation plan is admitted separately and later.

## 2. Dispositions as they stand at revision 4

### D-01. Boarding is direction-compatible (owner override)

**Disposition.** At a stop, the car's departure direction is established
before boarding: a car with a committed stop ahead in its heading
continues that way; a car that is idle or at the end of its sweep is
free. A passenger boards only if their direction matches the departure
direction; a free car takes the oldest waiting passenger at the floor and
departs their way, with everyone else at the floor travelling the same
way who fits. A passenger whose car passes the wrong way waits for its
return ([simulation_semantics.md](../simulation_semantics.md) §4.1, §5).

**Why the free-car rule, and not "turn toward the remaining stops".** The
latter deadlocks: a car between an up-bound passenger above and a
down-bound passenger below turns away from each on arrival and oscillates
forever ([worked_examples.md](../worked_examples.md) W-G). The free rule
makes every sweep end board someone when anyone is waiting there with
room, which is what the liveness argument in semantics §8 now rests on.

**Consequences propagated.** Travel equals trip distance (constitution
P12; `detour` removed from outputs, metrics and observations); `w_total`
removed from the cost function because it no longer varies across
candidates; the marginal-delay term may be negative and its test is
reworded; the projection reports capacity deferral (which decides the
tier) separately from wrong-way passes (a route cost); step 5 uses the
promised departure direction so an idle car never turns toward a nearer
stop against the passengers it just boarded; the liveness bound widened
to `6(F-1)(P+1)`; new tests `direction_deferral_then_return`,
`free_car_oldest_sets_direction`, `reversal_point_is_free`,
`promised_direction_overrides_nearest`, `never_boarded_wrong_way`,
`travel_equals_distance`. Delta of the override relative to revision 3:
`ΔS != NONE` (boarding semantics), `ΔO = NONE`, `ΔA = NONE`.

**Two-case test.** W-F (a down-bound passenger skipped by an up-continuing
car, boarded on the return, travel exactly 1) and W-C (Nearest Car still
picks the car heading away on a tie; cost-based picks the idle car).

### D-02. Stops take zero time (accepted)

No dwell or door time. A dwell parameter would add an authoritative
per-elevator counter and a checkpoint field; it is improvement 1 in
[assumptions_and_tradeoffs.md](../assumptions_and_tradeoffs.md) §4.

### D-03. A request with `origin == destination` is refused at load (accepted)

The Trace is refused with the offending index; the generator never emits
one. Stated in semantics §6 and the README's assumptions.

### D-04. Capacity admissibility is the policy's, in two tiers; the engine validates structure only (accepted)

The cost-based policy rejects any candidate whose projected route would
capacity-defer the candidate or an already-committed passenger while a
non-deferring candidate exists (Tier 1), else chooses the cheapest
deferring candidate and records `tier = 2`. Direction deferral is a route
cost, not infeasibility, and does not affect the tier. The engine
validates only that the proposal is an elevator id for a newly revealed,
unassigned passenger ([scheduler_design.md](../scheduler_design.md) §6.2, §7).

### D-05. Default cost parameters (accepted provisionally)

`w_wait = 1, w_marginal = 1, w_tail = 3, tail_threshold = 2(F-1),
age_scale = F-1`, all integers, all Configuration and part of `run_id`.
`w_total`, present at revision 3, was removed as a consequence of D-01;
no accepted value changed. Sensitivity sweeps are improvement 5.

### D-06. Checkpointing is explicit, never default (owner override)

No run checkpoints unless asked: `--checkpoint-at`, `--checkpoint-every`,
and the UI's Checkpoint action and optional interval. Durable I/O is never
on the ordinary tick path. A session never checkpointed does not survive
server death; the dedicated witness proves continuity
([cpoc_design.md](../cpoc_design.md) §2; [ui_design.md](../ui_design.md) §2.1).
Delta relative to revision 3: `NONE` (a default changed, no owner or
carrier).

### D-07. The documents phase counts toward "time spent" (accepted)

The README's figure includes the design phase logged in
[current_work.md](../current_work.md) §7.

## 3. Admission text (to be written by the owner after the independent audit)

Admission admits the exact bytes of the files below at the digests below.
If a digest differs at the time of admission (for instance after a repair
the independent audit requires), this table is regenerated before the
admission text is written. After admission, the admitted files are not
edited to change their status lines; this record supersedes them.

| File | SHA-256 (revision 4, 2026-11-04) |
| --- | --- |
| `docs/constitution.md` | `7848813a17d0958b3d85601fc030ed75724b7edb3cc803573947ce6fb8a116bb` |
| `docs/authority_model.md` | `132cf6b6d86432b65bd23f5ee3dd1e80b1142b380cb4e81b70dfa187c43830f9` |
| `docs/simulation_semantics.md` | `f259fb30f6ffe57512d91fb905e4887281d6967e090631d461cd9ea5976cffed` |
| `docs/scheduler_design.md` | `f82f4f0dcb9378e1c8a24d296e70577a9d1be8cc8c7d380d23a6e8a6e108e3a6` |
| `docs/evaluation_design.md` | `0fdbbaad6870d935b02e00740ea0b35cf93a6d5e0623f678293314a9fdc290d9` |
| `docs/cpoc_design.md` | `d9b828f3f7fb58ed8f6dc8be469be78be555e716f4af32095e2db51882d56844` |
| `docs/ui_design.md` | `e07a8492233a7849ca1a3ac0a3c80e1e3b75097708717ba6a7df174abcb457b6` |
| `docs/architecture.md` | `2dc2c98a44716f19071699c0ae44800bfaae4dbeaccb5cf0b5e99af6861277c8` |
| `docs/testing_contract.md` | `c9a9ad7d52d5f2cfdba47b7f3151efadce5f4346071b7c05fae45115f09ed566` |

Proposed wording, for the owner to adopt or amend:

```text
I confirm my decisions D-01 to D-07 of 2026-11-04 as recorded in §1.
I admit the governing documents at revision 4, at the digests in §3,
as the design baseline. Implementation remains not authorized until the
implementation plan is admitted by a separate record.
```

Preconditions the owner should see satisfied before writing it: the
independent audit of revision 4 against
[whole_design_audit_checklist.md](../audits/whole_design_audit_checklist.md)
recorded in `docs/audits/` with `OSA PASS`; no OPEN marker in the
governing documents.

## 4. What this record does not do

It does not admit the implementation plan, authorize any cut, certify
anything, or claim that a CPOC witness has run. Relative to revision 3
its propagated delta is D-01's `ΔS` (boarding semantics); everything else
is `0/0/0`.
