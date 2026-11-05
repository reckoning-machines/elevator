"""Cut 8 test (testing_contract §6): run identity follows the parameters."""

from elevator.domain import Configuration, bind_run, normalize_requests

CODE = "c" * 64
ROWS = [(0, "a", 0, 4), (2, "b", 3, 1)]


def run_id(**params):
    cfg = Configuration.create(6, 2, 3, policy="cost_based", policy_params=params or None)
    return bind_run(cfg, normalize_requests(ROWS, 6), CODE).run_id


def test_run_id_changes_with_params():
    base = run_id()
    assert run_id() == base and run_id(w_wait=1) == base  # nothing changed, or a default spelled out: same run_id
    for change in ({"w_wait": 2}, {"w_marginal": 2}, {"w_tail": 4}, {"tail_threshold": 11}, {"age_scale": 6}):
        assert run_id(**change) != base, change  # changing any cost weight or threshold changes the run_id
    assert len({run_id(w_wait=n) for n in range(5)}) == 5
    # and so do the other consequential inputs: building, trace, policy, code identity
    cfg = Configuration.create(6, 2, 3, policy="cost_based")
    trace = normalize_requests(ROWS, 6)
    assert bind_run(cfg, trace, "d" * 64).run_id != base
    assert bind_run(Configuration.create(6, 2, 4, policy="cost_based"), trace, CODE).run_id != base
    assert bind_run(Configuration.create(6, 2, 3, policy="round_robin"), trace, CODE).run_id != base
    assert bind_run(cfg, normalize_requests(ROWS[:1], 6), CODE).run_id != base
