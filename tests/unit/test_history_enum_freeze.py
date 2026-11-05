"""C3-I-01 (Enum boundary): an Enum member's value may be mutable, so
committed History never keeps the member, only a frozen copy of its value."""

import dataclasses
from enum import Enum

import pytest

from elevator.domain import (
    FrozenEnum,
    Heading,
    Proposal,
    SimulationEvent,
    SimulationEventKind as K,
    canonical_json,
    freeze,
)
from tests.engine_fixtures import build


class DictMode(Enum):
    A = {"cost": 5, "tags": ["x"]}


class ListMode(Enum):
    A = [1, [2, 3], {"k": [4]}]


class Plain(Enum):
    LOW = 1
    HIGH = "hi"


class Unsupported(Enum):
    BAD = 1.5


class SetValued(Enum):
    BAD = frozenset({1})


class EnumReceiptPolicy:
    def __init__(self, member):
        self.member = member

    def assign(self, view, request):
        return Proposal(0, {"mode": self.member, "plain": Plain.LOW})


def _committed(member):
    eng, _ = build([(0, "a", 0, 2)], floors=3, policy=EnumReceiptPolicy(member))
    eng.run()
    (assigned,) = [e for e in eng.history.events if e.kind is K.ASSIGNED]
    return eng, assigned


def test_enum_with_dict_value_mutation_leaves_history_unchanged():
    eng, assigned = _committed(DictMode.A)
    before = canonical_json(eng.history)
    DictMode.A.value["cost"] = -1
    DictMode.A.value["tags"].append("injected")
    DictMode.A.value["new"] = True
    assert canonical_json(eng.history) == before
    assert assigned.receipt["mode"].value["cost"] == 5
    assert assigned.receipt["mode"].value["tags"] == ("x",)
    DictMode.A.value.pop("new"); DictMode.A.value["tags"].remove("injected"); DictMode.A.value["cost"] = 5


def test_enum_with_nested_list_value_mutation_leaves_history_unchanged():
    eng, assigned = _committed(ListMode.A)
    before = canonical_json(eng.history)
    ListMode.A.value[1].append(99)
    ListMode.A.value[2]["k"].append(98)
    ListMode.A.value.append("tail")
    assert canonical_json(eng.history) == before
    assert assigned.receipt["mode"].value == (1, (2, 3), {"k": (4,)})
    ListMode.A.value[1].remove(99); ListMode.A.value[2]["k"].remove(98); ListMode.A.value.remove("tail")


def test_committed_enum_payload_exposes_nothing_mutable():
    eng, assigned = _committed(DictMode.A)
    before = canonical_json(eng.history)
    frozen = assigned.receipt["mode"]
    assert isinstance(frozen, FrozenEnum) and not isinstance(frozen, Enum)
    assert frozen.type_name.endswith("DictMode") and frozen.member_name == "A"
    with pytest.raises(dataclasses.FrozenInstanceError):
        frozen.value = {}
    with pytest.raises(TypeError):
        frozen.value["cost"] = 0
    with pytest.raises(AttributeError):
        frozen.value["tags"].append("x")
    with pytest.raises(TypeError):
        assigned.receipt["mode"] = None
    # a caller-built FrozenEnum around a mutable value is re-frozen too
    mutable = {"inner": [1]}
    fe = FrozenEnum("t.T", "M", mutable)
    mutable["inner"].append(2)
    assert fe.value["inner"] == (1,)
    ev = SimulationEvent(seq=0, kind=K.ASSIGNED, tick=0, receipt={"fe": fe})
    assert ev.receipt["fe"] is not fe and ev.receipt["fe"] == fe
    assert canonical_json(eng.history) == before


