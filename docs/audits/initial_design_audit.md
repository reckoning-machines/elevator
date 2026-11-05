# Initial Design Audit

Status: **EVIDENCE. Conducted 2026-11-04 on the draft governing documents. Authorizes nothing. Two passes: pass 1 during drafting (findings repaired before the revision-2 text was fixed), pass 2 on the revision-2 text (findings repaired in revision 3). Not to be edited; a later re-audit is appended.**

Method: for each governing document, ask what would satisfy its words and
still violate its intent; look for two owners of one fact, undefined terms,
hidden mutable state, future leakage, undefined ordering, contradictions
between documents, starvation, capacity ambiguity, nondeterminism,
unreconstructable metrics, UI authority, restart dependence on transient
state, over-claiming, tests that do not prove their rule, unnecessary
infrastructure, and missing source requirements. Severity: **HIGH** (a
constitutional or authority conflict, or a rule that could make the
simulation wrong), **MEDIUM** (an ambiguity that two implementers would
resolve differently, or a claim stronger than the design supports),
**LOW** (wording, redundancy, or a missing edge).

## Pass 1: findings against the drafting text (revision 1)

| # | Severity | Finding | Repair | Where |
| --- | --- | --- | --- | --- |
| F-1 | HIGH | Round Robin as "the next elevator in rotation" carried a pointer across ticks: hidden policy state, unowned, not checkpointed; a restart would change the next assignment. | Round Robin redefined as `passenger_id mod N`, stateless. Rule added: any policy state must be declared, engine-owned and checkpointed (constitution N14). | scheduler §4.1; constitution N14 |
| F-2 | HIGH | "Capacity infeasibility is a hard rejection" conflicted with "every passenger is immediately assigned": with one elevator that is full, no admissible candidate exists and the engine would have to reject or pick a default. | Deferred boarding defined as lawful engine behaviour; scheduler admissibility split into Tier 1 (no deferral) and Tier 2 fallback, with the tier recorded in the receipt. | semantics §5; scheduler §6.2 |
| F-3 | HIGH | An authoritative, stored "route" per elevator duplicated authority already held by Passenger records (committed stops are a function of them) and would drift after a later assignment. | Route is `DERIVED` (LOOK over floor, heading, committed stops); only `heading` is authoritative per elevator. Load and onboard/waiting sets likewise derived. | authority rows 7 to 9 |
| F-4 | MEDIUM | "Position at tick t" was ambiguous between the floor before and after the move, giving an off-by-one in wait and travel and in the `t = 0` row. | `floor_E(t)` defined as beginning-of-tick; RECORD placed before MOVE; consequences pinned by tests. | semantics §2, §3 |
| F-5 | MEDIUM | A draft Passenger record carried `expected_pickup` from the scheduler: an estimate on the authority for outcomes, one mutation away from being reported as realized. | Estimates exist only as `EPHEMERAL` during the call and as a `RECEIPT` on the `ASSIGNED` event; the Passenger type has no estimate field; a test asserts it. | constitution N9; authority row 13; testing §1 |
| F-6 | MEDIUM | The liveness claim was stated unconditionally; under unbounded adversarial demand with oldest-first boarding at a stop but not across floors, a passenger can be starved. | Claim narrowed to finite Traces with an explicit bound; `max_ticks` halt is an invariant failure; unbounded starvation is measured, not prevented, and said so. | semantics §8; scheduler §8 |
| F-7 | MEDIUM | The Checkpoint embeds future Requests, which looked like a no-look-ahead violation. | Clarified: the Trace is an input (authority row 2), persistence is not inspection; the invariant governs the policy's decision surface; the future-leakage negative witness proves non-influence. | cpoc §3, §6 |
| F-8 | LOW | Cost weights as floats would make ties platform-dependent. | Exact integer arithmetic; weights are integers; `age_scale` keeps the marginal term integral. | constitution N15; scheduler §6.3 |
| F-9 | MEDIUM | A continuation that silently reran from `t = 0` would pass an output-equality witness. | Witness strengthened: the fresh process must emit its first TickRecord at `t`, emit none earlier, record `RESUMED` with the checkpoint's `t`, and have a tick count equal to the remainder; the reference is a separate process. | cpoc §4 step 7; constitution N13 |
| F-10 | LOW | "Play" could become a browser-held tick counter; a stale tab could step a superseded state. | The client timer only issues Step requests; `from_time` is a guard the server checks against its own `t`, never a selector; stale requests are refused with the current state. | ui §2.1, §6; authority §6 |
| F-11 | MEDIUM | Termination as "all passengers completed" would end a run before later requests were revealed. | Termination requires all Requests revealed and all passengers complete. | semantics §8; test `termination_waits_for_unrevealed_requests` |
| F-12 | LOW | Draft evaluation text promised "the cost-based policy performs better"; the design cannot support a universal claim. | Paired-by-seed design; permitted claim form stated; forbidden forms listed. | evaluation §6.4, §6.5 |
| F-13 | MEDIUM | Projection exactness (scheduler and engine agreeing on the future) was asserted but would hold only if both used one function; two implementations "kept in sync" would drift. | `project` is defined as `next_heading` iterated; the engine's step 5 is `next_heading`; a test asserts function identity and one-step equality. | scheduler §5; testing §1 |
| F-14 | LOW | Nearest Car ignoring load and direction could be called a strawman. | Baseline defined exactly; claims bounded to that definition; said in assumptions. | scheduler §4.2; assumptions §3 |
| F-15 | MEDIUM | Whether an elevator reverses in the same tick it empties, or one tick later, was undefined, changing travel times by one. | HEAD is computed after BOARD in the same tick; reversal costs nothing. | semantics §2.1, §4 |
| F-16 | LOW | A request appearing at the elevator's floor: wait 0 or 1 was undefined. | Assign precedes board in the same tick: wait 0. | semantics §6 |
| F-17 | MEDIUM | Events and TickRecords both carried elevator positions (a `MOVED` event per tick), two historical carriers of one fact. | Elevator motion history lives only in TickRecords; Events carry passenger and run transitions only; the floor on `BOARDED`/`ALIGHTED` is the origin/destination already in the Trace. | authority rows 14, 15 |
| F-18 | LOW | Source requirement "README must include time spent" had no carrier. | `current_work.md` keeps a time log from this phase; plan cut 12 carries it to the README. | current_work §7 |

