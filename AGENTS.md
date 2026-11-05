# Elevator Simulation: repository jurisdiction and routing

Status: **ROOT ROUTER. DERIVATIVE, NOT AUTHORITY. PHASE: FINAL DELIVERY (ALL TWELVE CUTS IMPLEMENTED).**

This file is the entry point for any person or agent working in this
repository. It says what the project is, which documents govern which
questions, how work moves, when to stop, and what phase the work is in. It
owns none of the project's facts and grants no authority of its own.

## What this project is

A discrete-time, destination-dispatch elevator simulation built as a
take-home assignment: configurable elevators, floors and capacity; passengers
who state origin and destination at request time and are immediately and
irrevocably assigned to one elevator; one time unit per floor of movement;
replaceable scheduler policies (Round Robin, Nearest Car, Cost-Based);
a seeded Monte Carlo evaluation harness; a durable checkpoint with a real
process-death continuation witness; and a thin server-rendered web UI.

The sophistication is in correctness, measurement, authority, reproducibility
and explanation, not in infrastructure.

## Phase rule

```text
CURRENT PHASE: FINAL DELIVERY
GOVERNING DESIGN: ADMITTED — REVISION 7.5
IMPLEMENTATION PLAN: ADMITTED
IMPLEMENTATION: COMPLETE (cuts 1 to 12; standing in docs/current_work.md)
CURRENT AUTHORIZED CUT: NONE
```

The governing design is admitted at revision 7.1 by
[docs/decisions/owner_decision_006_revision_7_1_admission.md](docs/decisions/owner_decision_006_revision_7_1_admission.md),
which names the nine admitted files and their exact SHA-256 digests, as
amended to revision 7.2 by
[docs/decisions/owner_decision_008_invariant_violation_halt.md](docs/decisions/owner_decision_008_invariant_violation_halt.md)
(the `INVARIANT_VIOLATION` halt reason; new digests for semantics, testing
contract and plan) and to revision 7.3 by
[docs/decisions/owner_decision_009_policy_construction_edges.md](docs/decisions/owner_decision_009_policy_construction_edges.md)
(policy construction edges; new digest for the architecture) and to revision 7.4 by
[docs/decisions/owner_decision_011_ui_contract_reductions.md](docs/decisions/owner_decision_011_ui_contract_reductions.md)
(UI contract reductions; new digest for the UI design) and to revision 7.5 by
[docs/decisions/owner_decision_012_ui_execution_metadata_downloads.md](docs/decisions/owner_decision_012_ui_execution_metadata_downloads.md)
(conditional execution-metadata downloads; new UI design digest); the
admitted bytes are never edited in place (their draft status lines are
superseded by that record). The implementation plan is admitted by
[docs/decisions/owner_decision_007_implementation_plan_admission.md](docs/decisions/owner_decision_007_implementation_plan_admission.md).
Implementation proceeds cut by cut in the plan's order; the current
authorized cut and each cut's verified standing are recorded in
[docs/current_work.md](docs/current_work.md) and in the cut's
implementation record under `docs/implementation/`. Work outside the
current authorized cut, a change to an admitted governing document, or a
change to the admitted plan is a stop: it returns to the decision process
with a declared delta. Every governed entry point and every test process
runs under the supported execution contract (`python -B`, no `__pycache__`
inside `elevator/`). The cut-10 witness has run and passed for the local Store and process model (docs/cpoc/).

## Controlling documents and precedence

