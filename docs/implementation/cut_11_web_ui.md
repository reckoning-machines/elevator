# Cut 11 implementation record: the web UI

Date: 2026-11-05. Governing design: Revision 7.3 (`docs/ui_design.md` §1 to §7, testing contract §8). A thin
demonstration surface over the existing application boundaries; no production module under `elevator/` changed.

```text
CUT 11: IMPLEMENTED / LOCAL VERIFY PASS
```

## 1. Baseline

Governing and plan digests unchanged (constitution `b34958f91e6d`, authority_model `4a066fb9fd8d`, semantics `821cb89dbbd4`, scheduler `25e7ec14ec3a`, evaluation `b8c29a3d47b5`, cpoc `65ca79366e4f`, ui `b22ea1164403`, architecture `a38da7e42867`, testing_contract `b0e78b99a824`, plan `26f6920ee56c`). Before: 321 tests.

## 2. Files

- New: `web/{__init__,__main__,app}.py`; `web/templates/{base,index,session,_screen,_shaft,_why,_tick,_compare,_refused,evaluate}.html`; `web/static/htmx.min.js` (htmx 1.9.12, fetched from unpkg and committed so the demo runs offline); `web/demo_requests.csv` (the 25-request bursty example already used by Cuts 9 and 10); `tests/web/{__init__,test_ui}.py`.
- Changed: `pyproject.toml` (optional `web` extra: fastapi, jinja2, uvicorn, python-multipart; `httpx` in the test extra). Nothing in `elevator/` changed; the code identity is the Cut 10 one, `0367c5f3a8f28f956743b6806abffd0e2d45e83dc33111df6dc4662503881f64`.

## 3. Routes (all server-rendered HTML; no JSON API)

`GET /` (controls: policy, floors, elevators, capacity, built-in example or pasted `time,id,source,dest` rows; Store reopen list when a Store is configured) · `POST /runs` (new session via `api.create_engine`, RUNNING at t = 0, nothing written) · `GET /sessions/{id}` · `POST /sessions/{id}/step?from_time=t` (one tick; a stale or final guard renders unchanged state with a notice) · `POST /sessions/{id}/finish` (the same `step`, repeated server-side to the Run outcome) · `POST /sessions/{id}/checkpoint` and `POST /sessions` (explicit checkpoint and reopen by `execution_id` through the checkpoint module, only when `--store` is configured) · `GET /sessions/{id}/tick/{k}` (history from TickRecords and Events; `NO_HISTORY` / `HISTORY_TICK_NOT_AVAILABLE`, HTTP 404) · `GET /sessions/{id}/why/{passenger_id}` (the committed ASSIGNED receipt) · `GET /sessions/{id}/compare` (three policies, same Trace) · `GET /evaluate` (the committed `experiment_results.json`) · `POST /experiments` (a small Experiment, K from 1 to 10).

## 4. What it shows

Elevator view as inline SVG (floors vertical, car rectangles with heading and load/capacity) at the current t and, through a slider over recorded ticks, at any recorded tick (history labelled, from TickRecords only). Waiting and onboard lists. The "why" block renders the latest or selected assignment's receipt: candidate, tier, projected wait, marginal impact, cost, selected car (tier 1 stated as "no new capacity deferral in the projection, not a guarantee"); a baseline policy's receipt is printed as recorded. Final runs add reporting's summary, observations and passengers table, and for cost_based the calibration table with `error = realized − projected`, labelled as not demand forecasting. Compare shows avg wait, p95 wait, max wait, avg total and capacity deferrals for the three policies and the shared trace hash, labelled "a comparison on this one trace, not a ranking". HALTED shows a red badge, the halt reason and "did not complete", and no per-passenger metrics (a halted summary has none).

## 5. Authority boundary

The server holds sessions (`EPHEMERAL` pointers to live engines); the browser holds form values, the last fragments, and the Play flag (a query parameter). No route accepts a position, floor, heading, standing, load, assignment or tick as a setter (`from_time` is a guard only). The only engine mutation in `web/app.py` is `step()`. No cookies, local storage or client state; the only inline script is a one-line slider handler beside htmx. Store path is server configuration, never a request value; a file path posted as an `execution_id` is refused.

## 6. Dependencies (admitted table, architecture §1)

