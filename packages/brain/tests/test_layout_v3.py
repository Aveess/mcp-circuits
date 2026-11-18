"""Layout v3: la alimentacion entra por la fuente y se reparte por los rieles.

Eddie fijo la regla y no es estetica: es como se arma una placa de verdad.

1. la fuente es la pieza **Power Supply**, no el 5V del Uno;
2. rojo de su positivo al riel positivo, negro de su tierra al negativo;
3. otros dos cables al borde opuesto para alimentar la placa entera;
4. cada pata toca el riel de su propia mitad, en su misma columna;
5. una placa extra se alimenta de la placa ya alimentada, no de la fuente.

Lo que estos tests protegen es lo que no se ve en la foto:

- **el color miente facil**: un cable rojo de senal se ve perfecto y no dice
  nada de la alimentacion, asi que los colores son un contrato, no un adorno;
- **la placa grande funde su par de abajo en un nodo** (las dos filas se
  llaman ``X``): poner positivo y tierra ahi es un corto que el simulador no
  reporta como error de armado;
- **una pata lejos de su riel necesita la fila de bus**: sin ella la net queda
  partida en dos y el circuito "anda" hasta que deja de andar;
- **la segunda placa no se cuelga de la fuente**: si se cuelga, el dia que la
  fuente tenga un solo par de bornes el circuito no se puede armar.

La fixture es la real (``contador_jk_v3_fixture``) porque el reparto depende de
donde caen las patas: con una fixture de juguete se prueba el algoritmo, no el
circuito.
"""

from __future__ import annotations

import re

import pytest

from tinkercad_brain.boards import board, half, rail_holes
from tinkercad_brain.contador_jk_v2 import contador_jk_v2_fixture
from tinkercad_brain.contador_jk_v3 import contador_jk_v3_fixture
from tinkercad_brain.layout import LayoutError
from tinkercad_brain.layout_v2 import _net_name, column_conflicts
from tinkercad_brain.layout_v3 import plan_layout_v3, plan_nets_v3

ROJO, NEGRO = "red", "black"
COLORES = {"5V": ROJO, "GND": NEGRO}


def _fixture() -> dict:
    return contador_jk_v3_fixture()


def _plan():
    fixture = _fixture()
    layout = plan_layout_v3(fixture)
    return fixture, layout, plan_nets_v3(fixture, layout["placements"])


def _power(nets: dict, name: str) -> list[dict]:
    return [wire for wire in nets["wires"] if wire["net"] == name]


def _parse(endpoint: str):
    """``"b1/T+4"`` -> ``(1, "T+4")``; ``"7e"`` -> ``(0, "7e")``."""
    if endpoint.startswith("b") and "/" in endpoint:
        board_index, rest = endpoint[1:].split("/", 1)
        return int(board_index), rest
    return 0, endpoint


def _is_rail(node: str) -> bool:
    return node[:2] in ("T+", "T-", "B+", "B-") and node[2:].isdigit()


def _rail_side(layout: dict, board_index: int, node: str) -> str:
    """Lado fisico de un riel: el signo de ``y`` en la tabla de la placa."""
    y = board(layout["boards"][board_index]["kind"]).rails[node[:2]]
    return "top" if y > 0 else "bottom"


def _home_sides(layout: dict, nets: dict) -> dict[str, str]:
    """Lado de cada net, leido de donde entra la fuente en la placa 0."""
    sides = {}
    for name, pin in (("5V", "Vcc"), ("GND", "GND")):
        entry = next(w for w in _power(nets, name) if w["from"] == f"ps1.{pin}")
        board_index, node = _parse(entry["to"])
        sides[name] = _rail_side(layout, board_index, node)
    return sides


# --------------------------------------------------------------------------
# La fuente
# --------------------------------------------------------------------------


def test_la_fuente_es_una_pieza_libre_a_la_izquierda_de_la_primera_placa():
    _, layout, _ = _plan()

    assert layout["source"] == "ps1"
    placement = layout["placements"]["ps1"]
    assert "at" not in placement, "la fuente no va insertada: no tiene patas de placa"
    assert placement["free"]["x"] < layout["boards"][0]["x"]
    assert placement["free"]["y"] == 0


