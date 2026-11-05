# Independent Whole-Design Audit — Revision 4

## Standing

- Subject: the exact revision-4 document set present on 2026-11-04, before this record was created.
- Auditor: independent reviewing agent in this session; not the author of the governing drafts. No implementation, design repair, admission, or certification was performed.
- Date: 2026-11-04.
- Repository inspected: `/Users/jedgore/dev/elevator`, the supplied workspace. The request's `/dev/Elevator` was treated as the project name, not as a different checkout.
- Git standing: all 19 original documents were untracked; `git rev-parse --verify HEAD` confirmed that no HEAD commit exists. This audit is bound to the document bytes, not an invented Git revision.
- This audit is evidence only and authorizes nothing. Existing documents were not edited. This is the sole new file.
- Method: read every document below; inspect the source PDF visually; recompute examples and additional finite traces by hand; inspect hashes, links, inventory, and Git standing with read-only commands. No simulation, test, application, or patch file was created, and no implementation tests were run.

Files reviewed:

| File | Use in the audit |
| --- | --- |
| `AGENTS.md` | Routing, precedence, stop conditions, phase |
| `README.md` | Source restatement and deliverables |
| `docs/constitution.md` | Ontology, transitions, invariants, authority principles |
| `docs/authority_model.md` | All 22 rows, carrier sweep, refusals |
| `docs/simulation_semantics.md` | Every tick step, boarding, departure, termination, bound |
| `docs/scheduler_design.md` | Decision surface, projections, tiers, arithmetic, receipts |
| `docs/evaluation_design.md` | Scenarios, metrics, identities, comparison and claims |
| `docs/cpoc_design.md` | Boundary, checkpoint, loader, witness, negative witnesses |
| `docs/ui_design.md` | Controls, guards, historical reads, checkpoint behavior |
| `docs/architecture.md` | Dependencies, component boundaries, code identity |
| `docs/testing_contract.md` | All test categories and their stated proof obligations |
| `docs/assumptions_and_tradeoffs.md` | Assumptions and claimed source requirements |
| `docs/doctrine_adoption.md` | Adoption scope and source attribution |
| `docs/worked_examples.md` | W-A through W-G |
| `docs/current_work.md` | Phase, pending admissions, propagation claims |
| `docs/decisions/owner_decision_001_design_choices.md` | Recorded D-01 through D-07, proposed admission, digests |
| `docs/audits/initial_design_audit.md` | Historical findings and appended propagation claims |
| `docs/audits/whole_design_audit_checklist.md` | Minimum twenty-check contract |
| `docs/plans/implementation_plan.md` | Every cut and cross-cut obligation |

The owner subsequently identified the source brief as the latest PDF in Downloads. The newest PDF by modification time was `/Users/jedgore/Downloads/Take_home_Elevator_(2).pdf`, modified 2026-11-04. Its SHA-256 is `b6eb161d9716d16236dfeaa0a8056319a7acf3d6994d5994ed5f132087b9c007`. All three pages were visually read; text extraction returned empty pages because the document is image-based. References below to “PDF p. 1/2/3” mean this exact source. No PDF or rendered image was written into the repository.

All nine SHA-256 values in decision record §3 match their current files. All existing relative Markdown links resolve. All nine documents named in that digest table state revision 4. The repository contains documents only. D-01 through D-07 are recorded decisions, not merely recommendations. Their propagation is incomplete in the places identified below. The proposed admission text remains explicitly proposed, and there is no implementation-plan admission.

## Executive disposition

**OSA FAIL — C, STRUCTURAL GAP**

**CPOC: NOT APPLICABLE — DESIGN ONLY, WITNESS NOT IMPLEMENTED**

Findings: **7 HIGH / 9 MEDIUM / 3 LOW**.

The primary boarding algorithm is substantially clearer than the rejected direction-agnostic design. The hand-computed movement examples work, and negative marginal cost is mathematically coherent. Those conclusions do not close the authority and continuity gaps. In particular, a derived final-result file and the caller's output directory determine whether a supposedly final Run can resume; some consequential facts lack the required authority registration; the code-identity exception and operational History markers contradict unconditional identity guarantees; and the proposed witness does not exclude every prohibited reconstruction path it claims to exclude.

No finite lawful trace violating eventual service or exceeding the stated bound was found. That is distinct from a proof: the written argument has a false premise and does not derive the numerical bound. Admission cannot rely on the auditor supplying an unwritten replacement proof.

## Checklist results

References in this table identify exact repository documents and their numbered sections or named rows. “PASS” means the design closes the stated adversarial case, not that future implementation has been verified.

