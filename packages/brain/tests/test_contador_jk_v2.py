"""Fixture v2 del contador 0-7: mismo circuito, armado legible.

Lo que estos tests protegen:
- el decodificador es el del punto 4 con AND/OR/NOT/XOR reales (siete chips);
- el display va en catodo comun, asi que las salidas de compuerta van al
  display y el sketch lee HIGH;
- una net es un nodo: ninguna pata puede estar en dos nets (eso es un corto);
- todas las patas tienen hueco (el layout v2 no deja ninguna flotando);
- los puentes no salen diagonales: mismo renglon o misma columna.
"""

from __future__ import annotations

import pytest

from tinkercad_brain.boards import footprint_for
from tinkercad_brain.builder import fixture_to_model_call
from tinkercad_brain.contador_jk_v2 import (
    FIXTURE_ID,
    _chip_types,
    contador_jk_v2_fixture,
)
from tinkercad_brain.decoder7 import GATES_V2, SEGMENT_OUTPUT_V2, XOR_GATES_V2
from tinkercad_brain.layout_v2 import (
    column_conflicts,
    plan_layout_v2,
    plan_nets_v2,
)
from tinkercad_brain.sketches import contador_jk_sketch, contador_jk_v2_sketch


def _fixture() -> dict:
    return contador_jk_v2_fixture()


def _es_hueco(endpoint: str) -> bool:
    return "." not in endpoint


def _parse(endpoint: str):
    board = 1 if endpoint.startswith("b1/") else 0
    text = endpoint.split("/", 1)[1] if "/" in endpoint else endpoint
    return board, int(text[:-1]), text[-1]


def test_la_fixture_declara_layout_v2_y_dos_placas_grandes():
    fixture = _fixture()

    assert fixture["id"] == FIXTURE_ID
    assert fixture["layout"] == "v2"
    assert [b["kind"] for b in fixture["boards"]] == ["large", "large"]
    assert [b["x"] for b in fixture["boards"]] == [870, 1570]
    assert "wiring" not in fixture, "la placa grande no tiene rieles utilizables"


def test_una_pata_esta_en_una_sola_net():
    # Dos nets con la misma pata son dos nodos con el mismo nombre: en la
    # placa eso no existe y el layout lo ve como un corto por media columna.
    # Paso de verdad al cablear el segmento e: su compuerta tambien alimenta
    # a d, y se declaro la salida dos veces.
    fixture = _fixture()
    duenio = {}
    for num, net in enumerate(fixture["nets"]):
        assert len(net) >= 2, net
        for endpoint in net:
            assert endpoint not in duenio, (
                f"{endpoint} aparece en la net {duenio.get(endpoint)} y en la {num}"
            )
            duenio[endpoint] = num


def test_el_decodificador_usa_and_or_not_xor_reales():
    fixture = _fixture()
    por_ref = {c["ref"]: c["type"] for c in fixture["components"]}

    chips = _chip_types()
    assert len(chips) == 7, chips
    assert sorted(c["type"] for c in chips) == sorted([
        "not-gate", "and-gate", "and-gate", "or-gate", "or-gate", "or-gate",
        "xor-gate",
    ])
    for chip in chips:
        assert por_ref[chip["chip"]] == chip["type"]

    # Las compuertas del netlist que NO son de estos chips no existen: cada
    # salida de `signal_nets_v2` tiene que salir de un chip de la fixture.
    for gate in GATES_V2 + XOR_GATES_V2:
        assert por_ref.get(gate.chip) in {
            "and-gate", "or-gate", "not-gate", "xor-gate",
        }, gate


def test_el_display_es_de_catodo_comun_y_su_nodo_es_la_compuerta():
    fixture = _fixture()
    gnd = next(net for net in fixture["nets"] if "uno.GND1" in net)

    assert "seg.com1" in gnd and "seg.com2" in gnd, "los comunes van a GND"
    assert not any(ep == "seg.dp" for net in fixture["nets"] for ep in net)

    # El segmento va de la compuerta a su resistencia y de ahi al display: si
    # hubiera un inversor en medio, el nodo leido seria el negativo y el
    # sketch tendria que leer LOW (eso es la v1).
    por_par = {tuple(sorted(net)) for net in fixture["nets"]}
    for seg in SEGMENT_OUTPUT_V2:
        salida = next(g for g in GATES_V2 if g.out == SEGMENT_OUTPUT_V2[seg])
        nodo = f"{salida.chip}.{salida.slot}Y"
        assert any(nodo in net and f"r{seg}.1" in net for net in fixture["nets"]), seg
        assert ("r" + seg + ".2", f"seg.{seg}") in por_par or (
            f"seg.{seg}", "r" + seg + ".2") in por_par, seg


def test_todas_las_patas_de_la_fixture_tienen_huella():
    # Una pata sin huella es una pieza que el layout no sabe insertar: el
    # build falla y no se entera nadie hasta mirar la pantalla.
    fixture = _fixture()
    tipo = {c["ref"]: c["type"] for c in fixture["components"]}
    for net in fixture["nets"]:
        for endpoint in net:
            if _es_hueco(endpoint):
                continue
            ref, pin = endpoint.split(".", 1)
            if ref == "uno":
                continue
            if tipo[ref] == "capacitor":
                continue  # pieza libre: el puente la coloca por coordenadas
            huella = footprint_for(tipo[ref])
            assert pin in huella, f"{endpoint} no esta en la huella de {tipo[ref]}"


