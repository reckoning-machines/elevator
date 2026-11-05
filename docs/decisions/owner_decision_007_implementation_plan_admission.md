# Owner Decision Record 007: Admission of the Implementation Plan

Status: **ADMITTED 2026-11-05 by the owner.** This record is the owner's act admitting [plans/implementation_plan.md](../plans/implementation_plan.md) at the exact bytes below, against the governing design baseline admitted in [record 006](owner_decision_006_revision_7_1_admission.md).

## 1. Inspection performed before the act

The plan was inspected only for consistency with the admitted revision-7.1
baseline; no design audit was repeated.

| Check | Result |
| --- | --- |
| Cut 1 is first | Yes: "1. Domain model, input normalization, code identity" |
| Cut ordering is internally schedulable | Yes: cut 3 uses a stub policy and reads no written file; cut 6 depends on 3; cut 8 on 6 and 7; cut 9 on 3, 6 and 8; cut 10 on 9; cut 11 on 6, 8 and 9; cut 12 on everything; the cut-local dependency rule names only tests whose inputs earlier cuts produce |
| Cut 8 owns `operations` and public API integration | Yes: `elevator/operations.py`, `elevator/api.py` (`simulate`, `create_engine`), harness and CLI are cut 8's expected files |
| Cut 9 reuses `operations` and adds Store and continuity | Yes: cut 9 binds the same log through `operations` and adds Store creation, write admission, the loader and the continuation types; "no operations code is relocated into checkpoint in cut 9" (architecture §8) |
| No `api -> checkpoint` dependency | Yes: architecture §1 lists checkpoint under what `api` must not depend on; cut 8 writes no document |
| Exact test identifiers resolve to the testing contract | Yes: every backticked test identifier in the plan's test column appears in [testing_contract.md](../testing_contract.md) (checked by script on 2026-11-05; the only unmatched token, `next_heading`, is a function reference) |
| Local verification and CPOC qualification remain distinct | Yes: `IMPLEMENTED / LOCAL VERIFY PASS`, `/ CPOC PENDING` and `/ CPOC-QUALIFIED` are defined and the project cannot be called complete before cuts 3, 9 and 11 are `CPOC-QUALIFIED` |

## 2. The admitted plan

| File | SHA-256 |
| --- | --- |
| `docs/plans/implementation_plan.md` | `6254fffaea4c48582ae20733a5995ca6511a24f9d057de0e84efabfb82138d84` |

Admitted governing baseline: revision 7.1, at the digests of record 006.

## 3. Admission text

> I admit the implementation plan at the SHA-256 above against the
> revision-7.1 governing baseline. The twelve cuts are accepted in their
> stated order. Implementation is authorized beginning with Cut 1 only;
> each later cut becomes eligible only when the preceding cut has reached
> its verified standing. No cut may be skipped or silently broadened; a
> cut that needs a fact, carrier, writer, selector or transition the plan
> does not name stops and returns to the decision process. Local
> verification (`IMPLEMENTED / LOCAL VERIFY PASS`) does not imply CPOC
> certification; cuts 3, 9 and 11 carry `CPOC PENDING` until the cut-10
> witness passes for the code identity that includes them.

Owner, 2026-11-05.

## 4. Consequences

- The plan's status line ("PROPOSED PLAN. NOT ADMITTED.") is superseded by
  this record; the plan's bytes are not edited so the admitted digest
  stays exact. A change to the plan is a new plan revision requiring a new
  admission record.
- Repository standing becomes: phase IMPLEMENTATION; governing design
  ADMITTED (revision 7.1); implementation plan ADMITTED; implementation
  AUTHORIZED; current authorized cut: Cut 1.
