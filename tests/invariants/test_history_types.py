"""Cut 1 invariant test (testing_contract §2): the type half of N18."""

import pytest

from elevator.domain import (
    Heading,
    OperationalRecord,
    OperationalRecordKind,
    SimulationEvent,
    SimulationEventKind,
    SimulationHistory,
    TickEntry,
    TickRecord,
    canonical_json,
)


def test_no_operational_record_in_history():
    op = OperationalRecord(execution_id="e", op_seq=1, kind=OperationalRecordKind.EXECUTION_STARTED)
    ev = SimulationEvent(seq=0, kind=SimulationEventKind.REVEALED, tick=0, passenger_id=0)
    tr = TickRecord(tick=0, entries=(TickEntry(0, 0, Heading.UP, 1, (0,), ()),))
    with pytest.raises(TypeError):
        SimulationHistory(events=(ev, op), tick_records=(tr,))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        SimulationHistory(events=(ev,), tick_records=(tr, op))  # type: ignore[arg-type]
    history = SimulationHistory(events=(ev,), tick_records=(tr,))
    serialised = canonical_json(history).decode()
    for kind in OperationalRecordKind:
        assert kind.value not in serialised
    assert "execution_id" not in serialised
