"""A deliberately CHEATING fixture module (testing_contract §7). It is never imported by the package or run by
a test: the architecture scan reads its source and must detect every function here as a History-to-state path.
Each function rebuilds current state from the Simulation History, which constitution N14 prohibits."""

from elevator.checkpoint import HistoryPrefix, HistoryVerifier, Snapshot, construct_state, parse_history
from elevator.engine import ElevatorState, EngineState, PassengerState


def snapshot_from_history(history: HistoryPrefix, t: int) -> Snapshot:
    """Folds a History prefix into a Snapshot: the typed boundary's forbidden direction."""
    last = history.tick_records[t - 1]
    return Snapshot(t, tuple(ElevatorState(e.elevator_id, e.floor + e.heading.delta, e.heading) for e in last.entries),
                    (), "cheat")


def state_from_events(events: list, tick_records: list) -> EngineState:
    """Rebuilds engine state from raw events and tick records."""
    return EngineState(len(tick_records), (), tuple(PassengerState(e.passenger_id, "x", None, 0, 0, None, None)
                                                    for e in events))


def resume_from_document(document, verifier: HistoryVerifier):
    """No History-typed return, but it parses the History and calls construct_state itself: a state builder
    outside the one allowed caller (``load``)."""
    history = parse_history(document)
    return construct_state(history)  # type: ignore[arg-type]
