"""Cut 9 local continuity-negative tests: one fixture per negative witness of cpoc §6 marked cut 9, constructed
exactly as its row says, asserting the named reason and the step reached (so every earlier step passed).
Row numbers follow the table. Rows 9 and 10 (write admission) are in test_write_admission.py; row 33 in
test_resume.py; rows 15 and 16 (a different process) in test_processes.py."""

import json
import os
import shutil

import pytest

from elevator import checkpoint as C
from elevator.domain import Refusal
from tests.cpoc import fixture as X
from tests.cpoc.fixture import expect_refusal, fx  # noqa: F401  (pytest fixture)


# --- steps 1 to 5: store, schema, bindings ------------------------------------------------------------

def test_row_01_missing_snapshot_field(fx):
    doc = fx.doc()
    del doc["snapshot"]["elevators"][1]["heading"]
    fx.put(doc)
    expect_refusal(fx, "MALFORMED", 2)


def test_row_02_missing_section(fx):
    doc = fx.doc()
    del doc["simulation_history"]["tick_records"]
    fx.put(doc)
    expect_refusal(fx, "MALFORMED", 2)


def finish(fx):
    """Let the resumed process complete: the finality write."""
    resumed = C.resume(fx.store, fx.execution_id)
    C.drive(resumed.engine, resumed.writer, C.Controls(), skip_boundary=resumed.loaded.state.t)
    resumed.execution.log.close()
    return resumed


def test_row_03_final_execution_in_its_store(fx):
    finish(fx)
    expect_refusal(fx, "EXECUTION_FINAL", 7)


def test_row_04_final_execution_different_output_directory(fx, tmp_path):
    finish(fx)
    empty_output = tmp_path / "a_new_empty_output_directory"
    empty_output.mkdir()
    expect_refusal(fx, "EXECUTION_FINAL", 7)  # outputs are never consulted: nothing about them can change this
    assert os.listdir(empty_output) == []


def test_row_05_copy_into_another_store(fx, tmp_path):
    other = os.path.join(str(tmp_path), "S2")
    C.init_store(other)
    os.makedirs(os.path.join(other, fx.execution_id))
    copied = C.document_path(other, fx.execution_id)
    fx.put(fx.d12, copied)
    got = X.refusal(other, fx.execution_id)
    assert (got.reason, got.step) == ("STORE_MISMATCH", 5)


def test_row_06_overwrite_inside_the_store_is_the_stated_limit(fx):
    """Recorded as the design's stated limit, neither pass nor fail: deliberate replacement of a document inside
    its own Store by an actor that is not the Execution's process is outside the threat model (cpoc §3.3, §6)."""
    finish(fx)
    fx.put(fx.d12)  # D12 copied over the final document
    loaded = C.load(fx.store, fx.execution_id)  # admitted: it is a lawful RUNNING document
    assert loaded.state.t == X.T and loaded.write_sequence == 1


def test_row_07_independent_execution_of_the_same_run(fx, tmp_path):
    other = X.build_d12(tmp_path, store_name="S")  # a second Execution of the same inputs in the same Store
    assert other.store == fx.store and other.execution_id != fx.execution_id
    a_final = finish(fx)  # e_A completes; e_C is untouched
    assert X.refusal(fx.store, fx.execution_id).reason == "EXECUTION_FINAL"
    c = C.resume(other.store, other.execution_id)  # e_C is its own Execution: admitted
    C.drive(c.engine, c.writer, C.Controls(), skip_boundary=X.T)
    assert a_final.loaded.identity.run_id == c.loaded.identity.run_id  # one Run, two Executions
    from elevator.domain import canonical_json
    assert canonical_json(a_final.engine.history) == canonical_json(c.engine.history)  # identical Histories
    assert os.path.exists(C.document_path(fx.store, fx.execution_id)) and fx.execution_id != other.execution_id


def test_row_08_document_under_the_wrong_execution_path(fx):
    wrong = "e_X-" + fx.execution_id[4:]
    os.makedirs(os.path.join(fx.store, wrong))
    fx.put(fx.d12, C.document_path(fx.store, wrong))
    got = X.refusal(fx.store, wrong)
    assert (got.reason, got.step) == ("EXECUTION_MISMATCH", 5)


# --- step 6: identities ----------------------------------------------------------------------------------