def test_sin_fuente_o_con_dos_el_layout_no_se_inventa_una():
    fixture = _fixture()
    sin_fuente = {
        **fixture,
        "components": [c for c in fixture["components"] if c["ref"] != "ps1"],
    }
    with pytest.raises(LayoutError):
        plan_layout_v3(sin_fuente)

    dos = {
        **fixture,
        "components": fixture["components"] + [{"ref": "ps2", "type": "power-supply"}],
    }
    with pytest.raises(LayoutError):
        plan_layout_v3(dos)


def test_el_5v_del_uno_ya_no_alimenta_nada():
    _, _, nets = _plan()

    extremos = [end for wire in _power(nets, "5V") for end in (wire["from"], wire["to"])]
    assert "uno.5V" not in extremos
    assert "ps1.Vcc" in extremos


def test_la_tierra_del_uno_sigue_en_la_tierra():
    """Es la referencia de las lecturas analogicas, no un consumidor."""
    _, _, nets = _plan()

    tierra = [
        wire for wire in _power(nets, "GND")
        if "uno.GND1" in (wire["from"], wire["to"])
    ]
    assert len(tierra) == 1
    otro = tierra[0]["to"] if tierra[0]["from"] == "uno.GND1" else tierra[0]["from"]
    board_index, node = _parse(otro)
    assert board_index == 0 and _is_rail(node)


# --------------------------------------------------------------------------
# Los colores
# --------------------------------------------------------------------------


def test_rojo_es_positivo_y_negro_es_tierra_sin_excepciones():
    _, _, nets = _plan()

    for wire in nets["wires"]:
        if wire["net"] in COLORES:
            assert wire["color"] == COLORES[wire["net"]], wire
        else:
            assert wire["color"] not in (ROJO, NEGRO), (
                f"cable de senal {wire['net']} pintado de {wire['color']}: "
                "el color es la unica forma de leer la alimentacion"
            )


# --------------------------------------------------------------------------
# El reparto por rieles
# --------------------------------------------------------------------------


def test_la_fuente_entra_a_los_dos_rieles_de_la_placa_cero():
    _, _, nets = _plan()

    for name, pin in (("5V", "Vcc"), ("GND", "GND")):
        cables = [w for w in _power(nets, name) if w["from"] == f"ps1.{pin}"]
        assert len(cables) == 1, f"{name}: la fuente entra una sola vez"
        assert cables[0]["color"] == COLORES[name]
        board_index, node = _parse(cables[0]["to"])
        assert board_index == 0 and _is_rail(node)
        assert node.endswith("1"), "entra por el borde de la placa, no por el medio"


def test_positivo_y_tierra_no_comparten_el_par_de_abajo_de_la_placa_grande():
    """Las dos filas de abajo se llaman X y son un nodo: ahi un solo color."""
    _, layout, nets = _plan()

    for index, table in enumerate(layout["boards"]):
        if table["kind"] != "large":
            continue
        nets_abajo = set()
        for name in COLORES:
            for wire in _power(nets, name):
                for endpoint in (wire["from"], wire["to"]):
                    board_index, node = _parse(endpoint)
                    if board_index != index or not _is_rail(node):
                        continue
                    if _rail_side(layout, index, node) == "bottom":
                        nets_abajo.add(name)
        assert len(nets_abajo) <= 1, (
            "la placa grande funde sus dos filas de abajo: positivo y tierra "
            "ahi es un corto que el simulador no reporta"
        )


def test_cada_pata_del_lado_de_su_riel_baja_con_un_cable_en_su_columna():
    fixture, layout, nets = _plan()
    leg_holes = nets["leg_holes"]
    sides = _home_sides(layout, nets)

    for name in COLORES:
        pares = {
            frozenset((w["from"], w["to"])) for w in _power(nets, name)
        }
        for net in fixture["nets"]:
            if _net_name(net) != name:
                continue
            for endpoint in net:
                hole = leg_holes.get(endpoint)
                if hole is None:
                    continue
                board_index, col, row = hole
                if half(row) != sides[name]:
                    continue
                kind = layout["boards"][board_index]["kind"]
                # Las patas en columna sin hueco de riel bajan por la fila de
                # bus: no llevan tap vertical (ver el test de conectividad).
                if col not in rail_holes(kind):
                    continue
                rail = _home_rail(layout, board_index, sides[name])
                prefix = f"b{board_index}/" if board_index else ""
                esperado = frozenset((f"{prefix}{col}{row}", f"{prefix}{rail}{col}"))
                assert esperado in pares, (
                    f"{name}: la pata {endpoint} ({col}{row}) no toca el riel "
                    f"{rail} de su propia mitad con un cable vertical"
                )


