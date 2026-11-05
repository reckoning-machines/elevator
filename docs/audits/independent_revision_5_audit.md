# Independent Whole-Design Audit — Revision 5

## Standing

- Date: 2026-11-04.
- Auditor: independent reviewing agent; not the author of revision 5. This is the second independent whole-design audit.
- Subject: the current revision-5 bytes in `/Users/jedgore/dev/elevator`, the supplied workspace for `/dev/Elevator`.
- Evidence only: no document admission, implementation-plan admission, implementation, simulation execution, or certification is performed.
- Existing files are not edited. The only new artifact is this audit record. Original-file digests were captured before review; the final comparison confirmed all 22 pre-existing files unchanged and this audit as the only added file.
- Repository standing: documents only; Git status reports the document tree as untracked. No application or test code is present.
- Decision 001 records D-01–D-07; decision 002 is explicitly PROPOSED, NOT DECIDED, NOT ADMITTED. The audit assesses the coherence of the proposed revision-5 baseline, not whether those proposed decisions already have owner authority.

Reviewed in full: `AGENTS.md`, `README.md`, `constitution.md`, `authority_model.md`, `simulation_semantics.md`, `scheduler_design.md`, `evaluation_design.md`, `cpoc_design.md`, `ui_design.md`, `architecture.md`, `testing_contract.md`, `current_work.md`, `assumptions_and_tradeoffs.md`, `worked_examples.md`, `doctrine_adoption.md`, decision records 001 and 002, the initial audit including its appended pass 5, independent revision-4 audit, revision-5 repair record, current 26-item checklist, and implementation plan. Paths other than the root files are under `docs/` and the respective documented subdirectories.

The original source was inspected directly, visually, on all three pages: `/Users/jedgore/Downloads/Take_home_Elevator_(2).pdf`, SHA-256 `b6eb161d9716d16236dfeaa0a8056319a7acf3d6994d5994ed5f132087b9c007`. Images were rendered in memory; no PDF extraction/image artifacts were created. Source conclusions below do not rely on the repair record's description of the PDF. The recruiting email and separate original owner brief were not supplied as independently reviewable source artifacts; their provenance is distinguished accordingly.

All nine revision-5 digests in decision 002 §4 match the current files. Relative Markdown links resolve. Governing/design status lines identify revision 5. Historical decision/audit wording is not treated as an active revision-5 rule. Read-only searches, document hashing and PDF inspection were performed; no implementation or test program was created. One Python runtime fact used in the identity counterexample was checked against official Python documentation and is cited at the finding.

## Executive disposition

**OSA FAIL — C, STRUCTURAL GAP**

**CPOC: NOT APPLICABLE — DESIGN ONLY, WITNESS NOT IMPLEMENTED**

Previous findings: **6 CLOSED / 12 PARTIAL / 1 OPEN**.

New findings: **5 HIGH / 9 MEDIUM / 2 LOW**.

The repairs materially improve the design. Source IDs and the wide position export now have contracts; incremental Tier 1 and no-look-ahead comparisons are clearer; the Simulation History split removes checkpoint markers from deterministic event numbering; the new numerical liveness bound is valid under the independent proof below.

Admission nevertheless remains blocked. Finality is still not consistently scoped between Run identity, Store identity and repeat executions; the source hash is not necessarily the identity of executed Python code; a validating History-folding loader can pass the proposed witness; deterministic-output equality still includes provenance that can differ; and the new authority boundaries do not all fit the constitution's exhaustive transition classes. Several validation, experiment, UI and plan obligations also remain contradictory or incomplete.

The LOW liveness finding concerns the statement of a boundary lemma, not the numerical bound. No finite lawful simulation trace violating eventual service or `T_last + 2P(F-1)` was found. The independent argument below establishes the bound without randomized testing.

## Revision-4 finding closure

Each row repeats the original adversarial case and an adjacent variant. CLOSED does not mean implemented or tested. A repaired original example with a surviving related defect is PARTIAL; I-05 remains OPEN because the essential consumption-proof obligation is still unmet.

| Finding | Revision-4 defect | Revision-5 disposition | CLOSED / PARTIAL / OPEN | Evidence |
| --- | --- | --- | --- | --- |
| I-01 | Missing exact-fact authority coverage | Expanded to 36 rows, including departure, standing, identity and execution controls | PARTIAL | Original persistent-departure and omitted-standing cases are closed by authority rows 16–17. Adjacent Store creation and operational append have boundaries in authority §2 but no lawful class in constitution §4.5; store schema and operational execution binding remain incomplete. R5-I-13. |
| I-02 | Empty output directory permits resurrection | Store-bound run.json owns durable standing | PARTIAL | Original empty-output and foreign-document-copy cases now refuse (cpoc §§5–6). Adjacent independent same-run executions in two Stores, ordinary checkpoint replacement of an existing final path, and final-commit crash scope are unresolved. R5-I-01. |
| I-03 | Dirty SHA identity and mismatch override | Source-byte hash, no override | PARTIAL | Dirty `.py` edits change the computed hash and the override is removed. Adjacent stale-bytecode execution can run different instructions under the same source hash. R5-I-02; architecture §4. |
| I-04 | Checkpoint/resume markers break History equality | Separate Simulation History and Operational Log | PARTIAL | Original markers and simulation sequence-number shifts are closed by constitution §2/N18 and W-D. Adjacent same-run identity.json provenance still breaks unconditional derived-output equality; checkpoint operational receipts are also not coherently committed. R5-I-04, R5-I-09. |
| I-05 | Emission/count witness cannot exclude History folding | Snapshot-only signature, load hashes, tampering tests | OPEN | A loader can perform all original-snapshot checks, then build an equal snapshot-shaped value from History and pass it to construct_state. Correct hashes and tamper refusals do not distinguish that path. Adjacent helper outside checkpoint defeats the module-limited structural test. R5-I-03. |
| I-06 | Missing snapshot heading/capacity/ID checks | Eleven-step validation | PARTIAL | Original heading-only mutation now has a governing refusal, and IDs/capacity/travel checks are added. Adjacent forged TickRecord load survives the enumerated checks; negative-witness construction often hits the hash check before its claimed check. R5-I-05–06. |
| I-07 | False shrinking-stops premise and unproved bound | Progress proof, bound 2P(F-1) | CLOSED | Replacing an origin with a farther destination does not defeat the new progress accounting. Adjacent F=2, capacity 1, endpoint arrival and same-tick alight/board cases satisfy the independent proof below. The literal strict-ahead lemma needs only the bounded LOW correction R5-I-14. |
| I-08 | Future mutation wrongly requires equal termination | Decision/motion prefix through common active interval | CLOSED | Original 0→1 request plus a future request no longer requires equal COMPLETED events or later records. Adjacent both-active variants compare proposals, receipts, transitions and motion through the full cutoff; testing §3 preserves the core prohibition. |
| I-09 | Tier 1 described as absolute/permanent non-deferral | Explicit incremental harm and conditional receipts | CLOSED | Original 0→4, 2→4, 4→3 case remains Tier 1 for the third request despite existing deferral. Adjacent later Tier-2 assignment may defer an earlier Tier-1 passenger without rewriting its receipt. Scheduler §§6.1–6.5, 7 and tests state both. Classification terminology elsewhere is R5-I-07. |
| I-10 | Only next_heading sharing was checked | Three named shared primitives and structural obligations | CLOSED | Original duplicate departure plus shared-next_heading design violates semantics §4.3 and the revised identity/AST obligation. Adjacent promised-departure branch is now explicitly included. Behavioral equality remains a separate required check. No claim that AST naming alone proves arbitrary program equivalence is accepted. |
| I-11 | Obsolete nonnegative test and completion cycle | Negative example, staged local/CPOC standings | PARTIAL | The old test and blanket early CPOC-completion cycle are removed. Adjacent cut-3 requirement for all §2 invariants still demands cut-6 exports; a cut-9 named test is absent from the contract. R5-I-12. |
| I-12 | Irrational std, empty and zero-mean cases undefined | Integer sqrt/truncation and explicit null cases | PARTIAL | Original single-run numerical cases now compute deterministically. Adjacent ordinary Experiment aggregation of nullable wrong_way.mean_extra, empty distributions and halted results is undefined. R5-I-10. |
| I-13 | Scenario rules and experiment identity not closed | SplitMix64, recipes, definition/execution split | PARTIAL | Original burst clipping and sparse feasibility choices are specified; execution identity resolves code at start. Adjacent nondefault p_lobby is contradicted by hard-coded 4/5, and allowed concentrated sets can be unreachable. R5-I-08. |
| I-14 | Position file has N rows per timestamp | Wide required export, long secondary export | CLOSED | Original N=3 case now has one row with three elevator columns. Adjacent configurable N, t=0 and final tick have ascending columns and beginning-of-tick semantics. Evaluation §3; PDF p. 2. |
| I-15 | Supplied passenger ID has no input treatment | Normalized unique source_id and stable internal IDs | CLOSED | Original string IDs survive to passengers.csv; duplicate refusal is named. Adjacent numeric 1 and string "1" normalize to the same ID and refuse; lexical order does not displace input order at equal timestamps. Evaluation §2. The UI's use of the synchronous boundary is separately R5-I-16. |
| I-16 | Source brief credited with requirements absent from it | README separates PDF and owner additions | PARTIAL | Original §22, AIE, tick-order and AI-permission attributions are corrected at their main locations. Adjacent immutable-assignment and calibration assertions remain misattributed/overstated in active assumptions and scheduler prose. R5-I-15. |
| I-17 | W-D expects the wrong first refusal | Internally consistent mutations intended to reach check 11 | PARTIAL | Original null-fields/COMPLETED variant is replaced. Adjacent heading and new passenger-field mutations leave snapshot_hash unchanged, so check 9 fails before the claimed check 11. R5-I-05. |
| I-18 | Stale active wording and unsupported timing | Broad propagation pass | PARTIAL | Original plan admission header, cost wording, counts and timing claim are corrected. Adjacent renumbered invariant/authority references remain stale; adoption record is called unchanged although it was revised. R5-I-15. |
| I-19 | RUNNING history endpoint admits nonexistent current tick | t−1 bound and named 404 | PARTIAL | Original creation/t=1 cases now refuse. Adjacent HALTED-at-tick-0 case still permits final_tick=0 even though W-E has no TickRecord 0. R5-I-11. |