| Question or work | Read |
| --- | --- |
| What the system is, its canonical objects, consequential facts, lawful transitions, what may never happen, what admission and completion mean | [docs/constitution.md](docs/constitution.md) |
| Who owns each fact, its representation class, writers, readers, persistence and reconstruction | [docs/authority_model.md](docs/authority_model.md) |
| The exact tick order, position-log semantics, boarding, direction, reversal, capacity, termination, edge cases | [docs/simulation_semantics.md](docs/simulation_semantics.md) |
| How a passenger is assigned: the decision, its lawful information, the cost function, baselines, ties, fairness | [docs/scheduler_design.md](docs/scheduler_design.md) |
| Scenario generation, metrics, Monte Carlo reproducibility, fair comparison, claim boundaries | [docs/evaluation_design.md](docs/evaluation_design.md) |
| What must survive process death, the checkpoint, the continuation witness, negative witnesses | [docs/cpoc_design.md](docs/cpoc_design.md) |
| The component separation, package boundaries, data flow, what is deliberately absent | [docs/architecture.md](docs/architecture.md) |
| The screen, controls, projections, evaluation mode, what the browser may hold | [docs/ui_design.md](docs/ui_design.md) |
| Which tests must exist before any rule is claimed, by category | [docs/testing_contract.md](docs/testing_contract.md) |
| Every assumption the take-home left open and how it was resolved, with its source; trade-offs; what more time would buy | [docs/assumptions_and_tradeoffs.md](docs/assumptions_and_tradeoffs.md) |
| Which engineering doctrine was adopted from where, and what was deliberately not adopted | [docs/doctrine_adoption.md](docs/doctrine_adoption.md) |
| The owner's decisions D-01 to D-07 on revision 3 (historical to revision 4) | [docs/decisions/owner_decision_001_design_choices.md](docs/decisions/owner_decision_001_design_choices.md) |
| The revision-5 dispositions D-08 to D-14 (historical to revision 5; superseded in part by decision 003) | [docs/decisions/owner_decision_002_revision_5_repairs.md](docs/decisions/owner_decision_002_revision_5_repairs.md) |
| The revision-6 dispositions D-15 to D-22 (proposed; stand unless 004 says otherwise) | [docs/decisions/owner_decision_003_revision_6_repairs.md](docs/decisions/owner_decision_003_revision_6_repairs.md) |
| The revision-7 dispositions D-23 to D-28 (still proposed; revision-7 digests are historical) | [docs/decisions/owner_decision_004_revision_7_closure.md](docs/decisions/owner_decision_004_revision_7_closure.md) |
| The independent audits of revisions 4, 5 and 6 and the author's repair matrices | [docs/audits/independent_revision_4_audit.md](docs/audits/independent_revision_4_audit.md), [docs/audits/revision_5_repair_record.md](docs/audits/revision_5_repair_record.md), [docs/audits/independent_revision_5_audit.md](docs/audits/independent_revision_5_audit.md), [docs/audits/revision_6_repair_record.md](docs/audits/revision_6_repair_record.md), [docs/audits/independent_revision_6_closure_audit.md](docs/audits/independent_revision_6_closure_audit.md), [docs/audits/revision_7_repair_record.md](docs/audits/revision_7_repair_record.md) |
| Revision-7.1 component mapping, exact proposed-admission digests and bounded review scope | [docs/decisions/owner_decision_005_revision_7_1_mapping.md](docs/decisions/owner_decision_005_revision_7_1_mapping.md) |
| The owner's admission of the governing design at revision 7.1 (exact files and digests) | [docs/decisions/owner_decision_006_revision_7_1_admission.md](docs/decisions/owner_decision_006_revision_7_1_admission.md) |
| The owner's admission of the implementation plan (exact digest, cut order, Cut 1 authorized) | [docs/decisions/owner_decision_007_implementation_plan_admission.md](docs/decisions/owner_decision_007_implementation_plan_admission.md) |
| The owner's revision-7.2 delta: the `INVARIANT_VIOLATION` halt reason and the three re-admitted digests | [docs/decisions/owner_decision_008_invariant_violation_halt.md](docs/decisions/owner_decision_008_invariant_violation_halt.md) |
| The owner's revision-7.3 clarification: `policies` as a construction-only dependency of `api`, `harness`, `checkpoint` and `web`, and the re-admitted architecture digest | [docs/decisions/owner_decision_009_policy_construction_edges.md](docs/decisions/owner_decision_009_policy_construction_edges.md) |
| The owner's revision-7.4 UI-contract reductions (no partial live metrics, no projected stops, no scenario/seed controls on the single-run screen) and the re-admitted UI design digest | [docs/decisions/owner_decision_011_ui_contract_reductions.md](docs/decisions/owner_decision_011_ui_contract_reductions.md) |
| The owner's revision-7.5 clarification: execution-metadata download only where metadata was persisted, never fabricated, and the re-admitted UI design digest | [docs/decisions/owner_decision_012_ui_execution_metadata_downloads.md](docs/decisions/owner_decision_012_ui_execution_metadata_downloads.md) |
| The owner's definition of the fixed Experiment (values, validation, evidence rules, timing treatment) and the harness-dependency decision | [docs/decisions/owner_decision_010_fixed_experiment.md](docs/decisions/owner_decision_010_fixed_experiment.md) |
| Per-cut implementation records: files, tests, counts, deltas, standing | `docs/implementation/` |
| Revision-7 findings and revision-7.1 author repair evidence | [docs/audits/independent_revision_7_closure_audit.md](docs/audits/independent_revision_7_closure_audit.md), [docs/audits/revision_7_1_repair_record.md](docs/audits/revision_7_1_repair_record.md) |
| Concrete tick-by-tick traces of the rules, including a crash and recovery | [docs/worked_examples.md](docs/worked_examples.md) |
| The checklist an independent auditor runs before admission | [docs/audits/whole_design_audit_checklist.md](docs/audits/whole_design_audit_checklist.md) |
| What was found wrong, with what severity, and whether it was repaired | [docs/audits/initial_design_audit.md](docs/audits/initial_design_audit.md) |
| Build order, per-cut contracts, tests, evidence and deltas, once admitted | [docs/plans/implementation_plan.md](docs/plans/implementation_plan.md) |
| Current phase, what exists, open questions, admission status (the session handoff) | [docs/current_work.md](docs/current_work.md) |
| Orientation, how to run (future), time spent, assumptions summary | [README.md](README.md) |
| How the public repository must read (memo-shaped README, one public design document, governance corpus as evidence) | [docs/presentation_guidance.md](docs/presentation_guidance.md) |

