"""Fase 32: alarma de movimiento con PIR, buzzer y LED.

Contrato de la fase:

- el PIR va libre en la fila de partes libres y entrega un nivel en D2;
- con movimiento el sketch enciende el LED de D4 y hace sonar el buzzer
  de D3 con ``tone``; sin movimiento, ``noTone`` y LED apagado;
- el sketch imprime **solo los cambios** de estado (``TEST:MOV=1`` /
  ``TEST:MOV=0``) ademas del estado inicial: el estimulo lo da el
  simulador, no el sketch, y la ventana del runner no se llena de ceros;
- tres nets de GND: el circuito opta por rieles (fase 31);
- el guardado del PIR usa Signal/Power/Ground, inspect devuelve
  out/vcc/gnd.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import DID_BY_TYPE, BuildError, fixture_to_model_call
from tinkercad_brain.fase0.component_map import TYPE_MAP, fixture_type
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.sketches import pir_alarm_sketch
from tinkercad_brain.spec import PIN_TABLE, SpecError, validate_spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture():
    circuits = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == "alarma-pir")


def test_la_fixture_tiene_pir_buzzer_y_led_con_resistencia():
    tipos = [c["type"] for c in _fixture()["components"]]

    assert tipos.count("pir-sensor") == 1
    assert tipos.count("buzzer") == 1
    assert tipos.count("led") == 1
    assert tipos.count("resistor") == 1


def test_el_pir_va_libre_y_el_resto_en_la_placa():
    layout = plan_layout(_fixture())
    placements = layout["placements"]

    assert placements["pir1"]["free"] == {"x": 560, "y": -230, "angle": 0}
    assert "at" not in placements["pir1"]
    # La resistencia y su LED, alineados en la columna 1/5.
    assert placements["r1"] == {"at": "1g", "pin": "1", "angle": 90}
    assert placements["led1"] == {"at": "5i", "pin": "anode", "angle": 180}
    # El buzzer es un disco grande: arranca en la columna 24.
    assert placements["buzzer1"] == {"at": "24e", "pin": "positive", "angle": 0}
    assert layout.get("unplaced") == []


def test_did_y_nombres_del_catalogo():
    assert DID_BY_TYPE["pir-sensor"] == 234203
    assert TYPE_MAP["PIR Sensor"] == "pir-sensor"
    assert fixture_type("PIR Sensor") == "pir-sensor"


def test_model_call_cuatro_partes_y_diez_cables():
    call = fixture_to_model_call(_fixture())

    assert len(call["parts"]) == 4  # el Uno lo crea el puente
    assert len(call["wires"]) == 10
    free = [p for p in call["parts"] if "free" in p]
    assert free == [
        {"ref": "pir1", "did": 234203, "free": {"x": 560, "y": -230}, "angle": 0}
    ]


def test_el_pir_alimenta_y_entrega_su_salida_en_d2():
    call = fixture_to_model_call(_fixture())
    puntas = {frozenset((w["from"], w["to"])) for w in call["wires"]}

    assert frozenset(("uno.D2", "pir1.out")) in puntas
    assert frozenset(("uno.5V", "pir1.vcc")) in puntas
    assert frozenset(("pir1.gnd", "T-2")) in puntas
    assert frozenset(("uno.GND1", "T-1")) in puntas


def test_el_buzzer_y_el_led_cuelgan_del_uno_y_cierran_en_el_riel():
    call = fixture_to_model_call(_fixture())
    puntas = {frozenset((w["from"], w["to"])) for w in call["wires"]}

    assert frozenset(("uno.D3", "24e")) in puntas  # positivo del buzzer
    assert frozenset(("29e", "B-29")) in puntas  # negativo, al riel de abajo
    assert frozenset(("uno.D4", "1g")) in puntas
    assert frozenset(("5g", "5i")) in puntas  # resistencia -> anodo
    assert frozenset(("6i", "T-6")) in puntas  # catodo -> riel de arriba
    # Los dos rieles de GND se puentean en el borde.
    assert frozenset(("T-30", "B-30")) in puntas


def test_el_builder_rechaza_un_pin_inventado_del_pir():
    fixture = json.loads(json.dumps(_fixture()))
    fixture["nets"][2] = ["uno.D2", "pir1.signal"]
    with pytest.raises(BuildError):
        fixture_to_model_call(fixture)


def test_el_sketch_avisa_sonando_y_solo_imprime_los_cambios():
    codigo = pir_alarm_sketch()

    assert 'Serial.println("TEST:PIR=LISTO");' in codigo
    assert 'Serial.print("TEST:MOV=");' in codigo
    assert "tone(BUZZER, 1000);" in codigo
    assert "noTone(BUZZER);" in codigo
    assert "digitalWrite(LED, movimiento ? HIGH : LOW);" in codigo
    # Solo imprime cuando cambia: el oraculo no se llena de ceros.
    assert "if (movimiento != estado) {" in codigo
    assert codigo.count('Serial.print("TEST:MOV=");') == 2  # setup + cambio
    # Sin FIN: la alarma queda armada esperando el estimulo.
    assert "FIN" not in codigo


def test_el_sketch_valida_pines_y_parametros():
    with pytest.raises(ValueError):
        pir_alarm_sketch(pir_pin=2, buzzer_pin=2)  # repetido
    with pytest.raises(ValueError):
        pir_alarm_sketch(pir_pin=99)
    with pytest.raises(ValueError):
        pir_alarm_sketch(tone_hz=10)
    with pytest.raises(ValueError):
        pir_alarm_sketch(poll_ms=5)


def test_alias_del_pir_en_el_cableado_guardado():
    """El guardado del PIR usa Signal/Power/Ground."""
    inspect = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno", "pins": []},
            {"type": "PIR Sensor", "instance_id": "pir1", "pins": []},
        ],
        "wires": [
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D2"},
             "target": {"component": "PIR Sensor", "instance_id": "pir1", "pin": "Signal"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "5V"},
             "target": {"component": "PIR Sensor", "instance_id": "pir1", "pin": "Power"}},
            {"source": {"component": "PIR Sensor", "instance_id": "pir1", "pin": "Ground"},
             "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "GND"}},
        ],
    }
    grupos = {frozenset(net) for net in derive_nets(inspect)}

    assert frozenset({"uno.D2", "pirsensor1.out"}) in grupos
    assert frozenset({"uno.5V", "pirsensor1.vcc"}) in grupos
    assert frozenset({"uno.GND1", "pirsensor1.gnd"}) in grupos


def test_spec_conoce_los_pines_del_pir():
    assert PIN_TABLE["pir-sensor"] == frozenset({"out", "vcc", "gnd"})
    with pytest.raises(SpecError):
        validate_spec(
            {
                "parts": [
                    {"ref": "pir1", "type": "pir-sensor", "free": {"x": 560, "y": -230}},
                ],
                "wires": [["pir1.signal", "uno.D2"]],
            }
        )
