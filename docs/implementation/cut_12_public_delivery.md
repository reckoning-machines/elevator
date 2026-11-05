# Cut 12 implementation record: public delivery

Date: 2026-11-05. Documentation, packaging and presentation only. No change to `elevator/`, `web/` code or any governing document (the code identity is `0367c5f3a8f28f956743b6806abffd0e2d45e83dc33111df6dc4662503881f64`, unchanged since Cut 10).

```text
CUT 12: IMPLEMENTED / LOCAL VERIFY PASS
```

## 1. Baseline

Governing and plan digests unchanged (ui_design at the revision 7.5 digest `8560cb3d…`). Cut 11 was 344 tests before this cut.

## 2. Public files

- `README.md` (rewritten): the memo, with the demo screenshot after the introduction and before the architecture section. Sections are Problem, Simulation semantics, Architecture, Scheduling policies, Evaluation, Results, Calibration, Correctness, Restart continuity, Web demo, Running the project, Time spent, Assumptions and tradeoffs, Next steps.
- `docs/design.md` (new): the public design document. Four Mermaid diagrams (tick, Cost Based decision, paired evaluation, checkpoint and resume), the architecture diagram is in the README, and worked examples W-A, W-B, W-C, W-G and the W-D continuation sequence.
- `docs/walkthrough.md` (new): nine-section presentation outline, a whiteboard version and expected questions.
- `docs/README.md` (new): index that separates the start-here documents, the evidence and the development record. The governing documents stay where they are because the admitted decision records name them by exact path and digest, and moving them needs an owner decision. The README links only to the design document, the walkthrough and this index.
- `docs/images/web_demo.png` (new): one cropped screenshot of a finished Cost Based session on the built-in example, with the history view at tick 12 and the policy comparison loaded, captured with headless Chrome against the running demo.
- `examples/requests.csv` (new): the 25-request sample in the brief's row format.
- `tests/docs/test_public_delivery.py` (new, 7 tests).
- `web/templates/_tick.html`: the history shaft is wrapped in a block so the screenshot lays out cleanly (presentation only).

## 3. Evidence used

Every number in the README comes from `experiments/default_experiment_results.json` (the results table, the paired counts, the 92 and 68 capacity deferrals, the means 5.252 and 7.245), the committed calibration test case (`tests/unit/test_reporting.py`, errors +10 and +10), the sweep count in `test_calibration_zero_error_for_untouched_elevators` (977 rows, 374 untouched, 603 touched, 30 differing), the `-66 / -52` case in `docs/implementation/cut_05_cost_based_scheduler.md`, the 25-request demo (final ticks 36, 43, 31, from a real server run) and the restart witness record `docs/cpoc/witness_2026-11-05_0367c5f3…md`. The test suite compares the table and each paired statement against the JSON.

## 4. Verification

- `tests/docs/` runs the README simulate command through the CLI and through `elevator.api.simulate` on the sample file and compares the position log, starts `python -B -m web` and fetches the page, resolves every relative link, compares the results table and paired claims with the committed JSON, checks the evidence files exist, checks the diagram kinds, and checks the style rules (keyboard characters only, no listed marketing phrases, no semicolons or colons in prose).
- All five Mermaid diagrams were rendered with the real Mermaid library (10.9.1) in headless Chrome without errors.
- A clean copy of the repository in a fresh virtual environment, installed with the README's `pip install` line, ran the README simulate command and `tests/docs` and `tests/web` (30 passed) with no `__pycache__`.
- The README's Experiment command was executed (540 runs, no halts). Its aggregates, definition and per-run summaries equal the committed ones and only the code identity differs, which the README states.
- Full suite `python3 -B -m pytest -q -p no:cacheprovider tests` gives **351 passed** in 191.89 s (344 plus 7), no `__pycache__`.

## 5. Owner items

The owner supplied the time-spent figure (approximately 7 hours, including implementation, testing, evaluation, and documentation) and the wording of the AI disclosure. `AGENTS.md` now states the final delivery phase and no authorized cut.

## 6. Delta and standing

`ΔO = NONE / ΔS = NONE / ΔA = NONE`. OSA and CPOC `NOT APPLICABLE` (documents and a screenshot).

```text
CUT 12: IMPLEMENTED / LOCAL VERIFY PASS
```

All twelve cuts are implemented. Cuts 3, 9 and 10 carry `CPOC PASS`.
