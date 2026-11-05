"""Revision 7.3 resolver tests: one canonical name-to-policy resolver in policies.py (owner decision 009)."""

import ast
import os

import pytest

from elevator.domain import Configuration, Refusal
from elevator.policies import CostBased, NearestCar, RoundRobin, make_policy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_resolver_supports_exactly_the_three_admitted_policies():
    for name, cls in (("round_robin", RoundRobin), ("nearest_car", NearestCar), ("cost_based", CostBased)):
        cfg = Configuration.create(8, 2, 3, policy=name)
        policy = make_policy(cfg.policy, cfg.policy_params)
        assert type(policy) is cls and policy.name == name
    for bad in ("lookahead", "Round_Robin", "", "cost-based", "round_robin ", None, 3):
        with pytest.raises(Refusal) as info:
            make_policy(bad)  # type: ignore[arg-type]
        assert info.value.reason == "INVALID_CONFIGURATION"


def test_cost_based_parameters_come_from_the_configuration():
    cfg = Configuration.create(8, 2, 3, policy="cost_based", policy_params={"w_tail": 5, "age_scale": 2})
    built = make_policy(cfg.policy, cfg.policy_params)
    assert built == CostBased(w_wait=1, w_marginal=1, w_tail=5, tail_threshold=14, age_scale=2)
    assert built == CostBased(**dict(cfg.policy_params))
    # the Configuration's defaults and the resolver agree for every building size
    for floors in (2, 3, 9, 200):
        c = Configuration.create(floors, 1, 1, policy="cost_based")
        assert make_policy("cost_based", c.policy_params) == CostBased.for_building(floors)
    # incomplete or out-of-domain parameters refuse rather than being filled in silently
    for bad in ({"w_wait": 1}, {"w_wait": 1.5, "w_marginal": 1, "w_tail": 3, "tail_threshold": 2, "age_scale": 1}, {}):
        with pytest.raises((TypeError, ValueError)):
            make_policy("cost_based", bad)


def test_baselines_take_no_parameters_and_are_stateless_objects():
    for name in ("round_robin", "nearest_car"):
        with pytest.raises(Refusal) as info:
            make_policy(name, {"w_wait": 1})
        assert info.value.reason == "INVALID_CONFIGURATION"
        assert make_policy(name) == make_policy(name, {}) and make_policy(name) is not make_policy(name)


def test_there_is_one_resolver_and_no_registry_or_second_table():
    def tree(name):
        with open(os.path.join(ROOT, "elevator", name), encoding="utf-8") as fh:
            return ast.parse(fh.read())

    # no component other than policies.py names a policy class: they all go through make_policy
    for module in ("api.py", "harness.py", "cli.py", "engine.py", "reporting.py", "operations.py", "scenarios.py", "checkpoint.py"):
        t = tree(module)
        names = {n.id for n in ast.walk(t) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(t)
                                                                           if isinstance(n, ast.Attribute)}
        assert not names & {"RoundRobin", "NearestCar", "CostBased"}, module
    # api imports the resolver and nothing else from policies
    api = tree("api.py")
    imported = {a.name for n in ast.walk(api) if isinstance(n, ast.ImportFrom) and n.module == "elevator.policies"
                for a in n.names}
    assert imported == {"make_policy"}
    # the resolver holds no registry: no module-level mapping, no dynamic import, no globals
    pol = tree("policies.py")
    assert not [n for n in pol.body if isinstance(n, (ast.Assign, ast.AnnAssign))]
    calls = {c.func.id for c in ast.walk(pol) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    attrs = {a.attr for a in ast.walk(pol) if isinstance(a, ast.Attribute)}
    # no dynamic import and no code evaluation (getattr appears only in CostBased's own field validation)
    assert not calls & {"__import__", "exec", "eval", "compile", "globals", "import_module"}
    assert not attrs & {"import_module", "__subclasses__"} and not [n for n in ast.walk(pol) if isinstance(n, ast.Global)]
    mods = {n.module for n in ast.walk(pol) if isinstance(n, ast.ImportFrom)}
    assert {m for m in mods if m and m.startswith("elevator")} == {"elevator", "elevator.domain"}
