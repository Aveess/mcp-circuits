"""Fase 35: colocacion libre de partes grandes.

Contrato de la fase:

- la fixture puede pedir ``"free_parts": ["sv1"]`` y esa parte deja de
  montarse en la placa;
- las partes libres van a la derecha de la placa y a su altura, apiladas
  hacia abajo: a la altura del display el cable de senal lo cruza y una
  fila mas arriba el cuerpo del servo se monta encima del teclado
  (medido en vivo en la sonda 1altWwNOQdW);
- sus terminales se resuelven por nombre real (servo: Ground/Power/Signal)
  y sus nets de alimentacion bajan al riel de abajo, no al de arriba;
- un ref inexistente, un LED o un ref que ya va libre es error de layout;
- el circuito de la fase integra teclado + LCD + servo (tres bloques).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tinkercad_brain.builder import fixture_to_model_call
from tinkercad_brain.layout import LayoutError, plan_layout
from tinkercad_brain.sketches import access_control_sketch
from tinkercad_brain.spec import validate_spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixtures():
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def _fixture(circuit_id="control-acceso"):
    return next(c for c in _fixtures() if c["id"] == circuit_id)


def _blink():
    return next(c for c in _fixtures() if c["id"] == "blink-basico")


def test_la_fixture_integra_teclado_lcd_y_servo():
    tipos = [c["type"] for c in _fixture()["components"]]

    assert tipos.count("keypad-4x4") == 1
    assert tipos.count("lcd-16x2") == 1
    assert tipos.count("servo") == 1
    assert _fixture()["free_parts"] == ["sv1"]


def test_el_servo_va_libre_a_la_derecha_de_la_placa():
    layout = plan_layout(_fixture())

    assert layout["placements"]["sv1"]["free"] == {"x": 1250, "y": 60, "angle": 0}
    assert "at" not in layout["placements"]["sv1"]
    # El orden de la fila libre no depende del orden de las nets.
    assert layout["placements"]["kp1"]["free"] == {"x": 560, "y": -230, "angle": 0}
    assert layout["placements"]["lcd1"]["free"] == {"x": 1100, "y": -230, "angle": 0}
    assert layout.get("unplaced") == []


def test_dos_partes_libres_se_apilan_sin_tocarse():
    fixture = _blink()
    fixture["components"] = fixture["components"] + [
        {"ref": "sv1", "type": "servo"},
        {"ref": "sv2", "type": "servo"},
    ]
    fixture["nets"] = [["uno.D9", "sv1.signal"], ["uno.D10", "sv2.signal"]]
    fixture["free_parts"] = ["sv1", "sv2"]

    placements = plan_layout(fixture)["placements"]

    assert placements["sv1"]["free"]["y"] == 60
    assert placements["sv2"]["free"]["y"] == 260
    assert placements["sv1"]["free"]["x"] == placements["sv2"]["free"]["x"] == 1250


def test_un_ref_inexistente_en_free_parts_es_error():
    fixture = _blink()
    fixture["free_parts"] = ["noexiste"]

    with pytest.raises(LayoutError, match="no existen"):
        plan_layout(fixture)


def test_un_led_no_puede_ir_libre():
    fixture = _blink()
    fixture["free_parts"] = ["led1"]

    with pytest.raises(LayoutError, match="montado en la placa"):
        plan_layout(fixture)


def test_free_parts_debe_ser_una_lista():
    fixture = _blink()
    fixture["free_parts"] = "led1"

    with pytest.raises(LayoutError, match="lista"):
        plan_layout(fixture)


def test_una_parte_que_ya_va_libre_no_se_repite():
    fixture = _fixture()  # el lcd1 ya va libre por su tipo
    fixture["free_parts"] = ["lcd1"]

    with pytest.raises(LayoutError, match="ya se coloca libre"):
        plan_layout(fixture)


def test_los_pines_del_servo_libre_usan_sus_nombres_reales():
    call = fixture_to_model_call(_fixture())
    sv1 = next(p for p in call["parts"] if p["ref"] == "sv1")

    assert sv1["free"] == {"x": 1250, "y": 60}
    puntas = {frozenset((w["from"], w["to"])) for w in call["wires"]}
    assert frozenset(("uno.D10", "sv1.Signal")) in puntas
    assert frozenset(("sv1.Power", "B+29")) in puntas
    assert frozenset(("sv1.Ground", "B-29")) in puntas


def test_el_servo_baja_al_riel_de_abajo_no_al_de_arriba():
    call = fixture_to_model_call(_fixture())

    for wire in call["wires"]:
        if "sv1.Power" in (wire["from"], wire["to"]):
            assert wire["to"].startswith("B+"), wire
        if "sv1.Ground" in (wire["from"], wire["to"]):
            assert wire["to"].startswith("B-"), wire
    # Con los dos rieles en uso, el puente de borde existe una sola vez.
    puentes = [
        w for w in call["wires"]
        if {w["from"], w["to"]} == {"T+30", "B+30"} or {w["from"], w["to"]} == {"T-30", "B-30"}
    ]
    assert len(puentes) == 2


def test_el_esquema_valida_un_pin_inventado_del_servo_libre():
    spec = {
        "parts": [
            {"ref": "sv1", "type": "servo", "free": {"x": 1250, "y": 60}},
        ],
        "wires": [["sv1.senal", "uno.D10"]],
    }

    with pytest.raises(Exception):
        validate_spec(spec)


def test_el_sketch_integra_los_tres_bloques():
    codigo = access_control_sketch()

    assert "#include <LiquidCrystal.h>" in codigo
    assert "#include <Servo.h>" in codigo
    assert "LiquidCrystal lcd(A0, A1, A2, A3, A4, A5);" in codigo
    assert "cerrojo.attach(PIN_SERVO);" in codigo
    assert "pinMode(COLS[i], INPUT_PULLUP);" in codigo
    # Una pulsacion mantenida vale una sola tecla.
    assert "while (digitalRead(COLS[c]) == LOW) delay(5);" in codigo


def test_el_sketch_mueve_el_cerrojo_y_lo_devuelve_a_cerrado():
    codigo = access_control_sketch()

    assert "cerrojo.write(abierta ? ABIERTO : CERRADO);" in codigo
    assert 'Serial.print("TEST:SERVO=");' in codigo
    assert "Serial.println(abierta ? ABIERTO : CERRADO);" in codigo
    # El cerrojo se vuelve a cerrar solo, sin esperar otra tecla.
    assert codigo.count("cerrojo.write(CERRADO);") >= 2
    assert 'linea(1, abierta ? "ABIERTO" : "DENEGADO");' in codigo
    assert 'Serial.print("TEST:PANTALLA=");' in codigo


def test_el_sketch_valida_pines_y_angulos():
    with pytest.raises(ValueError):
        access_control_sketch(servo_pin=2)  # pin del teclado
    with pytest.raises(ValueError):
        access_control_sketch(open_angle=90, closed_angle=90)
    with pytest.raises(ValueError):
        access_control_sketch(open_angle=200)
    with pytest.raises(ValueError):
        access_control_sketch(lcd_pins=("D0", "A1", "A2", "A3", "A4", "A5"))
    with pytest.raises(ValueError):
        access_control_sketch(code="12Z4")
