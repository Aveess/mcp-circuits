"""Tester independiente ronda 7: layout/builder/derive_nets/sketches 3-pin.

Adversarial, sin repetir las suites existentes: aqui se fuerzan los
bordes nuevos (llenar las 30 columnas, mezclar familias con cursor
compartido, alias por tipo en el MISMO circuito) y la consistencia
cruzada fixture -> builder -> sketch. Sin bugs conocidos al escribirlo:
si un test falla, es un bug contra produccion.
"""
import json
import re
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import BuildError, fixture_to_model_call
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.sketches import servo_knob_sketch, ultrasonic_sketch

ROOT = Path(__file__).resolve().parents[1]
REAL_FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture(fixture_id):
    circuits = json.loads(REAL_FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == fixture_id)


def _col(hole):
    return int(re.fullmatch(r"(\d+)[a-j]", hole).group(1))


def _occupied3(placement):
    start = _col(placement["at"])
    return set(range(start, start + 3))


def _pairwise_disjoint(sets):
    for i, a in enumerate(sets):
        for b in sets[i + 1:]:
            assert a.isdisjoint(b), f"solapan {a} y {b}"


# ---------------------------------------------------------------- layout

def test_r7_muchos_3pines_llenan_30_columnas_y_el_resto_va_a_unplaced():
    # 10 partes de 3 pines: caben 7 bloques de 4 columnas (inicio 1,5,..,25;
    # el hueco 25-27 es el ultimo util). La 8a empezaria en 29 y su pin
    # +2 caeria en 31: debe ir a unplaced, sin solapar ni salir del tablero.
    cycle = [
        ("servo1", "servo"), ("pot1", "potentiometer"), ("tmp1", "tmp36"),
        ("servo2", "servo"), ("pot2", "potentiometer"), ("tmp2", "tmp36"),
        ("servo3", "servo"), ("pot3", "potentiometer"), ("tmp3", "tmp36"),
        ("servo4", "servo"),
    ]
    fixture = {
        "components": [{"ref": "uno", "type": "arduino-uno"}]
        + [{"ref": ref, "type": ctype} for ref, ctype in cycle],
        "nets": [],
    }

    result = plan_layout(fixture)

    first_pin = {"servo": "gnd", "potentiometer": "1", "tmp36": "vcc"}
    placed_refs = [ref for ref, _ in cycle[:7]]
    assert [result["placements"][r]["at"] for r in placed_refs] == [
        "1c", "5c", "9c", "13c", "17c", "21c", "25c",
    ]
    for ref, ctype in cycle[:7]:
        placement = result["placements"][ref]
        assert placement["pin"] == first_pin[ctype]
        assert placement["angle"] == 0
        assert min(_occupied3(placement)) >= 1
        assert max(_occupied3(placement)) <= 30
    _pairwise_disjoint([_occupied3(result["placements"][r]) for r in placed_refs])
    # Los que no entran: en unplaced, en orden de fixture, jamas colocados.
    assert result["unplaced"] == ["pot3", "tmp3", "servo4"]
    assert not set(result["unplaced"]) & set(result["placements"])
    # Y el builder no construye a medias con la placa llena.
    with pytest.raises(BuildError) as excinfo:
        fixture_to_model_call(fixture)
    for ref in ("pot3", "tmp3", "servo4"):
        assert ref in str(excinfo.value)


def test_r7_led_boton_servo_mezclados_con_cursor_compartido_no_solapan():
    # Orden de componentes adverso a proposito: el servo y el boton se
    # listan ANTES que el LED, pero el bloque LED/resistencia manda
    # primero y el resto comparte el cursor que ese bloque deja libre.
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "servo1", "type": "servo"},
            {"ref": "btn1", "type": "pushbutton"},
            {"ref": "led1", "type": "led"},
            {"ref": "r1", "type": "resistor"},
        ],
        "nets": [["r1.2", "led1.anode"], ["uno.D9", "servo1.signal"]],
    }

    result = plan_layout(fixture)

    assert result["unplaced"] == []
    assert result["placements"]["r1"] == {"at": "1g", "pin": "1", "angle": 90}
    assert result["placements"]["led1"] == {"at": "5i", "pin": "anode", "angle": 180}
    assert result["placements"]["servo1"] == {"at": "7c", "pin": "gnd", "angle": 0}
    assert result["placements"]["btn1"] == {"at": "11f", "pin": "1", "angle": 0}
    # Rangos reservados: bloque LED 1..6 (ancla r en 1, pin2 en 5,
    # anodo en 5, catodo en 6), servo 7..9, boton solo su columna 11
    # (la 10 es la separacion que deja el avance de 4 del servo).
    led_block = set(range(1, 7))
    servo_range = _occupied3(result["placements"]["servo1"])
    button_range = {_col(result["placements"]["btn1"]["at"])}
    _pairwise_disjoint([led_block, servo_range, button_range])


