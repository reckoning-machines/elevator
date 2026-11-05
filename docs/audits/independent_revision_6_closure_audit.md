# Independent Revision 6 Closure Audit

## Standing

- Date: 2026-11-04.
- Subject: revision 6 in `/Users/jedgore/dev/elevator`, the supplied workspace for `/dev/Elevator`.
- Role: independent closure auditor, not the revision-6 author. This is a bounded closure review, not another unrestricted whole-design audit.
- Scope: R5-I-01 through R5-I-16, the authority/semantic delta introduced by revision 6, preservation of the established liveness bound, and admission readiness. Previously closed revision-4 mechanics are not reopened.
- Assurance: the standard in cpoc §4.1 is accepted. No executable attestation, cryptographic causal-provenance proof, protection against deliberate non-writer Store overwrite, or detection of intentionally hidden dynamic-dispatch violations is demanded.
- Standing: documents/design only; implementation and plan admission remain unauthorized. Decision 003 is proposed, not decided or admitted. This audit evaluates the proposed baseline and grants no authority.
- CPOC: **NOT APPLICABLE — DESIGN ONLY, WITNESS NOT IMPLEMENTED**.

Reviewed: AGENTS.md, README.md, all nine current revision-6 design/obligation documents named in decision 003, current_work, assumptions_and_tradeoffs, worked_examples, doctrine_adoption, decisions 001–003, the independent revision-4 and revision-5 audit records, revision-5 and revision-6 repair records, the current checklist and implementation plan. Historical findings were used as closure inputs, not as a license to re-audit unchanged architecture. Worked examples, tests, repair assertions and current_work were not treated as semantic authority.

The nine SHA-256 entries in decision 003 §4 match the reviewed files. Relative Markdown links resolve. The final comparison against the captured baseline confirmed all 25 pre-existing repository files unchanged and this audit as the sole new file. No application code, test code, runtime artifact or patch file was created or executed. Review used document reads, targeted searches, hashing, hand calculations and in-memory PDF rendering.

The original PDF was inspected directly for preservation of the changed public boundary, output classification and domain assumptions: `/Users/jedgore/Downloads/Take_home_Elevator_(2).pdf`, SHA-256 `b6eb161d9716d16236dfeaa0a8056319a7acf3d6994d5994ed5f132087b9c007`. No PDF/image artifact was written.

## Executive disposition

**OSA FAIL — C, STRUCTURAL GAP**

R5 closure: **8 CLOSED / 8 PARTIAL / 0 OPEN**.

New/residual findings recorded here: **0 HIGH / 6 MEDIUM / 1 LOW**.

The original HIGH concerns about global Run finality, bounded executing-code identity, snapshot consumption, and missing transition classes are substantially resolved. The typed boundary and package-wide architectural tests are sufficient for the explicitly bounded accidental-defect standard; equal hashes are no longer misrepresented as proof of causal provenance. No stronger threat model is used to fail this revision.

Admission is still blocked by ordinary, concrete inconsistencies: an execution with no output location has no permitted Operational Log carrier; a stale-writer witness never advances the durable sequence before its attempted write; accepted sparse parameters produce an out-of-domain Trace; Experiment equality still includes random execution IDs; empty-run metrics contradict aggregation classification; and cut 9 demands later witness/UI capabilities. These are MEDIUM under this task's severity rules. The OSA FAIL disposition follows the user's explicit rule that any unresolved HIGH/MEDIUM blocks admission; it does not imply a newly discovered HIGH authority breach.

The previously established bound **`T_last + 2P(F-1)` remains established**. Revision 6 changes deferral classification without changing which passengers board or how a car moves. The corrected boundary invariant and event-count wording preserve the prior argument.

## R5-I-01 through R5-I-16 closure table

“CLOSED” means closed as a design obligation under the stated assurance standard, not implemented or verified by executed tests. “PARTIAL” distinguishes a repaired original example from a remaining adjacent defect or inconsistent obligation. R5-I-11's remaining defect is LOW: its original HALTED-history semantics are repaired.

