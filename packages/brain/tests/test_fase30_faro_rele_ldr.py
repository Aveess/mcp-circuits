"""Fase 30: faro automatico con rele SPDT, NPN y LDR.

Contrato de la fase:

- el LDR va en divisor (5V -> LDR -> A0 -> R -> GND) y decide;
- la bobina del rele NO se cuelga del pin: la maneja un NPN con
  resistencia de base y diodo de recirculacion entre COIL1 y COIL2;
- COM1-R1 es el contacto normalmente abierto: al energizar alimenta la
  bombilla, que va libre porque su vidrio taparia la placa;
- A1 se cablea al nodo del contacto como oraculo: 1 con el contacto
  cerrado, 0 cuando la bombilla lo baja a GND;
- rele y bombilla van libres en la fila de partes libres (y=-230), el
  rele primero;
- el guardado del rele usa "Terminal 1..12" y el de la bombilla
  "Terminal 1/2": sin alias la conectividad se cae a 0.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import DID_BY_TYPE, BuildError, fixture_to_model_call
from tinkercad_brain.fase0.component_map import TYPE_MAP, fixture_type
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.sketches import faro_ldr_relay_sketch
from tinkercad_brain.spec import PIN_TABLE, SpecError, validate_spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture():
    circuits = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == "faro-rele-ldr")


_RAIL_RE = re.compile(r"^([TB])([+-])\d+$")


def _node(endpoint):
    """Todas las columnas del mismo riel son el mismo nodo electrico."""
    match = _RAIL_RE.match(endpoint)
    if match:
        return f"rail:{match.group(1)}{match.group(2)}"
    return endpoint


def _grupos(call):
    """Nets del cableado del modelo, con los rieles colapsados a un nodo.

    El faro usa `"wiring": "rails"`: 5V y GND no cuelgan cada uno del pin
    del Uno sino del riel. Para comprobar la fisica (que extremos quedan
    conectados) hay que leer el cableado como nodos, no como pares.
    """
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for wire in call["wires"]:
        union(_node(wire["from"]), _node(wire["to"]))
    grupos = {}
    for endpoint in parent:
        grupos.setdefault(find(endpoint), set()).add(endpoint)
    return list(grupos.values())


def _conectados(call, first, second):
    return any({_node(first), _node(second)} <= grupo for grupo in _grupos(call))


def test_la_fixture_tiene_rele_bombilla_y_el_driver_del_rele():
    tipos = [c["type"] for c in _fixture()["components"]]

    assert tipos.count("relay-spdt") == 1
    assert tipos.count("light-bulb") == 1
    assert tipos.count("transistor-npn") == 1
    assert tipos.count("diode") == 1
    assert tipos.count("photoresistor") == 1
    # Dos resistencias: divisor del LDR y base del transistor.
    assert tipos.count("resistor") == 2


def test_rele_y_bombilla_van_libres_en_la_fila_de_partes_libres():
    layout = plan_layout(_fixture())
    placements = layout["placements"]

    assert placements["k1"]["free"] == {"x": 560, "y": -230, "angle": 0}
    assert placements["lamp1"]["free"] == {"x": 760, "y": -230, "angle": 0}
    # Misma fila: no cambian de y ni se pisan.
    assert placements["k1"]["free"]["y"] == placements["lamp1"]["free"]["y"]
    assert layout.get("unplaced") == []


def test_la_placa_queda_para_el_driver_y_el_divisor():
    placements = plan_layout(_fixture())["placements"]

    assert placements["r2"] == {"at": "1g", "pin": "1", "angle": 90}
    assert placements["q1"] == {"at": "7c", "pin": "collector", "angle": 0}
    assert placements["d1"] == {"at": "15g", "pin": "anode", "angle": 90}
    # El LDR es un disco grande: arranca en la columna 22 y su divisor a 3.
    assert placements["ldr1"] == {"at": "22e", "pin": "1", "angle": 0}
    assert placements["r1"] == {"at": "25e", "pin": "1", "angle": 90}


def test_did_y_nombres_del_catalogo():
    assert DID_BY_TYPE["relay-spdt"] == 122167
    assert DID_BY_TYPE["light-bulb"] == 116693
    assert TYPE_MAP["Relay SPDT"] == "relay-spdt"
    assert TYPE_MAP["Light bulb"] == "light-bulb"
    assert fixture_type("Relay SPDT") == "relay-spdt"
    assert fixture_type("Light bulb") == "light-bulb"


def test_model_call_siete_partes_y_diecinueve_cables_con_riel():
    """19: ocho de senal + los taps de 5V/GND alimentados por el riel.

    Sin riel eran 15 (una tirada por cada tap de alimentacion). Con riel son
    tres taps de GND, cuatro de 5V, una alimentacion del Uno por riel y dos
    puentes de borde. El riel es opt-in de la fixture, no el default.
    """
    call = fixture_to_model_call(_fixture())

    assert len(call["parts"]) == 7  # el Uno lo crea el puente
    assert len(call["wires"]) == 19
    free = sorted(p["ref"] for p in call["parts"] if "free" in p)
    assert free == ["k1", "lamp1"]


def test_la_bobina_va_por_transistor_con_diodo_de_recirculacion():
    call = fixture_to_model_call(_fixture())
    puntas = {frozenset((w["from"], w["to"])) for w in call["wires"]}

    # Base por resistencia: el pin del Uno no mueve la bobina directo.
    assert frozenset(("uno.D2", "1g")) in puntas
    assert frozenset(("5g", "8c")) in puntas
    # Colector a COIL2 y emisor a tierra (por el riel): el NPN cierra.
    assert frozenset(("k1.COIL2", "7c")) in puntas
    assert _conectados(call, "9c", "uno.GND1")
    # Diodo entre los dos extremos de la bobina (anodo al colector).
    assert frozenset(("k1.COIL2", "15g")) in puntas
    assert _conectados(call, "11g", "uno.5V")
    assert _conectados(call, "k1.COIL1", "uno.5V")
    # Nada de esto pasa por el riel: la bobina es senal, no alimentacion.
    for wire in call["wires"]:
        if "k1.COIL2" in (wire["from"], wire["to"]):
            assert not wire["from"].startswith(("T", "B"))
            assert not wire["to"].startswith(("T", "B"))


def test_el_contacto_na_alimenta_la_bombilla_y_a1_lo_verifica():
    call = fixture_to_model_call(_fixture())

    # COM1 come del riel de 5V, igual que la bobina.
    assert _conectados(call, "uno.5V", "k1.COM1")
    # El nodo R1 tiene tres extremos: rele, bombilla y la lectura de A1.
    assert frozenset(("uno.A1", "k1.R1")) in {frozenset((w["from"], w["to"])) for w in call["wires"]}
    assert frozenset(("uno.A1", "lamp1.1")) in {frozenset((w["from"], w["to"])) for w in call["wires"]}
    assert _conectados(call, "lamp1.2", "uno.GND1")


def test_el_divisor_del_ldr_esta_cableado():
    call = fixture_to_model_call(_fixture())
    puntas = {frozenset((w["from"], w["to"])) for w in call["wires"]}

    assert _conectados(call, "22e", "uno.5V")
    assert frozenset(("uno.A0", "23e")) in puntas  # pin 2 del LDR
    assert frozenset(("uno.A0", "25e")) in puntas  # pin 1 de la resistencia
    assert _conectados(call, "29e", "uno.GND1")  # pin 2, cuatro al este


def test_el_builder_rechaza_un_pin_inventado_del_rele():
    fixture = json.loads(json.dumps(_fixture()))
    fixture["nets"][3] = ["uno.D2", "k1.COIL3"]
    with pytest.raises(BuildError):
        fixture_to_model_call(fixture)


def test_el_sketch_lee_ldr_decide_y_verifica_el_contacto():
    codigo = faro_ldr_relay_sketch()

    assert 'Serial.println("TEST:FARO=LISTO");' in codigo
    assert 'Serial.print("TEST:LUZ=");' in codigo
    assert 'Serial.print("TEST:RELE=");' in codigo
    assert 'Serial.print("TEST:FOCO=");' in codigo
    assert 'Serial.println("TEST:FARO=FIN");' in codigo
    # La lectura del contacto es lo que convierte el visual en oraculo.
    assert "analogRead(A1) > 700 ? 1 : 0" in codigo
    # Al final apaga la bobina y vuelve a leer: prueba las dos posiciones.
    assert 'Serial.println("TEST:RELE=OFF");' in codigo


def test_el_sketch_cabe_en_la_ventana_de_simulacion():
    """4 ciclos de 300 ms + el cierre: el FIN entra en los 5 s del runner."""
    codigo = faro_ldr_relay_sketch()

    assert "for (byte i = 0; i < 4; i++)" in codigo
    assert "delay(300);" in codigo
    assert 4 * 0.3 + 0.3 + 0.1 < 5


def test_el_sketch_valida_pines_y_parametros():
    with pytest.raises(ValueError):
        faro_ldr_relay_sketch(ldr_pin="D2")
    with pytest.raises(ValueError):
        faro_ldr_relay_sketch(sense_pin="A9")
    with pytest.raises(ValueError):
        faro_ldr_relay_sketch(ldr_pin="A1", sense_pin="A1")
    with pytest.raises(ValueError):
        faro_ldr_relay_sketch(threshold=2000)
    with pytest.raises(ValueError):
        faro_ldr_relay_sketch(cycles=0)
    with pytest.raises(ValueError):
        faro_ldr_relay_sketch(step_ms=10)


def test_alias_del_rele_y_de_la_bombilla_en_el_cableado_guardado():
    """El guardado usa Terminal 1..12: cada uno mapea a un pin del rele."""
    inspect = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno", "pins": []},
            {"type": "Relay SPDT", "instance_id": "k1", "pins": []},
            {"type": "Light bulb", "instance_id": "lamp1", "pins": []},
        ],
        "wires": [
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "5V"},
             "target": {"component": "Relay SPDT", "instance_id": "k1", "pin": "Terminal 8"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "GND"},
             "target": {"component": "Relay SPDT", "instance_id": "k1", "pin": "Terminal 5"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "5V"},
             "target": {"component": "Relay SPDT", "instance_id": "k1", "pin": "Terminal 12"}},
            {"source": {"component": "Relay SPDT", "instance_id": "k1", "pin": "Terminal 6"},
             "target": {"component": "Light bulb", "instance_id": "lamp1", "pin": "Terminal 1"}},
            {"source": {"component": "Light bulb", "instance_id": "lamp1", "pin": "Terminal 2"},
             "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "GND"}},
        ],
    }
    grupos = {frozenset(net) for net in derive_nets(inspect)}

    # 5V alimenta la bobina y el contacto; GND cierra bobina y bombilla,
    # asi que cada grupo lleva sus dos extremos.
    assert frozenset({"uno.5V", "relayspdt1.COIL1", "relayspdt1.COM1"}) in grupos
    assert frozenset({"uno.GND1", "relayspdt1.COIL2", "lightbulb1.2"}) in grupos
    assert frozenset({"relayspdt1.R1", "lightbulb1.1"}) in grupos


def test_spec_conoce_los_pines_del_rele_y_de_la_bombilla():
    assert PIN_TABLE["relay-spdt"] == frozenset(
        {"COIL1", "COIL2", "COM1", "COM2", "R1", "R2"}
    )
    assert PIN_TABLE["light-bulb"] == frozenset({"1", "2"})
    with pytest.raises(SpecError):
        validate_spec(
            {
                "parts": [
                    {"ref": "k1", "type": "relay-spdt", "free": {"x": 560, "y": -230}},
                ],
                "wires": [["k1.COIL3", "uno.5V"]],
            }
        )
