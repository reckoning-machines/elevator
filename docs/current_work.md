# Current Work

Status: **RECORD AND HANDOFF SURFACE. Updated 2026-11-05 (revision 7.3; cut 8 in progress).**

## 1. Phase

```text
CURRENT PHASE: IMPLEMENTATION
GOVERNING DESIGN: ADMITTED — REVISION 7.5  (decision records 006, 008, 009, 011, 012; fixed Experiment 010)
IMPLEMENTATION PLAN: ADMITTED               (decision records 007, 008)
IMPLEMENTATION: AUTHORIZED
CUT 1: IMPLEMENTED / LOCAL VERIFY PASS
CUT 2: IMPLEMENTED / LOCAL VERIFY PASS
CUT 3: IMPLEMENTED / LOCAL VERIFY PASS / CPOC PASS   (lifted by the cut-10 witness, 2026-11-05)
       (independent re-audit PASS as reported by the owner on 2026-11-05; the audit
       record is not in the repository; C3-I-01 to C3-I-03 repaired, see the cut-3 record)
CUT 4: IMPLEMENTED / LOCAL VERIFY PASS
CUT 5: IMPLEMENTED / LOCAL VERIFY PASS
       (independent audit PASS as reported by the owner; the audit record is not in the repository)
CUT 6: IMPLEMENTED / LOCAL VERIFY PASS
CUT 7: IMPLEMENTED / LOCAL VERIFY PASS
CUT 8: IMPLEMENTED / LOCAL VERIFY PASS
       (decisions 009 and 010: revision 7.3 and the fixed Experiment; 231 tests; CPOC not applicable)
CUT 9: IMPLEMENTED / LOCAL VERIFY PASS / CPOC PASS   (lifted by the cut-10 witness, 2026-11-05)
       (Store, checkpoint, reconstruction, finality; ΔO/ΔS/ΔA = NONE; record cut_09_store_checkpoint_reconstruction.md)
CUT 10: IMPLEMENTED / LOCAL VERIFY PASS / CPOC PASS
       (witness for both policies; 321 tests; ΔO/ΔS/ΔA = NONE; record cut_10_cpoc_witness.md;
       evidence docs/cpoc/witness_2026-11-05_0367c5f3....md; bounded to the local Store/process model)
CUT 11: IMPLEMENTED / LOCAL VERIFY PASS   (focused re-audit PASS reported by the owner; Revision 7.5; see cut_11_web_ui.md §10-§13)
CUT 12: IMPLEMENTED / LOCAL VERIFY PASS   (README, docs/design.md, docs/walkthrough.md, one screenshot; 351 tests; record cut_12_public_delivery.md)
NEXT ELIGIBLE CUT: NONE — all twelve cuts are implemented
PROJECT IMPLEMENTATION: COMPLETE at its verified standing (twelve cuts; the cut-10 CPOC witness passed, bounded to the local Store/process model); the README time-spent figure (approximately 7 hours) was supplied by the owner
```

## 2. Admission (2026-11-05)

- The bounded closure audit of revision 7.1
  ([audits/independent_revision_7_1_closure_audit.md](audits/independent_revision_7_1_closure_audit.md))
  recorded R7-I-01 and R7-I-02 closed, no new authority owner, and
  `OSA PASS — BOUNDED CLOSURE COMPLETE`. It is evidence, not the act.
- [Decision record 006](decisions/owner_decision_006_revision_7_1_admission.md):
  the owner adopted the pending dispositions of records 002 to 005 as
  refined by the later records, and admitted the nine governing documents
  at the revision-7.1 digests (recomputed and matching before the act).
  The admitted bytes are not edited; their draft status lines are
  superseded by the record.
- [Decision record 007](decisions/owner_decision_007_implementation_plan_admission.md):
  the owner admitted the implementation plan at its recorded digest after
  the consistency inspection (cut order, `operations` in cut 8 reused by
  cut 9, no `api -> checkpoint` edge, every test identifier resolving,
  local verification distinct from CPOC qualification). Implementation is
  authorized beginning with cut 1 only.

