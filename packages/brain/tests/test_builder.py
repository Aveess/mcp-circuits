import json
from pathlib import Path

import pytest

from tinkercad_brain.builder import BuildError, build_circuit, fixture_to_model_call
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.spec import validate_spec

ROOT = Path(__file__).resolve().parents[1]
REAL_FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture(fixture_id):
    circuits = json.loads(REAL_FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == fixture_id)


def test_blink_basico_produces_exact_parts_and_wires():
    fixture = _fixture("blink-basico")

    # Anclado al layout real, no a una copia inventada.
    assert plan_layout(fixture) == {
        "placements": {
            "r1": {"at": "1g", "pin": "1", "angle": 90},
            "led1": {"at": "5i", "pin": "anode", "angle": 180},
        },
        "unplaced": [],
    }

    result = fixture_to_model_call(fixture, code="void setup() {}")

    assert result == {
        "parts": [
            {"ref": "r1", "did": 53184, "at": "1g", "pin": "1", "angle": 90},
            {"ref": "led1", "did": 58422, "at": "5i", "pin": "anode", "angle": 180},
        ],
        "wires": [
            ["uno.D13", "1g"],
            ["5g", "5i"],
            ["6i", "uno.GND1"],
        ],
        "code": "void setup() {}",
    }


def test_blink_basico_code_defaults_to_none():
    assert fixture_to_model_call(_fixture("blink-basico"))["code"] is None


def test_blink_basico_wrapped_with_types_passes_validate_spec():
    fixture = _fixture("blink-basico")
    result = fixture_to_model_call(fixture)
    type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}

    wrapped = {
        "parts": [
            {**part, "type": type_by_ref[part["ref"]]} for part in result["parts"]
        ],
        "wires": result["wires"],
    }

    validated = validate_spec(wrapped)
    assert validated["wires"] == [
        {"from": a, "to": b} for a, b in result["wires"]
    ]


def test_unplaced_servo_fixture_raises_build_error_listing_refs():
    with pytest.raises(BuildError) as excinfo:
        fixture_to_model_call(_fixture("servo-potenciometro"))

    message = str(excinfo.value)
    assert "servo1" in message
    assert "pot1" in message


def test_pushbutton_pin2_raises_build_error_unknown_geometry():
    # Supuesto documentado: solo se conoce la geometria del pin "1" del
    # boton (en `at`). El pin "2" de boton-pullup no se adivina: sin una
    # medicion de la geometria completa del pushbutton, es BuildError.
    with pytest.raises(BuildError) as excinfo:
        fixture_to_model_call(_fixture("boton-pullup"))

    assert "btn1.2" in str(excinfo.value)


def test_net_with_more_than_two_endpoints_splits_into_consecutive_pairs():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "r1", "type": "resistor"},
        ],
        "nets": [["uno.5V", "r1.1", "led1.anode"], ["led1.cathode", "uno.GND1"]],
    }

    result = fixture_to_model_call(fixture)

    assert result["wires"] == [
        ["uno.5V", "1g"],
        ["1g", "5i"],
        ["6i", "uno.GND1"],
    ]


def test_build_circuit_success_true_records_both_steps():
    calls = []

    def fake_call_tool(tool, arguments):
        calls.append((tool, arguments))
        if tool == "tinkercad_build_circuit_model":
            return json.dumps({"success": True})
        return json.dumps({"components": []})

    result = build_circuit(_fixture("blink-basico"), "void setup() {}", fake_call_tool)

    assert [tool for tool, _ in calls] == [
        "tinkercad_build_circuit_model",
        "tinkercad_inspect_circuit",
    ]
    assert calls[0][1] == fixture_to_model_call(
        _fixture("blink-basico"), "void setup() {}"
    )
    assert calls[1][1] == {}
    assert result["model_result"] == {"success": True}
    assert [r.tool for r in result["records"]] == [
        "tinkercad_build_circuit_model",
        "tinkercad_inspect_circuit",
    ]
    assert all(r.ok for r in result["records"])


def test_build_circuit_success_false_does_not_raise_and_is_recorded():
    def fake_call_tool(tool, arguments):
        if tool == "tinkercad_build_circuit_model":
            return json.dumps({"success": False, "error": "boom"})
        return "inspected"

    result = build_circuit(_fixture("blink-basico"), None, fake_call_tool)

    assert result["model_result"] == {"success": False, "error": "boom"}
    assert len(result["records"]) == 2
    assert result["records"][0].ok is True
    assert json.loads(result["records"][0].output) == {
        "success": False,
        "error": "boom",
    }
    assert result["records"][1].output == "inspected"


def test_build_circuit_non_json_model_output_stays_text():
    def fake_call_tool(tool, arguments):
        return "plain-output"

    result = build_circuit(_fixture("blink-basico"), None, fake_call_tool)

    assert result["model_result"] == "plain-output"


def test_build_circuit_unplaced_fixture_raises_before_any_tool_call():
    calls = []

    def fake_call_tool(tool, arguments):
        calls.append(tool)
        return "{}"

    with pytest.raises(BuildError):
        build_circuit(_fixture("servo-potenciometro"), None, fake_call_tool)

    assert calls == []
