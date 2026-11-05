# Architecture

Status: **DESCRIPTIVE. Revision 7.3 (owner decision 009: policy construction edges, 2026-11-05). Admission standing is recorded in `docs/decisions/`, not here. Decides no semantic question; maps the governing documents to components.**

Nothing in this document is implemented. It describes the intended
separation so that it can be challenged before code exists. Where it
restates a rule, the owning document controls.

## 1. Components and their authority

```text
   public boundaries (api):  normalize_requests(rows) -> Trace        (shared input boundary)
                             simulate(rows, N, F, C, policy) -> result  (batch: run to the outcome)
                             create_engine(rows, N, F, C, policy) -> RUNNING engine at t=0 (live)
                            |  (Trace load: validation, source ids, domain bounds, hashes, run_id)
                            v
                 +------------------------------------------------+
   inputs        |            simulation engine                   |   Simulation History (RECEIPT)
   Config  ----> |  owns: t, passengers, elevators (floor,heading)|----> simulation events, tick records
   Trace   ----> |  run standing; tick procedure = commit boundary|
                 |  reveals requests one tick at a time           |----> Execution: Continuation Document
                 +----------+--------------------+----------------+      <store>/<execution_id>/run.json
                            | SchedulerView      ^ Proposal              (snapshot + history prefix,
                            |                    |                        write_sequence; finality)
                            |                    |                       + operational.jsonl (receipts)
                            v                    |
                 +------------------------------------------------+
                 |  scheduler policy (pure)                       |
                 |  round_robin | nearest_car | cost_based        |
                 |  may call: route.project (pure)                |
                 +------------------------------------------------+

                 +------------------------------------------------+
                 |  route policy (pure, one implementation)       |
                 |  departure_direction(floor, heading, S_other)  |
                 |  eligible_boarders(waiting, D, load, C)        |
                 |  next_heading(floor, heading, stops) = LOOK    |
                 |  project(...) = the three above, iterated      |
                 +------------------------------------------------+
                      called by the engine (steps 4, 5) and by project

   loader: load(store, execution_id) -> eleven verifications (HistoryVerifier, discarded)
           -> parse_snapshot -> construct_state(Snapshot) -> LOAD_ADMITTED
   operational log: in-memory buffer until the Execution's evidence root (Store, else output location)
           exists, then a separate append-only file there; execution started/ended, checkpoint written,
           load admitted, resumed, finality written, code identity drift, diagnostic

   outputs (DERIVED) <---- reporting: Reproducible Output Surface (elevator_positions, position_log_long,
                                  ^   passengers, summary, observations, run_identity, history files)
                                  |   + execution_metadata.json (evidence, outside equality)
   evaluation harness ------------+   scenarios (SplitMix64 generator), experiments, paired comparison
                                  |
   web UI (FastAPI/Jinja2/HTMX) --+   projections of an in-process engine; browser owns nothing
```