| Finding | Revision-6 repair | CLOSED / PARTIAL / OPEN | Adversarial closure test | Evidence |
| --- | --- | --- | --- | --- |
| R5-I-01 — Finality scope/write admission | Logical Run versus random Execution identity; document keyed by execution_id; sequence-token admission; distinct in-memory outcome and durable finality | CLOSED | Original: complete one execution in S1 and resume a separately checkpointed execution of the same run_id in S2. This is now expressly lawful, not resurrection. Adjacent: checkpoint/finality writes after a final document refuse WRITE_AFTER_FINAL; an older token against a later RUNNING sequence refuses STALE_WRITER. Before final rename, last RUNNING authority survives; after rename, final authority survives even with no outputs. Assumes the stated single-writer/no-concurrent-access model; no global finality registry is demanded. | constitution §§2, 4.3, 4.5/N13; authority rows 17/17a/37; cpoc §§2.1–2.4, 3.2–3.4, 5 step 7. A defect in the test construction, not this admission predicate, is R6-I-02. |
| R5-I-02 — Bounded code identity | Hash every governed .py file before Run creation; bytecode writing disabled, no package __pycache__, lifetime source immutability, exit drift detection, no override | CLOSED | Original timestamp-valid package cache is outside the supported contract and causes entry refusal. Adjacent: start without the required flag, or modify governed source during a supported process: named environment refusal or CODE_IDENTITY_DRIFT invalidates evidence. The public boundaries are covered by authority §2 even though architecture lists representative executable entry points. No supported equal-identity/different-governed-source case was found. | constitution §12/N17; authority §2/row 4; architecture §4; testing §6 execution_environment_contract and code_identity_tracks_package_bytes; cpoc §6 rows 15–16. `-B` alone is not assumed to prevent cache reads: absence of package caches is the second necessary condition. External-cache/bypassed-entry and malicious-replacement cases expressly excluded by the repair posture are not reopened. |
| R5-I-03 — Snapshot consumption | Distinct Snapshot, HistoryPrefix and HistoryVerifier types; only parse_snapshot produces Snapshot; constructor rejects other types; both packages scanned; planted cheat required | CLOSED | Original validate-then-fold helper returning a snapshot-shaped dictionary fails the runtime type boundary. Adjacent: an ordinary helper returning a real Snapshot or EngineState from History elsewhere in the package violates the whole-package call/data-flow restriction and must be caught by the planted-cheat test. Verifier state cannot escape into the resumed engine. Hashes are explicitly value-equality evidence only. | constitution N14/§13; cpoc §§4.1, 5.1–5.2; testing §7 no_history_to_state_path_in_package/history_verifier_isolated; authority rows 25/38. No demand for protection against deliberate reflection or hidden dynamic dispatch. |
| R5-I-04 — Operational receipt commit/hash | Separate append-only log; write→hash final bytes→append→flush; execution_id/op_seq binding; missing receipt affects evidence only | PARTIAL | Original embedded self-hash and receipt-lost-before-document contradiction are closed. Adjacent: default simulate(output_dir=None), or New run with no output and no checkpoint controls, must still append EXECUTION_STARTED but has neither permitted file location. Later interactive checkpointing also changes the prescribed log location without a defined carrier transition. | cpoc §§2.2–2.4, 3.1–3.3; authority row 26; evaluation §§2, 3.2; UI §2.1. R6-I-01. |
| R5-I-05 — Negative-witness ordering | Explicit mutation/hash/binding/earlier-step columns; schema omissions fail at 2; future mutation moved to a second lawful Run | PARTIAL | Original heading mutation now recomputes snapshot_hash and reaches 11; un-rehashed variant deliberately fails at 9. Missing heading fails at 2; forged recorded load with repaired history_hash reaches 10. Adjacent stale-writer row 9 expects sequence >=2 while B is still running, but B has no checkpoint controls and writes sequence 2 only at finality. It therefore cannot produce its stated STALE_WRITER result as constructed. | cpoc §5; §6 rows 1, 3, 9–10, 17–19, 25; testing §§3, 7; W-D. R6-I-02. |
| R5-I-06 — Historical load checking | Isolated route-law verifier checks every consequential TickRecord field | CLOSED | Original intermediate load=C+1 mutation, with recomputed history_hash and unchanged events/snapshot, disagrees with verifier onboard count and refuses at 10. Adjacent: alter heading, boarded IDs or alighted IDs consistently enough to preserve JSON types: replay of shared route mechanics rejects the field mismatch, including wrong-way boarding. Verification working state is a distinct discarded type, not recovery authority. | cpoc §5 steps 10–11/§5.2 and §6 rows 25–27; authority rows 18/38; testing §7. |
| R5-I-07 — Deferral classification | Direction incompatibility evaluated before capacity; one shared primitive and observation rule | CLOSED | Original full-and-wrong-way W-F tick 2 is direction-only; compatible-full W-B tick 2 is capacity-only. Adjacent: a FREE car has each prospective direction until the first fitting passenger boards; after that a full opposite-direction passenger is direction-only. The declared synthetic FREE/full primitive case stays FREE and is capacity-only. Tier classification uses only capacity deferral. | semantics §4.2/§5; scheduler §5/§6.2/§7; authority row 22; testing §1 deferral_classification_direction_first; W-F. W-D's unrelated erroneous label is bounded in R6-I-07. |
| R5-I-08 — Generator domains | F/N/C/request/horizon/seed bounds; fixed lobby share; named pattern parameter rejection | PARTIAL | Original F>2^53 set case is now refused; p_lobby is no longer accepted, so there is one peak algorithm. Within F<=200, consecutive SplitMix draws reach each needed floor and duplicate-redraw loops terminate. Adjacent accepted sparse combination num_requests=1002, g=10^6, j=0 emits time 1,001,000,000, exceeding the new 10^9 public-input limit. No cross-parameter refusal is stated. | evaluation §§2, 6.1–6.3; testing §6 generate_refuses_invalid_parameters. R6-I-03. |
| R5-I-09 — Reproducible output surface | Eight named Run-only files; execution metadata/Operational Log excluded | PARTIAL | Original README-only Git change and differing informational Scenario provenance no longer affect a surface byte; distinct execution_ids are excluded. Adjacent Experiment reexecution writes new execution_ids into experiment.json, while its named acceptance test still demands byte-identical experiment.json. The Run-level contract is repaired; its propagated comparison obligation is not. | constitution P8/P12/N18; evaluation §§3, 7.3–7.4; testing §4 experiment_reexecution_identical. R6-I-04. |
| R5-I-10 — Nullable aggregates | Defined-value filtering, n_defined/n_pairs, halt counts and pair denominators | PARTIAL | Original no-wrong-way metric now aggregates null→null with n_defined=0, rather than dividing or treating null as zero. Adjacent empty completed run: §4.3 emits null deferred.count, wrong_way.count and tail_share, but §7.4 classifies them always defined and explicitly makes empty tail_share zero. Two competent implementations disagree on n_defined and paired participation. | evaluation §§4.3, 7.4; testing §6 experiment_null_aggregation/empty_population_summary. R6-I-05. |
| R5-I-11 — HALTED history availability | Availability derives from committed TickRecords; NO_HISTORY when none | PARTIAL | Original W-E halt at 0 now has no historical record and returns NO_HISTORY. Adjacent later halt k exposes only records through k−1, as required. The remaining adjacent creation case is correctly governed by NO_HISTORY but history_at_creation still expects HISTORY_TICK_NOT_AVAILABLE. Both are 404 and neither permits current-state substitution; residual is LOW propagation, not an unresolved history authority rule. | UI §2.2; W-E; testing §8 history_halted_range/history_at_creation. R6-I-07. |
| R5-I-12 — Plan prerequisites | Engine-local cut-3 list, export cut 6, exact names restored, Store init moved to 9, staged qualification retained | PARTIAL | Original cut-3 export dependency and missing checkpoint-at-zero test are closed. Adjacent revised cut 9 now requires every cpoc §6 witness exactly as written: row 29 uses the UI delivered in cut 11, and row 31 needs the qualification harness of cut 10. Cut 1 also places Snapshot before the checkpoint module to which its governing type contract assigns it. | plan Rules/Order/cuts 1, 3, 6, 9–11; cpoc §§5.1, 6 rows 29/31; testing §§1–2, 7. R6-I-06. |
| R5-I-13 — Transition classes | Code/Store/Execution/Operational append/Experiment execution classes; distinct simulation outcome versus durable standing; schema and IDs registered | CLOSED | Original store init and process identity have named classes; original double assignment of final document mutation is removed. Adjacent two processes continuing one Execution keep execution_id, increment op_seq and use the document token; PID reuse is not its identity. Creation/load invoke Operational Log append for receipts rather than defining an independent receipt owner. Store schema has its own constant/refusal. | constitution §§2, 4.3, 4.5; authority §2/rows 5, 17a, 26, 33, 37; cpoc §§2.4, 3, 5 step 1. Remaining log-location lifecycle is separately R6-I-01, not a reopened class-inventory finding. |
| R5-I-14 — Liveness wording | Weakly ahead at boundary, equality alights in step 3, survivors strictly ahead; count events and distinct progress ticks separately | CLOSED | Original F=2 passenger arriving at its destination is correctly weakly ahead, not a strict-boundary counterexample. Adjacent simultaneous alight/board events share a tick and do not increase the bound. No changed boarding/motion mechanics invalidate the established proof. | semantics §8.2; constitution P10; checklist 10. Preservation check below. |
| R5-I-15 — Active stale references | Main invariant/authority references, routing, attribution and horizon language corrected | PARTIAL | Original N15/N16, route-row, immutable-assignment attribution, calibration and reported-email cases are repaired. Targeted P11/P12 search still finds checklist 5 attributing travel-equals-distance to P12; UI §6 retains the original N8/N10 authority references. Historical decision/audit wording is correctly left alone. | repair record R5-I-15; scheduler §§1, 4.1, 6.3, 8–9; assumptions §§1–3; README §3; current_work §2; checklist 5; UI §6. R6-I-07. |
| R5-I-16 — Batch/live boundaries | Shared normalization, batch simulate, separate live create_engine; web checkpoint/reopen delegation explicit | CLOSED | Original New run→complete SimulationResult path is prohibited. Adjacent same input rows yield equal normalized Trace and first tick through both APIs, without a second simulator; web reaches create_engine and checkpoint only for the declared actions. Execution evidence-location concerns are isolated in R6-I-01, not conflated with the repaired engine lifecycle. | evaluation §2; architecture §1; UI §2.1; authority row 41; testing §§1, 8; plan cut 8/11. |

