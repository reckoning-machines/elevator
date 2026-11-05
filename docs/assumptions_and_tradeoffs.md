# Assumptions, Simplifications and Trade-offs

Status: **RECORD. DRAFT, NOT ADMITTED. Revision 6, 2026-11-04. Every item here is also stated in its owning document; this is the consolidated list the README will cite.**

Each entry: what the take-home left open, what was chosen, why, and the
alternative considered. Sources are distinguished: "the take-home" is the
three-page brief as read by the independent audit; "the owner's brief" is
the owner's project instructions of 2026-11-04 (tick-order starting point,
AIE framing, OSA and CPOC doctrine, Monte Carlo, web UI); "repository
doctrine" is what [doctrine_adoption.md](doctrine_adoption.md) adopted.

## 1. Assumptions resolving the source assignment

| # | Topic | Choice | Why | Alternative considered |
| --- | --- | --- | --- | --- |
| A1 | Floor numbering | `0..F-1`; floor 0 is the lobby; elevators start at 0 unless configured | zero-based ids everywhere; one convention | `1..F` |
| A2 | Tick order (our design choice; the take-home prescribes none) | reveal, assign, alight, board, head, record, terminate?, move, advance ([simulation_semantics.md](simulation_semantics.md) §2) | a same-floor request boards with zero wait; alighting frees room for boarding; reversal costs nothing; the record shows the floor where the tick's stops happened | record after move, the owner's brief's starting point (rejected: the row for `t` would show a floor at which nothing happened at `t`) |
| A3 | Position log meaning | beginning-of-tick position; heading = motion during the tick; load after boarding | `floor(0)` is the initial floor; `travel = distance` | end-of-tick |
| A4 | Doors and dwell time | zero: a stop consumes no time | the take-home defines one time unit as one floor of movement and nothing about doors; adding dwell adds a parameter with no evaluative content for the comparison | configurable dwell `d` ticks per stop (**would be the first improvement with more time**, see §4) |
| A5 | `origin == destination` | invalid Request; the Trace is refused at load | such a request has no decision content and would distort statistics with zero-time passengers; the generator never emits one | complete immediately with zero times |
| A5a | Supplied passenger id | the take-home's `id` column is the Passenger's `source_id`: required, unique, preserved in every output; `passenger_id` is the internal sorted position, with the mapping in `passengers.csv` (owner decision proposed as D-12) | the input's identity is not silently replaced; ordering stays a cheap integer | internal ids only (rejected by the independent audit, I-15) |
| A6 | Boarding direction | direction-compatible: a passenger boards only when the car's departure direction from the origin matches the passenger's direction; a car continuing its sweep takes same-direction passengers only; a free car (idle or at a reversal point) takes the oldest waiting passenger and departs their way; a passenger whose car passes the wrong way waits for its return (owner decision D-01, 2026-11-04) | conventional elevator behaviour; removes the objection that the modelling assumption inflates the cost-based policy's advantage over the baselines; travel time becomes exactly the trip distance | direction-agnostic boarding (the original recommendation; rejected by the owner as artificial) |
| A7 | Route policy | LOOK: continue while a committed stop is ahead, else turn toward the nearest stop, `UP` on ties | standard, explainable, starvation-free for finite traces, and a pure function of (floor, heading, stops) so the route is derived, not stored | ordered stop list with insertion (rejected: a second authoritative carrier of future intent; and LOOK with re-projection already evaluates insertion) |
| A8 | Capacity at execution | boarding is gated by `load < C`; a full car defers boarding and LOOK returns | capacity can never be exceeded; deferral is modelled exactly in the projection | hard failure on arrival full (rejected: not a lawful state to refuse into, since assignment is immutable) |
| A9 | Capacity at assignment | Tier 1: the candidate is not capacity-deferred in its projection and causes no new capacity deferral among the car's committed passengers; Tier 2 otherwise, chosen only when Tier 1 is empty; a Tier 1 receipt is a projection at assignment, not a guarantee | the take-home forbids rejecting a passenger, so a fallback must exist; the fallback is explicit and recorded | penalty-only (rejected: the owner's brief preferred a hard constraint, and it gives a cleaner invariant); reject the request (violates "every passenger immediately assigned") |
| A10 | Tie-breaking | lowest elevator id; `UP` before `DOWN`; oldest passenger first at a stop; passengers ordered by `(request_time, input index)` | determinism with no randomness | random with seed (rejected: needless state) |
| A11 | Assignment commitment | the engine's write in step 2 of the request's tick; immutable thereafter | the take-home requires immediate assignment and forbids changing the destination; **immutable assignment is this project's stricter rule**, chosen so that every decision is a single committed fact | reassignment of waiting passengers (a lawful reading of the take-home; rejected for authority clarity) |
| A12 | Termination | first tick at which all requests are revealed and all passengers complete; `max_ticks` defaults to the proved bound `T_last + 2P(F-1)` and may only be lowered | the log ends at the last alighting; exceeding the proved bound is an invariant failure (`LIVENESS_BOUND_EXCEEDED`); exceeding an explicit smaller horizon is a reported halt (`HORIZON_EXCEEDED`), not an invariant failure | a looser unproved horizon (revision 4; rejected by the independent audit, I-07) |
| A13 | Idle behaviour | stay put, heading `NONE` | simplest; parking is a policy question outside the comparison | return to lobby / zoning |
| A14 | Initial floors | all 0 by default; configurable per elevator | | random |
| A15 | Requests per tick | unbounded; simultaneous requests are assigned sequentially in id order, each seeing the previous assignment | the only way to keep each decision a pure function of a consistent view | batch assignment of simultaneous requests (rejected: a combinatorial sub-problem with no clear benefit) |