def test_enum_canonical_serialisation_deterministic_and_equivalent():
    a, _ = _committed(DictMode.A)
    b, _ = _committed(DictMode.A)
    assert canonical_json(a.history) == canonical_json(b.history) == canonical_json(a.history)
    assert a.history == b.history
    # key order of an Enum's dict value does not affect the committed bytes
    class OrderA(Enum):
        V = {"b": 1, "a": 2}
    class OrderB(Enum):
        V = {"a": 2, "b": 1}
    e1 = SimulationEvent(seq=0, kind=K.ASSIGNED, tick=0, receipt={"m": OrderA.V})
    e2 = SimulationEvent(seq=0, kind=K.ASSIGNED, tick=0, receipt={"m": OrderB.V})
    assert canonical_json(e1.receipt["m"].value) == canonical_json(e2.receipt["m"].value)
    # the same member frozen twice is identical; different members differ
    assert freeze(Plain.LOW) == freeze(Plain.LOW) and freeze(Plain.LOW) != freeze(Plain.HIGH)
    assert canonical_json(freeze(Plain.LOW)) != canonical_json(freeze(Plain.HIGH))
    # a FrozenEnum round-trips through freeze unchanged
    assert freeze(freeze(DictMode.A)) == freeze(DictMode.A)


def test_ordinary_scalar_enum_keeps_identity_and_value():
    f = freeze(Plain.HIGH)
    assert (f.member_name, f.value) == ("HIGH", "hi") and f.type_name.endswith("Plain")
    assert canonical_json(f) == canonical_json(freeze(Plain.HIGH))
    # heading enums inside TickEntry are unchanged: they are not freeze payloads
    assert freeze(Heading.UP).value == "UP"


def test_unsupported_enum_values_fail_closed():
    for member in (Unsupported.BAD, SetValued.BAD):
        with pytest.raises(TypeError):
            freeze(member)
        eng, _ = build([(0, "a", 0, 2)], floors=3, policy=EnumReceiptPolicy(member))
        out = eng.run()
        assert out.halt_reason == "INVALID_PROPOSAL" and eng.history.tick_records == ()

    # a self-referential value cannot be frozen either, and halts rather than escaping
    cyclic = []
    cyclic.append(cyclic)
    class Cyc(Enum):
        C = cyclic
    eng, _ = build([(0, "a", 0, 2)], floors=3, policy=EnumReceiptPolicy(Cyc.C))
    assert eng.run().halt_reason == "INVALID_PROPOSAL"


def test_existing_receipt_freeze_still_holds():
    src = {"tier": 1, "c": [{"E": 0}]}
    ev = SimulationEvent(seq=0, kind=K.ASSIGNED, tick=0, receipt=src)
    frozen = canonical_json(ev)
    src["tier"] = 2; src["c"][0]["E"] = 9; src["c"].append(1)
    assert canonical_json(ev) == frozen
    with pytest.raises(TypeError):
        ev.receipt["tier"] = 0


# --- FrozenEnum metadata is sealed at construction (re-audit of C3-I-01) ---

from elevator.engine import HALTED  # noqa: E402


class _Mutable:
    def __init__(self):
        self.x = ["a"]

    def __str__(self):
        return "".join(self.x)


class _StrSub(str):
    pass


def test_frozen_enum_type_name_must_be_an_exact_str():
    for bad in (["Mode"], {"k": "v"}, _Mutable(), ("t",), 5, None, b"Mode", _StrSub("Mode")):
        with pytest.raises(TypeError):
            FrozenEnum(bad, "A", 1)


def test_frozen_enum_member_name_must_be_an_exact_str():
    for bad in (["A"], {"k": "v"}, _Mutable(), ("a",), 5, None, b"A", _StrSub("A")):
        with pytest.raises(TypeError):
            FrozenEnum("t.T", bad, 1)


def test_codex_reproduction_is_refused_and_cannot_change_bytes():
    names = ["Mode"]
    with pytest.raises(TypeError):
        FrozenEnum(type_name=names, member_name="A", value=1)  # type: ignore[arg-type]
    names.append("changed")  # nothing was retained, so nothing to change


def test_scalar_metadata_stays_stable_after_commit():
    t, m = "pkg.Mode", "A"
    fe = FrozenEnum(t, m, {"v": [1]})
    ev = SimulationEvent(seq=0, kind=K.ASSIGNED, tick=0, receipt={"fe": fe})
    before = canonical_json(ev)
    t += "!"; m += "!"
    assert canonical_json(ev) == before
    assert (ev.receipt["fe"].type_name, ev.receipt["fe"].member_name) == ("pkg.Mode", "A")
    assert type(ev.receipt["fe"].type_name) is str and type(ev.receipt["fe"].member_name) is str


