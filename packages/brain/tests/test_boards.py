"""Geometria de placa y huellas de las piezas insertadas.

La v2 inserta los integrados en breadboards grandes: eso necesita saber donde
cae cada pata. Todo lo de aqui esta medido en vivo el 2026-11-15 sobre disenos
desechables (ver docs/superpowers/specs/2026-11-15-layout-v2-design.md). No se
recalcula nada: si un numero no cuadra, se vuelve a medir.

Convencion de filas (la del cerebro y la del puente, no la del modelo): `a` es
la fila de arriba (y = +55) y `j` la de abajo (y = -55). La placa grande rotula
al reves (`A` = -55), pero el puente ubica los huecos por `y`, asi que el
cerebro puede hablar siempre este idioma.
"""

from __future__ import annotations

import pytest

from tinkercad_brain.boards import (
    FOOTPRINTS,
    LARGE,
    SMALL,
    Board,
    board,
    columns,
    footprint,
    half,
    half_holes,
    hole,
    x_of,
)


def test_large_tiene_62_columnas_y_dos_mitades():
    assert len(list(columns("large"))) == 62
    assert x_of("large", 1) == -295 and x_of("large", 62) == 315
    assert half("e") == "top" and half("f") == "bottom"
    assert half("a") == "top" and half("j") == "bottom"


def test_half_holes_devuelve_los_cinco_de_la_mitad():
    assert half_holes(7, "top") == ["7a", "7b", "7c", "7d", "7e"]
    assert half_holes(7, "bottom") == ["7f", "7g", "7h", "7i", "7j"]
    assert hole("small", 5, "f") == "5f"


def test_la_placa_chica_sigue_con_30_columnas_y_rieles():
    assert SMALL.columns == 30
    assert x_of("small", 1) == -145 and x_of("small", 30) == 145
    assert set(SMALL.rails) == {"T+", "T-", "B+", "B-"}


def test_la_placa_grande_no_publica_rieles():
    # Los dos rieles de abajo comparten nombre "X" y nodo: usarlos para
    # alimentacion seria un corto silencioso.
    assert LARGE.rails == {}


def test_board_es_una_tabla_nombrada_y_se_busca_por_nombre():
    assert isinstance(SMALL, Board)
    assert board("large") is LARGE
    with pytest.raises(KeyError):
        board("mediana")


def test_columnas_fuera_de_rango_no_existen():
    assert hole("large", 62, "e") == "62e"
    with pytest.raises(ValueError):
        hole("large", 63, "e")
    with pytest.raises(ValueError):
        hole("small", 31, "e")
    with pytest.raises(ValueError):
        x_of("large", 0)


def test_huella_del_dip14_una_pata_por_media_columna():
    huella = footprint("dip14")

    assert len(huella) == 14
    assert huella["1A"] == (0, "e") and huella["Vcc"] == (0, "f")
    assert huella["GND"] == (6, "e") and huella["3Y"] == (6, "f")
    assert len({half(r) for _, r in huella.values()}) == 2


def test_huella_del_555_deja_una_hilera_por_mitad():
    huella = footprint("dip8-555")

    assert huella["CTRL"] == (0, "f") and huella["Reset"] == (0, "e")
    assert huella["Vcc"] == (-3, "f") and huella["GND"] == (-3, "e")
    assert len({half(r) for _, r in huella.values()}) == 2


def test_huella_del_display_encaja_en_cinco_columnas():
    huella = footprint("display-7seg")

    assert huella["a"] == (0, "e") and huella["b"] == (-1, "e")
    assert huella["c"] == (0, "i") and huella["dp"] == (-1, "i")
    assert huella["com1"] == (1, "i") and huella["com2"] == (1, "e")
    assert huella["g"] == (3, "e") and huella["e"] == (3, "i")
    assert len({(c, half(r)) for c, r in huella.values()}) == 10


def test_la_resistencia_cruza_el_canal_en_su_columna():
    huella = footprint("resistor")

    assert huella["1"] == (0, "e") and huella["2"] == (0, "g")
    assert half(huella["1"][1]) != half(huella["2"][1])


def test_ninguna_huella_repite_media_columna():
    # Dos patas en la misma media columna son el mismo nodo: eso es un corto
    # dentro del chip y el circuito falla sin que se vea en el dibujo.
    for nombre, huella in FOOTPRINTS.items():
        celdas = [(dcol, half(fila)) for dcol, fila in huella.values()]
        assert len(celdas) == len(set(celdas)), nombre


def test_las_huellas_usan_dos_filas_que_caen_en_mitades_distintas():
    # Ancla en `e`: filas `e` y `f` (o `e` y `g`) quedan una en cada mitad.
    # Si las dos hileras caen del mismo lado el chip queda cortado.
    for nombre, huella in FOOTPRINTS.items():
        filas = {fila for _, fila in huella.values()}
        assert len({half(f) for f in filas}) == 2, (nombre, filas)
