# Doctrine Adoption Record

Status: **ADOPTION RECORD. EVIDENCE OF WHAT WAS READ AND HOW IT WAS ADAPTED. NOT AN AUTHORITY. 2026-11-04.**

This record says which documents were read in sibling repositories under
`~/dev`, at which revision, which of their rules this project adopted, which
were adapted, and which were deliberately not adopted. The adapted rules
govern on their own terms in this repository's documents; nothing here
imports standing from the source repositories, and a later amendment there
does not bind this project until re-adapted here.

## 1. Sources read

Primary source: `~/dev/fin123-core` (IRIS) at `HEAD`
`5f083b8a10c128a8e7437ff58e96e1a911be8ace` (2026-11-04). The working tree
had 14 modified files, none of them listed below. "Last commit" is the last
commit touching the file; "digest" is the first 12 hex characters of
SHA-256 over the file as read.

| Source (relative to fin123-core) | Standing there | Last commit | Digest | Supplies |
| --- | --- | --- | --- | --- |
| `AGENTS.md` | current root router | `b925546f` 2026-10-13 | `375197e1cb56` | router shape: jurisdiction, authority rule, progressive disclosure, motion, pre-implementation authority gate, stop conditions, same-scope conflict, evidence versus authority, root-document jurisdiction |
| `docs/engineering_operating_contract.md` | current engineering operating contract (2026-08-16; CC amendment 2026-08-18) | `a83b1fb2` 2026-10-05 | `9fa7e5628cab` | the five rules; `Audit -> Plan -> Implement -> Verify` as working functions; authority sweep; Constitutional Delta with mandatory Authority Delta; constitutional stop condition; architectural budget; anti-metastasis; "server resolves semantic state, client resolves interaction state" |
| `docs/top_doctrines/iris_constitutional_coherence_doctrine.md` | current constitution (`CC-HD-001..006`) | `8caa4a63` 2026-08-27 | `3c50c596c2b1` | Constitutional Coherence; OSA; Authority Normal Form; the six representation classes; working/staged as lifecycle standing; the seven authority invariants; lawful change and migration rules |
| `docs/top_doctrines/iris_cross_process_operational_continuity_doctrine.md` | current companion conformance doctrine | `8caa4a63` 2026-08-27 | `018076296467` | the exact meaning of CPOC; its canonical lifecycle; the forbidden transient carriers; the negative invariants (transient-authority leakage, mutable-present substitution, resurrection, cross-surface disagreement, process-local continuation); applicability classification |
| `docs/top_contracts/iris_cpoc_certification_contract.md` | current conformance contract | `661c0a94` 2026-10-02 | `81c32f332b5d` | qualifying process boundary (distinct PIDs, signal, no transient inputs); boundary authority ledger; decision-surface parity; required negative witnesses; evidence record; standings vocabulary |
| `docs/top_doctrines/method_forward_evidentiary_doctrine.md` | controlling top doctrine | `0fc10231` 2026-08-12 | `a4c15a411f50` | commitment before outcome; a prediction fixed at commitment; outcome evaluates the prediction and never rewrites it; historical replay integrity |
| `docs/templates/iris_osa_cpoc_certification_section.md` | evidence template | `661c0a94` 2026-10-02 | `c92c17d1bf8b` | a prose `CERTIFIED` is not certification evidence; the applicability lines every record must carry |

Read for how the same doctrine was adapted to two earlier document-first
take-home or greenfield projects (shape only; no rule was taken from them
that is not in the fin123-core sources above):

| Source | Revision | Used for |
| --- | --- | --- |
| `~/dev/speedway/AGENTS.md`, `docs/decisions/fin123_core_adoption_20261018.md`, `docs/decisions/principal_decision_001_identity_and_evidence.md`, `docs/decisions/cv1_admission_20261019.md`, `docs/doctrines/new_speedway_constitution.md` Parts V to VII, `docs/audits/initial_osa_audit.md`, `docs/audits/cv1_whole_design_audit_checklist_20261019.md`, `docs/plans/document_first_design.md` | `76234ff` (2026-11-02) | the "documents-first, implementation not authorized until admitted" phase rule; the adoption-record format; the `ΔO/ΔS/ΔA` notation; directory jurisdiction wording; **the record shape the owner named as the analog** (2026-11-04): a `docs/decisions/` directory where each owner decision is a record with disposition, defect corrected, consequences and a two-case test; admission by SHA-256 digest of exact bytes; a transition-class table (who proposes, validates, decides, with budget); a representation table with bound-to and denied-rights columns; worked transitions including a crash-and-recover trace; an independent whole-design audit checklist with graded A/B/C disposition |
| `~/dev/equi/AGENTS.md`, `docs/governance/standards_adoption.md`, `docs/governance/cpoc_conformance.md`, `docs/governance/authority_register.md` (§1-9) | `7696a74` (2026-10-23) | a take-home-scale CPOC witness with one interruption; an authority register written before code; the "owner" vocabulary |

## 2. Generic engineering doctrine adopted (and where it lives here)

