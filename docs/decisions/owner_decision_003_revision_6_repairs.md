# Owner Decision Record 003: Revision 6 Repairs and Admission of the Governing Documents

Status: **PROPOSED 2026-11-04. NOT DECIDED. NOT ADMITTED. Nothing in this record has standing until the owner writes in §1 and §4.** This record proposes eight dispositions (D-15 to D-22) that revision 6 of the governing documents is written under, as a bounded repair in response to the independent revision-5 audit, and carries the admission text that would admit revision 6 at exact digests. Decision records 001 and 002 are historical and are not amended; D-08, D-09, D-10 and D-14 of record 002 are superseded in part by D-15 to D-21 below, while D-11, D-12 and D-13 stand as proposed there. Shape as in [doctrine_adoption.md](../doctrine_adoption.md) §1.

Source: [audits/independent_revision_5_audit.md](../audits/independent_revision_5_audit.md);
[audits/revision_6_repair_record.md](../audits/revision_6_repair_record.md);
[current_work.md](../current_work.md) §6.

## 1. Owner's decisions (to be written by the owner)

*(Empty until the owner writes here. A disposition the owner overrides is
propagated to the governing documents as revision 7 before the bounded
closure audit and admission.)*

## 2. Proposed dispositions

### D-15. Logical Run versus Execution: identity, finality and write admission

**Disposition.** `run_id` (hash of Configuration, Trace and code identity)
identifies deterministic simulation semantics and selects no durable
standing. An Execution, identified by a random 128-bit `execution_id`
minted by the process at Execution creation, owns continuation state,
durable Execution standing, the Operational Log and its output location.
The Continuation Document lives at `<store>/<execution_id>/run.json`,
records `(store_id, execution_id, run_id)` and a monotone
`write_sequence`; the loader is addressed by `(store, execution_id)`.
Separate Executions of one Run, in one Store or several, are lawful and
independent. Writes are admitted only against no document or a `RUNNING`
document whose `write_sequence` equals the writer's token; a finality
write moves standing to `COMPLETED` or `HALTED`; after that no write is
admitted (`WRITE_AFTER_FINAL`, `STALE_WRITER`; the writer halts). The Run
outcome (decided by the engine, a Simulation Event) and Execution standing
(the document) are distinct facts and transition classes.

**Finding corrected.** R5-I-01 (HIGH) and the transition-class part of
R5-I-13 (HIGH): a global "a final Run never resumes" rule conflicted with
per-Store documents and independent same-run executions; ordinary
checkpoint writes had no admission against an existing final path; the
final commit boundary did not distinguish transient completion from
durable finality.

**Consequences.** Constitution §2, §4.3, §4.5, N13, §13, §14; authority
rows 17, 17a, 23, 28, 37; cpoc §2, §3, §5, §6; architecture; UI reopen by
`execution_id`; outputs at `<output>/<run_id>/<execution_id>/`.

**Two-case / negative test.** cpoc §6 row 7 (two Executions of one Run in
one Store: one final, the other admitted; identical Simulation Histories);
rows 3, 4, 5, 8, 9, 10 (final in Store; different output directory; copy
into another Store; copy under another `execution_id`; stale writer; write
after final).

**If overridden.** Keeping a single global standing per `run_id` would
require a cross-Store registry (new infrastructure) or forbidding repeated
execution (which Experiments require). Not recommended.

**Delta.** `ΔO`: Execution. `ΔS`: write admission; outcome versus
standing. `ΔA`: the executing process owns its Execution; five
transition classes added.

### D-16. Code identity: a bounded supported execution contract

**Disposition.** Code identity remains the content hash of every `.py`
file of the governed package. Reproducibility is claimed only within the
supported execution contract: the interpreter runs with bytecode writing
disabled (`python -B` or `PYTHONDONTWRITEBYTECODE=1`); no `__pycache__`
exists inside the governed package; code identity is computed before any
Run begins; sources are not modified for the lifetime of the process
(re-hashed at exit; `CODE_IDENTITY_DRIFT` recorded if changed). Every
governed entry point checks the contract and refuses
`UNSUPPORTED_EXECUTION_ENVIRONMENT`. No override exists. Stated plainly:
the project does not attempt to attest against malicious replacement of
executing instructions after process start.