## Current checklist

This executes all 26 current checks. Evidence means document/counterexample evidence only. Sections are referenced by their exact file and section/row/test name.

| # | Check | Result | Adversarial case and evidence |
| --- | --- | --- | --- |
| 1 | Authority map | FAIL | New Store creation and operational append do not fit exhaustive constitutional transition classes; process identity/hash registrations do not close execution binding. Authority §2/rows 4–7, 25–29 versus constitution §4.5; R5-I-13. |
| 2 | Tick order | PASS | Moving HEAD after RECORD would violate semantics §2 and repaired constitution §4.2. Floor changes in 8, heading in 5; alight-before-board and zero dwell are explicit. Halt reason shorthand is editorially stale, R5-I-15. |
| 3 | Position semantics | PASS | Post-move t=0 export is excluded by semantics §§1–3 and W-A. Wide and long files derive the same beginning-of-tick floor. |
| 4 | Departure/reversal | PASS | Turning away before boarding at W-G's endpoint is excluded by FREE; overriding a boarder's promise with nearest-stop direction is excluded by step 5. Actual boarder/motion selection is deterministic. |
| 5 | Capacity/direction | FAIL | Full-and-wrong-way W-F is called capacity deferral by semantics §4.2 and direction-only by §5/reporting/tests. Boarding itself is safe; classification contract is inconsistent. R5-I-07. |
| 6 | No look-ahead | PASS | Mutate future requests while both runs remain alive; testing §3 requires equal proposals, receipts, passenger events and motion. Legitimate termination differences are excluded; the view has no Trace access. |
| 7 | Determinism | FAIL | Equal source bytes can execute stale versus fresh bytecode; equal run_id can emit different identity.json provenance. R5-I-02, R5-I-09. Integer decisions and tie rules otherwise pass. |
| 8 | Recovery | FAIL | Validate snapshot, fold History elsewhere, construct equal state: all listed receipts and tampering checks can pass. R5-I-03. W-D also has receipt/negative-case issues, R5-I-04–05. |
| 9 | Refusals | FAIL | Snapshot mutation without rehash fails at 9, not 11; foreign-store future-mutation fixture fails binding before continuation. History-load fields and halted history range remain gaps. R5-I-05–06, R5-I-11. |
| 10 | Liveness | FAIL as literally worded; bound verified | Checklist demands every lemma be true. Strictly ahead at every tick boundary is false on arrival. The independent argument establishes the exact proposed bound; no semantic counterexample. LOW R5-I-14. |
| 11 | Estimates/outcomes | PASS | Copying projected pickup into Passenger violates constitution N10, authority row 21 and scheduler §§6.5/9. Negative marginal −66 and cost −52 remain conditional estimates, never outcomes. |
| 12 | Evaluation claims | PASS | Different seeds per policy or universal superiority are prohibited by evaluation §§7.2–7.5. Comparisons remain paired and regime-scoped; aggregation mechanics have a separate defect R5-I-10. |
| 13 | Browser authority | FAIL | HALTED endpoint can ask for an absent record and has no lawful historical source. R5-I-11. Browser-owned time/assignments are otherwise prohibited and stale-step guard remains server-owned. |
| 14 | Tests prove rules | FAIL | Validating History fold passes the consumption witness; negative tests fail earlier than expected; current UI tests omit halted history. R5-I-03, R5-I-05, R5-I-11. |
| 15 | Scope | PASS | Store directory, JSON document, ten-module core, batch evaluation and thin UI add no prohibited database/broker/framework. The identified defects do not justify generalized infrastructure. Architecture §§6–8 and cpoc §9. |
| 16 | Source requirements/attribution | FAIL, attribution only | Required input/output shapes are now supported directly against PDF pp. 1–3. Immutable assignment is still attributed to source rules that explicitly forbid destination change, not reassignment. LOW R5-I-15. |
| 17 | OPEN/proposed choices | PASS | D-08–D-14 are visibly proposed in decision 002; no admission is inferred from prose repairs. Their pending owner decision is expected, not an audit defect. |
| 18 | Tunable numbers | FAIL | Nondefault p_lobby is advertised but algorithm uses draw(5)<4; parameter and primitive domains are not fully reconciled. R5-I-08. All five cost parameters do participate in Configuration. |
| 19 | Record consistency | FAIL | Nine digests and links pass. Active stale cross-references, absent test names and dependency obligations remain. R5-I-12, R5-I-15. |
| 20 | Unclaimed standing/performance | PASS | No current measured timing, scheduler superiority, implementation authorization, admission or executed CPOC claim. Proof claims are assessed here rather than treated as certification. |
| 21 | Finality carrier | FAIL | Independently generated same-run documents in two Stores can disagree; normal checkpoint replacement has no final-path admission guard. Manual-overwrite exclusion does not cover those operations. R5-I-01. |
| 22 | History/Operational Log split | FAIL overall; simulation split passes | Multiple checkpoints/resumes no longer change simulation event numbers. But operational receipt persistence/hash and execution binding are contradictory, and derived-output equality still includes provenance. R5-I-04, R5-I-09, R5-I-13. |
| 23 | Code identity | FAIL | Hashing all `.py` files does not establish that the imported bytecode executed those source bytes. Dirty-source test alone misses it. R5-I-02. |
| 24 | Snapshot construction | FAIL | Signature and equal state hash establish shape/value, not data origin; validation can precede prohibited folding. R5-I-03. Mutation fixtures do not currently reach the claimed refusal boundary, R5-I-05. |
| 25 | Source IDs/exports | PASS | Nonempty normalized IDs, duplicate refusal, stable sort and wide positions are explicit. IDs need appear where passengers are identified, not in a positions-only row; that is the coherent reading of “every output.” |
| 26 | Numerics/generator closure | FAIL | Single-run numerical cases pass, but experiment null arithmetic is unowned; parameterized peak rule and concentrated-set termination fail closure. R5-I-08, R5-I-10. A future reference vector is required, not supplied as current evidence. |

## New findings

### R5-I-01 — Store binding does not close Run finality or ordinary write admission

Severity: HIGH

**Governing rule:** Constitution §2 Run/Store, §4.3, N13; authority rows 7, 17, 23; cpoc §§2–3, §5, §6 rows 3–6; proposed D-08.

**Observed problem:** Finality is stated for a Run identified by run_id, but its durable standing is independently stored per `(store_id, run_id)`. The rules neither constrain fresh execution of an already-stored run nor specify checkpoint admission against an existing final document. Atomic replacement is atomicity, not a prohibition on a stale writer.

**Counterexample:** Execute run R in S2, checkpoint and kill it. Separately execute the same inputs/code in S1, checkpoint and complete, so S1 records R final. Then `load(S2,R)` admits the independently created RUNNING document: no copying, forged store_id, concurrent access or manual overwrite occurred. The global “a final Run never resumes” rule and the per-Store loader disagree. In one Store, a fresh execution of the same inputs can reach a requested checkpoint whose specified write replaces `<S>/<R>/run.json`; no checkpoint-write precondition rejects the already-final path. The loader's RUN_FINAL check does not govern that write.