| # | Check | PASS/FAIL | Adversarial case considered | Evidence / finding |
| --- | --- | --- | --- | --- |
| 1 | Authority map | FAIL | Implement exactly the 22 rows, but let a derived final-result file select finality, omit a carrier for code/schema identity, and treat the boarding departure as an undeclared mutable field. | `authority_model.md` §3 rows 1–22, §5 `RUN_FINAL`, §6; `constitution.md` §§3, 4.5; `cpoc_design.md` §§3, 5. The table is not closed over the independently discovered facts. I-01, I-02. |
| 2 | Tick order | FAIL | Follow the constitution's statement that both elevator fields change in the motion step rather than writing heading in HEAD before RECORD. | `constitution.md` §4.2 versus its §4.5 Head/Move rows and `simulation_semantics.md` §2 steps 5, 6, 8. The operational nine-step order is clear, but not every restatement matches. I-18. |
| 3 | Position log | PASS | Record after movement and label the resulting floor as tick 0, shifting pickup/travel by one. | `simulation_semantics.md` §§1–3, 9; `worked_examples.md` W-A. Beginning-of-tick positions and RECORD before MOVE exclude this. W-A independently yields positions 0,1,2,3 and travel 3. The separate source-file row-format defect is I-14. |
| 4 | Direction, departure and reversal | PASS | At W-G's upper origin, turn toward the lower waiting passenger before boarding; or let nearest-stop routing override an idle car's promise. | `simulation_semantics.md` §2 steps 4–5, §§4–4.1; decision D-01 §2; W-B, W-F, W-G. FREE allows a boarder to choose departure, and step 5 preserves that choice. With a stop ahead, heading continues. These rules close the specific oscillation and promise violations. This is not a general liveness proof. |
| 5 | Capacity and direction at the stop | FAIL | Treat an existing capacity-deferral obligation as disqualifying every candidate, or assume a Tier-1 assignment can never later be capacity-deferred. | `scheduler_design.md` §§6.1–6.2 define newly deferred others by set difference; §§7–8 and decision D-04 use broader guarantees. The mechanical boarding gates and P12 are sound, but tier scope is not consistently described. I-09. |
| 6 | No look-ahead | FAIL | Add a future request after an otherwise completed trace, then require identical run Events and state before that future request. | `scheduler_design.md` §3 closes the policy view, including same-tick unassigned passengers; `constitution.md` N1 and `testing_contract.md` §3 require broader equality incompatible with termination in `simulation_semantics.md` §2 step 7. I-08. No policy look-ahead path was found in the enumerated view. |
| 7 | Determinism | FAIL | Resume with different code while preserving run_id; run dirty code at the same Git SHA; compare a checkpointed execution's full History to one without checkpoints. | `constitution.md` §§2, 5 P8, 12, 14; `architecture.md` §4; `authority_model.md` §5; `cpoc_design.md` §§4–5. Tie and integer rules close ordinary decision nondeterminism, but identity and History equality do not. I-03, I-04; experiment closure also I-13. |
| 8 | Recovery | FAIL | Rebuild present state by replaying the saved History without emitting earlier TickRecords; or alter a snapshot heading while retaining an internally consistent historical prefix. | `cpoc_design.md` §4 step 7 measures emissions and a tick count, while §5 omits the checkpoint-heading continuity comparison. W-D's successful ordinary continuation is reproducible by hand but does not establish the general refusal/proof contract. I-04–I-06. A's pause, actual SIGKILL, exit wait, and separate reference are well specified. |
| 9 | Refusals | FAIL | Move an old checkpoint to an empty output directory; require W-D's malformed passenger to fail with History inconsistency before the loader's earlier state check. | `authority_model.md` §5, `cpoc_design.md` §§5–6, W-D negative variant. Named refusal vocabulary exists, but finality is directory-relative and the example violates first-failure ordering. I-02, I-06, I-17. `PROVENANCE_MISMATCH` is informational, not a load refusal. |
| 10 | Liveness | FAIL | Board a waiting passenger after T_last and replace its origin stop with a farther destination; repeatedly refill before an old passenger's compatible arrival. | `simulation_semantics.md` §8 incorrectly says the committed stop set only shrinks; W-G itself disproves that premise. Finite progress is discussed, but no quantitative accounting derives `6(F-1)(P+1)`. I-07. This is a proof gap, not a discovered starvation trace. |
| 11 | Estimates versus outcomes | PASS | Copy a projected pickup into the Passenger record or overwrite a receipt after observing actual pickup. | `constitution.md` N9; `authority_model.md` rows 10–14 and §4; `scheduler_design.md` §§1, 6.5, 9. Estimates are ephemeral, then immutable assignment receipts; realized times have separate engine writes. W-C's costs 35 and 5 and chosen pickup/dropoff 5/8 recompute correctly. |
| 12 | Evaluation claims | PASS | Compare policies on separately sampled demand or report one favorable seed as universal superiority. | `evaluation_design.md` §§6.2–6.5; `scheduler_design.md` §4. Every policy receives the same trace hash, comparisons are paired by seed and reported by regime, and naive Nearest Car is explicitly defined. No superiority claim is licensed. Numeric/scenario gaps remain I-12–I-13. |
| 13 | Browser authority | FAIL | Request history at k=t while the RUNNING engine is at the start of tick t and has no TickRecord t; fill the missing historical view from present state. | `ui_design.md` §2.2 permits k<=t, while `cpoc_design.md` §§2–3 and semantics §2 make the historical prefix end at t-1. I-19. Browser holdings, stale-step guard, server serialization, and read-only historical intent otherwise exclude browser authority. |
| 14 | Tests prove rules | FAIL | Duplicate departure/boarding code while sharing only next_heading; reconstruct from History without earlier tick emissions; pass ordinary stale-page tests while serving nonexistent current-tick history. | `testing_contract.md` §§1, 3, 5, 7–8; `cpoc_design.md` §4. I-05, I-08, I-10, I-19. The same-process round trip is correctly labelled non-CPOC; cross-process determinism and wrong-way/travel invariants are meaningful obligations. |
| 15 | Scope | PASS | Introduce a persisted route, broker, generalized workflow engine, browser state model, or database to make recovery easier. | `AGENTS.md` Scope control; `architecture.md` §§1, 6–8; `cpoc_design.md` §9. The explicit dependency and carrier lists prohibit these additions. OSA/CPOC are elaborate for a take-home but serve declared correctness and continuity goals; that rigor alone is not a failure. |
| 16 | Source requirements | FAIL | Accept only internally numbered three-field requests and deliver N rows per timestamp as the required position file. | PDF p. 2 Input and Output versus `constitution.md` §2 and `evaluation_design.md` §3. Supplied passenger ID handling is missing, and the required output row shape directly conflicts. I-14–I-15. Other source requirements are mapped below; liveness remains I-07. |
| 17 | OPEN markers | PASS | Treat an old audit's OPEN wording or provisionally accepted cost defaults as an undecided operative override. | Decision record §§1–2 explicitly resolves D-01–D-07; §3 alone is proposed admission. Historical OPEN text in the immutable initial audit is historical evidence. No operative OPEN/RECOMMENDED choice was found outside the decision process. Newly discovered gaps are not silently resolved by this PASS. |
| 18 | Numbers | FAIL | Generate burst centres/window edges differently while using the same parameter labels, or change a checkpoint interval without any declared standing for the changed operational History. | `evaluation_design.md` §§2, 6.1–6.3; `cpoc_design.md` §2; authority rows 17–19. All five cost parameters are explicitly Configuration inputs, but experiment/generator and operational-control closure remain incomplete. I-01, I-04, I-13. |
| 19 | Record-set consistency | FAIL | Follow the plan header's admission instruction or its old nonnegative-marginal test despite current-work's propagation claim. | Plan status line and cut 5; README §1; current-work §3; initial audit Pass 4 F-33/F-34. Digests and links pass, but stale record assertions remain. I-11, I-18. |
| 20 | What is not claimed | FAIL | Treat the categorical “microseconds per candidate” assertion as measured performance despite no implementation. | `scheduler_design.md` §5 makes that unmeasured timing claim. I-18. The more important standing boundaries pass: drafts remain unadmitted; no implementation, CPOC execution, certification, or empirical scheduler superiority is claimed as completed. |

## Findings

### I-01 — The authority inventory is not closed over consequential facts

Severity: HIGH

**Rule / documents involved:** `constitution.md` §§2–4.5; `authority_model.md` §§2–3, 6; `simulation_semantics.md` §§4.1, 5; `cpoc_design.md` §§2–5; `evaluation_design.md` §6.1; `architecture.md` §4.

**Observed problem:** The claimed complete 22-row map does not register all consequential facts with the promised owner, class, write boundary, persistence, reconstruction, and denied rights. Missing or incomplete entries include run standing/finality, code identity, schema version, departure_E/FREE, realized deferral counters, and checkpoint scheduling control. Experiment definition and id are only partly covered outside the table. Row 12 describes completion rather than the full Passenger standing lifecycle; row 3 uses `request_time <= t` during reconstruction although a start-of-tick checkpoint contains only `< t`.

**Concrete counterexample or proof gap:** An implementer can treat `departure_E` as a persistent elevator attribute, or treat code/schema identity as arbitrary module constants, without a corresponding table entry defining their standing. More concretely, final-result existence already acts as a decision input without an authoritative finality carrier (I-02). The carrier sweep's engine row says denied rights are “none,” although the constitution denies the engine reassignment, future-assisted decisions, and resurrection.

**Why it matters:** Generic “the engine owns runtime state” does not meet this repository's exact-fact registration obligation. The gap is not permission for the auditor to invent owners or silently extend rows.

**Required disposition before admission:** The owner must close the authority inventory, including operational versus simulation state, and reconcile the concrete conflicting uses. The independent sweep below identifies the coverage and omissions without assigning new authority.

### I-02 — Run finality is selected by a derived file and caller-chosen directory

Severity: HIGH

**Rule / documents involved:** `constitution.md` §§4.3, 6 N10/N12/N16; `authority_model.md` §5 `RUN_FINAL`, §6; `evaluation_design.md` §3; `cpoc_design.md` §5 rule 9 and §6 stale-checkpoint witness.

**Observed problem:** Finality is decided by whether a final result exists in the supplied output directory. Single-run outputs, including `identity.json`, are declared DERIVED. No authoritative durable finality carrier or directory binding is specified.

**Concrete counterexample or proof gap:** Checkpoint a run, complete it in directory A, then load the old checkpoint with directory B, which is empty. All nine specified checks can pass, including rule 9. The same run_id is resumed despite its final standing. Moving/deleting a result has the same effect. The stale-checkpoint negative witness only checks the original-directory case.

**Why it matters:** A derived file and an ordinary path argument acquire the right to decide whether lawful continuation exists. This is both a second source of consequential truth and a direct resurrection path.

