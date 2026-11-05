# Cross-Process Operational Continuity (CPOC) Design

Status: **GOVERNING DOCUMENT for continuation after process death. DRAFT, NOT ADMITTED. Revision 7.1 (bounded component-mapping and reference repairs, 2026-11-05).**

Jurisdiction: the exact continuity obligation for this project, the Store,
the Execution's Continuation Document and Operational Log (layout, write
admission, contents, receipt ordering, crash points), the qualifying
process boundary, the one certification witness and its bounded assurance
standard, the ordered load verification including the isolated history
verifier, the negative witnesses with their exact construction rules, and
the evidence record. Subordinate to [constitution.md](constitution.md)
§4.3, §12, §13 and the [authority model](authority_model.md) rows 17a, 23
to 29 and 37 to 40. CPOC never creates authority; it proves that the
authority already assigned survives the boundary. CPOC's meaning is adopted
unchanged from `fin123-core` ([doctrine_adoption.md](doctrine_adoption.md));
this document applies it at a bounded assurance standard (§4.1).

## 1. The obligation

> An Execution checkpointed at the start of tick `t`, continued in a fresh
> operating-system process from its Continuation Document alone, must
> produce from tick `t` onward exactly the Simulation History and the
> Reproducible Output Surface that an uninterrupted Execution of the same
> Run produces.

"Exactly" is byte-identical canonical serialisation of the Simulation
History (Simulation Events and TickRecords) and of every file of the
Reproducible Output Surface ([evaluation_design.md](evaluation_design.md)
§3). The Operational Log and `execution_metadata.json` are **not** part of
this equality: they record that a checkpoint, a kill and a load happened,
which an uninterrupted Execution never did. They are compared separately
(§4 step 7) as evidence.

What CPOC is not, here: it is not a serialisation round-trip test in one
interpreter; it is not "the UI reloads"; it is not "the same seed reruns
from zero and matches"; it is not "fold the saved History into a state and
carry on". The last two are prohibited as recovery (constitution N14) and
the witness is designed to fail an implementation that does either within
the bounded assurance standard of §4.1.

## 2. The CPOC boundary, the Store, Executions and granularity

The only process boundary in scope is **between two ticks**: after step 9
of tick `t-1` and before step 1 of tick `t` (or before tick 0). A Checkpoint
is a snapshot at that boundary. There is no mid-tick checkpoint, no
checkpoint of a policy call, and no checkpoint of a UI session. Process
death at any other moment loses every tick after the last Checkpoint; those
ticks are re-executed on continuation and, because the tick is
deterministic, produce the same Simulation History (constitution §4.4).

### 2.1 Run and Execution

A **Run** (`run_id`) is deterministic semantics. An **Execution**
(`execution_id`, a random 128-bit identifier minted by the process at
Execution creation) is one attempt to carry a Run forward, owning its
continuation state, its durable standing, its Operational Log and its
output location. Many Executions of one Run are lawful: every Experiment
executes the same `run_id` once per policy row, and the witness executes
it three times. They never share a document, a log or a standing. The
continuation path is `(store, execution_id)`; `run_id` is recorded in the
document and verified, but selects nothing.

### 2.2 Store layout

```text
<store>/store.json                           {store_schema_version, store_id}
<store>/<execution_id>/run.json              the Continuation Document (atomic replace)
<store>/<execution_id>/run.json.tmp          bytes in flight; never loaded; removed by the next admitted write
<store>/<execution_id>/operational.jsonl     the Operational Log (append-only), once the Execution is Store-bound
```

A Store is created explicitly (`elevator store init <path>`); the default
Store for the CLI and UI is `./runs_store`. Output directories are separate
and own nothing; outputs land at `<output>/<run_id>/<execution_id>/`
([evaluation_design.md](evaluation_design.md) §3). An Execution with no
checkpoint controls never touches a Store.

### 2.2a Operational Log carrier lifecycle

Revision-7.1 component mapping: `operations.py` implements the existing
process-owned log buffer, append, evidence-root binding and flush.
Checkpoint selects the Store location and supplies receipt payloads; API
creates the operational Execution handle; reporting binds output-only
batch evidence. Operations reads/writes the log only, never Store identity
or Continuation Documents, and makes no continuation decision
([architecture.md](architecture.md) §1.1). The carrier rules below and
their process owner are unchanged.

(Owner decision proposed as D-23.) Every Execution has exactly one
Operational Log, whose carrier changes once, from memory to a file:

- **Before durable binding.** From Execution creation the log is an
  in-memory buffer owned by the executing process (`EPHEMERAL`, authority
  row 26). `op_seq` starts at 1 with `EXECUTION_STARTED`. The buffer has
  no authority over simulation state and is lost with the process.
- **Evidence root.** The Execution's durable evidence root is the first of
  these to exist: the Store directory `<store>/<execution_id>/` once the
  Execution is bound to a Store (at creation when checkpoint controls are
  set, or at the first explicit checkpoint of a live session); otherwise
  the output location `<output>/<run_id>/<execution_id>/` when an output
  directory was supplied. A Store-bound Execution's root is always the
  Store, even if an output directory also exists; the output location then
  receives a copy at `EXECUTION_ENDED` (§3.2).