**Why it matters:** Choosing a Store or starting a repeat execution can still choose which standing is consumed. The stated deliberate-manual-overwrite limit does not excuse ordinary API writes. A crash after in-memory completion but before finality replacement also leaves a RUNNING durable document, so the finality commit boundary must explicitly distinguish transient completion from durable finality.

**Required disposition:** Resolve Run versus execution/Store scope, ordinary create/checkpoint/final writes against existing authority, and the final-transition commit boundary. No database or tamper-proof storage is demanded; the missing rules must be decided before implementation.

### R5-I-02 — Source-byte identity need not identify the code Python executes

Severity: HIGH

**Governing rule:** Constitution §2 Code identity, §12/P8/N17; architecture §4; cpoc §5 step 4; proposed D-09.

**Observed problem:** Every `.py` source file is hashed, but there is no requirement that imported executable code be compiled from those exact bytes or that the package remain immutable after import/hash. Ordinary Python bytecode-cache handling is not addressed.

**Counterexample:** Two installed copies have identical current `.py` files. One has a timestamp-valid cached policy from a prior same-size source version; the other recompiles current source. A changed tie expression of equal source length can select another elevator. Both processes compute the same source hash and run_id, but execute different policy instructions. Python's default cache validation checks source timestamp and size rather than source contents; source content hashes alone do not establish cache coherence. [Python 3.12 import reference, cached bytecode invalidation](https://docs.python.org/3.12/reference/import.html#cached-bytecode-invalidation).

**Why it matters:** This uses the permitted runtime's ordinary import mechanism, not an unsupported policy plugin or hypothetical hash collision. Excluding caches from source identity is sensible, but their execution cannot silently evade the identity promise. Hashing files after modules were imported also needs a stable-source assumption/binding.

**Required disposition:** Close the relation between hashed source, imported executable code and supported execution environment. State and verify the necessary package-loading/immutability constraints. The dirty-source and no-override repairs remain valid but insufficient.

### R5-I-03 — Validation plus a load receipt still cannot prove snapshot consumption

Severity: HIGH

**Governing rule:** Constitution N14/§13; cpoc §4 step 7 and its explanatory paragraph; §5 construction; testing §7; architecture §1.

**Observed problem:** The proposed proof observes equality of reconstructed values and a snapshot-only function signature. Neither establishes where the argument value was obtained. The structural check is scoped to functions exposed by the checkpoint module, not the complete construction data flow.

**Counterexample:** First validate the original document through all eleven checks, so every listed tampered snapshot refuses correctly. For accepted documents, use a helper in another permitted module, or an internal generic validation helper, to fold valid History into a snapshot-shaped value. Pass that value to `construct_state(snapshot)`. The helper need not return an engine object or expose a history-to-engine signature in checkpoint. On all valid inputs the folded value equals the validated snapshot, so constructed_state_hash equals snapshot_hash. No tick below the checkpoint is emitted. The tampering cases fail before this path and therefore cannot distinguish it.

**Why it matters:** This is precisely the prohibited source of authority, even when the values are equal. A larger hash receipt does not convert value equality into provenance evidence. The repair record acknowledges opaque helpers but the proposed structural obligations do not close that path.

**Required disposition:** Specify an auditable construction/data-flow boundary that excludes history-derived constructor input, with verification of the full relevant call graph and argument provenance. Do not claim the current signature/hash/tampering conjunction proves that property.

### R5-I-04 — Checkpoint operational receipts have no coherent commit or hash definition

Severity: MEDIUM

**Governing rule:** Authority rows 25–26; cpoc §3, §4 steps 2/7; architecture §2 item 4; W-D.

**Observed problem:** The document must contain A's CHECKPOINT_WRITTEN receipt after A dies. That receipt contains the document hash. The witness and architecture say write the document, then append the receipt; W-D instead shows it inside the written document. No exclusion rule defines a hash over a document containing its own hash receipt.

**Counterexample:** Write D, append CHECKPOINT_WRITTEN in memory, pause and SIGKILL: D does not contain the promised receipt. Append it before serializing instead: its document hash cannot denote those final bytes without a self-reference/exclusion rule. Rewrite after appending: the receipt hashes the earlier document, not the document the witness loads. Finality followed by EXECUTION_ENDED has the analogous “all executions so far” persistence question. Instrumented tick-emission observations are also said to be in the Operational Log although its allowed record vocabulary contains no such record type.

**Why it matters:** The main witness's mandatory evidence cannot be implemented unambiguously. Simulation-history separation itself is correct; operational evidence now needs an exact durable contract.

**Required disposition:** Define the hashed byte scope, receipt/write ordering, durable coverage and instrumentation carrier, including multiple checkpoints/resumes and final execution end. Do not let an unregistered second log silently acquire the missing evidence role.

### R5-I-05 — Negative witnesses fail earlier checks than their expected outcomes

Severity: MEDIUM

**Governing rule:** Cpoc §5 step 9, §6 rows 12–13/18/22; W-D negative variants; testing §7 ordered-refusal requirement.

**Observed problem:** Snapshot mutation cases change fields but do not recompute snapshot_hash. Step 9 checks that hash before step 11. The future-request witness copies the document to a fresh Store but says to recompute hashes/run_id, not its store binding.

**Counterexample:** Flip W-D heading UP→DOWN while retaining H_s as instructed: STATE_INCONSISTENT at step 9, not STATE_HISTORY_MISMATCH at 11. Its new completed-passenger variant has the same problem. Copy D12 to S2 and alter future requests/hashes/run_id: the unchanged store_id causes STORE_MISMATCH at 5, before a prefix comparison can run. Inserting a hash update or a new store binding mentally is an unrecorded repair.

**Why it matters:** Correct implementations fail the stipulated tests, and those tests never exercise the intended deeper boundary. Missing snapshot-field classification is also ambiguous between the document parse at 2 and structural check at 9 unless the parse contract deliberately admits missing sections.

**Required disposition:** Specify mutations and which dependent hashes/bindings are preserved or changed so each intended check is actually reached; pin structural parsing versus consistency failure ordering. Re-audit W-D after that change.

### R5-I-06 — History verification omits recorded-load consistency

Severity: MEDIUM

**Governing rule:** Constitution §14; authority rows 18–19/22; cpoc §5 steps 10–11.

**Observed problem:** The loader recomputes capacity from Events but never requires each TickRecord's recorded load to equal that reconstructed load. Snapshot comparison checks floors, headings and passenger events, not historical load fields.

**Counterexample:** Take a valid checkpoint and change only an intermediate TickRecord load to `C+1`, updating history_hash. Snapshot load and all passenger Events remain lawful. The explicit eleven checks still pass: recomputed event load is within capacity, snapshot agrees with Events, and recorded floors/headings are unchanged. The loaded History now reports an impossible occupancy and can change derived deferral/occupancy reports.

**Why it matters:** The loader admits two answers to a historical fact while claiming complete internal consistency. An adjacent direction change with a plausible floor path also requires validation of lawful route/departure behavior, beyond merely matching BOARDED to the recorded heading. The recorded-load case alone is sufficient to demonstrate the gap.

**Required disposition:** Close the enumerated History checks over every consequential TickRecord field and its canonical event/state derivation, with a negative witness that reaches that check. Do not reconstruct present state from History in order to repair it.

### R5-I-07 — Full-and-wrong-way deferral has contradictory definitions

Severity: MEDIUM

**Governing rule:** Simulation semantics §§4.2, 5; scheduler §5; evaluation §4.1; testing §1; W-F.

**Observed problem:** Semantics §4.2 explicitly calls a passenger who cannot fit a capacity deferral whether or not direction is compatible. Section 5 defines capacity deferral only at a compatible arrival. Scheduler/reporting/tests count a full incompatible arrival only as wrong-way. W-F says the direction check runs first, while the new primitive runs capacity first.

**Counterexample:** W-F tick 2 is the exact case: UP, full, down-bound passenger waiting. One governing section calls it capacity deferral; another calls it direction deferral, with zero capacity deferrals. The observable intended count can be inferred from reporting, but an independent auditor cannot resolve a same-scope semantic conflict by silently treating one definition as merely an internal label.

**Why it matters:** Tiering and reported counts depend on deferral meaning. Actual boarder selection remains safe and deterministic; the issue is the classification contract and its test claims.

**Required disposition:** Establish one meaning of each deferral and reconcile primitive comments, observation phase, examples and tests without changing the agreed direction-compatible boarding rule inadvertently.

### R5-I-08 — Scenario parameters and primitive range do not define every advertised generator

Severity: MEDIUM

**Governing rule:** Evaluation §§6.1–6.3, §7.1; proposed D-14; checklist 26.

**Observed problem:** up_peak advertises p_lobby but its exact algorithm always uses `draw(5)<4`; down_peak inherits that. Some validation domains exist only as future test examples. The 53-bit draw primitive cannot produce arbitrarily large concentrated floor sets, while F and m have no corresponding upper restriction.