**Required disposition before admission:** Resolve the authoritative scope and durable carrier of finality, and the relationship between execution identity, repeat executions, and output locations. A witness must cover directory changes; simply assuming callers reuse a directory does not close the rule.

### I-03 — Code identity permits different behavior under the same run_id

Severity: HIGH

**Rule / documents involved:** `constitution.md` §2 Run, §5 P8, §§12, 14; `authority_model.md` §5 `CODE_IDENTITY_MISMATCH`; `cpoc_design.md` §5 rules 2–3; `architecture.md` §4.

**Observed problem:** The loader permits different executing code with `--accept-code-mismatch`, retains the embedded run identity, and labels the run non-reproducible. The constitution has no such exception. Separately, code identity is just the Git SHA when available, without dirty-tree content coverage or a clean-tree requirement.

**Concrete counterexample or proof gap:** Resume a checkpoint using modified scheduling code and the override. Two executions with the recorded same run_id can have different assignments. Even without the override, modifying an uncommitted source file at a fixed HEAD leaves the specified SHA identity unchanged. No owner decision D-01–D-07 authorizes either identity exception.

**Why it matters:** Saying “not reproducible” in a receipt does not amend P8 or change the identity that claims reproducibility. The dirty-tree case can produce the same problem without even the warning.

**Required disposition before admission:** The owner must decide the lawful standing and identity of code-mismatched execution and close the definition of executing code identity. A subordinate loader flag cannot waive the constitution.

### I-04 — Operational History markers contradict equality and checkpoint-prefix rules

Severity: HIGH

**Rule / documents involved:** `constitution.md` §2 Event/History/Run, P8/P11, §14; `authority_model.md` rows 14–15; `cpoc_design.md` §§1, 3–5; `worked_examples.md` W-D.

**Observed problem:** History includes CHECKPOINTED and RESUMED, but same-run History equality is unconditional in the constitution. CPOC §4 introduces an exception only in its comparison prose. Events have sequence-number identity, yet removing extra markers does not remove their effects on later sequence numbers. The checkpoint promises Events only through t-1, while W-D embeds CHECKPOINTED at t=3 in a start-of-tick-3 checkpoint.

**Concrete counterexample or proof gap:** R executes without a checkpoint. A checkpoints once and B resumes. Same configuration, Trace, and code give the same run_id, but B has two extra Events. With one Event sequence, subsequent ASSIGNED/ALIGHTED sequence numbers differ even after filtering marker rows. A literal loader enforcing “prefix ends at t-1” rejects W-D's marker; another accepts a boundary-event exception not specified there.

**Why it matters:** Two competent implementations can normalize different evidence or fail lawful checkpoints. The CPOC document's exception cannot silently redefine the constitution's History or canonical equality.

**Required disposition before admission:** Establish one governing definition of simulation History versus operational events, their numbering and boundary placement, and exactly which canonical bytes comparisons require. Reconcile the constitution, checkpoint schema, examples, and tests by owner-approved text.

### I-05 — The continuity witness does not exclude prohibited reconstruction


Severity: HIGH

**Rule / documents involved:** `constitution.md` N13, §13; `authority_model.md` §4; `cpoc_design.md` §4 steps 5–7, §5 final paragraph; `testing_contract.md` §§5, 7.

**Observed problem:** The anti-recomputation observations are emitted TickRecords, the first emitted tick, a RESUMED payload, and a tick count. They do not independently establish where B's present state came from.

**Concrete counterexample or proof gap:** A loader can ignore snapshot Passenger/Elevator values and reconstruct present state by folding the checkpoint's Event/TickRecord prefix, without calling the ordinary tick procedure or emitting old records. It then emits RESUMED and executes exactly the expected remaining ticks. Every listed emission/count assertion and final-output comparison can pass. A separate silent replay helper from zero presents the analogous risk if the counter instruments only ordinary continuation ticks.

**Why it matters:** The design expressly prohibits present-state reconstruction from History and recovery from zero. A real kill and a fresh PID prove process death; they do not prove that the snapshot was consumed as authority. This is an adequacy defect in the proposed witness, not a claim that any implementation currently cheats.

**Required disposition before admission:** Specify evidence capable of distinguishing snapshot-based reconstruction from the prohibited reconstruction paths. The witness must fail those defective implementations, including a history-folding loader, before its claimed proof is justified.

### I-06 — The nine loader checks omit consequential state-consistency checks

Severity: HIGH

**Rule / documents involved:** `constitution.md` P3/P12, N6/N6a, §14; `authority_model.md` rows 6–7 and §5; `cpoc_design.md` §5 rules 5–8.

**Observed problem:** The loader checks heading domain and the last recorded floor plus recorded heading against snapshot floor, but does not require snapshot heading to equal the heading carried across that boundary. The enumerated checks also do not explicitly verify complete/unique elevator IDs, assignment IDs in range, reconstructed capacity, or the complete lawful motion/event history.

**Concrete counterexample or proof gap:** In W-D's checkpoint, change only the elevator's current heading from UP to DOWN. Floor 3 is still in range; DOWN is in the domain; the last TickRecord remains floor 2 plus UP = 3; passenger fields, hashes, visibility, and finality checks still pass. At tick 3 the loaded car has a committed waiting origin below and moves down toward 2, carrying p0 away from destination 4. It can deliver p0 at tick 6 instead of 4, violating P12 and continuation equivalence. A later runtime halt would not make the load lawful.

**Why it matters:** The prescribed verification sequence accepts a state that was not the committed continuation state. General corruption language is insufficient when the detailed verification contract purports to enumerate the checks.

**Required disposition before admission:** Close snapshot-to-history and internal-state validation obligations and their named refusals. Add corresponding negative-witness obligations; do not leave the author of the loader to decide new consistency rules.

### I-07 — The liveness argument does not establish its numerical bound

Severity: MEDIUM

**Rule / documents involved:** `constitution.md` P10; `simulation_semantics.md` §8; `testing_contract.md` §§2, 5; `assumptions_and_tradeoffs.md` §4 item 7.

**Observed problem:** The proof begins with “after the last request time ... committed stop set only shrinks.” Boarding removes an origin and can add a new destination. The text then argues finite progress qualitatively without bounding the number and length of the relevant progress intervals to obtain `6(F-1)(P+1)`.

**Concrete counterexample or proof gap:** W-G has T_last=0 and committed stops {3,5}. At tick 1, boarding p0 changes these to {3,6}; 6 is new. A sweep endpoint can thus move after the last request. Repeated compatible arrivals full of younger passengers are acknowledged, but their cost is not quantitatively charged to a finite bound. The improvement list itself defers proving the bound.

**Why it matters:** A universal finite-trace claim and a default halt horizon require a defensible proof, not just W-G and sampled runs. An unestablished horizon can turn a lawful finite workload into an invariant-failure halt.

**Required disposition before admission:** Supply a valid general progress argument and derive the stated bound, or have the owner explicitly revise the claim and horizon contract. No starvation counterexample or bound-exceeding trace was found in this audit; the failure is the proof obligation as written.

### I-08 — No-look-ahead equality includes legitimate termination differences

Severity: MEDIUM

**Rule / documents involved:** `constitution.md` N1; `simulation_semantics.md` §2 step 7, §8; `testing_contract.md` §3; `cpoc_design.md` §6 future-request-leakage witness.

**Observed problem:** N1's “any decision or state” and the tests' equality of every Event and TickRecord before the mutation cutoff include run termination, which legitimately depends on whether unrevealed requests remain.

**Concrete counterexample or proof gap:** T contains one request at 0 from 0 to 1. T' contains the same request plus one at 10. With cutoff t*=5, T completes at tick 1; T' cannot. They have identical lawful assignment and motion through service of the first request, but only T emits COMPLETED at 1, and only T' has records at 2–5. The sentinel and checkpoint future-time mutation constructions can produce the same conflict.