def test_el_borde_opuesto_lleva_el_mismo_color_a_la_otra_mitad():
    _, layout, nets = _plan()

    for name in COLORES:
        saltos = [
            w for w in _power(nets, name)
            if _is_rail(_parse(w["from"])[1]) and _is_rail(_parse(w["to"])[1])
            and _parse(w["from"])[0] == _parse(w["to"])[0]
        ]
        assert saltos, f"{name}: falta el cable al borde opuesto"
        for wire in saltos:
            board_index = _parse(wire["from"])[0]
            desde = _parse(wire["from"])[1]
            hasta = _parse(wire["to"])[1]
            assert desde[2:] == hasta[2:], "el cable del borde va en la misma columna"
            assert (
                _rail_side(layout, board_index, desde)
                != _rail_side(layout, board_index, hasta)
            ), "el cable del borde une las dos mitades de la placa"


def test_la_placa_chica_recibe_los_dos_colores_por_el_borde_derecho():
    """Tiene cuatro rieles distintos: ahi la regla se cumple entera."""
    _, layout, nets = _plan()
    indice = next(i for i, b in enumerate(layout["boards"]) if b["kind"] == "small")

    for name in COLORES:
        saltos = [
            w for w in _power(nets, name)
            if all(
                _parse(endpoint)[0] == indice and _is_rail(_parse(endpoint)[1])
                for endpoint in (w["from"], w["to"])
            )
        ]
        assert len(saltos) == 1, f"{name}: la placa chica necesita su cable de borde"
        columna = int(_parse(saltos[0]["from"])[1][2:])
        assert columna >= 28, (
            "el cable del borde va en el extremo del riel, no por el medio"
        )


def test_ni_dos_nets_en_una_media_columna_ni_patas_sin_hueco():
    fixture, _, nets = _plan()

    assert nets["errors"] == []
    assert column_conflicts(nets) == []
    for net in fixture["nets"]:
        for endpoint in net:
            if endpoint.startswith("ps1.") or endpoint.startswith("uno."):
                continue
            assert endpoint in nets["leg_holes"], f"{endpoint} quedo sin hueco"


def _cell_owner(fixture: dict, leg_holes: dict) -> dict:
    """{(placa, columna, mitad): net o pata} de **cada** pata colocada.

    Incluye las patas que no estan en ninguna net (las compuertas sobrantes
    del decodificador): tambien ocupan su media columna y un cable ajeno ahi
    es un corto.
    """
    name_of = {}
    for net in fixture["nets"]:
        name = _net_name(net)
        for endpoint in net:
            name_of[endpoint] = name
    owner = {}
    for endpoint, hole in leg_holes.items():
        board_index, col, row = hole
        owner[(board_index, col, half(row))] = name_of.get(endpoint, endpoint)
    return owner


def _cell_of(endpoint: str):
    """Media columna de un hueco, o ``None`` si el extremo es un riel o un pin."""
    board_index, rest = _parse(endpoint)
    if _is_rail(rest):
        return None
    match = re.fullmatch(r"(\d+)([a-j])", rest)
    if match is None:
        return None
    return (board_index, int(match.group(1)), half(match.group(2)))


@pytest.mark.parametrize("name", sorted(COLORES))
def test_ningun_cable_de_alimentacion_toca_la_media_columna_de_otra_net(name):
    """Cada chip tiene una pata por media columna: tocar el hueco es tocar la pata.

    La placa une los cinco huecos de la mitad, asi que un cable de 5V que baje
    en la media columna de una salida le mete 5V a la salida. El simulador no
    lo reporta como error de armado: quema el integrado y sigue. Por eso se
    verifica en el plan, antes de construir.
    """
    fixture, _, nets = _plan()
    owner = _cell_owner(fixture, nets["leg_holes"])

    for wire in _power(nets, name):
        for key in ("from", "to"):
            cell = _cell_of(wire[key])
            if cell is None:
                continue
            duena = owner.get(cell)
            assert duena in (None, name), (
                f"{name}: el cable a {wire[key]} cae en la media columna de "
                f"{duena} (cortocircuito)"
            )


