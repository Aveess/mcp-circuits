import json
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets

LIVE6 = Path("/home/usuario/jarvis_data/logs/tinkercad-fase0/live6.json")
LIVE14 = Path("/home/usuario/jarvis_data/logs/tinkercad-fase0/live14.json")
LIVE19 = Path("/home/usuario/jarvis_data/logs/tinkercad-fase0/live19.json")
LIVE21 = Path("/home/usuario/jarvis_data/logs/tinkercad-fase0/live21.json")
LIVE24 = Path("/home/usuario/jarvis_data/logs/tinkercad-fase0/live24.json")

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


def test_led_rgb_live_pin_names_red_green_blue_cathode():
    # Tipo y pines en vivo (circuito 6CynuRekrD2): "LED RGB", Red/Green/Blue/cathode.
    data = {
        "components": [
            _comp("Arduino Uno R3", "uno1"),
            _comp("LED RGB", "rgb_a"),
        ],
        "wires": [
            _wire(_ep("LED RGB", "Red", "rgb_a"), _ep("Arduino Uno R3", "D9", "uno1")),
            _wire(_ep("LED RGB", "Green", "rgb_a"), _ep("Arduino Uno R3", "D10", "uno1")),
            _wire(_ep("LED RGB", "Blue", "rgb_a"), _ep("Arduino Uno R3", "D11", "uno1")),
            _wire(_ep("LED RGB", "cathode", "rgb_a"), _ep("Arduino Uno R3", "GND", "uno1")),
        ],
    }
    nets = derive_nets(data)
    assert not any(
        ep.endswith((".Red", ".Green", ".Blue", ".Cathode")) for net in nets for ep in net
    )
    by_uno = {ep: net for net in nets for ep in net if ep.startswith("uno.")}
    assert any(ep.endswith(".red") for ep in by_uno["uno.D9"])
    assert any(ep.endswith(".green") for ep in by_uno["uno.D10"])
    assert any(ep.endswith(".blue") for ep in by_uno["uno.D11"])
    assert any(ep.endswith(".cathode") for ep in by_uno["uno.GND1"])


def test_led_rgb_terminal_aliases():
    data = {
        "components": [
            _comp("Arduino Uno R3", "uno1"),
            _comp("LED RGB", "rgb_a"),
        ],
        "wires": [
            _wire(_ep("LED RGB", "terminal-red", "rgb_a"), _ep("Arduino Uno R3", "D9", "uno1")),
            _wire(_ep("LED RGB", "terminal-green", "rgb_a"), _ep("Arduino Uno R3", "D10", "uno1")),
            _wire(_ep("LED RGB", "terminal-blue", "rgb_a"), _ep("Arduino Uno R3", "D11", "uno1")),
            _wire(_ep("LED RGB", "terminal-cathode", "rgb_a"), _ep("Arduino Uno R3", "GND", "uno1")),
        ],
    }
    nets = derive_nets(data)
    by_uno = {ep: net for net in nets for ep in net if ep.startswith("uno.")}
    assert any(ep.endswith(".red") for ep in by_uno["uno.D9"])
    assert any(ep.endswith(".green") for ep in by_uno["uno.D10"])
    assert any(ep.endswith(".blue") for ep in by_uno["uno.D11"])
    assert any(ep.endswith(".cathode") for ep in by_uno["uno.GND1"])


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