- **Flush at binding.** When the evidence root first exists, the entire
  unflushed buffer is appended, in `op_seq` order, to
  `<root>/operational.jsonl`, and every later record is appended there
  directly. Nothing is written twice; `op_seq` is continuous across the
  in-memory period, the flush, later checkpoints and every resume (a
  resumed process continues from the last `op_seq` in the file).
- **Never bound.** An Execution that never obtains an evidence root
  (`simulate(..., output_dir=None)`, or a live session never checkpointed
  and never given an output directory) keeps its log in memory only. That
  affects no simulation fact and no output of the Reproducible Output
  Surface; such an Execution cannot be cited as durable CPOC evidence.
- **CPOC qualification** requires a Store-bound Execution with a durable
  Operational Log.

There is one log per Execution; no second log exists. A live session that
binds to a Store at its first checkpoint therefore flushes
`EXECUTION_STARTED` and any `DIAGNOSTIC` records to the Store before the
`CHECKPOINT_WRITTEN` receipt of that first checkpoint is appended.

### 2.3 Granularity

(Owner decision D-06.) **On request, at a tick boundary; never by
default.** `--checkpoint-at <t>` writes once at that boundary and
continues; `--checkpoint-every <k>` writes every `k` ticks; the UI offers
an explicit Checkpoint action and an optional interval. Batch, Monte Carlo
and interactive runs all default to no document. These controls are
execution parameters (authority row 27). `--pause-after-checkpoint` is a
witness-only control: after the requested write the process blocks
indefinitely holding its in-memory state. `--witness-instrumentation`
makes the engine's single emission point append a `DIAGNOSTIC` record per
emitted TickRecord to the Operational Log, for the witness's
anti-recomputation evidence; it changes nothing else.

### 2.4 Multiple checkpoints and resumes

Each admitted checkpoint write replaces the Execution's document and
increments `write_sequence`. A resumed process reads `write_sequence` at
load and uses it as its admission token for its own later writes; it
continues `op_seq` from the last record in the Execution's Operational Log.
A second resume of the same Execution after a second death is the same
procedure again. Simulation sequence numbers and the Simulation History
are unaffected by how many times this happens.

## 3. The Continuation Document, write admission and the Operational Log

### 3.1 Document contents

```text
ContinuationDocument
  schema_version
  store_id, execution_id                        (the path's execution_id must equal this)
  run_id, code_identity, configuration_hash, trace_hash
  write_sequence                                (1 for the first write; +1 per admitted write)
  configuration (full)
  trace (full, every Request including those with request_time >= t)
  standing: RUNNING | COMPLETED | HALTED
  final: null while RUNNING; else {final_tick, halt_step?, halt_reason?, halt_passenger?}

  snapshot (present iff RUNNING; the Checkpoint):
     t                                          (the tick about to execute)
     elevators: [ {id, floor, heading} ]        exactly ids 0..N-1, ascending
     passengers: [ {passenger_id, source_id, standing, assigned_elevator,
                    assigned_at, pickup_time, dropoff_time} ]
                                                exactly the revealed set {p : request_time < t}, ascending id
     snapshot_hash                              (SHA-256 of the canonical bytes of the snapshot section excluding this field)

  simulation_history:                           (through tick t-1 while RUNNING; complete when final)
     events: [...]                              Simulation Events only
     tick_records: [...]
     history_hash                               (SHA-256 of the canonical bytes of this section excluding this field)
```

The document contains no hash of itself, no Operational Record, no
provenance block and no timestamp. `snapshot_hash` and `history_hash` are
integrity fields over their own sections; a test fixture that mutates a
section must recompute its field to reach any verification after step 9
(§6).

Why the full Trace is embedded: the Trace is an input of the Run
(authority row 2), not runtime state, and the no-look-ahead invariant
governs the scheduler's decision surface, not persistence. A document that
omitted future Requests could not continue the Run at all. That future
Requests influence no decision before their time is proved by the
no-look-ahead witnesses of [testing_contract.md](testing_contract.md) §3,
not by a continuation witness.

What is deliberately **not** in the document, and is recomputed: elevator
load, onboard sets, waiting sets, committed stops, departure directions,
routes; scheduler projections, costs, receipts other than those in
`ASSIGNED` events; the position exports, statistics, observations; any UI
state; any execution evidence.

### 3.2 Write admission and receipt ordering

Every checkpoint or finality write by the Execution's process:

1. read the document currently at `<store>/<execution_id>/run.json`, if
   any; if present, it must be parseable, carry this `execution_id`, have
   standing `RUNNING`, and have `write_sequence` equal to the writer's
   last-known value; otherwise refuse `WRITE_AFTER_FINAL` (standing final)
   or `STALE_WRITER` (sequence behind) or `EXECUTION_MISMATCH`, and halt
   the writer without writing;
