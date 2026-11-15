"""Tester independiente ronda 15: cableado en estrella, partes libres con
angulo a nivel de part y dos cuerpos grandes (fase 22).

No participe en el desarrollo de esta fase: todo lo de abajo se verifico
leyendo el codigo real (``builder.py``, ``layout.py``) y comparandolo con el
contrato declarado, con tablas y oraculos PROPIOS. No importo las tablas
privadas del builder (``_THREE_PIN_PINS``, ``_FOUR_PIN_PINS``,
``_BUZZER_*``...): si cambian, estos tests tienen que romperse.

Contrato que se pone a prueba
-----------------------------
1. Las nets de 3+ extremos se emparejan en ESTRELLA desde un hub: el primer
   extremo que empiece con ``uno.``; si la net no toca el Uno, el primero
   declarado. Hay exactamente ``len(net) - 1`` cables por net y todos cuelgan
   del mismo hub. Ninguno de esos cables debe unir dos huecos de placa entre
   si (un cable hueco-hueco lo dibuja recto el simulador).
2. Las nets de 2 extremos conservan la orientacion declarada ``(a, b)`` y su
   color por grupo: rojo alimentacion, negro tierra, paleta para senal.
3. Las partes libres (``free``) emiten ``{"ref", "did", "free": {"x", "y"},
   "angle"}``: el angulo va a NIVEL DE PART. Motor DC y bateria 9V no
   inventan angulo. El part del LCD pasa ``spec.validate_spec``.
4. Layout: con piezo y ultrasonico juntos **el piezo cede la placa** y va
   libre a la derecha, asi que el HC-SR04 arranca en su columna verificada
   (18) y no depende de cuantos bloques LED haya antes. (La regla vieja
   —sensor en 10 y piezo en 24e— se retiro en la fase 37: el cuerpo del
   sensor en 10 tapa la resistencia del LCD.)
5. Conectividad: para las 15 fixtures, un inspect armado a mano (placements
   del layout + traduccion de endpoints del builder) da
   ``compare_connectivity == 1.0`` sin shorts.
6. Determinismo y no mutacion: dos llamadas seguidas dan lo mismo, la fixture
   no se muta y el orden de las nets no cambia el conjunto de cables.
7. ``docs/benchmark.md`` lista 15 circuitos (``blN5d8qCr2z`` al 100%) y
   explica la estrella; ``docs/fase0-vivo.md`` trae la fase 22 y la seccion
   del nivel 5 ya no afirma la regla vieja de oclusion como vigente.

Hallazgo de esta ronda (MEDIUM): ``test_r15_la_estrella_no_deja_cables_hueco_hueco``
falla en ``motor-dc-transistor``. Detalle en el test y en el reporte.
"""
import copy
import json
import random
import re
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import (
    DID_BY_TYPE,
    _star_pairs,
    _translate_endpoint,
    fixture_to_model_call,
)
from tinkercad_brain.fase0.metrics import compare_connectivity
from tinkercad_brain.fase0.normalize import normalize_circuit
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.spec import validate_spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_PATH = ROOT / "fixtures" / "fase0" / "circuits.json"
BENCHMARK_PATH = ROOT / "docs" / "benchmark.md"
VIVO_PATH = ROOT / "docs" / "fase0-vivo.md"
LDIST = "blN5d8qCr2z"  # lcd-distancia, nivel 6

# Columnas del contrato (tabla propia, no importada de layout.py).
ULTRASONIC_COLUMN_WITHOUT_PIEZO = 18
PIEZO_COLUMN = 24
ULTRASONIC_PINS = 4

SIGNAL_PALETTE = {
    "blue", "green", "orange", "yellow", "purple", "turquoise", "pink", "brown",
}

HOLE_RE = re.compile(r"([1-9]|[12][0-9]|30)([a-j])")