**Counterexample:** With p_lobby=(0,1), following the parameter rule produces no designated lobby draws; following the pattern pseudocode still produces them with probability 4/5. These differ in draw count and Trace. Separately choose `F=2^53+1`, `m=F`: draw(F) has at most 2^53 possible outputs, so the specified distinct-floor collection cannot ever reach m even though `1<=m<=F` passes. This is a mathematical finite-parameter counterexample, not a randomized search.

**Why it matters:** “Exact algorithms” and “invalid parameters refuse” do not close an incompatible tunable or an unreachable set size. A future reference-vector test cannot decide which rule should govern.

**Required disposition:** Resolve parameter use and domains, including probability numerator/denominator and integer/cardinality bounds. Ensure each accepted scenario either has one terminating algorithm or a named refusal. No code or alternate generator is proposed here.

### R5-I-09 — Same-run byte equality still includes varying provenance outputs

Severity: HIGH

**Governing rule:** Constitution P8/P12, §12; evaluation §3 identity.json, §§6.1/6.4; authority §6; proposed D-10.

**Observed problem:** P8/P12 still require equal derived outputs, excluding only Operational Log equality. identity.json is a derived output containing Git SHA, worktree standing and Scenario provenance that are deliberately excluded from run_id.

**Counterexample:** Commit only README changes: executable source bytes, Configuration, Trace, code_identity and run_id remain identical, but identity.json's Git SHA changes. Alternatively seeds s and s+2^64 initialize the same specified generator state and produce the same Trace, while identity.json records different provenance seeds. Both are ordinary supported executions. Their Simulation Histories match and their derived identity files do not.

**Why it matters:** Splitting operational events repaired deterministic History but not the remaining unconditional output equality. Calling the mismatch a determinism defect contradicts the intended informational status of provenance.

**Required disposition:** Define the exact reproducible output surface versus execution/provenance evidence consistently in the constitution, reporting, CPOC and tests. Do not silently narrow P8 to the subset compared by the witness.

### R5-I-10 — Experiment arithmetic is undefined for valid nullable metrics

Severity: MEDIUM

**Governing rule:** Evaluation §§4.1–4.3, 7.4; plan cut 8; testing §4.

**Observed problem:** The Experiment requires means/medians of each metric and paired differences, but valid single-run summaries contain null metrics and halted summaries omit distributions. No exclusion, propagation, denominator or comparison policy is specified.

**Counterexample:** Two nonempty runs with no wrong-way passes each emit wrong_way.mean_extra=null. Their required paired difference is null−null. An empty valid uniform scenario makes wait/total distributions null as well. One policy with no wrong-way passes and another with some gives null versus a number. Treating null as zero, excluding the pair, retaining null or failing all produces different reported evidence.

**Why it matters:** Numeric edge repair moved an undefined operation from a single-run report into a routine Experiment. The default scenarios do not guarantee positive wrong-way counts, so this is not an exotic configuration.

**Required disposition:** Define aggregation and win/tie/loss treatment for undefined and unavailable metrics, including halted runs, and bind it to the experiment reporting contract and tests.

### R5-I-11 — The repaired history range still admits a halted tick with no record

Severity: MEDIUM

**Governing rule:** UI §2.2; constitution §4.3/P7/N12; W-E; testing §8.

**Observed problem:** The UI uses `0<=k<=final_tick` for both COMPLETED and HALTED. A halted tick is discarded; final_tick denotes the tick of the failure, not necessarily an available TickRecord.

**Counterexample:** W-E halts at tick 0 step 2 and has no TickRecord. The UI range admits `/tick/0` nevertheless. At a later halt k, the same defect affects `/tick/k`; substituting current state is prohibited. Revised tests cover only completed final ticks.

**Why it matters:** The original historical/present-state ambiguity survives on the other lifecycle branch.

**Required disposition:** Define historical availability for HALTED runs from committed records and add the corresponding boundary obligation. Do not change halt atomicity to manufacture a missing row.

### R5-I-12 — Plan prerequisites still demand later capabilities and absent test names

Severity: MEDIUM

**Governing rule:** Plan Rules/Order, cuts 3/6/8/9; testing §§2, 7.

**Observed problem:** Staged CPOC standing fixes the original cycle, but cut 3 still requires all §2 invariants, including position_exports_are_projections_of_tick_records and wide_export_one_row_per_timestamp, whose reporting files are not implemented until cut 6. Cut 9 names checkpoint_at_zero_reconstructs_initial_floors, absent from the current testing contract.

**Counterexample:** Completing the explicit cut-3 tests requires writing/readback of both export files before their admitted cut. Stub-only engine completion cannot satisfy them. Cut 8 also lists `store init`, although architecture permits only checkpoint to write Stores and that module is scheduled for cut 9; only resume is explicitly stubbed. The plan's exact-name rule is contradicted by the missing test and shorthand up/down combined name.

**Why it matters:** Local completion and ordered authorization remain incompatible even though CPOC qualification is now staged sensibly.

**Required disposition:** Align per-cut subsets, prerequisites and exact test names with the final module order. Preserve local versus CPOC-qualified standings; do not execute later cuts to satisfy an earlier-cut contradiction.

### R5-I-13 — New authority boundaries do not fit the exhaustive constitutional transition model

Severity: HIGH

**Governing rule:** Constitution §§2–4.5; authority §2, rows 4–7/25–29; cpoc §§2–5.

**Observed problem:** Authority §2 introduces Store creation and Operational Log append, but constitution §4.5 has neither class and explicitly permits no other class. Process-start identity creation is registered at another unlisted boundary. Conversely Terminate-or-halt already mutates the final Continuation Document, and Finality write also claims that change despite the exactly-one-class requirement.

**Counterexample/proof gap:** Executing the proposed `store init` necessarily establishes store_id, a governed fact, through a boundary with no allowed constitutional transition. Adding EXECUTION_STARTED/ENDED likewise has no matching class. The new `store.json.schema_version` is not the continuation-document schema fact in row 5 and lacks a separate stated check/version relationship. The Operational Log identity `(run_id, execution)` has no defined execution identifier/minting rule; PID evidence is not a durable unique execution identity across PID reuse.

**Why it matters:** Counting 36 rows does not establish a lawful transition for their writes. Implementers would have to choose new transition and identity semantics despite a NONE delta budget. These are actual authority-model closure gaps.

**Required disposition:** Reconcile the governing transition inventory with new boundaries and their ownership, including execution/log binding and Store version treatment. A decision record must authorize any changed ontology/authority; this audit does not supply it.

### R5-I-14 — The liveness proof states a false strict boundary lemma

Severity: LOW

**Governing rule:** Semantics §8.2 Lemma 1 and Lemma 2; constitution P10/P11; proposed D-11.

**Observed problem:** Lemma 1 says every onboard destination is strictly ahead at every tick boundary and that moving one floor preserves that strict property. A passenger arriving at its destination remains ONBOARD until the next tick's alighting step.

**Counterexample:** F=2, passenger 0→1 boards at tick 0; at boundary tick 1 the passenger is onboard at destination 1. Distance is zero, not strictly ahead. Lemma 2 already explicitly allows this zero-distance case. Progress ticks may also contain several events, rather than one strictly increasing event-time sequence per event.

**Why it matters:** The checklist cannot literally pass every lemma as written. This is bounded proof wording: the independent argument below proves the proposed bound using nonnegative boundary distance and post-alight strict distance without changing any simulation behavior.

**Required disposition:** Correct the phase-specific statement and distinguish event count from distinct event ticks. The numerical bound does not need a different semantic rule or an extra traversal term.

### R5-I-15 — Active references and source attributions still contain stale claims

Severity: LOW

**Governing rule:** AGENTS routing/update obligations; current-work repair claims; active scheduler/semantics/assumptions/adoption text.

**Observed problem:** Examples include AGENTS routing D-08–D-13 instead of D-14; travel referenced as P12 instead of P11; hidden policy state referenced as N14 instead of N15; exact decisions referenced as N15 instead of N16; UI authority refs N8/N10 instead of N9/N11; assumptions route ownership rows 7/9 now naming Store/time; doctrine adoption browser row 20 now route. Current-work calls doctrine_adoption unchanged although it contains revision-5 updates. Semantics step 7 still abbreviates every horizon halt as liveness-bound exceeded despite §8.3's split.

**Adjacent source case:** Assumptions §3 and scheduler §8 still say immutable assignment is required by the take-home. The PDF explicitly forbids destination modification, not reassignment; immutable assignment is the repository's stricter choice. Assumptions still says calibration measures what a demand model would be worth, while repaired scheduler §9 correctly requires controlled evaluation.