| Component | Authority | Depends on | Must not depend on |
| --- | --- | --- | --- |
| `domain` (values: Configuration, Request with `source_id`, Trace, Passenger, Elevator, Simulation Event, TickRecord, Operational Record, Continuation Document; validation; canonical serialisation; code identity) | none; immutable value types and validation | stdlib | anything else |
| `operations` (operational Execution handle, `execution_id`, OperationalLog, `op_seq`, `append`, `bind_evidence_root`, `flush_unflushed_prefix`) | none; implements the executing process's existing identity/log boundaries | `domain`, stdlib | engine, route, policies, checkpoint, reporting, API, web; no simulation state, Store authority or continuation semantics |
| `route` (`departure_direction`, `eligible_boarders`, `next_heading`, `project`) | none; pure; the single implementation of the Route Policy | `domain` | engine, policies, I/O |
| `engine` (tick procedure, request visibility, Run outcome, Simulation History; `create` at `t = 0`) | **all runtime state** | `domain`, `route`, the policy interface; `operations` only for the optional diagnostic hook (cut 9) | policies' internals, harness, UI, web frameworks, checkpoint I/O |
| `checkpoint` (Store creation, Store binding of an existing Execution via `operations`, Continuation Document write and finality write under write admission, `load` with the eleven verifications, the `Snapshot`, `HistoryPrefix` and `HistoryVerifier` types, `parse_snapshot`, `parse_history`, `construct_state(Snapshot)`) | none; a writer and a loader for the engine's state | `domain`, `engine` (to construct and to read state), `route` (for the verifier), `operations` (the same Execution log), `policies` (`make_policy` only, to construct the policy a Configuration names when an Execution is resumed) | reporting, web |
| `api` (`normalize_requests`, `simulate`, `create_engine`) | none; thin boundaries over Trace load, engine and reporting | `domain`, `engine`, `reporting`, `operations`, `policies` (`make_policy` only) | checkpoint, web |
| `policies` (three implementations of the interface, and `make_policy`, the one resolver from a policy name and the Configuration's parameters to a policy object) | none; pure | `domain`, `route` | engine internals, Trace, I/O |
| `reporting` (position exports, passenger table, summary with the pinned numeric rendering, observations, calibration) | none; derived outputs; invokes output-only log binding without acquiring log authority | `domain`; `operations` for the execution-output wrapper added in cut 8 | engine internals (reads the Simulation History and records only), checkpoint |
| `scenarios` (SplitMix64 primitive, patterns, `generate`) | Scenario definitions | `domain` | engine, `random` |
| `harness` (experiments, paired comparison) | Experiment definitions and results | engine (as a black box), `scenarios`, `reporting`, `policies` (`make_policy` only) | UI |
| `cli` (`store init`, `simulate`, `resume`, `experiment`) | none | all of the above | web |
| `web` (FastAPI app, Jinja2 templates, HTMX fragments) | UI sessions (`EPHEMERAL`) | `api` (`create_engine`, `normalize_requests`), engine (step), reporting, harness, checkpoint (explicit checkpoint and reopen only), `policies` (`make_policy` only) | nothing of the above may import it; it never calls `simulate` to create a session |

The dependencies in the table are acyclic: `operations` depends only on
`domain` and the standard library; API, reporting and checkpoint may call
it, and it imports none of them. The simulation package never imports
FastAPI, Jinja2, HTMX helpers or anything browser-related. Only checkpoint
interprets or writes `store.json` and Continuation Documents, and decides
the Store location supplied to operations; operations only reads/appends
the Operational Log at the supplied evidence root. It cannot admit a
Store or a continuation. `construct_state(Snapshot)` is the only function that
produces engine state from a document; `Snapshot` is produced only by
`parse_snapshot`; no function in either package produces a `Snapshot` or
engine state from History ([cpoc_design.md](cpoc_design.md) §5.1). The
architecture tests of [testing_contract.md](testing_contract.md) §7 scan
both packages for violations; this is the bounded assurance standard, not
an attestation of runtime behaviour.

### 1.1 Neutral operational component (revision 7.1)

`operations.py` implements only the existing process-owned Execution
identity and log lifecycle: `execution_id`, OperationalLog, `op_seq`,
`append()`, `bind_evidence_root()` and `flush_unflushed_prefix()`.
Its Execution handle holds operational identity and the log, not the
engine graph, Passenger fields, Run outcome, Store identity authority,
write-admission token or durable Execution standing. Those retain their
existing owners and carriers. This is a component mapping, not a new
canonical object, owner, lifecycle or persistence rule.

- API creates the Execution handle and its ephemeral log, appending
  EXECUTION_STARTED, for both `simulate` and `create_engine`.
- Reporting's execution-output wrapper may bind an output-only batch's
  same log to the caller's output root; metric functions never read it.
- Checkpoint selects the lawful Store location and binds that same log
  there using operations. On resume it reuses the admitted execution_id
  and opens the existing log through operations, continuing op_seq and
  recording the new process's EXECUTION_STARTED before LOAD_ADMITTED and
  RESUMED. No new execution_id is minted for a resume.
- Checkpoint performs document admission/write/load and supplies the
  resulting receipt payload to operations.append. Operations never
  interprets a snapshot, selects standing, hashes a document on its own,
  or makes a Store/admission decision.
- The optional engine diagnostic hook uses this same operational handle;
  it is excluded from simulation state, SchedulerView and snapshots.

Evidence-root selection, first flush, output-copy behavior and never-bound
execution semantics remain cpoc §2.2a and §3.2. API still does not depend on
checkpoint. Neither API nor checkpoint nor operations becomes the owner
of the log: the executing process remains its owner (authority row 26).
Constitutional Delta for this relocation: `NONE / NONE / NONE`.

### 1.2 Policy construction (revision 7.3)

The public functions take a policy **name** (evaluation §2) and an Experiment lists policy names
(evaluation §7.1), so something must turn a name and the Configuration's parameters into a policy
object. That is `policies.make_policy`, the "dict of three names" of §7: one function, no registry,
plugin, hook, dynamic import or mutable global, supporting exactly `round_robin`, `nearest_car` and
`cost_based`, refusing any other name deterministically. The edges to `policies` that this revision adds
for `api`, `harness`, `checkpoint` and `web` permit **policy construction only**, through that one
function: every component that resolves a name uses it, and none keeps a second table. The edges
transfer no engine authority, no assignment authority, no runtime state and no scheduler state. A policy
remains a pure proposal producer and the engine remains the only authority that validates and commits an
assignment. Constitutional Delta for this clarification: `NONE / NONE / NONE`.

## 2. Data flow of one tick

1. The engine reveals Requests with `request_time == t` from the Trace it
   holds (nothing else holds it).
2. For each, it builds a `SchedulerView` (a frozen value with no back
   reference), calls the policy, validates, commits, emits `ASSIGNED` with
   the policy's receipt.
3. It alights; for each car calls `route.departure_direction` then
   `route.eligible_boarders` and boards the returned passengers; sets
   headings (the promised departure, else `route.next_heading`); emits the
   TickRecord; checks termination; moves; advances.
4. If a checkpoint is due, the checkpoint module reads the existing
   document for write admission, writes the new document atomically,
   hashes the bytes at the path, and appends `CHECKPOINT_WRITTEN` to the
   Execution's Operational Log. At the Run outcome, if a document exists,
   it performs the finality write the same way.

The policy never sees step 3; the UI never sees anything but the History and
derived projections after the tick; the harness never sees inside a tick.

## 3. Persistence

A Store (`store.json` with a `store_id` and schema version) holding, per
Execution, one Continuation Document at `<store>/<execution_id>/run.json`
(replaced atomically under write admission) and one append-only
`operational.jsonl`; run outputs as files under
`<output_dir>/<run_id>/<execution_id>/`, never read back. No database, no
ORM, no cache layer, no message broker ([cpoc_design.md](cpoc_design.md)
§9). The loader is addressed by `(store, execution_id)`, never by a file
path.

## 4. Determinism machinery

- Ids are integers; all iteration is in ascending id order over lists, never
  over sets or dict insertion order that depends on construction history.
- Costs are `int`; the generator is the SplitMix64 integer primitive of
  [evaluation_design.md](evaluation_design.md) §6.1; reporting uses
  integers and exact rationals with the pinned rendering of evaluation §4.2.
- Code identity is the SHA-256 over the sorted sequence of (relative path,
  file bytes) of every `.py` file in the simulation package (`elevator/`),
  computed by the running process before any Run begins from its own
  installed package. It changes with any byte of the package, committed or
  not. The Git SHA and worktree standing (clean or dirty) are recorded in
  `execution_metadata.json` as provenance and never participate in any
  identity or check.
- Supported execution contract (constitution §12): governed entry points
  (`cli`, `web.app`, the witness subprocesses) require
  `sys.flags.dont_write_bytecode` to be set (`python -B` or
  `PYTHONDONTWRITEBYTECODE=1`), refuse to start a governed Run if a
  `__pycache__` directory exists inside `elevator/`
  (`UNSUPPORTED_EXECUTION_ENVIRONMENT`), compute code identity before the
  Run, and re-hash at exit (`CODE_IDENTITY_DRIFT` if changed). The
  project does not attempt to attest against malicious replacement of
  executing instructions after process start. No bytecode hashes, signed
  packages, container attestation or hermetic builds are introduced.
- `execution_id` is minted with the standard library's UUID version 4
  (128 random bits) at Execution creation; it is operational identity and
  never scheduler randomness.
- Canonical serialisation: JSON with sorted keys, no whitespace variance,
  integers only for all simulation quantities; CSV with a fixed column
  order. These are the bytes equality witnesses compare.

## 5. Web UI

Thin, server-rendered ([ui_design.md](ui_design.md)); an owner-directed
enhancement, not a take-home requirement. The FastAPI process holds engines
for open sessions in memory and is configured with one Store path; every
HTMX request returns a fragment rendered from engine state or History. "Play" is a client timer
that issues step requests; the server executes ticks. No WebSockets: a
one-second polling cadence over HTMX is sufficient for a take-home
animation, and the alternative would add a persistent connection whose only
purpose is latency.

## 6. Dependencies (complete list)

Runtime: Python 3.12 standard library for the simulation package. Web:
`fastapi`, `uvicorn`, `jinja2`, `python-multipart` (form posts), HTMX served
as a vendored static file. Tests: `pytest`, `hypothesis` (property tests).
Nothing else. Charting is server-rendered inline SVG from Jinja2, so no
charting library.

## 7. What is deliberately absent

- event sourcing as the state model: the Checkpoint is a snapshot plus the
  History prefix; History is a receipt log, not the thing state is rebuilt
  from ([assumptions_and_tradeoffs.md](assumptions_and_tradeoffs.md) §3);
- a plugin or registry framework for policies: a dict of three names;
- an abstract persistence layer: one function writes, one function loads;
- concurrency inside a Run;
- any component the scope control in [AGENTS.md](../AGENTS.md) names.

## 8. Expected package layout (for the plan; not to be created now)

```text
elevator/
  domain.py   route.py   engine.py   policies.py   reporting.py
  scenarios.py   harness.py   operations.py   checkpoint.py   api.py   cli.py
web/
  app.py   templates/   static/htmx.min.js
tests/
  unit/   invariants/   comparative/   property/   reproducibility/   cpoc/   web/
```

The flat package has eleven modules. `operations.py` arrives in cut 8,
with the API and reporting's execution-output wrapper; it stays there
when cut 9 adds Store integration. `cli` offers `simulate`
and `experiment` from cut 8; `store init` and `resume` arrive with the
checkpoint module in cut 9, as do the continuation types (`Snapshot`,
`HistoryPrefix`, `HistoryVerifier`), which belong to `checkpoint`, not
`domain`. Until cut 9 exists, an Execution's Operational Log is the
in-memory buffer flushed only to an output location. No operations code
is relocated into checkpoint in cut 9.