# ------------------------------------------------------- tablas propias
# Nombre real del componente en inspect (evidencia en vivo de las rondas
# anteriores, docs/fase0-vivo.md y docs/reportes/).
RAW_TYPE = {
    "arduino-uno": "Arduino Uno R3",
    "led": "LED",
    "resistor": "Resistor",
    "pushbutton": "Pushbutton",
    "servo": "Micro Servo",
    "potentiometer": "Potentiometer",
    "ultrasonic-hcsr04": "Ultrasonic Distance Sensor (4 Pin)",
    "buzzer": "Piezo",
    "photoresistor": "Photoresistor (LDR)",
    "dc-motor": "DC Motor",
    "transistor-npn": "NPN Transistor (BJT)",
    "diode": "Diode",
    "led-rgb-common-cathode": "LED RGB",
    "tmp36": "TMP36",
    "l293d": "H-bridge Motor Driver [L293D]",
    "battery-9v": "9V Battery",
    "lcd-16x2": "LCD 16 x 2",
    "seven-segment": "7 Segment Display",
    "shift-register": "8-Bit Shift Register [74HC595]",
    "xor-gate": "Quad XOR gate [74HC86]",
    "nand-gate": "Quad NAND gate [74HC00]",
    "flip-flop-d": "Dual D Flip-Flop [74HC74]",
    "flip-flop-jk": "Dual J-K Flip-Flop [74HC73]",
    "timer-555": "555 Timer",
    "capacitor": "Capacitor",
    "binary-counter": "4-Bit Binary Counter [74HC93]",
    "decade-counter": "Johnson Decade Counter [74HC4017]",
    "relay-spdt": "Relay SPDT",
    "light-bulb": "Light bulb",
    "pir-sensor": "PIR Sensor",
    "keypad-4x4": "Keypad 4x4",
}
LCD_TERMINALS = (
    "GND", "VDD", "VO", "RS", "RW", "E",
    "DB0", "DB1", "DB2", "DB3", "DB4", "DB5", "DB6", "DB7",
    "LED+", "LED-",
)
# pin de fixture -> nombre que reporta inspect para ese pin.
INSPECT_PIN = {
    "led": {"anode": "Anode", "cathode": "Cathode"},
    "resistor": {"1": "Terminal 1", "2": "Terminal 2"},
    "pushbutton": {"1": "Terminal 2a", "2": "Terminal 1a"},
    "servo": {"gnd": "Ground", "vcc": "Power", "signal": "Signal"},
    "potentiometer": {"1": "Terminal 1", "2": "Wiper", "3": "Terminal 2"},
    "ultrasonic-hcsr04": {
        "vcc": "Power", "trig": "Trigger", "echo": "Echo", "gnd": "Ground",
    },
    "buzzer": {"positive": "Positive", "negative": "Negative"},
    "photoresistor": {"1": "terminal-1", "2": "terminal-2"},
    "dc-motor": {"positive": "Terminal 1", "negative": "Terminal 2"},
    "transistor-npn": {
        "collector": "Collector", "base": "Base", "emitter": "Emitter",
    },
    "diode": {"anode": "Anode", "cathode": "Cathode"},
    "led-rgb-common-cathode": {
        "red": "terminal-red", "green": "terminal-green",
        "blue": "terminal-blue", "cathode": "terminal-cathode",
    },
    "tmp36": {"vcc": "Power", "vout": "Vout", "gnd": "GND"},
    "l293d": {
        "enable1": "Enable 1 & 2", "enable2": "Enable 3 & 4",
        "vss": "Power 1", "vs": "Power 2",
        "input1": "Input 1", "input2": "Input 2",
        "input3": "Input 3", "input4": "Input 4",
        "output1": "Output 1", "output2": "Output 2",
        "output3": "Output 3", "output4": "Output 4",
        "gnd": "gnd", "gnd1": "gnd1", "gnd2": "gnd2", "gnd3": "gnd3",
    },
    "battery-9v": {"positive": "Positive", "negative": "Negative"},
    "lcd-16x2": {pin: pin for pin in LCD_TERMINALS},
    # El cableado guardado usa las etiquetas del DOM: A..G, DP, Common.
    "seven-segment": {
        "a": "A", "b": "B", "c": "C", "d": "D", "e": "E", "f": "F", "g": "G",
        "dp": "DP", "com1": "Common", "com2": "Common",
    },
    "shift-register": {
        pin: pin for pin in (
            "Q0", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q7S",
            "DS", "SHCP", "STCP", "OE", "MR", "Vcc", "GND",
        )
    },
    # El guardado etiqueta Input 1A/Input 1B/Output 1 y Power/Ground.
    "xor-gate": {
        "Vcc": "Power", "GND": "Ground",
        **{f"{i}A": f"Input {i}A" for i in range(1, 5)},
        **{f"{i}B": f"Input {i}B" for i in range(1, 5)},
        **{f"{i}Y": f"Output {i}" for i in range(1, 5)},
    },
    "nand-gate": {
        "Vcc": "Power", "GND": "Ground",
        **{f"{i}A": f"Input {i}A" for i in range(1, 5)},
        **{f"{i}B": f"Input {i}B" for i in range(1, 5)},
        **{f"{i}Y": f"Output {i}" for i in range(1, 5)},
    },
    # El guardado: Input/Clock/Reset/Set/Output/Inverted Output.
    "flip-flop-d": {
        "Vcc": "Power", "GND": "Ground",
        **{f"{i}D": f"Input {i}" for i in range(1, 3)},
        **{f"{i}CP": f"Clock {i}" for i in range(1, 3)},
        **{f"{i}RD": f"Reset {i}" for i in range(1, 3)},
        **{f"{i}SD": f"Set {i}" for i in range(1, 3)},
        **{f"{i}Q": f"Output {i}" for i in range(1, 3)},
        **{f"{i}NQ": f"Inverted Output {i}" for i in range(1, 3)},
    },
    # El 74HC73 no tiene preset: el guardado escribe J/K/Clock/Reset/Output
    # (medido en vivo el 2026-11-14 cableando los 14 pines).
    "flip-flop-jk": {
        "Vcc": "Power", "GND": "Ground",
        **{f"{i}J": f"J {i}" for i in range(1, 3)},
        **{f"{i}K": f"K {i}" for i in range(1, 3)},
        **{f"{i}CP": f"Clock {i}" for i in range(1, 3)},
        **{f"{i}R": f"Reset {i}" for i in range(1, 3)},
        **{f"{i}Q": f"Output {i}" for i in range(1, 3)},
        **{f"{i}NQ": f"Inverted Output {i}" for i in range(1, 3)},
    },
    # El guardado del 555 usa Power/Reset/Ground/Discharge/Threshold/
    # Trigger/Out (descubierto en vivo en abIk7XRpSR4).
    "timer-555": {
        "Vcc": "Power", "Reset": "Reset", "GND": "Ground",
        "DIS": "Discharge", "THR": "Threshold", "TRIG": "Trigger",
        "OUT": "Out", "CTRL": "Control",
    },
    "capacitor": {"1": "Terminal 1", "2": "Terminal 2"},
    # El guardado del 74HC93 (descubierto en vivo en fCB0eO8cBbn).
    "binary-counter": {
        "Vcc": "Power", "GND": "Ground",
        "CP0": "Clock 0", "CP1": "Clock 1",
        "MR1": "Reset 1", "MR2": "Reset 2",
        "Q0": "Output Bit 0", "Q1": "Output Bit 1",
        "Q2": "Output Bit 2", "Q3": "Output Bit 3",
    },
    # El guardado del 74HC4017 (descubierto en vivo en ij6ypc8wB5x).
    "decade-counter": {
        "Vcc": "Power", "GND": "Ground",
        "CP0": "Clock", "CP1n": "Clock Enable", "MR": "Reset",
        **{f"Q{i}": f"Output {i + 1}" for i in range(10)},
    },
    # El guardado del rele usa la numeracion fisica Terminal 1..12
    # (medido cableando cada pin una sola vez en bDUH17ymla2).
    "relay-spdt": {
        "COIL1": "Terminal 8", "COIL2": "Terminal 5",
        "COM1": "Terminal 12", "R1": "Terminal 6",
        "COM2": "Terminal 1", "R2": "Terminal 7",
    },
    "light-bulb": {"1": "Terminal 1", "2": "Terminal 2"},
    # El guardado del PIR usa Signal/Power/Ground (vivo en dgFz6r0k1xV).
    "pir-sensor": {"out": "Signal", "vcc": "Power", "gnd": "Ground"},
    # El teclado guarda Row n / Column n (vivo en bOhGx6ENPnn).
    "keypad-4x4": {
        **{f"row{i}": f"Row {i}" for i in range(1, 5)},
        **{f"column{i}": f"Column {i}" for i in range(1, 5)},
    },
}

