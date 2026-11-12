import json
import re
from pathlib import Path

import pytest

import tinkercad_brain.builder as builder_module
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


_FIRST_PIN_3PIN = {"servo": "gnd", "potentiometer": "1", "tmp36": "vcc"}
_PIN_ORDER_3PIN = {
    "servo": ["gnd", "vcc", "signal"],
    "potentiometer": ["1", "2", "3"],
    "tmp36": ["vcc", "vout", "gnd"],
}


def _ensure_3pin_placements(monkeypatch):
    """Coloca en fila c las partes de 3 pines que el layout aun no coloque.

    Contrato documentado: `at` = hueco del primer pin fisico y los otros
    dos a +1/+2 columnas. Si plan_layout ya las coloca (merge del layout),
    este parche no altera nada.
    """
    real_plan_layout = builder_module.plan_layout

    def patched(fixture):
        layout = real_plan_layout(fixture)
        placements = dict(layout["placements"])
        type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}
        used_columns = {
            int(re.match(r"([0-9]+)c", p["at"]).group(1))
            for p in placements.values()
            if re.fullmatch(r"[0-9]+c", p["at"])
        }
        unplaced = []
        column = 1
        for ref in layout["unplaced"]:
            ctype = type_by_ref.get(ref)
            if ctype not in _FIRST_PIN_3PIN:
                unplaced.append(ref)
                continue
            while column in used_columns:
                column += 3
            placements[ref] = {
                "at": f"{column}c",
                "pin": _FIRST_PIN_3PIN[ctype],
                "angle": 0,
            }
            used_columns.add(column)
            column += 3
        return {"placements": placements, "unplaced": unplaced}

    monkeypatch.setattr(builder_module, "plan_layout", patched)


def _shift(hole, columns):
    match = re.fullmatch(r"([0-9]+)([a-j])", hole)
    return f"{int(match.group(1)) + columns}{match.group(2)}"


def _hole_for(placement, ctype, pin):
    index = _PIN_ORDER_3PIN[ctype].index(pin)
    return placement["at"] if index == 0 else _shift(placement["at"], index)


def test_servo_potentiometer_real_fixture_parts_and_wires(monkeypatch):
    fixture = _fixture("servo-potenciometro")
    _ensure_3pin_placements(monkeypatch)
    placements = builder_module.plan_layout(fixture)["placements"]
    type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}

    result = fixture_to_model_call(fixture)

    parts_by_ref = {p["ref"]: p for p in result["parts"]}
    assert parts_by_ref["servo1"] == {
        "ref": "servo1",
        "did": 142073,
        "at": placements["servo1"]["at"],
        "pin": "Ground",
        "angle": placements["servo1"]["angle"],
    }
    assert parts_by_ref["pot1"] == {
        "ref": "pot1",
        "did": 45547,
        "at": placements["pot1"]["at"],
        "pin": "term0",
        "angle": placements["pot1"]["angle"],
    }
    # Sin huecos repetidos como ancla.
    assert len({p["at"] for p in result["parts"]}) == len(result["parts"])

    expected_wires = []
    for net in fixture["nets"]:
        translated = []
        for endpoint in net:
            ref, pin = endpoint.split(".", 1)
            if ref == "uno":
                translated.append(endpoint)
            else:
                translated.append(
                    _hole_for(placements[ref], type_by_ref[ref], pin)
                )
        expected_wires.append(translated)
    assert result["wires"] == expected_wires
    assert len(result["wires"]) == 6


def test_tmp36_synthetic_fixture_parts_and_wires(monkeypatch):
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "tmp1", "type": "tmp36"},
        ],
        "nets": [
            ["uno.5V", "tmp1.vcc"],
            ["tmp1.vout", "uno.A0"],
            ["tmp1.gnd", "uno.GND1"],
        ],
    }
    _ensure_3pin_placements(monkeypatch)
    placement = builder_module.plan_layout(fixture)["placements"]["tmp1"]

    result = fixture_to_model_call(fixture)

    assert result["parts"] == [
        {
            "ref": "tmp1",
            "did": 112324,
            "at": placement["at"],
            "pin": "Vcc",
            "angle": placement["angle"],
        }
    ]
    assert result["wires"] == [
        ["uno.5V", placement["at"]],
        [_shift(placement["at"], 1), "uno.A0"],
        [_shift(placement["at"], 2), "uno.GND1"],
    ]


def test_ultrasonic_real_fixture_raises_build_error_unplaced():
    # Verificado hoy: plan_layout deja us1 en unplaced, asi que el
    # BuildError es por "sin layout" (antes de cualquier chequeo de DID;
    # ultrasonic-hcsr04 tampoco tiene DID en el builder).
    with pytest.raises(BuildError) as excinfo:
        fixture_to_model_call(_fixture("sensor-ultrasonico"))

    message = str(excinfo.value)
    assert "sin layout" in message
    assert "us1" in message


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
        build_circuit(_fixture("sensor-ultrasonico"), None, fake_call_tool)

    assert calls == []