`web` imports only `api`, `checkpoint`, `harness`, `reporting` and `domain` (`Refusal`, `establish_code_identity`). It does not import `engine`, `route`, `policies`, `scenarios`, `operations` or `cli`, never calls `simulate`, and nothing under `elevator/` imports `web` (all asserted). The built-in example and the pasted rows go through `create_engine`'s own `normalize_requests` path; a pattern-based "scenario" source was left out because architecture lists no `web -> scenarios` edge (the Experiment form passes pattern names to the harness instead).

## 7. Verification

```text
python3 -B -m pytest -q -p no:cacheprovider tests   -> 337 passed in 195.05s (321 + 16)
tests/web/test_ui.py                                 -> 16 passed in about 1.4 s
```

Tests: page loads; `ui_new_run_creates_engine_not_simulate`; stale `from_time` and `step_on_final_run_is_noop`; the history range rules (`history_at_creation`, `history_current_tick_refused`, `history_row_after_advancing`, `history_final_tick_completed`, HALTED range); `ui_projection_matches_engine` (row 29(b)); two clients, same state; the browser cannot set state; invalid input renders a refusal, never a trace; compare on one trace with values equal to reporting's; receipt values and calibration rows shown as committed; results from reporting; `ui_first_checkpoint_flushes_log`, reopen by `execution_id` only, final refusal; evaluate page from the committed results and a tiny live Experiment; structure (imports, no `simulate`, no route/policy/metric logic, no History-to-state path in `web/`). Real-server smoke (`python -B -m web`): new run, step, run to end, compare (round_robin final tick 36, nearest_car 43, cost_based 31 on the demo). No `__pycache__` in `elevator/`, `web/` or `tests/`. No screenshots taken.

## 8. Realization choices and gaps (flagged)

1. "Run to end" (`/finish`) is not a named route in ui_design; it repeats the same `step` server-side so a demo need not wait 500 ms per tick.
2. Live results while RUNNING are not shown (results appear when the run is final); the projected committed stops per car (ui §2.2) are not drawn because they need the route projection, which `web` may not implement; the wait-time histogram is not drawn (it would be a metric calculation in `web`).
3. `/experiments` takes the fixed Experiment's pattern parameters (decision 010) and a form building (default 20/4/8), K 1 to 10 (design says default 20, max 50); downloads of `experiment_results.json` are not offered.
4. `web/app.py` reads `_config` and `_trace` from the engine (as `cli.py` does) to build a `RunRecord`; no public accessor exists and none was added.
5. A server restart loses sessions never checkpointed (decision D-06); finishing a checkpointed session writes finality.
6. W-E (a halt in tick 0 with no TickRecord) is covered by the `NO_HISTORY` rule at t = 0 but not by a constructed halt-at-tick-0 run.

## 9. Delta and standing

`ΔO = NONE / ΔS = NONE / ΔA = NONE`. OSA `REQUIRED, sessions are EPHEMERAL pointers; no new owner, carrier or writer`. CPOC: the reopen path reuses the Cut 9 resume covered by the Cut 10 witness; the UI adds no continuity semantics (`CPOC PASS` of the witness is not re-run).

```text
CUT 11: IMPLEMENTED / LOCAL VERIFY PASS
```

Next eligible cut: cut 12. Not started.

## 10. Repair of the independent audit `FAIL — CUT 11` (2026-11-05)

Scope: Cut 11 only. No change to engine, route, policies, checkpoint, Store, scenarios, reporting, api or CPOC; `elevator/` is byte-unchanged (code identity `0367c5f3…1f64`). Test count 337 → 342 (21 in `tests/web/`), full suite green, no `__pycache__`. The audit is not marked PASS here.

