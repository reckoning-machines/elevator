# Authority Model

Status: **GOVERNING DOCUMENT for ownership. DRAFT, NOT ADMITTED. Revision 7.1 (bounded component-mapping and reference repairs, 2026-11-05).**

Jurisdiction: for every consequential fact, who owns it, its representation
class, who may write it, who may read it, whether it is persisted, how it is
reconstructed after process death, whether it is historical or mutable, and
which projections or caches of it may exist. Subordinate to
[constitution.md](constitution.md) §3; this document details it and may not
contradict it.

## 1. Representation classes used

Exactly the six classes adopted from `fin123-core`
([doctrine_adoption.md](doctrine_adoption.md)); lifecycle standings
(`WAITING`, `ONBOARD`, `RUNNING`, and so on) are not classes.

- `AUTHORITATIVE`: the one representation that establishes the fact; every
  write crosses its commit boundary; missing or contradictory authority fails
  closed.
- `DERIVED`: reproducible from exact authoritative inputs; no writer of its
  own; no decision right; recomputed, never trusted when stale. Identity
  hashes (`run_id`, Trace hash, Experiment ids) are `DERIVED` from the
  content they name.
- `CACHE`: replaceable acceleration; discardable; never repairs its source.
- `RECEIPT`: immutable evidence of an exact event, emitted inseparably from
  the commit that caused it; authoritative only for "this happened".
- `LEGACY_ONLY`: old-data compatibility with a bounded removal. **None exists
  in this project and none may be created without an owner decision.**
- `EPHEMERAL`: safely losable process-, tick- or interaction-lifetime state;
  never the sole carrier of a governed fact.

## 2. Commit boundaries

Revision 7.1 maps the existing Execution identity and Operational Log
operations to `operations.py` (architecture §1). The executing process
remains the owner of rows 26 and 37 and invokes the same Execution creation
and Operational Log append boundaries. The module has no independent
decision right, Store authority, continuation standing or simulation state.
API, reporting and checkpoint callers use the same Execution/log handle;
they do not become competing owners. `ΔO / ΔS / ΔA = NONE` for this
component relocation; the row-38 phase reference is corrected below.