def test_tmp36_live_pin_names_power_gnd_and_uno_gnd_unchanged():
    data = {
        "components": [
            _comp("Arduino Uno R3", "uno1"),
            _comp("Temperature Sensor [TMP36]", "tmp_a"),
        ],
        "wires": [
            _wire(_ep("Temperature Sensor [TMP36]", "Power", "tmp_a"), _ep("Arduino Uno R3", "5V", "uno1")),
            _wire(_ep("Temperature Sensor [TMP36]", "Vout", "tmp_a"), _ep("Arduino Uno R3", "A0", "uno1")),
            _wire(_ep("Temperature Sensor [TMP36]", "GND", "tmp_a"), _ep("Arduino Uno R3", "GND", "uno1")),
        ],
    }
    nets = derive_nets(data)
    by_uno = {}
    for net in nets:
        for endpoint in net:
            if endpoint.startswith("uno."):
                by_uno[endpoint] = net
    assert any(ep.endswith(".vcc") for ep in by_uno["uno.5V"])
    assert any(ep.endswith(".vout") for ep in by_uno["uno.A0"])
    # El GND del Uno sigue canonizado a GND1; el del sensor es gnd.
    assert "uno.GND1" in by_uno["uno.GND1"]
    assert any(ep.endswith(".gnd") and not ep.startswith("uno.") for ep in by_uno["uno.GND1"])
    assert not any(ep.endswith((".Power", ".GND")) for net in nets for ep in net)


def test_ultrasonic_live_pin_names_trigger_echo_ground_power():
    # Tipo en vivo en live21: no resuelve a ultrasonic-hcsr04 en el mapa.
    data = {
        "components": [
            _comp("Arduino Uno R3", "uno1"),
            _comp("Ultrasonic Distance Sensor (4-pin)", "us_a"),
        ],
        "wires": [
            _wire(_ep("Ultrasonic Distance Sensor (4-pin)", "Power", "us_a"), _ep("Arduino Uno R3", "5V", "uno1")),
            _wire(_ep("Ultrasonic Distance Sensor (4-pin)", "Trigger", "us_a"), _ep("Arduino Uno R3", "D7", "uno1")),
            _wire(_ep("Ultrasonic Distance Sensor (4-pin)", "Echo", "us_a"), _ep("Arduino Uno R3", "D6", "uno1")),
            _wire(_ep("Ultrasonic Distance Sensor (4-pin)", "Ground", "us_a"), _ep("Arduino Uno R3", "GND", "uno1")),
        ],
    }
    nets = derive_nets(data)
    assert not any(
        ep.endswith((".Power", ".Trigger", ".Echo", ".Ground"))
        for net in nets
        for ep in net
    )
    by_uno = {ep: net for net in nets for ep in net if ep.startswith("uno.")}
    assert any(ep.endswith(".trig") for ep in by_uno["uno.D7"])
    assert any(ep.endswith(".echo") for ep in by_uno["uno.D6"])
    assert any(ep.endswith(".vcc") for ep in by_uno["uno.5V"])
    assert any(ep.endswith(".gnd") and not ep.startswith("uno.") for ep in by_uno["uno.GND1"])


def test_ultrasonic_canonical_type_aliases():
    data = {
        "components": [
            _comp("Arduino Uno R3", "uno1"),
            _comp("Ultrasonic Distance Sensor", "us_a"),
        ],
        "wires": [
            _wire(_ep("Ultrasonic Distance Sensor", "Trigger", "us_a"), _ep("Arduino Uno R3", "D7", "uno1")),
            _wire(_ep("Ultrasonic Distance Sensor", "Echo", "us_a"), _ep("Arduino Uno R3", "D6", "uno1")),
            _wire(_ep("Ultrasonic Distance Sensor", "Ground", "us_a"), _ep("Arduino Uno R3", "GND", "uno1")),
        ],
    }
    nets = derive_nets(data)
    assert any("uno.D7" in net and any(ep.endswith(".trig") for ep in net) for net in nets)
    assert any("uno.D6" in net and any(ep.endswith(".echo") for ep in net) for net in nets)
    assert any("uno.GND1" in net and any(ep.endswith(".gnd") for ep in net) for net in nets)


def test_live21_artifact_ultrasonic_nets():
    if not LIVE21.exists():
        pytest.skip("live21.json no disponible")
    inspect_data = _inspect_from_artifact(LIVE21)
    if inspect_data is None:
        pytest.skip("live21.json sin inspect_circuit")
    nets = derive_nets(inspect_data)
    assert not any(
        ep.endswith((".Power", ".Trigger", ".Echo", ".Ground"))
        for net in nets
        for ep in net
    )
    assert any("uno.D7" in net and any(ep.endswith(".trig") for ep in net) for net in nets)
    assert any("uno.D6" in net and any(ep.endswith(".echo") for ep in net) for net in nets)
    assert any("uno.5V" in net and any(ep.endswith(".vcc") for ep in net) for net in nets)
    assert any(
        "uno.GND1" in net and any(ep.endswith(".gnd") and not ep.startswith("uno.") for ep in net)
        for net in nets
    )