POWER_ENDPOINTS = {"uno.5V", "uno.3V3", "uno.VIN"}
RAIL_POWER_RE = re.compile(r"[TB]\+(?:[1-9]|[12][0-9]|30)?")
RAIL_GROUND_RE = re.compile(r"[TB]-(?:[1-9]|[12][0-9]|30)?")


def _fixtures():
    return json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))


def _fixture(fixture_id):
    return next(c for c in _fixtures() if c["id"] == fixture_id)


FIXTURE_IDS = [c["id"] for c in _fixtures()]
# Fase 31: las fixtures que optan por rieles. No se parametriza sobre
# todas y se salta: un skip por 22 casos sanos esconde el caso real.
RAILED_IDS = [c["id"] for c in _fixtures() if c.get("wiring") == "rails"]


# ------------------------------------------------------------- utilidades

def _translations(fixture):
    placements = plan_layout(fixture)["placements"]
    type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}
    return placements, type_by_ref


def _board_of(endpoint, placements):
    """Placa del layout donde vive el extremo (0 si es el Uno o la primera).

    Fase 39: una parte puede pedir la segunda protoboard con ``board: 1`` y
    entonces sus huecos viajan al puente como ``b1/5d``.
    """
    ref = endpoint.split(".", 1)[0] if isinstance(endpoint, str) else ""
    placement = placements.get(ref) or {}
    return placement.get("board") or 0


def _translated_net(fixture, net):
    placements, type_by_ref = _translations(fixture)
    translated = []
    for endpoint in net:
        hole = _translate_endpoint(endpoint, placements, type_by_ref)
        board = _board_of(endpoint, placements)
        if board and HOLE_RE.fullmatch(hole):
            hole = f"b{board}/{hole}"
        translated.append(hole)
    return translated


def _is_uno(endpoint):
    return endpoint.startswith("uno.")


def _is_hole(text):
    return HOLE_RE.fullmatch(text) is not None


def _is_source_terminal(endpoint):
    """El "+"/"-" solo es alimentacion/tierra si la parte es una fuente.

    Desde la fase 37 el piezo puede ir libre y sus terminales se llaman
    "+"/"-" igual que las de la bateria, pero su positivo lo maneja un pin
    digital: pintarlo de rojo seria mentir sobre el circuito.
    """
    return endpoint.split(".", 1)[0].startswith("bat")


def _is_power(endpoint):
    return (
        endpoint in POWER_ENDPOINTS
        or RAIL_POWER_RE.fullmatch(endpoint) is not None
        or (endpoint.endswith(".+") and _is_source_terminal(endpoint))
    )


def _is_ground(endpoint):
    return (
        endpoint.startswith("uno.GND")
        or RAIL_GROUND_RE.fullmatch(endpoint) is not None
        or (endpoint.endswith(".-") and _is_source_terminal(endpoint))
    )


def _star_or_sort(translated):
    """Oraculo propio de los pares de UNA net (contrato, no el codigo).

    Contrato actualizado tras el hallazgo MEDIA de esta misma ronda: si la
    net no trae ningun pin del Uno, el hub es el terminal de una parte libre
    (lo unico que el puente rutea por carriles) y solo si tampoco hay uno se
    usa el primer extremo declarado. Un hub en un hueco dejaba cables
    hueco-hueco rectos sobre los cuerpos.
    """
    if len(translated) == 2:
        return [tuple(translated)]
    if len(translated) < 2:
        return []
    unique = list(dict.fromkeys(translated))
    hub = next(
        (e for e in unique if _is_uno(e)),
        next((e for e in unique if _is_free_terminal(e)), unique[0]),
    )
    return [(hub, endpoint) for endpoint in unique if endpoint != hub]