## Revision-6 authority delta

This is a delta sweep, not a repeat of the earlier 36-row inventory. Owners and classes of unchanged simulation state are not re-litigated.

| Changed fact | Owner / class | Transition and persistence | Denied rights and result |
| --- | --- | --- | --- |
| execution_id | Executing process; AUTHORITATIVE operational identity | Execution creation; persisted in document/path/log/metadata; retained across process resumes | Cannot enter run_id, Simulation History, scheduler input or reproducible outputs. Registration closed: constitution §2/§4.5, authority row 37 |
| write_sequence / last-known writer token | Process/document; AUTHORITATIVE durable sequence, process retains the admission token read at load or last write | Checkpoint/finality write; begins at 1 and increases; loader restores token from document | No stale or post-final replacement; token never decides a simulation event. Predicate closed under one-writer model; witness construction incomplete, R6-I-02 |
| Store/Execution/Run binding and standing | Store owns its ID; process owns Execution/document; Run remains deterministic identity | Store creation; Execution creation/binding; load verifies both coordinates and input hashes; finality write commits Execution standing | Output root cannot select standing; another Execution of the same Run is independent. Closed for already-bound executions |
| Code identity and supported-environment status | Process; AUTHORITATIVE established source identity under contract; checks/drift evidence | Code identity establishment before Run; log/metadata record evidence; fresh loader recomputes; no override | No claim outside supported environment; sources immutable for process; exit drift invalidates evidence. Bounded registration closed |
| Operational Log op_seq and receipt bytes | Process; RECEIPT identity (execution_id, op_seq) | Separate append-only file; append after document rename/hash; resume continues last op_seq | Never establishes/admit simulation state, never enters deterministic surface. Owner/class are named, but output-free and late-binding carrier lifecycle is incomplete, R6-I-01 |
| Reproducible output classification | Reporting; DERIVED from Run inputs/records | Output rendering; eight named files regenerated per Execution | No execution facts; metadata is informational RECEIPT outside equality. Run-level classification closed; Experiment test propagation fails, R6-I-04 |
| n_defined, n_pairs, halted_count, win/tie/loss population | Harness; DERIVED Experiment result facts under authority row 34 | Experiment execution/aggregation; persisted as results and regenerated | Cannot change a Run or silently turn null into zero. Ownership closed, empty-run semantics contradictory, R6-I-05 |
| Normalized Trace and batch/live input boundary | Trace load; DERIVED normalization then immutable authoritative Trace | Shared normalize_requests; both API paths use same engine, immutable inputs carried in snapshot document | Neither UI nor batch has a second parsing/simulation rule. Closed, authority row 41 |
| Isolated HistoryVerifier working state | Loader; EPHEMERAL distinct verifier type | Created during verification, compared only to validate, discarded before state construction | Cannot convert/feed resumed engine or Snapshot. Closed within bounded call-graph standard |

