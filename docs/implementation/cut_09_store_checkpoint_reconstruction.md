# Cut 9 implementation record: Store, checkpointing, reconstruction, finality

Date: 2026-11-05. Governing design: Revision 7.3 (decisions 006 to 010). Standing:

```text
CUT 9: IMPLEMENTED / LOCAL VERIFY PASS / CPOC PENDING
```

## 1. Baseline

Governing digests unchanged (first 12 hex): constitution `b34958f91e6d`, authority_model `4a066fb9fd8d`,
simulation_semantics `821cb89dbbd4`, scheduler_design `25e7ec14ec3a`, evaluation_design `b8c29a3d47b5`,
cpoc_design `65ca79366e4f`, ui_design `b22ea1164403`, architecture `a38da7e42867`, testing_contract `b0e78b99a824`,
plan `26f6920ee56c`. Cuts 1 to 8 were green (231 tests) before this cut.

## 2. Files

- New: `elevator/checkpoint.py`; `tests/cpoc/{fixture.py,scan.py}`, `tests/cpoc/local/test_{negative_witnesses,write_admission,resume,structure,processes}.py`, `tests/cpoc/cheats/history_cheat.py` (a deliberately cheating fixture, never imported by the package).
- Changed: `elevator/engine.py` (admitted hooks only: `ElevatorState`, `PassengerState`, `EngineState`, `Engine.state`, `Engine.restore`, `Engine.set_diagnostic`, single `_emit` after a fully committed tick; no tick-order, route or authority change); `elevator/operations.py` (`first_op_seq`, `bind_existing_root`, `copy_to`, `read_log`, `resume_execution`); `elevator/cli.py` (`store init`, `resume`, `simulate --store --checkpoint-at --checkpoint-every --pause-after-checkpoint --witness-instrumentation`); `tests/unit/test_engine.py` (public-surface set includes the three admitted hooks); `tests/unit/test_policy_resolver.py` (adds `checkpoint.py` to the no-policy-class-name module list).
- Untouched: `api.py` (`api.simulate` unchanged), `harness.py`, `reporting.py`, `scenarios.py`, `policies.py`, `route.py`, `domain.py`.

## 3. Contract as built

- Store: `<store>/store.json` (`store_id` uuid4, schema version 1, created exclusively, never overwritten); `<store>/<execution_id>/run.json` (atomic replace via `run.json.tmp`), `operational.jsonl`.
- Continuation Document: exactly the cpoc fields; canonical bytes (sorted keys, no whitespace, integers only); snapshot present iff RUNNING; no self-hash, timestamp or operational record.
- Write admission by `write_sequence` token: `MALFORMED`, `EXECUTION_MISMATCH`, `WRITE_AFTER_FINAL`, `STALE_WRITER`; no last-writer-wins. Receipt order: write tmp, flush, fsync, rename, read back and hash the bytes at the path, append receipt, flush. A refused write leaves the document byte-identical and writes no receipt; a writer halts itself after a refusal.
- Finality per Execution: COMPLETED/HALTED document with `final`, no snapshot, complete History; any later write refuses `WRITE_AFTER_FINAL`; load refuses `EXECUTION_FINAL` (step 7).
- Load: `establish_code_identity()` first (`UNSUPPORTED_EXECUTION_ENVIRONMENT`), then the eleven steps in order with the named reasons; `HistoryVerifier` is isolated and discarded before `parse_snapshot` and `construct_state`; `construct_state(Snapshot)` is the only state constructor and type-checks its argument.
- Resume: reuses `execution_id`, continues `op_seq`, appends this process's EXECUTION_STARTED, LOAD_ADMITTED, RESUMED; policy rebuilt only by `make_policy`; `Engine.restore` joins the snapshot to the Trace and attaches the History unchanged.
- LOAD_ADMITTED payload: document_sha256, snapshot_hash, history_hash, constructed_state_hash (== snapshot_hash), store_id, execution_id.

## 4. Realization choices (no admitted name or rule existed; flagged, not new authority)

1. A missing document with a non-None token refuses `STALE_WRITER`.
2. The log is opened or appended on resume only after all eleven verifications pass; a torn or malformed existing log makes resume refuse (OperationsError); a missing log is recreated at op_seq 1.
3. `--checkpoint-every k` writes at positive multiples of k; the first boundary of a resumed process is skipped; `--pause-after-checkpoint` blocks after the first write; `--store` requires a checkpoint control and vice versa (exit 2).
4. CheckpointRefusal maps to CLI exit 3 (UNSUPPORTED to 6); an existing Store or output exits 5.
5. Step 6 hashes are computed over the embedded dictionaries; `drive()` writes finality only if a document was written.
6. Fixture (test data only): bursty, seed 7, F=10, N=3, C=4, num_requests=25, horizon=20, checkpoint at t=12. Not the cut-10 witness fixture.

## 5. Evidence

- Negative witnesses cpoc §6 rows 1 to 28 (cut-9 rows; 9 and 10 in `test_write_admission.py`, 15 and 16 in `test_processes.py`, 33 in `test_resume.py`): each constructed as its row says, asserting reason and step; hashes recomputed by an independent hashlib/json implementation. Row 6 is recorded as the design's stated limit.
- Named tests: write_admission_stale_writer, write_admission_after_final, receipt_hash_matches_path, operational_log_flush_at_binding, operational_log_op_seq_continuous, independent_executions_same_run, history_verifier_isolated, no_history_to_state_path_in_package (structural scan finds all planted cheats and none in the package), construct_state structural, checkpoint_at_zero, finality on completion and halt, execution_environment_contract.
- Resume-not-replay: a spy on `Engine._tick` sees no tick during reconstruction and first tick 12; a replay-from-zero cheat executes ticks 0 to 11 and is detected by the same spy.
- Fresh process: process A SIGKILLed after its checkpoint (return code -9); a distinct-pid process B reconstructs, executes ticks 8 to final only, writes finality; a second resume refuses `EXECUTION_FINAL`. This is a local test, not the cut-10 witness: it does not compare against an uninterrupted Execution under the witness framework.
- `checkpoint_roundtrip_property` is labelled NOT CPOC evidence.

## 6. Verification

```text
python3 -B -m pytest -q -p no:cacheprovider tests   -> 286 passed in 182.57s
```

231 prior + 55 new (25 negative witnesses, 9 write admission, 12 resume, 3 structure, 6 processes). 0 failed; no `__pycache__` under `elevator/` or `tests/`. Code identity: `4b8747dab8da078d2a777f21eed649942394e249abc23454547c9359282fa0ce`. Note: Cut 8 evidence ids derived from code identity are checked for consistency by its test, which passes.

## 7. Delta and applicability

`ΔO = NONE / ΔS = NONE / ΔA = NONE`. OSA `REQUIRED, Store/Continuation Document, write admission, load and reconstruction`. CPOC `REQUIRED, but PENDING: local continuity machinery and negative witnesses verified; the process-death witness and byte-identical equivalence against an uninterrupted reference belong to cut 10`. Nothing is certified.

## 8. Standing

```text
CUT 9: IMPLEMENTED / LOCAL VERIFY PASS / CPOC PENDING
```

Next eligible cut: cut 10 (CPOC witness). Not started.