## Pass 2: findings against the revision-2 text

| # | Severity | Finding | Repair | Where |
| --- | --- | --- | --- | --- |
| F-19 | MEDIUM | The CPOC witness started process A with a flag named `--stop-after-checkpoint` and then said A "keeps running": contradictory. Worse, if A kept running it could complete the Run and write a final result before being killed, so B would refuse with `RUN_FINAL`: a race inside the witness. | A pauses after writing the checkpoint, holding its in-memory state, so the kill is of a live process holding authority and A cannot race ahead. | cpoc §4 step 2 |
| F-20 | LOW | The Checkpoint carried `policy: name, params` "repeated for the loader's check" while the Configuration already carries it; `run_id` listed "policy identity" as a separate input. A needless duplicate carrier. | Policy identity lives only in the Configuration; `run_id = hash(configuration_hash, trace_hash, code_identity)`; the Checkpoint carries a `provenance` block (scenario, seed) that is informational and not part of `run_id`. | constitution §2, §12; cpoc §3; authority §6 |
| F-21 | LOW | The "altered seed" negative witness referred to a seed in the Checkpoint's configuration block, which does not exist (the Configuration has no seed). | Rewritten as two witnesses over the `provenance` block: altering it changes nothing in the continuation (the embedded Trace decides) and is reported by the harness as a provenance mismatch; regenerating the Trace from the altered seed changes `run_id`. | cpoc §6 |
| F-22 | LOW | Reconstruction rule 8 required the last TickRecord to agree with elevator floors, impossible at `t = 0` where no TickRecord exists. | At `t = 0` floors must equal configured initial floors; test added. | cpoc §5; testing §1 |
| F-23 | LOW | "The last row's heading is `NONE`" was stated for every run; false for a `HALTED` run. | Qualified to `COMPLETED` runs. | semantics §3 |
| F-24 | LOW | `capacity_stress` required "distinct destinations", impossible when `num_requests > F - 1`. | Destinations drawn uniformly from the other floors. | evaluation §2 |
| F-25 | LOW | Whether same-tick revealed-but-unassigned passengers appear in a later `SchedulerView` of the same tick was implicit. | Stated: they do not (the view lists passengers only under elevators). | scheduler §3 |
| F-26 | LOW | A Step request on a `COMPLETED` run (the play timer keeps firing) was undefined. | No tick; final state returned; test added. | ui §2.1; testing §1 |

## Checks that found nothing

- **Conflicting ownership**: every row of the authority table has one
  owner and one write boundary; the sweep in authority §6 found no carrier
  outside the table.
