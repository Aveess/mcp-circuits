import copy
import json
from pathlib import Path

from tinkercad_brain.layout import plan_layout

ROOT = Path(__file__).resolve().parents[1]
REAL_FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture(fixture_id):
    circuits = json.loads(REAL_FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == fixture_id)


def test_blink_basico_places_resistor_and_led_in_first_block():
    result = plan_layout(_fixture("blink-basico"))

    assert result == {
        "placements": {
            "r1": {"at": "1g", "pin": "1", "angle": 90},
            "led1": {"at": "5i", "pin": "anode", "angle": 180},
        },
        "unplaced": [],
    }
    assert "uno" not in result["placements"]
    assert "uno" not in result["unplaced"]


def test_semaforo_places_three_blocks_without_repeated_holes():
    result = plan_layout(_fixture("semaforo-3-leds"))

    assert result["placements"] == {
        "r1": {"at": "1g", "pin": "1", "angle": 90},
        "led_rojo": {"at": "5i", "pin": "anode", "angle": 180},
        "r2": {"at": "7g", "pin": "1", "angle": 90},
        "led_amarillo": {"at": "11i", "pin": "anode", "angle": 180},
        "r3": {"at": "13g", "pin": "1", "angle": 90},
        "led_verde": {"at": "17i", "pin": "anode", "angle": 180},
    }
    assert result["unplaced"] == []
    anchors = [p["at"] for p in result["placements"].values()]
    assert len(anchors) == len(set(anchors))


def test_pushbutton_is_placed_after_led_blocks_on_row_f():
    result = plan_layout(_fixture("boton-pullup"))

    assert result["placements"]["btn1"] == {"at": "7f", "pin": "1", "angle": 0}
    assert result["unplaced"] == []


def test_unknown_type_goes_to_unplaced():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "us1", "type": "ultrasonic-hcsr04"},
        ],
        "nets": [["uno.D9", "us1.echo"]],
    }

    result = plan_layout(fixture)

    assert result == {"placements": {}, "unplaced": ["us1"]}


def test_servo_alone_is_placed_at_1c_with_gnd_first():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "servo1", "type": "servo"},
        ],
        "nets": [["uno.D9", "servo1.signal"]],
    }

    result = plan_layout(fixture)

    assert result == {
        "placements": {"servo1": {"at": "1c", "pin": "gnd", "angle": 0}},
        "unplaced": [],
    }


def test_servo_and_potentiometer_blocks_do_not_overlap():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "servo1", "type": "servo"},
            {"ref": "pot1", "type": "potentiometer"},
        ],
        "nets": [],
    }

    result = plan_layout(fixture)

    assert result["placements"] == {
        "servo1": {"at": "1c", "pin": "gnd", "angle": 0},
        "pot1": {"at": "5c", "pin": "1", "angle": 0},
    }
    assert result["unplaced"] == []
    ranges = []
    for placement in result["placements"].values():
        start = int(placement["at"][:-1])
        ranges.append(set(range(start, start + 3)))
    assert ranges[0].isdisjoint(ranges[1])


def test_servo_is_placed_after_led_block():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "r1", "type": "resistor"},
            {"ref": "servo1", "type": "servo"},
        ],
        "nets": [["r1.2", "led1.anode"]],
    }

    result = plan_layout(fixture)

    assert result["placements"]["servo1"] == {"at": "7c", "pin": "gnd", "angle": 0}
    assert result["unplaced"] == []


def test_tmp36_is_placed_with_vcc_first():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "tmp1", "type": "tmp36"},
        ],
        "nets": [],
    }

    result = plan_layout(fixture)

    assert result == {
        "placements": {"tmp1": {"at": "1c", "pin": "vcc", "angle": 0}},
        "unplaced": [],
    }


def test_servo_that_does_not_fit_goes_to_unplaced_after_led_blocks_fill_board():
    components = [{"ref": "uno", "type": "arduino-uno"}]
    nets = []
    for i in range(1, 5):
        components.append({"ref": f"led{i}", "type": "led"})
        components.append({"ref": f"r{i}", "type": "resistor"})
        nets.append([f"r{i}.2", f"led{i}.anode"])
    components.append({"ref": "servo1", "type": "servo"})
    components.append({"ref": "servo2", "type": "servo"})
    fixture = {"components": components, "nets": nets}

    result = plan_layout(fixture)

    assert result["placements"]["servo1"] == {"at": "25c", "pin": "gnd", "angle": 0}
    assert "servo2" not in result["placements"]
    assert result["unplaced"] == ["servo2"]


def test_pushbutton_and_servo_do_not_share_columns():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "btn1", "type": "pushbutton"},
            {"ref": "servo1", "type": "servo"},
        ],
        "nets": [],
    }

    result = plan_layout(fixture)

    assert result["unplaced"] == []
    button_start = int(result["placements"]["btn1"]["at"][:-1])
    servo_start = int(result["placements"]["servo1"]["at"][:-1])
    assert button_start != servo_start
    assert button_start not in range(servo_start, servo_start + 3)


def test_fifth_led_block_goes_to_unplaced():
    components = [{"ref": "uno", "type": "arduino-uno"}]
    nets = []
    for i in range(1, 6):
        components.append({"ref": f"led{i}", "type": "led"})
        components.append({"ref": f"r{i}", "type": "resistor"})
        nets.append([f"r{i}.2", f"led{i}.anode"])
    fixture = {"components": components, "nets": nets}

    result = plan_layout(fixture)

    assert len([p for p in result["placements"].values() if p["pin"] == "anode"]) == 4
    assert "led5" in result["unplaced"]
    assert "led5" not in result["placements"]


def test_resistor_without_led_uses_next_free_block():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "r1", "type": "resistor"},
        ],
        "nets": [["uno.D13", "r1.1"]],
    }

    result = plan_layout(fixture)

    assert result == {
        "placements": {"r1": {"at": "1g", "pin": "1", "angle": 90}},
        "unplaced": [],
    }


def test_led_resistor_association_via_resistor_pin_1():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "r1", "type": "resistor"},
        ],
        "nets": [["led1.anode", "r1.1"]],
    }

    result = plan_layout(fixture)

    assert result["placements"]["r1"] == {"at": "1g", "pin": "1", "angle": 90}
    assert result["placements"]["led1"] == {"at": "5i", "pin": "anode", "angle": 180}


def test_output_is_deterministic_and_anchors_are_unique():
    fixture = _fixture("semaforo-3-leds")

    first = plan_layout(copy.deepcopy(fixture))
    second = plan_layout(copy.deepcopy(fixture))

    assert first == second
    anchors = [p["at"] for p in first["placements"].values()]
    assert len(anchors) == len(set(anchors))