def test_row_11_corrupted_trace_bytes(fx):
    doc = fx.doc()
    doc["trace"][0][3] = (doc["trace"][0][3] + 1) % X.F or 1  # one byte of one Trace row changes
    fx.put(doc)
    expect_refusal(fx, "TRACE_HASH_MISMATCH", 6)


def test_row_12_truncated_file(fx):
    fx.put(fx.d12[: len(fx.d12) // 2])
    expect_refusal(fx, "MALFORMED", 2)


def test_row_13_edited_configuration_hash_not_updated(fx):
    doc = fx.doc()
    doc["configuration"]["num_floors"] = X.F + 1
    fx.put(doc)
    expect_refusal(fx, "CONFIG_HASH_MISMATCH", 6)


def test_row_14_edited_configuration_hash_updated(fx):
    doc = fx.doc()
    doc["configuration"]["num_floors"] = X.F + 1
    doc["configuration_hash"] = X.sha(X.canonical(doc["configuration"]))
    fx.put(doc)
    expect_refusal(fx, "RUN_ID_MISMATCH", 6)


# --- step 9: snapshot internal consistency ------------------------------------------------------------------

def moving_elevator(doc):
    return next(e for e in doc["snapshot"]["elevators"] if e["heading"] != "NONE")


def test_row_17_mutated_heading_hash_recomputed(fx):
    doc = fx.doc()
    e = moving_elevator(doc)
    e["heading"] = "DOWN" if e["heading"] == "UP" else "UP"
    X.recompute_snapshot_hash(doc)
    fx.put(doc)
    expect_refusal(fx, "STATE_HISTORY_MISMATCH", 11)  # a History-folding loader would have continued


def test_row_18_mutated_floor(fx):
    doc = fx.doc()
    e = doc["snapshot"]["elevators"][0]
    e["floor"] = e["floor"] + 1 if e["floor"] + 1 < X.F else e["floor"] - 1
    X.recompute_snapshot_hash(doc)
    fx.put(doc)
    expect_refusal(fx, "STATE_HISTORY_MISMATCH", 11)


def test_row_19_mutated_heading_hash_not_recomputed(fx):
    doc = fx.doc()
    e = moving_elevator(doc)
    e["heading"] = "DOWN" if e["heading"] == "UP" else "UP"
    fx.put(doc)
    expect_refusal(fx, "STATE_INCONSISTENT", 9)  # pins the ordering: the hash check precedes step 11


def test_row_20_duplicate_or_missing_elevator(fx):
    doc = fx.doc()
    doc["snapshot"]["elevators"].insert(2, dict(doc["snapshot"]["elevators"][1]))
    X.recompute_snapshot_hash(doc)
    fx.put(doc)
    expect_refusal(fx, "STATE_INCONSISTENT", 9)
    doc = fx.doc()
    del doc["snapshot"]["elevators"][2]
    X.recompute_snapshot_hash(doc)
    fx.put(doc)
    expect_refusal(fx, "STATE_INCONSISTENT", 9)


def test_row_21_invalid_assignment_id(fx):
    doc = fx.doc()
    doc["snapshot"]["passengers"][0]["assigned_elevator"] = X.N
    X.recompute_snapshot_hash(doc)
    fx.put(doc)
    expect_refusal(fx, "STATE_INCONSISTENT", 9)


def test_row_22_capacity_corrupt_passenger_set(fx):
    doc = fx.doc()
    for p in doc["snapshot"]["passengers"][: X.C + 1]:  # C + 1 passengers ONBOARD one car, consistent fields
        p.update(standing="ONBOARD", assigned_elevator=0, pickup_time=doc["trace"][p["passenger_id"]][0], dropoff_time=None)
    X.recompute_snapshot_hash(doc)
    fx.put(doc)
    expect_refusal(fx, "STATE_INCONSISTENT", 9)


def test_row_23_impossible_completed_travel(fx):
    doc = fx.doc()
    p = next(p for p in doc["snapshot"]["passengers"] if p["standing"] == "COMPLETED")
    r = doc["trace"][p["passenger_id"]]
    p["dropoff_time"] = p["pickup_time"] + abs(r[3] - r[2]) + 1
    X.recompute_snapshot_hash(doc)
    fx.put(doc)
    expect_refusal(fx, "STATE_INCONSISTENT", 9)


def test_row_24_resurrection_with_consistent_fields(fx):
    doc = fx.doc()
    t = doc["snapshot"]["t"]
    p = next(p for p in doc["snapshot"]["passengers"] if p["standing"] == "WAITING"
             and doc["trace"][p["passenger_id"]][0] + abs(doc["trace"][p["passenger_id"]][3] - doc["trace"][p["passenger_id"]][2]) < t)
    r = doc["trace"][p["passenger_id"]]
    p.update(standing="COMPLETED", pickup_time=r[0], dropoff_time=r[0] + abs(r[3] - r[2]))
    X.recompute_snapshot_hash(doc)
    fx.put(doc)
    expect_refusal(fx, "STATE_HISTORY_MISMATCH", 11)  # steps 9's ordering and < t checks pass; the events disagree


# --- step 10: history internal consistency ---------------------------------------------------------------------

def test_row_25_forged_recorded_load(fx):
    doc = fx.doc()
    doc["simulation_history"]["tick_records"][3]["entries"][0]["load"] = X.C + 1
    X.recompute_history_hash(doc)
    fx.put(doc)
    expect_refusal(fx, "HISTORY_INCONSISTENT", 10)


def test_row_26_forged_boarded_set(fx):
    doc = fx.doc()
    doc["simulation_history"]["tick_records"][2]["entries"][1]["boarded"].append(0)  # no BOARDED event
    X.recompute_history_hash(doc)
    fx.put(doc)
    expect_refusal(fx, "HISTORY_INCONSISTENT", 10)


def test_row_27_wrong_way_boarding_in_history(fx):
    doc = fx.doc()
    h = doc["simulation_history"]
    boarded = next(e for e in h["events"] if e["kind"] == "BOARDED")
    pid, el, k = boarded["passenger_id"], boarded["elevator_id"], boarded["tick"]
    r = doc["trace"][pid]
    direction = "UP" if r[3] > r[2] else "DOWN"
    k2 = next(rec["tick"] for rec in h["tick_records"]
              if rec["tick"] != k and rec["entries"][el]["heading"] not in (direction, "NONE"))
    h["tick_records"][k]["entries"][el]["boarded"].remove(pid)
    h["tick_records"][k2]["entries"][el]["boarded"].append(pid)
    boarded["tick"] = k2
    X.recompute_history_hash(doc)
    fx.put(doc)
    expect_refusal(fx, "HISTORY_INCONSISTENT", 10)


def test_row_28_operational_record_inside_the_history(fx):
    doc = fx.doc()
    doc["simulation_history"]["events"].insert(
        5, {"execution_id": fx.execution_id, "op_seq": 9, "kind": "CHECKPOINT_WRITTEN", "tick": 3, "payload": {}})
    X.recompute_history_hash(doc)
    fx.put(doc)
    expect_refusal(fx, "MALFORMED", 2)
    doc = fx.doc()  # variant: a Simulation-Event-shaped record of an unknown kind
    unknown = dict(doc["simulation_history"]["events"][0])
    unknown["kind"] = "RESURRECTED"
    doc["simulation_history"]["events"].insert(5, unknown)
    X.recompute_history_hash(doc)
    fx.put(doc)
    expect_refusal(fx, "MALFORMED", 2)


# --- the ordering across all of them -----------------------------------------------------------------------------

def test_every_refusal_names_the_first_failing_step_in_order(fx):
    """One document with two faults refuses at the earlier step: row 19's unrecomputed hash (step 9) is reported
    before a History fault (step 10), and a bad configuration hash (step 6) before either."""
    doc = fx.doc()
    e = moving_elevator(doc)
    e["heading"] = "DOWN" if e["heading"] == "UP" else "UP"
    doc["simulation_history"]["tick_records"][3]["entries"][0]["load"] = X.C + 1
    fx.put(doc)
    expect_refusal(fx, "STATE_INCONSISTENT", 9)
    doc["configuration"]["num_floors"] = X.F + 1
    fx.put(doc)
    expect_refusal(fx, "CONFIG_HASH_MISMATCH", 6)
    doc["schema_version"] = 2
    fx.put(doc)
    expect_refusal(fx, "SCHEMA_MISMATCH", 3)
    doc["snapshot"] = "not an object"
    fx.put(doc)
    expect_refusal(fx, "MALFORMED", 2)