**Why it matters:** These remain active restatements, not protected historical evidence. The controlling mechanics are identifiable, so these are bounded record corrections rather than new authority decisions.

**Required disposition:** Correct active references and attributions in a later author revision; preserve historical audits/decision 001 as evidence. Qualify recruiting-email permission as reported context until its source is independently available.

### R5-I-16 — The source simulate function cannot also supply the specified live UI session

Severity: MEDIUM

**Governing rule:** Evaluation §2 final paragraph and SimulationResult contract; UI §§2.1–2.3; architecture §1 api/web dependencies.

**Observed problem:** The public function simulates the supplied requests and returns positions, final summary/observations and identity. It explicitly does not write continuation documents. Evaluation then says CLI simulate and UI New run call that same boundary, while the UI must obtain a new RUNNING engine to step/checkpoint. No return value or mode supplies that engine.

**Counterexample:** POST /runs calls the declared synchronous simulate and receives a completed SimulationResult, not a RUNNING engine at boundary 0. Starting a second engine afterward or using an unmentioned partial-run/factory mode is an implementation choice absent from the contract. CLI checkpoint controls have the related wiring ambiguity. The architecture also does not list checkpoint among web dependencies despite explicit UI checkpoint/reopen actions.

**Why it matters:** This is a material contradiction between component contracts, not a demand for another simulator. Sharing input normalization is coherent, but it is not the same as calling the complete simulation function to create an interactive engine.

**Required disposition:** Define the shared input boundary versus full-run and live-session lifecycles, with lawful checkpoint delegation and dependencies, before plan admission. Do not infer a second simulation implementation.

## Owner decisions D-08 through D-14

These are proposals in decision 002, not already-effective owner decisions. The judgments below concern their suitability for admission in their current propagated form.

### D-08 — Finality carrier

**Not acceptable as written.** The single document within one Store is substantially clearer than output-file finality. Its identity is `(store_id, run_id)`; a fresh Store mints a 128-bit identifier and records it in `store.json`; a foreign document is refused by load step 5. A checkpoint is the snapshot section of this document, not another independently authoritative file. Output paths never enter the load procedure.

That closes the original empty-output-directory exploit and the straightforward copy into a fresh Store. It does not close normal writes to an already-final run path or reconcile global Run identity with independently generated documents in different Stores. The no-concurrency assumption does not prevent the sequential counterexample in R5-I-01. Store creation and finality-write classification also conflict with the exhaustive transition table (R5-I-13). Deliberate replacement of the actual authority within its own Store is explicitly outside the threat model; this audit accepts that limit and does not demand tamper-proof storage.

### D-09 — Code identity

**Not acceptable as written.** Architecture §4 specifies sorted package-relative paths and source bytes for all `.py` files under `elevator/`. Thus domain, route, policies, engine, serialization wherever placed in that package, checkpoint/loader, generator, reporting, API and CLI code are included. Dirty source changes identity. Web files, generated/cache files and Git metadata are excluded; Git is provenance. There is no loader override. Experiment execution identity resolves this identity at execution start.

Integer arithmetic, specified serialization and the fixed PRNG remove dependence on ordinary floating-point and library-random choices. Keeping web-only presentation changes outside simulation identity is coherent with the import boundary. However, source hashing does not bind the bytes Python actually executes, including when an accepted cache or previously imported module differs (R5-I-02). The existing dirty-source test detects a different source file, not this equal-source/different-execution case. The claim of execution identity therefore remains stronger than the contract.

### D-10 — Simulation History versus Operational Log

**The simulation separation is sound; the propagated proposal is not yet admission-ready.** Simulation Events are now only passenger transitions and final Run transitions, and TickRecords remain deterministic observations. Operational records have independent numbering and never increment Simulation Event sequence numbers. Repeated checkpoints and resumes therefore need not change any simulated event or metric.

W-D's corrected event sequence demonstrates the intended split. But the operational document hash, append timing, durable checkpoint receipt, per-execution identity and diagnostic emission records do not yet form a consistent evidence contract (R5-I-04, R5-I-13). P8/P12 also still quantify over derived outputs containing execution-varying provenance (R5-I-09). The narrower comparison in cpoc §4 cannot silently amend the constitution.

### D-11 — Liveness proof

**The dynamics and numerical bound are acceptable.** The independent proof below establishes `T_last + 2P(F-1)` for finite valid demand and zero dwell. The published strict-ahead statement is false at an arrival boundary and needs the LOW wording correction R5-I-14. This is not a failed numerical bound, a finite-trace service counterexample, or a reason to reintroduce the previous bound.

### D-12 — Source ID and public function

**The source-input proposal is acceptable; its integration wording is not.** Evaluation §2 defines input types, row-position errors, decimal normalization, unique nonempty IDs, stable timestamp ordering, internal IDs and output preservation. For example, rows with IDs `"z"` then `"a"` at equal times keep that order; non-contiguous IDs need not be renumbered publicly. Integer `1` and string `"1"` collide after normalization and refuse. String `"01"` remains a distinct string from `"1"`; numeric 1 normalizes to `"1"`. Input order matters when it changes the sorted Trace; identical normalized Trace bytes lawfully share identity.

The proposed `simulate(...) -> SimulationResult` is a thin full-run adapter over one engine and reporting path, which satisfies the PDF. The statement that UI New run calls this complete-run function conflicts with creation of a live session at tick 0 (R5-I-16). No second simulation implementation should be inferred to reconcile it.

### D-13 — Position export

**Acceptable.** Evaluation §3 specifies `t,elevator_0,...,elevator_{N-1}`, exactly one row per timestamp and ascending elevator columns for any configured N. Semantics §§1–3 define the beginning-of-tick floor, recorded after service/heading and before movement. A completed Run includes tick 0 through its final tick; a halted Run includes only committed ticks. The long-form analytical export is explicitly secondary. Both are derived from TickRecords and have no read-back authority. This matches the PDF's source-facing shape.

### D-14 — Scenario and Experiment identity

**Not acceptable as written.** Definition hash, execution id and Run id are now separate and correctly timed. Configuration, scenario parameters, seeds and policy parameters are included; code identity is resolved by the executing process rather than supplied by an experiment author. Explicit draw ordering, clipping and sparse spacing close several original ambiguities.

However, a nondefault `p_lobby` has two incompatible interpretations and the allowed floor/set domain exceeds the primitive's reachable draw range (R5-I-08). The results contract also lacks arithmetic for valid null or absent metrics (R5-I-10). Hashing an ambiguous recipe does not turn it into a unique reproducible Trace or report.

## Liveness proof verification

**Independent result: the bound is valid.** This proof concerns the fixed route mechanics, not scheduler quality, and assumes a valid finite Trace, lawful assignments, `F >= 2`, `C >= 1`, zero dwell, and no intentionally smaller stress horizon. Put `D = F - 1 >= 1`. At `T_last`, after reveal and assignment, no future assignment can add work. Analyze one elevator E with `P_E` assigned passengers.

1. **Onboard directional invariant, with the correct phase.** At a tick boundary an onboard destination is weakly ahead in the carried heading: it may equal the current floor immediately after the preceding movement. Step 3 removes passengers at their destination. Any survivors have destinations strictly ahead. Those destinations are committed stops, so departure cannot become FREE while they remain ahead; step 5 cannot reverse away from them. New boarders must agree with that departure and have destinations strictly ahead too. Thus an onboard passenger's movement remains monotone until alighting. Waiting origins cannot force a reversal past an onboard destination.
2. **Progress with onboard passengers.** If someone is already at their destination, an alighting occurs at this tick's service step. Otherwise a destination is at most D floors ahead. The car moves one floor on every nonfinal tick until some such destination is reached; intermediate boarding has zero dwell and cannot reverse it. Therefore an alighting occurs within D ticks, possibly sooner. A new farther destination does not remove the nearer onboard destination.
3. **Progress with no onboard passengers.** If waiting work exists at the current floor and departure is FREE, positive capacity permits a boarding immediately. Otherwise take the current heading if a committed waiting origin lies ahead, or the heading selected by `next_heading`. With no boarding, the waiting set cannot change after `T_last`. The car reaches the extreme committed origin in that direction within D floor movements. It may pass intermediate origins wrong-way, but at that extreme no committed stop remains ahead: departure is FREE and the empty car boards the first waiting passenger. If it boards earlier, progress has already occurred. There is no extra reversal or dwell tick to charge.
4. **Progress resets the argument.** After service at a tick with boarding/alighting, if work remains, either there is someone onboard (case 2) or there is only waiting work (case 3). The next irreversible event occurs no later than D ticks afterward. Multiple events at one tick only improve this bound. Capacity can block additional boarding while the car is occupied, but cannot block alighting; an empty car has room. No extra capacity-induced traversal escapes these cases.
5. **Count events, then bound time.** Every passenger boards at most once and alights at most once. Starting at `T_last`, there are at most `2P_E` remaining irreversible events, and at most that many distinct progress ticks. If those ticks are `tau_1,...,tau_m`, then `tau_1 <= T_last + D` and `tau_(j+1) <= tau_j + D`. Consequently `final_E <= T_last + mD <= T_last + 2P_E D`. A traversal already underway at `T_last` needs no additional term: its remaining distance is already at most D. Previously completed events only reduce m.
6. **Global bound.** Elevators proceed concurrently and independently once assignments stop. Taking the maximum, not the sum, gives `final <= T_last + 2(max_E P_E)D <= T_last + 2PD`. Cars with no work contribute nothing. For P=0 the specified Run completes at tick 0. For F=2, D=1 and the same proof applies. Completion is checked in the same tick as the last alighting, so no extra terminal tick is needed.