Precedence, for a conflict about the same consequential rule:

1. `docs/constitution.md` governs what the system is and what may never
   happen. Nothing overrides it except an explicit owner decision recorded in
   `docs/decisions/`.
2. `docs/authority_model.md` governs who owns a fact and through what; it is
   subordinate to the constitution and must agree with it.
3. `docs/simulation_semantics.md`, `docs/scheduler_design.md`,
   `docs/evaluation_design.md`, `docs/cpoc_design.md` and
   `docs/ui_design.md` each govern their own jurisdiction, stated at their
   top, and must agree with 1 and 2.
4. `docs/architecture.md` is descriptive. It maps the above to components; it
   decides no semantic question.
5. `docs/testing_contract.md` and `docs/plans/implementation_plan.md` are
   obligations and proposals; they decide no semantic question.
6. `docs/worked_examples.md` illustrates; where an example and a rule
   disagree, the example is wrong.
7. Audits are evidence. `docs/decisions/` records what the owner decided and
   admitted, and is the only place admission is recorded.
   `docs/current_work.md` is a record. `README.md` is orientation. None of
   them governs a simulation rule; a decision record changes standing.

A lower document that disagrees with a higher one is wrong and must be
repaired; it never wins by being more specific, more recent or more detailed.
Two documents at the same level that disagree are a **STOP** (below).

## Authority rule

Authority is scoped by exact governed fact. Every consequential fact has one
lawful owner, one commit boundary through which it changes, and every other
copy is classified as `DERIVED`, `CACHE`, `RECEIPT`, `LEGACY_ONLY` or
`EPHEMERAL` with no decision right. Do not infer who owns a fact from a file
or directory name, root proximity, recency, what code happens to do, what
persists, a passing test, an audit's wording or a document's own claim. The
ownership map is [docs/authority_model.md](docs/authority_model.md); the
rules it is judged by are in [docs/constitution.md](docs/constitution.md).

Three boundaries are absolute in this project:

- the **simulation engine** is the only authority for runtime simulation
  state and the only writer of committed assignments, and is itself bound
  by the constitution's negative invariants;
- the **loader** constructs state from a Continuation Document's typed
  snapshot only, by `(store, execution_id)`, and never from History, a
  file path, an output directory, another Execution or different code;
- a **scheduler policy** proposes; it never owns, writes or retains canonical
  state, and never sees a request before its request time;
- the **browser** displays; it never owns any consequential simulation fact.

## Engineering motion

```text
Audit -> Plan -> Implement -> Verify
```

These are working functions, not ceremonies. This phase is Audit and Plan.
Before any future Implement, for every fact the change reads, writes, derives
or selects, state its owner and carrier from the authority model, whether the
change adds a second carrier or writer for it, and whether it adds anything
that chooses among competing values. State the **Constitutional Delta**
(ontology, semantics, authority: before and after, or `NONE`); the Authority
Delta is its mandatory authority line, not a separate file. The normal budget
for an implementation cut is `NONE / NONE / NONE`. A cut that needs a new
owner, carrier, writer, selector or lifecycle transition **stops before
implementation** and returns to the owner.

Every future implementation record classifies OSA (is the state or transition
lawful in ontology, semantics and authority) and CPOC (does that lawful
authority survive process death) applicability explicitly, as `REQUIRED,
<subject>` or `NOT APPLICABLE, <bounded reason>`.

## What counts as verification evidence

- A rule in a governing document is verified only by the test the
  [testing contract](docs/testing_contract.md) names for it, executed, with
  its command and counts recorded in an implementation record.
- A reproducibility claim is verified only by two independent executions
  producing identical canonical outputs.
