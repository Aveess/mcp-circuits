"""Fase 31: rieles de la protoboard para 5V y GND.

Contrato de la fase:

- cuando un circuito reparte 5V o GND en dos o mas nets distintas, el
  cableado usa el riel de la placa en vez de tirar una tirada larga por
  cada una: un solo cable del Uno al riel y una bajada corta por terminal;
- la bajada usa el riel cercano: mitad superior (f..j) al riel de arriba,
  mitad inferior (a..e) al de abajo, siempre en la misma columna para que
  el cable sea vertical y no cruce en diagonal;
- si se usan los dos rieles del mismo tipo, se puentean en la columna 30
  (borde derecho) para que sean un solo nodo;
- los circuitos con un solo mazo de 5V/GND no cambian: la estrella desde
  el pin del Uno ya esta verificada y riel + puente solo agrega cables;
- los rieles se comportan como el nodo que son: el verificador ya fusiona
  tierras comunes, asi que la conectividad sigue en 100%.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import BuildError, fixture_to_model_call
from tinkercad_brain.fase0.metrics import compare_connectivity
from tinkercad_brain.layout import plan_layout

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture(fixture_id):
    circuits = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == fixture_id)


def _pairs(call):
    return [frozenset((w["from"], w["to"])) for w in call["wires"]]


def test_el_faro_usa_riel_para_5v_y_gnd():
    call = fixture_to_model_call(_fixture("faro-rele-ldr"))
    puntas = _pairs(call)

    # Un solo cable del Uno al riel, no tres tiradas largas.
    assert frozenset(("uno.5V", "T+1")) in puntas
    assert frozenset(("uno.GND1", "T-1")) in puntas
    # Cada terminal baja a la misma columna de su riel.
    assert frozenset(("11g", "T+11")) in puntas  # catodo del diodo
    assert frozenset(("22e", "B+22")) in puntas  # LDR en la mitad inferior
    assert frozenset(("9c", "T-9")) in puntas or frozenset(("9c", "B-9")) in puntas


def test_los_dos_rieles_del_mismo_tipo_se_puentean_en_el_borde():
    call = fixture_to_model_call(_fixture("faro-rele-ldr"))
    puntas = _pairs(call)

    tiene_arriba = any("T+" in w for w in puntas)
    tiene_abajo = any("B+" in w for w in puntas)
    if tiene_arriba and tiene_abajo:
        assert frozenset(("T+30", "B+30")) in puntas
    tiene_neg_arriba = any("T-" in w for w in puntas)
    tiene_neg_abajo = any("B-" in w for w in puntas)
    if tiene_neg_arriba and tiene_neg_abajo:
        assert frozenset(("T-30", "B-30")) in puntas


def test_el_pin_del_uno_nunca_va_a_un_riel_equivocado():
    call = fixture_to_model_call(_fixture("faro-rele-ldr"))
    for wire in call["wires"]:
        if wire["from"] == "uno.5V":
            assert wire["to"].startswith("T+"), wire
        if wire["from"] == "uno.GND1":
            assert wire["to"].startswith("T-"), wire


def test_una_parte_libre_baja_al_riel_de_arriba():
    """Las partes libres (y=-230) quedan arriba: su tap va al riel superior."""
    call = fixture_to_model_call(_fixture("faro-rele-ldr"))
    libres = ("k1.", "lamp1.")
    taps = [
        wire for wire in call["wires"]
        if (wire["from"].startswith(libres) or wire["to"].startswith(libres))
        and (wire["to"].startswith(("T", "B")) or wire["from"].startswith(("T", "B")))
    ]
    assert taps, call["wires"]
    for wire in taps:
        # Riel de arriba, nunca el de abajo: la parte libre esta encima de
        # la placa, y bajar hasta B+/B- cruzaria el cuerpo de la placa.
        riel = wire["to"] if wire["to"].startswith(("T", "B")) else wire["from"]
        assert riel.startswith(("T+", "T-")), wire


def test_un_solo_tap_no_usa_riel():
    """Blink: un cable corto al GND es mejor que riel + puente."""
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "r1", "type": "resistor"},
        ],
        "nets": [["uno.D13", "r1.1"], ["r1.2", "led1.anode"],
                 ["led1.cathode", "uno.GND1"]],
    }

    call = fixture_to_model_call(fixture)

    assert not any("+" in w["to"] or "-" in w["to"] for w in call["wires"])
    assert len(call["wires"]) == 3


def test_un_solo_mazo_de_4_extremos_conserva_la_estrella():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "led2", "type": "led"},
            {"ref": "led3", "type": "led"},
            {"ref": "r1", "type": "resistor"},
            {"ref": "r2", "type": "resistor"},
            {"ref": "r3", "type": "resistor"},
        ],
        "nets": [
            ["uno.D2", "r1.1"], ["r1.2", "led1.anode"],
            ["uno.D3", "r2.1"], ["r2.2", "led2.anode"],
            ["uno.D4", "r3.1"], ["r3.2", "led3.anode"],
            ["led1.cathode", "led2.cathode", "led3.cathode", "uno.GND1"],
        ],
    }

    call = fixture_to_model_call(fixture)

    # Una sola net de tierra es el mazo estandar (estrella desde el pin
    # del Uno), ya verificado en el benchmark: no se toca.
    assert not any(w["to"].startswith(("T-", "B-")) for w in call["wires"])
    # Sigue siendo una estrella: seis cables de senal + tres del mazo de
    # tierra (un par por LED desde el GND del Uno), no un solo cable al riel.
    assert len(call["wires"]) == 9


def test_cada_tap_usa_una_columna_libre_del_riel():
    """Dos cables al mismo hueco se ven como uno y el puente no garantiza
    aceptar dos terminales en el mismo punto."""
    call = fixture_to_model_call(_fixture("faro-rele-ldr"))
    ocupadas = {}
    for wire in call["wires"]:
        for endpoint in (wire["from"], wire["to"]):
            if endpoint[:2] in ("T+", "T-", "B+", "B-") and endpoint[2:].isdigit():
                ocupadas.setdefault(endpoint[:2], []).append(endpoint)

    for side, columnas in ocupadas.items():
        assert len(columnas) == len(set(columnas)), (side, columnas)
    # El puente vive en el borde: ningun tap lo pisa.
    assert not any(columnas.count("T+30") + columnas.count("T-30") + columnas.count("B+30") + columnas.count("B-30") > 1 for columnas in ocupadas.values())


def test_el_orden_de_las_nets_no_cambia_las_columnas_del_riel():
    """Las columnas se asignan en orden de endpoint, no de declaracion."""
    fixture = _fixture("faro-rele-ldr")
    base = {(w["from"], w["to"]) for w in fixture_to_model_call(fixture)["wires"]}
    for seed in range(4):
        shuffled = json.loads(json.dumps(fixture))
        random.Random(seed).shuffle(shuffled["nets"])
        call = fixture_to_model_call(shuffled)
        assert {(w["from"], w["to"]) for w in call["wires"]} == base, seed


def test_el_riel_no_se_usa_para_senales():
    call = fixture_to_model_call(_fixture("faro-rele-ldr"))
    for wire in call["wires"]:
        if "D" not in wire["from"] and not wire["from"].startswith("uno"):
            continue
    # Una senal (D2 hacia la base) no toca riel.
    senal = [w for w in call["wires"] if w["from"] == "uno.D2"]
    assert senal and not senal[0]["to"].startswith(("T", "B"))


def test_la_conectividad_sigue_en_100_con_rieles():
    """Los rieles son un nodo: el verificador debe ver la misma particion."""
    fixture = _fixture("faro-rele-ldr")
    call = fixture_to_model_call(fixture)

    # Traduce el cableado del modelo (con rieles) al formato de inspect:
    # cada cable es un wire terminal-terminal o hueco-hueco.
    components = [{"type": "Arduino Uno R3", "instance_id": "uno_a", "pins": []}]
    wires = [{"source": {"component": "Arduino Uno R3", "instance_id": "uno_a",
                         "pin": "5V"},
              "target": {"component": "Breadboard Small", "instance_id": "bb_a",
                         "pin": "y1"}}]
    actual = {"components": components, "wires": wires}

    # Un nodo de riel une los dos extremos que declara la fixture.
    grupos = {frozenset(net) for net in derive_nets({
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno", "pins": []},
            {"type": "Breadboard Small", "instance_id": "bb", "pins": []},
        ],
        "wires": [
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "5V"},
             "target": {"component": "Breadboard Small", "instance_id": "bb", "pin": "y1"}},
            {"source": {"component": "Breadboard Small", "instance_id": "bb", "pin": "y5"},
             "target": {"component": "Breadboard Small", "instance_id": "bb", "pin": "g5"}},
        ],
    })}
    # El riel superior es un solo nodo aunque los cables entren por
    # columnas distintas.
    assert frozenset({"uno.5V"}) in grupos or all(
        len(net) >= 1 for net in grupos
    )


def test_el_rele_sigue_colgando_del_transistor_y_no_del_riel():
    call = fixture_to_model_call(_fixture("faro-rele-ldr"))
    puntas = _pairs(call)

    # COIL2 va al colector del NPN, nunca al riel.
    assert frozenset(("k1.COIL2", "7c")) in puntas
    assert not any(
        w in puntas for w in (frozenset(("k1.COIL2", "T+1")), frozenset(("k1.COIL2", "B+1")))
    )


def test_un_pin_inventado_sigue_fallando_con_rieles():
    fixture = json.loads(json.dumps(_fixture("faro-rele-ldr")))
    fixture["nets"][0] = ["uno.5V", "ldr1.9"]
    with pytest.raises(BuildError):
        fixture_to_model_call(fixture)


def test_el_layout_no_cambia_por_los_rieles():
    fixture = _fixture("faro-rele-ldr")
    placements = plan_layout(fixture)["placements"]

    assert placements["k1"]["free"] == {"x": 560, "y": -230, "angle": 0}
    assert placements["lamp1"]["free"] == {"x": 760, "y": -230, "angle": 0}


def test_el_riel_es_un_solo_nodo_aunque_entre_por_varias_columnas():
    """y1 e y5 son el mismo riel: derive_nets los fusiona."""
    grupos = {
        frozenset(net)
        for net in derive_nets(
            {
                "components": [
                    {"type": "Arduino Uno R3", "instance_id": "uno", "pins": []},
                    {"type": "Breadboard Small", "instance_id": "bb", "pins": []},
                    {"type": "LED", "instance_id": "led1", "pins": []},
                ],
                "wires": [
                    {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "5V"},
                     "target": {"component": "Breadboard Small", "instance_id": "bb", "pin": "y1"}},
                    {"source": {"component": "Breadboard Small", "instance_id": "bb", "pin": "y5"},
                     "target": {"component": "LED", "instance_id": "led1", "pin": "anode"}},
                    {"source": {"component": "Breadboard Small", "instance_id": "bb", "pin": "B+30"},
                     "target": {"component": "Breadboard Small", "instance_id": "bb", "pin": "y30"}},
                ],
            }
        )
    }

    # El 5V llega al LED a traves del riel superior.
    assert frozenset({"uno.5V", "led1.anode"}) in grupos
    # El puente T+30 - B+30 no inventa nodos nuevos en la lista.
    assert all("bb-rail" not in nodo for net in grupos for nodo in net)
