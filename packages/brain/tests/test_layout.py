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
            {"ref": "servo1", "type": "servo"},
        ],
        "nets": [["uno.D9", "servo1.signal"]],
    }

    result = plan_layout(fixture)

    assert result == {"placements": {}, "unplaced": ["servo1"]}


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
