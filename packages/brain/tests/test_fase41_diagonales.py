"""Fase 41: ningun cable de una parte libre puede quedar en diagonal.

El puente solo ruteaba ``uno<->placa`` y ``libre<->placa``. Un cable entre
dos partes libres (555 -> compuerta, compuerta -> compuerta) se quedaba como
la recta que dibuja Tinkercad, y con los pines en filas distintas eso es una
diagonal larga: por eso el circuito 28 "se veia un poco torcido" aunque
funcionara.

Estas pruebas miden la polilinea que el puente ya devuelve (``route_debug``)
y separan dos cosas que no son lo mismo:

* un tramo diagonal en un cable que toca una parte libre o el Uno: es un
  defecto de ruteo y rompe el build;
* un salto recto entre dos huecos de la misma placa (``5g -> 8c``): es un
  puente sobre el plastico, se deja y solo se cuenta.
"""

from tinkercad_brain.builder import diagonal_segments

UNO = "uno"


def _route(wire, points, routed=True):
    return {"wire": wire, "routed": routed, "reason": "ok", "points": points}


def test_un_cable_libre_libre_ruteado_no_es_diagonal():
    """El Z de la fase 41: tramos horizontales y verticales, nada torcido."""
    routes = [_route("t1.OUT -> u1.1A",
                     [[580, -215], [660, -215], [660, -245], [740, -245]])]
    assert diagonal_segments(routes, free_refs=["t1", "u1"]) == []


def test_un_cable_libre_libre_recto_es_violacion():
    """Sin ruteo Tinkercad une los pines en diagonal: eso es el defecto."""
    routes = [_route("t1.OUT -> u1.1A", [[580, -215], [740, -245]], routed=False)]
    found = diagonal_segments(routes, free_refs=["t1", "u1"])
    assert len(found) == 1
    assert found[0]["wire"] == "t1.OUT -> u1.1A"
    assert found[0]["blocking"] is True
    assert found[0]["dx"] == 160 and found[0]["dy"] == 30


def test_un_cable_del_uno_tambien_tiene_que_ser_ortogonal():
    routes = [_route("uno.D8 -> u1.1B", [[200, -45], [745, -245]])]
    found = diagonal_segments(routes, free_refs=["u1"])
    assert [v["blocking"] for v in found] == [True]


def test_un_cable_con_un_solo_extremo_libre_cuenta():
    """Basta que una punta sea libre: el cable igual tiene que rutearse."""
    routes = [_route("seg.a -> 7e", [[1260, -230], [765, 15]])]
    found = diagonal_segments(routes, free_refs=["seg"])
    assert [v["blocking"] for v in found] == [True]


def test_un_salto_entre_huecos_se_cuenta_pero_no_rompe():
    """``5g -> 8c`` es un puente corto sobre la placa, no un cable torcido."""
    routes = [_route("5g -> 8c", [[-105, -25], [-75, 35]], routed=False)]
    found = diagonal_segments(routes, free_refs=["seg"])
    assert len(found) == 1
    assert found[0]["blocking"] is False
    assert found[0]["dx"] == 30 and found[0]["dy"] == 60


def test_la_etiqueta_del_cable_se_parsea_con_o_sin_espacios():
    diagonal = [[0, 0], [100, 100]]
    for label in ("t1.OUT -> u1.1A", "t1.OUT->u1.1A", " T1.OUT -> U1.1A "):
        found = diagonal_segments([_route(label, diagonal)], free_refs=["t1", "u1"])
        assert len(found) == 1, label


def test_una_polilinea_con_un_tramo_torcido_es_violacion():
    """Regresion: un solo tramo diagonal dentro de un ruteo bueno."""
    routes = [_route("u1.3Y -> u1.4A",
                     [[780, -245], [690, -245], [690, -240], [770, -215]])]
    found = diagonal_segments(routes, free_refs=["u1"])
    assert len(found) == 1
    assert found[0]["dx"] == 80 and found[0]["dy"] == 25


def test_la_tolerancia_de_dibujo_no_marca_rectas_casi_rectas():
    """Tinkercad redondea: medio punto no es una diagonal."""
    routes = [_route("t1.OUT -> u1.1A", [[580, -215], [740, -215.4]], routed=False)]
    assert diagonal_segments(routes, free_refs=["t1", "u1"]) == []


def test_cables_sin_polilinea_no_rompen():
    routes = [
        {"wire": "a -> b", "routed": True},
        {"wire": "c -> d", "routed": True, "points": []},
        {"wire": "e -> f", "routed": True, "points": [[0, 0]]},
        {"wire": "g -> h", "routed": True, "points": [["x", "y"], [1, 1]]},
        "basura",
        None,
    ]
    assert diagonal_segments(routes, free_refs=["t1"]) == []


def test_sin_free_refs_solo_el_uno_obliga():
    routes = [
        _route("uno.D4 -> 5e", [[200, 0], [765, 15]]),
        _route("5e -> 6e", [[765, 15], [775, 25]]),
    ]
    found = diagonal_segments(routes)
    assert [v["wire"] for v in found if v["blocking"]] == ["uno.D4 -> 5e"]
    assert [v["wire"] for v in found if not v["blocking"]] == ["5e -> 6e"]
