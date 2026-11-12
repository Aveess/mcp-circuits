"""Tester independiente ronda 8: HC-SR04 de punta a punta.

Adversarial sobre lo nuevo: builder real sin monkeypatch, normalizacion
guion/espacio/guion_bajo de fixture_type (y ausencia de colisiones en
TYPE_MAP), layout del ultrasonico contra 4 bloques LED y contra un
segundo ultrasonico, reorden alimentacion/tierra/senales con paleta que
da la vuelta, y derive_nets con servo + ultrasonico compartiendo los
nombres en vivo Power/Ground. Sin bugs conocidos al escribirlo: si un
test falla, es un bug contra produccion.
"""
import json
import re
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import fixture_to_model_call
from tinkercad_brain.fase0.component_map import TYPE_MAP, fixture_type
from tinkercad_brain.layout import plan_layout

ROOT = Path(__file__).resolve().parents[1]
REAL_FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"
PALETTE = [
    "blue", "green", "orange", "yellow", "purple", "turquoise", "pink", "brown",
]


def _fixture(fixture_id):
    circuits = json.loads(REAL_FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == fixture_id)


def _col(hole):
    return int(re.fullmatch(r"(\d+)[a-j]", hole).group(1))


def _us_holes(at):
    start = _col(at)
    row = at[-1]
    return [f"{start + i}{row}" for i in range(4)]


# ------------------------------------------------------- builder: real

def test_r8_sensor_real_wires_completos_contra_las_7_nets_y_sin_colision_led():
    fixture = _fixture("sensor-ultrasonico")
    assert len(fixture["nets"]) == 7

    layout = plan_layout(fixture)
    assert layout["unplaced"] == []
    assert layout["placements"]["us1"] == {"at": "18d", "pin": "vcc", "angle": 0}

    result = fixture_to_model_call(fixture)

    assert result["parts"] == [
        {"ref": "r1", "did": 53184, "at": "1g", "pin": "1", "angle": 90},
        {"ref": "led1", "did": 58422, "at": "5i", "pin": "anode", "angle": 180},
        {"ref": "us1", "did": 219295, "at": "18d", "pin": "pos", "angle": 0},
    ]
    # Orden del builder: alimentacion, tierra (por "from"), senales
    # (por "from", paleta en orden). Huecos US: vcc/trig/echo/gnd.
    assert result["wires"] == [
        {"from": "uno.5V", "to": "18d", "color": "red"},
        {"from": "21d", "to": "uno.GND1", "color": "black"},
        {"from": "6i", "to": "uno.GND1", "color": "black"},
        {"from": "5g", "to": "5i", "color": "blue"},
        {"from": "uno.D13", "to": "1g", "color": "green"},
        {"from": "uno.D6", "to": "20d", "color": "orange"},
        {"from": "uno.D7", "to": "19d", "color": "yellow"},
    ]

    # Cada una de las 7 nets de la fixture aparece exactamente una vez
    # como par de extremos (sin importar direccion) en los wires.
    hole_of = {
        "us1.vcc": "18d", "us1.trig": "19d", "us1.echo": "20d", "us1.gnd": "21d",
        "r1.1": "1g", "r1.2": "5g", "led1.anode": "5i", "led1.cathode": "6i",
    }
    expected_pairs = {
        frozenset(hole_of.get(ep, ep) for ep in net) for net in fixture["nets"]
    }
    actual_pairs = {
        frozenset((w["from"], w["to"])) for w in result["wires"]
    }
    assert actual_pairs == expected_pairs
    assert len(result["wires"]) == 7

    # Huecos del sensor at..at+3: ninguno es un hueco del bloque LED
    # (r en 1g/5g, led en 5i/6i) ni cae en sus columnas reservadas 1..6.
    us_holes = _us_holes(layout["placements"]["us1"]["at"])
    assert us_holes == ["18d", "19d", "20d", "21d"]
    assert set(us_holes).isdisjoint({"1g", "5g", "5i", "6i"})
    assert all(_col(h) > 6 for h in us_holes)


# ---------------------------------------------------------- fixture_type

@pytest.mark.parametrize("name", [
    "Ultrasonic Distance Sensor (4-pin)",
    "Ultrasonic Distance Sensor (4 Pin)",
    "Ultrasonic Distance Sensor (4 PIN)",
    "Ultrasonic Distance Sensor (4_pin)",
    "Ultrasonic_Distance_Sensor_(4-pin)",
    "ULTRASONIC-DISTANCE-SENSOR-(4_PIN)",
    "  ultrasonic   distance\tsensor (4-Pin)  ",
])
def test_r8_fixture_type_variantes_del_nombre_real_4pin(name):
    assert fixture_type(name) == "ultrasonic-hcsr04"


