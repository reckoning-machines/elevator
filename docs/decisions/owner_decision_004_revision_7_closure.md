# Owner Decision Record 004: Revision 7 Closure and Admission of the Governing Documents

Status: **PROPOSED 2026-11-05. NOT DECIDED. NOT ADMITTED. Nothing in this record has standing until the owner writes in §1 and §4.** This record proposes six bounded dispositions (D-23 to D-28) that revision 7 of the governing documents is written under, closing the seven findings of the independent revision-6 closure audit, and carries the admission text that would admit revision 7 at exact digests. Records 001 to 003 are historical and not amended; D-15 to D-22 of record 003 and D-11 to D-13 of record 002 stand as proposed and are not reopened here. R6-I-07 is editorial and carries no disposition. Shape as in [doctrine_adoption.md](../doctrine_adoption.md) §1.

Source: [audits/independent_revision_6_closure_audit.md](../audits/independent_revision_6_closure_audit.md);
[audits/revision_7_repair_record.md](../audits/revision_7_repair_record.md);
[current_work.md](../current_work.md) §6.

## 1. Owner's decisions (to be written by the owner)

*(Empty until the owner writes here. A disposition the owner overrides is
propagated to the governing documents as revision 8 before the closure
audit and admission.)*

## 2. Proposed dispositions

### D-23. Operational Log: in-memory buffer until durable binding, then one file

**Disposition.** Every Execution's Operational Log begins as an in-memory
buffer owned by the executing process (`EPHEMERAL`), with `op_seq` from 1
and `EXECUTION_STARTED` first. The Execution's evidence root is the Store
directory `<store>/<execution_id>/` for a Store-bound Execution (bound at
creation when checkpoint controls are set, or at a live session's first
explicit checkpoint), else the output location
`<output>/<run_id>/<execution_id>/` when an output directory was given.
When the root first exists the whole unflushed buffer is appended once, in
order, to `<root>/operational.jsonl`, and later records append there;
`op_seq` is continuous across the buffer, the flush, checkpoints and
resumes. An Execution that never obtains a root keeps its log in memory;
this affects no simulation fact and cannot be cited as CPOC evidence.
There is one log per Execution.

**Finding corrected.** R6-I-01 (MEDIUM): `simulate(output_dir=None)` and a
live session before its first checkpoint had a mandatory log and no
permitted carrier; late Store binding had no defined transfer.

**Consequences.** cpoc §2.2a, §3.2, §6 rows 33, 34; constitution §2, §4.5;
authority row 26, §6; evaluation §2, §3.2; ui §2.1; architecture; plan cuts
8, 9, 11; four tests.

**Negative test.** cpoc §6 row 33 (a live session's first checkpoint
flushes `EXECUTION_STARTED` and its `DIAGNOSTIC` records before the
checkpoint receipt, nothing duplicated) and row 34 (a never-bound
Execution writes no file and is refused as CPOC evidence).

**If overridden** (always write to a default location): a default root
would have to be invented and every `simulate` call would write to disk;
rejected as contrary to D-06 and D-22.

**Delta.** `ΔS`: the carrier lifecycle. `ΔO/ΔA`: none.

### D-24. Stale-writer and after-final witness construction; explicit time check

**Disposition.** The stale-writer witness starts from a `RUNNING` document
at `write_sequence = 1` with writer A holding token 1; A's admitted
checkpoint write advances the document to `write_sequence = 2` and A to
token 2; a simulated old holder of token 1 then attempts a write against
the still-`RUNNING` document and is refused `STALE_WRITER`. The after-final
witness is separate: after the admitted finality write, a write with the
current token is refused `WRITE_AFTER_FINAL`. The resurrection witness
chooses a `WAITING` passenger with `request_time + distance < t` and sets
`pickup = request_time`; load step 9 now states that every set time is
`< t`. The write-admission rule is unchanged.