| Rule | Home here |
| --- | --- |
| Every consequential fact has one lawful owner and one commit boundary; every other copy is classified and has no decision right ("duplication of representation is permissible; duplication of authority is not") | [constitution.md](constitution.md) §3; [authority_model.md](authority_model.md) |
| The six representation classes, exactly, and the rule that lifecycle standings are not classes | [authority_model.md](authority_model.md) §1 |
| The authority invariants: singular decision authority, classified representation closure, exclusive commit boundary, temporal and binding closure (history never from mutable present), owner-resolved consumption (no consumer reconciles), legacy isolation, failure closure (ambiguity fails closed) | [constitution.md](constitution.md) §5, §6, §7, §14 |
| OSA as the question "is this exact state or transition lawful"; CPOC as "does that lawful authority survive process death"; CPOC subordinate, creating no authority | [constitution.md](constitution.md) §13; [cpoc_design.md](cpoc_design.md) §1 |
| CPOC's canonical lifecycle, forbidden transient carriers and negative invariants | [cpoc_design.md](cpoc_design.md) §1, §3, §6 |
| Qualifying process boundary: real termination, distinct PIDs, fresh process receives only durable coordinates and ordinary configuration; same-interpreter recreation is not process death | [cpoc_design.md](cpoc_design.md) §4; [testing_contract.md](testing_contract.md) §5, §7 |
| Boundary ledger, negative witnesses, evidence record, standings (`OSA PASS/FAIL`, `CPOC PASS/FAIL`, `IMPLEMENTED NOT CERTIFIED`, `STOPPED`) | [cpoc_design.md](cpoc_design.md) §5 to §8 |
| `Audit -> Plan -> Implement -> Verify` as working functions; audit sweep follows the fact; Plan carries one Constitutional Delta with the Authority Delta; Implement bounded by the admitted Plan; Verify reconciles the actual delta and classifies OSA/CPOC applicability | [AGENTS.md](../AGENTS.md) "Engineering motion"; [plans/implementation_plan.md](plans/implementation_plan.md) |
| The constitutional stop condition and the rule never to resolve ambiguity by implementation, persistence, precedence, latest-value or test success | [AGENTS.md](../AGENTS.md) "Stop conditions", "Same-scope conflict handling" |
| Server resolves semantic state; client resolves interaction state; the browser never owns product truth | [ui_design.md](ui_design.md) §1, §6; [authority_model.md](authority_model.md) row 36 |
| Delete first; optimise the coherent system; verify behaviour and architecture together | [AGENTS.md](../AGENTS.md) "Scope control"; [architecture.md](architecture.md) §7 |
| Anti-metastasis: no subordinate process doctrine; amend the governing document directly | [AGENTS.md](../AGENTS.md) "Documentation update obligations"; the compact document set |
| Commitment before outcome: an estimate committed at decision time is a receipt; the realized outcome evaluates it and never rewrites it | [scheduler_design.md](scheduler_design.md) §1, §6.5, §9; [constitution.md](constitution.md) N9 |
| Audits are evidence; a plan authorizes nothing until admitted; prose is not certification | [AGENTS.md](../AGENTS.md) "Directory jurisdiction"; [cpoc_design.md](cpoc_design.md) §8 |
| The `Status:` line convention at the top of every document | every document here |

## 3. Deliberate adaptations

| Adaptation | Reason |
| --- | --- |
| "Owner" means the person who commissioned the project (the author of the take-home); "Principal" and "analyst" are not used | one person, one role |
| The future Authority Topology that fin123-core defers is small enough here to write in full before code: [authority_model.md](authority_model.md) | 42 rows at revision 6 |
| No G1 semantic-authority register; precedence is the fixed list in [AGENTS.md](../AGENTS.md) | the document set is small enough to order directly |
| The Constitutional Delta is stated once per document and per plan cut, in prose. Owner decisions and admissions are records in `docs/decisions/`, one record per batch of questions, admission naming files and digests (speedway's shape); no numbered `PD` series beyond what the project needs | one owner; exact admitted bytes |
| CPOC is scaled to one boundary class (between ticks), one continuation document per run in a store, one witness and the negative witnesses of cpoc §6 | proportionate to a take-home; one real restart proves the principle |
| Certification vocabulary kept, but "CERTIFIED" here means only "the named tests and the CPOC witness passed for the affected boundary at an exact SHA" | no deployment lane exists |
| "Same lawful continuation" is byte-identical history here (no nondeterministic provider) | stronger than the source because the system is deterministic |
| The engineering contract's frontend material is reduced to the UI document's §1 and §6 | the UI is a few fragments |

## 4. Not adopted (product-specific to IRIS)

- IRIS product ontology: Workspace, Repository, Model, ModelDocument,
  Working, W1, Version, Branch, HEAD, Method, Formula, Application, R3, R4,
  Run, Result, Rail, PM, Publication.
- The G1 register and its `SA-nnn` rows; known contradictions.
- The AAPL reference witness, the four-restart decision-surface matrix, the
  closed CPOC registry, `scripts/certify_consequential_change.py`, scoped
  and consequential lanes, receipt validator pins, certification tiers and
  cadence.
- The Deployment Certification Contract (historical-prefix upgrade,
  fresh install, real-workbook E2E).
- The knowledge-evolution control architecture, Earned Intelligence,
  Methods doctrines, Provider doctrine, SBCLEMG.
- Historical plans, audits, implementation records and current-work content.
- Speedway's investment ontology and Equi's allocator ontology.

## 5. What this record does not do

It grants no authority and admits nothing. It records what was read and how
it was adapted.
