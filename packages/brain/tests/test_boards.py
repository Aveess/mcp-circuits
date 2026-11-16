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
    footprint_for,
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


def test_la_placa_grande_publica_sus_cuatro_rieles_de_50_huecos():
    # Medido en vivo el 2026-11-15 sobre un diseno desechable: la grande tiene
    # cuatro filas de riel de 50 huecos, y -95/-85 abajo (el modelo rotula las
    # dos "X") y +85/+95 arriba ("Y"/"Z"). El par de abajo es un solo nodo, o
    # sea que ahi solo puede ir una polaridad; el layout v3 lo respeta
    # (`_SINGLE_NODE_SIDES`) en vez de prohibir los rieles enteros.
    assert set(LARGE.rails) == {"T+", "T-", "B+", "B-"}
    # El riel llega hasta la columna 60 (el ultimo hueco esta en x=295); son
    # 50 huecos **salteados** dentro de 1..60, no las primeras 50 columnas.
    assert LARGE.rail_columns == 60
    assert len(LARGE.rail_holes) == 50
    assert LARGE.rails["B+"] == -85 and LARGE.rails["B-"] == -95
    assert LARGE.rails["T+"] == 85 and LARGE.rails["T-"] == 95


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


def test_huella_del_jk_deja_las_dos_hileras_en_el_canal():
    # Medido en vivo el 2026-11-15 (fqm2OOLKTr3): el 74HC73 tiene las
    # hileras a 30 unidades, como el 555. Anclado por 1J en la fila de
    # abajo, la otra hilera queda arriba: una en cada mitad.
    huella = footprint("dip14-jk")

    assert huella["1J"] == (0, "f") and huella["1CP"] == (0, "e")
    assert huella["1NQ"] == (1, "f") and huella["1R"] == (1, "e")
    assert huella["Vcc"] == (3, "e") and huella["GND"] == (3, "f")
    assert huella["2J"] == (6, "e") and huella["2NQ"] == (6, "f")
    assert len(huella) == 14


def test_footprint_for_elige_la_huella_de_cada_tipo():
    # Las compuertas comparten el DIP-14 de 74HC00/08/32/86 (mismos nombres
    # de pin); el JK y el 555 son DIP mas anchos y el display tiene 10 patas.
    assert footprint_for("and-gate") == footprint("dip14")
    assert footprint_for("or-gate") == footprint("dip14")
    assert footprint_for("not-gate") == footprint("dip14-not")
    assert footprint_for("xor-gate") == footprint("dip14")
    assert footprint_for("flip-flop-jk") == footprint("dip14-jk")
    assert footprint_for("timer-555") == footprint("dip8-555")
    assert footprint_for("seven-segment") == footprint("display-7seg")
    assert footprint_for("resistor") == footprint("resistor")

    with pytest.raises(KeyError):
        footprint_for("led")


def test_el_inversor_tiene_seis_compuertas_en_la_misma_huella():
    # 74HC04 medido en vivo (2rI5SQHDHcD): 1A/1Y..6A/6Y, filas e/f. La
    # numeracion fisica no cambia respecto del DIP-14 generico, solo los
    # nombres: por eso comparte huella.
    huella = footprint_for("not-gate")

    assert huella["1A"] == (0, "e") and huella["1Y"] == (1, "e")
    assert huella["4Y"] == (6, "f") and huella["6A"] == (1, "f")
    assert "7A" not in huella


def test_ninguna_huella_repite_media_columna():
    # Dos patas en la misma media columna son el mismo nodo: eso es un corto
    # dentro del chip y el circuito falla sin que se vea en el dibujo.
    for nombre, huella in FOOTPRINTS.items():
        celdas = [(dcol, half(fila)) for dcol, fila in huella.values()]
        assert len(celdas) == len(set(celdas)), nombre


def test_las_huellas_usan_dos_filas_que_caen_en_mitades_distintas():
    # Ancla en `e`: filas `e` y `f` (o `e` y `g`) quedan una en cada mitad.
    # Si las dos hileras caen del mismo lado el chip queda cortado.
    # Excepcion medida: el capacitor (did 57752) no cruza el canal. Sus dos
    # patas son huecos vecinos de la MISMA fila (`10f` -> `10f`/`11f`), o sea
    # que se inserta como un puente, no como un DIP. Exigirle dos mitades
    # seria pedirle que la placa una lo que el capacitor tiene que separar.
    for nombre, huella in FOOTPRINTS.items():
        if nombre == "capacitor":
            continue
        filas = {fila for _, fila in huella.values()}
        assert len({half(f) for f in filas}) == 2, (nombre, filas)