| Boundary | What crosses it | Who may invoke it |
| --- | --- | --- |
| **Code identity establishment** | the process's code identity, read from its own governed package under the supported execution contract (constitution §12) before any Run begins | every governed entry point (CLI, web server, witness subprocesses, the public functions) |
| **Store creation** | `store.json` with a fresh `store_id` and the Store schema version | CLI (`store init`), harness, UI server, explicitly |
| **Trace load** | Configuration and the normalized Trace enter a Run; validation including `source_id` and the domain bounds; hashes and `run_id` computed | the public `normalize_requests` + `simulate` / `create_engine` boundaries, CLI, harness, UI server, loader (embedded copy) |
| **Execution creation** | `execution_id` minted; the Store bound if checkpoint controls are set; `EXECUTION_STARTED` appended | the executing process, after Trace load |
| **Tick procedure** ([simulation_semantics.md](simulation_semantics.md) §2) | every runtime fact: time, reveal, assignment, boarding, alighting, heading, floor, Simulation Events, TickRecords, the Run outcome | the engine only, one tick at a time |
| **Checkpoint write** | the Execution's Continuation Document, atomically, at a tick boundary, under write admission | the process, on request (`--checkpoint-at`, `--checkpoint-every`, UI action) |
| **Finality write** | the Execution's Continuation Document standing to final, with the complete Simulation History, under write admission | the process, after the Run outcome, only if the document exists |
| **Load** | admission or refusal of a Continuation Document by `(store, execution_id)`; isolated verification of the History prefix; construction of engine state from the typed snapshot; `LOAD_ADMITTED` and `RESUMED` records | the loader only |
| **Operational Log append** | one Operational Record in `<store>/<execution_id>/operational.jsonl` (or the output directory's copy for an Execution without a Store) | the process that performed the execution fact |
| **Scenario generation** | a Trace from `(pattern, parameters, seed)` | the harness |
| **Experiment execution** | the experiment execution id; definition and results files | the harness |

There are no other writers of consequential facts.

## 3. The authority table

Columns: **Owner** (the component with the decision right), **Class** of the
canonical carrier, **Write** (the only boundary that writes it), **Read**
(allowed readers), **Persist** (whether it must be durable for continuation),
**Reconstruct** (what a fresh process does), **H/M** (historical, mutable,
or historical-once-written), **Projections** (lawful non-authoritative
copies and their classes).

### 3.1 Inputs and identity

| # | Fact | Owner | Class | Write | Read | Persist | Reconstruct | H/M | Projections |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Simulation configuration (`F`, `N`, `C`, initial floors, `max_ticks`, policy name and parameters) | Configuration carrier (input file, function arguments or harness-generated dict), bound into the Run by hash | `AUTHORITATIVE` | Trace load | engine, policy (via view: `F`, `N`, `C` only), harness, UI | Yes, embedded in the Continuation Document with its hash | Loaded from the document; hash re-verified; mismatch refuses | H | UI controls form (`EPHEMERAL`); results header (`DERIVED`) |
| 2 | Request definitions (the Trace), each Request carrying `source_id`, `input_index`, `request_time`, `origin`, `destination` | Trace carrier (input rows, file or Scenario output), bound by hash | `AUTHORITATIVE` | Trace load (validation: floors, `origin != destination`, time `>= 0`, `source_id` non-empty and unique) | engine only in full; policies only via revealed passengers | Yes, embedded with its hash | Loaded from the document; hash re-verified | H | passenger table rows (`DERIVED`); UI waiting list (`DERIVED`) |
| 3 | The `source_id` to `passenger_id` mapping | Trace load (stable sort by `(request_time, input_index)`) | `DERIVED` from row 2 | Trace load | all | Implied by the Trace | Recomputed; must equal the ids in the snapshot | H | every output names both ids |
| 4 | Code identity | the running process, computed from its own governed package's `.py` bytes before any Run begins, under the supported execution contract (constitution §12) | `AUTHORITATIVE` for "which source the process was started from under the contract"; immutable for the process | Code identity establishment | Trace load (into `run_id`), loader (equality check), harness (into the experiment execution id), outputs | Yes, recorded in the Continuation Document, `run_identity.json`, `experiment_results.json` and every Operational Record | Recomputed by the fresh process from its own package; must equal the recorded value or the load refuses (`CODE_IDENTITY_MISMATCH`, no override) | H | Git SHA and worktree standing recorded in `execution_metadata.json` as provenance (`DERIVED` label; never checked, never substituted). Denied: it does not attest executing instructions outside the contract |
| 5 | Continuation Document schema version and Store schema version | constants of the code (therefore inside row 4) | `AUTHORITATIVE` as code | code | writer, Store creation, loader | Yes, written into the document and into `store.json` respectively | Equal or refuse (`SCHEMA_MISMATCH`, `STORE_SCHEMA_MISMATCH`) | H | none |
| 6 | `run_id`, Configuration hash, Trace hash | Trace load | `DERIVED` identities of rows 1, 2, 4 | Trace load | all | Yes, recorded and re-verified | Recomputed from embedded content; mismatch refuses | H | none |
| 7 | Store identity (`store_id`) | the Store (`store.json`) | `AUTHORITATIVE` | Store creation | the process (bound into every Continuation Document it writes there), loader | It is durable | Read from `store.json`; a document whose `store_id` differs refuses (`STORE_MISMATCH`) | H | none |

### 3.2 Runtime state (engine-owned)

| # | Fact | Owner | Class | Write | Read | Persist | Reconstruct | H/M | Projections |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | Request visibility at the start of tick `t` (which Requests are revealed) | engine | `DERIVED` from Trace and `t` (revealed iff `request_time < t` at a boundary; `<= t` after step 1 of tick `t`), materialised as Passenger existence | Tick step 1 | policies (revealed only), UI, harness | Implied by `t` and Trace | The snapshot's passenger set must equal `{p : request_time < t}` exactly | H per tick | none |
| 9 | Current simulation time `t` | engine | `AUTHORITATIVE` | Tick step 9 | all | Yes | From the snapshot | M | UI clock (`EPHEMERAL`); TickRecord `t` (`RECEIPT`) |
| 10 | Passenger standing (`WAITING`, `ONBOARD`, `COMPLETED`) | engine | `AUTHORITATIVE` (the standing field) | Tick steps 2, 4, 3 respectively | all | Yes | From the snapshot; must agree with the fields (row 11 to 13) and with the events (row 18) | M until `COMPLETED` | UI badges (`DERIVED`); throughput (`DERIVED`) |
| 11 | Passenger assignment (`assigned_elevator`, `assigned_at`) | engine | `AUTHORITATIVE`, write-once | Tick step 2 | all | Yes | From the snapshot; must agree with `ASSIGNED` events | H once written | `ASSIGNED` event (`RECEIPT`); UI assignment badge (`DERIVED`) |
| 12 | Pickup time | engine | `AUTHORITATIVE`, write-once | Tick step 4 (capacity and departure-direction gated, via `eligible_boarders`) | all | Yes | From the snapshot; must agree with `BOARDED` event | H once written | `BOARDED` event (`RECEIPT`); passenger table (`DERIVED`) |
| 13 | Dropoff time | engine | `AUTHORITATIVE`, write-once | Tick step 3 | all | Yes | From the snapshot; must agree with `ALIGHTED` event | H once written | `ALIGHTED` event (`RECEIPT`); passenger table (`DERIVED`) |
| 14 | Elevator position (`floor`) | engine | `AUTHORITATIVE` | Tick step 8 | all | Yes | From the snapshot; must equal the last TickRecord's floor plus its heading (initial floors at `t = 0`) | M | TickRecord floor (`RECEIPT`); position exports (`DERIVED`); UI shaft view (`DERIVED`) |
| 15 | Elevator direction (`heading`) | engine | `AUTHORITATIVE` | Tick step 5 | all | Yes | From the snapshot; must equal the last TickRecord's heading (`NONE` at `t = 0`) | M | TickRecord heading (`RECEIPT`); UI arrow (`DERIVED`) |
| 16 | Departure direction `departure_E` (`UP`, `DOWN`, `FREE`) at the current floor in the current tick | engine, via `departure_direction` and `eligible_boarders` | `EPHEMERAL` (intra-tick) | computed in step 4; consumed in step 5; discarded | steps 4 and 5 only; the projection computes its own | No; never persisted | Never reconstructed; recomputed by the next tick's step 4 | n/a | none. Denied: it is not an elevator field, is never stored, never checkpointed, never read by a policy or the UI; `FREE` is not a heading |
| 17 | Run outcome (`COMPLETED` with final tick, or `HALTED` with final tick, step and reason) | engine | `AUTHORITATIVE` in memory; the run-standing Simulation Event is its `RECEIPT` | Tick step 7, or the step that detects a halt | all | As part of the Simulation History | From the History's run-standing event | H once decided | `run_identity.json` standing field (`DERIVED`, never consulted by the loader); UI standing (`DERIVED`) |
| 17a | Execution standing (`RUNNING`, `COMPLETED`, `HALTED`) and the document's `write_sequence` | the executing process | `AUTHORITATIVE`, carried by the Continuation Document when one exists | Checkpoint write and Finality write, under write admission (constitution §4.3) | the loader; the writer (admission check); UI | Yes, when a document exists | From the document: a final standing refuses continuation (`EXECUTION_FINAL`); `RUNNING` admits; `write_sequence` is the writer's admission token | M until final; H once final | `execution_metadata.json` standing field (`DERIVED`, never consulted) |
| 18 | Simulation History: Simulation Events (`REVEALED`, `ASSIGNED`, `BOARDED`, `ALIGHTED`, `COMPLETED`, `HALTED`) and TickRecords | engine | `RECEIPT`, append-only; the declared immutable history of the simulated world | each tick step that establishes a transition; step 6 for TickRecords; step 7 for run-standing events | all | Yes: prefix through `t-1` while `RUNNING`; complete when final | Prefix loaded from the document and held as history; verified by the isolated verifier (row 38) against itself and against the snapshot; **never folded into present state** | H | `events.jsonl`, `tick_records.jsonl`, position exports (`DERIVED` serialisations) |
| 19 | Elevator load, onboard set, waiting set, committed stops | engine | `DERIVED` from rows 10, 11 and the floor | never written directly | all | No (recomputed) | Recomputed from the snapshot's Passengers | M | TickRecord load (`RECEIPT`); UI occupancy (`DERIVED`) |
| 20 | Elevator route (ordered future stops) | engine, via `project` | `DERIVED` (projection of the Route Policy functions over floor, heading, committed stops, waiting passengers) | never written; recomputed on demand | scheduler (own projection), UI | No | Recomputed | M | scheduler projection (`EPHEMERAL`); UI route strip (`DERIVED`) |
| 21 | Scheduler score estimates (projected pickup, dropoff, cost, tier per candidate) | the policy, for the duration of one call | `EPHEMERAL` | computed inside step 2, discarded | the policy; the engine copies the chosen candidate's estimate into the `ASSIGNED` event | No; the receipt copy is in the Simulation History | Not reconstructed; the receipt is read from History | n/a | `ASSIGNED` event `receipt` field (`RECEIPT`, never compared as realized); calibration report (`DERIVED`) |
| 22 | Realized capacity deferrals and wrong-way passes per passenger | reporting | `DERIVED` from the Simulation History under the classification rule of [simulation_semantics.md](simulation_semantics.md) §4.2 (direction decides first; capacity only at a compatible arrival) | output rendering | all | No | Regenerated | n/a | `passengers.csv` columns, metrics, observations (`DERIVED`) |

### 3.3 Continuity and execution

| # | Fact | Owner | Class | Write | Read | Persist | Reconstruct | H/M | Projections |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 23 | Continuation Document (snapshot + Simulation History prefix + `write_sequence` while `RUNNING`; final standing + complete Simulation History when final) | the executing process; held by the Store at `<store>/<execution_id>/run.json` | `AUTHORITATIVE` carrier of rows 1, 2, 4 to 7, 9 to 15, 17a, 18 for continuation and of row 17a for durable finality | Checkpoint write; Finality write, each under write admission | Load | It is the persistence | Admitted only by the loader after [cpoc_design.md](cpoc_design.md) §5; any refusal is final | H once written (each admitted write replaces the previous document atomically) | none; a document is never derived from another document, from outputs or from the Operational Log |
| 24 | Resumed simulation state | engine, in the fresh process | `AUTHORITATIVE` once constructed from the snapshot section; identical in class and owner to the pre-death state | Load, then the tick procedure | all | Continues to be checkpointed as any Run | n/a | M | same as the pre-death state |
| 25 | Load receipt (`LOAD_ADMITTED`: document SHA-256 of the bytes loaded, `snapshot_hash`, `history_hash`, constructed-state hash, `store_id`, `execution_id`, pid, code identity) | the loader | `RECEIPT` in the Operational Log | Operational Log append, at Load | the witness, operators | Yes, in the Operational Log | Not reconstructed | H | none. Denied: hash equality in the receipt proves value equality, not causal provenance; it is evidence beside the typed boundary of row 38, not a proof of consumption |
| 26 | Operational Log (`EXECUTION_STARTED`, `CHECKPOINT_WRITTEN`, `LOAD_ADMITTED`, `RESUMED`, `FINALITY_WRITTEN`, `EXECUTION_ENDED`, `CODE_IDENTITY_DRIFT`, `DIAGNOSTIC`), each record with `execution_id`, `op_seq` (from 1), tick, document SHA-256 where applicable, pid, code identity | the executing process for its own records | `EPHEMERAL` in-memory buffer from Execution creation until the Execution's evidence root exists; then `RECEIPT`, append-only, one file per Execution at `<root>/operational.jsonl`, the root being the Store directory `<store>/<execution_id>/` for a Store-bound Execution, else `<output>/<run_id>/<execution_id>/` when an output directory exists (cpoc §2.2a) | Operational Log append; the flush at binding writes the unflushed prefix once, in order | the witness, operators | As the file, once a root exists; never embedded in the Continuation Document; an Execution that never obtains a root keeps it in memory only | Read as evidence only; never validated to admit a load; a missing receipt fails witness evidence, not simulation authority; a never-bound Execution cannot be CPOC evidence | H once flushed | none. Denied: never in the Simulation History or the Reproducible Output Surface; never in `run_id`; never compared for P8 or P12; never read by a policy, the tick procedure or metric reporting; never establishes simulation state; never a second log |
| 27 | Checkpoint scheduling controls (`--checkpoint-at t`, `--checkpoint-every k`, `--pause-after-checkpoint`, `--witness-instrumentation`, the UI interval) | the invoking caller for one Execution | `EPHEMERAL` execution parameters | process arguments or UI form | the checkpoint hook; recorded in `EXECUTION_STARTED` | No (recorded as evidence only) | Not reconstructed; a resumed process has its own controls | n/a | none. Denied: not part of Configuration, `run_id` or any decision; cannot alter the Simulation History |
| 28 | Output directory | the invoking caller for one Execution | `EPHEMERAL` execution parameter; a storage location; outputs land at `<output>/<run_id>/<execution_id>/` | process arguments | the reporting writer | No | Not reconstructed | n/a | none. Denied: never consulted by the loader; never a selector of Execution standing, Store, Execution or Run |
| 29 | Process identity (pid, argv, environment summary) | the operating system; recorded by the process | `RECEIPT` fields inside Operational Records | Operational Log append | the witness | As evidence | n/a | H | none |

### 3.4 Evaluation

| # | Fact | Owner | Class | Write | Read | Persist | Reconstruct | H/M | Projections |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 30 | Monte Carlo scenario definitions (`pattern`, `parameters`, `seed`) | harness | `AUTHORITATIVE` for the Scenario | Experiment definition | harness, UI | Yes, in the Experiment definition file | Read from the file | H | the generated Trace (`DERIVED` from the Scenario by the exact generator; then `AUTHORITATIVE` as row 2 once bound into a Run by hash) |
| 31 | Random seed and generator state | harness (seed in row 30); generator state `EPHEMERAL` inside one `generate` call | `AUTHORITATIVE` as part of row 30; state `EPHEMERAL` | Experiment definition; generation | harness | Seed yes; state no | Seed read from the file; state recreated by generation | H | the `provenance` block of a Run (`DERIVED` label). No seed exists inside a Run: the engine has no randomness |
| 32 | Experiment definition (configuration, scenarios, seeds, policies) and its definition hash | harness | `AUTHORITATIVE`; the hash `DERIVED` | Experiment definition | harness, UI | Yes, `experiment_results.json` definition block | Read from the file | H | UI form (`EPHEMERAL`) |
| 33 | Experiment execution id = hash(definition hash, code identity) | harness, at execution start | `DERIVED` identity | Experiment run | all | Yes, in `experiment_results.json` | Recomputed | H | none |
| 34 | Experiment results: the Reproducible Experiment Result Surface (`experiment_results.json`: per-Run `run_id`, Trace hash, outcome, summaries, aggregates with `n_defined`, `n_pairs`, `halted_count`, paired comparisons) and the execution metadata (`experiment_execution.json`: per-Run `execution_id`s, paths, pid, timestamps) | harness | the result surface is `DERIVED` from the Runs' Reproducible Output Surfaces and byte-identical per definition and code identity; the execution metadata is a `RECEIPT` of the execution | Experiment execution | all | Both written | The result surface is regenerable by re-executing the same definition under the same code identity; the metadata is not | H once written | UI comparison table and chart (`DERIVED` from the result surface only) |
| 35 | Summary statistics and observations of a Run | reporting | `DERIVED` from Passenger records and the Simulation History of a final Run; part of the Reproducible Output Surface | output rendering | all | No; written to `summary.json` and `observations.md` | Regenerated | n/a | UI results panel (`DERIVED`); Monte Carlo aggregates (`DERIVED`) |
| 36 | UI state | UI server (session: which Execution is open, play/pause, interval); browser (form inputs, last fragment, play timer) | `EPHEMERAL` on both sides | request handlers | UI only | No | Lost; a session is recreated from a Store and `execution_id`, or a new Execution | M | none; the browser never persists simulation state |

### 3.5 Added at revision 6

| # | Fact | Owner | Class | Write | Read | Persist | Reconstruct | H/M | Projections |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 37 | `execution_id` | the executing process | `AUTHORITATIVE` operational identity, minted once (random 128-bit) | Execution creation | the loader (path and document binding), the Operational Log, execution metadata, the UI | Yes, in the Continuation Document, its path, every Operational Record and `execution_metadata.json` | Supplied by the caller to the loader; the document's recorded value must equal it (`EXECUTION_MISMATCH`) | H | none. Denied: never in `run_id`, the Simulation History, a decision or the Reproducible Output Surface; never a seed |
| 38 | History verifier working state (the isolated replay used by load verification) | the loader | `EPHEMERAL`, a distinct type (`HistoryVerifier`) that cannot be converted to `Snapshot` or engine state | created in Load step 10, retained through the comparison in step 11, then discarded before state construction | the loader only | No | n/a | n/a | none. Denied: may never become, feed or be compared as resumed present state; exists only to answer "is the History internally lawful" |
| 39 | Reproducible Output Surface (`elevator_positions.csv`, `position_log_long.csv`, `passengers.csv`, `summary.json`, `observations.md`, `events.jsonl`, `tick_records.jsonl`, `run_identity.json`) | reporting | `DERIVED` from the Simulation History, Passenger records and `run_id` inputs only | output rendering | all | Written per Execution; byte-identical across Executions of a Run | Regenerated | n/a | none. Denied: no execution fact may appear in it (constitution N18) |
| 40 | Execution metadata (`execution_metadata.json`: `execution_id`, `store_id` if any, Git SHA and worktree standing, scenario provenance, checkpoint controls, pid, timestamps, Execution standing as reported) | the executing process | `RECEIPT` of the Execution; informational | output rendering | all | Written per Execution | Not reconstructed | H | none. Denied: outside every equality claim; never consulted by the loader |
| 41 | Normalized Trace (the output of `normalize_requests`) | Trace load | `DERIVED` from the input rows; becomes row 2 once bound | Trace load | `simulate`, `create_engine`, CLI, UI | As row 2 | As row 2 | H | none |

## 4. Rules the table implies

- **The browser is never authoritative** for any row. Row 36's browser side
  holds form inputs and rendered HTML only.
- **Estimates are never outcomes.** Row 21 lives only as `EPHEMERAL` during
  a policy call and as a `RECEIPT` on the `ASSIGNED` event. No Passenger
  field holds an estimate. The calibration report compares receipts with
  rows 12 and 13 and writes nothing back.
- **Position exports are projections of TickRecords** (rows 14, 18). The
  files are regenerated from History and may never be read to establish a
  position.
- **Load, route and departure direction are derived or ephemeral** (rows 16,
  19, 20). The engine stores none of them. The only authoritative elevator
  fields are floor and heading.
- **Assignment, pickup and dropoff are write-once.** The engine's Passenger
  record is the authority; the matching Simulation Event is the receipt;
  they must agree, and a disagreement on load is a refusal (§5).
- **Present state is never reconstructed from History, and History is never
  reconstructed from present state.** The loader constructs rows 9 to 15
  and 17 from the snapshot section only (constitution N14) and validates
  them against the History prefix.
- **Execution standing has one durable carrier** (row 23, standing block
  and `write_sequence`), and writes to it are admitted, never assumed
  (constitution §4.3). Output files, output directories and caller
  arguments (rows 27, 28) cannot establish or select it. The Run outcome
  (row 17) is a simulation fact, identical for every Execution.
- **The Operational Log is sealed off** (row 26): a separate file, never
  embedded in the document, never hashing itself, never touching the
  Simulation History, `run_id`, decisions, metrics or the Reproducible
  Output Surface.
- **The Reproducible Output Surface is closed** (row 39) and execution
  metadata (row 40) is outside it; P8 and P12 quantify over the former.
- **Code identity is computed, never supplied** (row 4). There is no
  override.
- **No `CACHE` carrier exists in the design.** If one is introduced (for
  example memoised route projections inside one policy call), it is bound to
  the exact state hash of that call and discarded with it.
- **No `LEGACY_ONLY` carrier exists.** Schema changes are refusals (row 5),
  not compatibility paths.

## 5. Load verification (summary; the ordered contract is cpoc §5)

The loader refuses, with a named reason and without fallback, on the first
failure in the order of [cpoc_design.md](cpoc_design.md) §5. The reasons:

| Reason | Condition |
| --- | --- |
| `STORE_NOT_FOUND` / `STORE_MALFORMED` / `STORE_SCHEMA_MISMATCH` | the Store directory or its `store.json` is missing, unparseable, or of another Store schema version |
| `EXECUTION_NOT_FOUND` | no `<store>/<execution_id>/run.json` |
| `EXECUTION_MISMATCH` | the document's recorded `execution_id` differs from the path requested |
| `MALFORMED` | the document is not parseable as a Continuation Document |
| `SCHEMA_MISMATCH` | `schema_version` is not the one the code writes |
| `CODE_IDENTITY_MISMATCH` | recorded code identity differs from the running process's computed code identity; no override exists |
| `STORE_MISMATCH` | the document's `store_id` differs from the Store's |
| `CONFIG_HASH_MISMATCH` / `TRACE_HASH_MISMATCH` / `RUN_ID_MISMATCH` | a recomputed identity differs from the recorded one |
| `EXECUTION_FINAL` | the document's standing is `COMPLETED` or `HALTED` |
| `INPUT_INVALID` | the embedded Configuration or Trace fails Trace-load validation |
| `STATE_INCONSISTENT` | the snapshot section fails an internal check: elevator id set, duplicates, floor range, heading domain, passenger id set, duplicates, visibility set, assignment ids in range, standing/field consistency, load `<= C` |
| `HISTORY_INCONSISTENT` | the Simulation History prefix fails the isolated verifier: tick range, sequence, record/event agreement, floor continuity, recorded load, boarded and alighted sets, heading and boarder sets under the route law, travel distance |
| `STATE_HISTORY_MISMATCH` | the snapshot and the History prefix disagree: floors or headings do not continue from the last TickRecord; a passenger field has no matching event or an event has no matching field |

Any refusal leaves the fresh process with no Run. Nothing is partially
loaded.

## 6. Authority sweep: every carrier of runtime or continuity state

Enumerated so that no hidden carrier exists. "Denied rights" names what the
carrier may never do, so that a reader can test a proposed use against it.
The engine's own denied rights are in the constitution §3 and §9; authority
is not immunity.

| Carrier | Holds | Class | Bound to | Denied rights |
| --- | --- | --- | --- | --- |
| engine in-memory state (one object graph) | rows 9 to 15, 17, 18 | `AUTHORITATIVE` while the process lives; its durable twin is the Continuation Document when one exists | `run_id` | may not survive the process; may not reassign, read future Requests for a decision, continue a final Run, alter an emitted record, skip a tick, move more than one floor, or board against the departure direction |
| Continuation Document in a Store | rows 1, 2, 4 to 7, 9 to 15, 17a, 18, 37 | `AUTHORITATIVE` carrier for continuation and durable Execution standing | `(store_id, execution_id, t)`, `write_sequence`, hashes | cannot be loaded by a file path, into another Store, by other code, under another `execution_id`, or once final; cannot be partially loaded; cannot be repaired on load; cannot be replaced by a stale or post-final writer; its History section cannot construct present state |
| Operational Log buffer (in memory, before the Execution's evidence root exists) | row 26 | `EPHEMERAL` | `execution_id`, `op_seq` | never establishes anything; lost with the process; not CPOC evidence |
| `operational.jsonl` (at the Execution's evidence root: the Store directory, else the output location) | row 26 | `RECEIPT`, append-only | `execution_id`, `op_seq` | never establishes or admits anything; never embedded in the document; never hashed into any identity; written once per record |
| temp files beside the document (`run.json.tmp`) | bytes in flight | `EPHEMERAL` | the write | never loaded; never a selector; ignored and removed by the next admitted write |
| `store.json` | row 7 | `AUTHORITATIVE` for the Store's identity | the directory | cannot be copied to make a second Store with the same id (the loader does not care; a copied document in a fresh Store with a fresh id is refused by `STORE_MISMATCH`) |
| `events.jsonl`, `tick_records.jsonl` output files | Simulation History serialised | `DERIVED` serialisation (byte-identical content to the in-memory History; used for comparison witnesses) | `run_id` | never read to establish state, finality, or to continue a Run |
| `elevator_positions.csv`, `position_log_long.csv`, `passengers.csv`, `summary.json`, `observations.md`, `run_identity.json` (the Reproducible Output Surface) | projections | `DERIVED` | `run_id` | never read back by the engine, the loader or the harness to establish any fact; `run_identity.json`'s standing field is a report, never a selector; contains no execution fact |
| `execution_metadata.json` | row 40 | `RECEIPT` | `execution_id` | outside every equality claim; never consulted by the loader |
| history verifier | row 38 | `EPHEMERAL`, distinct type | one Load | never becomes engine state; never passed to `construct_state` |
| `experiment_results.json` | rows 32 to 34 (the result surface) | `AUTHORITATIVE` for the definition it embeds; `DERIVED` for ids and results | definition hash, experiment execution id, every `run_id` | cannot alter a Run; results are evidence, not inputs; contains no per-Run `execution_id`, path or timestamp |
| `experiment_execution.json` | row 34 (execution metadata) | `RECEIPT` | experiment execution id, per-Run `execution_id`s | outside every equality claim; never read by the harness's comparison |
| `provenance` block in `execution_metadata.json` | scenario pattern, parameters, seed that generated the Trace | `DERIVED` label; informational | `execution_id` | not part of `run_id` or the surface; never in the Continuation Document; never used to load an Execution; the harness re-derives the Trace from it only to detect a mismatch |
| scheduler view and projections | a read-only snapshot for one call | `EPHEMERAL` | the exact state at `(t, passenger_id)` | cannot be mutated, retained, or written anywhere but as the `ASSIGNED` receipt |
| `departure_E` | row 16 | `EPHEMERAL` (intra-tick) | `(t, elevator_id)` | never stored, checkpointed, displayed or read by a policy; `FREE` is not a heading value |
| process arguments and UI form values (checkpoint controls, output directory, store path) | rows 27, 28 | `EPHEMERAL` execution parameters | one execution | never a Configuration field; never in `run_id`; never a selector of finality or Run |
| UI session dict | which Execution's engine a session points at, interval, play state | `EPHEMERAL` | session id = `execution_id` | decides no simulation fact; lost on server death and recreated from a Store and `execution_id` |
| rendered HTML fragments; browser form inputs; play timer | a view; interaction state | `EPHEMERAL` | the `t` it was rendered at (as a guard) | cannot select, establish or reconcile any fact; a `from_time` is checked by the server and never trusted |
| test fixtures | input Traces and expected outputs | inputs are `AUTHORITATIVE` for the test's Trace; expected outputs are evidence | fixture hash | an expected output that disagrees with a governing document is a wrong fixture, never a rule |

No database, environment variable, module-level global, class attribute,
thread-local, browser storage, cookie or query parameter may carry a
runtime fact. A `from_time` parameter on a UI step request is a guard the
server checks against row 9, never a selector of it
([ui_design.md](ui_design.md) §6).

## 7. Constitutional Delta of this document

Founding assignment of authority (`ΔA` as stated). Revision 7 changes
only the carrier lifecycle of row 26 and the split of row 34; no owner or
writer changes. Revision 6 adds rows
17a and 37 to 41, splits Run outcome from Execution standing, moves the
Operational Log out of the document into its own file per Execution, binds
the Continuation Document to `(store_id, execution_id)`, and names the
Reproducible Output Surface. Revision 5 added rows 3 to 7, 10, 16, 17, 22
to 29 and 31 to 33, reclassed row 8's visibility condition, and moved
finality's durable carrier from "a result file in an output directory" to
the Continuation Document in a Store. No implementation authority is
granted.
