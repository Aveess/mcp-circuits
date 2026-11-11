import pytest

from tinkercad_brain.spec import SpecError, validate_spec


def blink_spec():
    return {
        "title": "Blink",
        "parts": [
            {
                "ref": "led1",
                "type": "led",
                "at": "9i",
                "pin": "anode",
                "angle": 180,
                "props": {"ohms": 220},
            },
            {"ref": "r1", "type": "resistor", "at": "5i", "pin": "1"},
        ],
        "wires": [["uno.D13", "5i"], ["10h", "T-10"]],
        "code": "void setup() {}",
    }


def test_blink_valid_passes_and_normalizes_wires():
    out = validate_spec(blink_spec())
    assert out["title"] == "Blink"
    assert out["parts"] == blink_spec()["parts"]
    assert out["wires"] == [
        {"from": "uno.D13", "to": "5i"},
        {"from": "10h", "to": "T-10"},
    ]
    assert out["code"] == "void setup() {}"


def test_wires_as_tuples_normalize():
    spec = blink_spec()
    spec["wires"] = [("uno.D13", "5i")]
    out = validate_spec(spec)
    assert out["wires"] == [{"from": "uno.D13", "to": "5i"}]


def test_wires_already_dicts_pass():
    spec = blink_spec()
    spec["wires"] = [{"from": "uno.D13", "to": "5i"}]
    out = validate_spec(spec)
    assert out["wires"] == [{"from": "uno.D13", "to": "5i"}]


def test_missing_parts_rejected():
    with pytest.raises(SpecError, match="parts"):
        validate_spec({"title": "x", "wires": []})


def test_parts_not_list_rejected():
    with pytest.raises(SpecError, match="parts"):
        validate_spec({"parts": "led1"})


def test_too_many_parts_rejected():
    spec = blink_spec()
    spec["parts"] = [
        {"ref": f"led{i}", "type": "led", "at": "1a"} for i in range(61)
    ]
    spec["wires"] = []
    with pytest.raises(SpecError, match="parts"):
        validate_spec(spec)


def test_too_many_wires_rejected():
    spec = blink_spec()
    spec["wires"] = [["uno.D13", "5i"]] * 151
    with pytest.raises(SpecError, match="wires"):
        validate_spec(spec)


def test_duplicate_ref_rejected():
    spec = blink_spec()
    spec["parts"].append({"ref": "led1", "type": "led", "at": "10i"})
    with pytest.raises(SpecError, match="duplicado|duplicate"):
        validate_spec(spec)


def test_ref_uno_reserved_rejected():
    spec = blink_spec()
    spec["parts"] = [{"ref": "uno", "type": "led", "at": "1a"}]
    with pytest.raises(SpecError, match="uno"):
        validate_spec(spec)


@pytest.mark.parametrize("ref", ["1led", "led-1", "led 1", "", "led.1", "led$"])
def test_ref_invalid_chars_rejected(ref):
    spec = blink_spec()
    spec["parts"] = [{"ref": ref, "type": "led", "at": "1a"}]
    spec["wires"] = []
    with pytest.raises(SpecError, match="ref"):
        validate_spec(spec)


def test_unknown_type_rejected():
    spec = blink_spec()
    spec["parts"] = [{"ref": "c1", "type": "capacitor", "at": "1a"}]
    spec["wires"] = []
    with pytest.raises(SpecError, match="type"):
        validate_spec(spec)


def test_fixture_only_types_accepted():
    # transistor-npn y diode aparecen en fixtures pero no en component_map.
    spec = {
        "parts": [
            {"ref": "q1", "type": "transistor-npn", "at": "5e", "pin": "base"},
            {"ref": "d1", "type": "diode", "at": "6e", "pin": "anode"},
        ],
        "wires": [["q1.collector", "d1.cathode"]],
    }
    out = validate_spec(spec)
    assert out["wires"] == [{"from": "q1.collector", "to": "d1.cathode"}]