def test_el_5v_no_baja_por_la_media_columna_de_una_salida_del_xor():
    """Regresion del build del 2026-11-15: el bus del 5V bajo por x1.4Y.

    En ``kSakfQXHtmU`` el 5V tenia dos patas en columnas sin hueco de riel (37
    y 55) y el bus eligio bajar en la 58, que es la media columna de la salida
    ``4Y`` del XOR. Quedo 5V contra una salida en bajo: el 74HC86 revento en
    la simulacion y el display seguia contando, asi que el sintoma no se veia
    en la secuencia. Ahora esas patas van con un cable directo al hueco de
    riel mas cercano.
    """
    fixture, _, nets = _plan()
    owner = _cell_owner(fixture, nets["leg_holes"])
    celda_4y = _cell_of(f"{nets['leg_holes']['x1.4Y'][1]}f")
    assert owner[celda_4y] == "x1.4Y"

    for wire in _power(nets, "5V"):
        for key in ("from", "to"):
            assert _cell_of(wire[key]) != celda_4y, (
                f"el 5V vuelve a tocar la salida 4Y por {wire[key]}"
            )


# --------------------------------------------------------------------------
# Los huecos de riel que existen de verdad
# --------------------------------------------------------------------------

# Como el guardado de Tinkercad nombra cada fila de riel. Dos filas con la
# misma letra son **el mismo nodo**: en la placa grande las dos de abajo se
# llaman "X" (medido el 2026-11-15 sobre el diseno kSakfQXHtmU).
_RAIL_LETTER = {
    "large": {85: "Y", 95: "Z", -85: "X", -95: "X"},
    "small": {95: "w", 85: "x", -85: "y", -95: "z"},
}


def _node(layout: dict, endpoint: str):
    """Nodo fisico de un extremo: media columna, fila de riel o pin."""
    index, rest = _parse(endpoint)
    if _is_rail(rest):
        kind = layout["boards"][index]["kind"]
        y = board(kind).rails[rest[:2]]
        return ("rail", index, _RAIL_LETTER[kind][y])
    match = re.fullmatch(r"(\d+)([a-j])", rest)
    if match:
        return ("half", index, int(match.group(1)), half(match.group(2)))
    return ("pin", endpoint)


def test_la_placa_grande_solo_tiene_riel_en_columnas_salteadas():
    """50 huecos con salto cada seis: pedir 24 o 43 no resuelve en el puente.

    Medido el 2026-11-15 con una sonda sobre el editor: las cuatro filas de
    riel de la grande tienen hueco en 50 de las 60 primeras columnas, y faltan
    justo en 6, 12, 18, 24, 30, 31, 37, 43, 49, 55 (mas 61 y 62). Los cinco
    cables que no resolvieron en el primer build de la v3 caian ahi.
    """
    grande = rail_holes("large")
    assert len(grande) == 50
    assert [c for c in range(1, 63) if c not in grande] == [
        6, 12, 18, 24, 30, 31, 37, 43, 49, 55, 61, 62,
    ]
    # La chica no salta ninguna.
    assert tuple(rail_holes("small")) == tuple(range(1, 31))


def test_ningun_cable_de_riel_cae_en_una_columna_sin_hueco():
    _, layout, nets = _plan()

    malos = []
    for wire in nets["wires"]:
        for endpoint in (wire["from"], wire["to"]):
            index, rest = _parse(endpoint)
            if not _is_rail(rest):
                continue
            kind = layout["boards"][index]["kind"]
            if int(rest[2:]) not in rail_holes(kind):
                malos.append((wire["net"], endpoint))
    assert malos == [], f"cables a huecos de riel inexistentes: {malos}"


