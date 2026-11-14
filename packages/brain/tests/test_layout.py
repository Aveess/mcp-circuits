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
            {"ref": "x1", "type": "unknown-widget"},
        ],
        "nets": [["uno.D9", "x1.echo"]],
    }

    result = plan_layout(fixture)

    assert result == {"placements": {}, "unplaced": ["x1"]}


def test_ultrasonic_alone_is_placed_at_18d_with_vcc_first():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "us1", "type": "ultrasonic-hcsr04"},
        ],
        "nets": [["uno.D7", "us1.trig"], ["uno.D6", "us1.echo"]],
    }

    result = plan_layout(fixture)

    assert result == {
        "placements": {"us1": {"at": "18d", "pin": "vcc", "angle": 0}},
        "unplaced": [],
    }


def test_ultrasonic_real_fixture_is_placed_after_led_block():
    result = plan_layout(_fixture("sensor-ultrasonico"))

    assert result["placements"]["us1"] == {"at": "18d", "pin": "vcc", "angle": 0}
    assert result["unplaced"] == []


def test_ultrasonic_shares_cursor_and_advances_five_after_servo():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "servo1", "type": "servo"},
            {"ref": "us1", "type": "ultrasonic-hcsr04"},
            {"ref": "tmp1", "type": "tmp36"},
        ],
        "nets": [],
    }

    result = plan_layout(fixture)

    assert result["placements"] == {
        "servo1": {"at": "1c", "pin": "gnd", "angle": 0},
        "us1": {"at": "18d", "pin": "vcc", "angle": 0},
        "tmp1": {"at": "23c", "pin": "vcc", "angle": 0},
    }
    assert result["unplaced"] == []


def test_ultrasonic_that_does_not_fit_goes_to_unplaced():
    components = [{"ref": "uno", "type": "arduino-uno"}]
    nets = []
    for i in range(1, 5):
        components.append({"ref": f"led{i}", "type": "led"})
        components.append({"ref": f"r{i}", "type": "resistor"})
        nets.append([f"r{i}.2", f"led{i}.anode"])
    components.append({"ref": "servo1", "type": "servo"})
    components.append({"ref": "us1", "type": "ultrasonic-hcsr04"})
    fixture = {"components": components, "nets": nets}

    result = plan_layout(fixture)

    assert result["placements"]["servo1"] == {"at": "25c", "pin": "gnd", "angle": 0}
    assert "us1" not in result["placements"]
    assert result["unplaced"] == ["us1"]


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


def test_led_rgb_real_fixture_places_rgb_and_resistors_by_color_net():
    # Nets map by color, not by name: r1->red (D9), r2->green (D10),
    # r3->blue (D11). First block: B=5.
    result = plan_layout(_fixture("led-rgb"))

    assert result == {
        "placements": {
            "rgb1": {"at": "5i", "pin": "red", "angle": 0},
            "r1": {"at": "1g", "pin": "1", "angle": 90},
            "r2": {"at": "4h", "pin": "1", "angle": 90},
            "r3": {"at": "3j", "pin": "1", "angle": 90},
        },
        "unplaced": [],
    }


def test_led_rgb_after_led_block_is_displaced_without_overlap():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "r0", "type": "resistor"},
            {"ref": "rgb1", "type": "led-rgb-common-cathode"},
            {"ref": "r1", "type": "resistor"},
            {"ref": "r2", "type": "resistor"},
            {"ref": "r3", "type": "resistor"},
        ],
        "nets": [
            ["r0.2", "led1.anode"],
            ["r1.2", "rgb1.red"],
            ["r2.2", "rgb1.green"],
            ["r3.2", "rgb1.blue"],
        ],
    }

    result = plan_layout(fixture)

    # LED block occupies the first cursor block (next free column 7), so
    # B = 7 + 4 = 11 and the RGB range 11..14 does not overlap it.
    assert result["placements"] == {
        "r0": {"at": "1g", "pin": "1", "angle": 90},
        "led1": {"at": "5i", "pin": "anode", "angle": 180},
        "rgb1": {"at": "11i", "pin": "red", "angle": 0},
        "r1": {"at": "7g", "pin": "1", "angle": 90},
        "r2": {"at": "10h", "pin": "1", "angle": 90},
        "r3": {"at": "9j", "pin": "1", "angle": 90},
    }
    assert result["unplaced"] == []
    rgb_columns = set(range(11, 15))
    assert rgb_columns.isdisjoint(range(1, 7))


def test_led_rgb_without_a_resistor_goes_all_to_unplaced():
    fixture = _fixture("led-rgb")
    fixture["components"] = [
        c for c in fixture["components"] if c["ref"] != "r3"
    ]
    fixture["nets"] = [
        net for net in fixture["nets"] if not any(e.startswith("r3.") for e in net)
    ]

    result = plan_layout(fixture)

    assert result == {"placements": {}, "unplaced": ["rgb1", "r1", "r2"]}


def test_led_rgb_without_a_color_net_goes_all_to_unplaced():
    fixture = _fixture("led-rgb")
    fixture["nets"] = [
        net for net in fixture["nets"] if net != ["r3.2", "rgb1.blue"]
    ]

    result = plan_layout(fixture)

    assert result == {
        "placements": {},
        "unplaced": ["rgb1", "r1", "r2", "r3"],
    }


