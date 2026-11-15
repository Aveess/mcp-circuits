"""Layout v2: integrados insertados en breadboards grandes y puentes cortos.

La v1 colocaba los chips **libres** fuera de la placa y tendia un cable por
net (estrella desde el Uno). La v2 los inserta y une las medias columnas: el
cable va de hueco a hueco, corto, y la placa hace el resto.

Lo que estos tests protegen es lo que no se ve en el dibujo:
- una media columna es un nodo: dos nets ahi son un corto silencioso;
- un DIP con las dos hileras en la misma mitad queda cortocircuitado;
- una net partida en dos trozos "funciona" en la foto y falla en la simulacion.

La fixture de aca es sintetica y minima (la real es el Task 6): dos chips,
un JK, el 555, el display con su resistencia y un capacitor libre.
"""

from __future__ import annotations

import pytest

from tinkercad_brain.boards import half
from tinkercad_brain.layout_v2 import (
    column_conflicts,
    footprint_for,
    plan_layout_v2,
    plan_nets_v2,
)

LARGE_X0 = 870
LARGE_X1 = 1570


def _fixture_v2() -> dict:
    return {
        "id": "prueba-v2",
        "layout": "v2",
        "boards": [
            {"kind": "large", "x": LARGE_X0, "y": 0},
            {"kind": "large", "x": LARGE_X1, "y": 0},
        ],
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "t1", "type": "timer-555"},
            {"ref": "ff1", "type": "flip-flop-jk"},
            {"ref": "u1", "type": "and-gate"},
            {"ref": "x1", "type": "xor-gate"},
            {"ref": "ra", "type": "resistor"},
            {"ref": "seg", "type": "seven-segment"},
            {"ref": "c1", "type": "capacitor"},
        ],
        "nets": [
            # Alimentacion: los dos chips, el 555 y los comunes del display.
            ["uno.5V", "t1.Vcc", "t1.Reset", "u1.Vcc", "x1.Vcc", "ff1.Vcc"],
            ["uno.GND1", "ff1.GND", "u1.GND", "x1.GND", "seg.com1", "seg.com2"],
            # Reloj del 555 al JK, y la lectura del periodo.
            ["t1.OUT", "ff1.1CP", "uno.D2"],
            # Enable del JK y reset activo en bajo (u1 hace de inversor).
            ["uno.D8", "ff1.1J", "ff1.1K"],
            ["u1.1Y", "ff1.1R"],
            # Salida del JK al decodificador.
            ["ff1.1Q", "x1.1A", "uno.D3"],
            # Segmento: compuerta -> resistencia -> display, y la lectura.
            ["x1.1Y", "ra.1", "uno.A0"],
            ["ra.2", "seg.a"],
            # Capacitor libre en el control del 555.
            ["t1.CTRL", "c1.1"],
        ],
    }


def _is_hole(ep: str) -> bool:
    return "." not in ep


def _board(ep: str) -> int:
    return 1 if ep.startswith("b1/") else 0


def _col(ep: str) -> int:
    return int(ep.split("/", 1)[1][:-1] if ep.startswith("b") else ep[:-1])


def test_los_dip_se_insertan_en_mitades_distintas():
    fixture = _fixture_v2()
    plan = plan_layout_v2(fixture)

    for ref, p in plan["placements"].items():
        if "at" not in p:
            continue
        ctype = next(c["type"] for c in fixture["components"] if c["ref"] == ref)
        huella = footprint_for(ctype)
        filas = {row for _, row in huella.values()}
        assert len({half(r) for r in filas}) == 2, (ref, p)
        # El ancla tiene que estar en la fila que declara la huella.
        assert p["at"].endswith(huella[p["pin"]][1]), (ref, p)


def test_el_display_se_inserta_con_el_angulo_medido():
    # Medido en jWUw1co8IZH: a 0 grados el puente dice "no angle fits all pins
    # in holes" y la fidelidad cae a 33/41 nets. El digito se lee derecho
    # porque el generador cablea cada segmento por su pata opuesta.
    plan = plan_layout_v2(_fixture_v2())

    assert plan["placements"]["seg"]["angle"] == 180


def test_ninguna_net_comparte_media_columna_con_otro():
    fixture = _fixture_v2()
    nets = plan_nets_v2(fixture, plan_layout_v2(fixture)["placements"])

    assert nets["errors"] == []
    assert column_conflicts(nets) == []