- **Hidden mutable state**: no module globals, class attributes, policy
  attributes or UI-side state hold a governed fact; the UI's only client
  state is the play timer.
- **Nondeterministic ties**: every tie rule is lexicographic on ids or a
  fixed preference.
- **Unreconstructable metrics**: every metric in evaluation §4 is a
  function of `passengers.csv` and the History; `deferred.count` and
  `elevator_utilisation` derive from TickRecords and Events.
- **UI authority leakage**: no JSON API, no client model, no URL state but
  identifiers.
- **Unnecessary infrastructure**: no database, broker, queue, WebSocket,
  framework beyond FastAPI/Jinja2/HTMX; justified in cpoc §9 and
  architecture §6.
- **Missing source requirements**: configurable `N`, `F`, `C`; destination
  dispatch; immediate immutable assignment; one floor per tick; ticking
  through gaps; no look-ahead; eventual service; total time objective;
  position log from `t = 0`; min/max/average wait and total; observations;
  README items; presentation: each has an owning section, and the plan's
  cut 12 carries the README and walkthrough.
- **Tests that do not prove their rule**: each test row names its rule;
  the no-look-ahead section states what weaker tests would miss; the
  in-process checkpoint round-trip is labelled "not CPOC".

## Disposition

All 26 findings are repaired in the revision-3 text. No finding remains
open as a constitutional or authority conflict. Six design choices are
marked **OPEN** or recommended for the owner's confirmation in
[current_work.md](../current_work.md) §5; none of them is a conflict
between documents, and each is written under the recommended choice so the
documents are coherent as they stand.

Pass-2 re-check after repairs: the repaired passages were re-read against
their cross-references (constitution §2 and §12 against cpoc §3 and
authority §6 for `run_id`; cpoc §4 against §5 and §8 for the paused
process; semantics §3 against §8 for `HALTED` rows). No new contradiction
found.

This audit establishes evidence of coherence at revision 3. It does not
admit the documents and does not authorize implementation.

## Pass 3 (appended 2026-11-04): worked examples and alignment with the speedway record shape

Writing the worked examples ([worked_examples.md](../worked_examples.md))
by hand against the rules, and comparing the repository's record shape
with the sibling project `~/dev/speedway` (which the owner named as the
analog), produced the following.

| # | Severity | Finding | Repair | Where |
| --- | --- | --- | --- | --- |
| F-27 | MEDIUM | A halt inside a tick (W-E: invalid proposal at tick 0, step 2) left the fate of that tick's already-emitted events (`REVEALED`, earlier `ASSIGNED`) undefined: "History up to the halt" could be read as including them, contradicting §4.4 (no partial tick is durable). | The History of a `HALTED` run is every completed tick plus one `HALTED` event recording tick, step and reason; the halting tick's events are discarded with it. | constitution §4.3; semantics §6; W-E |
| F-28 | LOW | No transition-class table: who proposes, validates and decides each kind of change was spread across several documents, so an auditor could not check "every change fits a class" in one place. | Constitution §4.5 added, mirroring speedway's Part V, with fifteen classes and the rule that a change fitting none is a stop. | constitution §4.5 |
| F-29 | LOW | The authority sweep listed carriers and classes but not what each carrier is denied, so a proposed misuse (reading `passengers.csv` to rebuild state, trusting `from_time`) had to be argued from principles each time. | A "Bound to" and "Denied rights" column on every carrier, mirroring speedway's Part VII. | authority §6 |
| F-30 | LOW | Admission was to be recorded in `current_work.md`, a mutable record, with no digest of what was admitted; a later edit could silently change the admitted text. | `docs/decisions/` created; the proposed decision record carries each governing document's SHA-256 so admission names exact bytes; `AGENTS.md` states the current revision and routes to the record. | decisions/owner_decision_001; AGENTS.md |
| F-31 | LOW | The audit was by the author of the drafts only. | An independent whole-design checklist with pass conditions and graded thresholds added; admission requires an audit against it by someone other than the author. | audits/whole_design_audit_checklist.md; AGENTS.md |

All five repaired in the revision-3 text (the revision number is unchanged
because the owner has not yet reviewed revision 3; the status lines were
not bumped for the same-day additions).

## Disposition under graded thresholds

**B, BOUNDED GAPS WITHIN A COHERENT FRAME**, by the thresholds in the
checklist. Every governed fact has one owner and one commit boundary; every
carrier is classified with its denied rights; every tick step, refusal and
transition class is stated once; the worked examples follow from the rules
by hand. It is not **A** because seven choices remain the owner's to
confirm (D-01 to D-07 in the decision record) and because no independent
audit has run. It is not **C**: no fact has two owners, no owner, or an
owner that is a policy, cache, projection or browser.

