"""Fase 25: media suma con compuertas logicas (74HC86 XOR + 74HC00 NAND).

Contrato de la fase:

- el XOR da la SUMA y dos NAND en cascada dan el ACARREO (NAND + NOT);
- las tres compuertas van libres en una fila sobre la placa (y=-230, de
  200 en 200) y se cablean a sus terminales reales, sin geometria de huecos;
- el Uno maneja A y B y LEE suma/acarreo, que tambien encienden un LED con
  su resistencia;
- el oraculo serial imprime la tabla completa (a,b,suma,acarreo);
- el guardado etiqueta Input 1A/Input 1B/Output 1/Power/Ground y hay alias
  por tipo.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import DID_BY_TYPE, BuildError, fixture_to_model_call
from tinkercad_brain.fase0.component_map import TYPE_MAP, fixture_type
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.sketches import half_adder_sketch
from tinkercad_brain.spec import PIN_TABLE, SpecError, validate_spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture():
    circuits = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == "media-suma-logica")


def test_la_fixture_tiene_xor_dos_nand_y_dos_leds_con_resistencia():
    tipos = [c["type"] for c in _fixture()["components"]]
    assert tipos.count("xor-gate") == 1
    assert tipos.count("nand-gate") == 2
    assert tipos.count("led") == 2
    assert tipos.count("resistor") == 2


def test_las_tres_compuertas_van_libres_en_una_fila_de_200_en_200():
    placements = plan_layout(_fixture())["placements"]

    assert placements["xor1"]["free"] == {"x": 560, "y": -230, "angle": 0}
    assert placements["nand1"]["free"] == {"x": 760, "y": -230, "angle": 0}
    assert placements["nand2"]["free"] == {"x": 960, "y": -230, "angle": 0}
    # Fila horizontal: mismo y, x creciente en el orden de la fixture.
    assert {p["free"]["y"] for p in placements.values() if "free" in p} == {-230}
    # Ninguna compuerta ocupa columnas de la placa.
    assert all("at" not in placements[ref] for ref in ("xor1", "nand1", "nand2"))


def test_dos_leds_con_sus_resistencias_se_colocan_sin_archivar_nada():
    layout = plan_layout(_fixture())
    assert layout.get("unplaced") == []
    huecos = [p["at"] for p in layout["placements"].values() if "at" in p]
    assert len(huecos) == len(set(huecos)) == 4


def test_did_y_nombres_del_catalogo():
    assert DID_BY_TYPE["xor-gate"] == 116727
    assert DID_BY_TYPE["nand-gate"] == 116696
    assert TYPE_MAP["Quad XOR gate [74HC86]"] == "xor-gate"
    assert TYPE_MAP["Quad NAND gate [74HC00]"] == "nand-gate"
    assert fixture_type("XOR Gate") == "xor-gate"
    assert fixture_type("Quad NAND gate") == "nand-gate"


def test_model_call_siete_partes_y_veinte_cables():
    call = fixture_to_model_call(_fixture())

    assert len(call["parts"]) == 7  # el Uno lo crea el puente
    assert len(call["wires"]) == 20
    free = {p["ref"]: p for p in call["parts"] if "free" in p}
    assert free["xor1"] == {"ref": "xor1", "did": 116727,
                            "free": {"x": 560, "y": -230}, "angle": 0}
    assert free["nand1"]["did"] == free["nand2"]["did"] == 116696


def test_los_cables_terminan_en_los_terminales_reales_de_las_compuertas():
    call = fixture_to_model_call(_fixture())
    pins = sorted(
        endpoint.split(".", 1)[1]
        for wire in call["wires"]
        for endpoint in (wire["from"], wire["to"])
        if endpoint.startswith(("xor1.", "nand1.", "nand2."))
    )
    # nand1.1Y aparece en dos cables (hacia 1A y 1B del segundo NAND).
    assert pins == [
        "1A", "1A", "1A", "1B", "1B", "1B", "1Y", "1Y", "1Y", "1Y",
        "GND", "GND", "GND", "Vcc", "Vcc", "Vcc",
    ]


def test_el_builder_rechaza_un_pin_inventado_de_la_compuerta():
    fixture = json.loads(json.dumps(_fixture()))
    fixture["nets"][2] = ["uno.D2", "xor1.9Z"]
    with pytest.raises(BuildError):
        fixture_to_model_call(fixture)


def test_el_sketch_emite_la_tabla_completa_de_la_media_suma():
    codigo = half_adder_sketch()

    assert 'Serial.println("TEST:LOGICA=LISTO");' in codigo
    assert "medir(0, 0);" in codigo
    assert "medir(0, 1);" in codigo
    assert "medir(1, 0);" in codigo
    assert "medir(1, 1);" in codigo
    assert 'Serial.print("TEST:HA=");' in codigo
    assert "pinMode(SUMA, INPUT);" in codigo
    assert "pinMode(ACARREO, INPUT);" in codigo


def test_el_sketch_valida_pines_repetidos_y_el_tiempo_de_estabilizacion():
    with pytest.raises(ValueError):
        half_adder_sketch(a=2, b=2)
    with pytest.raises(ValueError):
        half_adder_sketch(sum_pin=4, carry_pin=4)
    with pytest.raises(ValueError):
        half_adder_sketch(settle_ms=0)


def test_alias_de_las_compuertas_en_el_cableado_guardado():
    """El guardado usa Input 1A/Input 1B/Output 1/Power/Ground."""
    inspect = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno", "pins": []},
            {"type": "Quad XOR gate [74HC86]", "instance_id": "xor", "pins": []},
        ],
        "wires": [
            {"source": {"component": "Quad XOR gate [74HC86]", "instance_id": "xor", "pin": "Power"},
             "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "5V"}},
            {"source": {"component": "Quad XOR gate [74HC86]", "instance_id": "xor", "pin": "Ground"},
             "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "GND"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D2"},
             "target": {"component": "Quad XOR gate [74HC86]", "instance_id": "xor", "pin": "Input 1A"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D4"},
             "target": {"component": "Quad XOR gate [74HC86]", "instance_id": "xor", "pin": "Output 1"}},
        ],
    }
    nets = derive_nets(inspect)

    assert ["uno.5V", "xorgate1.Vcc"] in nets
    assert ["uno.GND1", "xorgate1.GND"] in nets
    assert ["uno.D2", "xorgate1.1A"] in nets
    assert ["uno.D4", "xorgate1.1Y"] in nets


def test_alias_del_nand_no_se_confunde_con_el_del_xor():
    inspect = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno", "pins": []},
            {"type": "Quad NAND gate [74HC00]", "instance_id": "nand", "pins": []},
        ],
        "wires": [
            {"source": {"component": "Quad NAND gate [74HC00]", "instance_id": "nand", "pin": "Input 1A"},
             "target": {"component": "Quad NAND gate [74HC00]", "instance_id": "nand", "pin": "Input 1B"}},
            {"source": {"component": "Quad NAND gate [74HC00]", "instance_id": "nand", "pin": "Output 1"},
             "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D5"}},
        ],
    }
    nets = derive_nets(inspect)

    assert ["nandgate1.1A", "nandgate1.1B"] in nets
    assert ["nandgate1.1Y", "uno.D5"] in nets


def test_spec_conoce_los_pines_de_ambas_compuertas():
    esperado = {"1A", "1B", "1Y", "2A", "2B", "2Y", "3A", "3B", "3Y",
                "4A", "4B", "4Y", "Vcc", "GND"}
    assert PIN_TABLE["xor-gate"] == frozenset(esperado)
    assert PIN_TABLE["nand-gate"] == frozenset(esperado)

    with pytest.raises(SpecError):
        validate_spec(
            {
                "parts": [
                    {"ref": "xor1", "type": "xor-gate", "free": {"x": 560, "y": -230}},
                ],
                "wires": [["xor1.9Z", "uno.D2"]],
            }
        )
