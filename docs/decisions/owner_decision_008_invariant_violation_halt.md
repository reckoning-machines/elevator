# Owner Decision Record 008: The `INVARIANT_VIOLATION` Halt Reason (Revision 7.2)

Status: **DECIDED AND ADMITTED 2026-11-05 by the owner.** This record admits a bounded semantic delta to the revision-7.1 baseline of [record 006](owner_decision_006_revision_7_1_admission.md) and the matching change to the plan admitted by [record 007](owner_decision_007_implementation_plan_admission.md). The result is revision 7.2. Records 006 and 007 are not rewritten; for the three files listed in §4 this record's digests supersede theirs.

## 1. Source

The independent cut-3 audit (supplied by the owner; `FAIL — CUT 3`) found
C3-I-02: engine corruption checks raised `EngineInvariantViolation` while
the Run stayed `RUNNING` and the engine stayed reusable. The repair stopped
because constitution §4.5 ("Terminate or halt ... any step that detects
corruption ... a named reason") and §14 ("Any of the following is
corruption, halts the Run") require a halt with a named reason, but no
admitted document named one ([cut-3 record §12.2](../implementation/cut_03_simulation_engine.md)).

## 2. Decision

> Add the admitted runtime halt reason `INVARIANT_VIOLATION`. When the
> engine detects a violation of an admitted runtime invariant during a
> tick: discard the entire failing tick; preserve all previously committed
> ticks; transition the Run to `HALTED`; commit exactly one `HALTED` event
> with the tick, the failing step, reason `INVARIANT_VIOLATION`, the
> relevant passenger and elevator where available, a diagnostic
> identifying the violated invariant, and the unserved count; make the Run
> final; later `step()` calls return the final outcome and perform no work.
> There are no separate halt reasons per invariant: `INVARIANT_VIOLATION`
> is the canonical reason and the specificity is in the diagnostic.

Owner, 2026-11-05.

## 3. Constitutional Delta

`ΔO = NONE / ΔS ≠ NONE / ΔA = NONE`.

- ΔS: one new halt reason in the engine's halt vocabulary, applying an
  existing constitutional rule (§4.5, §14) that had no name. No tick
  step, boarding, direction, termination, liveness or no-look-ahead rule
  changes; the rule is unreachable under a correct implementation.
- ΔO: none. No new object or standing; `HALTED` already exists.
- ΔA: none. The engine remains the only writer; the `HALTED` event is the
  existing run-standing Simulation Event; no new carrier, writer or
  selector.

## 4. Changed bytes (revision 7.2)

| File | Change | SHA-256 |
| --- | --- | --- |
| `docs/simulation_semantics.md` | §2 "Detected invariant violation" paragraph; §6 edge-case row; status line | `821cb89dbbd49ac0c44080f0eddc817ae2f8fece211d5a43f37f8b355d8fbd9d` |
| `docs/testing_contract.md` | new §1 row `detected_corruption_halts_the_run`; status line | `b0e78b99a824a0642f14adb45f9ac44e114fc40533ceae72259757b102d96001` |
| `docs/plans/implementation_plan.md` | cut 3 test list gains `detected_corruption_halts_the_run`; status line | `26f6920ee56c9ef17e053db7ad1f6ed5d2f15e5606258d60069648790d64c24e` |

Unchanged and still admitted at the digests of record 006:
`docs/constitution.md`, `docs/authority_model.md`, `docs/scheduler_design.md`,
`docs/evaluation_design.md`, `docs/cpoc_design.md`, `docs/ui_design.md`,
`docs/architecture.md`.

## 5. Admission

> I admit revision 7.2: the seven unchanged governing documents at the
> digests of record 006, and `docs/simulation_semantics.md` and
> `docs/testing_contract.md` at the digests above, as the governing design
> baseline; and the implementation plan at the digest above. Cut order and
> authorization are unchanged: cut 3 remains the current cut and cut 4 is
> not authorized until cut 3's independent re-audit passes.

Owner, 2026-11-05.

## 6. Propagation

The constitution already requires the halt (§4.5, §14) and needs no edit.
The UI and evaluation documents treat halted runs generically by reason
and need no edit. Worked examples are unaffected. Audits are evidence and
are not edited.
