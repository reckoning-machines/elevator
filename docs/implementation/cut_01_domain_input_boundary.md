# Cut 1 Implementation Record: Domain Model, Input Normalization, Code Identity

Status: **IMPLEMENTED / LOCAL VERIFY PASS. 2026-11-05.** Evidence record for plan cut 1 under the admitted plan ([decision 007](../decisions/owner_decision_007_implementation_plan_admission.md)) against the admitted design baseline ([decision 006](../decisions/owner_decision_006_revision_7_1_admission.md)). No later cut was started. Nothing is certified; no CPOC witness exists.

## 1. Admitted baseline

- Governing design: revision 7.1, admitted by record 006 at these digests,
  re-verified unchanged after this cut:

| File | SHA-256 |
| --- | --- |
| `docs/constitution.md` | `b34958f91e6d4c5fc32f74fe96be14b6287ca80abdde951e77eb2e730cb659c3` |
| `docs/authority_model.md` | `4a066fb9fd8d85ffa9175501fddf9992cdaa42e8f644ffa07893847f7daf384e` |
| `docs/simulation_semantics.md` | `94a3506932df8e00d663fd64d0f929970d83896e969010ffcf270ce1dcafeb87` |
| `docs/scheduler_design.md` | `25e7ec14ec3a46127430ca4d0bdd9e01d46d0ba1024d3ee10bbbf54cbddba881` |
| `docs/evaluation_design.md` | `b8c29a3d47b5be8fce9f517f931bb6848508a0a595254ff8187832cbeb7c1fa1` |
| `docs/cpoc_design.md` | `65ca79366e4f5a6c970ba2c59a0f01ff976519840e6219a5de26aa5f6e566d58` |
| `docs/ui_design.md` | `b22ea1164403bebc733aba986dea5b25b5ee9ad6e12e3e55a55cfb146382366c` |
| `docs/architecture.md` | `31f16b7d18cdd8cbfdf18df6a94de57fc061ff413291789836d4b5fe673ab9e6` |
| `docs/testing_contract.md` | `9c03308ab1f0df65a8f2540d77a20168b301e66d8b095dc4af106206841d602b` |

- Implementation plan: admitted by record 007 at
  `6254fffaea4c48582ae20733a5995ca6511a24f9d057de0e84efabfb82138d84`.

## 2. Scope checklist (from the admitted cut-1 row)

| Item | Plan text | Realised |
| --- | --- | --- |
| Governing contracts | constitution §2, §4.1, §12; semantics §1, §6; evaluation §2; architecture §4 | yes; cited in module docstrings |
| Authorized files | `elevator/domain.py`, `elevator/api.py` (`normalize_requests` only) | yes; plus the package marker `elevator/__init__.py`, `pyproject.toml` (pytest configuration, no dependencies) and the test files |
| Authority affected | domain-level value types for rows 1 to 6, 10 to 15, 17, 18, 41; `normalize_requests`; execution-contract check and code identity (row 4); no writer of runtime state | yes; every type is a frozen dataclass; no module-level mutable state; no persistence |
| Not pulled forward | `Snapshot`, `HistoryPrefix`, `HistoryVerifier` (cut 9); `operations`, `simulate`, `create_engine` (cut 8); route, engine, policies, reporting, scenarios, harness, checkpoint, UI | none present |
| Exact tests | the twelve identifiers in the cut-1 row | all present (§4) |
| Refusal behaviour | invalid input refuses with position, `source_id` and reason; an unsupported environment refuses to start | `Refusal(reason, detail, positions, source_id)`; `UNSUPPORTED_EXECUTION_ENVIRONMENT` from `check_execution_environment` |
| Verification evidence | pytest counts | §5 |
| Expected delta | NONE | NONE (§6) |

## 3. Files created