def test_dos_patas_nunca_cuelgan_del_mismo_hueco():
    # Un hueco con dos cables de pata se dibuja como un cable solo: la foto no
    # lo delata y la simulacion pierde una conexion. Paso de verdad en la
    # primera corrida de la v2: los dos capacitores libres colgaban los dos de
    # `b1/45i`. Un cable de bus si puede terminar donde entra un cable de pata
    # (asi se ve un tap de riel); lo que no se admite es dos PATAS en el mismo
    # hueco. Con la fixture sintetica de arriba (un solo capacitor libre) el
    # defecto no aparece: hace falta la real.
    from tinkercad_brain.contador_jk_v2 import contador_jk_v2_fixture

    fixture = contador_jk_v2_fixture()
    nets = plan_nets_v2(fixture, plan_layout_v2(fixture)["placements"])

    patas_por_hueco: dict[str, set] = {}
    for wire in nets["wires"]:
        frm, to = wire["from"], wire["to"]
        if _is_hole(frm) and not _is_hole(to):
            patas_por_hueco.setdefault(frm, set()).add(to)
        elif _is_hole(to) and not _is_hole(frm):
            patas_por_hueco.setdefault(to, set()).add(frm)

    repetidos = {hueco: sorted(patas) for hueco, patas in patas_por_hueco.items()
                 if len(patas) > 1}
    assert repetidos == {}, repetidos

    # Y ninguna pata de placa comparte media columna con otra: la placa las
    # uniria sin que se vea un cable.
    medias = {(b, col, half(row)) for (b, col, row) in nets["leg_holes"].values()}
    assert len(medias) == len(nets["leg_holes"]), (
        "dos patas comparten media columna: la placa las une sin querer"
    )


def test_los_puentes_son_cortos_y_no_saltan_de_placa():
    fixture = _fixture_v2()
    nets = plan_nets_v2(fixture, plan_layout_v2(fixture)["placements"])

    puentes = [
        w for w in nets["wires"] if _is_hole(w["from"]) and _is_hole(w["to"])
    ]
    assert puentes, "sin puentes hueco-hueco no hay nada que verificar"
    for w in puentes:
        if _board(w["from"]) == _board(w["to"]):
            # Dentro de la placa el puente es corto: si no, la net esta
            # partida y hay un cable largo haciendo de placa.
            assert abs(_col(w["from"]) - _col(w["to"])) <= 12, w


def test_cada_net_tiene_un_solo_color_y_alimentacion_en_rojo_y_negro():
    fixture = _fixture_v2()
    nets = plan_nets_v2(fixture, plan_layout_v2(fixture)["placements"])

    por_net: dict[str, set] = {}
    for w in nets["wires"]:
        por_net.setdefault(w["net"], set()).add(w["color"])

    assert all(len(v) == 1 for v in por_net.values()), por_net
    assert por_net["5V"] == {"red"}
    assert por_net["GND"] == {"black"}
    senales = {next(iter(v)) for k, v in por_net.items() if k not in ("5V", "GND")}
    assert "red" not in senales and "black" not in senales
    assert len(senales) >= 4, senales


def test_cada_net_queda_conectada_punta_a_punta():
    fixture = _fixture_v2()
    placements = plan_layout_v2(fixture)["placements"]
    nets = plan_nets_v2(fixture, placements)

    # Nodo = media columna (o pin libre). La placa une las cinco filas de una
    # mitad; cada cable une los nodos de sus dos extremos.
    padre: dict = {}

    def find(x):
        padre.setdefault(x, x)
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            padre[rb] = ra

    def nodo(ep: str):
        # El nodo es la media columna: una pata y un hueco de esa misma media
        # columna son el mismo punto. Si el test comparara cadenas, un cable
        # que entra por `7d` y una pata en `7f` pareceran desconectados aunque
        # la placa los una (que es justo lo que hay que probar).
        if ep in nets["leg_holes"]:
            board, col, row = nets["leg_holes"][ep]
            return (board, col, half(row))
        if _is_hole(ep):
            return (_board(ep), _col(ep), half(ep[-1]))
        return ep

    for w in nets["wires"]:
        union(nodo(w["from"]), nodo(w["to"]))

    for net in fixture["nets"]:
        raices = {find(nodo(ep)) for ep in net}
        assert len(raices) == 1, net


