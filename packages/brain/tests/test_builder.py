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
            {"from": "6i", "to": "uno.GND1", "color": "black"},
            {"from": "5g", "to": "5i", "color": "blue"},
            {"from": "uno.D13", "to": "1g", "color": "green"},
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
        {"from": w["from"], "to": w["to"]} for w in result["wires"]
    ]


def test_blink_wires_exact_order_and_colors_by_group():
    result = fixture_to_model_call(_fixture("blink-basico"))

    # Sin alimentacion: primero tierra (black), luego senales por "from".
    assert result["wires"] == [
        {"from": "6i", "to": "uno.GND1", "color": "black"},
        {"from": "5g", "to": "5i", "color": "blue"},
        {"from": "uno.D13", "to": "1g", "color": "green"},
    ]


def test_semaforo_wires_exact_order_and_colors_by_group():
    result = fixture_to_model_call(_fixture("semaforo-3-leds"))

    # Sin alimentacion: tierra ordenada por "from", luego senales por
    # "from" con la paleta rotando sin repetir consecutivos.
    assert result["wires"] == [
        {"from": "12i", "to": "uno.GND1", "color": "black"},
        {"from": "18i", "to": "uno.GND1", "color": "black"},
        {"from": "6i", "to": "uno.GND1", "color": "black"},
        {"from": "11g", "to": "11i", "color": "blue"},
        {"from": "17g", "to": "17i", "color": "green"},
        {"from": "5g", "to": "5i", "color": "orange"},
        {"from": "uno.D10", "to": "7g", "color": "yellow"},
        {"from": "uno.D11", "to": "1g", "color": "purple"},
        {"from": "uno.D9", "to": "13g", "color": "turquoise"},
    ]


def test_wires_are_bridge_dicts_with_from_to_color():
    for fixture_id in ("blink-basico", "semaforo-3-leds"):
        wires = fixture_to_model_call(_fixture(fixture_id))["wires"]
        assert wires
        for wire in wires:
            assert isinstance(wire, dict)
            assert set(wire) == {"from", "to", "color"}
            assert all(isinstance(wire[k], str) and wire[k] for k in wire)
        signal_colors = [
            w["color"] for w in wires if w["color"] not in ("black", "red")
        ]
        assert all(
            a != b for a, b in zip(signal_colors, signal_colors[1:])
        )


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

    def hole(ref, pin):
        return _hole_for(placements[ref], type_by_ref[ref], pin)

    # Alimentacion (red, "from" empatado: orden estable de las nets),
    # tierra (black) y senales (paleta), cada grupo ordenado por "from".
    assert result["wires"] == [
        {"from": "uno.5V", "to": hole("servo1", "vcc"), "color": "red"},
        {"from": "uno.5V", "to": hole("pot1", "1"), "color": "red"},
        {"from": hole("servo1", "gnd"), "to": "uno.GND1", "color": "black"},
        {"from": hole("pot1", "3"), "to": "uno.GND1", "color": "black"},
        {"from": hole("pot1", "2"), "to": "uno.A0", "color": "blue"},
        {"from": "uno.D9", "to": hole("servo1", "signal"), "color": "green"},
    ]
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
        {"from": "uno.5V", "to": placement["at"], "color": "red"},
        {
            "from": _shift(placement["at"], 2),
            "to": "uno.GND1",
            "color": "black",
        },
        {
            "from": _shift(placement["at"], 1),
            "to": "uno.A0",
            "color": "blue",
        },
    ]


_ULTRASONIC_PIN_ORDER = ["vcc", "trig", "echo", "gnd"]


def _ensure_ultrasonic_placement(monkeypatch):
    """Inyecta el placement esperado del layout si aun no lo emite.

    Contrato (agente layout): {"at": "<col>d", "pin": "vcc", "angle": 0}.
    Si plan_layout ya lo coloca, este parche no altera nada.
    """
    real_plan_layout = builder_module.plan_layout

    def patched(fixture):
        layout = real_plan_layout(fixture)
        placements = dict(layout["placements"])
        type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}
        unplaced = []
        for ref in layout["unplaced"]:
            if type_by_ref.get(ref) != "ultrasonic-hcsr04":
                unplaced.append(ref)
                continue
            placements[ref] = {"at": "20d", "pin": "vcc", "angle": 0}
        return {"placements": placements, "unplaced": unplaced}

    monkeypatch.setattr(builder_module, "plan_layout", patched)


