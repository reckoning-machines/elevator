# Owner Decision Record 009: Policy Construction Edges (Revision 7.3)

Status: **DECIDED AND ADMITTED 2026-11-05 by the owner.** This record admits an architectural clarification to the revision-7.2 baseline of [record 008](owner_decision_008_invariant_violation_halt.md). The result is revision 7.3. Records 006 to 008 are not rewritten; for `docs/architecture.md` this record's digest supersedes theirs.

## 1. Source

Cut 8 stopped on a dependency gap ([cut-8 record §2](../implementation/cut_08_evaluation_api_operations.md)): the public
functions take a policy name (evaluation §2) and an Experiment lists policy names (§7.1), but the architecture's
dependency table let none of `api`, `harness`, `checkpoint` or `web` import `policies`, and no document assigned
name-to-policy resolution to any component. Four options were put to the owner; the owner adopted option A.

## 2. Decision

> Adopt Option A. Add `policies` as an allowed dependency for the components that must resolve admitted policy
> names into policy objects: `api`, `harness`, `checkpoint` and `web`. Centralize resolution in
> `elevator/policies.py`. This is an architectural clarification only: `ΔO = NONE / ΔS = NONE / ΔA = NONE`.
> Record it as Revision 7.3 and re-admit the changed architecture digest. The edges permit policy construction
> only; they do not transfer engine authority, assignment authority, runtime state ownership or scheduler
> state. Policies remain pure proposal producers and the engine remains the sole assignment and commit
> authority.
>
> One canonical resolver in `elevator/policies.py`, supporting exactly `round_robin`, `nearest_car` and
> `cost_based`: no registry framework, no plugin system, no mutable global state, no dynamic imports; an
> unknown name fails deterministically; cost-based parameters come from the admitted Configuration fields;
> the baselines keep their existing exact definitions. Every component that resolves names uses this one
> resolver; no other component keeps a dictionary.

Owner, 2026-11-05.

## 3. Constitutional Delta

`ΔO = NONE / ΔS = NONE / ΔA = NONE`. `docs/architecture.md` is descriptive and decides no semantic question
(AGENTS.md precedence 4). No object, rule, authority row, writer, carrier, selector or lifecycle changes; the
policy set, the scheduler semantics and the public API semantics are unchanged.

## 4. Changed bytes (revision 7.3)

| File | Change | SHA-256 |
| --- | --- | --- |
| `docs/architecture.md` | the dependency rows of `api`, `harness`, `checkpoint` and `web` gain `policies` (`make_policy` only); `policies` is removed from `checkpoint`'s "must not depend on"; the `policies` row names `make_policy`; new §1.2 "Policy construction"; status line | `a38da7e428678721b0cfaf7cee6dce42c028b35c880d83c4853200188b558272` |

The complete admitted set at revision 7.3 (the eight unchanged files at the digests of records 006 and 008):

| File | SHA-256 |
| --- | --- |
| `docs/constitution.md` | `b34958f91e6d4c5fc32f74fe96be14b6287ca80abdde951e77eb2e730cb659c3` |
| `docs/authority_model.md` | `4a066fb9fd8d85ffa9175501fddf9992cdaa42e8f644ffa07893847f7daf384e` |
| `docs/simulation_semantics.md` | `821cb89dbbd49ac0c44080f0eddc817ae2f8fece211d5a43f37f8b355d8fbd9d` |
| `docs/scheduler_design.md` | `25e7ec14ec3a46127430ca4d0bdd9e01d46d0ba1024d3ee10bbbf54cbddba881` |
| `docs/evaluation_design.md` | `b8c29a3d47b5be8fce9f517f931bb6848508a0a595254ff8187832cbeb7c1fa1` |
| `docs/cpoc_design.md` | `65ca79366e4f5a6c970ba2c59a0f01ff976519840e6219a5de26aa5f6e566d58` |
| `docs/ui_design.md` | `b22ea1164403bebc733aba986dea5b25b5ee9ad6e12e3e55a55cfb146382366c` |
| `docs/architecture.md` | `a38da7e428678721b0cfaf7cee6dce42c028b35c880d83c4853200188b558272` |
| `docs/testing_contract.md` | `b0e78b99a824a0642f14adb45f9ac44e114fc40533ceae72259757b102d96001` |
| `docs/plans/implementation_plan.md` | `26f6920ee56c9ef17e053db7ad1f6ed5d2f15e5606258d60069648790d64c24e` |

## 5. Admission

> I admit revision 7.3: `docs/architecture.md` at the digest above together with the other governing documents
> and the implementation plan at the digests above, as the governing design baseline. Cut order and
> authorization are unchanged: cut 8 remains the current cut and resumes from its partial implementation; cut 9
> is not authorized until cut 8 reaches its verified standing.

Owner, 2026-11-05.

## 6. What this record does not decide

It does not decide the **default Experiment's** building, car count, capacity, per-pattern scenario parameters
or committed seed set (evaluation §7.6 states only "9 patterns, 20 seeds, 3 policies"; §7.1 gives the seed
default `0..K-1, K = 20`). Those are a separate owner decision; until it is made no default Experiment
definition and no committed experiment evidence is created. It also does not add any edge other than the four
named; in particular it does not add an `api` or `operations` edge to `harness` (see the cut-8 record).
