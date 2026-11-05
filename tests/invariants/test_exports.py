"""Cut 6 export invariants (testing_contract §2): the position exports are projections of the
TickRecords. The contract reads these against written files, so the files are written to disk."""

import os

from elevator import reporting as R
from tests.engine_fixtures import ByIdPolicy
from tests.invariants.test_engine_invariants import FIXTURES, _sweep
from tests.report_fixtures import run_record


def regenerate_wide(history, n):
    lines = ["t," + ",".join(f"elevator_{i}" for i in range(n))]
    for tr in history.tick_records:
        lines.append(f"{tr.tick}," + ",".join(str(e.floor) for e in tr.entries))
    return ("\n".join(lines) + "\n").encode()


def regenerate_long(history):
    lines = ["t,elevator_id,floor,heading,load"]
    for tr in history.tick_records:
        for e in tr.entries:
            lines.append(f"{tr.tick},{e.elevator_id},{e.floor},{e.heading.value},{e.load}")
    return ("\n".join(lines) + "\n").encode()


def records():
    for spec in FIXTURES + _sweep():
        args = dict(spec)
        rows, floors = args.pop("rows"), args.pop("floors")
        for policy in ("round_robin", "nearest_car", "cost_based"):
            yield run_record(rows, floors, args.get("elevators", 1), args.get("capacity", 2),
                             initial=args.get("initial"), policy=policy)[0]
    # halted runs: no committed ticks, some committed ticks, and a horizon halt
    yield run_record([(0, "a", 0, 2)], 3, 1, 2, policy="round_robin", policy_object=ByIdPolicy(mapping={0: 9}))[0]
    yield run_record([(0, "a", 0, 2), (3, "b", 1, 2)], 3, 2, 2, policy="round_robin",
                     policy_object=ByIdPolicy(mapping={1: 5}))[0]
    yield run_record([(0, "a", 0, 4)], 5, 3, 2, policy="round_robin", max_ticks=2)[0]


def test_position_exports_are_projections_of_tick_records(tmp_path):
    count = 0
    for i, rec in enumerate(records()):
        directory = str(tmp_path / f"run{i}")
        R.write_files(directory, R.reproducible_surface(rec))
        n = rec.configuration.num_elevators
        with open(os.path.join(directory, "elevator_positions.csv"), "rb") as fh:
            assert fh.read() == regenerate_wide(rec.history, n)
        with open(os.path.join(directory, "position_log_long.csv"), "rb") as fh:
            assert fh.read() == regenerate_long(rec.history)
        count += 1
    assert count > 700


def test_wide_export_one_row_per_timestamp(tmp_path):
    halted = 0
    for i, rec in enumerate(records()):
        directory = str(tmp_path / f"run{i}")
        R.write_files(directory, R.reproducible_surface(rec))
        with open(os.path.join(directory, "elevator_positions.csv"), encoding="utf-8") as fh:
            lines = fh.read().split("\n")
        assert lines[-1] == ""  # every row ends in a newline
        header, rows = lines[0].split(","), [r.split(",") for r in lines[1:-1]]
        n = rec.configuration.num_elevators
        assert len(header) == n + 1 and all(len(r) == n + 1 for r in rows)
        last = rec.history.events[-1]
        if last.kind.value == "COMPLETED":
            assert len(rows) == last.tick + 1  # exactly final + 1 rows, from t = 0
        else:
            halted += 1
            assert len(rows) == last.tick  # one row per committed tick; header only when none
        assert [int(r[0]) for r in rows] == list(range(len(rows)))  # every timestamp, gaps included
    assert halted == 3
