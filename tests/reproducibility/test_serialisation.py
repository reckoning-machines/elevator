"""Cut 1 reproducibility tests (testing_contract §6)."""

import os
import shutil
import subprocess
import sys

import pytest

from elevator import domain
from elevator.domain import (
    Configuration,
    EstablishedCodeIdentity,
    Heading,
    Refusal,
    bind_run,
    canonical_json,
    check_execution_environment,
    code_identity,
    detect_code_identity_drift,
    normalize_requests,
    parse_canonical_json,
)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _rows():
    return [{"time": 3, "id": "b", "source": 0, "dest": 4}, {"time": 0, "id": "a", "source": 2, "dest": 1}]


def test_canonical_serialisation_stable():
    trace = normalize_requests(_rows(), num_floors=6)
    cfg = Configuration.create(6, 2, 3, initial_floors=[0, 5])
    for value in (trace, cfg, trace.canonical_rows(), {"z": 1, "a": [Heading.UP, None, "x"]}):
        once = canonical_json(value)
        again = canonical_json(parse_canonical_json(once))
        assert once == again
        assert b" " not in once and b"\n" not in once
    # floats are refused so no platform rendering can enter a hash
    with pytest.raises(TypeError):
        canonical_json({"x": 1.5})
    # hashes are sensitive to every consequential input and insensitive to row order
    base = normalize_requests(_rows(), num_floors=6).trace_hash
    reordered = normalize_requests(list(reversed(_rows())), num_floors=6).trace_hash
    assert base == reordered  # the sorted Trace is the same content
    changed_id = normalize_requests([{"time": 3, "id": "B", "source": 0, "dest": 4}, _rows()[1]], num_floors=6).trace_hash
    changed_time = normalize_requests([{"time": 4, "id": "b", "source": 0, "dest": 4}, _rows()[1]], num_floors=6).trace_hash
    assert len({base, changed_id, changed_time}) == 3
    assert Configuration.create(6, 2, 3).configuration_hash != Configuration.create(6, 2, 4).configuration_hash
    assert (Configuration.create(6, 2, 3, policy_params={"w_tail": 4}).configuration_hash
            != Configuration.create(6, 2, 3).configuration_hash)
    # run_id binds configuration, trace and code identity
    ident = code_identity()
    r1 = bind_run(cfg, trace, ident)
    assert r1.run_id == bind_run(cfg, trace, ident).run_id
    assert r1.run_id != bind_run(cfg, trace, "0" * 64).run_id
    assert r1.max_ticks == trace.last_request_time + 2 * 2 * 5


def test_code_identity_tracks_package_bytes(tmp_path):
    src = os.path.join(ROOT, "elevator")
    copy_a = tmp_path / "pkg_a"
    copy_b = tmp_path / "pkg_b"
    shutil.copytree(src, copy_a, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(src, copy_b, ignore=shutil.ignore_patterns("__pycache__"))
    assert code_identity(str(copy_a)) == code_identity(str(copy_b)) == code_identity(src)
    with open(copy_b / "domain.py", "ab") as fh:
        fh.write(b"#")
    assert code_identity(str(copy_b)) != code_identity(str(copy_a))
    # the Git SHA does not participate: identity is a function of the bytes alone
    assert len(code_identity(src)) == 64
    # drift detection reports a CODE_IDENTITY_DRIFT record value, else None
    established = EstablishedCodeIdentity(package_dir=str(copy_a), identity=code_identity(str(copy_a)))
    assert detect_code_identity_drift(established, execution_id="e", op_seq=9) is None
    with open(copy_a / "api.py", "ab") as fh:
        fh.write(b"\n# drift\n")
    rec = detect_code_identity_drift(established, execution_id="e", op_seq=9)
    assert rec is not None and rec.kind is domain.OperationalRecordKind.CODE_IDENTITY_DRIFT
    assert rec.payload["established"] == established.identity != rec.payload["at_exit"]


def _run_check(args, env_overrides, cwd):
    env = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
    env.update(env_overrides)
    env["PYTHONPATH"] = ROOT
    code = ("from elevator.domain import check_execution_environment, Refusal\n"
            "try:\n    check_execution_environment()\nexcept Refusal as r:\n    print(r.reason)\nelse:\n    print('OK')\n")
    return subprocess.run([sys.executable, *args, "-c", code], capture_output=True, text=True,
                          env=env, cwd=cwd, check=True).stdout.strip()


def test_execution_environment_contract(tmp_path):
    # under the contract (python -B) the check proceeds
    assert _run_check(["-B"], {}, ROOT) == "OK"
    assert _run_check([], {"PYTHONDONTWRITEBYTECODE": "1"}, ROOT) == "OK"
    # bytecode writing enabled: refused. Caches are redirected away from the
    # governed package so the negative case cannot pollute it.
    cache_dir = tmp_path / "pycache_elsewhere"
    assert _run_check([], {"PYTHONPYCACHEPREFIX": str(cache_dir)}, ROOT) == "UNSUPPORTED_EXECUTION_ENVIRONMENT"
    assert not os.path.isdir(os.path.join(ROOT, "elevator", "__pycache__"))
    # a __pycache__ directory inside the package: refused even under -B
    pkg = tmp_path / "pkg"
    shutil.copytree(os.path.join(ROOT, "elevator"), pkg, ignore=shutil.ignore_patterns("__pycache__"))
    assert sys.flags.dont_write_bytecode, "the test process itself must run under python -B"
    check_execution_environment(str(pkg))
    os.makedirs(pkg / "__pycache__")
    with pytest.raises(Refusal) as info:
        check_execution_environment(str(pkg))
    assert info.value.reason == "UNSUPPORTED_EXECUTION_ENVIRONMENT"
    # a source file modified after establishment is reported as drift at exit
    shutil.rmtree(pkg / "__pycache__")
    established = domain.establish_code_identity(str(pkg))
    with open(pkg / "domain.py", "ab") as fh:
        fh.write(b"# modified after start\n")
    rec = detect_code_identity_drift(established, execution_id="e", op_seq=2)
    assert rec is not None and rec.kind.value == "CODE_IDENTITY_DRIFT"
