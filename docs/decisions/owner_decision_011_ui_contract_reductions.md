# Owner Decision Record 011: UI Contract Reductions (Revision 7.4)

Status: **DECIDED AND ADMITTED 2026-11-05 by the owner.** This record amends the admitted [UI design](../ui_design.md) of revision 7.3. The result is revision 7.4. Records 006 to 010 are not rewritten; for `docs/ui_design.md` this record's digest supersedes theirs.

## 1. Source

The independent audit of cut 11 (`FAIL — CUT 11`, finding C11-I-03) found three admitted UI features that no lawful component could provide ([cut-11 record §10](../implementation/cut_11_web_ui.md)): partial live metrics (`reporting` refuses a non-final Run), projected stops per car (`route` is not a `web` dependency and no accessor exists) and scenario/seed controls on the single-run screen (`web -> scenarios` is not admitted). Cut 11 stopped and returned the three to the owner.

## 2. Decision

> Do not add new runtime dependency edges or new reporting semantics to implement them. Remove the requirement for partial/live reporting metrics while a Run is `RUNNING`: the UI may display only current authoritative state already lawfully available (tick, elevator position, heading, load/capacity, waiting and onboard passengers, Run status); distribution metrics, final passenger metrics, calibration and the reporting surface remain final-run outputs, and no partial-reporting mode is added. Remove projected-stop visualization from the admitted UI; add no `web -> route`, no engine committed-stop accessor and no route projection in web; the committed assignment receipt remains the explanation surface for cost-based decisions. Remove scenario and seed controls from the interactive single-run screen: it operates on a concrete request Trace (the built-in example or user-supplied rows); scenario generation stays with the scenario and evaluation path and the Experiment page remains the scenario-based surface; add no `web -> scenarios`.

Owner, 2026-11-05.

## 3. Constitutional Delta

`ΔO = NONE / ΔS = UI-ONLY / ΔA = NONE`. The reductions remove screen obligations only. No simulation, scheduler, reporting or evaluation semantics, no authority row, owner, carrier, writer, selector or lifecycle, and no architecture dependency changes. `docs/architecture.md`, `docs/evaluation_design.md` and `docs/testing_contract.md` are unchanged.

## 4. Changed bytes (revision 7.4)

| File | Change | SHA-256 |
| --- | --- | --- |
| `docs/ui_design.md` | status line; §2 layout sketch (request source instead of scenario and seed; "Results (final run only)"); §2.1 first control row (concrete request Trace, no scenario or seed control); §2.2 the committed-stops bullet removed; §2.3 results are final-run outputs, RUNNING shows current state only | `388fbbca9ab34edf8267d277e51e692467082a28ced3d851cc123dcb6a50fe6f` |

The complete admitted set at revision 7.4 (the other documents at the digests of records 006, 008 and 009):

| File | SHA-256 |
| --- | --- |
| `docs/constitution.md` | `b34958f91e6d4c5fc32f74fe96be14b6287ca80abdde951e77eb2e730cb659c3` |
| `docs/authority_model.md` | `4a066fb9fd8d85ffa9175501fddf9992cdaa42e8f644ffa07893847f7daf384e` |
| `docs/simulation_semantics.md` | `821cb89dbbd49ac0c44080f0eddc817ae2f8fece211d5a43f37f8b355d8fbd9d` |
| `docs/scheduler_design.md` | `25e7ec14ec3a46127430ca4d0bdd9e01d46d0ba1024d3ee10bbbf54cbddba881` |
| `docs/evaluation_design.md` | `b8c29a3d47b5be8fce9f517f931bb6848508a0a595254ff8187832cbeb7c1fa1` |
| `docs/cpoc_design.md` | `65ca79366e4f5a6c970ba2c59a0f01ff976519840e6219a5de26aa5f6e566d58` |
| `docs/ui_design.md` | `388fbbca9ab34edf8267d277e51e692467082a28ced3d851cc123dcb6a50fe6f` |
| `docs/architecture.md` | `a38da7e428678721b0cfaf7cee6dce42c028b35c880d83c4853200188b558272` |
| `docs/testing_contract.md` | `b0e78b99a824a0642f14adb45f9ac44e114fc40533ceae72259757b102d96001` |
| `docs/plans/implementation_plan.md` | `26f6920ee56c9ef17e053db7ad1f6ed5d2f15e5606258d60069648790d64c24e` |

## 5. Other findings of the same audit (owner direction, recorded)

C11-I-05 (LOW): `httpx` is a test/development dependency required by Starlette's `TestClient`; it creates no production dependency edge and affects no runtime authority. It is a documentation observation (architecture §6 lists `pytest` and `hypothesis` for tests); architecture is not revised and no further implementation is required. The repairs of C11-I-01, -02, -03c, -03e, -03f and -04 stand.

## 6. Admission

> I admit revision 7.4: `docs/ui_design.md` at the digest above together with the other governing documents and the implementation plan at the digests above, as the governing design baseline. Cut 11 is re-audited against revision 7.4; cut 12 is not authorized until that re-audit.

Owner, 2026-11-05.