**Delta disposition: not fully closed.** The named owners and new transition classes exist and the old finality split is sound. The new log carrier does not cover every expressly supported lifecycle, and new aggregate semantics still contradict their inputs. This does not call for an additional platform or attestation mechanism; it requires complete rules within the chosen boundaries.

The transition review specifically checked Code identity establishment, Store creation, Execution creation, Operational Log append, Terminate or halt, Finality write and Experiment execution. The first six no longer have the original omitted-class/double-finality defect: the simulation outcome and document standing are distinct facts. Aggregate counters belong to Experiment execution, not a new runtime authority. A receipt append invoked at creation/load remains the Operational Log append boundary identified in authority §2 and row 25.

### Current-checklist application within the closure scope

The checklist does not expand this user-authorized audit into a new generic review. Its current checks map as follows; “preserved” retains prior conclusions on unchanged mechanics, rather than claiming new executed evidence.

| Checks | Bounded result |
| --- | --- |
| 1, 19 | Delta/propagation incomplete: R6-I-01, R6-I-06–07; nine admission digests and relative links pass |
| 2–4, 11–12, 15–17, 20, 25 | Preserved; no changed mechanic/source or standing regression identified in the required closure comparisons |
| 5 | Direction-first classification closes R5-I-07; its P12 cross-reference is LOW stale text |
| 6 | Corrected second-Run future mutation stays lawful; no checkpoint-binding obstacle; decision/motion surface preserved |
| 7, 30 | Run-level equality repaired; Experiment equality obligation still inconsistent, R6-I-04 |
| 8, 23–24, 34–35 | Bounded source/snapshot architecture acceptable; CPOC remains unimplemented; exact negative-witness obligations still need R6-I-02 |
| 9, 14 | Selected refusal fixtures mostly reach the intended step, but stale-writer construction and creation-history expected reason remain inconsistent |
| 10 | Established numerical bound preserved; phase-aware invariant repaired |
| 13, 31 | Historical source and HALTED range repaired; LOW test propagation remains, R6-I-07 |
| 18, 26 | Fixed lobby rule/individual bounds repaired; sparse cross-parameter range not closed, R6-I-03 |
| 21, 27–28 | Logical Run/Execution/finality/write-admission rules closed within the single-writer model; row-9 witness has a separate construction defect |
| 22, 29 | Separate log removes self-hashing and allows missing-receipt evidence failure without losing authority; supported log-location lifecycle remains incomplete |
| 32 | Conditional nonempty and halted populations defined; empty-run classification contradicts summary, R6-I-05 |
| 33 | Batch/live engine and normalization split repaired |

