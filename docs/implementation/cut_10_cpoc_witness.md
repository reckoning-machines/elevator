# Cut 10 implementation record: the CPOC witness

Date: 2026-11-05. Governing design: Revision 7.3. Evidence only (plan cut 10: "none; evidence only").

```text
CUT 10: IMPLEMENTED / LOCAL VERIFY PASS / CPOC PASS
```

## 1. Baseline

Governing and plan digests unchanged (constitution `b34958f91e6d`, authority_model `4a066fb9fd8d`, semantics `821cb89dbbd4`, scheduler `25e7ec14ec3a`, evaluation `b8c29a3d47b5`, cpoc `65ca79366e4f`, ui `b22ea1164403`, architecture `a38da7e42867`, testing_contract `b0e78b99a824`, plan `26f6920ee56c`). Cut 9 was 286 passing tests.

## 2. Files

- New: `tests/cpoc/witness/{__init__.py,harness.py,test_witness.py}`; fixture `tests/cpoc/witness/fixtures/bursty_seed7_F10_N3_C4.csv` (sha256 `d6f98ed53f03c212b68a2c443678af4a28cea0da16eb1011f2d7447a2803da0d`, committed with its hash constant); evidence record `docs/cpoc/witness_2026-11-05_0367c5f3a8f28f956743b6806abffd0e2d45e83dc33111df6dc4662503881f64.md`.
- Production change (one, flagged): `elevator/cli.py` gains `_run_simulate_instrumented`. Before, `simulate --witness-instrumentation` without a Store silently ignored the flag, so the reference Execution R could not carry the DIAGNOSTIC records cpoc §4.2 step 7 requires of R's log. The new path is the same Execution as `api.simulate` (no document; log bound to the output location only when one is given) plus the flag's documented per-tick DIAGNOSTIC. `api.simulate`, the engine, checkpoint and operations are unchanged. It adds no owner, carrier, writer or transition.
- The witness's qualifier (`harness.qualify`) is test-side; no production "harness" gained a witness role.

## 3. Witness (cpoc §4.2), both policies

Fixture: the committed CSV (the Trace of bursty seed 7, 25 requests, horizon 20), F=10, N=3, C=4, t=12. These parameters were fixed in Cut 9 by the stated t=12 properties, before any witness ran, and not tuned afterwards. The test asserts, for both policies, one ONBOARD, one WAITING, a Request after t=12, and a WAITING passenger with request_time + distance < 12 (row 24), and that the file denotes the same Run as the generated Trace.

Sequence (real processes, `python -B`, B and every child started with `PATH` only):
1. R: `simulate --requests FIXTURE ... --witness-instrumentation --out out` (no Store) to completion.
2. A: `simulate ... --store S --checkpoint-at 12 --pause-after-checkpoint --witness-instrumentation --out out`; CHECKPOINT_WRITTEN with write_sequence 1; A blocks.
3. SIGKILL A; wait; return code -9, PID gone; document re-read hashes to the receipt's d_A; standing RUNNING, snapshot.t 12.
4. B: `resume --store S --resume e_A --witness-instrumentation --out out` only (no fixture, seed, policy, document path or environment); B's pid differs from A's, R's and the test's.
5. B loads (eleven verifications, LOAD_ADMITTED), RESUMED(12), runs ticks 12..final, finality write_sequence 2, FINALITY_WRITTEN, EXECUTION_ENDED, outputs to `out/<run_id>/e_A/`.

## 4. Equality and evidence results (both policies)