## 3. Cut 1

Implemented and locally verified on 2026-11-05:
[implementation/cut_01_domain_input_boundary.md](implementation/cut_01_domain_input_boundary.md).
Files: `elevator/__init__.py`, `elevator/domain.py`, `elevator/api.py`
(`normalize_requests` only), `pyproject.toml`, the cut-1 tests under
`tests/unit/`, `tests/invariants/`, `tests/reproducibility/`. Verification:
`python3 -B -m pytest -v`: 13 passed, 0 failed, 0 skipped, 0 errors.
Delta `NONE / NONE / NONE`. CPOC `NOT APPLICABLE` (value types and pure
checks). Standing: `IMPLEMENTED / LOCAL VERIFY PASS`. Code identity at this
standing: `2b049a80a502e8f389f96183907fd2de5d626535e4ac96d77b7d729d0b9b5401`.

Not implemented at cut 1 (later cuts): route, engine, policies, reporting,
scenarios, harness, `operations`, `simulate`, `create_engine`, checkpoint,
Store, Operational Log carrier, UI. The continuation types belong to cut 9.

## 3a. Cut 2

Implemented and locally verified on 2026-11-05:
[implementation/cut_02_route_policy.md](implementation/cut_02_route_policy.md).
File: `elevator/route.py` (`Departure`, `next_heading`,
`departure_direction`, `eligible_boarders`, `project`), with
`tests/unit/test_route.py`. Verification: cut-2 tests 6 passed; full suite
`python3 -B -m pytest -q` 19 passed, 0 failed, 0 skipped, 0 errors; cut 1
green. Delta `NONE / NONE / NONE`. CPOC `NOT APPLICABLE` (pure). Code
identity at this standing: `bcb85a141c6487100e692d7492d9d404848d3cd8e2eb9aab79e46cbcb6a58eed`.

## 3b. Cut 3

Implemented and locally verified on 2026-11-05:
[implementation/cut_03_simulation_engine.md](implementation/cut_03_simulation_engine.md).
Files: `elevator/engine.py` (created); `elevator/domain.py` (decision-
surface value types appended; cut-1 code unchanged);
`tests/engine_fixtures.py`, `tests/unit/test_engine.py`,
`tests/invariants/test_engine_invariants.py`. Verification: cut-3 tests 45
passed; full suite `python3 -B -m pytest -q` 64 passed, 0 failed, 0
skipped, 0 errors; cuts 1 and 2 green. Delta `NONE / NONE / NONE`. CPOC
`PENDING` until cut 10. Code identity: `56461014a56f477ef3ef09b1c3b438e004a94228fbc0ac62a447dd29515569cb`.

## 3c. Cut 4

Implemented and locally verified on 2026-11-05:
[implementation/cut_04_scheduler_baselines.md](implementation/cut_04_scheduler_baselines.md).
Files: `elevator/policies.py` (`RoundRobin`: `passenger_id mod N`, receipt
`None`; `NearestCar`: minimum `(|floor - origin|, id)`, receipt
`{distance}`), `tests/unit/test_policies.py`,
`tests/invariants/test_no_look_ahead.py`; the engine-local invariant sweep
now also runs under both baselines and the cut-3 policy-module placeholder
in `test_engine.py` was completed. Verification: 19 new tests; full suite
`python3 -B -m pytest -q` 109 passed, 0 failed, 0 skipped, 0 errors; cuts 1
to 3 green. Delta `NONE / NONE / NONE`. CPOC `NOT APPLICABLE` (pure,
stateless). Code identity: `f4ade7779edeee20c0835c1ab624be77659f4dc28e0b032384deebea5c2cb2dd`.

## 3d. Cut 5

