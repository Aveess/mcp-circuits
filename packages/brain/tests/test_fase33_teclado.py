"""Fase 33: cerradura con teclado 4x4 y dos LEDs.

Contrato de la fase:

- el teclado va libre en la fila de partes libres; cuatro filas a D2..D5 y
  cuatro columnas a D6..D9, sin alimentacion;
- la clave de cuatro teclas enciende el LED de apertura (D10) y, si falla,
  el de rechazo (D11);
- el sketch barre la matriz con ``INPUT_PULLUP`` y **espera a que la tecla
  se suelte**: una pulsacion mantenida vale una sola tecla;
- el oraculo imprime ``TEST:TECLA=<tecla>`` por pulsacion y
  ``TEST:CLAVE=OK`` / ``TEST:CLAVE=FALLA`` al completar cuatro;
- el guardado del teclado usa ``Row n`` / ``Column n``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import DID_BY_TYPE, BuildError, fixture_to_model_call
from tinkercad_brain.fase0.component_map import TYPE_MAP, fixture_type
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.sketches import keypad_lock_sketch
from tinkercad_brain.spec import PIN_TABLE, SpecError, validate_spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture():
    circuits = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == "cerradura-teclado")


def test_la_fixture_tiene_teclado_y_dos_leds_con_sus_resistencias():
    tipos = [c["type"] for c in _fixture()["components"]]

    assert tipos.count("keypad-4x4") == 1
    assert tipos.count("led") == 2
    assert tipos.count("resistor") == 2


def test_el_teclado_va_libre_y_los_leds_en_la_placa():
    layout = plan_layout(_fixture())
    placements = layout["placements"]

    assert placements["kp1"]["free"] == {"x": 560, "y": -230, "angle": 0}
    assert "at" not in placements["kp1"]
    # Cada LED con su resistencia, en la misma columna.
    assert placements["r1"] == {"at": "1g", "pin": "1", "angle": 90}
    assert placements["led1"] == {"at": "5i", "pin": "anode", "angle": 180}
    assert placements["r2"] == {"at": "7g", "pin": "1", "angle": 90}
    assert placements["led2"] == {"at": "11i", "pin": "anode", "angle": 180}
    assert layout.get("unplaced") == []


def test_did_y_nombres_del_catalogo():
    assert DID_BY_TYPE["keypad-4x4"] == 203761
    assert TYPE_MAP["Keypad 4x4"] == "keypad-4x4"
    assert fixture_type("Keypad 4x4") == "keypad-4x4"


def test_model_call_cinco_partes_y_quince_cables():
    call = fixture_to_model_call(_fixture())

    assert len(call["parts"]) == 5  # el Uno lo crea el puente
    assert len(call["wires"]) == 15
    free = [p for p in call["parts"] if "free" in p]
    assert free == [
        {"ref": "kp1", "did": 203761, "free": {"x": 560, "y": -230}, "angle": 0}
    ]


def test_las_ocho_lineas_del_teclado_van_a_los_pines_dos_a_nueve():
    call = fixture_to_model_call(_fixture())
    puntas = {frozenset((w["from"], w["to"])) for w in call["wires"]}

    for i in range(4):
        assert frozenset((f"uno.D{2 + i}", f"kp1.row{i + 1}")) in puntas
        assert frozenset((f"uno.D{6 + i}", f"kp1.column{i + 1}")) in puntas
    # El teclado no se alimenta: ninguna de sus patas toca 5V ni GND.
    for wire in call["wires"]:
        for endpoint in (wire["from"], wire["to"]):
            if endpoint.startswith("kp1."):
                assert not endpoint.startswith(("kp1.vcc", "kp1.gnd")), wire


def test_cada_led_cuelga_de_su_pin_y_cierra_en_el_riel():
    call = fixture_to_model_call(_fixture())
    puntas = {frozenset((w["from"], w["to"])) for w in call["wires"]}

    assert frozenset(("uno.D10", "1g")) in puntas
    assert frozenset(("5g", "5i")) in puntas
    assert frozenset(("uno.D11", "7g")) in puntas
    assert frozenset(("11g", "11i")) in puntas
    # Los dos catodos bajan al riel de arriba; con un solo riel en uso no
    # hace falta puente de borde.
    assert frozenset(("6i", "T-6")) in puntas
    assert frozenset(("12i", "T-12")) in puntas
    assert frozenset(("uno.GND1", "T-1")) in puntas
    assert not any("B-" in wire["from"] or "B-" in wire["to"] for wire in call["wires"])


def test_el_builder_rechaza_una_fila_inventada_del_teclado():
    fixture = json.loads(json.dumps(_fixture()))
    fixture["nets"][0] = ["uno.D2", "kp1.row5"]
    with pytest.raises(BuildError):
        fixture_to_model_call(fixture)


def test_el_sketch_barre_la_matriz_y_espera_a_que_se_suelte():
    codigo = keypad_lock_sketch()

    assert "pinMode(COLS[i], INPUT_PULLUP);" in codigo
    assert "digitalWrite(FILAS[f], LOW);" in codigo
    assert "digitalRead(COLS[c]) == LOW" in codigo
    # Una pulsacion mantenida vale una sola tecla: sin esta espera el
    # barrido reporta la misma tecla muchas veces y la clave nunca cierra.
    assert "while (digitalRead(COLS[c]) == LOW) delay(5);" in codigo
    # Sin librerias: el teclado se barre a mano.
    assert "#include" not in codigo


def test_el_sketch_imprime_teclas_y_el_resultado_de_las_cuatro():
    codigo = keypad_lock_sketch()

    assert 'Serial.println("TEST:KP=LISTO");' in codigo
    assert 'Serial.println("TEST:CLAVE=ESPERANDO");' in codigo
    assert 'Serial.print("TEST:TECLA=");' in codigo
    assert 'Serial.println(abierta ? "OK" : "FALLA");' in codigo
    assert "if (digitos == 4) {" in codigo
    assert "bool abierta = (aciertos == 4);" in codigo
    # La tabla es fila-mayor, como el teclado fisico medido en vivo.
    assert "{'1', '2', '3', 'A'}," in codigo
    assert "{'*', '0', '#', 'D'}" in codigo  # ultima fila, sin coma final


def test_el_sketch_valida_pines_y_clave():
    with pytest.raises(ValueError):
        keypad_lock_sketch(row_pins=(2, 3, 4), column_pins=(6, 7, 8, 9))
    with pytest.raises(ValueError):
        keypad_lock_sketch(row_pins=(2, 3, 4, 6), column_pins=(6, 7, 8, 9))
    with pytest.raises(ValueError):
        keypad_lock_sketch(open_led=2)  # pin del teclado
    with pytest.raises(ValueError):
        keypad_lock_sketch(open_led=10, deny_led=10)
    with pytest.raises(ValueError):
        keypad_lock_sketch(code="123")  # tres teclas
    with pytest.raises(ValueError):
        keypad_lock_sketch(code="12Z4")  # tecla que no existe
    with pytest.raises(ValueError):
        keypad_lock_sketch(debounce_ms=1)


def test_alias_del_teclado_en_el_cableado_guardado():
    """El guardado del teclado usa Row n / Column n."""
    inspect = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno", "pins": []},
            {"type": "Keypad 4x4", "instance_id": "kp1", "pins": []},
        ],
        "wires": [
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D2"},
             "target": {"component": "Keypad 4x4", "instance_id": "kp1", "pin": "Row 1"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D9"},
             "target": {"component": "Keypad 4x4", "instance_id": "kp1", "pin": "Column 4"}},
        ],
    }
    grupos = {frozenset(net) for net in derive_nets(inspect)}

    assert frozenset({"uno.D2", "keypad4x41.row1"}) in grupos
    assert frozenset({"uno.D9", "keypad4x41.column4"}) in grupos


def test_spec_conoce_las_ocho_lineas_del_teclado():
    assert PIN_TABLE["keypad-4x4"] == frozenset(
        {f"row{i}" for i in range(1, 5)} | {f"column{i}" for i in range(1, 5)}
    )
    with pytest.raises(SpecError):
        validate_spec(
            {
                "parts": [
                    {"ref": "kp1", "type": "keypad-4x4", "free": {"x": 560, "y": -230}},
                ],
                "wires": [["kp1.row5", "uno.D2"]],
            }
        )