def test_motor_dc_transistor_real_fixture_places_all_parts():
    result = plan_layout(_fixture("motor-dc-transistor"))

    assert result["placements"]["q1"] == {"at": "7c", "pin": "collector", "angle": 0}
    assert result["placements"]["motor1"] == {"free": {"x": 560, "y": 60}}
    diode = result["placements"]["d1"]
    assert diode["pin"] == "anode" and diode["angle"] == 90
    assert diode["at"].endswith("g")
    anode_column = int(diode["at"][:-1])
    cathode_column = anode_column - 4
    assert cathode_column == 11
    assert result["placements"]["r1"] == {"at": "1g", "pin": "1", "angle": 90}
    assert result["unplaced"] == []


def test_two_dc_motors_get_distinct_free_x():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "motor1", "type": "dc-motor"},
            {"ref": "motor2", "type": "dc-motor"},
        ],
        "nets": [],
    }

    result = plan_layout(fixture)

    assert result["placements"]["motor1"] == {"free": {"x": 560, "y": 60}}
    assert result["placements"]["motor2"] == {"free": {"x": 680, "y": 60}}
    assert result["unplaced"] == []


def test_diode_transistor_motor_do_not_overlap_led_or_rgb_blocks():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "r0", "type": "resistor"},
            {"ref": "rgb1", "type": "led-rgb-common-cathode"},
            {"ref": "r1", "type": "resistor"},
            {"ref": "r2", "type": "resistor"},
            {"ref": "r3", "type": "resistor"},
            {"ref": "q1", "type": "transistor-npn"},
            {"ref": "d1", "type": "diode"},
            {"ref": "motor1", "type": "dc-motor"},
        ],
        "nets": [
            ["r0.2", "led1.anode"],
            ["r1.2", "rgb1.red"],
            ["r2.2", "rgb1.green"],
            ["r3.2", "rgb1.blue"],
        ],
    }

    result = plan_layout(fixture)

    assert result["unplaced"] == []
    led_block = set(range(1, 7))
    rgb_column = int(result["placements"]["rgb1"]["at"][:-1])
    rgb_range = set(range(rgb_column - 4, rgb_column + 4))
    q_column = int(result["placements"]["q1"]["at"][:-1])
    q_range = set(range(q_column, q_column + 3))
    anode_column = int(result["placements"]["d1"]["at"][:-1])
    diode_range = set(range(anode_column - 4, anode_column + 1))
    assert diode_range.isdisjoint(led_block) and diode_range.isdisjoint(rgb_range)
    assert q_range.isdisjoint(led_block) and q_range.isdisjoint(rgb_range)
    assert result["placements"]["motor1"] == {"free": {"x": 560, "y": 60}}


def test_motor_l293d_bateria_fixture_loads_and_places_without_overlap():
    from tinkercad_brain.fase0.fixtures import load_fixtures

    circuits = load_fixtures(REAL_FIXTURES)
    assert len(circuits) == 12
    fixture = next(c for c in circuits if c["id"] == "motor-l293d-bateria")

    result = plan_layout(fixture)

    assert result["placements"]["drv1"] == {"at": "17f", "pin": "enable1", "angle": 180}
    assert result["placements"]["pot1"] == {"at": "1c", "pin": "1", "angle": 0}
    assert result["placements"]["motor1"] == {"free": {"x": 560, "y": 60}}
    assert result["placements"]["bat1"] == {"free": {"x": 560, "y": 300}}
    assert result["placements"]["motor1"] != result["placements"]["bat1"]
    assert result["unplaced"] == []
    pot_columns = set(range(1, 4))
    assert pot_columns.isdisjoint(range(10, 18))


def test_l293d_goes_to_unplaced_when_columns_10_to_17_are_occupied():
    # Two LED blocks occupy columns 1-6 and 7-12, overlapping 10-17.
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "r1", "type": "resistor"},
            {"ref": "led2", "type": "led"},
            {"ref": "r2", "type": "resistor"},
            {"ref": "drv1", "type": "l293d"},
        ],
        "nets": [["r1.2", "led1.anode"], ["r2.2", "led2.anode"]],
    }

    result = plan_layout(fixture)

    assert "drv1" not in result["placements"]
    assert result["unplaced"] == ["drv1"]


def test_blocks_after_l293d_do_not_overlap_its_columns():
    components = [{"ref": "uno", "type": "arduino-uno"}, {"ref": "drv1", "type": "l293d"}]
    for i in range(1, 6):
        components.append({"ref": f"pot{i}", "type": "potentiometer"})
    fixture = {"components": components, "nets": []}

    result = plan_layout(fixture)

    assert result["placements"]["drv1"] == {"at": "17f", "pin": "enable1", "angle": 180}
    for i in range(1, 6):
        placement = result["placements"][f"pot{i}"]
        start = int(placement["at"][:-1])
        assert set(range(start, start + 3)).isdisjoint(range(10, 18))


