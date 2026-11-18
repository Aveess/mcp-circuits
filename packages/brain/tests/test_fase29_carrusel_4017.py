"""Fase 29: carrusel de 4 LEDs con el 74HC4017 (contador Johnson).

Contrato de la fase:

- el 4017 avanza en cada flanco de subida de CP0 y tiene las salidas
  one-hot; Q4 se cablea a MR para que el carrusel de la vuelta en 4 pasos
  sin que el Uno intervenga;
- CP1n (clock enable) va a GND y Vcc/GND salen del Uno;
- el Uno relojea CP0 y lee Q0..Q3, que ademas encienden cuatro LEDs con
  su resistencia (r en <c>g, LED en <c+4>i);
- el sketch emite la secuencia de la salida activa y FIN;
- el 4017 va libre en la fila de integrados (x=560, y=-230);
- el guardado etiqueta Power/Ground/Clock/Clock Enable/Reset y
  Output 1..10 (Q0 -> Output 1, Q4 -> Output 5).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import DID_BY_TYPE, BuildError, fixture_to_model_call
from tinkercad_brain.fase0.component_map import TYPE_MAP, fixture_type
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.sketches import decade_counter_sketch
from tinkercad_brain.spec import PIN_TABLE, SpecError, validate_spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture():
    circuits = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == "carrusel-4017")


def test_la_fixture_tiene_4017_y_cuatro_leds_con_resistencia():
    fixture = _fixture()
    tipos = [c["type"] for c in fixture["components"]]

    assert tipos.count("decade-counter") == 1
    assert tipos.count("led") == 4
    assert tipos.count("resistor") == 4
    # El segundo build reusa el diseno en vez de crear un duplicado.
    assert fixture["tinkercad_id"] == "ij6ypc8wB5x"


def test_el_4017_va_libre_en_la_fila_de_integrados():
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
    assert DID_BY_TYPE["decade-counter"] == 129343
    assert TYPE_MAP["Johnson Decade Counter [74HC4017]"] == "decade-counter"
    assert fixture_type("Decade Counter") == "decade-counter"


def test_model_call_nueve_partes_y_veintiun_cables():
    call = fixture_to_model_call(_fixture())

    assert len(call["parts"]) == 9  # el Uno lo crea el puente
    assert len(call["wires"]) == 21
    free = [p for p in call["parts"] if "free" in p]
    assert free == [
        {"ref": "n1", "did": 129343, "free": {"x": 560, "y": -230}, "angle": 0}
    ]


def test_q4_resetea_en_anillo_y_cp1n_queda_habilitado():
    call = fixture_to_model_call(_fixture())
    puntas = {frozenset((w["from"], w["to"])) for w in call["wires"]}

    # La realimentacion Q4 -> MR es lo que hace que el carrusel de 4 pasos
    # vuelva a Q0; sin ella el 4017 recorre las 10 salidas.
    assert frozenset(("n1.Q4", "n1.MR")) in puntas
    # CP1n es enable activo en bajo: sin tierra no avanza.
    assert frozenset(("uno.GND1", "n1.CP1n")) in puntas
    assert frozenset(("uno.5V", "n1.Vcc")) in puntas
    assert frozenset(("uno.GND1", "n1.GND")) in puntas
    assert frozenset(("uno.D2", "n1.CP0")) in puntas


def test_cada_salida_va_al_uno_y_a_su_resistencia():
    call = fixture_to_model_call(_fixture())
    puntas = {frozenset((w["from"], w["to"])) for w in call["wires"]}

    for salida, pin, columna in (
        ("Q0", "D4", 1), ("Q1", "D5", 7), ("Q2", "D6", 13), ("Q3", "D7", 19),
    ):
        anodo = f"{columna + 4}i"
        catodo = f"{columna + 5}i"
        assert frozenset((f"n1.{salida}", f"uno.{pin}")) in puntas
        # La resistencia cuelga del hub del Uno (net en estrella de 3) y su
        # pin 2 baja a la misma columna del anodo del LED.
        assert frozenset((f"uno.{pin}", f"{columna}g")) in puntas
        assert frozenset((f"{columna + 4}g", anodo)) in puntas
        # El catodo cierra el circuito a tierra.
        assert frozenset((catodo, "uno.GND1")) in puntas


def test_el_builder_rechaza_un_pin_inventado_del_4017():
    fixture = json.loads(json.dumps(_fixture()))
    fixture["nets"][3] = ["uno.D2", "n1.CLOCK"]
    with pytest.raises(BuildError):
        fixture_to_model_call(fixture)


def test_el_sketch_relojea_y_emite_la_salida_activa():
    codigo = decade_counter_sketch()

    assert 'Serial.println("TEST:4017=LISTO");' in codigo
    assert "digitalWrite(CLK, HIGH);" in codigo
    assert "digitalWrite(CLK, LOW);" in codigo
    assert 'Serial.print("TEST:4017=");' in codigo
    assert "Serial.println(leer());" in codigo
    assert 'Serial.println("TEST:4017=FIN");' in codigo
    assert "if (digitalRead(Q3)) return 3;" in codigo
    for pin in ("Q0", "Q1", "Q2", "Q3", "CLK"):
        assert f"pinMode({pin}," in codigo


def test_el_sketch_cabe_en_la_ventana_de_simulacion():
    """8 pasos de 400 ms + arranque: el oraculo cierra antes de 5 s.

    Con 500 ms el ciclo son 4 s y el FIN se queda fuera de la ventana del
    runner: el serial mostraba el carrusel pero nunca el cierre.
    """
    codigo = decade_counter_sketch()

    assert "for (byte i = 0; i < 8; i++)" in codigo
    assert "delay(380);" in codigo
    # 8 * 0.4 s = 3.2 s, mas 0.1 s de setup: el FIN entra en la ventana.
    assert 8 * 0.4 + 0.1 < 5


def test_el_sketch_valida_pines_y_parametros():
    with pytest.raises(ValueError):
        decade_counter_sketch(clk=2, bits=(4, 5, 6, 2))
    with pytest.raises(ValueError):
        decade_counter_sketch(bits=(4, 4, 6, 7))
    with pytest.raises(ValueError):
        decade_counter_sketch(step_ms=0)
    with pytest.raises(ValueError):
        decade_counter_sketch(step_ms=10)
    with pytest.raises(ValueError):
        decade_counter_sketch(cycles=0)
    with pytest.raises(ValueError):
        decade_counter_sketch(cycles=21)


def test_alias_del_4017_en_el_cableado_guardado():
    """El guardado usa Output 1..10, Clock, Clock Enable y Reset."""
    inspect = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno", "pins": []},
            {"type": "Johnson Decade Counter [74HC4017]", "instance_id": "n1", "pins": []},
        ],
        "wires": [
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "5V"},
             "target": {"component": "Johnson Decade Counter [74HC4017]", "instance_id": "n1", "pin": "Power"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "GND"},
             "target": {"component": "Johnson Decade Counter [74HC4017]", "instance_id": "n1", "pin": "Ground"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "GND"},
             "target": {"component": "Johnson Decade Counter [74HC4017]", "instance_id": "n1", "pin": "Clock Enable"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D2"},
             "target": {"component": "Johnson Decade Counter [74HC4017]", "instance_id": "n1", "pin": "Clock"}},
            {"source": {"component": "Johnson Decade Counter [74HC4017]", "instance_id": "n1", "pin": "Output 5"},
             "target": {"component": "Johnson Decade Counter [74HC4017]", "instance_id": "n1", "pin": "Reset"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D4"},
             "target": {"component": "Johnson Decade Counter [74HC4017]", "instance_id": "n1", "pin": "Output 1"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D7"},
             "target": {"component": "Johnson Decade Counter [74HC4017]", "instance_id": "n1", "pin": "Output 4"}},
        ],
    }
    grupos = {frozenset(net) for net in derive_nets(inspect)}

    assert frozenset({"uno.5V", "decadecounter1.Vcc"}) in grupos
    assert frozenset({"uno.GND1", "decadecounter1.GND", "decadecounter1.CP1n"}) in grupos
    assert frozenset({"uno.D2", "decadecounter1.CP0"}) in grupos
    # Output 5 es Q4 y Output 1 es Q0: si el alias se corre uno, el anillo
    # de 4 pasos pasa a 5 o a 3.
    assert frozenset({"decadecounter1.Q4", "decadecounter1.MR"}) in grupos
    assert frozenset({"uno.D4", "decadecounter1.Q0"}) in grupos
    assert frozenset({"uno.D7", "decadecounter1.Q3"}) in grupos


def test_spec_conoce_los_pines_del_4017():
    assert PIN_TABLE["decade-counter"] == frozenset(
        {"CP0", "CP1n", "MR", "Q0", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7",
         "Q8", "Q9", "Q5-9n", "Vcc", "GND"}
    )
    with pytest.raises(SpecError):
        validate_spec(
            {
                "parts": [
                    {"ref": "n1", "type": "decade-counter", "free": {"x": 560, "y": -230}},
                ],
                "wires": [["n1.Q10", "uno.D2"]],
            }
        )