**Why it matters:** The broad negative witness can fail a correct non-peeking engine or encourage suppressing legitimate finality information. Restricting the policy view is sound, but does not resolve the stated universal equality contract.

**Required disposition before admission:** Define the exact compared decision/state surfaces and valid comparison interval, with an explicit treatment of identity and termination events. The tests must distinguish forbidden decision leakage from lawful termination bookkeeping.

### I-09 — Tier guarantees are broader than the actual admissibility predicate

Severity: MEDIUM

**Rule / documents involved:** `scheduler_design.md` §§6.1–6.2, 7–8; decision record D-04 §2.

**Observed problem:** The formal predicate excludes newly deferred committed passengers: `with.deferred - base.deferred`. Prose says no already-committed passenger is deferred and “Under Tier 1 it never defers.” A Tier-1 assignment also cannot promise execution-time non-deferral after later assignments.

**Concrete counterexample or proof gap:** F=5, one car, C=1, all requests at 0 in this order: p0 0→4, p1 2→4, p2 4→3. Before assigning p2, p1 is already projected capacity-deferred at tick 2. Adding p2 lets it board at 4 and alight at 3 on the return, without newly deferring anyone. The formal predicate labels p2 Tier 1 while p1 still capacity-defers. Separately, a Tier-1 passenger waiting at floor 2 can later be blocked by a new same-car passenger boarding at floor 1; that later assignment is Tier 2, but the first receipt remains Tier 1.

**Why it matters:** Absolute and incremental admissibility yield different tiers and potentially different elevator choices. A receipt is a conditional projection, not a durable capacity guarantee.

**Required disposition before admission:** Make the owner-approved D-04 guarantee agree precisely with the predicate and projection time scope. Direction deferral must remain excluded from capacity admissibility.

### I-10 — The route-identity test does not prove shared D-01 mechanics

Severity: MEDIUM

**Rule / documents involved:** `scheduler_design.md` §5; `simulation_semantics.md` §2 steps 4–5; `testing_contract.md` §1 `projection_uses_engine_heading_function`; `architecture.md` §§1–2.

**Observed problem:** Revision 4 requires shared departure and boarding semantics, but the identity obligation still checks only `next_heading` and a one-step step-5 comparison. Step 5 does not call next_heading when a departure is already promised.

**Concrete counterexample or proof gap:** Implement departure/FREE and boarding twice, identically today, while sharing the same next_heading function object. All behavioral fixtures and next_heading identity can pass, yet the explicit single-implementation requirement is violated. A later change can update one copy alone. Even perfect agreement on ordinary LOOK cases says nothing about the branch that bypasses next_heading.

**Why it matters:** The test is structurally incapable of proving the shared-function claim it names. Behavioral projection equality is valuable but is a different obligation.

**Required disposition before admission:** Align the structural verification obligation with the actual shared D-01 primitives and define the projection's observation phase. Do not treat next_heading identity as proof of departure/boarding identity.

### I-11 — The implementation plan retains an obsolete test and incompatible completion gates

Severity: MEDIUM

**Rule / documents involved:** `plans/implementation_plan.md` cuts 2–5, 9–10, opening order rule and Cross-cut obligations; `testing_contract.md` §1; `cpoc_design.md` §8.

**Observed problem:** Cut 5 requires `cost_based_marginal_nonnegative`, which revision 4 replaced with `cost_based_marginal_equals_projection_delta` including a negative term. The sequential-cut completion rule also conflicts with CPOC §8: no cut touching the tick procedure, Passenger/Elevator fields, or History may be complete without the witness, but that witness is not built until cut 10.

**Concrete counterexample or proof gap:** The negative-cost trace below lawfully produces marginal −66, so the old cut-5 test rejects it. Cut 3 cannot be called complete before cut 10, while each later cut depends on earlier cuts; cut 9 expressly says its required CPOC is not yet passed. No staged-completion exception resolves the cycle. Some broad cut-3 test requirements also reference capabilities scheduled for later cuts.

**Why it matters:** Following the plan literally either rejects revision-4 semantics or requires violating its own completion gates. This is a plan-admission blocker, independently of the governing-design disposition.

**Required disposition before admission:** Reconcile every cut's test names, prerequisites, applicability, and completion standing with revision 4. Plan admission remains separate; this audit does not execute or amend the plan.

### I-12 — Numeric reporting is undefined for ordinary valid runs

Severity: MEDIUM

**Rule / documents involved:** `evaluation_design.md` §§4–5; `simulation_semantics.md` §6 empty Trace; `testing_contract.md` §§1, 4; plan cut 6.

**Observed problem:** Population standard deviation is required to be computed in exact rational arithmetic even though it need not be rational. Observation rules do not define a zero-mean tail ratio or empty-population behavior. Decimal rounding is not fully pinned.

**Concrete counterexample or proof gap:** Waits [0,0,1] have population standard deviation sqrt(2)/3, not a rational number. W-A has mean wait=0 and p95=0, so rule 1 divides 0 by 0. The valid empty Trace has no maximum-wait passenger, percentile, or mean. “No passengers” does not specify the canonical output fields or observation suppression.

**Why it matters:** Ordinary fixtures can make reporting fail or yield materially different canonical summaries, affecting repeat-execution and CPOC equality. Exact rational variance does not make its square root rational.

**Required disposition before admission:** Specify numerical rendering and undefined/empty cases, and require reporting checks for them. This needs a reporting contract, not an implementation's silent choice of zero, null, omission, or exception.

### I-13 — Experiment generation and identity inputs are not fully closed

Severity: MEDIUM

**Rule / documents involved:** `evaluation_design.md` §§2, 6.1–6.3; `authority_model.md` rows 17–19 and §6; `architecture.md` §4.

**Observed problem:** Several scenario recipes leave consequential choices unstated, including burst-centre/window sampling and boundary treatment, how concentrated floor sets are supplied/selected, and infeasible sparse-gap parameters. Generator reproducibility is explicitly limited to the same CPython minor version, but that version is not a declared experiment identity input. The Experiment block says code identity is recorded at runtime without specifying whether it is resolved before hashing the definition.

**Concrete counterexample or proof gap:** For a burst near time zero, clipping negative draws and redrawing them are both compatible with “a narrow window” and produce different traces. A sparse request count/horizon/gap combination may be impossible, yet there is no stated refusal or adjustment rule. Two environments can have the same Git-based identity while the generator's documented reproducibility precondition differs.

**Why it matters:** The claim that a definition/id reproduces every run and metric is stronger than the declared input and generation contract. Different code implementations may legitimately have different identities, but that does not fill in missing design semantics or environment binding.

**Required disposition before admission:** Close the consequential scenario choices, invalid-parameter behavior, and identity timing/environment requirements. Keep generated Trace authority and informational provenance distinct.

### I-14 — The required position-log file contradicts the source row format

Severity: HIGH

**Rule / documents involved:** Source PDF p. 2, Output / Elevator Positions Log; `simulation_semantics.md` §3; `evaluation_design.md` §3; `README.md` §2.

**Observed problem:** The source requires one row per timestamp showing all elevator positions. The design's required `position_log.csv` has one row per `(t, elevator_id)` with columns `t, elevator_id, floor, heading, load`.

**Concrete counterexample or proof gap:** With three elevators at tick 0, the source calls for one timestamp row containing their positions; the designed required output contains three rows. Internal TickRecords already group elevators, but the designated deliverable does not. No additional source-format file is specified.

**Why it matters:** The required output cannot simultaneously have both mandated row shapes. This is an actual source-contract mismatch, not a preference for a different internal representation.

**Required disposition before admission:** Resolve the source-facing deliverable format explicitly with the owner. The auditor does not silently add another export or reinterpret “one row per timestamp.”

