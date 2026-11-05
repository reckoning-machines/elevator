# Owner Decision Record 002: Revision 5 Repairs and Admission of the Governing Documents

Status: **PROPOSED 2026-11-04. NOT DECIDED. NOT ADMITTED. Nothing in this record has standing until the owner writes in §1 and §4.** This record proposes seven dispositions (D-08 to D-14) that revision 5 of the governing documents is written under, in response to the independent revision-4 audit, and carries the admission text that would admit revision 5 at exact digests. Decision record 001 is historical to revision 4 and is not amended. Shape as in [doctrine_adoption.md](../doctrine_adoption.md) §1.

Source: [audits/independent_revision_4_audit.md](../audits/independent_revision_4_audit.md);
[audits/revision_5_repair_record.md](../audits/revision_5_repair_record.md);
[current_work.md](../current_work.md) §6.

## 1. Owner's decisions (to be written by the owner)

*(Empty until the owner writes here. A disposition the owner overrides is
propagated to the governing documents as revision 6 before the independent
audit and admission.)*

## 2. Proposed dispositions

### D-08. Finality has one durable carrier: the Continuation Document in a Store

**Disposition.** Durable continuity state lives in a Store (a directory with
`store.json` holding a random `store_id`). Each Run has one Continuation
Document at `<store>/<run_id>/run.json`. While `RUNNING` it carries the
snapshot (the Checkpoint), the Simulation History prefix and the
Operational Log; when the Run becomes final, the engine writes the final
standing (with final tick and halt reason) into that same document by the
same atomic replace and removes the snapshot. The loader is addressed by
`(store, run_id)` only; it never takes a file path and never consults an
output directory. Refusals: `RUN_FINAL`, `STORE_MISMATCH` (a document whose
`store_id` is not the Store's), `RUN_NOT_FOUND`. A Run that never wrote a
document has no durable standing and no continuation question.

**Finding corrected.** I-02 (HIGH): revision 4 let a derived
`identity.json` in a caller-chosen output directory decide whether an old
checkpoint could resume; pointing the loader at an empty directory
resurrected a final Run.

**Consequences.** New objects Store and Continuation Document (constitution
§2); authority rows 7, 17, 23, 28; a finality-write transition class; the
CLI gains `store init` and `resume`; the UI reopens by `run_id` from the
server's Store and accepts no file upload; cpoc §6 rows 3 to 6.

**Negative test.** cpoc §6 rows 3 (same Store after finality: `RUN_FINAL`),
4 (different output directory: still `RUN_FINAL`), 5 (copy into a fresh
Store: `STORE_MISMATCH`). Row 6 records the stated limit: a deliberate
overwrite of the document inside its own Store is not distinguishable from
the authority and is not defended.

**If overridden.** The alternative is a separate run-state record beside
the checkpoint; it adds a second file and a two-file atomicity question.
Output-directory finality is not an option (it is the defect).

**Delta.** `ΔO`: Store, Continuation Document. `ΔS`: finality written
into the document. `ΔA`: Run standing's durable carrier moves to the
Continuation Document; the loader's selector is `(store, run_id)`.

### D-09. Code identity is a content hash of the executing package; there is no override

**Disposition.** Code identity is the SHA-256 over the sorted sequence of
(relative path, bytes) of every `.py` file in the simulation package,
computed by the running process from its own package at start. Any byte
change, committed or not, changes it. The Git SHA and worktree standing are
recorded as provenance and participate in nothing. A Continuation Document
whose recorded code identity differs from the running process's is refused
`CODE_IDENTITY_MISMATCH`; `--accept-code-mismatch` is removed. `run_id` and
the Experiment execution id include the code identity.

**Finding corrected.** I-03 (HIGH): an override let different code continue
under the original reproducible `run_id`; a Git SHA did not cover a dirty
tree.

**Consequences.** Constitution §2, §12, N17; authority row 4; architecture
§4; cpoc §5 step 4 and §6 row 10; evaluation §7.1; test
`code_identity_tracks_package_bytes`.

**Negative test.** cpoc §6 row 10: a one-byte change to a copy of the
package refuses the load; no flag changes the outcome.

**If overridden** (an override retained): it would have to mint a distinct
execution identity, claim no equivalence, and satisfy neither P8 nor P12
for the original Run; the documents would need a second identity concept.
The owner's brief preferred simplicity; the simple rule is proposed.

**Delta.** `ΔS`: no override; identity recipe. `ΔA`: none.

### D-10. Simulation History and Operational Log are separate objects with separate equality rules

**Disposition.** The Simulation History holds only what the Configuration,
Trace, policy, Route Policy and tick procedure determine: Simulation Events
(`REVEALED`, `ASSIGNED`, `BOARDED`, `ALIGHTED`, `COMPLETED`, `HALTED`) and
TickRecords, with sequence numbers within it. The Operational Log holds
execution evidence (`EXECUTION_STARTED`, `CHECKPOINT_WRITTEN`,
`LOAD_ADMITTED`, `RESUMED`, `FINALITY_WRITTEN`, `EXECUTION_ENDED`) and
never touches the Simulation History, `run_id`, a decision or a metric
(N18). P8 and P12 compare the Simulation History and derived outputs;
Operational Logs are compared separately as witness evidence. `STARTED` is
dropped (content-free).

**Finding corrected.** I-04 (HIGH): `CHECKPOINTED` and `RESUMED` inside
History broke same-run byte equality and the "prefix ends at `t-1`" rule.

**Consequences.** Constitution §2, P8, P12, N18; authority rows 18, 25, 26;
cpoc §1, §3, §4; evaluation §3 (`operational.jsonl`); W-D rewritten; test
`no_operational_record_in_history`.

**Two-case test.** W-D: the uninterrupted reference's Simulation History is
byte-identical to the checkpoint prefix plus the resumed continuation,
sequence numbers included, while the three processes' Operational Logs
differ exactly as expected.

**If overridden.** Keeping markers in one history would require an
explicit normalisation rule for comparison and renumbering; it was the
revision-4 defect.

**Delta.** `ΔO`: Operational Record and Log. `ΔS`: equality rules. `ΔA`:
none.

### D-11. Liveness is proved with bound `T_last + 2P(F-1)`; two halt reasons

**Disposition.** Constitution P10 claims completion of every passenger by
`T_last + 2 * P * (F - 1)` for every finite valid Trace under any
assignment, proved in semantics §8.2 by three lemmas (onboard destinations
are always ahead; an alighting within `F-1` ticks when anyone is onboard; a
boarding within `F-1` ticks when nobody is onboard and someone waits) and a
count of at most `2P` progress events. `max_ticks` defaults to the bound
and may only be lowered; exceeding the default is `LIVENESS_BOUND_EXCEEDED`
(an invariant failure, since proved); exceeding an explicit smaller horizon
is `HORIZON_EXCEEDED` (a reported halt with `unserved > 0`, not an
invariant failure).

**Finding corrected.** I-07 (MEDIUM): the revision-4 argument rested on a
false premise ("committed stops only shrink") and did not derive its
bound.

**Consequences.** Semantics §8; constitution P10; evaluation §2
(`max_ticks` ceiling); tests `liveness_bound_holds`,
`horizon_halt_reasons_distinct`; assumptions A12.

**Two-case test.** W-B (`P = 2, F = 5`: bound 16, final 8) and W-G
(`P = 2, F = 7`: bound 24, final 8); the audit's negative-marginal trace
(`P = 3, F = 8, T_last = 4`: bound 46).

**If overridden** (the owner's acceptable alternative): the qualitative
claim stands and the horizon becomes `SAFETY_HORIZON_EXCEEDED`, an
operational halt requiring investigation and not an invariant failure;
semantics §8.3 and the two tests change; P10 loses its number.

**Delta.** `ΔS`: the bound and the halt reasons. `ΔA`: none.

### D-12. The supplied passenger id is a required, unique, preserved `source_id`; the public function is specified

**Disposition.** A Request carries `source_id` (the take-home's `id`;
required, non-empty, unique; refusals `MISSING_SOURCE_ID`,
`DUPLICATE_SOURCE_ID`) and `input_index`. `passenger_id` is the stable-sort
position, used internally for ordering; the mapping is explicit and both
ids appear in every output. The source-facing function
`simulate(request_rows, num_elevators, num_floors, capacity, policy=...)`
is specified in evaluation §2 as a thin boundary over the ordinary Trace
load, engine and reporting.

**Finding corrected.** I-15 (MEDIUM): the supplied id was silently replaced
and the public function was unspecified.

**Consequences.** Constitution §2; authority rows 2, 3; semantics §1, §6;
evaluation §2, §3; architecture `api`; tests
`missing_source_id_refused`, `duplicate_source_id_refused`,
`source_id_preserved_in_outputs`; plan cuts 1, 8, 12.

**If overridden.** Internal ids only: the independent audit found that a
source-contract gap; not recommended.

**Delta.** `ΔO`: `source_id` on Request. `ΔS`: input validation. `ΔA`:
none.

### D-13. The source-facing position export is one row per timestamp with all elevator positions

**Disposition.** `elevator_positions.csv` (header `t,elevator_0,...`) is
the required position log; `position_log_long.csv` (one row per `(t,
elevator)` with floor, heading, load) is an analysis file. Both are
`DERIVED` from TickRecords.

**Finding corrected.** I-14 (HIGH): the designated required file had the
wrong row shape for the brief's "one row per timestamp containing all
elevator positions".

**Consequences.** Evaluation §3; semantics §3; README; tests
`wide_export_one_row_per_timestamp`,
`position_exports_are_projections_of_tick_records`; plan cuts 6, 12.

**If overridden.** The long form alone contradicts the brief as read by the
audit; the owner may prefer different file names.

**Delta.** `ΔS`: output contract. `ΔA`: none.

### D-14. The generator and experiment identity are closed

**Disposition.** The Scenario generator uses a specified integer primitive
(SplitMix64 with stated constants and `draw(k) = ((next() >> 11) * k) >>
53`), exact per-pattern draw orders, clamp-versus-redraw rules, set
construction, generated `source_id`s, and refusal rules. The Experiment
has a `definition_hash` over every consequential parameter and an
`execution_id = hash(definition_hash, code_identity)` computed at execution
start; no interpreter version participates because none is depended on.

**Finding corrected.** I-13 (MEDIUM).

**Consequences.** Evaluation §6, §7.1; architecture §4; authority rows 30
to 34; tests `splitmix_reference_vector`, `generate_is_pure`,
`generate_refuses_invalid_parameters`, `experiment_reexecution_identical`.

**If overridden** (keep `random.Random`): the CPython minor version must
join the execution id and the reproducibility promise narrows.

**Delta.** `ΔS`: generator and identity contract. `ΔA`: none.

### Other findings

I-01, I-05, I-06, I-08, I-09, I-10, I-11, I-12, I-16, I-17, I-18 and I-19
are repaired without a new owner-level disposition: they register existing
facts, strengthen witnesses and validation, narrow a stated invariant to
its mechanism, make D-04's wording exact, name shared primitives, repair
the plan and records, pin numerics, correct attribution, and fix examples.
Their repairs are listed in
[audits/revision_5_repair_record.md](../audits/revision_5_repair_record.md)
and are inside the owner's stated repair posture. D-04's exact statement
is now: Tier 1 means the candidate is not capacity-deferred in its
projection and causes no new capacity deferral among the car's committed
passengers; it is a projection at assignment, not a guarantee.

## 3. What is unchanged from revision 4

D-01 direction-compatible boarding with the `FREE` reversal point; D-02
zero dwell; D-03 refusal of `origin == destination`; D-04 the two-tier
capacity concept (wording made exact); D-05 the cost defaults; D-06 no
default checkpointing; D-07 time accounting; the three policies; the AIE
framing; Monte Carlo as evaluation; the thin UI; no database, no
WebSockets, no background queue, no event-sourced state model.

## 4. Admission text (to be written by the owner after the independent revision-5 audit)

Admission admits the exact bytes of the files below at the digests below.
If a digest differs at the time of admission (after a repair the
independent audit requires, or after an override above), this table is
regenerated before the admission text is written. After admission, the
admitted files are not edited to change their status lines; this record
supersedes them.

| File | SHA-256 (revision 5 as proposed, 2026-11-04) |
| --- | --- |
| `docs/constitution.md` | `ab01be2328db89d4b89a1e4ac2b92f4700e4f5cb95f7330a03fab4a564edfa40` |
| `docs/authority_model.md` | `ec7ad0dee9d182bf2b1b01e247f613597704fd2ac1167357c8c1dd7686415344` |
| `docs/simulation_semantics.md` | `1b91cc1d58f23e24a975ff0a2b16ea980131546730eccdb35c0c849e24528c05` |
| `docs/scheduler_design.md` | `af86812fc61ff86f5a9028d938b31dc53c011cd6c85ae76a90e5f4b72c0c7233` |
| `docs/evaluation_design.md` | `43982871e8fda915e11ee9e33db259a4c330ebd2398ae5dcc5227fe694d6ae41` |
| `docs/cpoc_design.md` | `53de9ace9c96ce6f28e6e4ae421f964144e8e3ea23416ad08d269e85a811b86e` |
| `docs/ui_design.md` | `c0c3797efc365734d6d8bd86e09fca6b7f32930ee4b5b1e5f8af41713840e0b7` |
| `docs/architecture.md` | `b7435bac96ff072c70785a2790176931fc521b6043127bd5c5aa44bac21439ed` |
| `docs/testing_contract.md` | `6f05c94783f6e1e9cdcc6582576e675947f81a17ce02f3866ff3a23e06af1af9` |

Proposed wording, for the owner to adopt or amend:

```text
I decide D-08 to D-14 as recorded in §1.
I admit the governing documents at revision 5, at the digests in §4,
as the design baseline. Implementation remains not authorized until the
implementation plan is admitted by a separate record.
```

Preconditions the owner should see satisfied before writing it: the
independent audit of revision 5 against
[whole_design_audit_checklist.md](../audits/whole_design_audit_checklist.md)
(26 checks) recorded in `docs/audits/` with `OSA PASS`; no OPEN marker in
the governing documents.

## 5. What this record does not do

It does not admit the implementation plan, authorize any cut, certify
anything, claim `OSA PASS` or `CPOC PASS`, or grade revision 5. Its
cumulative Constitutional Delta relative to revision 4 is the sum of the
deltas above; relative to revision 5 as drafted it is `0/0/0`.