This covers capacity 1, opposite directions at one origin, origins on both sides, repeated wrong-way passes before a pickup, sweep extrema, simultaneous requests, and a boarding that adds a farther destination. Assignments before `T_last` may change the path but preserve the onboard invariant; they do not invalidate the proof from `T_last`. The FREE rule rules out an empty car bouncing forever between unserved extremes. A requested lower `max_ticks` intentionally produces `HORIZON_EXCEEDED`; it is not evidence against the default liveness bound. A default-bound breach is a different invariant failure.

The same directional invariant proves `travel_time = |destination-origin|`: after boarding the passenger's destination remains ahead, the promised heading governs the first movement, there is one floor of movement per tick, no intervening reversal and no dwell. This is a statement about completed passengers, not a scheduler estimate.

The published proof's only identified defect is its strict-ahead statement at **every tick boundary**. A passenger riding 0→1 is onboard at boundary 1 at its destination, then alights in step 3. The phase-aware proof above does not require a semantic change. Checklist 10 fails its demand that every written lemma be true, but this bounded wording issue is LOW and the numerical proof passes.

## OSA authority sweep

The following set was derived from the actual reads/writes, selectors and outputs across the documents, then compared to authority §3's 36 rows. A row's existence was not treated as proof. A = AUTHORITATIVE, D = DERIVED, R = RECEIPT, E = EPHEMERAL. H/M states are historical/mutable. Denied rights below supplement, rather than replace, the engine's constitutional restrictions.

| Independently identified fact(s) | Owner, class, boundary; readers | Persistence, reconstruction, H/M and denied rights | Match / result |
| --- | --- | --- | --- |
| F/N/C, initial floors, horizon, policy and all cost parameters | Input carrier A, Trace load; engine, lawful view, reporting/harness/UI | Embedded and hash-checked; immutable H. A form or caller cannot change a running Configuration | Row 1; closed |
| Normalized source rows, request time/origin/destination, source_id, input_index | Trace carrier A, public normalization then Trace load; full Trace only engine/loader | Embedded; input validation repeated; H. Policy cannot reach future rows | Row 2; closed |
| source_id→passenger_id and stable tie order | Trace load D; all users of passenger identity | Recompute from sorted Trace, verify snapshot IDs; H. Lexical ID order has no selector right | Row 3; closed |
| Executed code and continuation schema constant | Process/package A at start; Trace load, loader, harness | Recomputed on load; H; no override. Source bytes do not establish executed instructions without the missing binding | Rows 4–5; R5-I-02 |
| Configuration/Trace hashes and run_id | Trace load D; all | Persist then recompute; H. Neither Git nor output directory can supply identity | Row 6; formula closed, finality scope R5-I-01 |
| store_id and Store schema | Store A, explicit Store creation; engine/loader | store.json durable; H. Foreign document fails binding; copying the authority itself is a stated limit | Row 7 covers id; separate Store schema relationship and creation class incomplete, R5-I-13 |
| Visibility and current t | Engine D visibility/A t; reveal and tick increment; lawful views/UI/reporting | Snapshot t plus exact passenger set; visibility reconstructed from Trace/t; M | Rows 8–9; closed, phase `<t`/`<=t` explicit |
| Passenger standing, assignment, pickup, dropoff | Engine A; assignment/board/alight; all read-only consumers | Snapshot; compare events without using them to construct state; standing M, times H once written | Rows 10–13; complete carriers, consumption witness still R5-I-03 |
| Floor and heading | Engine A; move/head steps; view/UI/reporting | Snapshot fields; compare last TickRecord; M. No load/route cache may replace them | Rows 14–15; closed |
| FREE/reversal status and promised departure_E | Engine E from route functions in step 4, consumed in 5 | Never durable; recompute only within a tick; no policy/UI read, no extra Elevator field | Row 16; closed |
| Run standing, final tick, halt step/reason/passenger | Engine A, terminate/halt and durable finality write; read-only reports | Document standing when one exists; final standing H; loader refuses final | Row 17; competing scope/commit classification R5-I-01, R5-I-13 |
| Simulation Events, TickRecords and event sequence | Engine R inseparable from tick commit; readers may inspect | Durable prefix, attached unchanged; H. Next event number follows prefix; no operational event consumes it; no replay into state | Row 18; split closed; historical-load validation gap R5-I-06 |
| Load, onboard/waiting sets, stops and projected route | Engine/route D from Passenger state; scheduler via lawful view, UI | Recompute; no independent storage authority; M projections | Rows 19–20; closed |
| Candidate scores, projected times, tier, chosen receipt | Policy E during one call; engine copies R to ASSIGNED; calibration reader | Only receipt persists; H evidence of estimate. No Passenger estimate, no realized guarantee | Row 21; closed |
| Capacity/direction deferral, wrong-way count/extra wait | Reporting D from historical passenger presence and TickRecords | Regenerate from immutable History; never new mutable counters or policy authority | Row 22; classification conflict R5-I-07, validation R5-I-06 |
| Continuation document and admitted resumed object graph | Engine A; checkpoint/finality/load | Snapshot consumed; History retained as History; no alternate output or stale file selector | Rows 23–24; finality and anti-folding gaps R5-I-01, R5-I-03 |
| Document/snapshot/history/constructed-state hashes and load receipt | Hashes D; loader emits R at admission; witness/operator readers | Receipt retained as evidence; H. Hash equality cannot establish origin of equal values | Row 25 and document schema; R5-I-03–05 |
| Operational sequence, execution grouping, start/end/checkpoint/resume facts | Executing process R at operational append; witness/operators | Document log plus operational.jsonl, H; excluded from world and metrics | Row 26 registers log, but execution binding/append/hash contract incomplete; R5-I-04, R5-I-13 |
| Checkpoint tick/interval/pause controls | Invoking caller E for execution; checkpoint hook only | Recorded as evidence, not reconstructed controls; no run_id or decision influence | Row 27; closed |
| Output root, Store path | Caller E; reporting writer / loader respectively | No output read-back. Store path chooses a Store, which must not choose alternate standing for one globally identified Run | Row 28 and §6; Store-selector gap R5-I-01 |
| PID, argv, environment evidence | OS fact recorded as R by process | Operational evidence; H; cannot establish simulation state or be assumed globally unique execution identity | Row 29; execution grouping incomplete, R5-I-13 |
| Scenario recipe, seed and generator state | Harness A recipe/seed, generator E state; generation | Recipe durable; redraw from seed; no runtime RNG or policy input from seed | Rows 30–31; algorithm/domain gaps R5-I-08 |
| Experiment definition/hash and execution id | Harness A definition, D identities at definition/execution boundaries | Durable definition/results; reproduce under same code; H | Rows 32–33; separation closed; inherited code-identity issue |
| Per-Run results, paired aggregates | Harness D, result file R of execution | Re-execution regenerates; not authority over Run | Row 34; nullable arithmetic R5-I-10 |
| Statistics, observations, exports, provenance labels | Reporting D from proper source state/history; UI/harness read | Regenerate; never repair source. Provenance informational and cannot govern continuation | Row 35 and §6; equality scope R5-I-09 |
| Session id/pointer, interval, play timer, from_time | Server/browser E at requests; UI only | Lost on death, reopened from Store/run_id; no browser fallback state | Row 36 and §6; historical HALTED range and creation contract R5-I-11, R5-I-16 |

The expansion closes many genuine omissions, including departure_E, run standing, max_ticks, checkpoint controls, source mapping and Experiment execution identity. No additional hidden scheduler state is needed. Nevertheless the Store schema/execution-binding facts and unmatched/overlapping transitions identified above prevent an authority PASS. Merely naming all these facts in this audit would not grant their missing authority.

## CPOC design adequacy

**Not adequate yet to prove the claimed boundary.** The intended boundary is now precise: before reveal at tick t, with full immutable inputs, exactly the revealed Passenger set, all floor/heading fields, standing and History through t−1. Derived load, routes, departure, projections and UI sessions are appropriately excluded. Full future Trace storage is necessary input persistence and does not grant scheduler access.