### I-15 — The supplied passenger ID has no defined input treatment

Severity: MEDIUM

**Rule / documents involved:** Source PDF p. 2 Input; `constitution.md` §2 Request/Trace/Passenger; `authority_model.md` row 2; `architecture.md` §8; plan cuts 1 and 8.

**Observed problem:** The source asks for a function accepting request rows `time,id,source,dest`, where id is a unique passenger ID. The canonical Request has only time/origin/destination, and passenger_id is generated by sorted position. The design does not specify the public input function, source-ID validation, or mapping to internal IDs.

**Concrete counterexample or proof gap:** Input IDs `passenger1` and `passenger2` are replaced by 0 and 1, with no declared mapping or duplicate-ID behavior. An adapter could resolve this, but no adapter contract establishes what it must retain or refuse. Adding one mentally would repair the subject of the audit.

**Why it matters:** Two implementers can accept different input shapes or silently discard source identity. If source identity becomes a canonical fact, implementation would require an undeclared ontology/authority decision.

**Required disposition before admission:** Define how the required input function and unique supplied ID relate to internal request/passenger identity, including validation and any reporting/provenance obligations. Do not infer a requirement for string IDs internally; the gap is the absent boundary contract.

### I-16 — Several requirements are falsely attributed to the source brief

Severity: LOW

**Rule / documents involved:** Source PDF pp. 1–3; `simulation_semantics.md` §2.1; `scheduler_design.md` §1; `assumptions_and_tradeoffs.md` §2 heading; `README.md` §2.

**Observed problem:** The actual three-page brief does not prescribe a tick-step ordering, contain a §22, request four AIE strata, or state that AI assistance is permitted and human assistance prohibited. Those assertions are attributed to the brief in the documents. CPOC, Monte Carlo, and a web UI are repository extensions, not requirements in this PDF.

**Concrete counterexample or proof gap:** A reviewer following “the brief's §22” cannot find it. The claimed rejected record-after-move order is not specified in the supplied source. An additional owner brief may have existed, but no such source was supplied or located in the repository.

**Why it matters:** Source fidelity requires distinguishing source requirements from later owner instructions and chosen design assumptions. The extra features are not rejected merely because they are extensions.

**Required disposition before admission:** Correct or substantiate these attributions in a subsequent owner/author revision. Preserve legitimate owner requirements while naming their actual source.

### I-17 — W-D's negative variant expects the wrong first refusal

Severity: LOW

**Rule / documents involved:** `worked_examples.md` W-D negative variant; `cpoc_design.md` §5 rules 7–8; `authority_model.md` §5.

**Observed problem:** W-D changes p1 from WAITING to COMPLETED without adding pickup/dropoff fields and expects `HISTORY_INCONSISTENT`. The loader checks standing/field consistency first.

**Concrete counterexample or proof gap:** p1 still has null pickup_time and dropoff_time. Rule 7 fails before rule 8 can compare ALIGHTED events. The stated first-failure contract yields `STATE_INCONSISTENT`.

**Why it matters:** An example-derived negative test would reject a loader obeying the governing order. The governing loader order wins; the example does not amend it.

**Required disposition before admission:** Correct the illustration or its constructed corruption in a later author revision. W-D's separate boundary-marker problem is I-04.

### I-18 — Revision-4 propagation and record claims remain stale

Severity: LOW

**Rule / documents involved:** `constitution.md` §4.2; `architecture.md` §1 diagram; plan status line; `README.md` §1; `current_work.md` §3; initial audit Pass 4; `scheduler_design.md` §§5, 9.

**Observed problem:** The constitution says floor and heading both change in the motion step, despite distinct Head and Move transitions. The architecture diagram still calls project “next_heading iterated,” omitting D-01's departure/boarding mechanics. The plan header still says admission occurs in current_work, although its last section was repaired. README still says total time is a cost term. Current-work lists five examples and 31 findings in its inventory despite seven examples and 35 prior findings. Scheduler §5 asserts microsecond projection timing without implementation evidence; §9's claim that small calibration errors imply no value in a demand model is stronger than that observation establishes.

**Concrete counterexample or proof gap:** A reader can follow the stale plan header or README and contradict the current decision record or cost formula. A shared next_heading alone omits the promised-departure branch. No benchmark establishes the stated timing. Small errors under one policy do not prove that alternative demand-informed decisions have no value.

**Why it matters:** These are record/restatement defects where the controlling operational rule or evidence limitation is identifiable. They still defeat the claim of complete propagation. The obsolete cut-5 test is separately MEDIUM in I-11 because it is an executable plan obligation.

**Required disposition before admission:** Reconcile the stale derivative statements and unsupported claims in a new revision. Do not rewrite the historical audit; append a correction/re-audit as required by repository rules.

### I-19 — Historical UI reads admit a tick with no historical record

Severity: MEDIUM

**Rule / documents involved:** `ui_design.md` §2.2; `simulation_semantics.md` §2 step 9; `cpoc_design.md` §§2–3; `constitution.md` N11; `testing_contract.md` §8.

**Observed problem:** The history endpoint permits any `k <= t`, but a RUNNING engine at boundary t has executed only ticks through t-1. At creation, t=0 and there is no TickRecord at all.

**Concrete counterexample or proof gap:** Immediately after executing tick 0 and advancing to t=1, request `/tick/1`. The UI contract permits it, but a historical view for 1 cannot be rendered from the required records. Returning current state violates the stated historical source; refusing is not the documented permitted-range behavior. The existing history test only checks a past tick before/after another step.

**Why it matters:** This is a same-tick API ambiguity at the exact historical/present-state boundary the design intends to protect.

**Required disposition before admission:** Define the admissible historical range and missing-tick behavior, including the differing completed-run boundary, and require a test at creation and the current running boundary.

## Worked-example verification

All movement computations below use the governing order: reveal/assign, alight, establish departure/board, head, record, terminate, move, advance. No example was treated as authority. An arrow in the heading sequences is the movement after that tick's recorded floor. FREE is temporary departure status, not a fourth stored heading.