**Finding corrected.** R6-I-02 (MEDIUM): the fixture asserted a later
sequence it never produced; row 24's fixed `pickup = 2` could fail step 9.

**Consequences.** cpoc §5 step 9, §6 rows 9, 10, 24; testing §7; W-D.

**If overridden.** None sensible; the rule is untouched and only the
fixtures change.

**Delta.** `ΔS`: the `< t` check made explicit. `ΔO/ΔA`: none.

### D-25. Sparse cross-parameter validity

**Disposition.** A `sparse` Scenario is accepted only if
`(num_requests - 1) * g + j <= 10^9` (when `num_requests >= 1`); otherwise
`INVALID_SCENARIO_PARAMETERS` naming `num_requests, g, j`, before any
draw. Times are never clipped and counts never reduced; the request-time
bound stays `10^9`. No other pattern can leave the domain (bounded
`horizon`, clamp, or `num_requests - 1`); the generator guards every
emitted time.

**Finding corrected.** R6-I-03 (MEDIUM).

**Consequences.** evaluation §6.3; testing §6; plan cuts 7, 8.

**Negative test.** `num_requests = 1002, g = 10^6, j = 0` refuses;
`1001` is accepted with last time exactly `10^9`.

**If overridden** (clip or reduce): prohibited by the owner; broadening
the time domain would reopen D-21.

**Delta.** `ΔS`: one refusal. `ΔO/ΔA`: none.

### D-26. Experiment outputs: reproducible result surface and execution metadata

**Disposition.** `experiment_results.json` holds the definition, its hash,
the experiment execution id, code identity, and per `(scenario, seed,
policy)` the `run_id`, Trace hash, outcome and summary, plus the
aggregates with `n_defined`, `n_pairs`, `halted_count` and paired
comparisons; it is byte-identical for every execution of the same
definition under the same code and holds no per-Run `execution_id`, path,
timestamp or pid. `experiment_execution.json` holds those and is outside
every equality claim. Comparisons and the UI render from the result
surface.

**Finding corrected.** R6-I-04 (MEDIUM).

**Consequences.** evaluation §7.3, §7.4; authority rows 32 to 34, §6;
constitution §2; ui §3; testing §4; plan cut 8.

**Negative test.** `experiment_reexecution_identical` (result surface
byte-identical; metadata differs only in execution ids, paths, timestamps)
and `experiment_results_surface_excludes_execution_facts`.

**If overridden** (one file): random ids would have to be excluded by a
normalisation rule at comparison time; rejected as the same defect in
another place.

**Delta.** `ΔS`: equality scope. `ΔO/ΔA`: none.

### D-27. Empty-run metric semantics

**Disposition.** For a `COMPLETED` Run with `n = 0`: counts are defined and
zero (`n`, `completed`, `unserved`, `makespan`, `deferred.count`,
`wrong_way.count`; `elevator_utilisation` is defined because its
denominator is at least one tick); every share or distribution with a
zero denominator is `null` (`tail_share`, `wrong_way.mean_extra`,
`tail_ratio`, `wait.*`, `total.*`, `travel.mean`). In Experiment
aggregation, always-defined counts participate with value 0; `tail_share`
and the other shares and distributions are conditional; nulls are excluded
and never zero; `n_defined` and `n_pairs` are reported.

**Finding corrected.** R6-I-05 (MEDIUM): §4.3 made counts null and §7.4
made `tail_share` zero.

**Consequences.** evaluation §4.3, §7.4; testing §6; ui §3.

**Negative test.** `empty_population_summary` (exact bytes) and
`experiment_null_aggregation` (the empty run contributes zero counts and
an undefined `tail_share`).

**If overridden** (`tail_share = 0` for `n = 0`): it becomes
always-defined and a one-seed empty cell reports a defined zero share;
either rule is coherent, this one is proposed.

**Delta.** `ΔS`: one consistent rule. `ΔO/ΔA`: none.

### D-28. Plan cut-local CPOC obligation split

