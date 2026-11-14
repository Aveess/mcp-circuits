"""Fase 36: el LCD sale de lado y se corre a la derecha.

La deuda de la fase 34 era visible en cinco circuitos: las 16 terminales
del LCD 16x2 miran hacia ARRIBA, y el puente bajaba en vertical desde el
pin hasta el carril. Ese tramo atraviesa el propio display, asi que los
cables parecian nacer en el borde inferior del cuerpo.

El arreglo tiene dos mitades y este archivo fija las dos:

- **layout:** el LCD pasa de ``x=870`` a ``x=1100``. En 870 el teclado del
  circuito ``clave-lcd`` queda a 310 unidades y el abanico de salida le
  pasa por encima al cuerpo; en 1100 hay ~390 de aire a su izquierda. El
  display de 7 segmentos NO se mueve: sus terminales miran hacia abajo.
- **puente:** una parte libre con terminales arriba sale primero de lado
  (``FREE_ESCAPE``, relativo al ORIGEN de la parte y escalonado por
  carril) y despues baja. Se verifica en ``tinkercad-mcp``.

El apilado sigue siendo compartido entre tipos aunque la ``x`` cambie: un
LCD y un display de 7 segmentos en el mismo circuito nunca comparten
altura.
"""

from __future__ import annotations

import json
from pathlib import Path

from tinkercad_brain.builder import fixture_to_model_call
from tinkercad_brain.layout import (
    FREE_MODULE_STEP_Y,
    FREE_MODULE_X,
    FREE_SHIFT_REGISTER_Y,
    LCD_FREE_X,
    plan_layout,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"
LCD_FIXTURES = (
    "lcd-contador",
    "lcd-temperatura",
    "lcd-distancia",
    "clave-lcd",
    "control-acceso",
)


def _fixture(circuit_id):
    circuits = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == circuit_id)


def _free(components):
    fixture = {
        "components": [{"ref": "uno", "type": "arduino-uno"}] + components,
        "nets": [],
    }
    layout = plan_layout(fixture)
    return {ref: spot["free"] for ref, spot in layout["placements"].items()
            if "free" in spot}


def test_el_lcd_vive_a_la_derecha_del_display_de_7_segmentos():
    assert LCD_FREE_X == 1100
    assert FREE_MODULE_X == 870


def test_los_cinco_circuitos_con_lcd_lo_colocan_en_la_misma_x():
    for circuit_id in LCD_FIXTURES:
        layout = plan_layout(_fixture(circuit_id))
        lcd = layout["placements"]["lcd1"]["free"]

        assert lcd == {"x": LCD_FREE_X, "y": -230, "angle": 0}, circuit_id
        # Sigue sin consumir huecos de placa.
        assert layout["placements"]["lcd1"].keys() == {"free"}, circuit_id


def test_el_display_de_7_segmentos_no_se_mueve():
    # Sus terminales miran hacia abajo: no necesita escape y su x no cambia.
    assert _free([{"ref": "seg", "type": "seven-segment"}]) == {
        "seg": {"x": FREE_MODULE_X, "y": -230, "angle": 0}
    }
    fixture = _fixture("siete-segmentos")
    assert plan_layout(fixture)["placements"]["seg"]["free"]["x"] == FREE_MODULE_X


def test_lcd_y_display_comparten_apilado_aunque_no_compartan_x():
    # Primero el LCD: el display baja un escalon, en su propia columna.
    assert _free([
        {"ref": "lcd1", "type": "lcd-16x2"},
        {"ref": "seg", "type": "seven-segment"},
    ]) == {
        "lcd1": {"x": LCD_FREE_X, "y": -230, "angle": 0},
        "seg": {"x": FREE_MODULE_X, "y": -230 - FREE_MODULE_STEP_Y, "angle": 0},
    }
    # Al reves: el LCD es el que baja.
    assert _free([
        {"ref": "seg", "type": "seven-segment"},
        {"ref": "lcd1", "type": "lcd-16x2"},
    ]) == {
        "seg": {"x": FREE_MODULE_X, "y": -230, "angle": 0},
        "lcd1": {"x": LCD_FREE_X, "y": -230 - FREE_MODULE_STEP_Y, "angle": 0},
    }


def test_dos_lcd_se_apilan_en_su_columna():
    assert _free([
        {"ref": "lcd1", "type": "lcd-16x2"},
        {"ref": "lcd2", "type": "lcd-16x2"},
    ]) == {
        "lcd1": {"x": LCD_FREE_X, "y": -230, "angle": 0},
        "lcd2": {"x": LCD_FREE_X, "y": -230 - FREE_MODULE_STEP_Y, "angle": 0},
    }


def test_ninguna_parte_libre_cae_debajo_del_cuerpo_del_lcd():
    # El cuerpo del LCD mide ~290 de ancho; una parte a menos de 300 de su
    # ancla queda tapada por el en la captura.
    spots = _free([
        {"ref": "lcd1", "type": "lcd-16x2"},
        {"ref": "ic1", "type": "shift-register"},
        {"ref": "ic2", "type": "binary-counter"},
        {"ref": "k1", "type": "relay-spdt"},
        {"ref": "l1", "type": "light-bulb"},
    ])

    assert spots["ic1"]["x"] == FREE_MODULE_X - 310  # 560
    assert spots["ic2"]["x"] == FREE_MODULE_X - 110  # 760
    # El hueco natural del rele (960) cae dentro del display: se corre.
    for ref in ("k1", "l1"):
        assert abs(spots[ref]["x"] - LCD_FREE_X) >= 300, (ref, spots[ref])
        assert spots[ref]["y"] == FREE_SHIFT_REGISTER_Y


def test_los_taps_del_riel_bajan_junto_al_lcd():
    # x=1100 cae en la columna 29 del riel. Los cuatro terminales de GND
    # buscan hueco contiguo hacia la izquierda en vez de dar la vuelta hasta
    # la columna 2 (eso estiraba los cables por todo el riel).
    call = fixture_to_model_call(_fixture("clave-lcd"))
    puntas = {frozenset((w["from"], w["to"])) for w in call["wires"]}

    assert frozenset(("lcd1.VDD", "T+29")) in puntas
    for pin, column in (("GND", 29), ("LED-", 28), ("RW", 27), ("VO", 26)):
        assert frozenset((f"lcd1.{pin}", f"T-{column}")) in puntas


def test_el_asignador_de_riel_no_usa_la_columna_del_puente():
    call = fixture_to_model_call(_fixture("control-acceso"))

    for wire in call["wires"]:
        for endpoint in (wire["from"], wire["to"]):
            assert endpoint not in {"T+30", "T-30", "B+30", "B-30"} or (
                wire["from"].endswith("30") and wire["to"].endswith("30")
            ), wire