2. serialise the new document with `write_sequence + 1` (1 if none
   existed) to `run.json.tmp`; fsync; rename over `run.json`;
3. read back and hash the bytes now at `run.json` (SHA-256);
4. append `CHECKPOINT_WRITTEN` (or `FINALITY_WRITTEN`) to the Execution's
   Operational Log at its evidence root (§2.2a; the first checkpoint of a
   live session first binds the Execution to the Store and flushes the
   buffer) with `execution_id`, the next `op_seq`, the tick,
   `write_sequence`, the document SHA-256 from step 3, `snapshot_hash`,
   `history_hash`, pid and code identity; flush.

At `EXECUTION_ENDED`, a Store-bound Execution that also has an output
location copies its Operational Log there as evidence; the Store file
remains the log.

The receipt therefore denotes exactly the bytes a later loader reads. A
missing or unflushed receipt (death between steps 2 and 4) makes the
witness's evidence incomplete and fails certification for that attempt; it
does not invalidate the document, which is lawful simulation authority on
its own.

### 3.3 Crash points

| Death point | Durable state at the path | Consequence |
| --- | --- | --- |
| No document ever written | none | no continuation promised (D-06) |
| After the Run outcome in memory, before the finality write's rename | the last `RUNNING` document | continuation re-executes from its snapshot and reaches the same outcome; transient completion is not finality |
| `run.json.tmp` written, before rename | the previous document; the temp file | the temp file is never loaded and is removed by the next admitted write; the previous document governs |
| During rename | the previous or the new document, never torn | atomic replace |
| After rename, before the receipt append | the new document | lawful authority; the witness's receipt evidence is missing and that attempt fails certification |
| After the finality rename, before derived outputs | final document | load refuses `EXECUTION_FINAL` whatever the output directory holds |
| After outputs | final document | outputs may be regenerated from the document; changing the output directory has no effect |
| A later process holding an old `write_sequence` attempts a write | unchanged | `STALE_WRITER`; the writer halts |
| A later process attempts a write after finality | unchanged | `WRITE_AFTER_FINAL`; the writer halts |

Deliberate replacement of the document inside its own Store by an actor
that is not the Execution's process is outside the threat model (§6 row
6) and is the design's stated limit.

### 3.4 Finality write

When an Execution that has a document reaches its Run outcome, the process
performs one more admitted write: `standing` final, `final` filled,
`snapshot` removed, `simulation_history` complete, `write_sequence + 1`;
then the `FINALITY_WRITTEN` receipt. An Execution that never wrote a
document writes nothing at finality.

## 4. The certification witness

### 4.1 Bounded assurance standard

OSA and CPOC in this project prevent accidental competing authority and
prove the designed continuation boundary. They do not prove against
implementation code that deliberately violates its own source contract.
The instruments are explicit architectural boundaries, import and call
graph restrictions, negative tests and runtime assertions. Two statements
bound the claims:

> Code identity establishes reproducibility only within the supported
> execution contract (constitution §12). The project does not attempt to
> attest against malicious replacement of executing instructions after
> process start.

> Hash equality proves value equality, not causal provenance.
> Snapshot-consumption assurance comes from the typed API and the
> prohibited call graph (§5.1), supported by negative tests.

No stronger proof is claimed.

### 4.2 The witness

One witness, run by the test suite as a subprocess orchestration, proves the
principle. It is the witness the implementation plan's cut 10 must deliver.

