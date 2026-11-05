"""Cut 9 architecture tests: no History-to-state path anywhere in the package, and the dependency graph of the
continuity components (architecture §1 as amended by revision 7.3)."""

import os

from tests.cpoc import scan

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CHEAT = os.path.join(ROOT, "tests", "cpoc", "cheats", "history_cheat.py")


def test_no_history_to_state_path_in_package():
    # the real package (and the web package, when it exists) has no function that turns History into state
    assert scan.scan_package(ROOT) == {}
    # the deliberately cheating fixture is detected by the very same scan: every cheating function is found
    found = scan.scan_file(CHEAT)
    assert len(found) >= 5, found
    for name in ("snapshot_from_history", "state_from_events", "resume_from_document"):
        assert any(f.startswith(f"history_cheat.{name}:") for f in found), name
    assert any("takes history-shaped input and yields or builds state" in f and "snapshot_from_history" in f for f in found)
    assert any("builds state outside the allowed constructors" in f and "resume_from_document" in f for f in found)
    # the fixture is excluded from the real package: it lives under the test tree and the package scan never sees it
    assert os.path.commonpath([CHEAT, os.path.join(ROOT, "elevator")]) == ROOT
    assert "history_cheat" not in " ".join(scan.scan_package(ROOT))


def test_the_scan_is_not_a_search_for_a_function_name(tmp_path):
    """The scan decides by data flow (annotations and the call graph), so a cheat with an innocent name and no
    History-typed annotation is still found, and an innocently-named allowed constructor is not mistaken."""
    sneaky = tmp_path / "innocent.py"
    sneaky.write_text("from elevator.checkpoint import construct_state, Snapshot\n"
                      "def helper(x):\n    return construct_state(Snapshot(0, (), (), 'h'))\n"
                      "def shape(events: list) -> 'Snapshot':\n    return None\n")
    found = scan.scan_file(str(sneaky))
    assert any("innocent.helper" in f for f in found) and any("innocent.shape" in f for f in found)
    harmless = tmp_path / "harmless.py"
    harmless.write_text("def total(events: list) -> int:\n    return len(events)\n")
    assert scan.scan_file(str(harmless)) == []


def test_continuity_components_follow_the_dependency_table():
    def elevator_imports(name):
        return {m for m in scan.imports_of(os.path.join(ROOT, "elevator", name)) if m.startswith("elevator")}

    allowed = {"elevator", "elevator.route", "elevator.operations", "elevator.engine", "elevator.domain",
               "elevator.policies"}
    mods = elevator_imports("checkpoint.py")
    assert {m.split(".")[0] + "." + m.split(".")[1] if m.count(".") >= 1 and m != "elevator" else m for m in mods} <= allowed | {
        "elevator.route", "elevator.operations", "elevator.engine", "elevator.domain", "elevator.policies"}
    assert {m for m in mods if m.startswith("elevator.policies")} == {"elevator.policies", "elevator.policies.make_policy"}
    assert not {m for m in mods if any(x in m for x in ("reporting", "api", "web", "harness", "scenarios", "cli"))}
    # nothing below the continuity layer depends on it: no cycle and no edge back
    for module in ("engine.py", "route.py", "policies.py", "reporting.py", "scenarios.py", "operations.py",
                   "domain.py", "api.py", "harness.py"):
        assert not [m for m in elevator_imports(module) if "checkpoint" in m], module
    # operations still depends on domain and the standard library only, and checkpoint adds nothing to it
    assert not {m for m in elevator_imports("operations.py") if m.startswith("elevator")} - {
        "elevator.domain", "elevator.domain.OperationalRecord", "elevator.domain.OperationalRecordKind",
        "elevator.domain.canonical_json", "elevator.domain.freeze"}
    # the CLI is the one place that composes the API with the checkpoint module (api -> checkpoint never exists)
    assert any("checkpoint" in m for m in elevator_imports("cli.py"))
    pystd = scan.imports_of(os.path.join(ROOT, "elevator", "checkpoint.py"))
    assert not pystd & {"random", "time", "datetime", "subprocess", "socket", "secrets"}  # no clock or randomness
    assert "uuid" in pystd  # the Store's own random identity, minted once at `store init`