def test_direct_construction_cannot_bypass_validation_through_freeze():
    ok = FrozenEnum("t.T", "M", 1)
    # a malformed instance forced past the frozen dataclass is refused when frozen again
    object.__setattr__(ok, "type_name", ["x"])
    with pytest.raises(TypeError):
        freeze(ok)
    with pytest.raises(TypeError):
        SimulationEvent(seq=0, kind=K.ASSIGNED, tick=0, receipt={"fe": ok})
    # dataclasses.replace re-runs the constructor check
    good = FrozenEnum("t.T", "M", 1)
    with pytest.raises(TypeError):
        dataclasses.replace(good, member_name=["M"])


def test_nested_frozen_enum_in_payload_stays_immutable():
    inner_value = {"n": [1, 2]}
    fe = FrozenEnum("t.T", "M", inner_value)
    payload = {"outer": [fe, {"deep": (fe,)}]}
    ev = SimulationEvent(seq=0, kind=K.ASSIGNED, tick=0, receipt=payload)
    before = canonical_json(ev)
    inner_value["n"].append(3)
    payload["outer"].append("x")
    payload["outer"][1]["deep"] = ()
    assert canonical_json(ev) == before
    nested = ev.receipt["outer"][0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        nested.type_name = "other"
    with pytest.raises(TypeError):
        nested.value["n"] = ()
    with pytest.raises(AttributeError):
        ev.receipt["outer"][1]["deep"].append(1)


def test_mutation_through_exposed_history_cannot_change_bytes():
    eng, assigned = _committed(DictMode.A)
    before = canonical_json(eng.history)
    exposed = assigned.receipt["mode"]
    for attr in ("type_name", "member_name", "value"):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(exposed, attr, "x")
    assert type(exposed.type_name) is str and type(exposed.member_name) is str
    assert canonical_json(eng.history) == before


def test_ordinary_enum_conversion_keeps_qualified_names():
    f = freeze(Plain.LOW)
    assert f.type_name == f"{Plain.__module__}.{Plain.__qualname__}" and f.member_name == "LOW"
    assert type(f.type_name) is str and type(f.member_name) is str


def test_halted_payload_with_frozen_enum_is_immutable():
    value = {"why": ["x"]}
    fe = FrozenEnum("t.T", "M", value)
    halt = {"step": "ASSIGN", "reason": "INVALID_PROPOSAL", "passenger": 0, "unserved": 1, "ctx": fe}
    ev = SimulationEvent(seq=0, kind=K.HALTED, tick=0, passenger_id=0, halt=halt)
    before = canonical_json(ev)
    value["why"].append("y")
    halt["ctx"] = None
    assert canonical_json(ev) == before
    with pytest.raises(TypeError):
        ev.halt["ctx"] = None
    with pytest.raises(dataclasses.FrozenInstanceError):
        ev.halt["ctx"].member_name = "z"


def test_malformed_frozen_enum_payload_fails_closed_without_partial_commit():
    bad = FrozenEnum("t.T", "M", 1)
    object.__setattr__(bad, "member_name", ["M"])  # forced malformed instance

    class Policy:
        def assign(self, view, request):
            return Proposal(0, {"fe": bad})

    eng, _ = build([(0, "a", 0, 2), (0, "b", 1, 2)], floors=3, policy=Policy())
    out = eng.run()
    assert (out.standing, out.halt_reason, out.final_tick) == (HALTED, "INVALID_PROPOSAL", 0)
    assert eng.history.tick_records == () and eng.passengers == ()
    assert [e.kind for e in eng.history.events] == [K.HALTED]
    assert eng.step() is out


def test_scalar_subclasses_are_frozen_to_exact_builtins():
    class Evil(str):
        pass

    class EvilInt(int):
        pass

    frozen = freeze({"s": Evil("abc"), "i": EvilInt(7), Evil("k"): [Evil("v")]})
    assert type(frozen["s"]) is str and type(frozen["i"]) is int and type(frozen["k"][0]) is str
    assert all(type(k) is str for k in frozen)