```text
Fixture: configuration F=10, N=3, C=4; Trace = generate(bursty, seed 7) (committed as a fixture file with its hash)
Policy: cost_based with default params; the whole witness is repeated for round_robin
Chosen t: a tick strictly inside the run, with at least one passenger ONBOARD, one WAITING,
          and at least one Request with request_time > t (the fixture is chosen so t = 12
          satisfies this; the witness asserts it before proceeding)
Store S: created fresh by the witness (store init); its store_id recorded
Every process is started under the supported execution contract (python -B, no __pycache__ in the package).

 1. Reference Execution R (execution_id e_R): simulate to completion with no Store, outputs to out/.
    Record R's PID and its EXECUTION_STARTED/ENDED records (in out/<run_id>/e_R/operational.jsonl).
 2. Execution A (execution_id e_A): start the same Run with --store S --checkpoint-at 12
    --pause-after-checkpoint --witness-instrumentation, outputs to out/. Record A's PID. A writes
    S/e_A/run.json at the start of tick 12 (write_sequence 1), appends CHECKPOINT_WRITTEN
    (document SHA-256 d_A, snapshot_hash H_s, history_hash H_h) and then blocks, holding its
    in-memory engine state.
 3. Kill A with SIGKILL. Wait for exit; assert A's PID is gone and the exit was by signal 9.
    Read S/e_A/run.json: assert its SHA-256 equals d_A from the receipt; parse; assert standing RUNNING,
    snapshot.t == 12, write_sequence == 1; keep a byte copy D12.
 4. Process B: a fresh interpreter started with only: --store S --resume e_A
    --witness-instrumentation and an output directory. No fixture path, no seed, no policy flag,
    no document path, no environment from A. Record B's PID; assert B's PID != A's PID and != R's PID.
 5. B loads by (S, e_A): the verifications of §5 pass in order; B appends LOAD_ADMITTED and
    RESUMED(t=12) to S/e_A/operational.jsonl (op_seq continuing after A's records); B continues
    ticks 12.. to completion; at the Run outcome B performs the finality write (write_sequence 2)
    and FINALITY_WRITTEN; B writes outputs to out/<run_id>/e_A/.
 6. Compare (Simulation History and the Reproducible Output Surface):
    - B's tick_records for t >= 12 and B's Simulation Events after the last event of tick 11
      are byte-identical to R's for the same ticks;
    - (D12.simulation_history prefix + B's continuation) is byte-identical to R's complete
      Simulation History, sequence numbers included;
    - every file of the Reproducible Output Surface in out/<run_id>/e_A/ is byte-identical to
      the same file in out/<run_id>/e_R/ (run_identity.json included);
    - execution_metadata.json differs in execution_id, pid and timestamps and nowhere else that
      the surface definition does not permit; it is compared for shape only.
 7. Anti-recomputation and bounded anti-folding evidence (constitution N14), all required:
    - the LOAD_ADMITTED record's document SHA-256 equals d_A (B loaded the bytes A wrote);
      its snapshot_hash equals H_s; its constructed_state_hash equals H_s (value equality;
      evidence beside the structural boundary, not proof of provenance, §4.1);
    - the DIAGNOSTIC records in S/e_A/operational.jsonl attributable to B's pid name no tick
      below 12; the first names 12; their count equals (final tick - 12 + 1); R's output log
      names every tick from 0; A's names 0..11;
    - the structural obligations of §5.1 hold for the package under test (the suite's
      architecture tests ran green at the same code identity);
    - R's Operational Log has exactly EXECUTION_STARTED, DIAGNOSTIC records, EXECUTION_ENDED;
      A's has EXECUTION_STARTED, DIAGNOSTIC records 0..11, CHECKPOINT_WRITTEN; B's has
      EXECUTION_STARTED, LOAD_ADMITTED, RESUMED, DIAGNOSTIC records 12..final, FINALITY_WRITTEN,
      EXECUTION_ENDED. These differences are expected and are the evidence; they are never part
      of the Simulation History or surface comparison.
 8. Record the evidence (§7).
```

The uninterrupted reference `R` is a separate Execution in a separate
process; the witness never compares `B` against anything produced in its
own process except the document it was given.

What each prohibited path would fail: a rerun from zero emits `DIAGNOSTIC`
records below 12 and has a count of `final + 1`; a History-folding loader
violates the typed boundary of §5.1, which the architecture tests detect
(a function producing a `Snapshot` or engine state from History, anywhere
in the package), and, where it skips verification, the tampering witnesses
of §6 refuse where it would have continued. Process death with a distinct
PID proves death; the typed boundary, the call-graph prohibition, the
receipts and the tampering witnesses together are the bounded assurance
that the snapshot was the authority consumed.

## 5. Load verification (ordered contract)

`load(store, execution_id)` performs these verifications in this order and
refuses on the first failure with the named reason; nothing is partially
loaded; there is no override for any step.

1. **Store**: the Store directory and `store.json` exist, parse, and carry
   the code's Store schema version (`STORE_NOT_FOUND`, `STORE_MALFORMED`,
   `STORE_SCHEMA_MISMATCH`).
2. **Document**: `<store>/<execution_id>/run.json` exists
   (`EXECUTION_NOT_FOUND`) and parses as a Continuation Document against
   the schema: every required section and field present with the right
   type, no unknown sections (`MALFORMED`). A missing or mistyped field
   fails here, not later.
3. **Schema**: `schema_version` equals the code's constant
   (`SCHEMA_MISMATCH`).
4. **Code identity**: recorded `code_identity` equals the running process's
   computed code identity (`CODE_IDENTITY_MISMATCH`).
5. **Bindings**: the document's `store_id` equals the Store's
   (`STORE_MISMATCH`); its `execution_id` equals the requested path's
   (`EXECUTION_MISMATCH`).
6. **Identities**: recomputed `configuration_hash`, `trace_hash` and
   `run_id` equal the recorded ones (`CONFIG_HASH_MISMATCH`,
   `TRACE_HASH_MISMATCH`, `RUN_ID_MISMATCH`).
7. **Standing**: `standing` is `RUNNING` (`EXECUTION_FINAL` otherwise);
   `snapshot` is present and `final` is null (`MALFORMED` otherwise, since
   the schema makes them conditional on standing).
8. **Inputs**: the embedded Configuration and Trace pass Trace-load
   validation, including `source_id` uniqueness and the domain bounds
   (`INPUT_INVALID`).
