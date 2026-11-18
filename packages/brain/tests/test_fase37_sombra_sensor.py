"""Fase 37: el piezo cede la placa cuando hay un sensor ultrasonico.

Medido en vivo (ver docs/fase0-vivo.md, fases 22 y 36): el cuerpo del
HC-SR04 se dibuja unos 17 huecos de ancho alrededor de sus cuatro pines,
7 columnas a la izquierda del pin ``vcc`` y 10 a la derecha. Con el piezo
en la placa (``24e``) su disco choca con ese cuerpo; la unica forma de
que ambos cupieran era empujar el sensor a la columna 10. Ahi su cuerpo
tapa las filas altas sobre las columnas 3..20: en ``lcd-distancia`` la
resistencia de backlight del LCD queda anclada en ``1g`` y su segundo pin
en ``5g``, debajo del sensor. El cable que sale de ese hueco
(``5g -> lcd1.LED+``) parece terminar dentro del cuerpo.

Regla de la fase: **dos cuerpos grandes no comparten placa**. El piezo
tiene dos cables y ya se sabe colocar libre a la derecha (fase 35,
``free_parts`` verificado en vivo con el servo); el sensor recupera la
columna 18, que es la posicion verificada en vivo donde su cuerpo no tapa
nada.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tinkercad_brain.builder import fixture_to_model_call
from tinkercad_brain.layout import (
    FREE_RIGHT_X,
    FREE_RIGHT_Y,
    plan_layout,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"

# Medido en vivo: cuerpo del HC-SR04 alrededor de su pin `vcc`. El cuerpo
# sube desde la fila d (donde estan sus pines) y tapa las filas altas.
SHADOW_LEFT = 7
SHADOW_RIGHT = 10
UPPER_ROWS = "jihgf"

# Columnas que ocupa cada tipo sobre la placa, desde su columna de ancla.
# Solo los que aparecen en circuitos con sensor; el resto cae en el ancla.
PIN_SPANS = {
    "resistor": 5,        # pin 2 cuatro columnas a la derecha (angle 90)
    "led": 2,             # anodo en el ancla, catodo una columna despues
    "led-rgb-common-cathode": 4,
    "servo": 3,
    "buzzer": 6,          # "-" cinco columnas despues del "+"
    "pushbutton": 1,
}


def _fixture(circuit_id):
    circuits = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == circuit_id)


def _column(at):
    return int(at.rstrip("abcdefghij"))


def _row(at):
    return at[-1]


def _shadow(placement):
    start = _column(placement["at"])
    return {
        (column, row)
        for column in range(start - SHADOW_LEFT, start + SHADOW_RIGHT + 1)
        for row in UPPER_ROWS
    }


def _pin_holes(ref, placement, type_by_ref):
    column, row = _column(placement["at"]), _row(placement["at"])
    width = PIN_SPANS.get(type_by_ref[ref], 1)
    return {(column + offset, row) for offset in range(width)}


def _board_pin_holes(fixture):
    layout = plan_layout(fixture)
    type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}
    return {
        ref: _pin_holes(ref, spot, type_by_ref)
        for ref, spot in layout["placements"].items()
        if "at" in spot
    }


def test_el_piezo_de_lcd_distancia_va_libre_a_la_derecha():
    layout = plan_layout(_fixture("lcd-distancia"))
    buzzer = layout["placements"]["buzzer1"]

    assert buzzer == {"free": {"x": FREE_RIGHT_X, "y": FREE_RIGHT_Y, "angle": 0}}
    assert "at" not in buzzer


def test_el_sensor_recupera_su_columna_verificada():
    # Sin el disco del piezo en la placa, el cuerpo del sensor ya no choca
    # con nada a su izquierda: vuelve a la columna 18.
    layout = plan_layout(_fixture("lcd-distancia"))

    assert layout["placements"]["us1"] == {"at": "18d", "pin": "vcc", "angle": 0}


def test_la_resistencia_del_lcd_ya_no_cae_bajo_el_cuerpo_del_sensor():
    layout = plan_layout(_fixture("lcd-distancia"))
    r1 = layout["placements"]["r1"]

    assert r1 == {"at": "1g", "pin": "1", "angle": 90}
    # pin 1 en la columna 1, pin 2 en la 5: ninguno dentro de la sombra.
    assert not ({(1, "g"), (5, "g")} & _shadow(layout["placements"]["us1"]))


@pytest.mark.parametrize(
    "circuit_id",
    ["sensor-ultrasonico", "parking-servo-ultrasonico-rgb", "lcd-distancia"],
)
def test_ningun_pin_de_placa_cae_bajo_el_cuerpo_del_sensor(circuit_id):
    fixture = _fixture(circuit_id)
    layout = plan_layout(fixture)
    sombra = _shadow(layout["placements"]["us1"])

    for ref, holes in _board_pin_holes(fixture).items():
        if ref == "us1":
            continue
        assert not (holes & sombra), (circuit_id, ref, sorted(holes))


@pytest.mark.parametrize("circuit_id", ["buzzer-activo", "alarma-pir"])
def test_sin_sensor_el_piezo_sigue_montado_en_la_placa(circuit_id):
    layout = plan_layout(_fixture(circuit_id))
    buzzer = layout["placements"]["buzzer1"]

    assert "at" in buzzer
    assert _column(buzzer["at"]) >= 24


def test_el_piezo_libre_se_cablea_a_sus_pines_reales():
    call = fixture_to_model_call(_fixture("lcd-distancia"))
    part = next(p for p in call["parts"] if p["ref"] == "buzzer1")

    assert part == {
        "ref": "buzzer1",
        "did": 114067,
        "free": {"x": FREE_RIGHT_X, "y": FREE_RIGHT_Y},
        "angle": 0,
    }
    # El puente resuelve las terminales por nombre real, no por la
    # geometria de huecos (que aqui no existe).
    ends = {
        endpoint
        for wire in call["wires"]
        for endpoint in (wire["from"], wire["to"])
        if endpoint.startswith("buzzer1.")
    }
    assert ends == {"buzzer1.+", "buzzer1.-"}


def test_el_parking_no_se_mueve():
    # Circuito con sensor y sin piezo: el RGB y sus resistencias siguen
    # donde estaban y su ancla queda fuera de la sombra.
    layout = plan_layout(_fixture("parking-servo-ultrasonico-rgb"))

    assert layout["placements"]["rgb1"] == {"at": "5i", "pin": "red", "angle": 0}
    assert layout["placements"]["us1"] == {"at": "18d", "pin": "vcc", "angle": 0}
    assert layout["placements"]["servo1"] == {"at": "9c", "pin": "gnd", "angle": 0}


def test_el_cable_de_senal_del_piezo_libre_no_se_pinta_como_alimentacion():
    # `buzzer1.+` no es una fuente: el "+" de una bateria libre si es rojo,
    # pero el del piezo lo maneja un pin digital. En la placa ese cable era
    # verde; libre tiene que seguir siendo de senal.
    call = fixture_to_model_call(_fixture("lcd-distancia"))
    color = {frozenset((w["from"], w["to"])): w["color"] for w in call["wires"]}

    assert color[frozenset(("uno.D8", "buzzer1.+"))] != "red"
    assert color[frozenset(("uno.GND1", "buzzer1.-"))] == "black"


def test_el_mas_de_la_bateria_libre_sigue_siendo_rojo():
    # Sin regresion: el terminal "+" de la bateria es alimentacion.
    call = fixture_to_model_call(_fixture("motor-l293d-bateria"))
    color = {frozenset((w["from"], w["to"])): w["color"] for w in call["wires"]}

    cables = [c for ends, c in color.items() if any(e.endswith("bat1.+") for e in ends)]
    assert cables == ["red"]
