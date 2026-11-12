import json
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets

LIVE6 = Path("/home/usuario/jarvis_data/logs/tinkercad-fase0/live6.json")
LIVE14 = Path("/home/usuario/jarvis_data/logs/tinkercad-fase0/live14.json")

EXPECTED_SERVO_POT = [
    ["potentiometer1.1", "servo1.vcc", "uno.5V"],
    ["potentiometer1.2", "uno.A0"],
    ["potentiometer1.3", "servo1.gnd", "uno.GND1"],
    ["servo1.signal", "uno.D9"],
]


def _comp(type_, instance_id):
    return {"type": type_, "instance_id": instance_id, "name": "1", "pins": []}


def _wire(source, target):
    return {"source": source, "target": target}


def _ep(component, pin, instance_id):
    return {"component": component, "pin": pin, "instance_id": instance_id}


def _blink_data():
    bb = ("Breadboard Small", "bb1")
    uno = ("Arduino Uno R3", "uno1")
    r = ("Resistor", "r_a")
    led = ("LED", "led_a")
    def e(comp, pin):
        return _ep(comp[0], pin, comp[1])

    wires = [
        _wire(e(uno, "D13"), e(bb, "i1")),
        _wire(e(r, "Terminal 1"), e(bb, "g1")),
        _wire(e(r, "Terminal 2"), e(bb, "g5")),
        _wire(e(led, "Anode"), e(bb, "i5")),
        _wire(e(led, "Cathode"), e(bb, "i6")),
        _wire(e(bb, "j6"), e(bb, "z6")),
        _wire(e(uno, "GND"), e(bb, "z1")),
    ]
    return {
        "components": [_comp(*uno), _comp(*bb), _comp(*r), _comp(*led)],
        "wires": wires,
    }


EXPECTED_BLINK = [
    ["led1.anode", "r1.2"],
    ["led1.cathode", "uno.GND1"],
    ["r1.1", "uno.D13"],
]


def test_blink_via_breadboard_continuity_and_rail():
    assert derive_nets(_blink_data()) == EXPECTED_BLINK


def test_duplicate_wires_do_not_duplicate_nets():
    data = _blink_data()
    data["wires"] = data["wires"] + data["wires"]
    assert derive_nets(data) == EXPECTED_BLINK


def test_opposite_halves_same_column_are_not_connected():
    data = _blink_data()
    # Move resistor pin 1 to e1: same column 1, opposite half (a-e vs f-j).
    data["wires"][1] = _wire(
        _ep("Resistor", "Terminal 1", "r_a"),
        _ep("Breadboard Small", "e1", "bb1"),
    )
    nets = derive_nets(data)
    assert ["r1.1", "uno.D13"] not in nets
    assert ["r1.1"] not in nets


def test_lower_half_and_different_rail_letters():
    data = {
        "components": [
            _comp("Arduino Uno R3", "uno1"),
            _comp("Breadboard Small", "bb1"),
            _comp("Resistor", "r_a"),
            _comp("LED", "led_a"),
        ],
        "wires": [
            _wire(_ep("Arduino Uno R3", "D13", "uno1"), _ep("Breadboard Small", "a3", "bb1")),
            _wire(_ep("Resistor", "Terminal 1", "r_a"), _ep("Breadboard Small", "e3", "bb1")),
            # Different rail letters must not join.
            _wire(_ep("Resistor", "Terminal 2", "r_a"), _ep("Breadboard Small", "z2", "bb1")),
            _wire(_ep("LED", "Anode", "led_a"), _ep("Breadboard Small", "y2", "bb1")),
        ],
    }
    assert derive_nets(data) == [["r1.1", "uno.D13"]]