The qualifying process arrangement is sound: R is an independent uninterrupted process; A blocks holding state, is killed with SIGKILL, and is waited for; B is a fresh interpreter with a distinct PID and only Store/run_id/output arguments. The reference is not generated in B. Tick counts and emission instrumentation can distinguish a normal rerun from zero. Reopen is through `(store, run_id)`, not a caller-selected checkpoint filename. Uncheckpointed UI loss is an explicitly accepted boundary, not accidental transient continuity.

The remaining proof defect is specific: validation of the original snapshot can precede a silent History fold. A helper can return a snapshot-shaped dictionary, and `construct_state(snapshot)` can consume that dictionary without accepting any History argument itself. The restricted module/signature/AST checks do not exclude that path throughout the dependency graph. All tampering refusals still occur first, and equal-state hashes still match. Thus the receipt proves value equality, not that the admitted snapshot was the authority consumed (R5-I-03). This is a structurally passing defective loader, not an allegation that an implementation already exists.

### Final-transition crash analysis

| Death point | Durable standing surviving under the specified atomic replacement | Audit consequence |
| --- | --- | --- |
| No document has ever been written | No durable Run | No resume is promised; acceptable D-06 boundary |
| After in-memory progress/completion, before final replacement | Last RUNNING document and its old snapshot | Last checkpoint can be loaded; transient completion versus irrevocable finality must be consistently scoped, R5-I-01 |
| Temporary final file written, before rename | Old RUNNING document | Temporary file must not become a second selector; the named path still governs |
| During atomic rename | Old complete RUNNING document or new complete final document | Atomicity avoids torn authority; it does not itself prohibit a later stale ordinary write |
| After final replacement, before derived output writes | COMPLETED/HALTED, no snapshot | Load must refuse RUN_FINAL even with absent/empty outputs; this repair works |
| After outputs | Same final document | Changing output directory has no effect; works |

These are process-death cases, not an additional power-loss/filesystem durability certification demand. A deliberate manual overwrite within the same Store remains the documented limit.

### Loader attack outcomes

| Attack | Ordered contract / result |
| --- | --- |
| Mutate heading or passenger state, retain old snapshot hash | Step 9 STATE_INCONSISTENT, not the claimed step-11 result in several fixtures |
| Mutate heading, keep it in domain, recompute snapshot hash while retaining plausible History | Step 11 STATE_HISTORY_MISMATCH; the governing rule closes the original omission |
| Remove snapshot/heading/passenger | Must refuse; parse-versus-internal-check fixture shape must reach the named boundary rather than fail earlier |
| Missing/duplicate elevator, assignment outside range, C+1 onboard | Step 9 STATE_INCONSISTENT |
| Completed travel differs from distance | Step 9 STATE_INCONSISTENT |
| Wrong-way boarding, with checksums and event/record pairing otherwise made consistent | Step 10 HISTORY_INCONSISTENT |
| Plausible History plus inconsistent snapshot | Refusal is required; no silent History repair. This does not distinguish validate-then-fold on valid inputs |
| Forged historical TickRecord load, recomputed history hash, all events/snapshot unchanged | Enumerated checks can admit it; R5-I-06 |
| Malformed JSON, schema/code/input/hash mismatch | Named ordered refusals in steps 1–10; no override. Equal-source/different-executed-code remains outside what step 4 detects |
| Operational marker inserted in Simulation History | Step 10 refuses; the new split is enforceable |
| Malformed Operational Log | JSON parse failures refuse; semantically malformed but parseable operational sequences/grouping have no equally precise validation contract. Operational evidence cannot repair simulation state; R5-I-04, R5-I-13 |
| Final document, new output directory | RUN_FINAL; repaired |
| Old document copied into genuinely fresh Store | STORE_MISMATCH; repaired |
| Independently produced old same-run document in another Store | Can admit under its own binding; R5-I-01 |
| Changed informational provenance only | Continuation unchanged; harness may report mismatch. The full derived-output equality claim must account for that changed label, R5-I-09 |
| Future requests changed with new identities | Decisions/motion through common live cutoff must match; the new-Store fixture must also be lawfully rebound or it never reaches continuation, R5-I-05 |

Multiple checkpoints/resumes preserve the simulation prefix and next simulation sequence number. Their extra operational records must remain separate; however, the current document-hash self-reference and append timing prevent the specified durable evidence from being produced exactly as written. A log loaded from A plus B's process-specific records also needs the defined execution binding before assertions about “B's log” can be checked. These are design obligations, not current executed failures.

No witness was implemented or run. Standing remains **NOT APPLICABLE — DESIGN ONLY, WITNESS NOT IMPLEMENTED**.

## Source fidelity

The PDF was inspected visually, all three pages. Its requirements are distinct from recruiting-email permission, owner additions and imported engineering doctrine. No absent external email was treated as source evidence.

| PDF requirement | Current owning contract / result |
| --- | --- |
| Configurable elevators, floors, capacity | Constitution §2; evaluation §2 bounds and arguments; supported |
| Destination supplied at request, immediate elevator assignment, immutable destination | Semantics §§1–2/6; scheduler §§2–3; supported. Immutable **assignment** is an additional project rule, not the same PDF statement |
| Discrete movement, one floor/time unit, ticking through timestamp gaps | Semantics §§2–3/7; supported |
| No future peek | Constitution N1, SchedulerView and testing §3; supported with a valid common-active-prefix comparison |
| Eventual service and attempt to minimize total passenger time | P10 and proof above; scheduler wait-plus-marginal heuristic, travel fixed by distance; supported without claiming optimality |
| Direction/capacity constraints | Mechanics support both; conflicting full-and-wrong-way diagnostic classifications remain R5-I-07 |
| Function consuming time, id, source, dest | Evaluation §2, D-12; supported as a public batch adapter; live-UI wiring is separate R5-I-16 |
| Position output from t=0, one row/timestamp with all elevators | Evaluation §3, D-13; directly supported |
| Minimum, maximum, average wait and total | Evaluation §4; supported; added statistics have deterministic single-run rendering |
| Notable observations | Evaluation §5; rule-generated output plus cited presentation commentary |
| Python, public GitHub, README run instructions/time/assumptions/improvements | Architecture, README and plan cut 12; future deliverable obligations, not falsely claimed as implemented |
| Presentation/readiness | README walkthrough and cut 12; planned, not yet delivered |

Multiple policies, Monte Carlo, OSA/CPOC/AIE, a Store and HTMX are project/owner enhancements, not PDF mandates. Express-elevator handling is not made a mandatory source requirement. The remaining source issue is attribution, not absence of the PDF's input/output contract (R5-I-15). No invented source requirement is used to fail admission.

### Numeric reporting recheck

Evaluation §§4.2–4.3 closes the original single-run cases. All following are hand calculations, not executions:

| Population/case | Required canonical values |
| --- | --- |
| Zero passengers | Completed at 0; specified distribution fields null; utilisation `"0.000"`; single no-passengers observation; no division |
| One wait x | min/max/p95 = integer x; mean/median = x with three decimals; std `"0.000"` |
| Positive population of all zero waits | All wait statistics zero in their specified types; tail_ratio null and tail-ratio observation suppressed |
| Waits [0,0,1] | min 0, max 1, mean `"0.333"`, median `"0.000"`, p95 1; variance 2/9, std `"0.471"` by specified truncation |
| Waits [1,2] | mean and median `"1.500"`, p95 2, std `"0.500"` |
| Exact rounding ties | 1.2345 → `"1.235"`; −1.2345 → `"-1.235"`, relevant to paired differences |
| No wrong-way passengers | wrong_way.count = 0, wrong_way.mean_extra = null |

The standard deviation rule intentionally truncates, while rational means/medians round half away from zero; neither uses binary floating point. Canonical JSON uses integer values or decimal strings, sorted keys and no insignificant whitespace. What remains undefined is aggregation/subtraction of the valid null/missing results across an Experiment (R5-I-10), not these single-run arithmetic cases.

### Scenario boundary recheck

| Pattern | Adversarial boundary and result |
| --- | --- |
| uniform | Zero requests emits no rows; simultaneous times use generation index; F=2 destination redraw has one alternative; draw order is explicit |
| up_peak / down_peak | Default 4/5 recipes and floor reflection are readable; nondefault p_lobby contradicts literal draw(5)<4, R5-I-08 |
| bursty | Centers near 0/horizon use explicit clamp, not redraw; duplicate centers/timestamps are lawful and stable. Positive k/w domains must be governed consistently, not only appear in future test names |
| concentrated_origin / concentrated_destination | Ordered first-seen set is explicit; m>F refuses. Accepted F=m=2^53+1 cannot fill a set using a primitive with at most 2^53 possible draw(F) results, R5-I-08 |
| capacity_stress | More than N*C requests and in-range origin required; zero requests is invalid for this pattern, not silently relaxed; simultaneous time 0 is deterministic |
| sparse | g>=1 and 0<=j<g give minimum gap g−j>=1; horizon is explicitly unused, so exceeding it is not an implicit clipping choice |
| adversarial | No draws; time i and alternating endpoint trips; F=2 is valid |