Implemented and locally verified on 2026-11-05:
[implementation/cut_05_cost_based_scheduler.md](implementation/cut_05_cost_based_scheduler.md).
File: `elevator/policies.py` (`CostBased`, calling the shared
`route.project`; integer cost, tiered admissibility, signed marginal,
receipt per scheduler §6.5), `tests/unit/test_cost_based.py`,
`tests/invariants/test_projection_exactness.py`; the no-look-ahead
witnesses and the engine-local invariant sweep now cover all three
policies. Verification: 23 new tests; full suite `python3 -B -m pytest -q`
132 passed, 0 failed, 0 skipped, 0 errors; cuts 1 to 4 green; projection
exactness over 16420 (tick, car) pairs with 0 mismatches; the audit's
negative-marginal case exact (marginal `-66`, cost `-52`, Tier 1). Delta
`NONE / NONE / NONE`. CPOC `NOT APPLICABLE` (pure, stateless). One
non-blocking observation for a later revision: scheduler §6.1's marginal
sum nominally includes onboard passengers whose `request_time` is not in
the §3 view; their terms are identically zero (constitution P11), so no
behaviour depends on it (record §4.3). Code identity: `ab156ddb11e85eeaee7cfc44871542c90e3b23e4714a3563bb7586616315337d`.

## 3e. Cut 6

Implemented and locally verified on 2026-11-05:
[implementation/cut_06_reporting_calibration.md](implementation/cut_06_reporting_calibration.md).
File: `elevator/reporting.py` (the eight-file Reproducible Output Surface as
bytes, the pinned exact numeric rendering, the summary, the seven observation
rules, the calibration report, the execution-metadata serialiser and a
no-overwrite file writer), `tests/report_fixtures.py`,
`tests/unit/test_reporting.py`, `tests/invariants/test_exports.py`,
`tests/reproducibility/test_reporting_surface.py`, and a committed fixture under
`tests/fixtures/reporting/`. Verification: 28 new tests; full suite
`python3 -B -m pytest -q` 160 passed, 0 failed, 0 skipped, 0 errors; cuts 1 to
5 green; calibration is exactly zero for all 374 assignments with no later
assignment to the same car, and the witness shows `+10`/`+10` for one that
had one. Delta `NONE / NONE / NONE`. CPOC `NOT APPLICABLE` (derived). Eight
rendering or reading choices where the governing text is silent are listed in
the record (§6); the empty-population `summary.json` null-distribution keys are
the one most worth the owner's check. Code identity: `705d82573789bc94980c5a4bb6f0a99c4e59e9938901953688e70dae946f63a3`.

## 3f. Cut 7

Implemented and locally verified on 2026-11-05:
[implementation/cut_07_scenario_generator.md](implementation/cut_07_scenario_generator.md).
File: `elevator/scenarios.py` (SplitMix64, the nine admitted patterns, `Scenario`,
`generate`, `resolve_parameters`, `provenance`), `tests/reproducibility/test_scenarios.py`,
`tests/invariants/test_scenario_validity.py`, and fixtures under
`tests/fixtures/scenarios/` including `oracle.c`, an independent C implementation
of the specification that produced the committed expected Traces. Verification: 13
new tests; full suite `python3 -B -m pytest -q` 173 passed, 0 failed, 0 skipped, 0
errors; cuts 1 to 6 green; the Python generator equals the independent oracle on
7,000 random scenarios and five deliberate mutations were each caught; a 540-Trace
validity sweep. Delta `NONE / NONE / NONE`. CPOC `NOT APPLICABLE` (pure). Code
identity: `bdd62c2752e9eaa6ce3db71266b5d0e0f0a66a8433ed3488e85c436cbde372b0`.

## 3g. Cut 8 (partial; stopped)

Record: [implementation/cut_08_evaluation_api_operations.md](implementation/cut_08_evaluation_api_operations.md).
Implemented and verified (22 new tests; full suite 195 passed, 0 failed, 0 skipped, 0 errors; cuts 1 to 7
green): `elevator/operations.py` (Execution identity and the Operational Log lifecycle), the
execution-output wrapper in `elevator/reporting.py`, and the pure core of `elevator/harness.py`
(definition and identity, paired comparison, null-aware aggregation, result documents, the
fair-comparison and completeness witness). Not implemented: `api.simulate`, `api.create_engine`, the harness
Run loop, the CLI, the default Experiment with its committed evidence and timing claim. The reason is the
open question below. Two edits made on the way (a `make_policy` factory and a refactor of `scenarios.py`)
were reverted; the validated cut 1 to 7 modules are byte-identical to their recorded state apart from the
one added function in `reporting.py`.