def _ultrasonic_hole(placement, pin):
    index = _ULTRASONIC_PIN_ORDER.index(pin)
    return placement["at"] if index == 0 else _shift(placement["at"], index)


def test_ultrasonic_synthetic_parts_and_wires(monkeypatch):
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "us1", "type": "ultrasonic-hcsr04"},
        ],
        "nets": [
            ["uno.5V", "us1.vcc"],
            ["us1.gnd", "uno.GND1"],
            ["uno.D7", "us1.trig"],
            ["uno.D6", "us1.echo"],
        ],
    }
    _ensure_ultrasonic_placement(monkeypatch)
    placement = builder_module.plan_layout(fixture)["placements"]["us1"]
    # Contrato del layout para el ancla.
    assert placement["pin"] == "vcc"
    assert placement["at"].endswith("d")

    result = fixture_to_model_call(fixture)

    assert result["parts"] == [
        {
            "ref": "us1",
            "did": 219295,
            "at": placement["at"],
            "pin": "pos",
            "angle": placement["angle"],
        }
    ]
    assert result["wires"] == [
        {"from": "uno.5V", "to": _ultrasonic_hole(placement, "vcc"), "color": "red"},
        {
            "from": _ultrasonic_hole(placement, "gnd"),
            "to": "uno.GND1",
            "color": "black",
        },
        {"from": "uno.D6", "to": _ultrasonic_hole(placement, "echo"), "color": "blue"},
        {"from": "uno.D7", "to": _ultrasonic_hole(placement, "trig"), "color": "green"},
    ]


def test_ultrasonic_real_fixture_parts_and_wires(monkeypatch):
    fixture = _fixture("sensor-ultrasonico")
    _ensure_ultrasonic_placement(monkeypatch)
    placement = builder_module.plan_layout(fixture)["placements"]["us1"]

    result = fixture_to_model_call(fixture)

    parts_by_ref = {p["ref"]: p for p in result["parts"]}
    assert parts_by_ref["us1"] == {
        "ref": "us1",
        "did": 219295,
        "at": placement["at"],
        "pin": "pos",
        "angle": placement["angle"],
    }
    # Los 4 huecos del HC-SR04 aparecen como extremos de wire.
    wire_ends = {w["from"] for w in result["wires"]} | {
        w["to"] for w in result["wires"]
    }
    for pin in _ULTRASONIC_PIN_ORDER:
        assert _ultrasonic_hole(placement, pin) in wire_ends


def test_ultrasonic_real_fixture_builds_with_did():
    # Integracion final: el layout ya coloca el HC-SR04 (fila d) y el
    # builder lo traduce con su DID real.
    result = fixture_to_model_call(_fixture("sensor-ultrasonico"))
    us = next(p for p in result["parts"] if p["ref"] == "us1")
    assert us["did"] == 219295
    assert us["pin"] == "pos"


_RGB_PIN_ORDER = ["red", "cathode", "blue", "green"]


def _ensure_rgb_placement(monkeypatch):
    """Inyecta el placement esperado del layout si aun no lo emite.

    Contrato (agente layout): {"at": "<col>i", "pin": "red", "angle": ...}
    con red en `at` y cathode/blue/green a +1/+2/+3. Si plan_layout ya
    lo coloca, este parche no altera nada. Dependencia: hoy el layout
    deja rgb1 en unplaced.
    """
    real_plan_layout = builder_module.plan_layout

    def patched(fixture):
        layout = real_plan_layout(fixture)
        placements = dict(layout["placements"])
        type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}
        unplaced = []
        for ref in layout["unplaced"]:
            if type_by_ref.get(ref) != "led-rgb-common-cathode":
                unplaced.append(ref)
                continue
            placements[ref] = {"at": "5i", "pin": "red", "angle": 180}
        return {"placements": placements, "unplaced": unplaced}

    monkeypatch.setattr(builder_module, "plan_layout", patched)


def _rgb_hole(placement, pin):
    index = _RGB_PIN_ORDER.index(pin)
    return placement["at"] if index == 0 else _shift(placement["at"], index)