def test_cada_pata_de_alimentacion_llega_de_verdad_a_la_fuente():
    """Conectividad real: media columna y letra de riel colapsadas.

    Un cable que "existe" en la lista puede terminar en un nodo que no toca
    nada. Aqui se unen los cables y se pregunta, pata por pata, si su nodo
    fisico esta en la misma componente que el borne de la fuente.
    """
    fixture, layout, nets = _plan()

    padre: dict = {}

    def find(a):
        padre.setdefault(a, a)
        while padre[a] != a:
            padre[a] = padre[padre[a]]
            a = padre[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            padre[ra] = rb

    # Un nodo con dos duenos es un corto: el simulador no siempre lo reporta.
    dueno: dict = {}
    for wire in nets["wires"]:
        for endpoint in (wire["from"], wire["to"]):
            node = _node(layout, endpoint)
            previo = dueno.setdefault(node, wire["net"])
            assert previo == wire["net"], (
                f"el nodo {node} lo comparten {previo} y {wire['net']}"
            )
        union(_node(layout, wire["from"]), _node(layout, wire["to"]))

    for name, source in (("5V", "ps1.Vcc"), ("GND", "ps1.GND")):
        root = find(_node(layout, source))
        for net in fixture["nets"]:
            if _net_name(net) != name:
                continue
            for endpoint in net:
                if endpoint == source:
                    continue
                hole = nets["leg_holes"].get(endpoint)
                if hole is None:
                    # Pines que no van a la placa: el Uno y la propia fuente.
                    node = _node(layout, endpoint)
                else:
                    node = ("half", hole[0], hole[1], half(hole[2]))
                assert find(node) == root, (
                    f"{name}: {endpoint} -> {node} no esta conectado al borne "
                    f"{source}; la net quedaria partida"
                )


# --------------------------------------------------------------------------
# Los cables entre placas
# --------------------------------------------------------------------------


def test_la_segunda_placa_se_alimenta_de_la_primera_no_de_la_fuente():
    _, layout, nets = _plan()

    for name in COLORES:
        desde_fuente = [
            w for w in _power(nets, name)
            if w["from"].startswith("ps1.") or w["to"].startswith("ps1.")
        ]
        assert len(desde_fuente) == 1, "la fuente alimenta una sola placa"

        enlaces = [
            w for w in _power(nets, name)
            if _parse(w["from"])[0] != _parse(w["to"])[0]
            and _is_rail(_parse(w["from"])[1]) and _is_rail(_parse(w["to"])[1])
        ]
        assert len(enlaces) == len(layout["boards"]) - 1, (
            f"{name}: falta el cable de la placa anterior a la siguiente"
        )
        for wire in enlaces:
            anterior = _parse(wire["from"])[0]
            siguiente = _parse(wire["to"])[0]
            assert siguiente == anterior + 1
            assert wire["color"] == COLORES[name]


# --------------------------------------------------------------------------
# La v1 y la v2 quedan intactas
# --------------------------------------------------------------------------


def test_la_v3_es_la_v2_con_la_alimentacion_cambiada():
    v2 = contador_jk_v2_fixture()
    v3 = _fixture()

    assert v3["layout"] == "v3"
    assert [c["ref"] for c in v3["components"]] == ["ps1"] + [
        c["ref"] for c in v2["components"]
    ]

    v2_nets = [list(net) for net in v2["nets"]]
    v3_nets = [list(net) for net in v3["nets"]]
    assert len(v2_nets) == len(v3_nets)
    for antes, despues in zip(v2_nets, v3_nets):
        esperado = ["ps1.Vcc" if e == "uno.5V" else e for e in antes]
        if "uno.GND1" in antes:
            esperado = esperado + ["ps1.GND"]
        assert despues == esperado


def test_la_v2_sigue_siendo_la_v2():
    v2 = contador_jk_v2_fixture()

    assert v2.get("layout") == "v2"
    assert [c["ref"] for c in v2["components"]][:1] == ["uno"]
    assert any("uno.5V" in net for net in v2["nets"])


def _home_rail(layout: dict, board_index: int, side: str) -> str:
    """Riel interior de ese lado: el que esta pegado a las filas."""
    rails = board(layout["boards"][board_index]["kind"]).rails
    candidatos = [
        name for name, y in rails.items() if (y > 0) == (side == "top")
    ]
    return min(candidatos, key=lambda name: abs(rails[name]))