## New findings

### R6-I-01 — Operational-log carrier is undefined for output-free and late-checkpoint executions

Severity: MEDIUM

**Closure relation:** R5-I-04 PARTIAL; introduced by D-18's separate-file carrier interacting with D-22's supported public/live boundaries.

**Governing evidence:** constitution §4.5 Execution creation; authority §2 and row 26; cpoc §§2.2–2.4; evaluation §2 and §3.2; UI §2.1.

**Observed problem:** Every Execution appends EXECUTION_STARTED, and its log's only carrier is a file in the Store or output directory. But simulate explicitly supports output_dir=None and produces its results in memory. create_engine has no output-dir argument; UI New run writes no outputs; an Execution without checkpoint controls expressly never touches a Store. No alternative in-memory log carrier or deferred append lifecycle is declared.

**Counterexample:** Call the source function with valid rows and default output_dir=None. It creates an Execution but has no permitted location for its mandatory log. Independently, create a default UI session, step it, then request its first checkpoint. Before that action it must not touch the Store and has no output location; afterward its log must be in the Store. The documents do not define the binding/transfer of the pre-checkpoint log, its prior op_seq or its EXECUTION_STARTED record. Inventing a default output root, retaining an undeclared log in memory, or omitting the record are materially different implementations.

**Why it matters:** The write→hash→receipt sequence is coherent for an already-bound Execution, but not all expressly supported ways of creating one have a lawful evidence carrier. This is an ordinary API/UI lifecycle gap, not malicious overwrite or a demand that uncheckpointed simulation state survive death.

**Required disposition before admission:** State one consistent carrier/lifecycle rule covering output-free batch execution, default live creation and first explicit Store binding, including log sequence continuity. Propagate it to the public/UI contracts and the plan. The owner/author chooses the rule; this audit does not supply an implementation.

