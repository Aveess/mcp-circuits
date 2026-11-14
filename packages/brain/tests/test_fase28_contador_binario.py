"""Fase 28: contador binario 4 bits 74HC93 con LEDs.

Contrato de la fase:

- Q0 se cablea a CP1 (ripple) y el Uno da el reloj en CP0 (flanco de
  bajada); MR1/MR2 van a un pin que el sketch pulsa para resetear;
- el nibble Q0..Q3 se lee y tambien enciende cuatro LEDs con resistencia;
- el sketch emite la secuencia completa (1..15, 0) y FIN;
- el contador va libre en el apilado de integrados;
- el guardado etiqueta Clock 0/1, Reset 1/2 y Output Bit 0..3.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import DID_BY_TYPE, BuildError, fixture_to_model_call
from tinkercad_brain.fase0.component_map import TYPE_MAP, fixture_type
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.sketches import binary_counter_sketch
from tinkercad_brain.spec import PIN_TABLE, SpecError, validate_spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture():
    circuits = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == "contador-binario")


def test_la_fixture_tiene_contador_y_cuatro_leds_con_resistencia():
    tipos = [c["type"] for c in _fixture()["components"]]
    assert tipos.count("binary-counter") == 1
    assert tipos.count("led") == 4
    assert tipos.count("resistor") == 4


def test_el_contador_va_libre_en_el_apilado_de_integrados():
    layout = plan_layout(_fixture())
    placements = layout["placements"]

    assert placements["n1"]["free"] == {"x": 560, "y": -230, "angle": 0}
    assert "at" not in placements["n1"]
    assert layout.get("unplaced") == []


def test_cada_led_queda_alineado_con_su_resistencia():
    """r en <c>g (pin 2 en c+4) y su LED en <c+4>i: cable vertical corto."""
    placements = plan_layout(_fixture())["placements"]

    for resistor, led, column in (
        ("r1", "led1", 1), ("r2", "led2", 7), ("r3", "led3", 13), ("r4", "led4", 19),
    ):
        assert placements[resistor] == {"at": f"{column}g", "pin": "1", "angle": 90}
        assert placements[led] == {
            "at": f"{column + 4}i", "pin": "anode", "angle": 180,
        }


def test_did_y_nombres_del_catalogo():
    assert DID_BY_TYPE["binary-counter"] == 116728
    assert TYPE_MAP["4-Bit Binary Counter [74HC93]"] == "binary-counter"
    assert fixture_type("Binary Counter") == "binary-counter"


def test_model_call_nueve_partes_y_veintidos_cables():
    call = fixture_to_model_call(_fixture())

    assert len(call["parts"]) == 9  # el Uno lo crea el puente
    assert len(call["wires"]) == 22
    free = [p for p in call["parts"] if "free" in p]
    assert free == [
        {"ref": "n1", "did": 116728, "free": {"x": 560, "y": -230}, "angle": 0}
    ]


def test_el_ripple_q0_reloj1_esta_cableado():
    call = fixture_to_model_call(_fixture())
    puntas = {frozenset((w["from"], w["to"])) for w in call["wires"]}

    # Q0 y CP1 comparten net (ripple): la estrella cuelga del pin del Uno,
    # asi que ambos llegan a el. Sin esto el contador no pasa de 1 bit.
    assert frozenset(("uno.D4", "n1.Q0")) in puntas
    assert frozenset(("uno.D4", "n1.CP1")) in puntas
    # El reset y el reloj salen del Uno.
    assert frozenset(("uno.D3", "n1.MR1")) in puntas
    assert frozenset(("uno.D3", "n1.MR2")) in puntas
    assert frozenset(("uno.D2", "n1.CP0")) in puntas
    # Cada bit va al Uno y, desde el mismo hub, a su resistencia (LED en
    # serie).
    for bit, pin, resistor in (
        ("Q0", "D4", "1g"), ("Q1", "D5", "7g"),
        ("Q2", "D6", "13g"), ("Q3", "D7", "19g"),
    ):
        assert frozenset((f"n1.{bit}", f"uno.{pin}")) in puntas
        assert frozenset((f"uno.{pin}", resistor)) in puntas


def test_el_builder_rechaza_un_pin_inventado_del_contador():
    fixture = json.loads(json.dumps(_fixture()))
    fixture["nets"][3] = ["uno.D2", "n1.CLOCK"]
    with pytest.raises(BuildError):
        fixture_to_model_call(fixture)


def test_el_sketch_resetea_y_emite_la_secuencia_completa():
    codigo = binary_counter_sketch()

    assert 'Serial.println("TEST:CONTADOR=LISTO");' in codigo
    assert "digitalWrite(RST, HIGH);" in codigo
    assert "digitalWrite(RST, LOW);" in codigo
    assert "for (byte i = 0; i < 16; i++)" in codigo
    assert 'Serial.print("TEST:CONTADOR=");' in codigo
    assert "Serial.println(leer());" in codigo
    assert 'Serial.println("TEST:CONTADOR=FIN");' in codigo
    assert "if (digitalRead(Q0)) valor |= 1;" in codigo
    assert "if (digitalRead(Q3)) valor |= 8;" in codigo


def test_el_loop_sigue_contando_despacio_sin_serial():
    codigo = binary_counter_sketch()

    loop = codigo.split("void loop()", 1)[1]
    assert "digitalWrite(CLK, HIGH);" in loop
    assert "Test" not in loop and "Serial" not in loop


def test_el_sketch_valida_pines_y_parametros():
    with pytest.raises(ValueError):
        binary_counter_sketch(clk=2, reset=2)
    with pytest.raises(ValueError):
        binary_counter_sketch(bits=(4, 4, 6, 7))
    with pytest.raises(ValueError):
        binary_counter_sketch(settle_ms=0)
    with pytest.raises(ValueError):
        binary_counter_sketch(pulses=0)
    with pytest.raises(ValueError):
        binary_counter_sketch(pulses=65)


def test_alias_del_contador_en_el_cableado_guardado():
    """El guardado usa Clock 0/1, Reset 1/2 y Output Bit 0..3."""
    inspect = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno", "pins": []},
            {"type": "4-Bit Binary Counter [74HC93]", "instance_id": "n1", "pins": []},
        ],
        "wires": [
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "5V"},
             "target": {"component": "4-Bit Binary Counter [74HC93]", "instance_id": "n1", "pin": "Power"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "GND"},
             "target": {"component": "4-Bit Binary Counter [74HC93]", "instance_id": "n1", "pin": "Ground"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D2"},
             "target": {"component": "4-Bit Binary Counter [74HC93]", "instance_id": "n1", "pin": "Clock 0"}},
            {"source": {"component": "4-Bit Binary Counter [74HC93]", "instance_id": "n1", "pin": "Output Bit 0"},
             "target": {"component": "4-Bit Binary Counter [74HC93]", "instance_id": "n1", "pin": "Clock 1"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D3"},
             "target": {"component": "4-Bit Binary Counter [74HC93]", "instance_id": "n1", "pin": "Reset 1"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D3"},
             "target": {"component": "4-Bit Binary Counter [74HC93]", "instance_id": "n1", "pin": "Reset 2"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D7"},
             "target": {"component": "4-Bit Binary Counter [74HC93]", "instance_id": "n1", "pin": "Output Bit 3"}},
        ],
    }
    grupos = {frozenset(net) for net in derive_nets(inspect)}

    assert frozenset({"uno.5V", "binarycounter1.Vcc"}) in grupos
    assert frozenset({"uno.GND1", "binarycounter1.GND"}) in grupos
    assert frozenset({"uno.D2", "binarycounter1.CP0"}) in grupos
    assert frozenset({"binarycounter1.CP1", "binarycounter1.Q0"}) in grupos
    assert frozenset({"uno.D3", "binarycounter1.MR1", "binarycounter1.MR2"}) in grupos
    assert frozenset({"uno.D7", "binarycounter1.Q3"}) in grupos


def test_spec_conoce_los_pines_del_contador():
    assert PIN_TABLE["binary-counter"] == frozenset(
        {"CP0", "CP1", "MR1", "MR2", "Q0", "Q1", "Q2", "Q3", "Vcc", "GND"}
    )
    with pytest.raises(SpecError):
        validate_spec(
            {
                "parts": [
                    {"ref": "n1", "type": "binary-counter", "free": {"x": 560, "y": -230}},
                ],
                "wires": [["n1.Q9", "uno.D2"]],
            }
        )
