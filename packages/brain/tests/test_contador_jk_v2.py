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

import json
from pathlib import Path

import pytest

from tinkercad_brain.boards import footprint_for
from tinkercad_brain.builder import fixture_to_model_call
from tinkercad_brain.contador_jk_v2 import (
    FIXTURE_ID,
    _PIN_GIRADO,
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


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "fase0" / "circuits.json"


def _es_hueco(endpoint: str) -> bool:
    return "." not in endpoint


def _parse(endpoint: str):
    board = int(endpoint[1]) if endpoint.startswith("b") and "/" in endpoint else 0
    text = endpoint.split("/", 1)[1] if "/" in endpoint else endpoint
    return board, int(text[:-1]), text[-1]


def test_la_entrada_del_repositorio_es_la_que_genera_el_modulo():
    # Misma red de seguridad que la v1: si la entrada de circuits.json y el
    # generador divergen, el build en vivo arma un circuito que no es el que
    # los tests aprueban. El mensaje dice cual clave se separo.
    circuits = json.loads(FIXTURES.read_text(encoding="utf-8"))
    entrada = next((c for c in circuits if c["id"] == FIXTURE_ID), None)
    assert entrada is not None, f"falta {FIXTURE_ID} en circuits.json"

    generada = _fixture()
    claves = (
        "title", "layout", "boards", "components", "nets", "doc", "oracle",
        "oracle_serial", "notes", "sim_wait_seconds", "code_features",
    )
    for clave in claves:
        assert entrada.get(clave) == generada.get(clave), clave

    # El id lo escribe la corrida en vivo, no el generador. Si se pierde, el
    # siguiente build crea un duplicado en el dashboard en vez de reusarlo.
    assert entrada.get("tinkercad_id"), "la entrada necesita tinkercad_id"


def test_la_fixture_declara_layout_v2_dos_placas_grandes_y_una_chica():
    fixture = _fixture()

    assert fixture["id"] == FIXTURE_ID
    assert fixture["layout"] == "v2"
    assert [b["kind"] for b in fixture["boards"]] == ["large", "large", "small"]
    assert [b["x"] for b in fixture["boards"]] == [870, 1570, 2100]
    # La chica arranca en la columna 9: con dos capacitores, empezar en la 1
    # los deja pegados al borde y el montaje se ve a medias.
    assert fixture["boards"][2].get("start") == 9
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

    # Va UN solo comun, como en la v1: medido en el diseno jWUw1co8IZH, el
    # cableado guardado etiqueta las dos patas del comun igual ("Common"),
    # asi que la lectura no puede distinguirlas y declarar las dos bajaba la
    # fidelidad a 40/41 nets sin que faltara un solo cable.
    assert "seg.com1" in gnd, "el comun va a GND"
    assert "seg.com2" not in gnd, "la lectura no distingue los dos comunes"
    assert not any(ep == "seg.dp" for net in fixture["nets"] for ep in net)

    # El segmento va de la compuerta a su resistencia y de ahi al display: si
    # hubiera un inversor en medio, el nodo leido seria el negativo y el
    # sketch tendria que leer LOW (eso es la v1).
    por_par = {tuple(sorted(net)) for net in fixture["nets"]}
    for seg in SEGMENT_OUTPUT_V2:
        salida = next(g for g in GATES_V2 if g.out == SEGMENT_OUTPUT_V2[seg])
        nodo = f"{salida.chip}.{salida.slot}Y"
        assert any(nodo in net and f"r{seg}.1" in net for net in fixture["nets"]), seg
        pata = _PIN_GIRADO[seg]
        assert ("r" + seg + ".2", f"seg.{pata}") in por_par or (
            f"seg.{pata}", "r" + seg + ".2") in por_par, seg


def test_el_display_girado_cablea_cada_segmento_por_su_pata_opuesta():
    # El modulo entra girado 180 grados (unica orientacion que encaja en la
    # placa grande). Un giro de 180 grados mueve la pata `a` al sitio de la
    # `d`, la `b` al de la `e` y la `c` al de la `f`; `g` queda en el medio.
    # Si alguien "arregla" el cableado poniendo segmento a -> pata a, el
    # numero sale invertido en la placa aunque el serial siga en verde.
    assert _PIN_GIRADO == {"a": "d", "b": "e", "c": "f",
                           "d": "a", "e": "b", "f": "c", "g": "g"}

    fixture = _fixture()
    pares = {tuple(sorted(net)) for net in fixture["nets"] if len(net) == 2}
    for seg in SEGMENT_OUTPUT_V2:
        assert (f"r{seg}.2", f"seg.{_PIN_GIRADO[seg]}") in pares, seg
    # Ninguna senal de segmento cae en su pata homonima: eso seria cablearlo
    # como si el display estuviera derecho, y en la placa se lee al reves.
    for seg in "abcdef":
        assert (f"r{seg}.2", f"seg.{seg}") not in pares, seg


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
    # Los capacitores ya no cuelgan libres a la derecha: van insertados en la
    # placa chica, uno al lado del otro y lejos del borde.
    for ref, primera in (("c1", 9), ("c2", 13)):
        assert "free" not in por_ref[ref], por_ref[ref]
        assert por_ref[ref]["board"] == 2, (ref, por_ref[ref])
        assert por_ref[ref]["at"] == f"{primera}f", por_ref[ref]
    # Girado 180: es la unica orientacion en la que sus diez patas entran en
    # huecos (medido: a 0 el puente no encuentra angulo y pierde 8 nets).
    assert por_ref["seg"]["angle"] == 180
    assert por_ref["seg"]["at"].endswith("e")


def test_el_cableado_no_tiene_cortos_ni_errores():
    fixture = _fixture()
    plan = plan_layout_v2(fixture)
    nets = plan_nets_v2(fixture, plan["placements"])

    assert nets["errors"] == []
    assert column_conflicts(nets) == [], "dos nets en una media columna es un corto"
    assert len(nets["wires"]) > 100, "un contador de 7 chips no se cablea con 20 cables"


def test_dos_patas_no_cuelgan_del_mismo_hueco():
    # Dos cables de pata en un hueco se dibujan como uno: en el diseno
    # jWUw1co8IZH los dos capacitores libres caian en b1/45i y el circuito se
    # veia con un solo cable. Un cable de pata si puede entrar donde termina
    # un puente de la misma fila: eso es un tap, no una superposicion.
    fixture = _fixture()
    plan = plan_layout_v2(fixture)
    nets = plan_nets_v2(fixture, plan["placements"])

    por_hueco: dict[str, list] = {}
    for wire in nets["wires"]:
        if _es_hueco(wire["from"]) and _es_hueco(wire["to"]):
            continue
        hueco = wire["to"] if _es_hueco(wire["to"]) else wire["from"]
        por_hueco.setdefault(hueco, []).append(wire["net"])

    repetidos = {h: v for h, v in por_hueco.items() if len(v) > 1}
    assert repetidos == {}, repetidos


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


def test_ningun_cable_empieza_y_termina_en_el_mismo_hueco():
    # Un cable de un hueco a si mismo no se ve (largo cero) y el puente lo
    # rechaza. Aparecio con la placa chica: la net del CTRL tocaba la placa 1
    # por la mitad de abajo y la 2 por la de arriba, y el cruce elegia la
    # misma columna de la pata. `emit` ahora lo rechaza con nombre.
    fixture = _fixture()
    plan = plan_layout_v2(fixture)
    nets = plan_nets_v2(fixture, plan["placements"])

    repetidos = [w for w in nets["wires"] if w["from"] == w["to"]]
    assert repetidos == [], repetidos
    assert nets["errors"] == []


def test_cada_capacitor_cuelga_de_la_placa_chica_con_un_puente_horizontal():
    # Lo que se ve en el montaje: los capacitores insertados en la placa
    # chica y un solo cable por net hasta la placa del 555, a la misma altura
    # (horizontal). Si el cruce eligiera otra fila, el puente saldria diagonal.
    fixture = _fixture()
    plan = plan_layout_v2(fixture)
    nets = plan_nets_v2(fixture, plan["placements"])

    por_net: dict[str, list] = {}
    for wire in nets["wires"]:
        toca_chica = "b2/" in str(wire["from"]) or "b2/" in str(wire["to"])
        if toca_chica and _es_hueco(wire["from"]) and _es_hueco(wire["to"]):
            por_net.setdefault(wire["net"], []).append(wire)

    assert {"GND", "r2.2", "t1.CTRL"} <= set(por_net), sorted(por_net)
    for nombre, cables in por_net.items():
        entre_placas = [
            w for w in cables
            if w["from"].startswith("b2/") != w["to"].startswith("b2/")
        ]
        assert len(entre_placas) == 1, (nombre, cables)
        cruce = entre_placas[0]
        assert cruce["from"][-1] == cruce["to"][-1], (nombre, cruce)


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


def test_el_builder_arma_la_llamada_con_tres_placas_y_la_placa_en_cada_pieza():
    call = fixture_to_model_call(_fixture(), code="// v2")

    assert [b["did"] for b in call["boards"]] == [116648, 116648, 111211]
    por_ref = {part["ref"]: part for part in call["parts"]}
    assert "uno" not in por_ref
    for ref in ("u1", "u2", "u3", "u4", "u5", "u6", "x1"):
        assert por_ref[ref]["at"][:3] != "b1/", por_ref[ref]
    for ref in ("ff1", "t1", "seg"):
        assert por_ref[ref]["at"].startswith("b1/"), por_ref[ref]
        assert por_ref[ref]["board"] == 1
    for ref in ("c1", "c2"):
        assert por_ref[ref]["at"].startswith("b2/"), por_ref[ref]
        assert por_ref[ref]["board"] == 2
        assert "free" not in por_ref[ref]


def test_el_sketch_v2_lee_high_y_cuenta_en_vivo():
    # Contratos distintos a proposito: la v1 ya esta entregada y verde, la v2
    # arregla lo que Eddie reporto ("no pasa de 0"). Ya no comparten esqueleto.
    v1 = contador_jk_sketch()
    v2 = contador_jk_v2_sketch()

    assert "digitalRead(SENSE[i]) == LOW" in v1
    assert "digitalRead(SENSE_G) == LOW" in v1
    assert "digitalRead(SENSE[i]) == HIGH" in v2
    assert "digitalRead(SENSE_G) == HIGH" in v2
    assert "catodo comun" in v2 and "anodo comun" not in v2

    # v1: al terminar las pruebas el loop no hace nada. El contador sigue
    # avanzando por hardware pero el sketch deja de leerlo y el display se
    # queda en el ultimo digito (0 tras la prueba de reset). Ese es el
    # sintoma que se reporto, y en la v1 se deja como estaba.
    assert v1.rstrip().endswith("void loop() {\n  delay(100);\n}")
    assert 'Serial.print("TEST:DIGITO=")' not in v1

    # v2: el display cuenta desde el primer segundo y el sketch no vuelve a
    # mover EN ni RESET. Las cuatro pruebas del taller quedan fuera: eran
    # justo el tramo donde la pantalla se quedaba en 0.
    assert 'Serial.print("TEST:DIGITO=")' in v2
    assert "if (demoCuenta < DEMO_MAX)" in v2
    assert '"TEST:DEMO=OK"' in v2
    for fuera in ("pruebaCiclo", "pruebaEn0",
                  "pruebaReanuda", "pruebaResetMedio"):
        assert fuera not in v2, fuera
        assert fuera in v1, fuera
    assert "correPruebas" not in v2

    # El setup suelta el contador una sola vez y no lo vuelve a tocar: si el
    # loop escribiera EN o RST, el conteo dependeria del sketch otra vez.
    setup_v2 = v2[v2.index("void setup() {"):v2.index("void loop() {")]
    assert setup_v2.count("digitalWrite(EN, HIGH);") == 1
    assert setup_v2.count("pulsaReset();") == 1
    assert "digitalWrite(EN, LOW);" in setup_v2  # solo la linea de reposo
    loop_v2 = v2[v2.index("void loop() {"):]
    for escritura in ("digitalWrite(EN", "digitalWrite(RST", "pulsaReset"):
        assert escritura not in loop_v2, escritura

    # La rama sin cambio duerme: sin ese delay el loop lee tres pines miles
    # de veces por segundo y el simulador se arrastra.
    assert "if (valor == anterior) {\n    delay(15);\n    return;\n  }" in v2
    # La v1 conserva sus pruebas en setup() y la vuelta larga.
    assert "for (int i = 1; i < 17; i++)" in v1


def test_el_oraculo_pide_los_ocho_digitos_en_orden():
    # El oraculo ya no demuestra las pruebas del taller (no las corre el
    # sketch de la v2): demuestra lo que Eddie pide ver, que el contador
    # avance. Cada marca es un digito, y el sketch imprime el valor que
    # acaba de leer, sin transformarlo, asi que pueden salir en orden.
    fixture = _fixture()
    marcas = fixture["oracle_serial"]
    sketch = contador_jk_v2_sketch()

    assert marcas == ["TEST:PERIODO="] + [
        f"TEST:DIGITO={digito}" for digito in range(8)
    ]
    assert 'Serial.print("TEST:DIGITO=");' in sketch
    assert "Serial.println(estable);" in sketch
    # Sin prefijo DISTINTO ni sufijo: la marca del oraculo es exactamente lo
    # que se imprime.
    assert sketch.count("TEST:DIGITO=") == 1
    assert sketch.count("Serial.println(estable);") == 1


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
