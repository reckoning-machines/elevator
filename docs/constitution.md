# Elevator Simulation Constitution

Status: **GOVERNING DOCUMENT. DRAFT, NOT ADMITTED. Revision 7.1 (bounded component-mapping and reference repairs, 2026-11-05).**

This document says what the system is, what its objects are, which facts are
consequential, who owns them, which transitions are lawful, what may never
happen, what is historical and what is mutable, what a committed assignment
and a completed passenger are, what makes a run reproducible, what lawful
continuation after process death means, and what would constitute corruption.
It is the highest governing document in this repository. The ownership
detail per fact is in [authority_model.md](authority_model.md); the exact
tick mechanics are in [simulation_semantics.md](simulation_semantics.md).
Where this document states a rule and another document restates it, this
document controls.

The engineering doctrine behind the words "owner", "commit boundary",
"representation class", "OSA" and "CPOC" was adopted from the sibling
repository `fin123-core`; what was adopted and what was not is recorded in
[doctrine_adoption.md](doctrine_adoption.md). The doctrine is summarised here
only as far as this project needs it.

## 1. What the system is

A **Simulation** is one deterministic execution of a discrete-time
destination-dispatch elevator world: a building of `F` floors numbered
`0..F-1`, `N` elevators numbered `0..N-1`, each with capacity `C`, driven by a
finite, fixed **Trace** of passenger requests, under one **Scheduler Policy**,
one fixed **Route Policy**, and one **Configuration**. Time is an integer
`t >= 0`. One tick is one time unit. An elevator moves at most one floor per
tick.

The system's purpose is to answer, for every passenger request, the decision:

> Which elevator should receive this passenger request, given only the
> information lawfully available at this time?

and to measure the consequences of different ways of answering it.

## 2. Canonical objects