def test_led_rgb_real_fixture_parts_and_wires(monkeypatch):
    fixture = _fixture("led-rgb")
    _ensure_rgb_placement(monkeypatch)
    placements = builder_module.plan_layout(fixture)["placements"]
    placement = placements["rgb1"]
    # Contrato del layout para el ancla.
    assert placement["pin"] == "red"
    assert placement["at"].endswith("i")

    result = fixture_to_model_call(fixture)

    parts_by_ref = {p["ref"]: p for p in result["parts"]}
    assert parts_by_ref["rgb1"] == {
        "ref": "rgb1",
        "did": 58456,
        "at": placement["at"],
        "pin": "terminal-red",
        "angle": placement["angle"],
    }
    for ref in ("r1", "r2", "r3"):
        assert parts_by_ref[ref]["did"] == 53184
    assert set(parts_by_ref) == {"rgb1", "r1", "r2", "r3"}

    def resistor_hole(ref, pin):
        at = placements[ref]["at"]
        return at if pin == "1" else _shift(at, 4)

    # Orden fisico verificado en vivo: blue=+2, green=+3 (no al reves).
    blue_hole = _shift(placement["at"], 2)
    green_hole = _shift(placement["at"], 3)
    assert _rgb_hole(placement, "blue") == blue_hole
    assert _rgb_hole(placement, "green") == green_hole
    assert blue_hole != green_hole

    # Las 7 nets de la fixture, ya traducidas a huecos.
    expected_pairs = {
        ("uno.D9", resistor_hole("r1", "1")),
        (resistor_hole("r1", "2"), _rgb_hole(placement, "red")),
        ("uno.D10", resistor_hole("r2", "1")),
        (resistor_hole("r2", "2"), green_hole),
        ("uno.D11", resistor_hole("r3", "1")),
        (resistor_hole("r3", "2"), blue_hole),
        (_rgb_hole(placement, "cathode"), "uno.GND1"),
    }
    assert len(result["wires"]) == 7
    assert {(w["from"], w["to"]) for w in result["wires"]} == expected_pairs

    # Catodo a GND en negro; el resto son senales con color (sin negro/rojo).
    cathode_wire = next(w for w in result["wires"] if w["to"] == "uno.GND1")
    assert cathode_wire == {
        "from": _shift(placement["at"], 1),
        "to": "uno.GND1",
        "color": "black",
    }
    signal_wires = [w for w in result["wires"] if w is not cathode_wire]
    assert signal_wires
    assert all(w["color"] not in ("black", "red") for w in signal_wires)


def test_motor_dc_transistor_real_fixture_parts_and_wires():
    fixture = _fixture("motor-dc-transistor")
    placements = plan_layout(fixture)["placements"]
    # Contratos del layout ya mergeado.
    assert placements["q1"]["pin"] == "collector"
    assert placements["q1"]["at"].endswith("c")
    assert placements["d1"]["pin"] == "anode"
    assert placements["motor1"] == {"free": {"x": 560, "y": 60}}

    result = fixture_to_model_call(fixture)

    parts_by_ref = {p["ref"]: p for p in result["parts"]}
    assert set(parts_by_ref) == {"r1", "motor1", "q1", "d1"}
    assert parts_by_ref["q1"] == {
        "ref": "q1", "did": 58468, "at": placements["q1"]["at"],
        "pin": "collector", "angle": placements["q1"]["angle"],
    }
    assert parts_by_ref["d1"] == {
        "ref": "d1", "did": 58320, "at": placements["d1"]["at"],
        "pin": "anode", "angle": placements["d1"]["angle"],
    }
    # Motor libre: sin at/pin/angle.
    assert parts_by_ref["motor1"] == {
        "ref": "motor1", "did": 114158, "free": {"x": 560, "y": 60},
    }
    assert parts_by_ref["r1"]["did"] == 53184

    q1, d1, r1 = placements["q1"]["at"], placements["d1"]["at"], placements["r1"]["at"]
    base, emitter = _shift(q1, 1), _shift(q1, 2)
    cathode = _shift(d1, -4)  # catodo 4 columnas antes que el anodo
    expected_pairs = {
        ("uno.D9", r1),
        (_shift(r1, 4), base),
        (emitter, "uno.GND1"),
        (q1, "motor1.2"),
        ("motor1.2", d1),
        ("motor1.1", "uno.5V"),
        ("uno.5V", cathode),
    }
    assert len(result["wires"]) == 7
    assert {(w["from"], w["to"]) for w in result["wires"]} == expected_pairs

    # Conectividad de las nets de 3 extremos tras descomponer en pares.
    graph = {}
    for w in result["wires"]:
        graph.setdefault(w["from"], set()).add(w["to"])
        graph.setdefault(w["to"], set()).add(w["from"])

    def connected(a, b):
        seen, stack = set(), [a]
        while stack:
            node = stack.pop()
            if node == b:
                return True
            if node not in seen:
                seen.add(node)
                stack.extend(graph.get(node, ()))
        return False

    assert connected(q1, "motor1.2") and connected("motor1.2", d1)
    assert connected("motor1.1", "uno.5V") and connected("uno.5V", cathode)
    # Colores por grupo: 5V rojo, GND negro.
    assert next(w for w in result["wires"] if w["to"] == "uno.5V")["color"] == "red"
    assert next(w for w in result["wires"] if w["to"] == "uno.GND1")["color"] == "black"