**Finding corrected.** R5-I-02 (HIGH): a stale, timestamp-valid bytecode
cache could execute instructions that differ from the hashed source.

**Consequences.** Constitution §2, §12, §4.5; authority row 4;
architecture §4; cpoc §4.1, §6 row 16; README run instructions; test
`execution_environment_contract`.

**Negative test.** An entry point started with bytecode writing enabled,
or with a `__pycache__` in the package, refuses; a source modified after
start is reported at exit.

**If overridden** (full attestation): executable-bytecode hashing, signed
packages or hermetic builds, which the owner has excluded as beyond the
take-home. Overriding toward no contract at all would leave R5-I-02 open.

**Delta.** `ΔS`: the contract and its refusal. `ΔA`: none.

### D-17. Snapshot-consumption assurance: a typed boundary and a prohibited call graph

**Disposition.** `Snapshot` is produced only by `parse_snapshot(document)`;
`HistoryPrefix` and `HistoryVerifier` are distinct types with no
conversion; `construct_state(Snapshot)` rejects any other type at runtime
and is called only by `load`; no function anywhere in the simulation or
web package takes History-typed input and returns a `Snapshot`, an
`EngineState` or an argument of `construct_state`; the architecture test
scans both packages and must detect a planted cheating fixture. The load
receipt still records hashes, stated as value equality, not causal
provenance.

**Finding corrected.** R5-I-03 (HIGH): value-equal hashes and a snapshot-
only signature cannot distinguish a loader that validates, then folds
History into a snapshot-shaped value.

**Consequences.** cpoc §4.1, §5.1, §5.2; constitution N14, §13; authority
rows 25, 38; testing §7.

**Negative test.** `no_history_to_state_path_in_package` with the planted
cheat; `history_verifier_isolated`; runtime rejection of a non-`Snapshot`
argument.

**If overridden** (demanding provenance proof): no bounded design can
supply it; the owner has chosen the structural standard.

**Delta.** `ΔO`: the three types. `ΔS`: the stated assurance standard.
`ΔA`: none.

### D-18. Operational Log: a separate receipt file with write-then-hash-then-append ordering