| Object | Identity | Meaning |
| --- | --- | --- |
| Configuration | content hash | `F` floors, `N` elevators, capacity `C`, initial floor per elevator, `max_ticks` (the liveness horizon, §5 P10), scheduler policy name and parameters. Immutable for a run. |
| Request | `source_id` (supplied by the input) and `input_index` (position in the input) | A passenger's `(source_id, request_time, origin, destination)` with `origin != destination`, both in `0..F-1`, `request_time >= 0`, `source_id` a non-empty string unique within the Trace. Immutable. |
| Trace | content hash of its canonical form | The ordered, finite list of all Requests for a run, sorted stably by `(request_time, input_index)`. Immutable. Known to the engine in full; revealed to policies one tick at a time. |
| Passenger | `passenger_id`, the Request's position in the sorted Trace, numbered from 0; the Request's `source_id` is carried with it and is the public name of the Passenger | The lifecycle record of one Request: standing, assigned elevator, assignment time, pickup time, dropoff time. |
| Elevator | `elevator_id` in `0..N-1` | A car with a current floor and a heading. Everything else about it (load, onboard set, waiting set, departure direction, route) is derived from Passengers and the current floor and heading. |
| Assignment | the pair `(passenger_id, elevator_id)` written once | The committed fact that a Passenger will be served by exactly one Elevator. |
| Tick | `t` | One application of the tick procedure of [simulation_semantics.md](simulation_semantics.md) §2. |
| TickRecord | `t` | The immutable record, emitted at tick `t`'s observation step, of every elevator's floor, heading and load at tick `t` and the boardings and alightings that occurred at `t`. |
| Simulation Event | sequence number within the Simulation History | An immutable record of one passenger transition (`REVEALED`, `ASSIGNED`, `BOARDED`, `ALIGHTED`) or one run-standing transition (`COMPLETED`, `HALTED`), with the tick and the facts the transition established. Every Simulation Event's existence and content is determined by the Configuration, the Trace, the policy, the Route Policy and the tick procedure alone. |
| Simulation History | `run_id` | The ordered set of all Simulation Events and TickRecords of a run from `t = 0`. It contains nothing about processes, files, checkpoints or loads. |
| Execution | `execution_id`, a random 128-bit identifier (UUID version 4 or equivalent) minted when the Execution is created by the process that will run it | One attempt to carry a Run forward in one or more processes: the in-memory engine, its durable continuation state if any, its Execution standing, its Operational Log, and its output location. A Run may have any number of Executions, in one Store or many, concurrently or in sequence; each is lawful and each produces the same Simulation History. The `execution_id` is operational identity only; it never enters a decision, the Simulation History or `run_id`. |
| Operational Record | `(execution_id, op_seq)`, `op_seq` a monotone sequence within one Execution's log | An immutable record of one execution fact: `EXECUTION_STARTED`, `CHECKPOINT_WRITTEN`, `LOAD_ADMITTED`, `RESUMED`, `FINALITY_WRITTEN`, `EXECUTION_ENDED`, `CODE_IDENTITY_DRIFT`, or a `DIAGNOSTIC` record used by the witness, with the tick, the document's SHA-256 where applicable, process identity and code identity. |
| Operational Log | `execution_id` | One Execution's ordered Operational Records: an in-memory buffer from Execution creation until the Execution's evidence root (its Store directory, else its output location) exists, then an append-only file there, flushed once in order ([cpoc_design.md](cpoc_design.md) §2.2a). It is evidence about execution. It never influences the Simulation History, any decision, any metric, or `run_id`, and it never establishes simulation state. An Execution that never obtains an evidence root keeps it in memory only and cannot be cited as durable CPOC evidence. |
| Store | `store_id`, a random 128-bit identifier minted when the Store is created and recorded in its `store.json` together with the Store schema version | A directory that holds, per Execution, a Continuation Document and an Operational Log at `<store>/<execution_id>/`. Output directories are not Stores. |
| Continuation Document | `(store_id, execution_id)`; it also records `run_id` | The single durable document of one Execution. While the Execution is `RUNNING` it carries the snapshot at a tick boundary (the Checkpoint) and the Simulation History prefix; once the Execution is final it carries the final standing, final tick, halt reason, and the complete Simulation History. It is the only durable carrier of Execution standing. It carries a monotone `write_sequence` that admits or refuses writers (§4.3). |
| Checkpoint | `(store_id, execution_id, t)` | The snapshot section of a `RUNNING` Continuation Document: everything required to continue the Execution lawfully from the start of tick `t`. |
| Run | `run_id` = hash of (Configuration hash, Trace hash, code identity); the policy name and parameters are inside the Configuration | The logical Run: one deterministic Simulation. Every Execution of the same `run_id` produces the identical Simulation History and the identical Reproducible Output Surface. `run_id` identifies semantics; it does not identify any one durable execution standing. |
| Reproducible Output Surface | `run_id` | The set of derived outputs that every Execution of a Run must produce byte-identically: the Simulation History serialisations, the passenger table, both position exports, the canonical summary, the observations and `run_identity.json`. Execution metadata and the Operational Log are outside it ([evaluation_design.md](evaluation_design.md) §3). |
| Code identity | content hash of the governed simulation package's source bytes (every `.py` file of the package, by relative path), which includes the schema version constants | The identity of the code that ran, under the supported execution contract of §12. It is computed by the running process from its own package before any Run begins and is never supplied by a caller, a Git ref or a flag. A Git commit SHA may be recorded beside it as provenance; it never substitutes for it. |
| Scenario | `(pattern, parameters, seed)` | A reproducible recipe that generates a Trace by the exact algorithms of [evaluation_design.md](evaluation_design.md) §2. Not a runtime object. |
| Experiment | definition hash; experiment execution id = hash of (definition hash, code identity) | A set of Scenarios, seeds and policies, and the Runs and comparisons an execution of it produced. Each Run inside it is an Execution with its own `execution_id`. Its results are split into a Reproducible Experiment Result Surface (byte-identical per definition and code identity) and execution metadata ([evaluation_design.md](evaluation_design.md) §7.4). Not a runtime object. |

There are no other canonical objects. Routes, stop sets, loads, departure
directions, estimates, statistics, position exports, projections, the
history verifier's working state and UI views are derived or ephemeral
representations, named in [authority_model.md](authority_model.md).

## 3. Consequential facts and their owners

A fact is consequential when its value changes what the simulation does, what
a policy decides, what is recorded as history, what is reported as a result,
or whether a continuation is lawful. The complete table, with representation
classes, writers, readers, persistence and reconstruction, is
[authority_model.md](authority_model.md). The ownership principle:

- **The simulation engine owns all runtime simulation state**: current time,
  request visibility, every Passenger field, every Elevator's floor and
  heading, the Run outcome, and the Simulation History. It is the only
  writer of all of them, through the tick procedure, which is the single
  governed commit boundary for runtime state. Engine authority does not
  mean the engine has no denied rights: it is bound by every rule in §6 and
  may not reassign, read the future on a policy's behalf, continue a final
  Run, alter history, skip a tick or move more than one floor.