def test_cada_net_que_toca_las_dos_placas_lleva_un_puente_entre_ellas():
    # La alimentacion y las senales que cruzan de placa necesitan un puente
    # explicito: sin el, la segunda placa queda sin esa senal y el dibujo no
    # lo muestra. Y el puente va en la misma fila en las dos placas, si no
    # sale la diagonal larga que el puente no rutea.
    fixture = _fixture_v2()
    nets = plan_nets_v2(fixture, plan_layout_v2(fixture)["placements"])

    puentes = [
        w for w in nets["wires"] if _is_hole(w["from"]) and _is_hole(w["to"])
    ]
    cruces = [w for w in puentes if _board(w["from"]) != _board(w["to"])]
    assert cruces, "5V y GND tienen patas en las dos placas"

    por_net: dict[str, list] = {}
    for w in cruces:
        por_net.setdefault(w["net"], []).append(w)

    for nombre, lista in por_net.items():
        assert len(lista) == 1, (nombre, lista)
        for w in lista:
            assert w["from"][-1] == w["to"][-1], w
    assert {"5V", "GND"} <= set(por_net), por_net.keys()


def test_la_huella_del_tipo_desconocido_se_reporta_sin_colocar():
    fixture = _fixture_v2()
    fixture["components"].append({"ref": "led1", "type": "led"})
    fixture["nets"].append(["uno.D13", "led1.anode"])

    plan = plan_layout_v2(fixture)

    assert plan["unplaced"] == ["led1"]
    assert "led1" not in plan["placements"]
    assert any("led" in e for e in plan["errors"]), plan["errors"]


def test_el_builder_despacha_v2_y_arma_la_llamada_del_puente():
    # La fixture v2 no pasa por `plan_layout` (la v1): sus huecos ya vienen
    # resueltos y las placas viajan en la llamada. Si el despacho se pierde,
    # el build falla por un type sin layout o construye la estrella de la v1
    # en la placa equivocada.
    from tinkercad_brain.builder import fixture_to_model_call

    call = fixture_to_model_call(_fixture_v2(), code="// hola")

    assert call["code"] == "// hola"
    assert [b["did"] for b in call["boards"]] == [116648, 116648]
    assert [b["x"] for b in call["boards"]] == [LARGE_X0, LARGE_X1]

    por_ref = {p["ref"]: p for p in call["parts"]}
    assert "uno" not in por_ref, "el Uno lo crea el puente"
    assert por_ref["c1"]["free"] == {"x": LARGE_X1 + 380, "y": -250}
    assert por_ref["seg"]["angle"] == 180
    # Una pieza de la segunda placa lleva su hueco prefijado: sin `b1/` el
    # puente la clava en la primera placa y el cableado queda partido.
    assert por_ref["t1"]["at"].startswith("b1/"), por_ref["t1"]
    assert "b1/" not in por_ref["u1"]["at"], por_ref["u1"]

    colores = {w["color"] for w in call["wires"]}
    assert {"red", "black"} <= colores, colores
    # Un color por net: si el rojo apareciera en una senal, el bus de 5V y la
    # senal se verian iguales en el dibujo y el error no saltaria a la vista.
    por_net = {}
    for wire in call["wires"]:
        assert set(wire) == {"from", "to", "color"}, wire
        por_net.setdefault(wire["color"], 0)
        por_net[wire["color"]] += 1
    assert len(por_net) >= 5, por_net


def test_una_media_columna_con_dos_nets_no_se_construye():
    # Dos nets en la misma media columna es un corto que la foto no delata:
    # el build tiene que negarse, no elegir una y seguir.
    from tinkercad_brain.builder import BuildError, fixture_to_model_call
    from tinkercad_brain import builder

    original = builder.plan_nets_v2

    def con_conflicto(fixture_, placements):
        nets = original(fixture_, placements)
        clave = next(iter(nets["claims"]))
        nets["claims"][clave] = {"otro-net", "y-otro"}
        return nets

    builder.plan_nets_v2 = con_conflicto
    try:
        with pytest.raises(BuildError, match="medias columnas con dos nets"):
            fixture_to_model_call(_fixture_v2())
    finally:
        builder.plan_nets_v2 = original