The large-floor counterexample is mathematical, not a performance demand: the declared valid domain admits a nonterminating recipe. Default practical cases can work while that universal specification is false. Rejecting or restricting it would require a governing choice, not a silent implementation adjustment.

### Worked-example recomputation

The seven examples were checked as illustrations against the rules. Floor sequences below include every listed tick; service and heading follow the same phase as the TickRecord.

| Example | Independent arithmetic/semantics | Result |
| --- | --- | --- |
| W-A | Floors 0,1,2,3 at ticks 0..3; UP through tick 2, NONE at 3. Pickup 0/dropoff 3; wait/travel/total 0/3/3. Events 0..4 and wide export correct | PASS |
| W-B | Floors 0,1,2,3,4,3,2,3,4 at 0..8. Heading UP at 0..3, DOWN at 4..5, UP at 6..7, NONE at 8. p0 0→4; p1 pickup 6/dropoff 8; waits 0/6 and travel 4/2. Compatible full pass at 2; p1 Tier 2, cost 4×6=24, marginal 0; final 8<=16 | PASS |
| W-C | From t=4, E0 floors 2,3,4,5,4,3,2,1,2,3,4 at 4..14; p1 alights 7, hypothetical p3 boards 11/alights 14. E1 0,1,2,3,4 at 4..8; p3 boards 5/alights 8. Both Tier 1, costs 35 and 5, marginal 0. Nearest-Car distance tie chooses E0; cost chooses E1 | PASS for the declared local state |
| W-D | At boundary 3: floor 3/UP, p0 onboard/p1 waiting, events 0..4 and records 0..2. B executes 3..8, six ticks, events 5..8; restored physical behavior matches W-B | FAIL as a whole: checkpoint receipt/hash and negative mutation first-failure claims are wrong, R5-I-04–05. Simulation History split and continuation arithmetic pass |
| W-E | Invalid proposal at tick 0 discards reveal with partial tick; only HALTED event 0 remains, no TickRecord. No passenger outcome metric may be invented | PASS; also supplies the counterexample to UI's halted historical range |
| W-F | Floors 0,1,2,3,4,3,2,1 at 0..7; p1 pickup 6/dropoff 7, wait/travel/total 6/1/7. Projection Tier 1 and no incremental capacity harm under scheduler §5; cost 24 with marginal 0 | Physical trace/arithmetic PASS; diagnostic claim FAIL against the conflicting semantics §4.2 statement. Governing conflict R5-I-07, not repaired by the illustration |
| W-G | Floors 4,5,6,5,4,3,2,1,0 at 0..8; UP at 0..1, DOWN at 2..7, NONE at 8. FREE boarding at 1 and 5; pickup/dropoff pairs (1,2),(5,8); totals 2 and 8; final 8<=24 | PASS; an example, not the general proof |

Scheduler §6's separate negative-marginal example was also rechecked: the added request changes the FREE choice and accelerates existing work, giving marginal −66 and total cost −52 as stated. Signed cost is coherent because only ordering matters; no probability, nonnegative duration or realized outcome is inferred from it. A weighted reduction for older existing passengers can outweigh the candidate's extra wait. That is an explicit heuristic tradeoff, not a promised minimization of every individual's delay. All five cost parameters are Configuration inputs; removing w_total is justified by fixed trip distance.

## Implementation-plan compatibility

The plan is explicitly unadmitted. Its staged `LOCAL VERIFY PASS / CPOC PENDING` standing correctly separates local tests from continuity qualification; the old blanket requirement to finish CPOC before constructing the witness is gone. It may not claim continuity proven until cut 10 passes for the applicable code identity. This audit grants none of those standings.

| Cut | Independent compatibility review |
| --- | --- |
| 1 Domain/input | Source normalization, source_id, code identity, canonical serialization and History types are included. Identity execution binding still needs the governing resolution R5-I-02 |
| 2 Route | All three shared primitives and projection are included; no direction-agnostic boarding or w_total obligation survives |
| 3 Engine | Revision-5 phase/heading, FREE/promise, halt atomicity and History split are represented. Requiring all testing §2 invariants here also requires exports/read-back checks delivered only in cut 6; R5-I-12 |
| 4 Interface/baselines | Closed view, deterministic RR/Nearest-Car and corrected future-mutation comparisons are represented |
| 5 Cost | Incremental Tier tests, negative marginal, integer cost, projection exactness and new liveness tests are included. Deferral conflict still blocks an unambiguous fixture expectation |
| 6 Reporting | Wide/long exports, IDs, rendering, zero populations and observations appear in the correct reporting cut; same-run provenance equality remains unresolved |
| 7 Scenarios | Exact PRNG/vector and validation tests are required, but cannot choose between the governing parameter/domain interpretations in R5-I-08 |
| 8 Public API/harness/CLI | Definition/execution identity and paired experiments included. Nullable arithmetic and live-vs-batch adapter are unresolved. `store init` appears before its sole writer module in cut 9; only resume is explicitly deferred |
| 9 Continuity | Store/finality, load order, receipt, snapshot construction and final writes included. `checkpoint_at_zero_reconstructs_initial_floors` is absent from the test contract despite the exact-name rule; R5-I-12. Governing witness/validation gaps are not cured by placing them in this cut |
| 10 Witness | Correct death/reference arrangement and two-policy obligation. Its currently specified assertions can still admit prohibited folding, and several negatives cannot reach their claimed check |
| 11 UI | Stale-step guard, shared session state and completed history endpoint are included. Halted history boundary and live creation wiring omitted/contradictory; R5-I-11, R5-I-16 |
| 12 Deliverables | README execution, public function example, time spent, assumptions/improvements, presentation and evidence are required; no present completion or admission is claimed |

Exact test-name inspection also finds shorthand `one_elevator_one_passenger_up/down` rather than the individual contract names. That is bounded as a naming defect within R5-I-12; the export and Store dependency obligations are material. No implementation-plan cut was executed, and no stub permitted by a future cut was created during this audit.

## Record consistency

Active files were searched independently of historical audit text. Revision-5 status lines and the nine proposed-admission digests agree. Decision 002 remains proposed; current_work is a handoff record and does not itself admit documents or the plan. Documents-only standing is true. No application, test scaffold or runtime file was found.

The main obsolete obligations are removed: 22-row ownership, SHA-only identity and mismatch override, direction-agnostic boarding, detour/w_total cost, nonnegative marginal, old numerical liveness formula, every-tick checkpoint default, five-example count and measured-microseconds claim do not remain as active governing requirements. Historical audits and explanations of removed rules properly retain old wording; those are not new findings.

Remaining active defects are the exact references and attribution claims in R5-I-15, plan names/dependencies in R5-I-12, the still-conflicting deferral statement, and the broader semantic contradictions recorded above. The current CPOC negative-witness list has 24 entries; row 6 is expressly LIMIT, not a qualifying success. Checkpoint/RESUMED references inside W-D's operational section and the deliberately invalid History fixture are lawful; they are not stale canonical Simulation Events. No claim of elapsed implementation time or measured policy superiority was inferred from planned tests.

OSA/CPOC rigor remains proportionate in structure: a small Python simulation package, exact integer mechanics, a file Store, batch experiments, and a server-rendered HTMX view. No database, broker, event-sourcing runtime, solver, RL system, microservice or agent framework has appeared. The audit fails contradictions in those contracts, not the choice to be rigorous.

## Admission recommendation

**NOT READY FOR ADMISSION**

All HIGH and MEDIUM findings must be resolved in governing documents and their propagated obligations, then independently re-audited. The five HIGH findings concern actual authority/constitutional or continuity-proof gaps; they cannot be waived as record cleanup. The nine MEDIUM findings leave materially different implementations or inadequate tests possible. The two LOW findings alone would not block coherent admission once the structural and semantic defects were closed.

The prior finding count is 6 CLOSED, 12 PARTIAL, 1 OPEN. D-12's source normalization and D-13's export are acceptable; D-11's bound is independently proved with a LOW wording defect; D-10's simulation split is sound but its evidence/output contracts are incomplete; D-08, D-09 and D-14 remain unacceptable as propagated. D-08–D-14 are therefore not acceptable as an admission package.

This record is evidence only. It authorizes nothing, admits neither design nor implementation plan, and claims neither executed CPOC evidence nor certification.