def test_transistor_npn_bjt_live_pin_names():
    data = {
        "components": [_comp("Arduino Uno R3", "uno1"), _comp("NPN Transistor (BJT)", "q_a")],
        "wires": [
            _wire(_ep("NPN Transistor (BJT)", "Collector", "q_a"), _ep("Arduino Uno R3", "D7", "uno1")),
            _wire(_ep("NPN Transistor (BJT)", "Base", "q_a"), _ep("Arduino Uno R3", "D9", "uno1")),
            _wire(_ep("NPN Transistor (BJT)", "Emitter", "q_a"), _ep("Arduino Uno R3", "GND", "uno1")),
        ],
    }
    assert derive_nets(data) == [
        ["transistornpn1.base", "uno.D9"],
        ["transistornpn1.collector", "uno.D7"],
        ["transistornpn1.emitter", "uno.GND1"],
    ]


def test_dc_motor_numeric_pins_positive_negative_and_resistor_unchanged():
    data = {
        "components": [
            _comp("Arduino Uno R3", "uno1"),
            _comp("DC Motor", "motor_a"),
            _comp("Resistor", "r_a"),
        ],
        "wires": [
            _wire(_ep("DC Motor", "1", "motor_a"), _ep("Arduino Uno R3", "5V", "uno1")),
            _wire(_ep("DC Motor", "2", "motor_a"), _ep("Resistor", "Terminal 1", "r_a")),
        ],
    }
    nets = derive_nets(data)
    flat = {ep for net in nets for ep in net}
    assert any(ep.endswith(".positive") for ep in flat)
    assert any(ep.endswith(".negative") for ep in flat)
    # El "1" (via Terminal 1) de la resistencia no se convierte.
    assert "r1.1" in flat
    assert not any(ep.startswith("r1.") and ep.endswith((".positive", ".negative")) for ep in flat)


def test_dc_motor_terminal_pins_positive_negative():
    data = {
        "components": [_comp("Arduino Uno R3", "uno1"), _comp("DC Motor", "motor_a")],
        "wires": [
            _wire(_ep("DC Motor", "Terminal 1", "motor_a"), _ep("Arduino Uno R3", "5V", "uno1")),
            _wire(_ep("DC Motor", "Terminal 2", "motor_a"), _ep("Arduino Uno R3", "GND", "uno1")),
        ],
    }
    nets = derive_nets(data)
    assert any("uno.5V" in net and any(ep.endswith(".positive") for ep in net) for net in nets)
    assert any("uno.GND1" in net and any(ep.endswith(".negative") for ep in net) for net in nets)


def test_battery_9v_capitalized_pins_positive_negative_and_others_unchanged():
    data = {
        "components": [
            _comp("Arduino Uno R3", "uno1"),
            _comp("9V Battery", "bat_a"),
            _comp("Resistor", "r_a"),
        ],
        "wires": [
            _wire(_ep("9V Battery", "Positive", "bat_a"), _ep("Arduino Uno R3", "5V", "uno1")),
            _wire(_ep("9V Battery", "Negative", "bat_a"), _ep("Arduino Uno R3", "GND", "uno1")),
            # Un "Positive" de otro tipo no entra en el alias acotado.
            _wire(_ep("Resistor", "Positive", "r_a"), _ep("Arduino Uno R3", "D9", "uno1")),
        ],
    }
    nets = derive_nets(data)
    flat = {ep for net in nets for ep in net}
    assert any("uno.5V" in net and "battery9v1.positive" in net for net in nets)
    assert any("uno.GND1" in net and "battery9v1.negative" in net for net in nets)
    assert "r1.Positive" in flat
    assert not any(ep.startswith("battery9v1.") and ep.endswith((".Positive", ".Negative")) for ep in flat)