def test_r8_normalizacion_no_colisiona_nombres_distintos_del_mapa():
    # Contraejemplo buscado en el TYPE_MAP real: si dos nombres con
    # slugs DISTINTOS normalizaran a la misma clave, el mapa
    # normalizado de produccion pisaria uno con el otro en silencio.
    def normalize(name):
        return " ".join(name.replace("-", " ").replace("_", " ").split()).casefold()

    by_key = {}
    for name, slug in TYPE_MAP.items():
        by_key.setdefault(normalize(name), set()).add(slug)
    collisions = {k: v for k, v in by_key.items() if len(v) > 1}
    assert collisions == {}
    # Y cada nombre del mapa sigue resolviendo a SU slug tras normalizar.
    for name, slug in TYPE_MAP.items():
        assert fixture_type(name) == slug


# ---------------------------------------------------------------- layout

def _four_led_blocks_plus_ultrasonic():
    components = [
        {"ref": "uno", "type": "arduino-uno"},
        # El ultrasonico va primero a proposito: los bloques LED mandan.
        {"ref": "us1", "type": "ultrasonic-hcsr04"},
    ]
    nets = [
        ["uno.5V", "us1.vcc"], ["us1.gnd", "uno.GND1"],
        ["uno.D7", "us1.trig"], ["uno.D6", "us1.echo"],
    ]
    for i in range(1, 5):
        components.append({"ref": f"led{i}", "type": "led"})
        components.append({"ref": f"r{i}", "type": "resistor"})
        nets.append([f"uno.D{8 + i}", f"r{i}.1"])
        nets.append([f"r{i}.2", f"led{i}.anode"])
        nets.append([f"led{i}.cathode", "uno.GND1"])
    return {"components": components, "nets": nets}


def test_r8_ultrasonico_tras_4_bloques_led_entra_en_25d_sin_solapar():
    result = plan_layout(_four_led_blocks_plus_ultrasonic())

    assert result["unplaced"] == []
    assert result["placements"]["us1"] == {"at": "25d", "pin": "vcc", "angle": 0}
    led_ranges = [set(range(s, s + 6)) for s in (1, 7, 13, 19)]
    us_range = set(range(25, 29))
    assert us_range == {_col(h) for h in _us_holes("25d")}
    for led_range in led_ranges:
        assert us_range.isdisjoint(led_range)
    # Los 4 bloques LED quedaron en sus anclas de siempre.
    for i, start in enumerate((1, 7, 13, 19), start=1):
        assert result["placements"][f"r{i}"]["at"] == f"{start}g"
        assert result["placements"][f"led{i}"]["at"] == f"{start + 4}i"


def test_r8_dos_ultrasonicos_layout_y_builder_huecos_disjuntos():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "us1", "type": "ultrasonic-hcsr04"},
            {"ref": "us2", "type": "ultrasonic-hcsr04"},
        ],
        "nets": [
            ["uno.5V", "us1.vcc"], ["us1.gnd", "uno.GND1"],
            ["uno.D7", "us1.trig"], ["uno.D6", "us1.echo"],
            ["uno.5V", "us2.vcc"], ["us2.gnd", "uno.GND1"],
            ["uno.D9", "us2.trig"], ["uno.D8", "us2.echo"],
        ],
    }

    layout = plan_layout(fixture)
    assert layout["unplaced"] == []
    assert layout["placements"]["us1"] == {"at": "18d", "pin": "vcc", "angle": 0}
    assert layout["placements"]["us2"] == {"at": "23d", "pin": "vcc", "angle": 0}
    holes1 = set(_us_holes("18d"))
    holes2 = set(_us_holes("23d"))
    assert holes1.isdisjoint(holes2)

    result = fixture_to_model_call(fixture)
    assert result["parts"] == [
        {"ref": "us1", "did": 219295, "at": "18d", "pin": "pos", "angle": 0},
        {"ref": "us2", "did": 219295, "at": "23d", "pin": "pos", "angle": 0},
    ]
    assert result["wires"] == [
        {"from": "uno.5V", "to": "18d", "color": "red"},
        {"from": "uno.5V", "to": "23d", "color": "red"},
        {"from": "21d", "to": "uno.GND1", "color": "black"},
        {"from": "26d", "to": "uno.GND1", "color": "black"},
        {"from": "uno.D6", "to": "20d", "color": "blue"},
        {"from": "uno.D7", "to": "19d", "color": "green"},
        {"from": "uno.D8", "to": "25d", "color": "orange"},
        {"from": "uno.D9", "to": "24d", "color": "yellow"},
    ]
    wire_ends = {w["from"] for w in result["wires"]} | {w["to"] for w in result["wires"]}
    assert holes1 | holes2 <= wire_ends


# ------------------------------------------------- builder: orden/colores

