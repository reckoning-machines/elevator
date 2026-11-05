# Owner Decision Record 012: UI Execution-Metadata Downloads (Revision 7.5)

Status: **DECIDED AND ADMITTED 2026-11-05 by the owner.** This record amends the admitted [UI design](../ui_design.md) of revision 7.4 ([record 011](owner_decision_011_ui_contract_reductions.md)). The result is revision 7.5. Earlier records are not rewritten; for `docs/ui_design.md` this record's digest supersedes theirs.

## 1. Source

The independent revision-7.4 re-audit found that live Experiment execution metadata was keyed by the logical Experiment id (repeated executions replaced it), and that the fixed Experiment page offered no execution-metadata download. The first is repaired ([cut-11 record §12](../implementation/cut_11_web_ui.md)). For the second, the fixed Experiment's committed evidence is `experiments/default_experiment_results.json` only: [decision 010](owner_decision_010_fixed_experiment.md) keeps execution facts out of it, and no execution metadata was ever persisted for it. Cut 11 reported that evidence gap rather than fabricate one.

## 2. Decision

> Do not create an execution-metadata artifact for the fixed Experiment. Live Experiment executions keep both downloads, with execution metadata keyed by execution-specific identity. The fixed committed Experiment exposes only its results (`default_experiment_results.json`) and states that no execution metadata was persisted for that committed evidence. Revise ui_design §3: Experiment result downloads expose the reproducible experiment-results artifact; execution-metadata download is additionally exposed when execution metadata was persisted for that execution; the UI must not reconstruct or fabricate execution metadata for committed evidence lacking such an artifact. Absence of operational evidence is represented as absence.

Owner, 2026-11-05.

## 3. Constitutional Delta

`ΔO = NONE / ΔS = UI-ONLY / ΔA = NONE`. A screen obligation is made conditional; no simulation, reporting, evaluation, scheduler or authority rule, no architecture dependency and no committed evidence changes.

## 4. Changed bytes (revision 7.5)

| File | Change | SHA-256 |
| --- | --- | --- |
| `docs/ui_design.md` | §3 downloads bullet (conditional execution-metadata download, no fabrication); status line | `8560cb3dfa77e5420296efbfc443630aeab1b51c9342e233a56fd01d91984c84` |

The complete admitted set at revision 7.5 (the others at the digests of record 011 §4, unchanged): constitution `b34958f91e6d…`, authority_model `4a066fb9fd8d…`, simulation_semantics `821cb89dbbd4…`, scheduler_design `25e7ec14ec3a…`, evaluation_design `b8c29a3d47b5…`, cpoc_design `65ca79366e4f…`, architecture `a38da7e42867…`, testing_contract `b0e78b99a824…`, plan `26f6920ee56c…`; full digests as listed in records 009 and 011.

## 5. Admission and scope of re-audit

> I admit revision 7.5: `docs/ui_design.md` at the digest above together with the other governing documents and the plan at their unchanged digests. Codex re-audits only the two download findings (live execution-metadata keying; fixed-Experiment downloads) against revision 7.5; no broad Cut 11 audit is required.

Owner, 2026-11-05.