- **The Configuration and the Trace are owned by their input carriers**
  (file, function argument or scenario generator output), immutable once a
  Run starts, and bound into the Run by hash.
- **A Scheduler Policy owns nothing.** It is a pure function from a read-only
  view of lawful state plus one newly revealed Request to one proposed
  elevator id. The engine validates and commits. Any state a policy would
  need across ticks must be declared, is owned by the engine, and is part of
  the Checkpoint; the three policies in scope declare none.
- **The Route Policy owns nothing.** It is a set of pure functions
  (`departure_direction`, `eligible_boarders`, `next_heading`) from one
  elevator's floor, heading, committed stops and waiting passengers to the
  departure direction, the boarders and the next heading. The engine applies
  them in steps 4 and 5. The same functions, iterated by `project`, are the
  route projection the scheduler may use. There is one implementation of
  each; the engine and the projection call the same function objects.
- **The evaluation harness owns Scenarios and Experiments** and nothing
  inside a Run.
- **The executing process owns its Execution**: it mints `execution_id`,
  writes the Execution's Continuation Document and Operational Log, and
  computes its own code identity. Execution standing's durable carrier is
  the Continuation Document in a Store. Output directories hold derived
  files and own nothing.
- **The loader owns nothing.** It admits or refuses a Continuation Document
  by `(store, execution_id)`, verifies the History with an isolated
  verifier whose state is discarded, and constructs the engine's state from
  the typed snapshot only.
- **The UI server owns interaction sessions** (which Run is open in which
  session). The **browser owns nothing consequential**: form inputs and the
  last rendered fragment only.

## 4. Lifecycle and lawful transitions

### 4.1 Passenger standing

```text
UNREVEALED --(reveal at t = request_time)--> [revealed, unassigned: transient within the tick]
           --(assignment committed at t = request_time)--> WAITING
WAITING    --(board at t at origin, assigned elevator present, room available,
               departure direction compatible)--> ONBOARD
ONBOARD    --(alight at t at destination)--> COMPLETED
```

- Reveal and assignment happen in the same tick; no Passenger is ever
  `WAITING` without an assigned elevator, and the transient revealed-but-
  unassigned condition is never persisted or observable to any policy or
  projection.
- Every transition is written exactly once and recorded as a Simulation
  Event in the same tick commit.
- `WAITING` may persist across many ticks, including ticks in which the
  assigned elevator is at the origin floor but full (capacity deferral) or
  departing the other way (direction deferral), both lawful conditions
  defined in [simulation_semantics.md](simulation_semantics.md) §5.
- There is no `REJECTED`, `REASSIGNED` or `CANCELLED` standing. A Request that
  is invalid (same origin and destination, floor out of range, negative
  time, missing or duplicate `source_id`) is refused when the Trace is
  loaded; the Run does not start.

### 4.2 Elevator state

An Elevator has exactly two authoritative fields: `floor` in `0..F-1` and
`heading` in `{UP, DOWN, NONE}`. `heading` changes only in the tick
procedure's heading step (step 5); `floor` changes only in its motion step
(step 8). `heading = NONE` means idle: no committed stops. The departure
direction established in step 4 is an intra-tick ephemeral value that
decides step 5's heading; it is never stored and never survives the tick.

### 4.3 Run outcome and Execution standing

Two distinct facts:

- the **Run outcome**, decided by the engine in memory at tick `t` (step 7,
  or the step that detects a halt): `COMPLETED` with final tick, or
  `HALTED` with final tick, step and reason. It is a simulation fact,
  recorded as a run-standing Simulation Event, identical for every
  Execution of the Run;
- the **Execution standing**, `RUNNING`, `COMPLETED` or `HALTED`, the
  durable standing of one Execution, carried by its Continuation Document
  when one exists.

```text
Execution:  CREATED --(start)--> RUNNING --(finality write after the Run outcome)--> COMPLETED | HALTED
            RUNNING --(checkpoint write)--> RUNNING
            Continuation Document (RUNNING) --(fresh process, load admitted)--> RUNNING at the checkpointed tick
```

**Write admission.** Every write of an Execution's Continuation Document
is admitted against the document that currently exists at
`<store>/<execution_id>/run.json`:

- a checkpoint write is admitted only if no document exists (the first
  write of this Execution) or the existing document's standing is
  `RUNNING` and its `write_sequence` equals the writer's last-known
  `write_sequence`; the new document carries `write_sequence + 1`;