- Simulation History: tick_records for t >= 12 identical; events after the checkpoint prefix identical with sequence numbers; document prefix + continuation == R's complete History; both History files byte-identical.
- Reproducible Output Surface: all eight files byte-identical, `run_identity.json` included; no execution fact in any surface file (N18 scan); `execution_metadata.json` compared for shape (differs only in execution_id, pid, store_id, timestamps).
- Row 29(a): the position export regenerated independently from B's TickRecords equals R's `elevator_positions.csv`.
- No replay: B's DIAGNOSTIC records name ticks 12..final only, first 12, count final-12+1 (cost_based 20, round_robin 25); A's 0..11; R's 0..final; disjoint sets.
- LOAD_ADMITTED: document sha256 == d_A; snapshot_hash == constructed_state_hash == H_s; history_hash == H_h; store_id and execution_id match.
- Operational Log: op_seq 1..n contiguous, one execution_id; A's prefix (STARTED, 12 DIAGNOSTIC, CHECKPOINT_WRITTEN) appears once and first; B's STARTED, LOAD_ADMITTED, RESUMED, DIAGNOSTICs, FINALITY_WRITTEN, ENDED follow; R's is STARTED, DIAGNOSTICs, ENDED; output-location log is a byte copy of the Store's; none of it appears in History or surface.
- Finality: document COMPLETED, write_sequence 2, no snapshot; resume refuses `EXECUTION_FINAL` (also with a new output directory, which is never created); write-after-final with the current token refuses `WRITE_AFTER_FINAL` on a Store copy; the final document is byte-identical after each refusal.
- Architecture: no History-to-state path in the package; the planted cheat fixture is still detected.

## 5. Negative witnesses and controls

Rows 29(a), 30 (argv and environment of B contain nothing but the admitted flags; EXECUTION_STARTED payload has code_identity and pid only), 31 (process-local run, and a run whose first process was never killed: both refused as evidence), 32 (real SIGKILL between rename and receipt, via a test-side patch in a child interpreter: the document loads lawfully, the run completes, qualification is `EVIDENCE_INCOMPLETE`), 34 qualification half (`api.simulate(output_dir=None)` writes no file, its surface equals a bound Execution's, refused `REFUSED_NEVER_BOUND`). Rows 1 to 28 and 33 ran in Cut 9; row 6 is the stated limit, row 7 admitted; row 29(b) is Cut 11.

Controls that fail the witness: a replay-from-zero cheat in a fresh process (same History, caught by the anti-recomputation evidence: ticks below 12 and the count); a skipped and a duplicated post-checkpoint tick; wrong floor, wrong heading and wrong passenger standing restored through production `Engine.restore` (each diverges or is refused, with a faithful-restore positive control equal to R); a mutated Snapshot with the hash recomputed (`STATE_HISTORY_MISMATCH`) and not (`STATE_INCONSISTENT`), a mutated Trace (`TRACE_HASH_MISMATCH`) and configuration (`CONFIG_HASH_MISMATCH`), each refused by a real fresh resume that continues nothing and leaves the document as found; a different Trace yields a different run_id and a different surface; an operational fact leaked into the surface fails comparison and the leak scan.

## 6. Verification

```text
python3 -B -m pytest -q -p no:cacheprovider tests   -> 321 passed in 188.11s (286 + 35)
tests/cpoc/witness/test_witness.py                   -> 35 passed (both policies), about 7 s
```

0 failed, 0 skipped, 0 errors; no `__pycache__` in `elevator/` or `tests/`. Code identity `0367c5f3a8f28f956743b6806abffd0e2d45e83dc33111df6dc4662503881f64` (changed from Cut 9's by the CLI addition; the Cut 8 committed-evidence test, which checks code-identity-derived ids for consistency, passes).

## 7. Delta, applicability, standing

`ΔO = NONE / ΔS = NONE / ΔA = NONE`. OSA `REQUIRED, evidence of the continuation boundary` (no new fact or owner). CPOC `REQUIRED, PASS`: bounded to the supported local Store/process model (cpoc §4.1); hash equality is value equality, not provenance; no claim of general crash consistency or distributed fault tolerance.

```text
CUT 10: IMPLEMENTED / LOCAL VERIFY PASS / CPOC PASS
```

Cuts 3 and 9 are lifted from `CPOC PENDING` to `CPOC PASS` by this witness; cut 11 stays `CPOC PENDING` until it exists. Next eligible cut: cut 11 (web UI). Not started.