9. **Snapshot internal consistency** (`STATE_INCONSISTENT`), in this order:
   - `t >= 0`; `snapshot_hash` equals the hash of the canonical snapshot
     bytes;
   - elevators: exactly the ids `0..N-1`, each once, ascending; every
     `floor` in `0..F-1`; every `heading` in `{UP, DOWN, NONE}`;
   - passengers: exactly the ids `{p : request_time(p) < t}`, each once,
     ascending; every `source_id` equals the Trace's for that id;
   - every `assigned_elevator` in `0..N-1`; `assigned_at == request_time`;
   - standing/field consistency: `WAITING` has assignment and null pickup
     and dropoff; `ONBOARD` has pickup set and null dropoff; `COMPLETED`
     has both set; `pickup >= request_time`; `dropoff > pickup`; every set
     time is `< t`; `dropoff - pickup == |destination - origin|` for
     `COMPLETED`;
   - reconstructed load per elevator (count of `ONBOARD` with that
     assignment) `<= C`.
10. **History internal consistency** (`HISTORY_INCONSISTENT`), by the
    isolated verifier of §5.2: `history_hash` equals the hash of the
    canonical history bytes; `tick_records` is exactly ticks `0..t-1`,
    each with exactly the ids `0..N-1`; events are in sequence from 0 with
    no gaps, every tick in `0..t-1`, no run-standing event and no
    Operational Record among them; and the verifier's replay agrees with
    every TickRecord field as specified in §5.2.
11. **Snapshot versus History** (`STATE_HISTORY_MISMATCH`):
    - if `t == 0`: no TickRecords, no events; every floor equals its
      configured initial floor and every heading is `NONE`;
    - if `t > 0`: for every elevator, snapshot `floor` equals
      `tick_records[t-1][E].floor + delta(tick_records[t-1][E].heading)`
      and snapshot `heading` equals `tick_records[t-1][E].heading`;
    - for every passenger in the snapshot: `ASSIGNED` exists iff assignment
      set, with equal elevator and tick; `BOARDED` exists iff
      `pickup_time` set, with equal tick and elevator; `ALIGHTED` exists
      iff `dropoff_time` set, with equal tick and elevator; standing agrees
      with the events' presence; no event refers to a passenger absent
      from the snapshot;
    - the verifier's final state at the boundary (its own onboard sets and
      floors) equals the snapshot's; this equality is a check, and the
      verifier is discarded afterwards.

Then the loader builds the typed `Snapshot` from the document's snapshot
section (§5.1), calls `construct_state(snapshot)`, hashes the constructed
state canonically, appends `LOAD_ADMITTED` and `RESUMED(t)`, attaches the
History prefix as the engine's history without transformation, and tick `t`
begins. Derived values (loads, routes) are recomputed on demand as in any
tick.

### 5.1 The typed snapshot boundary

- `Snapshot` is a value type defined in the checkpoint module. The only
  constructor of a `Snapshot` in the simulation package is
  `parse_snapshot(document)`, which reads the document's snapshot section
  and nothing else; it does not accept events, tick records or a
  `HistoryPrefix`.
- `HistoryPrefix` is a distinct value type produced by
  `parse_history(document)`. It cannot be passed where a `Snapshot` is
  required (distinct types; a runtime assertion in `construct_state`
  rejects anything but a `Snapshot`).
- `construct_state(snapshot: Snapshot) -> EngineState` is the only function
  in the simulation package that produces engine state during a resume,
  and it is called only by `load`.
- No function anywhere in the simulation package or the web package takes
  a `HistoryPrefix`, a list of events or tick records, or a `HistoryVerifier`
  and returns a `Snapshot`, an `EngineState`, or any value that is then
  passed to `construct_state`. The architecture test
  `no_history_to_state_path_in_package`
  ([testing_contract.md](testing_contract.md) §7) scans every module's
  call graph and annotations for such a function, and a deliberately
  cheating fixture module placed under the test tree must be detected by
  the same scan.
- `HistoryVerifier` (§5.2) is a distinct type with no conversion to
  `Snapshot` or `EngineState`.

### 5.2 The isolated history verifier

Historical verification may replay receipts into an isolated verifier
solely to determine whether the History is internally lawful. Its result
may not be used as resumed present state.

The verifier starts from the configured initial floors and headings
`NONE`, with no passengers, and replays ticks `0..t-1` using the events as
the given assignments and the shared Route Policy functions for
everything else:

- at tick `k`: apply `REVEALED` and `ASSIGNED` events of tick `k` (every
  `ASSIGNED` must have `k == request_time` and exactly one preceding
  `REVEALED`; at most one `ASSIGNED`, `BOARDED`, `ALIGHTED` per passenger,
  in that order);
- alight: the set of its onboard passengers whose destination equals the
  car's floor must equal `tick_records[k][E].alighted` and the `ALIGHTED`
  events of `(k, E)`;
- board: `departure_direction` and `eligible_boarders` over its own
  waiting set must yield exactly `tick_records[k][E].boarded` and the
  `BOARDED` events of `(k, E)`;
- heading: the promised departure, else `next_heading`, must equal
  `tick_records[k][E].heading`;