| Example | Verdict | Independent arithmetic / semantic verification |
| --- | --- | --- |
| W-A | PASS | Ticks 0–3: floors `[0,1,2,3]`, headings `[UP,UP,UP,NONE]`, loads `[1,1,1,0]`. At 0 FREE becomes UP on boarding; at 1–2 destination 3 keeps UP; at 3 alighting leaves FREE and no stops, hence NONE. p0 pickup/dropoff 0/3; wait/travel/total 0/3/3. Final tick 3. |
| W-B | PASS | Ticks 0–8: floors `[0,1,2,3,4,3,2,3,4]`, headings `[UP,UP,UP,UP,DOWN,DOWN,UP,UP,NONE]`, loads `[1,1,1,1,0,0,1,1,0]`. Tick 2 is compatible but full; tick 4 alights p0 then reverses; tick 6 is FREE and p1 sets UP. p0 0/4 gives 0/4/4; p1 6/8 gives 6/2/8. One capacity deferral, no wrong-way pass. p1 Tier 2. Default bound 72 exceeds final tick 8. With default age_scale=4, p1 cost is 24 and marginal 0. |
| W-C | PASS | At t=4 E0 is at 2 UP with destination 5; it visits 3/4/5 at 5/6/7, then 4/3/2/1 at 8/9/10/11. FREE at 1 lets p3 board UP at 11, alighting 4 at 14. Existing p1 still drops at 7, so marginal 0; candidate wait 7 and cost 35. E1 travels 0→1 at t=5, boards UP and reaches 4 at 8: wait 1, cost 5. Both Tier 1; cost-based chooses E1, while distance tie makes Nearest Car choose E0. Candidate travel 3, totals 4 versus 10. This example illustrates two Tier-1 choices; it does not by itself exercise Tier-1-before-Tier-2 selection despite its test-name cross-reference. |
| W-D | FAIL | Physical continuation from the stated snapshot is correct: boundary t=3, floor 3 UP, p0 onboard and p1 waiting; ticks 3–8 follow W-B, six executed ticks, final 8. It is not independently valid as written because the embedded CHECKPOINTED(t=3) conflicts with the through-t−1 Events prefix, and its negative variant expects the wrong first refusal (I-04, I-17). The block is explicitly abridged; omission of the displayed full Trace/Configuration is not itself charged as a missing-field defect. |
| W-E | PASS | With N=1, proposal 1 is invalid at tick 0 step 2. The revealed event is discarded, no assignment or TickRecord commits, and History is STARTED plus HALTED identifying tick/step/reason. There is no summary. This conforms to the constitutional halted-tick exception; the generic position-completeness wording must be read with that exception. The claimed RUN_FINAL refusal remains conditional on resolving I-02. |
| W-F | PASS | Ticks 0–7: floors `[0,1,2,3,4,3,2,1]`, headings `[UP,UP,UP,UP,DOWN,DOWN,DOWN,NONE]`, loads `[1,1,1,1,0,0,1,0]`. At 2 the down-bound p1 fails direction even though full, so this is not capacity deferral. At tick 6 FREE permits DOWN boarding; pickup/dropoff 6/7, wait/travel/total 6/1/7. One wrong-way pass, no capacity deferral, Tier 1. Default cost for p1 is 24, marginal 0. |
| W-G | PASS | Ticks 0–8: floors `[4,5,6,5,4,3,2,1,0]`, headings `[UP,UP,DOWN,DOWN,DOWN,DOWN,DOWN,DOWN,NONE]`, loads `[0,1,0,0,0,1,1,1,0]`. Idle tie goes UP; FREE at 5 boards p0 UP; at 6 p0 alights and the car turns DOWN; FREE at 3 boards p1 DOWN. p0 pickup/dropoff 1/2, wait/travel/total 1/1/2. p1 5/8, wait/travel/total 5/3/8. No capacity deferral, both finish at/before 8; default bound 108. This refutes the rejected turn-away rule, not every possible liveness counterexample. |

Halt atomicity was also checked beyond W-E: if a second same-tick proposal fails after the first succeeds, constitution §4.3 discards the tick's earlier ASSIGNED and REVEALED events with the tick. No partial checkpoint is allowed. The named invalid-proposal fixture alone does not exercise that rollback-after-an-earlier-success case; the atomicity rule must remain an explicit implementation verification obligation.

## Revision-4 special review

### D-01 direction-compatible boarding

For lawful reachable states, the local movement rules are deterministic. An onboard passenger's destination remains ahead after boarding in its direction; LOOK cannot reverse while that stop remains ahead. Zero dwell and one floor per tick then give travel exactly equal to distance, including when later assignments add stops. Alighting before boarding prevents an old completed destination from incorrectly keeping departure committed.

The additional hand cases considered were:

- Multiple opposite-direction passengers at one floor: an idle/reversal FREE car takes the lowest-id fitting passenger, fixes D, and skips incompatible passengers even if room remains. A full car continuing a sweep records capacity deferral only for compatible passengers; W-F correctly classifies the full-and-wrong-way case as direction deferral.
- Capacity freed at a stop: alighters leave before the first compatible boarder; capacity is checked per boarding, not once per floor.
- Stops on both sides: existing stops ahead retain heading; with no stop ahead, a local boarder's promise can override which remaining stop is nearer. This is an intentional D-01 rule, not a conflict with the step-5 fallback.
- A new request at a reversal tick: assignment precedes departure computation, so a new stop farther ahead can eliminate FREE for that tick. It may delay a waiting opposite-direction passenger; it cannot reverse an onboard passenger away from a destination still ahead.
- An old origin repeatedly behind a sweep: finite demand eventually stops adding requests, but boarding can still add destinations. The examples did not strand a passenger; the general progress bound remains unproved as written (I-07).

No concrete FREE-induced oscillation under the actual rule was found. A full car cannot lawfully be at a sweep end with unresolved onboard destinations all behind it if P12 has held; that would itself indicate an invalid state. This reasoning does not excuse the loader's acceptance of such a state in I-06.

### Liveness proof and bound

The bound is policy-independent in intention and appropriately excludes unbounded adversarial demand. The flaw is proof closure, not a demand for an optimal bound. W-G explicitly invalidates the shrinking-stop-set premise. The text does not derive a maximum delay between irreversible passenger-progress events or charge all sweep extensions to P. Sampled property and Monte Carlo runs cannot supply that missing universal argument. Default and user-overridden short horizons must also remain distinct when reporting a halt.

### Cost function after removal of `w_total`

Removal of a separate total-time term is coherent because `total_c = wait_c + fixed trip distance` for this candidate. Total time still varies across elevators through wait; it is redundant, not constant across candidates. Removing a weighted total term also changes the effective wait-versus-marginal weighting relative to revision 3; the decision record explicitly authorizes the new formula, so this is not an unauthorized change.

All five cost-driving parameters (`w_wait`, `w_marginal`, `w_tail`, `tail_threshold`, `age_scale`) are in Configuration and therefore run_id. There is no retained policy state. The candidate comparison is lexicographic by tier, exact integer cost, then elevator id. Baselines are stateless and honestly named.

The closed SchedulerView excludes future and later-unassigned same-tick requests. It contains request_time for waiting passengers but not onboard passengers. The literal marginal formula mentions age for all committed passengers; under P12 the onboard passengers' with-minus-base dropoff delta is identically zero, so their contribution is zero without recovering request_time. This does not justify expanding the view or importing the Trace. No hidden input is necessary for the nonzero terms.

### Negative marginal terms

Negative marginal and negative total cost are lawful and have the same integer scale as positive values. This hand-computed reachable one-car trace confirms the revision-4 case the obsolete plan test would reject:

Configuration F=8, N=1, C=1, initial floor 0. At t=0: p0 is 5→0 and p1 is 5→6, in that order. At t=4 a candidate p2 requests 6→7. The elevator is then at floor 4 heading UP.

| Projection | Essential service sequence | Dropoff p0 | Dropoff p1 | Candidate pickup/dropoff |
| --- | --- | --- | --- | --- |
| Base without p2 | At 5/t5 FREE boards older p0 DOWN; alight at 0/t10; return to 5/t15 and board p1 UP | 10 | 16 | — |
| With p2 | Stop 6 keeps UP at 5/t5, skips p0 and boards p1; at 6/t6 p1 alights and p2 boards; p2 alights 7/t7; return to 5/t9 and board p0 DOWN | 14 | 6 | 6/7 |

At decision t=4 both existing passengers have age 4 and default age_scale=7. Thus marginal is `(7+4) * ((14-10)+(6-16)) = -66`. Candidate wait=2, tail penalty=0, and cost=`7*2-66=-52`. Neither existing passenger nor candidate incurs capacity deferral; direction changes are not capacity failures, so this candidate is Tier 1.

There is no semantic requirement for costs to be nonnegative. Age weighting magnifies improvements to older passengers as well as harms; a negative marginal can outweigh candidate wait and its tail penalty. Consequently the policy may prefer a longer wait for the candidate to accelerate others. This is consistent with a system-cost heuristic and soft fairness terms, but it is not a per-passenger fairness guarantee or a proof of optimization. No clamping, extra normalization, or hidden fairness rule was supplied by this audit.

### D-06 checkpoint semantics

The default is consistently no checkpoint in batch, Monte Carlo, and interactive runs. Explicit checkpoint and interval controls are present. Loss of an uncheckpointed UI session is expressly accepted by the owner and does not fail the declared boundary.