### R6-I-02 — The stale-writer witness never establishes a stale token

Severity: MEDIUM

**Closure relation:** R5-I-05 PARTIAL. The underlying write-admission predicate is not failed by this finding.

**Governing evidence:** cpoc §4.2 steps 4–5, §3.2, §6 row 9; testing §7 write_admission and exact negative-fixture obligation.

**Observed problem:** Row 9 resumes B from D12/sequence 1 and attempts a second writer “while B runs,” asserting that B's document already has sequence >=2. In the specified continuation B has no checkpoint controls. Its only write is finality, sequence 2, at completion.

**Counterexample:** Attempt the second write before B's finality: the document is still RUNNING/1 and the token is 1, so the stated sequence predicate admits it; STALE_WRITER cannot be the result. Attempt it after finality: the result is WRITE_AFTER_FINAL, also not STALE_WRITER. Neither reaches a RUNNING document with a later sequence. The Preserved column asserts such a state but the Mutation/construction column never produces it.

**Why it matters:** The named test cannot verify its promised refusal if constructed exactly as required. An ordinary conforming writer fails the test. This is not a demand for concurrent compare-and-swap or malicious-writer protection: the intended later RUNNING version can be tested within the declared model, but its creation must be part of the fixture.

**Required disposition before admission:** Specify a reachable RUNNING document/token mismatch and its ordering in the witness, then align the test with that construction. Do not treat a fabricated expected precondition as an executed state transition.

Other sampled ordering repairs pass: heading plus rehash reaches step 11; heading without rehash reaches 9; required-field removal reaches 2; final Execution reaches 7; forged TickRecord load plus history_hash reaches 10; future mutation is now a second independently valid Run and needs no foreign-Store copy. A further fixture precondition to pin in the same repair is row 24's fixed pickup=2: it reaches 11 only for a selected WAITING passenger requested no later than 2; the generic D12 fixture currently promises WAITING, not that request-time condition.

### R6-I-03 — Accepted sparse parameters exceed the request-time domain

Severity: MEDIUM

**Closure relation:** R5-I-08 PARTIAL; an adjacent case created by the newly narrowed input domain, not an out-of-domain large-number attack.

**Governing evidence:** evaluation §2, §6.2, sparse row in §6.3 and the concluding refusal list; constitution §4.5 Scenario generation; testing §6 generate_refuses_invalid_parameters.

**Counterexample:** F=2, N=1, C=1, seed=0, pattern=sparse, num_requests=1002, g=1,000,000, j=0. Every parameter lies inside its declared domain; no horizon parameter is supplied. For i=1001, time=i*g+draw(1)=1,001,000,000, greater than the allowed 10^9 request time. This is a hand calculation; no long simulation was run.

**Observed problem:** The advertised valid recipe emits a Trace that the shared public boundary refuses. The scenario refusal list names individual-domain violations, unknown parameters and capacity_stress constraints, but no combined spacing/request-count constraint or generated-time refusal boundary. The plan nevertheless requires every generated Trace to be valid.

**Why it matters:** One implementer can accept generation and fail at Trace load with INPUT_INVALID; another can reject the Scenario upfront; another can change spacing to fit. Those are different behaviors, and clipping is expressly prohibited except where named. Narrowing F fixes the original unreachable-set counterexample but does not close all accepted combinations.

**Required disposition before admission:** Reconcile the accepted sparse parameter combinations with the generated request-time domain and name the rejection boundary/reason. Do not silently adjust generated times or broaden the input domain during implementation.

### R6-I-04 — Experiment equality still includes random execution IDs

Severity: MEDIUM

**Closure relation:** R5-I-09 PARTIAL; the Run's eight-file surface is repaired.

**Governing evidence:** evaluation §§7.3–7.4; testing §4 experiment_reexecution_identical; plan cut 8.

**Counterexample:** Execute the same Experiment definition twice under the same code. The experiment_execution_id, run_ids, summaries and aggregates match. Each per-Run execution_id is freshly minted and differs, as §7.3 expressly permits. Section 7.4 requires those IDs in experiment.json. The test still demands “experiment.json byte-identical, same execution_id.”

**Why it matters:** A conforming implementation cannot satisfy that byte-equality test. Fixing execution IDs to make it pass would violate the new Execution identity contract; omitting required fields or normalizing only in a test without a stated comparison surface would silently choose semantics. This is the same output-equality repair problem moved into the changed Experiment record.