- A CPOC claim is verified only by the witness in
  [docs/cpoc_design.md](docs/cpoc_design.md): a real operating-system process
  terminated by signal, a fresh process with a distinct PID reconstructing
  from the Continuation Document's typed snapshot alone, a load receipt
  whose document hash equals the written receipt's, the architecture tests
  that prohibit any History-to-state path, and byte-identical canonical
  Simulation History and Reproducible Output Surface against an
  uninterrupted reference. Serialization round-trips inside one
  interpreter, "the app restarted", reruns from time zero, and folding
  History into state are not CPOC evidence. The assurance standard is
  bounded ([docs/cpoc_design.md](docs/cpoc_design.md) §4.1): it is not
  attestation against deliberately non-conforming code.
- A comparative scheduler claim is verified only on identical demand traces
  with identical seeds across policies, reported per regime.
- Prose, screenshots, passing unit tests alone, and the author's confidence
  are not verification evidence.

## Stop conditions

Stop and return the question to the owner when progress would require newly
deciding:

- which of two carriers is authoritative for a fact, or any change to a row
  of the authority model;
- a lifecycle transition, tick-order step, direction or departure rule,
  boarding rule or termination rule not in the constitution or simulation
  semantics;
- a change to the no-look-ahead invariant, the assignment-immutability
  invariant, the capacity invariant, the one-floor-per-tick invariant, the
  Execution identity or write admission, the code-identity execution
  contract, the typed snapshot boundary, the deferral classification, or
  the History/Operational Log separation;
- any Constitutional Delta other than `NONE`;
- writing application code in this phase, or outside an admitted plan's cut
  in a later phase;
- a dependency, service, database, queue or framework the architecture does
  not name;
- a public claim about scheduler performance before the experiment that
  supports it has run.

Do not resolve a stop by writing code, by choosing a storage or framework
technology, by making a cache, projection, browser state or test fixture
authoritative, or by picking the newest or most confident document.

## Same-scope conflict handling

If two documents answer the same consequential question differently:
identify the exact fact; apply the precedence above; look for an owner
decision in `docs/decisions/`; distinguish a recorded decision from a
recommendation marked `RECOMMENDED` or `OPEN`; if still ambiguous, **STOP**
and record the conflict in `docs/current_work.md` under unresolved questions.
Never resolve it in implementation.

## Scope control

This is a take-home simulation. Nothing is added unless it directly serves
simulation correctness, scheduler evaluation, persistence and restart
correctness, reproducibility, or presentation of results. No workflow engine,
Kubernetes, Redis, Kafka, Celery, WebSockets, React, reinforcement learning,
OR-Tools, global optimal-routing solver, microservices, agent framework, or
abstraction whose only purpose is possible future scale. A database is not
introduced unless [docs/cpoc_design.md](docs/cpoc_design.md) justifies one;
it currently does not (a Store is a directory with one identity file). The
architecture names every permitted dependency. The take-home requires the
simulation, its outputs, a README and a walkthrough; OSA, CPOC, Monte
Carlo, AIE and the web UI are the owner's additions and are judged on
their own terms.

## CPOC obligation

The project must eventually demonstrate, with one real witness:

```text
persist -> process death -> reconstruct -> reopen -> continue -> verify history
```

from the durable checkpoint only, producing the same lawful continuation the
uninterrupted run would have produced. The boundary, the checkpoint contents,
the witness and the negative witnesses are owned by
[docs/cpoc_design.md](docs/cpoc_design.md).

## Documentation update obligations

- A change to a governing rule is made in the owning document first, then
  propagated to every document that restates it, in the same change.
- Every repair and open question is recorded in `docs/current_work.md`
  with its date; every owner decision is a record in `docs/decisions/`.
- A future implementation cut updates `docs/current_work.md` and its own
  implementation record before it is called done.
- Audits are never edited after the fact; a re-audit is appended.

## Directory jurisdiction

- `AGENTS.md` owns entry routing, phase, precedence and stop behaviour only.
- `README.md` orients; it owns nothing.
- `docs/constitution.md` and `docs/authority_model.md` govern.
- `docs/*.md` design documents govern their stated jurisdiction.
- `docs/decisions/` records owner decisions and admissions. A decision
  changes standing; a document edit without one does not. An admission
  names the admitted files and their SHA-256 digests.
- `docs/audits/` is evidence. An audit authorizes nothing. Admission
  requires an audit by someone other than the author of the drafts, run
  against `docs/audits/whole_design_audit_checklist.md`.
- `docs/plans/` proposes. A plan authorizes work only after a decision
  record admits it.
- `docs/worked_examples.md` illustrates the rules; it governs nothing.
- `docs/current_work.md` records phase, open questions and admission
  status by reference to `docs/decisions/`.

If this file disagrees with a governing document, this file is wrong.
