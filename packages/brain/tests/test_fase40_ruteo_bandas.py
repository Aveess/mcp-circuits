"""Fase 40: el cable ruteado no pasa sobre el cuerpo de la placa.

Antes se miraba el screenshot. Los carriles arrancaban en ±115 y el cuerpo
de la protoboard llega a ±110: 5 unidades de aire, que en pantalla es un
cable pegado al borde. El puente ahora devuelve la polilínea de cada cable
ruteado y estas pruebas convierten la regla 3 de ``organizacion-cables.md``
en algo medible.
"""

from tinkercad_brain.builder import (
    _BOARD_HALF_X,
    _BOARD_HALF_Y,
    _ROUTE_MIN_AIR,
    diagonal_segments,
    route_band_violations,
)

UNO = {"x": 870, "y": 0}


def _route(wire, points, routed=True):
    return {"wire": wire, "routed": routed, "reason": "ok", "points": points}


def test_un_carril_pegado_al_borde_es_violacion():
    """El valor viejo (±115) no pisaba la placa, pero no dejaba aire."""
    assert _BOARD_HALF_Y < 115 < _BOARD_HALF_Y + _ROUTE_MIN_AIR
    routes = [_route("uno.D4 -> 5e", [[200, 0], [200, 115], [765, 115], [765, 15]])]
    violations = route_band_violations(routes, [UNO])
    assert violations == [{"wire": "uno.D4 -> 5e", "y": 115.0, "board": UNO}]


def test_el_carril_nuevo_deja_aire_y_no_es_violacion():
    routes = [_route("uno.D4 -> 5e", [[200, 0], [200, 130], [765, 130], [765, 15]])]
    assert route_band_violations(routes, [UNO]) == []


def test_un_tramo_vertical_puede_cruzar_la_placa():
    """Bajar del carril al hueco cruza la placa: así se entra a la placa."""
    routes = [_route("uno.D4 -> 5e", [[200, 0], [200, 130], [765, 130], [765, 15]])]
    assert route_band_violations(routes, [UNO]) == []


def test_un_tramo_horizontal_fuera_del_ancho_no_cruza_nada():
    """A la derecha de la placa no hay cuerpo: el carril bajo es legal."""
    right = UNO["x"] + _BOARD_HALF_X + 10
    routes = [_route("seg.a -> 7e", [[right, 0], [right, 115], [right + 200, 115]])]
    assert route_band_violations(routes, [UNO]) == []


def test_la_segunda_placa_tambien_cuenta():
    boards = [UNO, {"x": 1270, "y": 0}]
    # Arranca en 1050, a la derecha de la placa 1 (710..1030): solo cruza la 2.
    routes = [_route("uno.D5 -> b1/1d", [[1050, 130], [1135, 130], [1135, 25]])]
    assert route_band_violations(routes, boards) == []

    pegado = [_route("uno.D5 -> b1/1d", [[1050, -115], [1135, -115], [1135, 25]])]
    assert route_band_violations(pegado, boards) == [
        {"wire": "uno.D5 -> b1/1d", "y": -115.0, "board": {"x": 1270.0, "y": 0.0}}
    ]


def test_la_parte_libre_corre_por_encima_de_su_cuerpo():
    """El display vive en y=-230: su corrida va 30 más arriba (-260)."""
    routes = [_route("seg.a -> 5e", [[1260, -230], [1260, -260], [765, -260], [765, 15]])]
    assert route_band_violations(routes, [UNO]) == []


def test_un_cable_sin_polilinea_o_sin_rutear_no_rompe():
    routes = [
        {"wire": "a -> b", "routed": False, "points": [[0, 0], [0, 0]]},
        {"wire": "c -> d", "routed": True},
        {"wire": "e -> f", "routed": True, "points": []},
        {"wire": "g -> h", "routed": True, "points": [["x", "y"], [0, 0]]},
        "basura",
    ]
    assert route_band_violations(routes, [UNO]) == []


def test_sin_placas_usa_la_de_siempre():
    routes = [_route("uno.D4 -> 5e", [[200, 0], [200, 115], [765, 115]])]
    assert route_band_violations(routes) == [
        {"wire": "uno.D4 -> 5e", "y": 115.0, "board": {"x": 870.0, "y": 0.0}}
    ]


# --------------------------------------------------------------------------
# Fase 51: la medida es el dibujo, no la intencion
# --------------------------------------------------------------------------


def _route_actual(wire, points, actual, routed=True):
    """Cable con la polilinea pedida y la que el editor guardo."""
    route = _route(wire, points, routed=routed)
    route["actual"] = actual
    return route


def test_el_lint_mide_lo_que_guardo_el_editor_y_no_lo_que_pidio():
    """`points` ortogonal + `actual` diagonal = cable torcido de verdad.

    Medido el 2026-11-16 en `3akmw1EaG0p`: el build pedia
    `[1545,55] -> [1545,-178] -> [815,-178] -> [815,-305]` y el editor
    guardaba `[1545,55] -> [1654.2577,-99.9588] -> ...`, con la primera
    pierna en diagonal. El lint decia "0 diagonales" porque miraba `points`.
    """
    pedido = [[1545, 55], [1545, -178], [815, -178], [815, -305]]
    guardado = [[1545, 55], [1654.2577, -99.9588], [924.2577, -99.9588], [815, -305]]
    routes = [_route_actual("b1/28a -> b2/10a", pedido, guardado)]
    diagonales = diagonal_segments(routes)
    # Las dos piernas de entrada/salida quedaron torcidas, no solo la primera.
    assert len(diagonales) == 2
    assert {d["wire"] for d in diagonales} == {"b1/28a -> b2/10a"}
    assert abs(diagonales[0]["dx"] - 109.2577) < 1e-3
    assert abs(diagonales[0]["dy"] - 154.9588) < 1e-3
    assert abs(diagonales[1]["dy"] - 205.0412) < 1e-3


def test_el_lint_no_inventa_diagonales_cuando_el_dibujo_es_ortogonal():
    pedido = [[1545, 55], [1545, -178], [815, -178], [815, -305]]
    routes = [_route_actual("b1/28a -> b2/10a", pedido, [list(p) for p in pedido])]
    assert diagonal_segments(routes) == []


def test_el_tramo_sobre_placa_tambien_se_mide_en_el_dibujo():
    """El carril pedido va a -178 (aire), pero el guardado cae en -100."""
    pedido = [[1545, 55], [1545, -178], [815, -178], [815, -305]]
    guardado = [[1545, 55], [1654.2577, -99.9588], [924.2577, -99.9588], [815, -305]]
    routes = [_route_actual("b1/28a -> b2/10a", pedido, guardado)]
    violations = route_band_violations(routes, [UNO])
    assert violations == [{"wire": "b1/28a -> b2/10a", "y": -99.9588, "board": UNO}]