With interval k>1, process death can lose completed but uncheckpointed ticks as well as an in-progress tick; continuation begins at the last durable checkpoint. CPOC §2's wording about losing the in-progress tick must not be read as a promise to preserve every completed tick. The interval's ownership/persistence and its effect on operational markers need classification (I-01, I-04). No stale every-UI-tick default remains in the actual control contract.

### OSA authority sweep

This inventory was derived from uses of facts throughout the documents, then compared with the table. A row's existence was not taken as proof of ownership closure. In the following table, A/D/R/E mean AUTHORITATIVE/DERIVED/RECEIPT/EPHEMERAL. “Gap” identifies missing registration or conflicting consumption; it does not assign authority on behalf of the owner.

| Discovered fact | Stated owner, class and write boundary | Persistence / reconstruction; history or mutable standing | Lawful readers/projections and denied rights; table result |
| --- | --- | --- | --- |
| Building, capacity, initial floors, max_ticks, policy parameters | Input Configuration, A, Trace load | Immutable; embedded/hash-checked | Engine and restricted policy view; controls E and headers D. Row 1 covers it. Default horizon depends on full Trace but cannot be exposed as policy foresight. |
| Request time, origin, destination, stable input order | Trace carrier, A, Trace load | Immutable full Trace in checkpoint | Engine full access; policy revealed values only. Row 2 covers internal definitions; external supplied ID is absent (I-15). |
| Passenger visibility/existence and stable internal id | Engine; visibility D from Trace/time; Reveal | Reconstructed exact revealed set | SchedulerView excludes unassigned same-tick passengers. Row 3 covers intent but its <=t reconstruction wording conflicts with boundary <t. |
| Current time | Engine, A, Advance | Mutable; checkpoint | Browser guard only, never time selector. Row 4 covers it. Initial creation is separately implied by Trace load. |
| Assignment and assigned_at | Engine, A, Assign; event R | Immutable once set; checkpoint plus consistency check | Policy proposes; cannot rewrite. Row 5 covers it. |
| Floor and heading | Engine, A, Move and Head respectively | Mutable; checkpoint, checked against historical boundary | Logs/shaft/arrow D, TickRecords R. Rows 6–7 cover them; heading load check incomplete (I-06). |
| Passenger standing WAITING/ONBOARD/COMPLETED | Engine; Assign/Board/Alight in constitution | Mutable until completion; checkpoint | No policy/browser writes. Row 12 only explicitly maps completion; full lifecycle/carrier coverage is incomplete. |
| Pickup/dropoff | Engine, A write-once, Board/Alight | Historical once set; checkpoint and matching Events | Summaries D, never estimates. Rows 10–11 cover them. |
| Load, onboard/waiting sets, committed stops | Engine-derived from Passenger standing/assignment | Recompute; no stored authoritative list | Mechanical route/boarding and displays consume exact current inputs. Row 8 names load; sets/stops appear in prose and checkpoint exclusions, without full individual registration. |
| Route | Engine-derived through pure mechanics, D | Recompute, never persisted as authority | Scheduler projection E and UI strip D; cannot establish future intent. Row 9 covers intent, but its LOOK-only description omits D-01 mechanics. |
| departure_E and FREE/reversal classification | Computed in engine Board from current floor/heading/stops and ordered boarders | Intra-tick value; no persistence necessary if derivation is exact | Selects Head; must not be independent persistent elevator state. No corresponding exact-fact class/rights row (I-01). |
| Projected times, costs, tiers, first compatible arrival, projected capacity/direction deferral | Policy computation E; engine copies receipt in Assign | Projection discarded; immutable receipt retained in History | Candidate selection only; no realized Passenger fields. Row 13 plus scheduler §5 covers estimates; no estimate becomes outcome. |
| Realized capacity deferrals and wrong-way-pass counts | Reporting D from historical arrivals, boardings and passenger status | Recompute from retained History, not current waiting list | Passenger output and observations only; no write-back. Reporting outputs named in sweep, but exact facts and classifications not enumerated in 22 rows. |
| Events, TickRecords, board/alight order | Engine R at transition/Record boundaries | Append-only, prefix persisted | Historical queries; never substituted for snapshot present state. Rows 14–15 cover them; operational marker identity unresolved (I-04). |
| Position/passenger files, summary, observations, calibration | Reporting D | Regenerate from canonical records | Cannot feed state back. Rows 15–16 and sweep cover most outputs; required source row shape conflicts (I-14). |
| Run standing, halt reason, final tick, durable finality | Engine transition described in constitution | Final standing immutable; durable carrier not registered | Results D; loader nevertheless consumes final-result existence. No closed table row; I-01–I-02. |
| run_id, configuration/Trace hashes | Content derivation at Trace load | Embedded and recomputed | Bind identity, never choose latest file. References throughout table; executing-code binding not closed (I-03). |
| code_identity and schema_version | Code/configuration checks described, but no complete owner/class/write registration | Immutable for a claimed execution/schema; embedded, checked | Both decide load legality. Architecture alone supplies code identity recipe; authority registration absent. I-01, I-03. |
| Checkpoint snapshot and resumed object graph | Engine A carrier at write/load | Boundary snapshot plus preserved History | Only loader establishes resumed present; no fallback, no partial load. Rows 21–22 cover them, subject to I-02/I-04/I-06. |
| Checkpoint-at/interval/pause controls | CLI or UI request; engine performs boundary write | Control lifetime and resumption treatment not fully classified | May alter operational History, must not alter simulation decisions. No exact-fact authority entry. I-01/I-04. |
| Output directory and final-result existence | Caller supplies directory; result currently D | External file existence survives independently of checkpoint | Intended ordinary coordinate becomes finality selector. Not an innocuous E path under current rule. I-02. |
| Scenario recipe/seed and generated Trace | Harness A definition, generation boundary; generated Trace binds as A input | Definition persisted; regenerate with stated environment qualification | No engine RNG. Rows 17–18 cover them; incomplete recipe/identity closure I-13. |
| Experiment definition and Experiment id | Harness; definition A in §6 carrier sweep; id content-derived | Definition file; immutable experiment binding intended | Cannot alter a Run. Table row 19 names results, not complete definition/id registration; I-01/I-13. |
| Experiment results and paired comparisons | Harness D; execution file R | Regenerable from runs; receipt historical | Evidence, not scheduler input. Row 19 covers intent; §6's blanket prohibition on harness reading derived output facts needs reconciliation with this consumption. |
| Scenario provenance | Informational D label | Embedded; may be checked against regenerated Trace | Cannot affect load/continuation; mismatch reported by harness. §6 sweep covers it; no hidden seed authority. |
| UI session id/pointer, play/pause, form state, from_time | Server/browser E with split roles, request handlers | Safely lost; recreate from checkpoint/new Run | No simulation decision right; from_time checked against engine t. Row 20 and sweep cover session id=run_id. Historical range gap I-19. |
| written_at, PID/argv/environment witness metadata | Informational evidence, not simulation input | Checkpoint/evidence records as specified | Cannot decide assignment or substitute state. Denied decision use is explicit for written_at; evidence must remain evidence. |
| Test input and expected fixtures | Input Trace A for that test; expected result evidence | Fixture files with hashes | Expected output never overrules governing rules; sweep covers this. |

No duplicate policy-owned pointer or browser-owned simulation state was discovered. OSA still fails because exact carrier closure and finality authority do not follow from those successes.

### CPOC design

The intended process boundary is well chosen: complete tick, durable snapshot, kill A while paused and live, wait for signal termination, launch a distinct B, and compare with separate R. The full future Trace belongs in the checkpoint, while load, routes, sets and summaries are correctly excluded as independent authority. B does not need a seed, fixture file, old policy object, or browser session. Provenance mismatch is correctly informational.

