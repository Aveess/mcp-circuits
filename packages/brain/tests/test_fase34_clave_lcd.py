"""Fase 34: caja fuerte con teclado 4x4 y LCD 16x2.

Contrato de la fase:

- primer circuito con dos bloques integrados: entrada matricial y salida
  de texto;
- el teclado ocupa D2..D9 y el LCD los analogicos A0..A5 (funcionan como
  digitales, verificado en vivo), porque los pines digitales restantes no
  alcanzan para los dos;
- con rieles, la alimentacion del LCD baja en vertical al riel superior;
- el sketch enmascara la clave en el LCD y muestra ABIERTO / DENEGADO;
- el servo quedo fuera a proposito: en una placa densa su cuerpo tapa los
  taps del riel y el cable de senal rodea el Uno (ver docs/fase0-vivo.md).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tinkercad_brain.builder import BuildError, fixture_to_model_call
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.sketches import keypad_lcd_sketch

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture():
    circuits = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == "clave-lcd")


def test_la_fixture_integra_teclado_lcd_y_su_resistencia():
    tipos = [c["type"] for c in _fixture()["components"]]

    assert tipos.count("keypad-4x4") == 1
    assert tipos.count("lcd-16x2") == 1
    assert tipos.count("resistor") == 1
    assert "servo" not in tipos  # el actuador quedo para otra fase


def test_el_teclado_y_el_lcd_van_libres_sin_taparse():
    layout = plan_layout(_fixture())
    placements = layout["placements"]

    # 310 unidades de separacion entre centros: los cuerpos no se tocan.
    assert placements["kp1"]["free"] == {"x": 560, "y": -230, "angle": 0}
    assert placements["lcd1"]["free"] == {"x": 870, "y": -230, "angle": 0}
    assert placements["r1"] == {"at": "1g", "pin": "1", "angle": 90}
    assert layout.get("unplaced") == []


def test_model_call_tres_partes_y_veintitres_cables():
    call = fixture_to_model_call(_fixture())

    assert len(call["parts"]) == 3  # el Uno lo crea el puente
    assert len(call["wires"]) == 23
    libres = sorted(p["ref"] for p in call["parts"] if "free" in p)
    assert libres == ["kp1", "lcd1"]


def test_el_teclado_va_a_los_pines_digitales():
    call = fixture_to_model_call(_fixture())
    puntas = {frozenset((w["from"], w["to"])) for w in call["wires"]}

    for i in range(4):
        assert frozenset((f"uno.D{2 + i}", f"kp1.row{i + 1}")) in puntas
        assert frozenset((f"uno.D{6 + i}", f"kp1.column{i + 1}")) in puntas


def test_el_lcd_usa_los_analogicos_como_digitales():
    call = fixture_to_model_call(_fixture())
    puntas = {frozenset((w["from"], w["to"])) for w in call["wires"]}

    assert frozenset(("uno.A0", "lcd1.RS")) in puntas
    assert frozenset(("uno.A1", "lcd1.E")) in puntas
    for offset, pin in enumerate(("DB4", "DB5", "DB6", "DB7")):
        assert frozenset((f"uno.A{2 + offset}", f"lcd1.{pin}")) in puntas
    # Ningun pin digital queda compartido entre los dos bloques.
    for wire in call["wires"]:
        for endpoint in (wire["from"], wire["to"]):
            if endpoint.startswith("lcd1."):
                assert "uno.D" not in wire["from"] + wire["to"], wire


def test_la_alimentacion_baja_en_vertical_al_riel_de_arriba():
    call = fixture_to_model_call(_fixture())
    puntas = {frozenset((w["from"], w["to"])) for w in call["wires"]}

    # 5V: el Uno alimenta el riel y los dos consumos bajan por su columna.
    assert frozenset(("uno.5V", "T+1")) in puntas
    assert frozenset(("1g", "T+2")) in puntas
    assert frozenset(("lcd1.VDD", "T+15")) in puntas
    # GND: los cuatro terminales del LCD bajan al mismo riel.
    for pin, column in (("GND", 15), ("LED-", 16), ("RW", 17), ("VO", 18)):
        assert frozenset((f"lcd1.{pin}", f"T-{column}")) in puntas
    assert frozenset(("uno.GND1", "T-1")) in puntas
    # Un solo riel por tipo: no hace falta puente de borde.
    assert not any("B" in (wire["from"][:1], wire["to"][:1]) for wire in call["wires"])


def test_el_builder_rechaza_un_pin_inventado_del_lcd():
    fixture = json.loads(json.dumps(_fixture()))
    fixture["nets"][-1] = ["uno.A5", "lcd1.DB8"]
    with pytest.raises(BuildError):
        fixture_to_model_call(fixture)


def test_el_sketch_integra_teclado_y_lcd_sin_servo():
    codigo = keypad_lcd_sketch()

    assert "#include <LiquidCrystal.h>" in codigo
    assert "LiquidCrystal lcd(A0, A1, A2, A3, A4, A5);" in codigo
    assert "#include <Servo.h>" not in codigo
    assert "Servo" not in codigo
    assert "pinMode(COLS[i], INPUT_PULLUP);" in codigo
    # Una pulsacion mantenida vale una sola tecla.
    assert "while (digitalRead(COLS[c]) == LOW) delay(5);" in codigo


def test_el_sketch_enmascara_la_clave_y_reporta_la_pantalla():
    codigo = keypad_lcd_sketch()

    assert "lcd.print('*');" in codigo
    assert 'linea(1, abierta ? "ABIERTO" : "DENEGADO");' in codigo
    assert 'Serial.print("TEST:PANTALLA=");' in codigo
    assert 'Serial.println("TEST:CLAVE=ESPERANDO");' in codigo
    assert 'Serial.println(abierta ? "OK" : "FALLA");' in codigo


def test_el_sketch_valida_los_pines_del_lcd_y_la_clave():
    with pytest.raises(ValueError):
        keypad_lcd_sketch(lcd_pins=("A0", "A1", "A2", "A3", "A4"))  # cinco
    with pytest.raises(ValueError):
        keypad_lcd_sketch(lcd_pins=("D10", "A1", "A2", "A3", "A4", "A5"))
    with pytest.raises(ValueError):
        keypad_lcd_sketch(lcd_pins=("A0", "A0", "A2", "A3", "A4", "A5"))
    with pytest.raises(ValueError):
        keypad_lcd_sketch(code="12345")
    with pytest.raises(ValueError):
        keypad_lcd_sketch(code="12Z4")
    with pytest.raises(ValueError):
        keypad_lcd_sketch(debounce_ms=1)
    with pytest.raises(ValueError):
        keypad_lcd_sketch(hold_ms=10)