def test_r8_builder_reordena_aunque_la_senal_venga_antes_que_la_alimentacion():
    # Nets en orden adverso: senales primero, alimentacion al final.
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "servo1", "type": "servo"},
            {"ref": "us1", "type": "ultrasonic-hcsr04"},
        ],
        "nets": [
            ["uno.D6", "us1.echo"],
            ["uno.D7", "us1.trig"],
            ["uno.D9", "servo1.signal"],
            ["us1.gnd", "uno.GND1"],
            ["servo1.gnd", "uno.GND1"],
            ["uno.5V", "servo1.vcc"],
            ["uno.5V", "us1.vcc"],
        ],
    }

    result = fixture_to_model_call(fixture)

    # servo en 1c (gnd/vcc/signal = 1c/2c/3c), US en 18d (18d/19d/20d/21d).
    assert result["wires"] == [
        {"from": "uno.5V", "to": "2c", "color": "red"},
        {"from": "uno.5V", "to": "18d", "color": "red"},
        {"from": "1c", "to": "uno.GND1", "color": "black"},
        {"from": "21d", "to": "uno.GND1", "color": "black"},
        {"from": "uno.D6", "to": "20d", "color": "blue"},
        {"from": "uno.D7", "to": "19d", "color": "green"},
        {"from": "uno.D9", "to": "3c", "color": "orange"},
    ]
    groups = [w["color"] for w in result["wires"]]
    assert groups == ["red", "red", "black", "black", "blue", "green", "orange"]


def test_r8_paleta_de_senales_da_la_vuelta_sin_repetir_consecutivos():
    # 4 bloques LED + ultrasonico = 10 senales: la paleta de 8 colores
    # se agota y vuelve a empezar; jamas dos senales seguidas iguales.
    result = fixture_to_model_call(_four_led_blocks_plus_ultrasonic())

    colors = [w["color"] for w in result["wires"]]
    assert colors[0] == "red"
    assert colors[1:6] == ["black"] * 5  # 4 catodos + gnd del US
    signal_colors = colors[6:]
    assert len(signal_colors) == 10
    assert signal_colors == (PALETTE * 2)[:10]
    assert all(a != b for a, b in zip(signal_colors, signal_colors[1:]))
    assert all(set(w) == {"from", "to", "color"} for w in result["wires"])


# ------------------------------------------------------------- derive_nets

def _comp(type_, instance_id):
    return {"type": type_, "instance_id": instance_id, "name": "1", "pins": []}


def _ep(component, pin, instance_id):
    return {"component": component, "pin": pin, "instance_id": instance_id}


def _wire(source, target):
    return {"source": source, "target": target}


def test_r8_derive_nets_servo_y_ultrasonico_a_la_vez_ground_en_ambos():
    # "Ground" existe en ambos tipos y "Power" tambien: la traduccion
    # debe depender del dueno del endpoint. El tipo en vivo del sensor
    # usa la capitalizacion "(4-PIN)", que solo resuelve via la nueva
    # normalizacion de fixture_type.
    us = "Ultrasonic Distance Sensor (4-PIN)"
    data = {
        "components": [
            _comp("Arduino Uno R3", "uno1"),
            _comp("Micro Servo", "servo_a"),
            _comp(us, "us_a"),
        ],
        "wires": [
            _wire(_ep("Micro Servo", "Power", "servo_a"), _ep("Arduino Uno R3", "5V", "uno1")),
            _wire(_ep("Micro Servo", "Ground", "servo_a"), _ep("Arduino Uno R3", "GND", "uno1")),
            _wire(_ep("Micro Servo", "Signal", "servo_a"), _ep("Arduino Uno R3", "D9", "uno1")),
            _wire(_ep(us, "Power", "us_a"), _ep("Arduino Uno R3", "5V", "uno1")),
            _wire(_ep(us, "Trigger", "us_a"), _ep("Arduino Uno R3", "D7", "uno1")),
            _wire(_ep(us, "Echo", "us_a"), _ep("Arduino Uno R3", "D6", "uno1")),
            _wire(_ep(us, "Ground", "us_a"), _ep("Arduino Uno R3", "GND", "uno1")),
        ],
    }

    nets = derive_nets(data)

    assert nets == [
        ["servo1.gnd", "ultrasonichcsr041.gnd", "uno.GND1"],
        ["servo1.signal", "uno.D9"],
        ["servo1.vcc", "ultrasonichcsr041.vcc", "uno.5V"],
        ["ultrasonichcsr041.echo", "uno.D6"],
        ["ultrasonichcsr041.trig", "uno.D7"],
    ]
    # Ningun nombre en vivo queda sin traducir en ninguna net.
    assert not any(
        ep.endswith((".Power", ".Ground", ".Trigger", ".Echo", ".Signal"))
        for net in nets
        for ep in net
    )
