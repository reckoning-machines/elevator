# Owner Direction Record 005: Revision 7.1 Component Mapping

Status: **OWNER-DIRECTED DOCUMENT REPAIR, 2026-11-05. DESIGN AND PLAN NOT ADMITTED.** This records the owner's instruction following the independent revision-7 closure audit. It changes the component mapping and two references only. It does not decide the outstanding substantive proposals in records 002–004 or admit any baseline.

## 1. Direction and scope

The owner directed revision 7.1 rather than another whole-design revision:
use a small neutral `operations.py` for Execution identity and Operational
Log mechanics; align architecture imports and cuts 8–9; correct the
verifier lifetime and W-D resume sequence; regenerate digests; then review
only R7-I-01, R7-I-02 and whether the relocation introduces an authority
owner. The agent performing this amendment is its author, not its
independent closure auditor.

Source: the owner's instruction of 2026-11-05 and
[independent_revision_7_closure_audit.md](../audits/independent_revision_7_closure_audit.md).
Records 001–004 and all completed audits remain unchanged.

## 2. Component mapping

`operations` depends only on domain and the standard library. It supplies
the operational Execution handle, execution_id, OperationalLog, op_seq,
append, bind_evidence_root and flush_unflushed_prefix. It owns no
simulation state, checkpoint semantics, Store authority or scheduler rule.

- API invokes operations for Execution creation and the initial log.
- Reporting's execution-output wrapper invokes operations for output-only
  batch evidence binding. Metric calculations do not read the log.
- Checkpoint chooses the lawful Store location and invokes operations on
  that same Execution log for binding, resumed sequence and receipts.
- The executing process remains the authority owner. The new module
  implements the existing boundaries; it is not another owner.
- The checkpoint module retains Store/Continuation Document handling,
  write admission and load verification. API does not depend on it.

The exact mapping is [architecture §1.1](../architecture.md). Cut 8
delivers operations; cut 9 consumes it without moving its implementation.
Cut 6's reporting remains independent of the later operational wrapper.
Existing code-identity rules automatically cover operations.py as a
governed package source file when implementation is later authorized.

## 3. Reference corrections and delta

Authority row 38 now retains HistoryVerifier through comparison step 11,
discarding it before state construction. W-D includes B's
EXECUTION_STARTED before LOAD_ADMITTED and RESUMED, with continuous
operational sequence numbers; Simulation History is unchanged.

Constitutional Delta: `ΔO = NONE / ΔS = NONE / ΔA = NONE`.
No new fact, authority carrier, writer, selector, lifecycle, refusal,
scheduler behavior or continuity assurance claim is introduced. This is
an implementation mapping and reference correction. Liveness and source
contracts are unchanged.

## 4. Exact revision-7.1 bytes proposed for later admission

These hashes identify the revised documents; this table is not admission.

| File | SHA-256 |
| --- | --- |
| `docs/constitution.md` | `b34958f91e6d4c5fc32f74fe96be14b6287ca80abdde951e77eb2e730cb659c3` |
| `docs/authority_model.md` | `4a066fb9fd8d85ffa9175501fddf9992cdaa42e8f644ffa07893847f7daf384e` |
| `docs/simulation_semantics.md` | `94a3506932df8e00d663fd64d0f929970d83896e969010ffcf270ce1dcafeb87` |
| `docs/scheduler_design.md` | `25e7ec14ec3a46127430ca4d0bdd9e01d46d0ba1024d3ee10bbbf54cbddba881` |
| `docs/evaluation_design.md` | `b8c29a3d47b5be8fce9f517f931bb6848508a0a595254ff8187832cbeb7c1fa1` |
| `docs/cpoc_design.md` | `65ca79366e4f5a6c970ba2c59a0f01ff976519840e6219a5de26aa5f6e566d58` |
| `docs/ui_design.md` | `b22ea1164403bebc733aba986dea5b25b5ee9ad6e12e3e55a55cfb146382366c` |
| `docs/architecture.md` | `31f16b7d18cdd8cbfdf18df6a94de57fc061ff413291789836d4b5fe673ab9e6` |
| `docs/testing_contract.md` | `9c03308ab1f0df65a8f2540d77a20168b301e66d8b095dc4af106206841d602b` |

The separate, unadmitted plan's SHA-256 is
`6254fffaea4c48582ae20733a5995ca6511a24f9d057de0e84efabfb82138d84`.
It is not included in any governing-document admission.

If the bounded review passes, the owner may record admission of these
exact bytes and separately decide/confirm the pending substantive
dispositions from records 002–004. Implementation remains unauthorized
until subsequent, separate plan admission. This document contains no
executed admission text.

## 5. Remaining independent review

Ask only:

> Is R7-I-01 closed, is R7-I-02 corrected, and did this relocation
> introduce any new authority owner?

Use [revision_7_1_repair_record.md](../audits/revision_7_1_repair_record.md)
as author evidence, not an independent verdict. No full audit, simulation
implementation or stronger assurance exercise is requested.