**Disposition.** The continuation types `Snapshot`, `HistoryPrefix` and
`HistoryVerifier` are implemented in cut 9 with the checkpoint module, not
in cut 1. cpoc §6 carries a "Cut" column: rows 1 to 28 and 33 are cut-9
local continuity-negative tests (checkpoint and store modules plus an
in-process engine); rows 29(a), 30, 31, 32 and 34's qualification half are
cut-10 witness tests; row 29(b) is a cut-11 UI test. Each cut's test list
names only tests whose inputs that cut and earlier cuts produce.
`LOCAL VERIFY PASS`, `CPOC PENDING` and `CPOC-QUALIFIED` are unchanged.

**Finding corrected.** R6-I-06 (MEDIUM).

**Consequences.** plan cuts 1, 8, 9, 10, 11 and cross-cut obligations;
cpoc §6; testing §7, §8; architecture §8.

**If overridden.** Any mapping that keeps each test with its dependencies
is acceptable; this one is proposed.

**Delta.** none.

## 3. What is unchanged from revision 6

Everything the owner's closure posture lists as settled, and the liveness
bound `T_last + 2P(F-1)`.

## 4. Admission text (to be written by the owner after the bounded closure audit)

Admission admits the exact bytes of the files below at the digests below.
If a digest differs at the time of admission (after a repair the closure
audit requires, or after an override above), this table is regenerated
before the admission text is written. After admission, the admitted files
are not edited to change their status lines; this record supersedes them.

| File | SHA-256 (revision 7 as proposed, 2026-11-05) |
| --- | --- |
| `docs/constitution.md` | `9c89f998611dd55afed420fa1d3d7667a40b82509f0d461bf05f95b664897988` |
| `docs/authority_model.md` | `6de26ece4c4350b3de20a6018688d2cdb105f320ae94bae9c1b16354f13cb471` |
| `docs/simulation_semantics.md` | `54b62d31b29f681b18aa3e1c3452e08b94ffa8ff8c46fe67f651ce8480b6bc59` |
| `docs/scheduler_design.md` | `8917d7cbad7bace0adef7163b8a3129ca1b55f810f8e4a8f73a096629e9d0df4` |
| `docs/evaluation_design.md` | `113340d202aafe4d76ca2da7eb88ac60049ff7376cf8d83be8da6d5c50a68ba3` |
| `docs/cpoc_design.md` | `24b20e7f0181d394d327eed70f7e0997b6528d539ed8e0cd4c021b2881edf456` |
| `docs/ui_design.md` | `3a2690d1a410544f0537ffb79636d8bf5220215c064d46fae06a41a42b8e2f74` |
| `docs/architecture.md` | `963c32a8927ab48722afcf08ca51d7301de108907ebcf7dc6bee623880bfb8ce` |
| `docs/testing_contract.md` | `084bb2b3b8b76f4bad1e4e776ab642334fd91c2dbfd6391d99dfebdf2400dcc6` |

Proposed wording, for the owner to adopt or amend:

```text
I decide D-23 to D-28 as recorded in §1, and confirm D-15 to D-22 of
record 003 and D-11 to D-13 of record 002.
I admit the governing documents at revision 7, at the digests in §4,
as the design baseline. Implementation remains not authorized until the
implementation plan is admitted by a separate record.
```

Preconditions the owner should see satisfied before writing it: one
bounded independent closure audit of revision 7 (R6-I-01 to R6-I-07 each
`CLOSED`; checklist checks 19, 26, 28 to 32 and 35 passing) recorded in
`docs/audits/` with `OSA PASS`; no OPEN marker in the governing documents.

## 5. What this record does not do

It does not admit the implementation plan, authorize any cut, certify
anything, claim `OSA PASS` or `CPOC PASS`, or grade revision 7. Its
cumulative Constitutional Delta relative to revision 6 is `ΔS` only, as
listed above; relative to revision 7 as drafted it is `0/0/0`.