- a finality write is admitted under the same conditions and sets the
  standing to `COMPLETED` or `HALTED`, removes the snapshot, and carries
  the complete Simulation History;
- after a final standing no write is admitted: a writer that finds a final
  document refuses `WRITE_AFTER_FINAL` and halts itself; a writer whose
  last-known `write_sequence` is behind the document's refuses
  `STALE_WRITER` and halts itself. Both fail closed; neither rewrites.

Atomic replace (temp file, fsync, rename) guarantees that the document at
the path is never torn; write admission guarantees that no stale or
superseded writer replaces the Execution's authority. Transient completion
(the Run outcome decided in memory) and durable finality (the finality
write) are different moments: a process that dies between them leaves a
`RUNNING` document whose snapshot is the last checkpoint, and a continuation
re-executes from that snapshot and reaches the same outcome.

A final Execution is final. It cannot be resumed, reopened or extended. An
Execution that never wrote a Continuation Document has no durable standing
and no continuation question arises. Derived outputs (`run_identity.json`,
`execution_metadata.json`) may report standing; they never establish it. A
`HALTED` Run has no statistics; it has a reason and a Simulation History
consisting of every completed tick plus one `HALTED` event recording the
tick, the step and the reason. Events of the tick in which the halt
occurred are discarded with that tick (§4.4).

### 4.4 The tick as the commit boundary

The tick procedure (exact order in [simulation_semantics.md](simulation_semantics.md) §2)
is atomic with respect to durable state: a Checkpoint is written only at a
tick boundary, and a process that dies mid-tick loses that tick entirely. On
reconstruction the tick is executed again from the Checkpoint and, because
the procedure is deterministic, produces the same result. No partial tick is
ever durable. A process that dies between checkpoints loses every tick after
the last Checkpoint; continuation re-executes them and produces the same
Simulation History.

### 4.5 Transition classes

Every change to a governed fact belongs to exactly one class below. The
table says what the class mutates, who proposes it, who validates it, who
decides it, and its constitutional budget. "Engine" means the tick
procedure; "process" means the operating-system process executing an
Execution; "owner" means the person who commissioned the project.

| Class | Mutates | Proposer | Validation | Decider | Budget |
| --- | --- | --- | --- | --- | --- |
| Code identity establishment | the process's code identity (read-only establishment of a fact about the process) | the process, before any Run begins | the supported execution contract (§12): bytecode writing disabled, no bytecode cache inside the governed package, every `.py` file hashed; otherwise `UNSUPPORTED_EXECUTION_ENVIRONMENT` | the process | `0/0/0` |
| Store creation | `store.json`: `store_id`, store schema version | CLI, harness, UI server, explicitly | the directory does not already hold a Store; a fresh random `store_id` | the Store creation boundary | `0/0/0` |
| Trace load | Configuration and the normalized Trace enter a Run; `run_id` minted | CLI, the public `simulate` and `create_engine` boundaries, harness, UI server, loader (embedded copy) | structural validity (§2) including `source_id` presence and uniqueness, bounds of [evaluation_design.md](evaluation_design.md) §2; hashes | the load boundary (refuses or admits) | `0/0/0` |
| Execution creation | `execution_id` minted; the Execution bound to a Store when checkpoint controls are set; the Operational Log buffer opened and `EXECUTION_STARTED` appended as `op_seq` 1 | the process, after Trace load | a fresh random id; the Store, if any, exists and its schema version matches | the process | `0/0/0` |
| Reveal | Passenger existence at `request_time` | engine, step 1 | `request_time == t` | engine | `0/0/0` |
| Assign | `assigned_elevator`, `assigned_at`; standing `WAITING`; `ASSIGNED` event | a Scheduler Policy proposes one elevator id | engine: id in range, passenger newly revealed and unassigned | engine commits or halts; never substitutes | `0/0/0` |
| Board | `pickup_time`; standing `ONBOARD`; `BOARDED` event | engine, step 4, via `eligible_boarders` | assigned elevator at origin; departure direction compatible; `load < C`; id order | engine | `0/0/0` |
| Alight | `dropoff_time`; standing `COMPLETED`; `ALIGHTED` event | engine, step 3 | onboard the assigned elevator at destination | engine | `0/0/0` |
| Head | `heading` | the Route Policy functions | the departure direction established in step 4, else `next_heading` | engine applies, step 5 | `0/0/0` |
| Record | one TickRecord | engine, step 6 | one per tick per elevator | engine | `0/0/0` |
| Move | `floor` | engine, step 8 | at most one floor, in range | engine | `0/0/0` |
| Terminate or halt | the Run outcome in memory; the run-standing Simulation Event | engine, step 7 or any step that detects corruption or an invalid proposal | the termination condition (§4.3) or a named reason | engine | `0/0/0` |
| Checkpoint write | the Execution's Continuation Document (snapshot, Simulation History prefix, `write_sequence`) | the process, at a tick boundary, on request | write admission (§4.3); atomic replace; contents per [cpoc_design.md](cpoc_design.md) §3 | the process | `0/0/0` |
| Finality write | the Execution's Continuation Document standing to final, with the complete Simulation History | the process, after the Run outcome, only if a document exists | write admission (§4.3); the document was `RUNNING` | the process | `0/0/0` |
| Operational Log append | one Operational Record in the Execution's log (buffer or file); at the first existence of the evidence root, the flush of the unflushed prefix | the process that performed the execution fact | `execution_id` equals the log's; `op_seq` is the next integer; the document SHA-256, where present, is of the bytes now at the path; a flush writes each record once, in order | the process | `0/0/0` |
| Load | a Run in a fresh process; `LOAD_ADMITTED` and `RESUMED` records | the loader, on request, by `(store, execution_id)` | the verifications of [cpoc_design.md](cpoc_design.md) §5; refuses on the first failure; constructs state from the typed snapshot only | the loader | `0/0/0` |
| Scenario generation | a Trace from `(pattern, parameters, seed)` | harness | pattern parameters within their domains; emitted Trace valid | harness | `0/0/0` |
| Experiment execution | the experiment execution id = hash(definition hash, code identity); the results file | harness | every policy sees the same Trace hash per `(scenario, seed)`; aggregation per [evaluation_design.md](evaluation_design.md) §7.4 | harness | `0/0/0` |
| UI session open, step, checkpoint, reopen | the session's pointer; delegates to the classes above | a browser request | `from_time` guard; Execution standing; historical range | the UI server, by delegating; it decides no simulation fact | `0/0/0` |
| Document amendment | a governing document | anyone, in a proposed revision | the audit motion of [AGENTS.md](../AGENTS.md); the Constitutional Delta stated | the owner, by a record in `docs/decisions/` | declared `ΔO/ΔS/ΔA`; non-zero permitted only here |