def test_r7_dos_servos_refs_y_bloques_distintos_y_senales_distintas():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "servo1", "type": "servo"},
            {"ref": "servo2", "type": "servo"},
        ],
        "nets": [["uno.D9", "servo1.signal"], ["uno.D10", "servo2.signal"]],
    }

    result = plan_layout(fixture)

    assert result["unplaced"] == []
    assert result["placements"]["servo1"] == {"at": "1c", "pin": "gnd", "angle": 0}
    assert result["placements"]["servo2"] == {"at": "5c", "pin": "gnd", "angle": 0}
    _pairwise_disjoint(
        [_occupied3(p) for p in result["placements"].values()]
    )
    # Extremo a extremo: cada signal cae en el at+2 de SU servo.
    model = fixture_to_model_call(fixture)
    assert [p["at"] for p in model["parts"]] == ["1c", "5c"]
    assert {p["ref"] for p in model["parts"]} == {"servo1", "servo2"}
    assert model["wires"] == [["uno.D9", "3c"], ["uno.D10", "7c"]]


# ---------------------------------------------------------------- builder

def test_r7_tmp36_sintetica_completa_wires_pin_a_pin_contra_layout():
    # Fixture sintetica completa (servo + tmp36, 6 nets): cada pin del
    # tmp36 debe caer en at/+1/+2 segun layout, con DID y alias reales.
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "servo1", "type": "servo"},
            {"ref": "tmp1", "type": "tmp36"},
        ],
        "nets": [
            ["uno.D9", "servo1.signal"],
            ["uno.5V", "servo1.vcc"],
            ["servo1.gnd", "uno.GND1"],
            ["uno.5V", "tmp1.vcc"],
            ["tmp1.vout", "uno.A1"],
            ["tmp1.gnd", "uno.GND1"],
        ],
    }

    layout = plan_layout(fixture)
    assert layout["placements"]["tmp1"] == {"at": "5c", "pin": "vcc", "angle": 0}

    result = fixture_to_model_call(fixture)

    assert result["parts"] == [
        {"ref": "servo1", "did": 142073, "at": "1c", "pin": "Ground", "angle": 0},
        {"ref": "tmp1", "did": 112324, "at": "5c", "pin": "Vcc", "angle": 0},
    ]
    tmp_at = layout["placements"]["tmp1"]["at"]
    assert result["wires"] == [
        ["uno.D9", "3c"],
        ["uno.5V", "2c"],
        ["1c", "uno.GND1"],
        ["uno.5V", tmp_at],        # vcc: el ancla misma (5c)
        ["6c", "uno.A1"],          # vout: at+1
        ["7c", "uno.GND1"],        # gnd: at+2
    ]


def test_r7_pot_wiper_cae_en_el_hueco_del_medio_y_servo_signal_en_at_mas2():
    # Sin monkeypatch: contra el layout real de la fixture real.
    fixture = _fixture("servo-potenciometro")

    result = fixture_to_model_call(fixture)

    assert result["parts"] == [
        {"ref": "servo1", "did": 142073, "at": "1c", "pin": "Ground", "angle": 0},
        {"ref": "pot1", "did": 45547, "at": "5c", "pin": "term0", "angle": 0},
    ]
    assert result["wires"] == [
        ["uno.D9", "3c"],       # servo.signal = at(1c)+2
        ["uno.5V", "2c"],       # servo.vcc = at+1
        ["1c", "uno.GND1"],     # servo.gnd = at
        ["uno.5V", "5c"],       # pot.1 (term0) = at
        ["6c", "uno.A0"],       # pot.2 (wiper) = at+1, el hueco del medio
        ["7c", "uno.GND1"],     # pot.3 (term1) = at+2
    ]


# ------------------------------------------------------------- derive_nets

def _comp(type_, instance_id):
    return {"type": type_, "instance_id": instance_id, "name": "1", "pins": []}


def _ep(component, pin, instance_id):
    return {"component": component, "pin": pin, "instance_id": instance_id}


def _wire(source, target):
    return {"source": source, "target": target}


