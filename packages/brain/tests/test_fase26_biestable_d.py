"""Fase 26: biestable D 74HC74 como divisor por 2 (biestable T).

Contrato de la fase:

- 1D se ata a 1NQ (1Q conmuta en cada flanco) y el reloj lo maneja el Uno;
- 1RD y 1SD quedan en alto (inactivos) y la mitad 2 se deja estable;
- el sketch imprime cada muestra (TEST:FF=q) y un veredicto explicito
  (TEST:FF=TOGGLE-OK / FAIL) que compara solo muestras consecutivas;
- el registro va libre en el apilado de integrados y el guardado usa
  Input/Clock/Reset/Set/Output/Inverted Output.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import DID_BY_TYPE, BuildError, fixture_to_model_call
from tinkercad_brain.fase0.component_map import TYPE_MAP, fixture_type
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.sketches import d_flip_flop_sketch
from tinkercad_brain.spec import PIN_TABLE, SpecError, validate_spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture():
    circuits = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == "biestable-d")


def test_la_fixture_tiene_un_74hc74_un_led_y_su_resistencia():
    tipos = [c["type"] for c in _fixture()["components"]]
    assert tipos.count("flip-flop-d") == 1
    assert tipos.count("led") == 1
    assert tipos.count("resistor") == 1


def test_el_registro_va_libre_en_el_apilado_de_integrados():
    placements = plan_layout(_fixture())["placements"]

    assert placements["ff"]["free"] == {"x": 560, "y": -230, "angle": 0}
    assert "at" not in placements["ff"]
    layout = plan_layout(_fixture())
    assert layout.get("unplaced") == []


def test_did_y_nombres_del_catalogo():
    assert DID_BY_TYPE["flip-flop-d"] == 116725
    assert TYPE_MAP["Dual D Flip-Flop [74HC74]"] == "flip-flop-d"
    assert fixture_type("D Flip-Flop") == "flip-flop-d"


def test_model_call_tres_partes_y_catorce_cables():
    call = fixture_to_model_call(_fixture())

    assert len(call["parts"]) == 3  # el Uno lo crea el puente
    assert len(call["wires"]) == 14
    assert any(
        p == {"ref": "ff", "did": 116725, "free": {"x": 560, "y": -230}, "angle": 0}
        for p in call["parts"]
    )


def test_los_cables_terminan_en_los_terminales_reales_del_registro():
    call = fixture_to_model_call(_fixture())
    pins = sorted(
        endpoint.split(".", 1)[1]
        for wire in call["wires"]
        for endpoint in (wire["from"], wire["to"])
        if endpoint.startswith("ff.")
    )
    assert pins == [
        "1CP", "1D", "1NQ", "1Q", "1RD", "1SD",
        "2CP", "2D", "2RD", "2SD", "GND", "Vcc",
    ]


def test_el_feedback_1nq_a_1d_esta_en_el_cableado():
    call = fixture_to_model_call(_fixture())
    puntas = {frozenset((w["from"], w["to"])) for w in call["wires"]}
    assert frozenset(("ff.1NQ", "ff.1D")) in puntas


def test_el_builder_rechaza_un_pin_inventado_del_registro():
    fixture = json.loads(json.dumps(_fixture()))
    fixture["nets"][2] = ["uno.D2", "ff.1CLOCK"]
    with pytest.raises(BuildError):
        fixture_to_model_call(fixture)


def test_el_sketch_emite_muestras_y_veredicto_explicito():
    codigo = d_flip_flop_sketch()

    assert 'Serial.println("TEST:FF=LISTO");' in codigo
    assert 'Serial.print("TEST:FF=");' in codigo
    assert 'Serial.println(alterna ? "TEST:FF=TOGGLE-OK" : "TEST:FF=FAIL");' in codigo
    assert "for (byte i = 0; i < 8; i++)" in codigo
    assert "digitalWrite(CLK, HIGH);" in codigo
    assert "digitalWrite(CLK, LOW);" in codigo


def test_el_veredicto_compara_solo_muestras_consecutivas():
    """Leer Q antes del primer pulso no es fiable (el pin flota)."""
    codigo = d_flip_flop_sketch()

    assert "int previo = -1;" in codigo
    assert "if (previo >= 0 && actual == previo)" in codigo
    assert "bool previo = digitalRead(Q);" not in codigo


def test_el_sketch_valida_pines_y_parametros():
    with pytest.raises(ValueError):
        d_flip_flop_sketch(clk=2, q=2)
    with pytest.raises(ValueError):
        d_flip_flop_sketch(settle_ms=0)
    with pytest.raises(ValueError):
        d_flip_flop_sketch(cycles=0)
    with pytest.raises(ValueError):
        d_flip_flop_sketch(cycles=True)


def test_alias_del_registro_en_el_cableado_guardado():
    inspect = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno", "pins": []},
            {"type": "Dual D Flip-Flop [74HC74]", "instance_id": "ff", "pins": []},
        ],
        "wires": [
            {"source": {"component": "Dual D Flip-Flop [74HC74]", "instance_id": "ff", "pin": "Power"},
             "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "5V"}},
            {"source": {"component": "Dual D Flip-Flop [74HC74]", "instance_id": "ff", "pin": "Ground"},
             "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "GND"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D2"},
             "target": {"component": "Dual D Flip-Flop [74HC74]", "instance_id": "ff", "pin": "Clock 1"}},
            {"source": {"component": "Dual D Flip-Flop [74HC74]", "instance_id": "ff", "pin": "Inverted Output 1"},
             "target": {"component": "Dual D Flip-Flop [74HC74]", "instance_id": "ff", "pin": "Input 1"}},
            {"source": {"component": "Dual D Flip-Flop [74HC74]", "instance_id": "ff", "pin": "Output 1"},
             "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D4"}},
        ],
    }
    nets = derive_nets(inspect)

    assert ["flipflopd1.Vcc", "uno.5V"] in nets
    assert ["flipflopd1.GND", "uno.GND1"] in nets
    assert ["flipflopd1.1CP", "uno.D2"] in nets
    assert ["flipflopd1.1D", "flipflopd1.1NQ"] in nets
    assert ["flipflopd1.1Q", "uno.D4"] in nets


def test_spec_conoce_los_pines_del_registro_y_rechaza_los_inventados():
    assert PIN_TABLE["flip-flop-d"] == frozenset(
        {"1D", "1CP", "1RD", "1SD", "1Q", "1NQ",
         "2D", "2CP", "2RD", "2SD", "2Q", "2NQ", "Vcc", "GND"}
    )
    with pytest.raises(SpecError):
        validate_spec(
            {
                "parts": [
                    {"ref": "ff", "type": "flip-flop-d", "free": {"x": 560, "y": -230}},
                ],
                "wires": [["ff.9Q", "uno.D2"]],
            }
        )