No other class exists. A change that fits none of them is a constitutional
stop. The relationship between the two outcome classes: Terminate or halt
decides the Run outcome; Finality write durably commits that outcome for
one Execution. Neither performs the other's mutation.

## 5. Positive invariants

Each invariant names the test category in [testing_contract.md](testing_contract.md)
that proves it.

- **P1 One floor per tick.** For every elevator and every `t`,
  `|floor(t+1) - floor(t)| <= 1`. (Invariants)
- **P2 Floor bounds.** `0 <= floor(t) <= F-1` always. (Invariants)
- **P3 Capacity.** The number of `ONBOARD` passengers assigned to an elevator
  never exceeds `C`. (Invariants)
- **P4 Order of life.** For every completed passenger,
  `assigned_at = request_time <= pickup_time < dropoff_time`. (Invariants)
- **P5 One assignment.** Every revealed passenger has exactly one assigned
  elevator, written once, at `t = request_time`. (Invariants)
- **P6 One pickup, one dropoff.** Every `COMPLETED` passenger has exactly one
  `BOARDED` and one `ALIGHTED` event, in that order, on the assigned
  elevator, at the origin and destination floors respectively. (Invariants)
- **P7 Position completeness.** The Simulation History of a `COMPLETED` Run
  contains exactly one TickRecord per tick from `0` to the final tick, with
  one entry per elevator; a `HALTED` Run's TickRecords cover exactly its
  completed ticks, which may be none. (Invariants)
- **P8 Determinism.** Every Execution of the same `run_id` produces the
  byte-identical canonical Simulation History and the byte-identical
  Reproducible Output Surface (§2). Execution metadata and the Operational
  Log are outside this equality and may differ. (Reproducibility)
- **P9 Projection exactness.** For an elevator to which no further assignment
  is made after tick `t`, the route projection computed at `t` predicts its
  actual pickup and dropoff times exactly. (Unit/behavioural)