def test_r7_terminal2_se_traduce_distinto_por_tipo_en_el_mismo_circuito():
    # "Terminal 2" en la resistencia es el pin "2"; en el potenciometro
    # es el pin "3" (term1), porque su "2" es el Wiper. Ambos wires
    # conviven en el MISMO circuito: la traduccion depende del tipo
    # del componente dueño del endpoint, no del nombre del pin.
    data = {
        "components": [
            _comp("Arduino Uno R3", "uno1"),
            _comp("Resistor", "r_a"),
            _comp("Potentiometer", "pot_a"),
        ],
        "wires": [
            _wire(_ep("Resistor", "Terminal 1", "r_a"), _ep("Arduino Uno R3", "D13", "uno1")),
            _wire(_ep("Resistor", "Terminal 2", "r_a"), _ep("Arduino Uno R3", "D11", "uno1")),
            _wire(_ep("Potentiometer", "Terminal 1", "pot_a"), _ep("Arduino Uno R3", "5V", "uno1")),
            _wire(_ep("Potentiometer", "Wiper", "pot_a"), _ep("Arduino Uno R3", "A0", "uno1")),
            _wire(_ep("Potentiometer", "Terminal 2", "pot_a"), _ep("Arduino Uno R3", "GND", "uno1")),
        ],
    }

    nets = derive_nets(data)

    assert nets == [
        ["potentiometer1.1", "uno.5V"],
        ["potentiometer1.2", "uno.A0"],
        ["potentiometer1.3", "uno.GND1"],
        ["r1.1", "uno.D13"],
        ["r1.2", "uno.D11"],
    ]
    # La net del "Terminal 2" del pote NO es la del wiper: son pins y
    # nets distintos dentro del mismo componente.
    net_of = {ep: net for net in nets for ep in net}
    assert net_of["potentiometer1.3"] is not net_of["potentiometer1.2"]
    assert "r1.2" in net_of["uno.D11"]
    assert "potentiometer1.2" not in net_of["uno.D11"]


# ---------------------------------------------------------------- sketches

def test_r7_servo_knob_pot_pin_minuscula_es_rechazado_criterio_estricto():
    """Criterio: RECHAZAR "a0", no normalizar.

    En Arduino, analogRead(a0) no compila (el identificador es A0) y
    aceptar en silencio ocultaria un typo de la fixture; la validacion
    del resto de sketches es estricta (pines fuera de rango = ValueError).
    Por eso la minuscula es error, con mensaje que nombra el rango.
    """
    with pytest.raises(ValueError, match=r"pot_pin fuera de A0\.\.A5"):
        servo_knob_sketch(pot_pin="a0")
    # La forma canonica si pasa y llega literal al sketch.
    assert "analogRead(A0)" in servo_knob_sketch(pot_pin="A0")


def test_r7_ultrasonic_trig2_echo3_en_el_borde_inferior_es_valido():
    sketch = ultrasonic_sketch(trig=2, echo=3)

    assert "pinMode(2, OUTPUT)" in sketch
    assert "pinMode(3, INPUT)" in sketch
    assert "digitalWrite(2, HIGH)" in sketch
    assert "digitalWrite(2, LOW)" in sketch
    assert "pulseIn(3, HIGH)" in sketch
    assert "TEST:DIST=" in sketch


# ------------------------------------------------------- consistencia cruzada

def test_r7_cruzado_fixture_builder_sketch_el_servo_queda_en_d9():
    fixture = _fixture("servo-potenciometro")
    # Verdad de la fixture: el servo pide D9 y el pote A0.
    assert ["uno.D9", "servo1.signal"] in fixture["nets"]
    assert ["pot1.2", "uno.A0"] in fixture["nets"]

    result = fixture_to_model_call(fixture)
    servo_part = next(p for p in result["parts"] if p["ref"] == "servo1")
    assert servo_part["did"] == 142073
    assert servo_part["pin"] == "Ground"  # ancla = pin fisico en at

    # Reconstruccion desde los huecos: el ancla 1c es Ground, luego
    # 2c = Power y 3c = Signal. El wire que toca 3c dice que pin del
    # Uno alimenta el servo.
    signal_hole = f"{_col(servo_part['at']) + 2}c"
    assert signal_hole == "3c"
    uno_endpoint = next(
        other
        for wire in result["wires"]
        if signal_hole in wire
        for other in wire
        if other != signal_hole
    )
    match = re.fullmatch(r"uno\.D(\d+)", uno_endpoint)
    assert match is not None
    servo_pin = int(match.group(1))
    assert servo_pin == 9

    # El sketch generado con ese pin debe adjuntar el servo en D9 y
    # leer el pote en A0, como pide la fixture.
    sketch = servo_knob_sketch(servo_pin=servo_pin, pot_pin="A0")
    assert "attach(9)" in sketch
    assert "analogRead(A0)" in sketch