def test_output_is_deterministic_and_anchors_are_unique():
    fixture = _fixture("semaforo-3-leds")

    first = plan_layout(copy.deepcopy(fixture))
    second = plan_layout(copy.deepcopy(fixture))

    assert first == second
    anchors = [p["at"] for p in first["placements"].values()]
    assert len(anchors) == len(set(anchors))


def _anchor_columns(result):
    assert result["unplaced"] == []
    columns = [int(p["at"][:-1]) for p in result["placements"].values()]
    assert len(columns) == len(set(columns))
    return columns


def test_buzzer_real_fixture_places_positive_anchor_on_row_e_in_six_columns():
    result = plan_layout(_fixture("buzzer-activo"))

    assert result["placements"]["buzzer1"] == {"at": "1e", "pin": "+", "angle": 0}
    buzzer_columns = set(range(1, 1 + 6))
    button_column = int(result["placements"]["btn1"]["at"][:-1])
    assert button_column not in buzzer_columns
    assert result["unplaced"] == []

    # Same fixture plus an LED block: the buzzer block must not land on it.
    fixture = _fixture("buzzer-activo")
    fixture["components"].extend(
        [{"ref": "led1", "type": "led"}, {"ref": "r1", "type": "resistor"}]
    )
    fixture["nets"].extend([["r1.2", "led1.anode"]])
    with_led = plan_layout(fixture)

    led_column = int(with_led["placements"]["led1"]["at"][:-1])
    led_block = set(range(led_column - 4, led_column + 2))
    buzzer_column = int(with_led["placements"]["buzzer1"]["at"][:-1])
    assert buzzer_column not in led_block
    assert set(range(buzzer_column, buzzer_column + 6)).isdisjoint(led_block)


def test_ldr_real_fixture_places_divider_resistor_three_columns_right_on_row_e():
    result = plan_layout(_fixture("ldr-divisor"))

    assert result["placements"]["ldr1"] == {"at": "7e", "pin": "1", "angle": 0}
    assert result["placements"]["r1"] == {"at": "10e", "pin": "1", "angle": 90}
    ldr_column = int(result["placements"]["ldr1"]["at"][:-1])
    divider_column = int(result["placements"]["r1"]["at"][:-1])
    assert divider_column - ldr_column == 3
    # divider pin 2 lands 4 columns after pin 1, both inside the block.
    assert set(range(ldr_column, ldr_column + 2)).isdisjoint(
        range(divider_column, divider_column + 5)
    )
    _anchor_columns(result)


def test_parking_real_fixture_places_rgb_first_servo_and_ultrasonic_without_overlap():
    result = plan_layout(_fixture("parking-servo-ultrasonico-rgb"))

    assert result["unplaced"] == []
    assert result["placements"]["rgb1"] == {"at": "5i", "pin": "red", "angle": 0}
    assert result["placements"]["r1"] == {"at": "1g", "pin": "1", "angle": 90}
    assert result["placements"]["r2"] == {"at": "4h", "pin": "1", "angle": 90}
    assert result["placements"]["r3"] == {"at": "3j", "pin": "1", "angle": 90}
    ultrasonic_column = int(result["placements"]["us1"]["at"][:-1])
    assert ultrasonic_column >= 18
    _anchor_columns(result)


def test_ldr_without_divider_resistor_is_placed_alone():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "ldr1", "type": "photoresistor"},
        ],
        "nets": [["uno.5V", "ldr1.1"], ["ldr1.2", "uno.A0"]],
    }

    result = plan_layout(fixture)

    assert result == {
        "placements": {"ldr1": {"at": "1e", "pin": "1", "angle": 0}},
        "unplaced": [],
    }


def test_rgb_backfills_first_free_window_when_cursor_already_passed():
    # LED block 1-6, ultrasonic forced to 18-21, servo 23-25: the cursor
    # is at 27, so the RGB must not depend on being placed first.
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "r0", "type": "resistor"},
            {"ref": "us1", "type": "ultrasonic-hcsr04"},
            {"ref": "servo1", "type": "servo"},
            {"ref": "rgb1", "type": "led-rgb-common-cathode"},
            {"ref": "r1", "type": "resistor"},
            {"ref": "r2", "type": "resistor"},
            {"ref": "r3", "type": "resistor"},
        ],
        "nets": [
            ["r0.2", "led1.anode"],
            ["r1.2", "rgb1.red"],
            ["r2.2", "rgb1.green"],
            ["r3.2", "rgb1.blue"],
        ],
    }

    result = plan_layout(fixture)

    assert result["unplaced"] == []
    assert result["placements"]["rgb1"] == {"at": "11i", "pin": "red", "angle": 0}
    assert result["placements"]["r1"] == {"at": "7g", "pin": "1", "angle": 90}
    assert result["placements"]["r2"] == {"at": "10h", "pin": "1", "angle": 90}
    assert result["placements"]["r3"] == {"at": "9j", "pin": "1", "angle": 90}
    rgb_columns = set(range(7, 15))
    assert rgb_columns.isdisjoint(range(1, 7))
    assert rgb_columns.isdisjoint(range(18, 22))
    assert rgb_columns.isdisjoint(range(23, 26))