| Finding | Disposition |
| --- | --- |
| **C11-I-01 HIGH** same-Trace comparison | **Repaired.** `compare` takes the source session's `identity.trace_hash` as authority and checks each comparison engine's Run identity against it before running it; any difference renders `COMPARISON_TRACE_MISMATCH` (HTTP 409) with no table and no "same trace" claim. The displayed hash is the session's. Tests: the audit's probe (every comparison run given the same wrong Trace, agreeing with each other, still refused and stopped at the first run); a single wrong policy refused; the honest path shows the session's hash. |
| **C11-I-02 MEDIUM** `n_defined` | **Repaired.** `evaluation_view` keeps each metric's own `n_defined`; every aggregate shows `mean (n=…)`, the column `K` is labelled "seeds (K)". Test with K = 20 and one metric `n_defined` = 19. |
| **C11-I-03 MEDIUM** missing admitted features | **Partly repaired; three sub-items STOPPED, below.** Done: **3c** wait histogram (inline SVG; bars are counts of reporting's `wait_time` cells of the final or halted run's passengers table, layout only); **3e** per-seed p95 wait strip plot per pattern (the committed document's `per_seed` values, no new statistic); **3f** downloads (`/evaluate/experiment_results.json` serves the committed file's bytes; for a live Experiment, `/experiments/{id}/experiment_results.json` and `experiment_execution.json` serve the bytes produced once at run time, looked up by identifier in memory, never by a path; traversal and unknown ids refuse 404). |
| **C11-I-04 MEDIUM** `web -> domain` | **Repaired.** `web/app.py` imports only `api`, `checkpoint`, `harness`, `reporting`. Refusals from those boundaries are recognised by their declared `reason` attribute (a `guarded` wrapper) instead of importing `Refusal`; the code identity for a live Experiment is read from an Execution's own `run_identity`. Asserted by the import test. |
| **C11-I-05 LOW** `httpx` | **Disposition: documentation gap, reported, architecture unchanged.** `architecture.md` §6 is titled "Dependencies (complete list)" and lists tests as `pytest`, `hypothesis`; `httpx` (required by Starlette's `TestClient`) is not named, and `hypothesis` is listed though not installed. It is a test-only extra in `pyproject.toml`; no runtime edge is involved. |

### STOPPED sub-items of C11-I-03 (exact gaps, nothing implemented locally)

- **3a live results while RUNNING.** `reporting.summary`, `reproducible_surface` and `calibration` refuse a non-final Run (`ReportError: the History does not end in a run-standing event: the Run is not final`). No admitted surface yields wait/total metrics over "passengers completed so far"; adding one would change what reporting computes (a Cut 6 rule), and computing it in `web` is forbidden. Needs an owner decision (a reporting read helper for a partial Run, with its metric definitions).
- **3b projected stops per car.** ui §2.2 says "from the route projection"; that is `route.project`/the committed-stops derivation (authority rows 19, 20), `route` is not in `web`'s dependency row, and `Engine`, `api` and `reporting` expose no committed-stops accessor. Needs either an admitted `web -> route` edge or an engine/api read accessor.
- **3d scenario and seed controls.** Trace generation lives in `scenarios`; `web -> scenarios` is not admitted, `api` takes request rows only, and `harness` exposes generation only inside `execute_experiment` (no public "Trace for (pattern, seed)"). Needs an owner decision (an admitted edge or a harness/api function returning the generated rows).

### Standing after local repair

`/finish` remains a realization choice (a server-side repeat of the same `step`; the design does not forbid it). `ΔO = NONE / ΔS = NONE / ΔA = NONE`. Cut 12 stays blocked.

```text
CUT 11: IMPLEMENTED / LOCAL VERIFY PASS (C11-I-03 sub-items 3a, 3b, 3d STOPPED for the owner) / INDEPENDENT RE-AUDIT PENDING
```

## 11. Revision 7.4 (owner decision 011) and local verification against it

[Decision 011](../decisions/owner_decision_011_ui_contract_reductions.md) resolved the three STOPPED sub-items by reducing the admitted UI contract, not by adding edges or semantics: **3a** no partial live metrics (a RUNNING session shows current state only; metrics, histogram, observations, passengers table and calibration are final-run outputs); **3b** no projected-stop visualization (the committed receipt stays the cost-based explanation); **3d** no scenario or seed controls on the single-run screen (concrete request Trace only: built-in example or pasted rows; the Experiment page remains the scenario-based surface). `docs/ui_design.md` is re-admitted at `388fbbca9ab34edf8267d277e51e692467082a28ced3d851cc123dcb6a50fe6f`; `ΔO = NONE / ΔS = UI-ONLY / ΔA = NONE`. Architecture, semantics, scheduler, reporting and evaluation documents are unchanged.

C11-I-03 is therefore closed by the contract reduction plus the implemented 3c, 3e and 3f. **C11-I-05 (LOW)** is recorded as a documentation observation only: `httpx` is a test/development dependency required by Starlette's `TestClient`, creates no production dependency edge, affects no runtime authority; no further implementation.

The implementation already matched the reduced contract (no stops, no scenario or seed control, results only when final); one test was added (`test_running_screen_shows_current_state_only_and_the_form_has_no_scenario_controls`): the RUNNING screen has the tick, elevators, waiting and onboard lists and no results sections, the form has no scenario, pattern or seed field, and `web` imports no `route`, `scenarios` or `domain`.

Verification: `python3 -B -m pytest -q -p no:cacheprovider tests` → **343 passed** in 190.37 s (22 in `tests/web/`); governing digests verified (constitution `b34958f91e6d`, authority_model `4a066fb9fd8d`, semantics `821cb89dbbd4`, scheduler `25e7ec14ec3a`, evaluation `b8c29a3d47b5`, cpoc `65ca79366e4f`, ui `388fbbca9ab3`, architecture `a38da7e42867`, testing_contract `b0e78b99a824`, plan `26f6920ee56c`); `web/app.py` imports only `api`, `checkpoint`, `harness`, `reporting` (no new dependency edge); no `__pycache__`; `elevator/` unchanged (code identity `0367c5f3…1f64`).

```text
CUT 11: IMPLEMENTED / LOCAL VERIFY PASS / INDEPENDENT RE-AUDIT PENDING   (against Revision 7.4)
```

Cut 12 is not started and stays blocked until Cut 11 is re-audited against revision 7.4.

## 12. Repair of the experiment-download finding (independent Revision 7.4 re-audit)

Defect: live Experiment downloads were keyed by the *logical* `experiment_execution_id` (a hash of the definition and code identity), so re-running the same Experiment replaced the execution metadata behind the earlier link; and the fixed Experiment page offered no execution-metadata download.

Repair (`web/app.py`, `web/templates/evaluate.html`; nothing under `elevator/` changed, code identity `0367c5f3…1f64`):
- `experiment_results.json` stays logical: `/experiments/{experiment_execution_id}/experiment_results.json`, identical bytes for identical executions, no execution fact in it.
- `experiment_execution.json` is execution-specific and immutable: `/experiments/{experiment_execution_id}/executions/{execution_key}/experiment_execution.json`, where `execution_key` is the random `execution_id` of that Execution's first Run (a uuid4 minted per Execution, already in the harness's run facts). Each Execution's metadata is stored under its own key and never overwritten; both links are served from bytes stored at run time, by identifier, never by a path.
- Tests: Execution A and B of the identical Experiment share the logical id and the result bytes, have distinct links, distinct metadata and disjoint run execution ids; A's link still returns A's exact metadata after B ran; neither Execution's facts appear in the results; unknown keys, mismatched ids and traversal attempts return 404.