## Pass 4 (appended 2026-11-04): owner review and decisions D-01 to D-07

The owner reviewed revision 3 and decided D-01 to D-07 (recorded in
[decisions/owner_decision_001_design_choices.md](../decisions/owner_decision_001_design_choices.md) §1).
The review also found two record defects. Findings and the revision-4
propagation:

| # | Severity | Finding | Repair | Where |
| --- | --- | --- | --- | --- |
| F-32 | MEDIUM | The constitution (§15) still said admission is "recorded in `current_work.md`", contradicting `AGENTS.md` and the decision record, which make `docs/decisions/` the only admission surface. Found by the owner. | §15 now names a decision record in `docs/decisions/` with files and digests. | constitution §15 |
| F-33 | LOW | The implementation plan's "What admits this plan" still said admission occurs in `current_work.md`. Found by the owner. | Now a separate decision record, written after the design is admitted and the plan inspected against the admitted revision. | plan, last section |
| F-34 | HIGH (design, by owner decision) | D-01 overridden: direction-agnostic boarding, though coherent, let a baseline carry a passenger the wrong way and so inflated the cost-based policy's advantage; an interviewer could call the comparison unfair. | Direction-compatible boarding (semantics §4.1, §5): a car continuing its sweep takes same-direction passengers; a free car (idle or at a reversal point) takes the oldest waiting passenger and departs their way; a wrong-way pass defers the passenger to the return. Consequences propagated: travel equals distance (new P12; `detour` removed everywhere); `w_total` removed from the cost (it no longer varies across candidates); `marginal` may be negative and the test is reworded; `deferred` in the projection means capacity deferral at a compatible arrival, with `wrong_way_passes` reported separately; step 5 uses the promised departure direction so an idle car never turns toward a nearer stop against its boarders; liveness argument rewritten and the bound widened to `6(F-1)(P+1)`; the oscillation case that a naive "turn toward remaining stops" rule produces is shown and tested (W-G). | semantics, constitution, scheduler, evaluation, testing, worked examples, assumptions |
| F-35 | MEDIUM (design, by owner decision) | D-06 overridden: checkpointing every interactive tick put fsync-and-rename on a 500 ms hot path for a durability nobody asked for. | No default checkpoint anywhere; explicit Checkpoint action and optional interval in the UI; continuity proved by the witness, not by every session. | cpoc §2; ui §2.1 |

D-02, D-03, D-04, D-07 accepted as proposed; D-05 accepted provisionally
with the note that `w_total` was removed as a consequence of D-01 (it is
not a change of any accepted value, since the remaining defaults are
unchanged). All propagated as revision 4; the governing set's digests were
recomputed in the decision record. Not re-audited independently: that is
the next step, and it is not for the author of the drafts.

## Pass 5 (appended 2026-11-04): pointer to the revision-5 repair record

Revision 4 was audited independently
([independent_revision_4_audit.md](independent_revision_4_audit.md)) and
failed (`OSA FAIL — C`; 7 HIGH, 9 MEDIUM, 3 LOW; I-01 to I-19). The
author's repairs are recorded, finding by finding, in
[revision_5_repair_record.md](revision_5_repair_record.md), which is
author repair evidence only. No grade is given to revision 5 here or there.
This historical audit is otherwise unchanged.

## Pass 6 (appended 2026-11-04): pointer to the revision-6 repair record

Revision 5 was audited independently
([independent_revision_5_audit.md](independent_revision_5_audit.md)) and
failed (`OSA FAIL — C`; 5 HIGH, 9 MEDIUM, 2 LOW; R5-I-01 to R5-I-16). The
author's bounded repairs are recorded, finding by finding, in
[revision_6_repair_record.md](revision_6_repair_record.md), which is
author repair evidence only. No grade is given to revision 6 here or there.
This historical audit is otherwise unchanged.

## Pass 7 (appended 2026-11-05): pointer to the revision-7 repair record

Revision 6 received a bounded independent closure audit
([independent_revision_6_closure_audit.md](independent_revision_6_closure_audit.md)):
8 CLOSED, 8 PARTIAL, 0 OPEN; 0 HIGH, 6 MEDIUM, 1 LOW (R6-I-01 to
R6-I-07). The author's surgical closure is recorded in
[revision_7_repair_record.md](revision_7_repair_record.md), author
evidence only. This historical audit is otherwise unchanged.