def _is_free_terminal(endpoint):
    """Un terminal de parte libre no traduce a hueco ni a pin del Uno."""
    ref = endpoint.split(".", 1)[0]
    return ref != "uno" and not re.fullmatch(r"\d+[a-j]", endpoint)


def _expected_pairs(fixture):
    pairs = []
    for net in fixture["nets"]:
        pairs.extend(_star_or_sort(_translated_net(fixture, net)))
    return pairs


def _pairs(call):
    return [(wire["from"], wire["to"]) for wire in call["wires"]]


def _railed(fixture):
    """La fixture opta por rieles (fase 31): su topologia no es la estrella."""
    return fixture.get("wiring") == "rails"


_RAIL_ENDPOINT_RE = re.compile(r"^((?:b[1-9]/)?)([TB])([+-])\d+$")


def _node(endpoint):
    """Todas las columnas del mismo riel son el mismo nodo electrico.

    El prefijo de placa se conserva: el riel de la placa 2 no es el de la 1.
    """
    match = _RAIL_ENDPOINT_RE.match(endpoint)
    if match:
        return f"rail:{match.group(1)}{match.group(2)}{match.group(3)}"
    return endpoint


def _model_groups(call):
    """Nets fisicas del cableado del modelo, con el riel colapsado a un nodo."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for wire in call["wires"]:
        union(_node(wire["from"]), _node(wire["to"]))
    grupos = {}
    for endpoint in parent:
        grupos.setdefault(find(endpoint), set()).add(endpoint)
    return list(grupos.values())


def _part_y_did(call):
    return {part["ref"]: part for part in call["parts"]}


def _used_pins(fixture, ref):
    return {
        endpoint.split(".", 1)[1]
        for net in fixture["nets"]
        for endpoint in net
        if endpoint.split(".", 1)[0] == ref
    }


def _part_holes(fixture):
    """{ref: {pin: hueco}} de todas las patas cableadas de partes de placa."""
    placements, type_by_ref = _translations(fixture)
    holes = {}
    for component in fixture["components"]:
        ref = component["ref"]
        if ref == "uno" or "free" in placements[ref]:
            continue
        holes[ref] = {
            pin: _translate_endpoint(f"{ref}.{pin}", placements, type_by_ref)
            for pin in _used_pins(fixture, ref)
        }
    return holes


def _col(hole):
    return int(HOLE_RE.fullmatch(hole).group(1))


# ------------------------------- inspect armado a mano (oraculo de red)

def _inspect_for(fixture):
    """Inspect del circuito real: cada pata al hueco del layout y las nets
    de la fixture encadenadas por sus extremos traducidos.

    Las partes de placa se cablean por hueco; las libres por su terminal
    real (LCD por nombre de inspect, motor/bateria por Terminal N /
    Positive-Negative). Asi ``derive_nets`` reconstruye la red fisica.
    """
    placements, type_by_ref = _translations(fixture)
    instance = {"uno": "uno_a"}
    for component in fixture["components"]:
        if component["ref"] != "uno":
            instance[component["ref"]] = "i_" + component["ref"]

    def bb_of(ref):
        """Instancia de protoboard donde la parte tiene sus patas."""
        return "bb_b" if (placements.get(ref) or {}).get("board") else "bb_a"

    wires = []

    def wire(source, target):
        wires.append(
            {
                "source": {
                    "component": source[0], "instance_id": source[0],
                    "pin": source[1],
                },
                "target": {
                    "component": target[0], "instance_id": target[0],
                    "pin": target[1],
                },
            }
        )

    for ref, pins in _part_holes(fixture).items():
        real_by_pin = INSPECT_PIN[type_by_ref[ref]]
        for pin, hole in pins.items():
            wire((instance[ref], real_by_pin[pin]), (bb_of(ref), hole))

    def node(endpoint):
        ref, pin = endpoint.split(".", 1)
        if ref == "uno":
            return ("uno_a", pin)
        if "free" in placements[ref]:
            return (instance[ref], INSPECT_PIN[type_by_ref[ref]][pin])
        return (
            bb_of(ref),
            _translate_endpoint(endpoint, placements, type_by_ref),
        )

    for net in fixture["nets"]:
        nodes = [node(endpoint) for endpoint in net]
        for first, second in zip(nodes, nodes[1:]):
            wire(first, second)

    components = [
        {"type": RAW_TYPE["arduino-uno"], "instance_id": "uno_a", "pins": []},
        {"type": "Breadboard Small", "instance_id": "bb_a", "pins": []},
    ]
    if any((placement or {}).get("board") for placement in placements.values()):
        components.append(
            {"type": "Breadboard Small", "instance_id": "bb_b", "pins": []}
        )
    for component in fixture["components"]:
        if component["ref"] == "uno":
            continue
        components.append(
            {
                "type": RAW_TYPE[component["type"]],
                "instance_id": instance[component["ref"]],
                "pins": [],
            }
        )
    return {"components": components, "wires": wires}


def _actual_from_inspect(inspect):
    return {
        "components": normalize_circuit(inspect, {"nets": []})["components"],
        "nets": derive_nets(inspect),
    }


# ------------------------------------------- 1. la estrella, fixture a fixture

@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_r15_los_cables_son_exactamente_la_estrella_declarada(fixture_id):
    """Pares exactos: estrella de 3+ desde el hub, 2 extremos tal cual, y
    exactamente ``len(net) - 1`` cables por net."""
    fixture = _fixture(fixture_id)
    if _railed(fixture):
        pytest.skip(
            f"{fixture_id}: opta por rieles (fase 31), su topologia no es la "
            "estrella; la equivalencia fisica se comprueba en "
            "test_r15_con_rieles_cada_net_sigue_siendo_un_nodo"
        )
    call = fixture_to_model_call(fixture)
    pairs = _pairs(call)

    assert sorted(pairs) == sorted(_expected_pairs(fixture))
    assert len(pairs) == sum(len(net) - 1 for net in fixture["nets"])
    assert len(pairs) == len(set(pairs))
    for first, second in pairs:
        assert first != second, (fixture_id, first)


@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_r15_la_estrella_no_deja_cables_hueco_hueco(fixture_id):
    """Ningun cable de una net de 3+ extremos puede unir dos huecos de placa.

    Un cable hueco-hueco lo dibuja recto el simulador y cruza en diagonal
    sobre los cuerpos: es exactamente el defecto que la estrella elimino.
    """
    fixture = _fixture(fixture_id)
    pairs = set(_pairs(fixture_to_model_call(fixture)))

    if _railed(fixture):
        # Con riel cada extremo de una net de 3+ baja al riel: si dos huecos
        # de esa net quedaran unidos por un cable, seria el defecto de nuevo.
        offenders = []
        for net in fixture["nets"]:
            if len(net) < 3:
                continue
            huecos = [e for e in _translated_net(fixture, net) if _is_hole(e)]
            for first in huecos:
                for second in huecos:
                    if first < second and (first, second) in pairs:
                        offenders.append((net, first, second))
        assert offenders == [], (fixture_id, offenders)
        return

    offenders = []
    for net in fixture["nets"]:
        if len(net) < 3:
            continue
        for first, second in _star_or_sort(_translated_net(fixture, net)):
            assert (first, second) in pairs, (fixture_id, net, first, second)
            if _is_hole(first) and _is_hole(second):
                offenders.append((net, first, second))

    assert offenders == [], (
        f"{fixture_id}: cables hueco-hueco dentro de una net de 3+ extremos "
        f"(la estrella cuelga de un hub que no es pin del Uno ni terminal "
        f"libre): {offenders}"
    )


@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_r15_el_hub_es_el_primer_pin_del_uno_si_esta_en_la_net(fixture_id):
    fixture = _fixture(fixture_id)
    call = fixture_to_model_call(fixture)
    pairs = set(_pairs(call))

    if _railed(fixture):
        # Sin estrella no hay hub por net: el hub es el riel, y el riel se
        # alimenta con un unico cable desde el pin del Uno. Si falta ese
        # cable el riel queda flotando aunque los taps existan.
        nodos = {_node(w["from"]) for w in call["wires"]} | {
            _node(w["to"]) for w in call["wires"]
        }
        for riel, pin in (("rail:T+", "uno.5V"), ("rail:T-", "uno.GND1")):
            if riel not in nodos:
                continue
            assert any(
                _node(w["to"]) == riel and w["from"] == pin for w in call["wires"]
            ), (fixture_id, riel, call["wires"])
        return

    for net in fixture["nets"]:
        if len(net) < 3:
            continue
        translated = _translated_net(fixture, net)
        unique = list(dict.fromkeys(translated))
        uno_endpoints = [e for e in unique if _is_uno(e)]
        if not uno_endpoints:
            continue
        hub = uno_endpoints[0]
        expected = [(hub, e) for e in unique if e != hub]
        assert len(expected) == len(net) - 1, (fixture_id, net)
        for pair in expected:
            assert pair in pairs, (fixture_id, net, pair)
        # Ningun cable de la net sale de otro hub.
        for first, second in expected:
            assert first == hub


def test_r15_la_tierra_larga_del_termometro_cuelga_del_uno_declarado_al_final():
    """Caso explicito: la net de GND de 6 extremos de lcd-temperatura tiene el
    pin del Uno al final y aun asi el hub es ese pin."""
    fixture = _fixture("lcd-temperatura")
    gnd = next(net for net in fixture["nets"] if "lcd1.GND" in net)
    assert gnd[-1] == "uno.GND1"
    pairs = set(_pairs(fixture_to_model_call(fixture)))

    translated = _translated_net(fixture, gnd)
    far = [e for e in translated if e != "uno.GND1"]
    assert len(far) == 5
    for endpoint in far:
        assert ("uno.GND1", endpoint) in pairs, endpoint
    # El hub no es el primer extremo declarado (lcd1.GND).
    assert ("lcd1.GND", "lcd1.VO") not in pairs


# ------------------------------------------ 2. nets de 2 extremos y colores

@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_r15_las_nets_de_dos_extremos_conservan_su_orientacion(fixture_id):
    fixture = _fixture(fixture_id)
    pairs = _pairs(fixture_to_model_call(fixture))

    for net in fixture["nets"]:
        if len(net) != 2:
            continue
        translated = tuple(_translated_net(fixture, net))
        if _railed(fixture) and any(
            _is_power(e) or _is_ground(e) for e in translated
        ):
            # Con riel, 5V/GND no van pin a pin: el extremo baja al riel y
            # el Uno alimenta el riel una sola vez.
            continue
        assert pairs.count(translated) == 1, (fixture_id, net, translated)


@pytest.mark.parametrize("fixture_id", RAILED_IDS)
def test_r15_con_rieles_cada_net_sigue_siendo_un_nodo(fixture_id):
    """El riel cambia el dibujo, no la fisica: cada net de la fixture debe
    quedar en un solo nodo del cableado del modelo."""
    fixture = _fixture(fixture_id)
    assert _railed(fixture)

    grupos = _model_groups(fixture_to_model_call(fixture))
    for net in fixture["nets"]:
        nodos = {_node(e) for e in _translated_net(fixture, net)}
        assert any(nodos <= grupo for grupo in grupos), (
            f"{fixture_id}: la net {net} quedo partida en el cableado con riel"
        )


@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_r15_el_color_de_cada_cable_corresponde_a_su_grupo(fixture_id):
    """Rojo alimentacion, negro tierra, paleta para senal (sin excepciones)."""
    call = fixture_to_model_call(_fixture(fixture_id))

    for wire in call["wires"]:
        endpoints = (wire["from"], wire["to"])
        has_power = any(_is_power(e) for e in endpoints)
        has_ground = any(_is_ground(e) for e in endpoints)
        if has_power:
            assert wire["color"] == "red", (fixture_id, wire)
        elif has_ground:
            assert wire["color"] == "black", (fixture_id, wire)
        else:
            assert wire["color"] in SIGNAL_PALETTE, (fixture_id, wire)
        assert not (has_power and has_ground), (fixture_id, wire)


def test_r15_el_color_de_las_nets_de_dos_extremos_es_el_de_su_familia():
    fixture = _fixture("servo-potenciometro")
    colors = {
        (w["from"], w["to"]): w["color"]
        for w in fixture_to_model_call(fixture)["wires"]
    }

    for net in fixture["nets"]:
        assert len(net) == 2
        pair = tuple(_translated_net(fixture, net))
        color = colors[pair]
        if any(_is_power(e) for e in pair):
            assert color == "red", (net, pair, color)
        elif any(_is_ground(e) for e in pair):
            assert color == "black", (net, pair, color)
        else:
            assert color in SIGNAL_PALETTE, (net, pair, color)


# --------------------------------------------- 3. partes libres con angulo

def test_r15_el_part_libre_del_lcd_lleva_el_angulo_a_nivel_de_part():
    call = fixture_to_model_call(_fixture("lcd-distancia"))
    lcd = _part_y_did(call)["lcd1"]

    assert lcd == {
        "ref": "lcd1",
        "did": DID_BY_TYPE["lcd-16x2"],
        "free": {"x": 1100, "y": -230},
        "angle": 0,
    }
    assert set(lcd) == {"ref", "did", "free", "angle"}
    assert set(lcd["free"]) == {"x", "y"}
    # El validador de specs exige exactamente {x, y} dentro de `free` y el
    # angulo a nivel de part: el part del builder tiene que redondear.
    validated = validate_spec(
        {
            "parts": [
                {
                    "ref": "lcd1",
                    "type": "lcd-16x2",
                    "free": lcd["free"],
                    "angle": lcd["angle"],
                }
            ],
            "wires": [],
        }
    )
    assert validated["parts"][0]["free"] == {"x": 1100, "y": -230}


@pytest.mark.parametrize(
    "ref, did, spot",
    [
        ("motor1", 114158, {"x": 560, "y": 60}),
        ("bat1", 116841, {"x": 560, "y": 300}),
    ],
)
def test_r15_motor_y_bateria_libres_no_inventan_angulo(ref, did, spot):
    call = fixture_to_model_call(_fixture("motor-l293d-bateria"))
    part = _part_y_did(call)[ref]

    assert part == {"ref": ref, "did": did, "free": spot}
    assert "angle" not in part
    assert set(part["free"]) == {"x", "y"}
    types = {"motor1": "dc-motor", "bat1": "battery-9v"}
    validated = validate_spec(
        {
            "parts": [{"ref": ref, "type": types[ref], "free": part["free"]}],
            "wires": [],
        }
    )
    assert validated["parts"][0]["free"] == spot


# --------------------------------------------- 4. dos cuerpos grandes

def test_r15_lcd_distancia_libera_el_piezo_y_el_sensor_vuelve_a_18d():
    """Fase 37: el piezo cede la placa.

    Con el piezo montado en 24e el sensor tenia que arrancar en 10d para no
    chocar con su disco, y ahi su cuerpo tapaba la resistencia del LCD (pin
    2 en 5g). Ahora el piezo va libre y el sensor usa su columna verificada.
    """
    fixture = _fixture("lcd-distancia")
    placements = plan_layout(fixture)["placements"]

    assert placements["us1"] == {"at": "18d", "pin": "vcc", "angle": 0}
    assert placements["buzzer1"] == {
        "free": {"x": 1250, "y": 60, "angle": 0},
    }
    # El piezo ya no ocupa huecos de placa.
    assert "buzzer1" not in _part_holes(fixture)
    # El segundo pin de la resistencia queda fuera del cuerpo del sensor
    # (7 columnas a la izquierda y 10 a la derecha de su pin "vcc").
    holes = _part_holes(fixture)
    assert holes["r1"] == {"1": "1g", "2": "5g"}
    sombra = set(range(18 - 7, 18 + 10 + 1))
    assert _col(holes["r1"]["2"]) not in sombra


def test_r15_sin_piezo_el_sensor_sigue_en_la_columna_18():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "us1", "type": "ultrasonic-hcsr04"},
        ],
        "nets": [],
    }
    placements = plan_layout(fixture)["placements"]

    assert placements["us1"]["at"] == f"{ULTRASONIC_COLUMN_WITHOUT_PIEZO}d"
    assert placements["us1"]["at"] == "18d"


def test_r15_con_piezo_el_que_cede_es_el_piezo():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "us1", "type": "ultrasonic-hcsr04"},
            {"ref": "buzzer1", "type": "buzzer"},
        ],
        "nets": [],
    }
    placements = plan_layout(fixture)["placements"]

    assert placements["us1"]["at"] == f"{ULTRASONIC_COLUMN_WITHOUT_PIEZO}d"
    assert placements["buzzer1"] == {
        "free": {"x": 1250, "y": 60, "angle": 0},
    }


@pytest.mark.parametrize("led_blocks", [1, 2])
def test_r15_con_piezo_el_sensor_no_choca_con_los_bloques_led(led_blocks):
    """Sin el piezo en la placa el sensor siempre arranca en 18 (fase 37),
    sin importar cuantos bloques LED se hayan colocado antes, y no comparte
    ningun hueco con ellos."""
    components = [
        {"ref": "uno", "type": "arduino-uno"},
        {"ref": "us1", "type": "ultrasonic-hcsr04"},
        {"ref": "buzzer1", "type": "buzzer"},
    ]
    # Nets del sensor y del piezo para que sus patas esten cableadas (el
    # layout no depende de ellas: solo las de LED/resistencia mueven bloques).
    nets = [
        ["uno.5V", "us1.vcc"],
        ["us1.gnd", "uno.GND1"],
        ["uno.D7", "us1.trig"],
        ["uno.D6", "us1.echo"],
        ["uno.D8", "buzzer1.positive"],
        ["buzzer1.negative", "uno.GND1"],
    ]
    for index in range(1, led_blocks + 1):
        components += [
            {"ref": f"led{index}", "type": "led"},
            {"ref": f"r{index}", "type": "resistor"},
        ]
        nets += [
            [f"uno.D{13 - index}", f"r{index}.1"],
            [f"r{index}.2", f"led{index}.anode"],
        ]
    fixture = {"components": components, "nets": nets}

    placements = plan_layout(fixture)["placements"]
    assert placements["us1"]["at"] == f"{ULTRASONIC_COLUMN_WITHOUT_PIEZO}d"
    assert "free" in placements["buzzer1"]

    holes = _part_holes(fixture)
    sensor = set(holes["us1"].values())
    assert sensor == {
        f"{col}d"
        for col in range(ULTRASONIC_COLUMN_WITHOUT_PIEZO,
                          ULTRASONIC_COLUMN_WITHOUT_PIEZO + ULTRASONIC_PINS)
    }
    for ref, part_holes in holes.items():
        if ref == "us1":
            continue
        assert sensor.isdisjoint(part_holes.values()), (ref, part_holes, sensor)


def test_r15_presupuesto_de_columnas_de_lcd_distancia():
    """Todo dentro de 1..30 y a..j, y ningun hueco repetido entre partes."""
    fixture = _fixture("lcd-distancia")
    holes = _part_holes(fixture)

    owner = {}
    for ref, pins in holes.items():
        for pin, hole in pins.items():
            assert HOLE_RE.fullmatch(hole), (ref, pin, hole)
            assert 1 <= _col(hole) <= 30, (ref, pin, hole)
            assert hole[-1] in "abcdefghij", (ref, pin, hole)
            assert hole not in owner, (hole, owner.get(hole), (ref, pin))
            owner[hole] = (ref, pin)

    # Todos los huecos que usan los cables pertenecen a una parte de placa.
    call = fixture_to_model_call(fixture)
    wire_holes = {
        text
        for wire in call["wires"]
        for text in (wire["from"], wire["to"])
        if _is_hole(text)
    }
    assert wire_holes == set(owner)
    # El display no aporta huecos: va libre.
    assert "lcd1" not in holes


# ------------------------------------ 5. conectividad extremo a extremo

@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_r15_conectividad_armada_a_mano_es_1_0(fixture_id):
    fixture = _fixture(fixture_id)
    result = compare_connectivity(
        {"components": fixture["components"], "nets": fixture["nets"]},
        _actual_from_inspect(_inspect_for(fixture)),
    )

    assert result["missing_components"] == [], fixture_id
    assert result["extra_components"] == [], fixture_id
    assert result["shorts"] == [], fixture_id
    assert result["components_score"] == 1.0, fixture_id
    assert result["connectivity_score"] == 1.0, fixture_id
    assert result["score"] == 1.0, fixture_id


def test_r15_lcd_distancia_conserva_sus_dos_nets_largas_al_leerlo():
    """La GND de 7 extremos y la de 5V de 4 quedan completas en el inspect."""
    fixture = _fixture("lcd-distancia")
    inspect = _inspect_for(fixture)
    actual = _actual_from_inspect(inspect)
    nets = actual["nets"]

    sensor_ref = next(
        comp["ref"]
        for comp in actual["components"]
        if comp["type"] == "ultrasonic-hcsr04"
    )
    gnd = next(net for net in nets if "uno.GND1" in net)
    assert len(gnd) == 7
    assert {
        "lcd1.GND", "lcd1.VO", "lcd1.RW", "lcd1.LED-",
        "buzzer1.negative", "uno.GND1", f"{sensor_ref}.gnd",
    } == set(gnd)

    power = next(net for net in nets if "uno.5V" in net)
    assert set(power) == {"uno.5V", "lcd1.VDD", "r1.1", f"{sensor_ref}.vcc"}


# -------------------------- 6. determinismo y no mutacion

def test_r15_dos_llamadas_dan_lo_mismo_y_no_mutan_la_fixture():
    for fixture_id in FIXTURE_IDS:
        fixture = _fixture(fixture_id)
        before = copy.deepcopy(fixture)

        first = fixture_to_model_call(fixture, code="void setup() {}")
        second = fixture_to_model_call(fixture, code="void setup() {}")

        assert fixture == before, fixture_id
        assert first == second, fixture_id
        assert first["code"] == "void setup() {}"


def test_r15_el_orden_de_las_nets_no_cambia_el_conjunto_de_cables():
    for fixture_id in FIXTURE_IDS:
        fixture = _fixture(fixture_id)
        base = fixture_to_model_call(fixture)
        base_pairs = {(w["from"], w["to"]) for w in base["wires"]}

        for seed in range(4):
            shuffled = copy.deepcopy(fixture)
            random.Random(seed).shuffle(shuffled["nets"])
            call = fixture_to_model_call(shuffled)

            assert {(w["from"], w["to"]) for w in call["wires"]} == base_pairs, (
                fixture_id,
                seed,
            )
            assert call["parts"] == base["parts"], (fixture_id, seed)
            assert sorted(
                (w["from"], w["to"], w["color"]) for w in call["wires"]
            ) == sorted(
                (w["from"], w["to"], w["color"]) for w in base["wires"]
            ), (fixture_id, seed)


def test_r15_star_pairs_reglas_del_hub():
    """Contrato directo de la funcion de estrella."""
    # 2 extremos: tal cual, sin invertir.
    assert _star_pairs(["1a", "2b"]) == [("1a", "2b")]
    assert _star_pairs(["uno.GND1", "5g"]) == [("uno.GND1", "5g")]
    # 3+: hub = primer pin del Uno, aunque este declarado al final.
    assert _star_pairs(["5g", "9c", "uno.GND1"]) == [
        ("uno.GND1", "5g"), ("uno.GND1", "9c"),
    ]
    # 3+ sin Uno: hub = primero declarado.
    assert _star_pairs(["1a", "2b", "3c", "4d"]) == [
        ("1a", "2b"), ("1a", "3c"), ("1a", "4d"),
    ]
    # Duplicados: no hay cable de un extremo consigo mismo.
    assert _star_pairs(["uno.5V", "uno.5V", "7c"]) == [("uno.5V", "7c")]
    # Menos de 2 extremos: ningun cable.
    assert _star_pairs([]) == []
    assert _star_pairs(["1a"]) == []


# --------------------------------------------------------------- 7. docs

def test_r15_benchmark_lista_los_15_circuitos_y_explica_la_estrella():
    text = BENCHMARK_PATH.read_text(encoding="utf-8")

    rows = re.findall(r"^\|\s*(\d+)\s*\|", text, re.M)
    # La fase 35 agrega la fila 27 (control de acceso con servo).
    assert len(rows) == 28, rows  # fase 38: contador 555+compuertas
    assert [int(number) for number in rows] == list(range(1, 29))  # fase 38: fila 28

    line = next(line for line in text.splitlines() if LDIST in line)
    assert "100%" in line, line
    assert "LCD" in line.title() or "distancia" in line.lower(), line

    # La regla de cableado en estrella esta explicada como vigente.
    lowered = " ".join(text.lower().split())  # el markdown parte frases
    assert "estrella" in lowered
    assert "hub" in lowered or "pin del uno" in lowered
    assert "hueco-hueco" in lowered or "carril" in lowered


def test_r15_fase0_vivo_trae_la_fase_22_y_supera_la_oclusion_del_nivel_5():
    text = VIVO_PATH.read_text(encoding="utf-8")

    parts = text.split("## Fase 22", 1)
    assert len(parts) == 2, "falta la seccion de la fase 22"
    body = parts[1]
    assert "estrella" in body.lower()
    assert "10" in body and "24e" in body
    assert LDIST in body
    assert "dos cuerpos grandes" in body.lower()

    # El nivel 5 ya no afirma la regla vieja de oclusion como vigente.
    nivel5 = text.split("## Nivel 5", 1)
    assert len(nivel5) == 2
    nivel5_body = nivel5[1].split("\n## ", 1)[0]
    assert "guarda de oclusion" in nivel5_body
    assert "quedo superada" in nivel5_body.lower()
    assert "fase 21" in nivel5_body.lower()