def _ensure_l293d_battery_placements(monkeypatch):
    """Inyecta placements esperados si el layout aun no los emite.

    Contrato: l293d {"at": "10f", "pin": "enable1", "angle": 0} y
    battery-9v free {"x": 560, "y": 300} (como el dc-motor).
    Dependencia: hoy el layout deja ambos en unplaced.
    """
    real_plan_layout = builder_module.plan_layout

    def patched(fixture):
        layout = real_plan_layout(fixture)
        placements = dict(layout["placements"])
        type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}
        unplaced = []
        for ref in layout["unplaced"]:
            ctype = type_by_ref.get(ref)
            if ctype == "l293d":
                placements[ref] = {"at": "10f", "pin": "enable1", "angle": 0}
            elif ctype == "battery-9v":
                placements[ref] = {"free": {"x": 560, "y": 300}}
            else:
                unplaced.append(ref)
        return {"placements": placements, "unplaced": unplaced}

    monkeypatch.setattr(builder_module, "plan_layout", patched)


def test_motor_l293d_bateria_synthetic_parts_and_wires(monkeypatch):
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "bat1", "type": "battery-9v"},
            {"ref": "drv1", "type": "l293d"},
            {"ref": "motor1", "type": "dc-motor"},
            {"ref": "pot1", "type": "potentiometer"},
        ],
        "nets": [
            ["uno.D9", "drv1.enable1"],
            ["uno.D8", "drv1.input1"],
            ["uno.D7", "drv1.input2"],
            ["uno.5V", "drv1.vss"],
            ["uno.5V", "pot1.1"],
            ["pot1.2", "uno.A0"],
            ["pot1.3", "uno.GND1"],
            ["bat1.positive", "drv1.vs"],
            ["drv1.output1", "motor1.positive"],
            ["drv1.output2", "motor1.negative"],
            ["uno.GND1", "drv1.gnd", "drv1.gnd1", "drv1.gnd2",
             "drv1.gnd3", "bat1.negative"],
        ],
    }
    _ensure_l293d_battery_placements(monkeypatch)
    placements = builder_module.plan_layout(fixture)["placements"]
    assert placements["drv1"] == {"at": "17f", "pin": "enable1", "angle": 180}
    assert placements["bat1"] == {"free": {"x": 560, "y": 300}}

    result = fixture_to_model_call(fixture)

    parts_by_ref = {p["ref"]: p for p in result["parts"]}
    assert set(parts_by_ref) == {"bat1", "drv1", "motor1", "pot1"}
    # Driver con ancla real capitalizada; bateria y motor libres (sin at/pin).
    assert parts_by_ref["drv1"] == {
        "ref": "drv1", "did": 112326, "at": "17f", "pin": "Enable1", "angle": 180,
    }
    assert parts_by_ref["bat1"] == {
        "ref": "bat1", "did": 116841, "free": {"x": 560, "y": 300},
    }
    assert parts_by_ref["motor1"]["did"] == 114158
    assert "free" in parts_by_ref["motor1"]
    assert parts_by_ref["pot1"]["did"] == 45547

    pot_at = placements["pot1"]["at"]
    # Filas verificadas: f = enable1..vs (10f..17f), i = vss..enable2 (10i..17i).
    expected_pairs = {
        ("uno.D9", "17f"), ("uno.D8", "16f"), ("uno.D7", "11f"),
        ("uno.5V", "17e"), ("uno.5V", pot_at),
        (_shift(pot_at, 1), "uno.A0"), (_shift(pot_at, 2), "uno.GND1"),
        ("bat1.+", "10f"),
        ("15f", "motor1.1"), ("12f", "motor1.2"),
        ("uno.GND1", "14f"), ("14f", "13f"), ("13f", "13e"),
        ("13e", "14e"), ("14e", "bat1.-"),
    }
    assert len(result["wires"]) == len(expected_pairs) == 15
    assert {(w["from"], w["to"]) for w in result["wires"]} == expected_pairs
    by_pair = {(w["from"], w["to"]): w["color"] for w in result["wires"]}
    assert by_pair[("bat1.+", "10f")] == "red"
    assert by_pair[("14e", "bat1.-")] == "black"
    assert by_pair[("uno.GND1", "14f")] == "black"
    assert by_pair[("uno.D9", "17f")] not in ("red", "black")