def test_el_reparto_de_placas_es_el_medido():
    fixture = _fixture()
    plan = plan_layout_v2(fixture)

    assert plan["errors"] == [] and plan["unplaced"] == []
    por_ref = plan["placements"]
    compuertas = {c["chip"] for c in _chip_types()}
    for ref in compuertas:
        assert por_ref[ref]["board"] == 0, (ref, por_ref[ref])
    for ref in ("ff1", "ff2", "t1", "seg", "ra", "rb", "rc", "rd", "re", "rf", "rg"):
        assert por_ref[ref]["board"] == 1, (ref, por_ref[ref])
    for ref in ("c1", "c2"):
        assert "free" in por_ref[ref], ref
    # El display girado 180: con otra orientacion sus patas no caen en huecos.
    assert por_ref["seg"]["angle"] == 180
    assert por_ref["seg"]["at"].endswith("e")


def test_el_cableado_no_tiene_cortos_ni_errores():
    fixture = _fixture()
    plan = plan_layout_v2(fixture)
    nets = plan_nets_v2(fixture, plan["placements"])

    assert nets["errors"] == []
    assert column_conflicts(nets) == [], "dos nets en una media columna es un corto"
    assert len(nets["wires"]) > 100, "un contador de 7 chips no se cablea con 20 cables"


def test_ningun_puente_sale_diagonal():
    # El puente no rutea hueco-hueco: Tinkercad los dibuja rectos. Un salto
    # de (5c) a (9f) se ve diagonal sobre la placa. La regla de la v2 es que
    # todo puente comparte renglon o columna.
    fixture = _fixture()
    plan = plan_layout_v2(fixture)
    nets = plan_nets_v2(fixture, plan["placements"])

    for wire in nets["wires"]:
        if not (_es_hueco(wire["from"]) and _es_hueco(wire["to"])):
            continue
        a, b = _parse(wire["from"]), _parse(wire["to"])
        if a[0] != b[0]:
            # Puente entre placas: va en el mismo renglon, o sea horizontal.
            assert a[2] == b[2], wire
            continue
        assert a[1] == b[1] or a[2] == b[2], wire


def test_un_color_por_net_y_rojo_negro_para_la_alimentacion():
    fixture = _fixture()
    plan = plan_layout_v2(fixture)
    nets = plan_nets_v2(fixture, plan["placements"])

    colores: dict[str, set] = {}
    for wire in nets["wires"]:
        colores.setdefault(wire["net"], set()).add(wire["color"])

    assert all(len(v) == 1 for v in colores.values()), colores
    assert colores["5V"] == {"red"}
    assert colores["GND"] == {"black"}


def test_el_builder_arma_la_llamada_con_dos_placas_y_la_placa_en_cada_pieza():
    call = fixture_to_model_call(_fixture(), code="// v2")

    assert [b["did"] for b in call["boards"]] == [116648, 116648]
    por_ref = {part["ref"]: part for part in call["parts"]}
    assert "uno" not in por_ref
    for ref in ("u1", "u2", "u3", "u4", "u5", "u6", "x1"):
        assert por_ref[ref]["at"][:3] != "b1/", por_ref[ref]
    for ref in ("ff1", "t1", "seg"):
        assert por_ref[ref]["at"].startswith("b1/"), por_ref[ref]
        assert por_ref[ref]["board"] == 1
    assert por_ref["c1"]["free"] and por_ref["c2"]["free"]


def test_el_sketch_v2_lee_high_y_el_v1_sigue_leyendo_low():
    v1 = contador_jk_sketch()
    v2 = contador_jk_v2_sketch()

    assert "digitalRead(SENSE[i]) == LOW" in v1
    assert "digitalRead(SENSE_G) == LOW" in v1
    assert "digitalRead(SENSE[i]) == HIGH" in v2
    assert "digitalRead(SENSE_G) == HIGH" in v2
    assert "catodo comun" in v2 and "anodo comun" not in v2
    # Mismo esqueleto: lo unico que cambia es el nivel de "encendido".
    assert v1.count("digitalRead") == v2.count("digitalRead")
    assert len(v1.splitlines()) == len(v2.splitlines())


def test_el_oraculo_tiene_las_ocho_marcas_en_orden():
    fixture = _fixture()
    marcas = fixture["oracle_serial"]
    sketch = contador_jk_v2_sketch()

    assert marcas == [
        "TEST:PERIODO=",
        "TEST:RESET=OK",
        "TEST:CICLO=OK",
        "TEST:EN0=OK",
        "TEST:REANUDA=OK",
        "TEST:RESET_MEDIO=OK",
        "TEST:DECODER=OK",
        "TEST:FIN=OK",
    ]
    posiciones = [sketch.find(marca) for marca in marcas]
    assert all(pos >= 0 for pos in posiciones), posiciones
    assert posiciones == sorted(posiciones), posiciones


def test_el_lint_de_resistencia_serie_acepta_la_fixture():
    # Cada segmento cuelga de su compuerta por 220 ohm: si faltara, el
    # display se quemaria en el simulador y el build lo rechaza.
    from tinkercad_brain.builder import _series_resistor_errors

    assert _series_resistor_errors(_fixture()) == []
    malo = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "seg", "type": "seven-segment"},
        ],
        "nets": [["uno.A0", "seg.a"]],
    }
    assert _series_resistor_errors(malo), "sin resistencia el lint tiene que quejarse"
