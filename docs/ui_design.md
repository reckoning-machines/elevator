# UI Design

Status: **GOVERNING DOCUMENT for the web interface's jurisdiction (what the browser may hold, what the server projects). Admitted by record 006 at revision 7.1; amended to revision 7.4 by [record 011](decisions/owner_decision_011_ui_contract_reductions.md) (three UI-contract reductions: §2, §2.1, §2.2, §2.3) and to revision 7.5 by [record 012](decisions/owner_decision_012_ui_execution_metadata_downloads.md) (§3 downloads). The draft status words of the earlier revisions are superseded by those records.**

Jurisdiction: the screen, its controls, the projections it shows, the
evaluation mode, the request/response shape, and the rule that the browser
owns nothing consequential. Subordinate to [constitution.md](constitution.md)
and [authority_model.md](authority_model.md) row 36. The UI is an owner-directed
enhancement, not a take-home requirement.

## 1. Principle

The UI is a projection of server-owned state. The server process holds the
engine; the browser holds form inputs and the last fragment it was sent. A
fresh browser tab on the same session must show exactly the same thing. The
simulation package has no knowledge that the UI exists.

Stack: FastAPI, Jinja2, HTMX, inline SVG for charts, no JavaScript beyond
HTMX and at most a few lines to start and stop the play timer.

## 2. One screen, three regions, and an evaluation page

```text
+------------------------------------------------------------------+
| Controls                                                         |
| elevators [3] floors [10] capacity [4] scheduler [cost_based v]   |
| requests [built-in example | pasted rows]  [New run] [Step] [Play] |
| t = 12   standing: RUNNING                                       |
+--------------------------------+---------------------------------+
| Elevator view                  | Results (final run only)        |
|  9 |   |   |   |               | completed 14 / 40               |
|  8 |   | B |   |               | wait  mean 3.2  p95 9  max 12   |
|  7 |   | ^2|   |               | total mean 7.9  p95 15          |
|  6 | A |   |   |   waiting:    | deferred 1  wrong-way 2         |
|  5 | v3|   | C |   floor 3: #17 (->8, E=A)                       |
| ...                            | [histogram of wait times, SVG]  |
|  0 |   |   | -0|               | why #17 -> A: tier 1 (no new    |
|                                |   capacity deferral), cost 23   |
+--------------------------------+---------------------------------+
```

### 2.1 Controls

| Control | Server effect | Browser role |
| --- | --- | --- |
| elevators, floors, capacity, scheduler, request source (the built-in example or pasted rows) | `POST /runs` creates a session by calling `create_engine` ([evaluation_design.md](evaluation_design.md) §2) with a concrete request Trace: the built-in example, or `time,id,source,dest` rows through `normalize_requests`. The single-run screen has no scenario or seed control: scenario generation belongs to the scenario and evaluation path, and the Experiment page (§3) is the scenario-based surface; the engine is `RUNNING` at `t = 0`; no outputs are written; it never calls the batch `simulate` | a form; values are not state until posted |
| New run | as above | |
| Step | `POST /sessions/{id}/step?from_time=t` executes exactly one tick if the engine's `t` equals `from_time` and the run is `RUNNING`; otherwise it returns the current screen unchanged with a "stale page" or "run is final" notice. `from_time` is a guard (the server's `t` decides), never a selector | the button carries the last rendered `t` |
| Play / Pause | the browser issues Step every 500 ms (`hx-trigger="every 500ms"` while playing); the server executes at most one tick per request | the timer is the only client-side state, and it is interaction state |
| Checkpoint | `POST /sessions/{id}/checkpoint` delegates to the checkpoint module: the Execution's Continuation Document in the server's Store at the current boundary, under write admission (the only durable write a session makes unless an interval is set). The first checkpoint binds the session's Execution to the Store and flushes its in-memory Operational Log there before the checkpoint receipt (cpoc §2.2a); a session never checkpointed keeps its log in memory only | |
| Checkpoint interval (optional, default none) | sets `--checkpoint-every k` semantics for the session | a form field |
| Reopen execution | `POST /sessions` with an `execution_id` chosen from the server's Store listing; the server loads it by `(store, execution_id)`; a file upload is not accepted; the loader's refusals are shown verbatim | |

Sessions are not checkpointed unless the user asks (owner decision D-06):
a server restart loses sessions that were never checkpointed, and reopens
any that were, from the Store. The session id is the `execution_id`. The
Store path is server configuration, never a request parameter.

### 2.2 Elevator view (derived from engine state at `t`)

- the building as floors `F-1` down to `0`;
- each elevator as a column: position (floor), heading arrow or `-` for
  idle, load as `n/C`;