**Required disposition before admission:** Make the Experiment comparison obligation agree with its deterministic and operational fields and distinguish experiment_execution_id from per-Run execution_id. No change to the repaired Run surface is implied.

### R6-I-05 — Empty-run metrics conflict with null-aware aggregation

Severity: MEDIUM

**Closure relation:** R5-I-10 PARTIAL.

**Governing evidence:** evaluation §4.3 and §7.4; testing §6 empty_population_summary and experiment_null_aggregation; UI §3; authority row 34.

**Counterexample:** A completed empty uniform Scenario yields, under §4.3, null deferred.count, null wrong_way.count and null tail_share. Section 7.4 classifies all three as always-defined for every completed Run and explicitly says tail_share is 0 when n=0. Yet nulls must be excluded, never treated as zero. In a one-seed empty cell, the null-preserving interpretation gives n_defined=0/null aggregate; the always-defined interpretation gives n_defined=1, with a zero tail-share aggregate. Paired participation changes likewise.

**Why it matters:** The intended denominators are now explicit for ordinary conditional metrics, but two same-jurisdiction definitions still disagree on a valid input. The test includes an empty Run without resolving this contradiction, so it cannot settle the expected result by itself.

**Required disposition before admission:** Make empty-population metric values and aggregate classification consistent, including n_defined and n_pairs. Preserve the declared rule against silently turning null into zero.

The rest of the new aggregation rule is coherent: all-null wrong_way.mean_extra produces null with n_defined=0; one defined/one null side produces no pair; halted Runs contribute to halted_count and listings, not distributions; win/tie/loss counts use n_pairs. For example, cost values [null,4] and baseline values [2,null] have one defined value per side and zero defined pairs. No unpaired subtraction or denominator K is implied.

### R6-I-06 — Cut 9 still requires later witness and UI capabilities

Severity: MEDIUM

**Closure relation:** R5-I-12 PARTIAL; the original cut-3/export dependency is repaired.

**Governing evidence:** plan Rules/Order and cuts 1, 9–11; cpoc §5.1 and §6 rows 29/31; testing §7.

**Counterexample:** Cut 9 requires one fixture for every cpoc §6 negative witness, constructed exactly as its row states. Row 29 includes comparing the UI shaft projection with engine state, but the UI arrives in cut 11, which depends on cut 9. Row 31 asks the witness harness to refuse CPOC qualification with A still alive; that harness is delivered in cut 10, which also depends on cut 9. The plan forbids implementing later-cut features early.

**Additional direct placement conflict:** Cut 1 includes Snapshot/HistoryPrefix types while its expected files are domain.py and normalization-only api.py. The governing cpoc §5.1 defines Snapshot in the checkpoint module, scheduled for cut 9. The plan does not delimit an early checkpoint-type-only portion.

**Why it matters:** The new local/CPOC-pending labels correctly defer qualification, but they do not remove prerequisites from the explicit local test list. Exact test names now exist; their required capabilities still prevent completion in the admitted order.

**Required disposition before plan admission:** Reconcile the cut-local obligation subsets and type placement with their governing ownership/module contracts. Preserve the distinction between local verification and later CPOC qualification. This audit does not re-plan or execute any cut.

### R6-I-07 — Active refusal, invariant and illustration references remain stale

Severity: LOW

**Closure relation:** R5-I-15 PARTIAL; LOW residual of R5-I-11. These are bounded propagation defects, not new simulation semantics.

**Evidence and cases:**

- UI §2.2 now gives NO_HISTORY for every historical request on a new t=0 session with no TickRecord. Testing §8 history_at_creation still expects HISTORY_TICK_NOT_AVAILABLE for precisely that request. Both specify 404 and no current-state fallback; the expected symbolic reason is stale.
- Checklist check 5 still calls travel-equals-distance P12; it is P11. This is within the requested targeted P11/P12 sweep. UI §6 also retains the original authority-reference pair N8/N10, where the intended authority/projection prohibitions are N9/N11.
- Rewritten W-D uses W-B, whose p1 travels 2→4. Its verification-10 narrative calls p1 wrong-way at tick 2; the actual case is compatible and full. The TickRecords and governing rule still determine capacity deferral. The same row says the verifier is discarded, while its boundary state is used at verification 11; cpoc §5.2 correctly discards it after 11.