| File | Content |
| --- | --- |
| `elevator/__init__.py` | package marker and docstring |
| `elevator/domain.py` | `Refusal`; canonical JSON and SHA-256; `Request`, `Trace` (stable sort, `trace_hash` over `[time, source_id, origin, dest]` rows); `normalize_requests` (row shapes, type normalisation, validation in the admitted order, 100000-row limit); `Configuration.create` (domain bounds, initial floors, policy name, cost-based parameter defaults fixed at creation, `0..10^6`), `validate_with_trace` (`max_ticks` at most the default bound), `configuration_hash`; `default_max_ticks` (`T_last + 2P(F-1)`); `Standing`, `Heading`, `Passenger` (no estimate field), `Elevator` (floor, heading); `SimulationEventKind`, `SimulationEvent` (receipt only meaningful on `ASSIGNED`), `TickEntry`, `TickRecord`, `OperationalRecordKind`, `OperationalRecord` (value only), `SimulationHistory` (refuses anything but events and tick records); `code_identity` (sorted path, length, bytes encoding), `check_execution_environment` (`sys.flags.dont_write_bytecode`, no `__pycache__` in the package), `establish_code_identity`, `detect_code_identity_drift` (returns a `CODE_IDENTITY_DRIFT` record value); `RunIdentity`, `bind_run` (`run_id = sha256(canonical [configuration_hash, trace_hash, code_identity])`) |
| `elevator/api.py` | re-exports `normalize_requests`; `simulate` and `create_engine` are cut 8's |
| `pyproject.toml` | package metadata; pytest `testpaths`, cache provider disabled; no runtime dependencies |
| `tests/unit/test_domain.py` | the §1 tests of the cut-1 row |
| `tests/invariants/test_history_types.py` | `no_operational_record_in_history` (type half) |
| `tests/reproducibility/test_serialisation.py` | `canonical_serialisation_stable`, `code_identity_tracks_package_bytes`, `execution_environment_contract` |
| `tests/__init__.py`, `tests/unit/__init__.py`, `tests/invariants/__init__.py`, `tests/reproducibility/__init__.py` | package markers |