The witness cannot yet establish its claimed conclusion because of I-02 through I-06. Specifically, directory-relative finality can be bypassed; code mismatch retains an incompatible identity; marker and sequence normalization is undefined; prohibited history-derived reconstruction can pass the observations; and loader checks can accept a corrupted heading. The altered-future-request witness's copied prefix is identical by construction, so that equality alone proves nothing about prior decisions; its continuation comparison and the independent in-process mutation test are necessary, with the termination exception resolved by I-08.

All negative-witness rows were reviewed: missing authority, stale checkpoint, corrupt/truncated input, incomplete history, config hash edits, altered request stream, provenance/seed edits, projection disagreement, future leakage, passenger resurrection, transient inputs, and process-local continuation. There are twelve table rows, despite “eleven” in the plan/adoption description. Hash-edit refusals and actual process-local rejection have clear intended effects. The stale-output and reconstruction cases above remain uncovered. The heading mutation provides an additional concrete missing negative case. The witness has not run; no continuity standing beyond design-only is earned.

### Implementation-plan compatibility

| Cut | Revision-4 review |
| --- | --- |
| 1 Domain | No direction-agnostic field is demanded. Source-ID boundary and omitted authority facts must be resolved first. |
| 2 Route | Departure cases were added, but “half: identity” of the engine heading function is not an executable proof before engine construction and does not cover shared D-01 boarding. |
| 3 Engine | Refers to current semantics, so D-01 should apply. Broad “all” invariant/behavioral obligations include later-capability dependencies; completion is blocked by the CPOC gate cycle. |
| 4 Baselines | Stateless definitions remain compatible. No-look-ahead comparisons need the I-08 scope correction. |
| 5 Cost | Materially stale `cost_based_marginal_nonnegative`; negative terms are lawful. No w_total cost is required by this cut's contract. |
| 6 Reporting | Current wrong-way and capacity metrics are reached by reference. Source output shape and numeric edge definitions are unresolved. |
| 7 Scenarios | No new infrastructure; generator choices and invalid parameter handling need closure. |
| 8 Harness/CLI | Same-trace comparisons are compatible. Experiment identity/generation and execution-directory semantics remain unresolved. |
| 9 Checkpoint | Explicit at/every/pause controls are compatible with D-06; it does not restore every-UI-tick default. Loader/equality gaps and completion standing remain. |
| 10 Witness | Real subprocess witness intended; proof gaps above remain. Its “eleven” count is stale relative to twelve negative-witness rows. |
| 11 UI | Thin server projection and guarded steps remain; historical boundary is ambiguous. No default checkpoint-every-tick obligation remains. |
| 12 Deliverables | README commands, time log, assumptions and presentation are carried. Actual source input/output compliance must be included, not merely the README restatement. |

No operative plan requirement for detour metrics, w_total, the old liveness multiplier, or direction-agnostic boarding was found. The stale nonnegative-marginal test is a direct revision-3 survivor. Admission-by-current_work remains in the opening line even though the final admission section was repaired. These are findings, not instructions to execute any cut.

### Source-assignment fidelity

| Source requirement | Owning design / disposition |
| --- | --- |
| Configurable elevator count, floor count, passenger capacity; Python (PDF p. 1) | Constitution §2 Configuration; semantics §§1, 6; architecture §6 Python 3.12. Supported in design; exact input validation domains still need implementation contract clarity. The source's 1–10 elevators is an example, not a mandated upper limit. |
| Destination dispatch, immediate assignment, immutable destination (PDF p. 1) | Constitution §§4.1, 8, 10, N3; semantics §2 steps 1–2. Supported. Immutable assignment is an additional repository constraint; the source explicitly forbids destination modification. |
| One floor per discrete unit and tick through timestamp gaps (PDF p. 1) | Semantics §§2–3, 6 and P1/P7. Supported; no wall-clock synchronization required. |
| Function accepting time/id/source/dest (PDF p. 2) | Internal Trace model is specified, but the public function and supplied-ID boundary are not. I-15. |
| Do not peek ahead (PDF p. 2) | Closed SchedulerView and pure policies structurally support it. Input validation/checkpoint storage of the full Trace are not decision look-ahead. Equality witness scope needs I-08 resolution. |
| Every request eventually served (PDF p. 1) | P10 and semantics §8 own the claim. Proof insufficient as written, I-07; no concrete finite counterexample found. |
| Attempt to minimize wait + travel (PDF p. 1) | Scheduler §§6–8 heuristic, with travel fixed by P12. Supported as an objective without an optimality claim. |
| Capacity and direction constraints (PDF p. 1) | Semantics §§4–5, D-01. Mechanical gates supported; tier promises need I-09. |
| Positions from t=0, one row per timestamp containing all elevator positions (PDF p. 2) | Time semantics supported; designated file format contradicts the source, I-14. |
| Min/max/average wait and total, notable observations (PDF p. 2) | Evaluation §§3–5. Included, but reporting edge cases remain I-12. |
| Public GitHub repository containing Python code (PDF p. 3) | README §2 names the deliverable. Documents-only phase intentionally has no code/publication yet; this is not itself a defect. No publication was authorized or performed. |
| README how to run, time spent, assumptions/trade-offs, improvements (PDF p. 3) | README §§3–5, current-work §7, assumptions §§1–4, plan cut 12. Supported as future deliverables, with design time included by D-07. |
| Presentation readiness (PDF p. 3) | Plan cut 12 walkthrough/slides. Supported as a future obligation; presentation not claimed complete. |
| Optional different policies, express elevators, fairness/efficiency exploration (PDF p. 2) | Multiple policies and fairness reporting included. Express elevators are optional and may remain excluded. No requirement invented from the bonus list. |

The PDF does not require OSA, CPOC, Monte Carlo, a web UI, exact route projection, or the AIE framing. Their repository adoption is permitted and is audited on its own terms; it must not be misattributed to the source.

### Testing-contract adequacy and scope

The proposed movement, capacity, assignment immutability, wrong-way boarding, and travel-equals-distance checks are meaningful because they inspect Events and TickRecords against Trace inputs rather than only summary metrics. Direction and capacity have separate fixtures; the negative-marginal replacement test requires an actual negative case; cross-process determinism uses separate interpreters; historical UI reads are checked after present state changes. Those are good obligations, not executed evidence.

Defects still capable of passing named obligations include: a history-folding loader (I-05); duplicated departure/boarding implementations sharing next_heading (I-10); a stale checkpoint resumed into another directory (I-02); an invalid loaded heading (I-06); and serving current-tick “history” from present state where the existing UI test only requests older ticks (I-19). The future-mutation test can also fail a correct implementation for termination differences (I-08). The liveness tests sample the claim but do not prove its quantified bound (I-07). Zero-wait, empty-population, irrational-standard-deviation, and rollback-after-earlier-same-tick-assignment cases need explicit verification obligations.

The thin UI, pure simulation core, three policies, single JSON checkpoint and batch evaluation remain proportionate. There is no adopted database, message broker, event-sourcing state engine, WebSocket layer, generalized agent/workflow framework, solver, RL system, plugin registry, or microservice design. OSA clarifies the intended boundary but its inventory must be completed; CPOC is bounded in infrastructure but its identity/finality proof currently overclaims. Monte Carlo remains evaluation and cannot feed future demand into scheduling.

## Admission recommendation

**NOT READY FOR ADMISSION**

The owner must resolve the HIGH structural and source-contract findings and the MEDIUM proof/semantic/test gaps before governing-document admission. Low-risk record corrections alone cannot produce a pass. The implementation plan additionally requires its obsolete test and incompatible completion gates to be reconciled before its separate admission.

All nine recorded design digests matched the audited bytes; that confirms which revision failed, not that it is admitted. Existing documents and historical audits remain unchanged. No application code, test code, runtime file, implementation cut, admission act, CPOC execution, or certification is part of this audit.