## 4. Records

Governing (admitted, revision 7.1): the nine documents of record 006.
Plan (admitted): record 007. Owner direction for the public deliverable:
[presentation_guidance.md](presentation_guidance.md) (plan cut 12).
Revision 7.3 (record 009) re-admits only `docs/architecture.md` at a new digest.
Revision 7.2 (record 008) re-admitted semantics, the testing contract and
the plan at new digests; the other governing files keep record 006's
digests. Decisions 001 to 005, every audit and every repair record are
unchanged evidence. `docs/implementation/` holds one record per cut.

## 5. Standing rules now in force

- Work outside the current authorized cut is a stop.
- A change to an admitted governing document or to the admitted plan is a
  new revision with a declared delta and a decision record; the admitted
  bytes are never edited in place.
- Every governed entry point and every test process runs under
  `python -B` with no `__pycache__` inside `elevator/`.
- `LOCAL VERIFY PASS` is not CPOC certification; cuts 3, 9 and 11 will
  carry `CPOC PENDING` until the cut-10 witness passes for the code
  identity that includes them.

## 6. Open questions

**Resolved by decision 009 (kept for the record): no component could resolve a policy name.** The public
functions take a policy name (evaluation §2) and an Experiment lists `(name, params)` (§7.1), but the
architecture §1 dependency table lets neither `api` nor `harness` (nor, in cuts 9 and 11, `checkpoint` or
`web`) import `policies`, and no document assigns name resolution to any component. Options and my
recommendation (A: add `policies` to those rows, a descriptive-table correction needing a revision-7.3
record) are in [the cut-8 record §2](implementation/cut_08_evaluation_api_operations.md). No edge was added.
Also noted, not blocking: the default Experiment's building and per-pattern parameters are not defined in the
governing documents.

Resolved 2026-11-05: the policy-name resolution gap above, by [decision 009](decisions/owner_decision_009_policy_construction_edges.md)
(revision 7.3, option A).

**Resolved by decision 010 (kept for the record): the default Experiment's values.** The documents
define its patterns, seeds (`0..19`), policies and initial floors but not the building (floors, elevators,
capacity), `num_requests` and `horizon` per pattern, or the "fixed Experiment" for committed evidence
([cut-8 record §9.4](implementation/cut_08_evaluation_api_operations.md)). Decided 2026-11-05 by
[decision 010](decisions/owner_decision_010_fixed_experiment.md) (20 floors, 4 cars, capacity 8, `num_requests` 100,
`horizon` 1000 where a pattern has one); definition `experiments/default.json`, evidence
`experiments/default_experiment_results.json`. One reading flagged for the owner there (§3.2): `horizon` is
supplied only to the six patterns that have one. Timing is observed, not a threshold (§6).

Resolved earlier: C3-I-02's missing halt reason was decided on 2026-11-05 by
[decision 008](decisions/owner_decision_008_invariant_violation_halt.md)
(`INVARIANT_VIOLATION`, `ΔS` only; revision 7.2) and implemented
([cut-3 record §13](implementation/cut_03_simulation_engine.md)).

## 7. Time log

