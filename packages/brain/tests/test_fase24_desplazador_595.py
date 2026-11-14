"""Fase 24: contador 0-9 con 74HC595 y display 7 segmentos.

Cuatro piezas nuevas:
- el 74HC595 va como parte libre (did 116695) a la izquierda del display;
- `shift_register_sketch` emite la tabla ya invertida para anodo comun y
  usa `shiftOut` con DS/SHCP/STCP;
- el cableado guardado etiqueta los pines con nombres humanos
  ("Output 1", "Shift Register Clock"...), asi que hay alias por tipo;
- `PIN_TABLE` conoce los 16 pines del integrado.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import DID_BY_TYPE, BuildError, fixture_to_model_call
from tinkercad_brain.fase0.component_map import TYPE_MAP, fixture_type
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.sketches import (
    SEVEN_SEG_DIGITS,
    _seven_seg_mask,
    shift_register_sketch,
)
from tinkercad_brain.spec import PIN_TABLE, SpecError, validate_spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture():
    circuits = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == "desplazador-595")


def test_fixture_del_595_tiene_integrado_display_y_siete_resistencias():
    fixture = _fixture()
    tipos = [c["type"] for c in fixture["components"]]
    assert tipos.count("shift-register") == 1
    assert tipos.count("seven-segment") == 1
    assert tipos.count("resistor") == 7


def test_el_595_va_libre_a_la_izquierda_del_display():
    placements = plan_layout(_fixture())["placements"]

    assert placements["ic"]["free"] == {"x": 560, "y": -230, "angle": 0}
    assert placements["seg"]["free"] == {"x": 870, "y": -230, "angle": 0}
    # Sin huecos: el integrado no ocupa columnas de la placa.
    assert all("at" not in placements[ref] for ref in ("ic", "seg"))


def test_las_siete_resistencias_caben_sin_archivar_ninguna():
    layout = plan_layout(_fixture())
    assert layout.get("unplaced") == []
    huecos = [p["at"] for p in layout["placements"].values() if "at" in p]
    assert len(huecos) == len(set(huecos)) == 7


def test_did_y_nombre_del_catalogo():
    assert DID_BY_TYPE["shift-register"] == 116695
    assert TYPE_MAP["8-Bit Shift Register [74HC595]"] == "shift-register"
    assert fixture_type("Shift Register") == "shift-register"


def test_model_call_doce_partes_y_veintidos_cables():
    call = fixture_to_model_call(_fixture())
    assert len(call["parts"]) == 9  # el Uno lo crea el puente
    assert len(call["wires"]) == 22
    ic = next(p for p in call["parts"] if p["ref"] == "ic")
    assert ic == {"ref": "ic", "did": 116695, "free": {"x": 560, "y": -230}, "angle": 0}


def test_los_cables_del_595_usan_sus_terminales_reales():
    call = fixture_to_model_call(_fixture())
    pines = sorted(
        endpoint.split(".", 1)[1]
        for wire in call["wires"]
        for endpoint in (wire["from"], wire["to"])
        if endpoint.startswith("ic.")
    )
    assert pines == ["DS", "GND", "MR", "OE", "Q0", "Q1", "Q2", "Q3",
                     "Q4", "Q5", "Q6", "SHCP", "STCP", "Vcc"]


def test_el_builder_rechaza_un_pin_inventado_del_595():
    fixture = _fixture()
    fixture = json.loads(json.dumps(fixture))
    fixture["nets"][2] = ["uno.D11", "ic.INPUT"]
    with pytest.raises(BuildError):
        fixture_to_model_call(fixture)


def test_la_tabla_del_sketch_invierte_para_anodo_comun():
    codigo = shift_register_sketch()
    # 0 logico = segmentos a..f encendidos -> 0b0111111 -> invertido 0x40.
    assert "0x40,  // 0" in codigo
    # 8 logico = todos encendidos -> invertido 0x00.
    assert "0x00,  // 8" in codigo
    # 1 logico = b,c -> 0b0000110 -> invertido 0x79.
    assert "0x79,  // 1" in codigo
    for digit in range(10):
        esperado = (~_seven_seg_mask(SEVEN_SEG_DIGITS[digit])) & 0x7F
        assert f"0x{esperado:02X},  // {digit}" in codigo, digit


def test_el_sketch_usa_shiftout_y_los_tres_pines():
    codigo = shift_register_sketch()
    assert "shiftOut(DS, SHCP, MSBFIRST, DIGITOS[digito]);" in codigo
    assert "const byte DS = 11;" in codigo
    assert "const byte SHCP = 8;" in codigo
    assert "const byte STCP = 12;" in codigo
    assert "TEST:595=LISTO" in codigo
    assert "TEST:DIGITO=" in codigo


def test_el_sketch_valida_pines_repetidos_y_hold():
    with pytest.raises(ValueError):
        shift_register_sketch(ds=11, shcp=11)
    with pytest.raises(ValueError):
        shift_register_sketch(hold_ms=0)


def test_alias_del_595_en_el_cableado_guardado():
    inspect = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno", "pins": []},
            {"type": "8-Bit Shift Register [74HC595]", "instance_id": "ic", "pins": []},
        ],
        "wires": [
            {
                "source": {"component": "8-Bit Shift Register [74HC595]", "instance_id": "ic", "pin": "Output 1"},
                "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D2"},
            },
            {
                "source": {"component": "8-Bit Shift Register [74HC595]", "instance_id": "ic", "pin": "Shift Register Clock"},
                "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D8"},
            },
            {
                "source": {"component": "8-Bit Shift Register [74HC595]", "instance_id": "ic", "pin": "Shift Register Clear"},
                "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "5V"},
            },
        ],
    }
    nets = derive_nets(inspect)
    assert ["shiftregister1.Q0", "uno.D2"] in nets
    assert ["shiftregister1.SHCP", "uno.D8"] in nets
    assert ["shiftregister1.MR", "uno.5V"] in nets


def test_spec_conoce_los_pines_del_595_y_rechaza_los_inventados():
    assert PIN_TABLE["shift-register"] == frozenset(
        {"Q0", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q7S",
         "DS", "SHCP", "STCP", "OE", "MR", "Vcc", "GND"}
    )
    with pytest.raises(SpecError):
        validate_spec(
            {
                "parts": [
                    {"ref": "ic", "type": "shift-register", "free": {"x": 560, "y": -230}},
                ],
                "wires": [["ic.NOPE", "uno.D8"]],
            }
        )