- load: its onboard count after boarding must equal
  `tick_records[k][E].load` and must be `<= C`;
- floor: `tick_records[k][E].floor` must equal its floor, which starts at
  the initial floor and advances by `delta(heading)` each tick; every floor
  in range;
- every `BOARDED` passenger's `dir` equals the recorded heading; every
  `ALIGHTED` passenger's travel equals its distance.

Any disagreement is `HISTORY_INCONSISTENT`. This is full route-law
verification over the prefix: every consequential TickRecord field
(`floor`, `heading`, `load`, `boarded`, `alighted`) is checked against the
verifier's replay, and the verifier is discarded when step 11 completes.
What is trusted without recomputation: nothing in the TickRecords; the
`ASSIGNED` choices themselves (the scheduler's decisions are receipts and
are not re-decided).

## 6. Negative witnesses

Each is a test that constructs the failure and asserts the refusal or the
non-effect. Each refusal must already be a rule above; the witness invents
no semantics. Constructions start from the byte copy `D12` of §4.2 step 3,
written back to `S/e_A/run.json` (or to a fresh Store and Execution
directory where stated), with `operational.jsonl` left as A wrote it (the
loader never reads it). Columns: what is mutated; which dependent integrity
fields are recomputed; what is preserved; which earlier steps therefore
pass; the expected refusal and step. The fixture `D12` is chosen so that
at least one `WAITING` passenger has `request_time + distance < 12` (row
24 needs it) and the witness asserts that before proceeding.

Where a row's dependencies exist decides which implementation cut runs
it ([plans/implementation_plan.md](plans/implementation_plan.md)): rows
that need only the checkpoint and store modules and an in-process engine
are **cut 9 local** continuity-negative tests; rows that need process
orchestration, death, or the harness's evidence qualification are **cut
10**; the UI half of row 29 is **cut 11**. The column "Cut" says which.