def test_direct_wire_and_numbering_and_singletons_filtered():
    data = {
        "components": [
            _comp("Arduino Uno R3", "uno1"),
            _comp("Resistor", "r_a"),
            _comp("Resistor", "r_b"),
            _comp("LED", "led_a"),
        ],
        "wires": [
            _wire(_ep("Arduino Uno R3", "D13", "uno1"), _ep("Resistor", "Terminal 1", "r_a")),
            _wire(_ep("Resistor", "Terminal 2", "r_b"), _ep("LED", "Anode", "led_a")),
        ],
    }
    # Second resistor is r2; its single wire-less partner endpoints still form a net.
    assert derive_nets(data) == [["led1.anode", "r2.2"], ["r1.1", "uno.D13"]]


def test_empty_and_malformed():
    assert derive_nets({}) == []
    assert derive_nets({"components": [], "wires": []}) == []
    assert derive_nets({"wires": [{"source": {"pin": "D13"}}]}) == []


def test_servo_potentiometer_real_pin_aliases():
    data = {
        "components": [
            _comp("Arduino Uno R3", "uno1"),
            _comp("Micro Servo", "servo_a"),
            _comp("Potentiometer", "pot_a"),
        ],
        "wires": [
            _wire(_ep("Micro Servo", "Power", "servo_a"), _ep("Arduino Uno R3", "5V", "uno1")),
            _wire(_ep("Micro Servo", "Ground", "servo_a"), _ep("Arduino Uno R3", "GND", "uno1")),
            _wire(_ep("Micro Servo", "Signal", "servo_a"), _ep("Arduino Uno R3", "D9", "uno1")),
            _wire(_ep("Potentiometer", "Terminal 1", "pot_a"), _ep("Arduino Uno R3", "5V", "uno1")),
            _wire(_ep("Potentiometer", "Wiper", "pot_a"), _ep("Arduino Uno R3", "A0", "uno1")),
            _wire(_ep("Potentiometer", "Terminal 2", "pot_a"), _ep("Arduino Uno R3", "GND", "uno1")),
        ],
    }
    assert derive_nets(data) == EXPECTED_SERVO_POT


def test_generic_power_aliases_tmp36():
    data = {
        "components": [_comp("Arduino Uno R3", "uno1"), _comp("TMP36", "tmp_a")],
        "wires": [
            _wire(_ep("TMP36", "Vcc", "tmp_a"), _ep("Arduino Uno R3", "5V", "uno1")),
            _wire(_ep("TMP36", "Vout", "tmp_a"), _ep("Arduino Uno R3", "A0", "uno1")),
            _wire(_ep("TMP36", "Gnd", "tmp_a"), _ep("Arduino Uno R3", "GND", "uno1")),
        ],
    }
    assert derive_nets(data) == [
        ["tmp361.gnd", "uno.GND1"],
        ["tmp361.vcc", "uno.5V"],
        ["tmp361.vout", "uno.A0"],
    ]


def _inspect_from_artifact(path):
    entries = json.loads(path.read_text(encoding="utf-8"))
    for entry in entries:
        if entry.get("tool") == "tinkercad_inspect_circuit":
            return json.loads(entry["output"])
    return None


def test_live14_artifact_servo_pot_nets():
    if not LIVE14.exists():
        pytest.skip("live14.json no disponible")
    inspect_data = _inspect_from_artifact(LIVE14)
    if inspect_data is None:
        pytest.skip("live14.json sin inspect_circuit")
    assert derive_nets(inspect_data) == EXPECTED_SERVO_POT


def test_live6_artifact_blink_nets():
    if not LIVE6.exists():
        pytest.skip("live6.json no disponible")
    entries = json.loads(LIVE6.read_text(encoding="utf-8"))
    inspect_data = None
    for entry in entries:
        if entry.get("tool") == "tinkercad_inspect_circuit":
            inspect_data = json.loads(entry["output"])
            break
    if inspect_data is None:
        pytest.skip("live6.json sin inspect_circuit")
    nets = derive_nets(inspect_data)
    for expected in EXPECTED_BLINK:
        assert expected in nets