@pytest.mark.parametrize(
    "at", ["31a", "0a", "1k", "a1", "T-31", "T-0", "X+1", "1A", "301a", "T*2", ""]
)
def test_at_invalid_rejected(at):
    spec = blink_spec()
    spec["parts"] = [{"ref": "led1", "type": "led", "at": at}]
    spec["wires"] = []
    with pytest.raises(SpecError, match="at"):
        validate_spec(spec)


def test_neither_at_nor_free_rejected():
    spec = blink_spec()
    spec["parts"] = [{"ref": "led1", "type": "led"}]
    spec["wires"] = []
    with pytest.raises(SpecError, match="at|free"):
        validate_spec(spec)


def test_rail_without_column_valid():
    spec = blink_spec()
    spec["parts"] = [{"ref": "led1", "type": "led", "at": "T-"}]
    spec["wires"] = [["led1.cathode", "B+"], ["uno.GND1", "T-"]]
    out = validate_spec(spec)
    assert out["parts"][0]["at"] == "T-"


def test_free_valid_without_at():
    spec = blink_spec()
    spec["parts"] = [
        {"ref": "led1", "type": "led", "free": {"x": 120, "y": 40}, "pin": "anode"}
    ]
    spec["wires"] = [["uno.D13", "led1.anode"]]
    out = validate_spec(spec)
    assert out["parts"][0]["free"] == {"x": 120, "y": 40}


def test_free_invalid_rejected():
    spec = blink_spec()
    spec["parts"] = [{"ref": "led1", "type": "led", "free": {"x": 1}}]
    spec["wires"] = []
    with pytest.raises(SpecError, match="free"):
        validate_spec(spec)


def test_pin_unknown_for_type_rejected():
    spec = blink_spec()
    spec["parts"] = [{"ref": "led1", "type": "led", "at": "1a", "pin": "foo"}]
    spec["wires"] = []
    with pytest.raises(SpecError, match="pin"):
        validate_spec(spec)


@pytest.mark.parametrize(
    "endpoint", ["99z", "foo", "T-99", "31a", "", "uno", ".anode", "led1."]
)
def test_wire_endpoint_invalid_rejected(endpoint):
    spec = blink_spec()
    spec["wires"] = [[endpoint, "5i"]]
    with pytest.raises(SpecError, match="wire|endpoint|extremo"):
        validate_spec(spec)


def test_wire_ref_undeclared_rejected():
    spec = blink_spec()
    spec["wires"] = [["led9.anode", "5i"]]
    with pytest.raises(SpecError, match="led9|no declarado|undeclared"):
        validate_spec(spec)


def test_wire_ref_pin_unknown_rejected():
    spec = blink_spec()
    spec["wires"] = [["led1.foo", "5i"]]
    with pytest.raises(SpecError, match="pin"):
        validate_spec(spec)


@pytest.mark.parametrize("endpoint", ["uno.D14", "uno.GND", "uno.X1", "uno.D", "uno."])
def test_wire_uno_pin_invalid_rejected(endpoint):
    spec = blink_spec()
    spec["wires"] = [[endpoint, "5i"]]
    with pytest.raises(SpecError, match="uno|pin"):
        validate_spec(spec)


@pytest.mark.parametrize(
    "pin", ["D0", "D13", "A0", "A5", "5V", "3V3", "VIN", "GND1", "GND2", "GND3",
            "AREF", "IOREF", "RESET", "SDA", "SCL"]
)
def test_wire_uno_pins_valid(pin):
    spec = blink_spec()
    spec["wires"] = [[f"uno.{pin}", "5i"]]
    out = validate_spec(spec)
    assert out["wires"][0]["from"] == f"uno.{pin}"


def test_wire_malformed_rejected():
    spec = blink_spec()
    spec["wires"] = [["uno.D13"]]
    with pytest.raises(SpecError, match="wire"):
        validate_spec(spec)