- **P10 Liveness for finite traces.** For every finite valid Trace, under the
  fixed Route Policy and any assignment of passengers to elevators, every
  passenger reaches `COMPLETED` at a tick no later than
  `T_last + 2 * P * (F - 1)`, where `T_last` is the last request time (0 if
  the Trace is empty) and `P` the number of Requests. The proof is
  [simulation_semantics.md](simulation_semantics.md) §8. `max_ticks`
  defaults to this bound; exceeding it is an invariant failure. (Invariants;
  Monte Carlo)
- **P11 Travel equals distance.** For every completed passenger,
  `dropoff_time - pickup_time = |destination - origin|`. (Invariants)
- **P12 Continuation equivalence.** An Execution reconstructed from its
  Checkpoint at tick `t` and continued to completion produces the same
  Simulation History from `t` onward, and the same Reproducible Output
  Surface, as an uninterrupted Execution of the Run. Its Operational Log
  and execution metadata differ and are compared separately. (CPOC)

## 6. Negative invariants: what may never happen

- **N1 No look-ahead.** At time `t`, no Scheduler Policy, Route Policy or
  projection may read any Request with `request_time > t`. The policy's
  decision surface is the read-only view defined in
  [scheduler_design.md](scheduler_design.md) §3, which cannot reach the Trace.
  Changing Requests with `request_time > t*` must not change any proposal,
  assignment receipt, passenger transition or elevator motion at ticks
  `<= t*`. Run termination is not part of this surface: the engine lawfully
  knows whether unrevealed Requests remain, so the final tick and the
  run-standing events may differ between two Traces that agree through
  `t*`. The exact compared surface is [testing_contract.md](testing_contract.md) §3.
- **N2 No reassignment.** An Assignment, once committed, never changes. No
  code path writes `assigned_elevator` twice.
- **N3 No destination change.** A Passenger's destination is the Request's
  destination, forever.
- **N4 No pickup before request.** No `BOARDED` event at `t < request_time`.
- **N5 No dropoff before pickup.** No `ALIGHTED` event without a prior
  `BOARDED` event for the same passenger.
- **N6 No overload.** No boarding that would make load exceed `C`. A
  boarding that would overload is refused and the passenger stays
  `WAITING` (capacity deferral, lawful). An `ONBOARD` count exceeding `C`
  is corruption.
- **N7 No wrong-way boarding.** No `BOARDED` event on an elevator whose
  departure direction at that floor and tick is incompatible with the
  passenger's direction. A passenger whose car departs the other way stays
  `WAITING` (direction deferral, lawful).
- **N8 No teleportation.** No elevator floor change other than by the motion
  step, by at most one.
- **N9 No second owner.** No surface other than the engine writes runtime
  state. The scheduler returns a proposal; the browser sends requests; the
  harness reads outputs; the loader constructs state once and then the
  engine owns it; none of them writes a Passenger or Elevator field.
- **N10 No estimate as outcome.** A scheduler's projected pickup, dropoff,
  cost or score is never written to a Passenger record and never reported as
  a realized time. It may be recorded as a `RECEIPT` on the `ASSIGNED` event
  for later calibration only.
- **N11 No projection as authority.** The position exports, statistics,
  route display, UI fragments and Monte Carlo summaries are derived from the
  Simulation History and Passenger records and may never be read back to
  establish them.