def _force_l293d_180_placement(monkeypatch):
    """Fuerza drv1 a {"at": "17f", "pin": "enable1", "angle": 180}.

    El layout (otro agente) pasa a emitir ese placement; forzarlo aqui
    mantiene el test del builder determinista antes y despues del merge.
    """
    real_plan_layout = builder_module.plan_layout

    def patched(fixture):
        layout = real_plan_layout(fixture)
        placements = dict(layout["placements"])
        type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}
        unplaced = []
        for ref in layout["unplaced"]:
            ctype = type_by_ref.get(ref)
            if ctype == "l293d":
                placements[ref] = {"at": "17f", "pin": "enable1", "angle": 180}
            elif ctype == "battery-9v":
                placements[ref] = {"free": {"x": 560, "y": 300}}
            else:
                unplaced.append(ref)
        for ref, ctype in type_by_ref.items():
            if ctype == "l293d" and ref in placements:
                placements[ref] = {"at": "17f", "pin": "enable1", "angle": 180}
        return {"placements": placements, "unplaced": unplaced}

    monkeypatch.setattr(builder_module, "plan_layout", patched)


def test_motor_l293d_bateria_angle180_real_fixture_parts_and_wires(monkeypatch):
    fixture = _fixture("motor-l293d-bateria")
    _force_l293d_180_placement(monkeypatch)

    result = fixture_to_model_call(fixture)

    parts_by_ref = {p["ref"]: p for p in result["parts"]}
    # El part emite el angle 180 del placement, con ancla real capitalizada.
    assert parts_by_ref["drv1"] == {
        "ref": "drv1", "did": 112326, "at": "17f", "pin": "Enable1", "angle": 180,
    }
    pairs = {(w["from"], w["to"]) for w in result["wires"]}
    # Geometria 180 verificada: f decreciente desde 17f, e creciente a 17e.
    assert ("bat1.+", "10f") in pairs  # vs = 10f
    assert ("uno.5V", "17e") in pairs  # vss = 17e
    assert ("uno.D9", "17f") in pairs  # PWM -> enable1 = 17f
    assert ("15f", "motor1.1") in pairs  # output1 = 15f
    assert ("12f", "motor1.2") in pairs  # output2 = 12f
    assert ("uno.D7", "16f") in pairs  # input1
    assert ("uno.D8", "11f") in pairs  # input2
    assert ("uno.GND1", "14f") in pairs  # gnd
    by_pair = {(w["from"], w["to"]): w["color"] for w in result["wires"]}
    assert by_pair[("bat1.+", "10f")] == "red"
    assert by_pair[("uno.D9", "17f")] not in ("red", "black")


def test_boton_pullup_pushbutton_geometry_real_fixture():
    # Geometria verificada en vivo (bWmMIRN5dwi): btn en <c>f, senal
    # (pin "1") por <c+2>j y tierra (pin "2") por <c>j.
    fixture = _fixture("boton-pullup")
    layout = plan_layout(fixture)
    assert layout["placements"]["btn1"] == {
        "at": "7f", "pin": "1", "angle": 0,
    }

    result = fixture_to_model_call(fixture)

    parts_by_ref = {p["ref"]: p for p in result["parts"]}
    assert parts_by_ref["btn1"] == {
        "ref": "btn1", "did": 144786, "at": "7f", "pin": "1", "angle": 0,
    }
    pairs = {(w["from"], w["to"]) for w in result["wires"]}
    assert ("uno.D2", "9j") in pairs  # btn1.1 -> columna at+2
    assert ("7j", "uno.GND1") in pairs  # btn1.2 -> columna at
    by_pair = {(w["from"], w["to"]): w["color"] for w in result["wires"]}
    assert by_pair[("7j", "uno.GND1")] == "black"
    assert by_pair[("uno.D2", "9j")] not in ("red", "black")


def test_pushbutton_unknown_pin_raises_build_error():
    fixture = _fixture("boton-pullup")
    fixture["nets"] = [["btn1.3", "uno.GND1"]]

    with pytest.raises(BuildError) as excinfo:
        fixture_to_model_call(fixture)

    assert "btn1.3" in str(excinfo.value)


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
        {"from": "uno.5V", "to": "1g", "color": "red"},
        {"from": "6i", "to": "uno.GND1", "color": "black"},
        {"from": "1g", "to": "5i", "color": "blue"},
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