def test_l293d_internal_schematic_pin_names():
    # Nombres del esquematico interno en los wires de inspect (en vivo);
    # la fixture usa enable1/enable2/vss/vs/inputN/outputN. Los GND ya
    # salen como gnd/gnd1/gnd2/gnd3 y deben pasar sin cambios.
    drv = "H-bridge Motor Driver [L293D]"
    cases = [
        ("Enable 1 & 2", "D9", "enable1"),
        ("Enable 3 & 4", "D10", "enable2"),
        ("Power 1", "5V", "vss"),
        ("Power 2", "A5", "vs"),
        ("Input 1", "D7", "input1"),
        ("Input 2", "D8", "input2"),
        ("Input 3", "D11", "input3"),
        ("Input 4", "D12", "input4"),
        ("Output 1", "D2", "output1"),
        ("Output 2", "D3", "output2"),
        ("Output 3", "D4", "output3"),
        ("Output 4", "D5", "output4"),
        ("gnd", "GND", "gnd"),
        ("gnd1", "A1", "gnd1"),
        ("gnd2", "A2", "gnd2"),
        ("gnd3", "A3", "gnd3"),
    ]
    data = {
        "components": [_comp("Arduino Uno R3", "uno1"), _comp(drv, "drv_a")],
        "wires": [
            _wire(
                _ep(drv, live_pin, "drv_a"),
                _ep("Arduino Uno R3", uno_pin, "uno1"),
            )
            for live_pin, uno_pin, _fixture_pin in cases
        ],
    }
    nets = derive_nets(data)
    flat = {ep for net in nets for ep in net}
    for _live_pin, uno_pin, fixture_pin in cases:
        uno_ep = "uno.GND1" if uno_pin == "GND" else f"uno.{uno_pin}"
        assert any(
            uno_ep in net and f"l293d1.{fixture_pin}" in net for net in nets
        ), fixture_pin
    assert not any(
        ep.startswith("l293d1.")
        and any(ch in ep for ch in (" ", "&"))
        for ep in flat
    )


def test_live24_artifact_transistor_nets():
    if not LIVE24.exists():
        pytest.skip("live24.json no disponible")
    inspect_data = _inspect_from_artifact(LIVE24)
    if inspect_data is None:
        pytest.skip("live24.json sin inspect_circuit")
    nets = derive_nets(inspect_data)
    assert not any(ep.endswith((".Collector", ".Base", ".Emitter")) for net in nets for ep in net)
    flat = {ep for net in nets for ep in net}
    assert {"transistornpn1.collector", "transistornpn1.base", "transistornpn1.emitter"} <= flat
    # Motor DC: positive en la net de 5V, negative en la del colector.
    assert any("uno.5V" in net and any(ep.endswith(".positive") for ep in net) for net in nets)
    assert any(
        "transistornpn1.collector" in net and any(ep.endswith(".negative") for ep in net)
        for net in nets
    )
    assert not any(ep.endswith((".1", ".2")) and "motor" in ep for net in nets for ep in net)


def test_live19_artifact_tmp36_nets():
    if not LIVE19.exists():
        pytest.skip("live19.json no disponible")
    inspect_data = _inspect_from_artifact(LIVE19)
    if inspect_data is None:
        pytest.skip("live19.json sin inspect_circuit")
    nets = derive_nets(inspect_data)
    assert not any(ep.endswith((".Power", ".GND")) for net in nets for ep in net)
    net_5v = next(net for net in nets if "uno.5V" in net)
    net_gnd = next(net for net in nets if "uno.GND1" in net and any(ep.endswith(".gnd") for ep in net))
    assert any(ep.endswith(".vcc") and not ep.startswith("uno.") for ep in net_5v)
    assert any(ep.endswith(".gnd") and not ep.startswith("uno.") for ep in net_gnd)


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