- **N12 No mutable present as history.** A historical question ("where was
  elevator 2 at tick 7?") is answered from TickRecords and Simulation
  Events, never from current state, and only for ticks that have a record.
- **N13 No resurrection.** A final Execution is never resumed, and its
  Continuation Document is never replaced by a checkpoint or finality
  write (`EXECUTION_FINAL` on load; `WRITE_AFTER_FINAL`, `STALE_WRITER` on
  write); a `COMPLETED` passenger never boards again; a copy of a `RUNNING`
  document placed in another Store is refused (`STORE_MISMATCH`); another
  Execution of the same Run is never treated as the continuation of this
  one (the document's `execution_id` must equal the requested one). No
  output directory, file path or caller argument can select Execution
  standing. Separate Executions of the same `run_id`, in one Store or
  several, are lawful and independent.
- **N14 No recovery by recomputation.** Continuation after process death
  starts at the checkpointed tick from the Checkpoint's typed snapshot.
  Rerunning from `t = 0` is not continuation, and folding the Simulation
  History prefix into present state is not continuation, even when either
  produces the same output. The loader constructs state from the typed
  `Snapshot` only; the History prefix is verified by an isolated verifier
  whose working state is a distinct type that can never become engine
  state; no function anywhere in the simulation package produces a
  `Snapshot` or engine state from History ([cpoc_design.md](cpoc_design.md) §5.1).
- **N15 No hidden policy state.** No Scheduler Policy retains state between
  calls in memory. If a policy needed state, it would be declared, engine-
  owned and checkpointed; none in scope does.
- **N16 No float in decisions.** Costs, ties and comparisons that decide an
  assignment use exact integer arithmetic.
- **N17 No silent fallback.** A missing, malformed, mismatched, stale or
  foreign Continuation Document, Trace or Configuration refuses with a named
  reason. Nothing substitutes an older or default representation. There is
  no code-identity override: a Continuation Document written by different
  code is refused, always. An unsupported execution environment refuses to
  start a governed Run.
- **N18 No operational fact in the Simulation History or the Reproducible
  Output Surface.** No record of a process, file, checkpoint, load,
  resumption, timestamp, `execution_id`, `store_id`, Git provenance or
  scenario label appears in the Simulation History or in any file of the
  Reproducible Output Surface, or affects sequence numbers, bytes,
  `run_id`, any decision or any metric.

## 7. Historical versus mutable

| Historical (immutable once written) | Mutable present (changes only in the tick procedure) |
| --- | --- |
| Configuration (including policy name and parameters), Trace, code identity | current time `t` |
| every Simulation Event and TickRecord | each Elevator's `floor` and `heading` |
| every Operational Record | each Passenger's standing (until `COMPLETED`) |
| each Passenger's `assigned_elevator`, `assigned_at`, `pickup_time`, `dropoff_time` once written | Execution standing (until final); the document's `write_sequence` |
| `execution_id`, `store_id`; a Continuation Document's final standing once written | the open UI session's "current execution" pointer |

Mutable present state is always reconstructible from the Checkpoint.
History is never reconstructed from mutable present state, and present
state is never reconstructed from History.

## 8. What scheduler authority means

A Scheduler Policy has the authority to **propose**, for exactly one newly
revealed Request, exactly one elevator id, using only the view it is given.
It has no authority to write, retain, reorder, defer, reject or revisit. The
engine validates the proposal (elevator id in range, passenger newly revealed
and unassigned) and commits it. A proposal outside the range, or a policy
that raises, halts the Run; the engine never substitutes a default elevator.

## 9. What simulation authority means

The engine has the authority to **establish** every runtime fact, through the
tick procedure only, in the exact order defined, and to **emit** the
Simulation History atomically with each establishment. It has no authority
to look at future Requests on behalf of a policy, to change an Assignment,
to skip a tick, to move more than one floor, to overload, to board against
the departure direction, to continue a final Run, or to alter a record once
emitted.

## 10. What constitutes a committed assignment

An Assignment is committed when, in the assignment step of tick
`t = request_time`, the engine has validated the policy's proposal and written
`assigned_elevator` and `assigned_at = t` to the Passenger record and emitted
the `ASSIGNED` event. Before that write there is no assignment; after it there
is exactly one, forever. Nothing a policy returns is an assignment until the
engine writes it.

## 11. What constitutes passenger completion

A Passenger is `COMPLETED` when the engine, in the alighting step of a tick
`t`, finds the Passenger `ONBOARD` its assigned elevator with
`floor = destination`, writes `dropoff_time = t` and emits `ALIGHTED`. Then
and only then do `wait_time = pickup_time - request_time`,
`travel_time = dropoff_time - pickup_time` and
`total_time = dropoff_time - request_time` exist for that passenger.

## 12. What makes a run reproducible

A Run is reproducible when its `run_id` inputs are fixed: Configuration
(including policy name and parameters), Trace, and code identity. The
engine is deterministic by construction: fixed tick order, fixed iteration
orders (ids ascending), fixed tie-breaking (lowest id, `UP` before `DOWN`),
exact integer arithmetic, no wall-clock, no randomness. The only randomness
in the project is the Scenario generator, which is a pure integer function
of `(pattern, parameters, seed)` under its own specified generator and is
outside the Run. A seeded stochastic Scheduler Policy is permitted by this
constitution only if its seed and random state are declared engine-owned
facts in the authority model and carried in the Checkpoint; none is in
scope.

Code identity is part of `run_id` so that the same inputs under different
code are different Runs. Two Executions that differ in code identity never
share a `run_id`, and a Continuation Document is never loaded by code other
than the code that wrote it.

**Supported execution contract.** Code identity establishes
reproducibility only within this contract, which every governed entry
point checks before a Run begins and refuses to start otherwise
(`UNSUPPORTED_EXECUTION_ENVIRONMENT`): the interpreter runs with bytecode
writing disabled (`python -B` or `PYTHONDONTWRITEBYTECODE=1`); no
`__pycache__` directory exists inside the governed simulation package;
code identity is computed from the package's `.py` files before any Run
begins; the package's source files are not modified for the lifetime of
the process (the process re-hashes at exit and records
`CODE_IDENTITY_DRIFT` in its Operational Log if they were, which
invalidates that Execution's evidence). The project does not attempt to
attest against malicious replacement of executing instructions after
process start; it prevents the ordinary stale-bytecode and dirty-source
cases.

## 13. What lawful continuation after process death means

A continuation is lawful when a fresh operating-system process, given only a
Store and an `execution_id`, admits that Execution's Continuation Document
after every verification in [cpoc_design.md](cpoc_design.md) §5, verifies
the Simulation History prefix with an isolated verifier and discards that
verifier, constructs the exact time `t`, every Passenger and Elevator
field and the Execution standing from the typed snapshot alone, holds the
prefix through `t-1` as its history, records what it admitted in a
`LOAD_ADMITTED` operational record, and then executes tick `t` onward by
the ordinary tick procedure, producing the Simulation History an
uninterrupted Execution would have produced. CPOC never creates authority; it tests that the authority above
survives the boundary.

## 14. What constitutes corruption or contradiction

Any of the following is corruption, halts the Run (or refuses the load) and
is reported, never repaired silently:

- a violated positive invariant P1 to P7 or P11 observed at runtime;
- any negative invariant N1 to N18 observed at runtime or in a load;
- a Continuation Document whose recorded `run_id`, Configuration hash,
  Trace hash, `store_id` or `execution_id` does not match its own embedded
  contents, its Store or its path;
- a Continuation Document whose Simulation History prefix does not end at
  `t-1`, whose Passenger fields contradict its events, whose TickRecords
  do not follow from its events under the route law, or whose elevator
  floors and headings do not continue from its last TickRecord;
- two Executions with the same `run_id` and different Simulation
  Histories or different Reproducible Output Surfaces (a determinism
  defect, reported as a `HALTED`-class failure of the comparison);
- two surfaces answering the same question differently after
  reconstruction (position export versus TickRecords, passenger summary
  versus Passenger records, UI view versus engine state).

Two governing documents disagreeing about a consequential rule is a
constitutional contradiction: work stops until the owner resolves it
([AGENTS.md](../AGENTS.md), same-scope conflict handling).

## 15. Constitutional Delta of this document

This is the founding document. `ΔO`: defines the ontology in §2. `ΔS`:
defines the meanings in §4 to §13. `ΔA`: assigns authority in §3 and
[authority_model.md](authority_model.md). Revision 6 relative to revision 5
(proposed in [decisions/owner_decision_003_revision_6_repairs.md](decisions/owner_decision_003_revision_6_repairs.md)):
Revision 7 relative to revision 6 (proposed in
[decisions/owner_decision_004_revision_7_closure.md](decisions/owner_decision_004_revision_7_closure.md)):
`ΔS`: the Operational Log carrier lifecycle and the Experiment result
split; `ΔO/ΔA`: none. Revision 6 relative to revision 5: `ΔO`: adds
Execution and `execution_id`, the Reproducible Output Surface,
the Operational Log as a separate file keyed by `execution_id`, and the
Store schema version; `ΔS`: separates the Run outcome from Execution
standing, defines write admission, the supported execution contract and
the typed snapshot boundary, narrows P8/P12 to the Reproducible Output
Surface; `ΔA`: the executing process owns its Execution; transition
classes added for code identity establishment, Store creation, Execution
creation, Operational Log append and Finality write. Revision 5 relative
to revision 4
(proposed in [decisions/owner_decision_002_revision_5_repairs.md](decisions/owner_decision_002_revision_5_repairs.md)):
`ΔO`: adds Store, Continuation Document, Operational Record and Log, code
identity as an object, and `source_id` on Request; `ΔS`: separates
Simulation History from the Operational Log, narrows N1 to the decision and
motion surface, replaces the liveness bound with a proved one, removes the
code-identity override; `ΔA`: Run standing's durable carrier is the
Continuation Document in a Store; the loader's construction authority is
limited to the snapshot section. It grants no implementation authority;
admission is the owner's act, recorded as a decision record in
`docs/decisions/` naming the admitted files and their digests.