**Disposition.** `<store>/<execution_id>/operational.jsonl` (or the
output directory's copy for an Execution without a Store) is append-only
and is the only carrier of Operational Records; it is never embedded in
the Continuation Document, which holds no hash of itself. Each record
carries `execution_id`, `op_seq`, tick, the document's SHA-256 where
applicable, pid and code identity; the vocabulary is closed
(`EXECUTION_STARTED`, `CHECKPOINT_WRITTEN`, `LOAD_ADMITTED`, `RESUMED`,
`FINALITY_WRITTEN`, `EXECUTION_ENDED`, `CODE_IDENTITY_DRIFT`,
`DIAGNOSTIC`). Ordering: write the document atomically, hash the bytes at
the path, append the receipt, flush. A missing receipt fails witness
evidence (`EVIDENCE_INCOMPLETE`), never simulation authority.

**Finding corrected.** R5-I-04 (MEDIUM) and the log-binding part of
R5-I-13.

**Consequences.** Constitution §2, §4.5; authority rows 26, 27; cpoc §2.3,
§2.4, §3.2, §3.3, §4.2, §6 row 32, §8; W-D.

**Negative test.** cpoc §6 row 32 (death between rename and append); the
receipt's SHA-256 equals the bytes at the path (`write_admission`).

**If overridden** (receipt inside the document): a self-reference or
exclusion rule would be needed; rejected as the source of the defect.

**Delta.** `ΔO`: the log as its own carrier. `ΔS`: ordering. `ΔA`: none.

### D-19. Deferral classification: direction decides first

**Disposition.** A passenger whose direction is incompatible with the
departure direction is a direction deferral (wrong-way pass); capacity is
not evaluated for them. A capacity deferral is recorded only when the
direction is compatible (or the car is `FREE`) and the passenger would
otherwise have boarded but the car has no room. A full car departing the
other way yields a wrong-way pass only. Boarding mechanics, load safety
and tiering are unchanged.

**Finding corrected.** R5-I-07 (MEDIUM): two sections classified the
full-and-wrong-way case differently.

**Consequences.** Semantics §4.2, §5; scheduler §5; authority row 22;
W-F; test `deferral_classification_direction_first`.

**Two-case test.** W-F tick 2 (wrong-way, full: one wrong-way pass, zero
capacity deferrals) and W-B tick 2 (compatible, full: one capacity
deferral).

**If overridden** (capacity first): the counts change for the
full-and-wrong-way case only; the tier rule is unaffected.

**Delta.** `ΔS`: classification. `ΔA`: none.

### D-20. Reproducible Output Surface and null-aware aggregation

**Disposition.** The eight files `elevator_positions.csv`,
`position_log_long.csv`, `passengers.csv`, `summary.json`,
`observations.md`, `events.jsonl`, `tick_records.jsonl` and
`run_identity.json` are the Reproducible Output Surface: byte-identical
for every Execution of a Run; P8 and P12 quantify over exactly them; no
execution fact may appear in them (N18). `execution_metadata.json` (Git
SHA, worktree standing, scenario provenance, `execution_id`, `store_id`,
controls, pid, timestamps) and the Operational Log are outside equality.
Experiment aggregation classifies every metric as always-defined or
conditional; nulls are excluded, never zero; `n_defined`, `n_pairs` and
`halted_count` are reported; paired differences exist only over completed,
defined pairs; halted runs are excluded from distributions and comparisons.

**Finding corrected.** R5-I-09 (HIGH) and R5-I-10 (MEDIUM).

**Consequences.** Constitution §2, P8, P12, N18; authority rows 39, 40;
evaluation §3, §7.4; cpoc §1, §4.2; tests
`reproducible_surface_excludes_execution_facts`,
`experiment_null_aggregation`.

**Negative test.** A README-only commit between two Executions leaves
every surface file identical; a results set with null metrics, an empty
run and a halted run aggregates as specified.

**If overridden** (provenance in a reproducible file): P8 would be false
under ordinary operation, the revision-5 defect.

**Delta.** `ΔO`: the surface. `ΔS`: equality scope; aggregation. `ΔA`:
none.

### D-21. Practical domains and a fixed lobby share

**Disposition.** `2 <= F <= 200`, `1 <= N <= 20`, `1 <= C <= 50`,
`0 <= num_requests <= 100000`, `0 <= horizon <= 10^6`,
`0 <= time <= 10^9`, `0 <= seed < 2^64` (refused, not reduced),
`1 <= k <= 1000`, `1 <= w <= 10^6`, `1 <= m <= F`, `1 <= g <= 10^6`,
`0 <= j < g`; every advertised scenario parameter is used exactly once;
the lobby share of `up_peak` and `down_peak` is fixed at `4/5`; unknown or
out-of-domain parameters refuse `INVALID_SCENARIO_PARAMETERS`; the
configuration domain refuses `INVALID_CONFIGURATION`.

**Finding corrected.** R5-I-08 (MEDIUM): an advertised `p_lobby` that the
algorithm ignored; set constructions that could not terminate for
`F > 2^53`; a seed space that mapped two seeds to one state.

**Consequences.** Evaluation §2, §6; semantics §1; tests
`configuration_domain_refusals`, `generate_refuses_invalid_parameters`,
`seed_domain_refused`.

**If overridden** (a tunable lobby share): it becomes a rational
`(num, den)` with `0 <= num <= den <= 10^6`, drawn as `draw(den) < num`;
one more parameter row. Larger domains would require re-deriving
termination.

**Delta.** `ΔS`: domains. `ΔA`: none.

### D-22. Batch versus interactive execution boundary

**Disposition.** `normalize_requests` is the single input boundary;
`simulate` runs a Run to its outcome and writes no Continuation Document;
`create_engine` returns a `RUNNING` engine at tick boundary 0 for the UI,
which steps it and delegates checkpoint and reopen to the checkpoint
module. One engine implementation; the UI never calls `simulate` to create
a session; web may depend on `api`, engine (step), reporting, harness and
checkpoint (explicit checkpoint and reopen only).

**Finding corrected.** R5-I-16 (MEDIUM).

**Consequences.** Evaluation §2; architecture §1; ui §2.1; constitution
§4.5; authority row 41; tests `normalization_shared_by_batch_and_live`,
`ui_new_run_creates_engine_not_simulate`.

**If overridden** (UI through `simulate`): a partial-run mode would have
to be invented; rejected.

**Delta.** `ΔO`: none. `ΔS`: boundary contracts. `ΔA`: none.

### Other findings

R5-I-05, R5-I-06, R5-I-11, R5-I-12, R5-I-14 and R5-I-15 are repaired
without a new owner-level disposition (test constructions, the isolated
verifier's checks, the committed-record history range, plan prerequisites,
lemma wording, references and attribution); their repairs are listed in
[audits/revision_6_repair_record.md](../audits/revision_6_repair_record.md)
and are inside the owner's stated repair posture.

## 3. What is unchanged from revision 5

Every mechanic the owner's posture lists as preserved: direction-
compatible boarding with the `FREE` reversal point; zero dwell;
beginning-of-tick positions; immutable assignment; LOOK; Round Robin,
Nearest Car and cost-based with negative marginal cost; incremental Tier
1 and 2; the AIE framing; Monte Carlo as evaluation; no demand
forecasting; no reassignment; the thin FastAPI/Jinja2/HTMX UI; no
database, broker, WebSockets, event-sourced state engine, solver or RL;
the liveness bound `T_last + 2P(F-1)`.

## 4. Admission text (to be written by the owner after the bounded closure audit)

Admission admits the exact bytes of the files below at the digests below.
If a digest differs at the time of admission (after a repair the closure
audit requires, or after an override above), this table is regenerated
before the admission text is written. After admission, the admitted files
are not edited to change their status lines; this record supersedes them.

| File | SHA-256 (revision 6 as proposed, 2026-11-04) |
| --- | --- |
| `docs/constitution.md` | `79e2e8a90beb6ab342b8675bab4a6917f32389015c1dd2f993b5bff7a625dda0` |
| `docs/authority_model.md` | `b33700e6727b39b960385c25d85e080e94787b09797d511618f50e955e63688a` |
| `docs/simulation_semantics.md` | `6bb2780bbdcd6073a58f42be2ac9f9c4b68950a8f67f3e3b4ec6e586e3c6d66d` |
| `docs/scheduler_design.md` | `6deff87bf9e9c02e2f28d74f0861bf8068c4d9398a9a40b06a9440d9f9f3d9ca` |
| `docs/evaluation_design.md` | `32dc5c75c58f4255adeac66eadba69d05c9f687d06fe926f6b879f96e2fbd6ee` |
| `docs/cpoc_design.md` | `81b52abc523b0012af3c048a1708071786d7ba125d7de2b35d020685e530f2f0` |
| `docs/ui_design.md` | `4430c0c6000bc95620e8a70aee6887f085c483dc82e3521f44b03304606a639f` |
| `docs/architecture.md` | `36dbec84ed3e1745d766c7d7e871b97cdcea276f78b7fd93250a2dcb342eac4a` |
| `docs/testing_contract.md` | `ecc35c327ffdb634f8edf27f955d194ed43fd4ec74a9f8a3b1b6c22d59a8c826` |

Proposed wording, for the owner to adopt or amend:

```text
I decide D-15 to D-22 as recorded in §1, and confirm D-11, D-12 and
D-13 of record 002.
I admit the governing documents at revision 6, at the digests in §4,
as the design baseline. Implementation remains not authorized until the
implementation plan is admitted by a separate record.
```

Preconditions the owner should see satisfied before writing it: the
bounded independent closure audit of revision 6 against
[whole_design_audit_checklist.md](../audits/whole_design_audit_checklist.md)
(35 checks, with R5-I-01 to R5-I-16 each marked `CLOSED`) recorded in
`docs/audits/` with `OSA PASS`; no OPEN marker in the governing documents.

## 5. What this record does not do

It does not admit the implementation plan, authorize any cut, certify
anything, claim `OSA PASS` or `CPOC PASS`, or grade revision 6. Its
cumulative Constitutional Delta relative to revision 5 is the sum of the
deltas above; relative to revision 6 as drafted it is `0/0/0`.