def _force_buzzer_ldr_placements(monkeypatch):
    """Inyecta los placements de piezo/LDR si el layout aun no los emite.

    Geometria verificada en vivo (cZcqbZ3eNlA): piezo con ancla "+" y
    "-" a +5 columnas; LDR con ancla "terminal-1" y "terminal-2" a +1.
    Se fuerza para que el test no dependa de las columnas del layout.
    """
    real_plan_layout = builder_module.plan_layout

    def patched(fixture):
        layout = real_plan_layout(fixture)
        placements = dict(layout["placements"])
        type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}
        unplaced = []
        for ref in layout["unplaced"]:
            ctype = type_by_ref.get(ref)
            if ctype == "buzzer":
                placements[ref] = {"at": "20c", "pin": "positive", "angle": 0}
            elif ctype == "photoresistor":
                placements[ref] = {"at": "20c", "pin": "1", "angle": 0}
            else:
                unplaced.append(ref)
        return {"placements": placements, "unplaced": unplaced}

    monkeypatch.setattr(builder_module, "plan_layout", patched)


def test_buzzer_activo_real_fixture_parts_and_wires(monkeypatch):
    fixture = _fixture("buzzer-activo")
    _force_buzzer_ldr_placements(monkeypatch)
    placement = builder_module.plan_layout(fixture)["placements"]["buzzer1"]

    result = fixture_to_model_call(fixture)

    parts_by_ref = {p["ref"]: p for p in result["parts"]}
    assert parts_by_ref["buzzer1"] == {
        "ref": "buzzer1",
        "did": 114067,
        "at": placement["at"],
        "pin": "+",
        "angle": placement["angle"],
    }
    assert parts_by_ref["btn1"]["did"] == 144786

    anchor = placement["at"]
    negative = _shift(anchor, 5)
    pairs = {(w["from"], w["to"]) for w in result["wires"]}
    assert ("uno.D8", anchor) in pairs  # senal al terminal "+"
    assert (negative, "uno.GND1") in pairs  # "-" a 5 columnas a GND
    by_pair = {(w["from"], w["to"]): w["color"] for w in result["wires"]}
    assert by_pair[(negative, "uno.GND1")] == "black"
    assert by_pair[("uno.D8", anchor)] not in ("red", "black")


def test_ldr_divisor_real_fixture_offsets(monkeypatch):
    fixture = _fixture("ldr-divisor")
    _force_buzzer_ldr_placements(monkeypatch)
    placements = builder_module.plan_layout(fixture)["placements"]
    anchor = placements["ldr1"]["at"]

    result = fixture_to_model_call(fixture)

    parts_by_ref = {p["ref"]: p for p in result["parts"]}
    assert parts_by_ref["ldr1"] == {
        "ref": "ldr1",
        "did": 116691,
        "at": anchor,
        "pin": "terminal-1",
        "angle": placements["ldr1"]["angle"],
    }
    second = _shift(anchor, 1)
    pairs = {(w["from"], w["to"]) for w in result["wires"]}
    # Pin "2" del LDR traduce al hueco del ancla +1 columna.
    assert ("uno.5V", anchor) in pairs
    assert (second, "uno.A0") in pairs
    assert ("uno.A0", placements["r1"]["at"]) in pairs


def test_buzzer_and_ldr_unknown_pins_raise_build_error(monkeypatch):
    _force_buzzer_ldr_placements(monkeypatch)

    buzzer = _fixture("buzzer-activo")
    buzzer["nets"] = [["buzzer1.piezo", "uno.GND1"]]
    with pytest.raises(BuildError) as excinfo:
        fixture_to_model_call(buzzer)
    assert "buzzer1.piezo" in str(excinfo.value)

    ldr = _fixture("ldr-divisor")
    ldr["nets"] = [["ldr1.3", "uno.GND1"]]
    with pytest.raises(BuildError) as excinfo:
        fixture_to_model_call(ldr)
    assert "ldr1.3" in str(excinfo.value)


def test_build_circuit_unplaced_fixture_raises_before_any_tool_call():
    calls = []
    def fake_call_tool(tool, arguments):
        calls.append(tool)
        return "{}"

    with pytest.raises(BuildError):
        build_circuit(_fixture("buzzer-activo"), None, fake_call_tool)

    assert calls == []
