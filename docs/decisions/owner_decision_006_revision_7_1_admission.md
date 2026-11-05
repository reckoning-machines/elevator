# Owner Decision Record 006: Admission of the Governing Design, Revision 7.1

Status: **ADMITTED 2026-11-05 by the owner.** This record is the owner's act. The independent closure record [audits/independent_revision_7_1_closure_audit.md](../audits/independent_revision_7_1_closure_audit.md) (`OSA PASS — BOUNDED CLOSURE COMPLETE`) is evidence supporting admission; it is not the admission. The implementation plan is admitted separately in [owner_decision_007_implementation_plan_admission.md](owner_decision_007_implementation_plan_admission.md).

## 1. Verification performed before the act

- The nine governing documents' SHA-256 digests were recomputed in the
  working tree on 2026-11-05 and match the proposed revision-7.1 table of
  [decision 005 §4](owner_decision_005_revision_7_1_mapping.md) exactly.
- The closure audit's standing section reports that it recomputed the same
  nine digests and found them matching.
- No governing document was edited to perform this admission; their status
  lines still read "DRAFT, NOT ADMITTED", and this record supersedes those
  lines by design so that the admitted bytes stay exact.

## 2. Adoption of the pending dispositions

The owner adopts the pending owner dispositions incorporated into revision
7.1 as refined by the successive decision records: D-11, D-12 and D-13 of
[record 002](owner_decision_002_revision_5_repairs.md); D-15 to D-22 of
[record 003](owner_decision_003_revision_6_repairs.md); D-23 to D-28 of
[record 004](owner_decision_004_revision_7_closure.md); and the component
mapping of [record 005](owner_decision_005_revision_7_1_mapping.md). D-08,
D-09, D-10 and D-14 of record 002 are adopted only as superseded and
refined by records 003 to 005. Where the wording of an earlier proposal
differs from a later record, the latest record controls. D-01 to D-07 of
[record 001](owner_decision_001_design_choices.md) were decided on
2026-11-04 and are unchanged. Historical records are not rewritten.

## 3. Admission text

> I adopt the pending owner dispositions incorporated into Revision 7.1 as
> refined by the successive decision records.
>
> I admit the exact Revision-7.1 governing-document bytes at the SHA-256
> digests recorded in this admission as the governing design baseline.
>
> Future ontology, semantic or authority changes require the repository's
> declared delta and decision process.

Owner, 2026-11-05.

## 4. The admitted bytes

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

## 5. Consequences

- The governing design baseline is revision 7.1 at these digests. A change
  to any of these files is a new revision, with its Constitutional Delta
  declared and decided under [AGENTS.md](../../AGENTS.md); the admitted
  bytes are not edited in place.
- Implementation is not authorized by this record. It is authorized only by
  the separate plan admission in record 007, and then cut by cut.
- Nothing is certified; no CPOC witness has run; the standing vocabulary of
  [cpoc_design.md](../cpoc_design.md) §8 and the plan's staged standings
  apply unchanged.