## 2. Design decisions (the list the owner's brief required to be made explicit)

| Decision | Resolution | Owner document |
| --- | --- | --- |
| Exact tick ordering | A2 | semantics §2 |
| Beginning- vs end-of-tick logging | beginning (A3) | semantics §3 |
| Door/dwell time | zero (A4) | semantics §6 |
| Same-floor source/destination | refused (A5) | semantics §6 |
| Deterministic tie-breaking | A10 | semantics §2, scheduler §6.4 |
| Route representation | derived projection of LOOK; only `heading` is stored (A7) | authority rows 14, 15, 20 |
| Direction semantics | `next_heading` function; departure direction at a stop (`departure`) | semantics §4, §4.1 |
| Reversal semantics | only when nothing ahead; same tick; no cost | semantics §4 |
| Assignment commitment point | A11 | constitution §10 |
| Capacity feasibility semantics | A8, A9 | semantics §5, scheduler §6.2 |
| Fairness/starvation mechanism | LOOK liveness; oldest-first boarding; age-weighted marginal delay; tail penalty; Tier 1 admissibility | scheduler §8 |
| Termination condition | A12 | semantics §8 |
| Monte Carlo reproducibility | a specified integer generator (SplitMix64) with exact per-pattern algorithms; trace hash recorded; definition hash and execution id | evaluation §6, §7.1 |
| Checkpoint granularity | at tick boundaries, on request or at an optional interval; never by default, including UI sessions (owner decision D-06) | cpoc §2 |
| Run versus Execution | `run_id` is deterministic semantics; an Execution (`execution_id`, random) owns continuation state, durable standing, Operational Log and output location; the loader is addressed by `(store, execution_id)`; writes admitted by `write_sequence` (proposed D-15, superseding D-08's `(store, run_id)`) | constitution §2, §4.3; cpoc §2, §3 |
| Code identity | content hash of the governed package under the supported execution contract (`-B`, no `__pycache__`, hash before the Run, sources immutable for the process); no override (proposed D-16, refining D-09) | constitution §2, §12; architecture §4 |
| Simulation History versus Operational Log | two carriers; the Operational Log is a separate append-only file per Execution, written after the document it reports is hashed (proposed D-18, refining D-10) | constitution §2, N18; cpoc §3.2 |
| Snapshot consumption | typed `Snapshot` boundary and a prohibited call graph, with negative tests; hash equality is value equality, not provenance (proposed D-17) | cpoc §4.1, §5.1 |
| Deferral classification | direction decides first; capacity only at a compatible arrival (proposed D-19) | semantics §4.2 |
| Reproducible output surface | the eight surface files are identical per `run_id`; `execution_metadata.json` and the Operational Log are outside equality (proposed D-20) | constitution P8, P12, N18; evaluation §3 |
| Scenario domains | `2 <= F <= 200`, `1 <= N <= 20`, `1 <= C <= 50`, bounded counts and horizons, fixed lobby share 4/5 (proposed D-21) | evaluation §2, §6 |
| Batch versus live | `normalize_requests` shared; `simulate` runs to the outcome; `create_engine` returns a running engine for the UI (proposed D-22) | evaluation §2; architecture §1 |
| Liveness standing | proved bound `T_last + 2P(F-1)` (D-11, independently verified at revision 5; lemma wording corrected at revision 6) | semantics §8 |
| Source-facing position export | `elevator_positions.csv`, one row per timestamp; the long form is an analysis file (D-13) | evaluation §3 |
| Historical event/log representation | append-only Simulation Events and TickRecords (receipts); position exports derived | authority row 18 |
| UI state ownership | server session (ephemeral pointer to an engine); browser holds form inputs and fragments | ui §6 |
| Event sourcing | not used as the state model; snapshot + history prefix | §3 below |
| State persisted for continuation | configuration, trace, `t`, elevator floor and heading, every revealed passenger's fields, run standing, Simulation History prefix, Operational Log, identity hashes and store id | cpoc §3 |
| Derived values recomputed after restart | load, onboard and waiting sets, committed stops, departure directions, routes, projections, position exports, statistics, UI views | cpoc §3 |

## 3. Trade-offs accepted

- **Immutable assignment limits fairness.** No mechanism can rescue a
  passenger from a poor assignment. Accepted as this project's own rule
  (the take-home forbids destination changes, not reassignment); the consequence is measured by tail metrics.
- **Direction-compatible boarding can leave a passenger waiting for a
  return trip** even when their car passed them with room. Accepted
  because it is how elevators behave, it keeps the policy comparison free
  of a modelling assumption that favours the cost-based policy, and the
  cost is visible as `wrong_way_passes` in the outputs.
- **Sessions are not crash-durable unless checkpointed.** Accepted so that
  durable I/O never sits on the interactive tick path; continuity is proved
  by the dedicated witness, not by every session.
- **No demand forecasting in the scheduler.** The one lawful source of
  foresight (patterns in past requests) is not used; the calibration report
  measures one source of projection error, which is an input to, not an
  answer to, whether a demand model would be worth building.
- **Snapshot checkpoint rather than event sourcing.** Event sourcing would
  make state a replay of History and remove the snapshot, but it would also
  make reconstruction a recomputation, blur the line the constitution draws
  between present state and history, and add a replay engine. The snapshot
  carries present state; the History prefix carries the past; the loader
  checks they agree. For a few thousand ticks the snapshot is small.
- **Zero dwell** flatters every policy equally; absolute numbers are not
  comparable to a real building.
- **Pure Python, single process per run.** No timing is claimed until
  measured; if the default Experiment proves slow, independent runs are
  trivially parallel and nothing semantic changes.
- **A local file Store cannot defend against deliberate overwrite of its
  own document** (cpoc §6 row 6). Accepted as the limit of a take-home
  persistence design; location independence, copy refusal and write
  admission against stale or post-final writers are what the design does
  guarantee.
- **Assurance is bounded.** OSA and CPOC prevent accidental competing
  authority and prove the designed continuation boundary with typed
  boundaries, call-graph restrictions, negative tests and runtime
  assertions. They do not attest against code that deliberately violates
  its own source contract, and no attestation infrastructure is built.
- **Server-rendered SVG charts** instead of a charting library: fewer
  dependencies, less JavaScript, and one histogram is all that is needed.
- **Nearest Car ignores load and direction.** It is the classic baseline
  and is named as such; a smarter nearest-car is not claimed to be beaten.
- **Total time is wait plus a fixed distance.** Since travel equals the
  trip distance under direction-compatible boarding, the policies differ
  only in wait; the cost function prices wait and the delay imposed on
  others, and total time is reported, not optimised separately.

## 4. What would be improved with more time

1. A dwell parameter (A4) and a door-time model, since the comparison's
   sensitivity to stop cost is the first thing a reviewer will ask.
2. A direction-agnostic boarding variant as a configuration switch, to
   measure what the elevator convention costs each policy.
3. A demand-aware term in the cost (rate of recent arrivals by floor), with
   its value measured against the calibration report.
4. Idle parking policies (return to lobby during up-peak).
5. Sensitivity sweeps over the cost weights, reported as a table rather than
   tuned.
6. A background job for larger Experiments in the UI.
7. Tightening the liveness bound (it is proved but conservative).

## 5. Explicit non-goals

Everything in [AGENTS.md](../AGENTS.md) "Scope control". Also: elevator
acceleration, multiple doors, express zones, group control by floor sector,
energy, and real-time scheduling.