- waiting passengers by floor with destination and assigned elevator;
- onboard passengers listed per elevator with destination;
- a "why" disclosure for the most recent assignment, rendered from the
  `ASSIGNED` event's receipt: tier, cost, the candidate table. Tier 1 is
  rendered as "no new capacity deferral in the projection at assignment",
  never as a guarantee ([scheduler_design.md](scheduler_design.md) §6.2).
- a history scrubber: `GET /sessions/{id}/tick/{k}` renders the view for a
  past tick `k` **from TickRecords and Simulation Events only**
  (constitution N12), labelled "history". Availability follows committed
  TickRecords, never `final_tick`: let `max_history_tick` be the largest
  `t` with a TickRecord, if any exist. The lawful range: for a `RUNNING`
  session at boundary `t`, `0 <= k <= t - 1`; for a `COMPLETED` run,
  `0 <= k <= final_tick` (the final tick always has a record); for a
  `HALTED` run, `0 <= k <= max_history_tick`. If no TickRecord exists (a
  session at `t = 0`, or a halt in tick 0 as in W-E), every history
  request returns `NO_HISTORY` (HTTP 404). A `k` outside the range returns
  `HISTORY_TICK_NOT_AVAILABLE` (HTTP 404). Neither ever substitutes current
  state. It is read-only; Step always applies to the engine's current `t`.

### 2.3 Results (derived)

Final-run outputs only. While a run is `RUNNING` the screen shows current state only (the tick, each elevator's floor, heading and load, the waiting and onboard passengers and the run standing); there is no partial reporting mode, and no metric, distribution or calibration is shown until the run is final. When the run completes: completed/total, wait mean, median, p95, max;
total mean, p95; capacity-deferral and wrong-way-pass counts; throughput; a histogram of wait
times as inline SVG; when the run is complete, the generated observations.
A "compare" link runs the same Trace under the other two policies
server-side (three runs, same Trace hash) and shows a three-column metric
table. This is the single-run comparison; it is not the Monte Carlo result.

## 3. Evaluation page (`/evaluate`)

Separate from the interactive screen. A form selects patterns, `K` seeds,
building parameters; `POST /experiments` runs the Experiment synchronously
with a bounded `K` (default 20, maximum 50) and renders:

- per pattern, a table of policies by the metrics of
  [evaluation_design.md](evaluation_design.md) §4 (mean across seeds);
- per pattern, the paired-difference summary against each baseline (win,
  tie, loss counts; median paired difference) for p95 wait and mean total;
- the experiment execution id and code identity of the Experiment, with
  `n_defined`, `n_pairs` and `halted_count` shown beside every aggregate;
- one distribution visualisation: for the selected pattern, overlaid
  per-seed p95 wait as a strip plot or small histogram per policy, inline
  SVG;
- downloads: Experiment result downloads expose the reproducible
  experiment-results artifact (`experiment_results.json`, which every
  comparison on the page is rendered from). Execution-metadata download
  (`experiment_execution.json`) is additionally exposed when execution
  metadata was persisted for that execution: for a live Experiment the
  server produced, each Execution has its own metadata under an
  execution-specific key, and a later Execution of the same Experiment never
  replaces it. The UI must not reconstruct or fabricate execution metadata
  for committed evidence that lacks such an artifact (the fixed Experiment's
  committed evidence is the result surface only); the page states that none
  was persisted.

The page never animates runs. If the Experiment exceeds a bounded time, the
response says so and suggests a smaller `K`; no background job system is
introduced for a take-home.

## 4. Request/response shape

Every mutating request is a form `POST`; every response is a full-screen or
regional HTML fragment. There is no JSON API for the browser, no client-side
model, no local storage, no cookies beyond the session id, and no state
encoded in URLs except identifiers (`session id`, `tick k`).

## 5. Failure display

A halted run shows the halt reason and the History to that point. A refused
reopen shows the loader's reason verbatim. A stale Step shows the current
state with a notice. A history request outside the lawful range shows the
refusal. The UI never retries, never reconciles, never guesses.

## 6. What the browser may hold

Form field values before submission, the last rendered fragments, the play
timer flag, scroll position. Nothing else. In particular: not `t` (the
`from_time` it echoes is a copy used as a guard), not positions, not
assignments, not results. Any of these appearing in client-side JavaScript
state, local storage or a URL as a source of truth is an authority breach
(constitution N9, N11).

## 7. Constitutional Delta

NONE. The UI adds no owner, carrier or writer. UI sessions are `EPHEMERAL`
pointers to engines (each an Execution) whose durable twin, when one
exists, is the Execution's Continuation Document in the server's Store.