| Date | Activity | Time |
| --- | --- | --- |
| 2026-11-04 | read doctrine sources; design; draft 16 documents; audit; repair; re-audit | approximately 3 hours, agent-assisted (the owner records their own review time here) |
| 2026-11-04 | read speedway's records; add decisions directory, worked examples, transition classes, denied rights, independent checklist; pass-3 audit | approximately 1 hour, agent-assisted |
| 2026-11-04 | owner review; D-01 to D-07; propagate D-01 and D-06; recompute digests; pass-4 note | approximately 1 hour, agent-assisted, plus the owner's review time |
| 2026-11-04 | independent revision-4 audit (Codex) | the auditor's time, not logged here |
| 2026-11-04 | revision-5 repairs for I-01 to I-19 | approximately 3 hours, agent-assisted |
| 2026-11-04 | independent revision-5 audit | the auditor's time, not logged here |
| 2026-11-04 | revision-6 bounded repairs for R5-I-01 to R5-I-16: Execution model, write admission, Operational Log contract, bounded assurance statements, verifier, deferral rule, domains, output surface, null arithmetic, history range, plan, decision 003, repair record, checklist | approximately 3 hours, agent-assisted |
| 2026-11-04 | independent revision-6 bounded closure audit | the auditor's time, not logged here |
| 2026-11-05 | revision-7 closure of R6-I-01 to R6-I-07: log lifecycle, fixtures, sparse precondition, experiment split, empty-run rule, plan cuts, references; decision 004; repair record | approximately 1.5 hours, agent-assisted |
| 2026-11-05 | revision-7.1 bounded mapping/reference repair and author verification | agent-assisted; elapsed time not measured |
| 2026-11-05 | bounded independent revision-7.1 closure check | the reviewer's time, not logged here |
| 2026-11-05 | admission of the design (006) and the plan (007); cut 1 implementation and local verification; implementation record | approximately 1.5 hours, agent-assisted |
| 2026-11-05 | cut 2 route policy implementation and local verification; implementation record | approximately 0.5 hours, agent-assisted |
| 2026-11-05 | cut 3 simulation engine implementation and local verification; implementation record | approximately 1 hour, agent-assisted |
| 2026-11-05 | cut 3 repair after the independent audit (C3-I-01, C3-I-03 repaired; C3-I-02 stopped for an owner decision) | approximately 0.75 hours, agent-assisted |
| 2026-11-05 | decision 008 (`INVARIANT_VIOLATION`, revision 7.2); C3-I-02 repair and local verification | approximately 0.5 hours, agent-assisted |
| 2026-11-05 | C3-I-01 Enum-payload residual repair and local verification | approximately 0.25 hours, agent-assisted |
| 2026-11-05 | C3-I-01 FrozenEnum-metadata residual repair and local verification | approximately 0.25 hours, agent-assisted |
| 2026-11-05 | cut 4 scheduler interface and baseline policies implementation and local verification; implementation record | approximately 0.75 hours, agent-assisted |
| 2026-11-05 | cut 5 cost-based scheduler and projection-exactness implementation and local verification; implementation record | approximately 1.25 hours, agent-assisted |
| 2026-11-05 | cut 6 reporting, metrics, observations and calibration implementation and local verification; implementation record | approximately 1.5 hours, agent-assisted |
| 2026-11-05 | cut 7 scenario generator implementation, independent C oracle and local verification; implementation record | approximately 1.25 hours, agent-assisted |
| 2026-11-05 | cut 8 partial: operations, execution-output wrapper, harness core; stopped on the policy-resolution dependency gap; partial implementation record | approximately 1.5 hours, agent-assisted |
| 2026-11-05 | revision 7.3 (decision 009); canonical resolver; cut 8 resumption: simulate, create_engine, harness loop, CLI, tests; default-Experiment gap recorded | approximately 2 hours, agent-assisted |
| 2026-11-05 | decision 010: validation, fixed Experiment definition and committed evidence, closing tests, cut 8 completion | approximately 1 hour, agent-assisted (plus about 11 minutes of Experiment execution and suite runs) |

## 8. Admission status

**DESIGN ADMITTED (REVISION 7.2). PLAN ADMITTED. IMPLEMENTATION AUTHORIZED, CUT BY CUT.**

## 9. Next step

None. All twelve cuts are implemented. The owner supplied the time-spent figure (approximately 7 hours) and the AI-disclosure wording for the README. Cut 12 (README, design document, walkthrough, screenshot) was completed on 2026-11-05.