**Evidence gap (reported, not invented).** `ui_design` §3 asks for an `experiment_execution.json` download on the evaluation page, but the fixed Experiment's committed evidence contains only `experiments/default_experiment_results.json` (decision 010: committed evidence excludes execution facts; no `experiment_execution.json` was ever persisted for it). The fixed-Experiment page therefore offers the committed result download only and states that no execution metadata was persisted; none is fabricated. If the owner wants a persisted execution-metadata artifact for the fixed Experiment, that is a separate evidence decision.

Verification: full suite **344 passed**; `tests/web/` 23 passed; no `__pycache__`; `ui_design` digest `388fbbca…` and the other governing digests unchanged; `web` imports only `api`, `checkpoint`, `harness`, `reporting`. Closed findings (source-session Trace binding, `n_defined`, Revision 7.4 reductions, histogram, per-seed visual, dependency compliance, receipt and calibration fidelity) are exercised by the same suite. `ΔO = NONE / ΔS = NONE / ΔA = NONE`.

```text
CUT 11: IMPLEMENTED / LOCAL VERIFY PASS / INDEPENDENT RE-AUDIT PENDING
```

## 13. Revision 7.5 (owner decision 012)

The fixed-Experiment evidence gap of §12 is resolved by [decision 012](../decisions/owner_decision_012_ui_execution_metadata_downloads.md): no execution-metadata artifact is created for the fixed Experiment; the page exposes only `default_experiment_results.json` and states that no execution metadata was persisted; live executions keep both downloads under execution-specific keys; `docs/ui_design.md` §3 is revised so the metadata download applies only where metadata exists and is never fabricated (digest `8560cb3dfa77e5420296efbfc443630aeab1b51c9342e233a56fd01d91984c84`, `ΔO = NONE / ΔS = UI-ONLY / ΔA = NONE`). The implemented behaviour already matched; no code change. Codex re-audits only the two download findings.

```text
CUT 11: IMPLEMENTED / LOCAL VERIFY PASS / INDEPENDENT RE-AUDIT PENDING   (against Revision 7.5)
```