| # | Negative witness | Mutation | Recomputed | Preserved | Earlier steps pass | Expected | Cut |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Missing snapshot field | delete `elevators[1].heading` | nothing | all identities | 1 | `MALFORMED` at 2 (schema: required field absent) | 9 |
| 2 | Missing section | delete `tick_records` | nothing | all identities | 1 | `MALFORMED` at 2 | 9 |
| 3 | Final Execution in its Store | let B complete (finality written); `load(S, e_A)` | n/a | everything | 1 to 6 | `EXECUTION_FINAL` at 7 | 9 |
| 4 | Final Execution, different output directory | as 3 with a new empty output directory | n/a | everything | 1 to 6 | `EXECUTION_FINAL` at 7 (outputs never consulted) | 9 |
| 5 | Copy into another Store | create `S2`; copy `D12` to `S2/e_A/run.json` | nothing | `store_id = s1` inside | 1 to 4 | `STORE_MISMATCH` at 5 | 9 |
| 6 | Overwrite inside the Store (limit) | copy `D12` over `S/e_A/run.json` after finality | nothing | everything | all | admitted; recorded as the design's stated limit, neither pass nor fail | 9 (limit) |
| 7 | Independent Execution of the same Run | execute the same inputs in `S` as a new Execution `e_C` with a checkpoint at 12; also complete `e_A`; `load(S, e_C)` | n/a | `e_C`'s own document | all | admitted: `e_C` is its own Execution and `e_A`'s finality is irrelevant; the witness asserts both `run_id`s are equal and the Simulation Histories identical | 9 |
| 8 | Document under the wrong Execution path | copy `D12` to `S/e_X/run.json` for a fresh random `e_X`; `load(S, e_X)` | nothing | `execution_id = e_A` inside | 1 to 4 | `EXECUTION_MISMATCH` at 5 | 9 |
| 9 | Stale writer | starting standing `RUNNING`, `write_sequence = 1` (D12), writer A holds token 1. Intermediate lawful mutation: A performs an admitted checkpoint write (reads token 1, writes `RUNNING` with `write_sequence = 2`, now holds token 2; in the fixture this is the checkpoint module's write function called in-process with A's token). Attempted mutation: writer B, simulated as an old holder of token 1, calls the write function against the still-`RUNNING` document with token 1 | n/a | the `RUNNING` document at `write_sequence = 2` | n/a (a write, not a load) | `STALE_WRITER`; B halts; the document still carries `write_sequence = 2` and A's content | 9 |
| 10 | Write after final | starting standing `RUNNING`, `write_sequence = 1`, token 1. Intermediate lawful mutation: the admitted finality write (standing `COMPLETED`, `write_sequence = 2`). Attempted mutation: a checkpoint write with token 2 (the current token, so the sequence matches) | n/a | the final document | n/a | `WRITE_AFTER_FINAL`; unchanged. Kept separate from row 9: standing, not sequence, refuses here | 9 |
| 11 | Corrupted Trace bytes | flip one byte in a Trace row | nothing | recorded `trace_hash` | 1 to 5 | `TRACE_HASH_MISMATCH` at 6 | 9 |
| 12 | Truncated file | truncate the document | nothing | n/a | 1 | `MALFORMED` at 2 | 9 |
| 13 | Edited configuration, hash not updated | change `F` | nothing | recorded hash | 1 to 5 | `CONFIG_HASH_MISMATCH` at 6 | 9 |
| 14 | Edited configuration, hash updated | change `F`; recompute `configuration_hash` | `configuration_hash` | recorded `run_id` | 1 to 5 | `RUN_ID_MISMATCH` at 6 | 9 |
| 15 | Different code | load `D12` with a process whose governed package differs by one comment byte, under the execution contract | nothing | everything | 1 to 3 | `CODE_IDENTITY_MISMATCH` at 4; no flag or environment variable changes this | 9 |
| 16 | Unsupported environment | start B with bytecode writing enabled, or with a `__pycache__` present in the package | n/a | n/a | n/a | `UNSUPPORTED_EXECUTION_ENVIRONMENT` before any load | 9 |
| 17 | Mutated heading | set `elevators[0].heading` from `UP` to `DOWN` | `snapshot_hash` | `simulation_history`, all identities | 1 to 10 | `STATE_HISTORY_MISMATCH` at 11 (snapshot heading differs from `tick_records[t-1]`); a History-folding loader would have continued | 9 |
| 18 | Mutated floor | change one `floor` by one, in range | `snapshot_hash` | `simulation_history` | 1 to 10 | `STATE_HISTORY_MISMATCH` at 11 | 9 |
| 19 | Mutated heading, hash not recomputed | as 17 without recomputing | nothing | n/a | 1 to 8 | `STATE_INCONSISTENT` at 9 (`snapshot_hash`); included to pin the ordering | 9 |
| 20 | Duplicate or missing elevator | duplicate elevator 1's entry; separately remove elevator 2 | `snapshot_hash` | history | 1 to 8 | `STATE_INCONSISTENT` at 9 | 9 |
| 21 | Invalid assignment id | set a passenger's `assigned_elevator` to `N` | `snapshot_hash` | history | 1 to 8 | `STATE_INCONSISTENT` at 9 | 9 |
| 22 | Capacity-corrupt passenger set | set `C+1` passengers `ONBOARD` the same car with consistent fields | `snapshot_hash` | history | 1 to 8 | `STATE_INCONSISTENT` at 9 | 9 |
| 23 | Impossible completed travel | set a `COMPLETED` passenger's `dropoff_time` to `pickup_time + distance + 1` | `snapshot_hash` | history | 1 to 8 | `STATE_INCONSISTENT` at 9 | 9 |
| 24 | Resurrection with consistent fields | choose a `WAITING` passenger `p` with `request_time(p) + distance(p) < t`; set it to `COMPLETED` with `pickup = request_time(p)`, `dropoff = pickup + distance` (so step 9's time ordering and `< t` checks pass) | `snapshot_hash` | history (no `BOARDED`/`ALIGHTED` for `p`) | 1 to 10 | `STATE_HISTORY_MISMATCH` at 11 | 9 |
| 25 | Forged recorded load | change an intermediate `tick_records[k][E].load` to `C+1` | `history_hash` | snapshot, events | 1 to 9 | `HISTORY_INCONSISTENT` at 10 (verifier load disagrees) | 9 |
| 26 | Forged boarded set | add a passenger id to `tick_records[k][E].boarded` with no `BOARDED` event | `history_hash` | snapshot, events | 1 to 9 | `HISTORY_INCONSISTENT` at 10 | 9 |
| 27 | Wrong-way boarding in History | move a `BOARDED` event and its `boarded` entry to a tick where the recorded heading opposes the passenger's direction | `history_hash` | snapshot | 1 to 9 | `HISTORY_INCONSISTENT` at 10 | 9 |
| 28 | Operational record inside the History | insert a `CHECKPOINT_WRITTEN`-shaped record among `events` | `history_hash` | snapshot | 1 (schema allows only Simulation Event kinds) | `MALFORMED` at 2; variant with a Simulation-Event-shaped record of unknown kind: `MALFORMED` at 2 | 9 |
| 29 | Projection disagreement | (a) after resume, regenerate the position exports from TickRecords and compare with R's; (b) separately, compare the UI shaft projection with engine state | n/a | n/a | n/a | identical; identical (any difference is `HALTED`-class corruption, constitution §14) | (a) 10; (b) 11 |
| 30 | Transient-authority leakage | B is started with a clean environment and no arguments but `--store`, `--resume`, `--witness-instrumentation` and an output directory; the witness asserts this from B's `EXECUTION_STARTED` record | n/a | n/a | n/a | the continuation succeeds with no such inputs | 10 |
| 31 | Process-local continuation | the "continuation" is run with A still alive (no kill) in a variant, and the harness is asked to label it | n/a | n/a | n/a | the harness refuses to label it CPOC evidence | 10 |
| 32 | Receipt missing | kill A between the rename and the receipt append (a test hook) | n/a | document | all | the document loads lawfully; the witness attempt is recorded `EVIDENCE_INCOMPLETE` and fails certification, not the load | 10 |
| 33 | Log flush at late binding | a live Execution (no output directory) steps to tick 5 with `--witness-instrumentation`, then takes its first explicit checkpoint into `S` | n/a | the in-memory buffer | n/a | `S/e/operational.jsonl` begins with `EXECUTION_STARTED` (`op_seq` 1), the `DIAGNOSTIC` records 0..4 in order, then `CHECKPOINT_WRITTEN`; no record is duplicated; a later resume continues `op_seq` from the file | 9 |
| 34 | Never-bound Execution | `simulate(rows, ..., output_dir=None)` | n/a | n/a | n/a | the result is complete and its Reproducible Output Surface is byte-identical to a bound Execution's; no file is written anywhere; the harness refuses to accept the Execution as CPOC evidence | 8 |

No-look-ahead across process death is not a continuation witness: the
future-request mutation test is [testing_contract.md](testing_contract.md)
§3, which constructs a second lawful Run (different `run_id`, same prefix)
and compares decision and motion prefixes; its cross-process variant simply
runs each Run in its own process.

## 7. Evidence record

Each execution of the witness writes `docs/cpoc/witness_<date>_<code_identity>.md`
(after implementation) with:

```text
Subject: continuation of Execution e_A of run <run_id> from t=12 (policy ...)
Code identity; Git SHA and worktree standing (provenance only); execution contract confirmed (python -B, no __pycache__)
Store: path, store_id, store schema version
Fixture: path, trace hash, configuration hash
Execution R: execution_id, PID, exit code, operational records
Execution A: execution_id, PID, CHECKPOINT_WRITTEN (document SHA-256 d_A, write_sequence 1, H_s, H_h), killed by SIGKILL, exit by signal confirmed, document SHA-256 re-read == d_A
Process B: PID, argv, environment summary, LOAD_ADMITTED payload (document SHA-256 == d_A), RESUMED, FINALITY_WRITTEN (write_sequence 2)
Loader verifications: 1..11 PASS in order; verifier discarded
Simulation History comparison: tick_records (t>=12) identical / events identical with sequence numbers / prefix+continuation == R
Reproducible Output Surface: every file identical to R's
Anti-recomputation: DIAGNOSTIC ticks for B start at 12, none below, count = ...; architecture tests green at this code identity
Negative witnesses: each number -> PASS/FAIL (6 -> LIMIT, 7 -> ADMITTED as designed)
Command and configuration:
Counts: pass / fail / skip / error
CPOC standing: PASS / FAIL
```

The record is evidence. It does not become authority for anything it
observed.

## 8. Standings

- `CPOC PASS`: the witness of §4.2 and every negative witness of §6
  (except 6, which records a limit, and 7, which asserts admission) passed
  for the exact code identity, for both policies, with every receipt
  present in a durable, Store-bound Operational Log.
- `CPOC FAIL`: any assertion failed or any refusal did not occur.
- `EVIDENCE_INCOMPLETE`: a required receipt was absent; the attempt is
  repeated.
- `IMPLEMENTED NOT CERTIFIED`: continuation code exists but the witness has
  not run, or its record is absent.
- `STOPPED`: the witness exposed an authority or semantic contradiction;
  work returns to the owner.

Staged standing for implementation cuts is defined in
[plans/implementation_plan.md](plans/implementation_plan.md): a cut that
touches persistence, reconstruction, the tick procedure, Passenger or
Elevator fields, or the Simulation History may be `IMPLEMENTED / LOCAL
VERIFY PASS / CPOC PENDING` until the witness runs, and receives its
CPOC-qualified standing only after `CPOC PASS`.

## 9. Why no database

The durable state is one JSON document and one append-only log per
Execution in a Store directory. There is one writer per Execution, one
reader, no concurrent access by design, no query need, and no partial
update. Write admission is a one-integer check against the document at the
path. A database would add a second carrier with its own consistency
semantics and nothing the witness needs.

## 10. Constitutional Delta of this document

Relative to revision 5 (proposed in
[decisions/owner_decision_003_revision_6_repairs.md](decisions/owner_decision_003_revision_6_repairs.md)):
Revision 7 (proposed in
[decisions/owner_decision_004_revision_7_closure.md](decisions/owner_decision_004_revision_7_closure.md)):
`ΔS`: the Operational Log carrier lifecycle (§2.2a); the stale-writer and
resurrection fixtures; `ΔO/ΔA`: none. Revision 6: `ΔO`: Execution and
`execution_id`; the Operational Log as a separate
file; `HistoryVerifier`, `Snapshot` and `HistoryPrefix` as distinct types;
`ΔS`: write admission; receipt ordering; the eleven-step order with the
isolated verifier; the bounded assurance standard; `ΔA`: the executing
process owns its Execution's document and log. The witness harness, when
built, is an evidence carrier and may never repair, reconcile, select or
become fallback authority for the facts it tests.