Files changed: none of the admitted governing documents or the admitted
plan. `AGENTS.md`, `README.md` and `docs/current_work.md` were updated to
the implementation standing (records 006 and 007 supersede the admitted
files' draft status lines, which were not edited).

## 4. Tests implemented (contract identifier → function)

| Contract identifier | Function | Section |
| --- | --- | --- |
| `same_floor_source_destination_refused` | `tests/unit/test_domain.py::test_same_floor_source_destination_refused` | §1 |
| `missing_source_id_refused` | `::test_missing_source_id_refused` | §1 |
| `duplicate_source_id_refused` | `::test_duplicate_source_id_refused` | §1 |
| `source_id_normalization_cases` | `::test_source_id_normalization_cases` | §1 |
| `configuration_domain_refusals` | `::test_configuration_domain_refusals` | §1 |
| `source_id_preserved_in_outputs` (mapping half) | `::test_source_id_preserved_in_outputs` | §1 |
| `horizon_halt_reasons_distinct` (refusal half) | `::test_horizon_halt_reasons_distinct` | §1 |
| `receipt_never_on_passenger` | `::test_receipt_never_on_passenger` | §1 |
| `no_operational_record_in_history` (type half) | `tests/invariants/test_history_types.py::test_no_operational_record_in_history` | §2 |
| `canonical_serialisation_stable` | `tests/reproducibility/test_serialisation.py::test_canonical_serialisation_stable` (also asserts hash sensitivity of the Trace hash, the Configuration hash and `run_id` to their consequential inputs) | §6 |
| `code_identity_tracks_package_bytes` | `::test_code_identity_tracks_package_bytes` | §6 |
| `execution_environment_contract` | `::test_execution_environment_contract` (subprocesses with and without `-B`; a `__pycache__` inside a package copy; drift after establishment, reported as a record value since the log carrier is cut 8's) | §6 |

One additional structural assertion, not a contract identifier:
`test_public_boundary_is_normalize_requests` proves the cut-1 expected-file
obligation that `elevator/api.py` exposes `normalize_requests` and nothing
else parses rows. The "output half" of `source_id_preserved_in_outputs`
and the "halt half" of `horizon_halt_reasons_distinct` are cuts 6 and 3
respectively and were not implemented.

## 5. Verification evidence

Command (under the supported execution contract):

```text
python3 -B -m pytest -v
```

Output (tail):

```text
collected 13 items
tests/invariants/test_history_types.py::test_no_operational_record_in_history PASSED
tests/reproducibility/test_serialisation.py::test_canonical_serialisation_stable PASSED
tests/reproducibility/test_serialisation.py::test_code_identity_tracks_package_bytes PASSED
tests/reproducibility/test_serialisation.py::test_execution_environment_contract PASSED
tests/unit/test_domain.py::test_same_floor_source_destination_refused PASSED
tests/unit/test_domain.py::test_missing_source_id_refused PASSED
tests/unit/test_domain.py::test_duplicate_source_id_refused PASSED
tests/unit/test_domain.py::test_source_id_normalization_cases PASSED
tests/unit/test_domain.py::test_configuration_domain_refusals PASSED
tests/unit/test_domain.py::test_source_id_preserved_in_outputs PASSED
tests/unit/test_domain.py::test_horizon_halt_reasons_distinct PASSED
tests/unit/test_domain.py::test_receipt_never_on_passenger PASSED
tests/unit/test_domain.py::test_public_boundary_is_normalize_requests PASSED
============================== 13 passed in 0.56s ==============================
```

Counts: 13 passed, 0 failed, 0 skipped, 0 errors, 0 deselected.
Interpreter: CPython 3.12.3 (`/Users/jedgore/.pyenv/versions/3.12.3/bin/python3`), pytest 8.4.1.
No `__pycache__` directory exists under `elevator/` or `tests/` after the run.
Code identity of the governed package at this standing:
`2b049a80a502e8f389f96183907fd2de5d626535e4ac96d77b7d729d0b9b5401`.

## 6. Constitutional / Semantic / Authority Delta

`ΔO = NONE / ΔS = NONE / ΔA = NONE`. Every type realises an object the
constitution §2 names; every rule realises evaluation §2, semantics §1/§6/§8.3
or architecture §4 as written. Implementation choices that are
realisations, not reinterpretations, recorded for the reviewer:

- a mapping row must have exactly the four admitted keys, and `bool`
  values are refused, under evaluation §2's "anything else refuses
  `INPUT_INVALID`";
- cost-based parameter defaults that depend on `F` (scheduler §6.3) are
  filled at `Configuration.create`, so the Configuration and `run_id` are
  fully determined by the Configuration's fields;
- the `max_ticks` ceiling is checked when the Configuration is bound to a
  Trace (`validate_with_trace`, called by `bind_run`), since the default
  bound depends on the Trace;
- `detect_code_identity_drift` returns the `CODE_IDENTITY_DRIFT` record as a
  value; appending it to a log is the `operations` module's (cut 8).

No undeclared fact, carrier, writer, selector or transition was needed.

## 7. Applicability

- OSA: `REQUIRED` for the facts constructed (rows 1 to 6, 41); the tests
  above are the evidence.
- CPOC: `NOT APPLICABLE` (value types and pure checks; no persistence, no
  continuation, no history read).

## 8. Worktree standing

`git status`: every file untracked (`AGENTS.md`, `README.md`, `docs/`,
`elevator/`, `pyproject.toml`, `tests/`); no HEAD commit exists. Nothing
was committed: repository instructions do not authorize committing.

## 9. Resulting standing

```text
CUT 1: IMPLEMENTED / LOCAL VERIFY PASS
```

Next eligible cut under the admitted plan: cut 2 (route policy). Not
started.