**Required disposition:** Correct these active references/expected record labels in the author revision; do not edit historical audits. The governing history range and mechanics are already unambiguous. These LOW issues alone would not justify structural failure under the user's standard.

## Liveness preservation check

**Preserved: `T_last + 2P(F-1)`.** This review did not restart the theorem audit. It compared the changed mechanics and wording with the independently established revision-5 proof.

The only boarding-function change is the order of classification checks. For a full incompatible passenger, both old and new functions skip boarding; the new rule names the skip direction-only. For a full compatible passenger, both skip for capacity. For a FREE car with room, the first fitting passenger sets departure and later boarders must match. The promised departure still controls heading; LOOK, zero dwell, one-floor movement, service phases and assignment immutability are unchanged. Execution IDs, write tokens and operational receipts never enter these mechanics.

The published invariant now says weakly ahead at a tick boundary, equality alights in step 3, and remaining onboard destinations are strictly ahead afterward. The progress account explicitly permits several board/alight events at one tick and bounds the number of distinct progress ticks by at most 2P. There is no new dwell, reversal or idle delay to add to the established F−1 interval argument. Narrowing the valid configuration/input domain does not invalidate a theorem already established on the larger finite domain.

The new sparse-domain finding is a generation/validation inconsistency, not a lawful engine trace violating eventual service. No new finite-trace liveness counterexample was found or claimed. No randomized simulation was used as proof.

## Source-contract preservation

Direct PDF inspection confirms preservation of the changed source-facing contracts:

- The function still consumes time,id,source,dest and preserves supplied unique IDs. Shared normalization and a separate live factory do not replace the required batch function with a second simulator.
- Configurable elevator/floor/capacity inputs remain. The PDF does not require unlimited configuration ranges; the declared practical limits are permissible assumptions and include its illustrated floor-51 input with an appropriately sized building. The internally inconsistent sparse combination remains R6-I-03, not an invented PDF maximum requirement.
- The source-facing position export remains one row per timestamp with all elevator positions from t=0. Separating execution metadata does not remove that file or required min/max/average wait and total metrics and observations.
- Direction-compatible destination dispatch, immediate assignment, discrete movement through gaps and no future peek are preserved. The PDF forbids changing destination; immutable assignment is correctly attributed as the project's stricter choice.
- Python/public GitHub, README run/time/assumptions/improvements and presentation remain future deliverable obligations. None is claimed implemented by this audit.

No new source-contract contradiction was identified in the revision-6 changes. OSA/CPOC, Monte Carlo, AIE and the UI remain separately attributed enhancements. Recruiting-email AI permission is qualified as reported context; no absent email was treated as reviewed evidence.

## Implementation-plan closure

Targeted recheck confirms the original requested repairs: cut 3 now lists engine-local in-memory invariants; export tests are in cut 6; one_elevator_one_passenger_up and one_elevator_one_passenger_down are separate exact names; checkpoint_at_zero_reconstructs_initial_floors exists in the testing contract; store init and resume are absent from cut 8 and appear in cut 9. The batch/live boundary is scheduled in cut 8, and UI use in cut 11.

Local verification versus CPOC-qualified standing remains coherent as a standing model. Cuts may be locally verified while CPOC is pending, and no continuity-qualified project claim is permitted before the applicable cut-10 witness. However, R6-I-06 demonstrates that explicit cut-9 prerequisites still defeat that intended staging. R6-I-04 additionally makes a cut-8 acceptance test impossible under its changed output contract; R6-I-05 makes its empty-Run aggregation expectation ambiguous. Those must be closed before the unadmitted plan can be executed in order.

No general re-plan, framework review, performance expansion, new mechanism or implementation was undertaken.

## Admission recommendation

**NOT READY FOR ADMISSION**

The six MEDIUM findings require closure before owner admission under the user's stated threshold. The main bounded-assurance repairs are accepted; failure is not based on declining cryptographic/malicious-code assurances. The LOW propagation finding is explicitly bounded and does not change the established liveness mechanics.

Final closure count: **8 CLOSED / 8 PARTIAL / 0 OPEN**. New/residual count: **0 HIGH / 6 MEDIUM / 1 LOW**. Liveness remains established. The revision-6 authority delta is not fully closed because the separate-log lifecycle lacks a permitted carrier in supported output-free/late-binding executions; aggregate semantics and their obligations also require reconciliation.

This record is evidence only. It admits no document or plan, authorizes no implementation and claims no executed CPOC result or certification.
