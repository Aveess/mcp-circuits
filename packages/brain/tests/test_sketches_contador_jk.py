"""Sketch secuenciador del contador 0-7 con JK.

El sketch no solo cuenta: demuestra las cuatro pruebas del punto 5 en la
simulacion y verifica el decodificador contra la tabla de verdad. El serial
es el oraculo, asi que cada prueba deja una marca fija.

Regla de lectura: el acarreo entre JK es asincrono y el display pasa por
estados intermedios, asi que toda lectura se toma con dos muestras iguales
separadas 60 ms.
"""

from __future__ import annotations

import re

from tinkercad_brain.decoder7 import LIT_TABLE
from tinkercad_brain.sketches import contador_jk_sketch


def test_emite_las_siete_marcas_del_oraculo():
    codigo = contador_jk_sketch()
    for marca in (
        "TEST:PERIODO=",
        "TEST:RESET=OK",
        "TEST:CICLO=OK",
        "TEST:EN0=OK",
        "TEST:REANUDA=OK",
        "TEST:RESET_MEDIO=OK",
        "TEST:DECODER=OK",
        "TEST:FIN=OK",
    ):
        assert marca in codigo, marca


def test_la_tabla_del_sketch_es_la_del_netlist():
    codigo = contador_jk_sketch()
    valores = re.search(r"TABLA\[8\]\s*=\s*\{([^}]*)\}", codigo)
    assert valores, "falta la tabla de segmentos"
    numeros = [int(v.strip(), 0) for v in valores.group(1).split(",") if v.strip()]
    assert tuple(numeros) == LIT_TABLE


def test_usa_millis_y_no_delays_largos():
    codigo = contador_jk_sketch()
    assert "millis()" in codigo
    # Los unicos delay permitidos son los de sondeo y estabilizacion.
    for valor in re.findall(r"delay\((\d+)\)", codigo):
        assert int(valor) <= 120, valor


def test_pines_del_contrato():
    codigo = contador_jk_sketch()
    assert "const int CLK = 2;" in codigo
    assert "const int Q0 = 3;" in codigo
    assert "const int Q1 = 4;" in codigo
    assert "const int Q2 = 5;" in codigo
    assert "const int SENSE_G = 6;" in codigo
    assert "const int EN = 8;" in codigo
    assert "const int RST = 9;" in codigo
    assert "A0" in codigo and "A5" in codigo


def test_la_secuencia_esperada_es_la_del_contador():
    codigo = contador_jk_sketch()
    # Dos ciclos completos: 0..7..0..7..0.
    esperada = re.search(r"SECUENCIA\[\]\s*=\s*\{([^}]*)\}", codigo)
    assert esperada, "falta la secuencia esperada"
    valores = [int(v.strip()) for v in esperada.group(1).split(",") if v.strip()]
    assert valores == list(range(8)) * 2 + [0]


def test_el_decoder_se_lee_con_guarda_de_flanco():
    """Medido: leer Q y los segmentos por separado hacia fallar el decoder.

    Un flanco del reloj cae entre las dos lecturas (~60 ms) y la mascara no
    corresponde al numero. La guarda exige Q igual antes y despues.
    """
    codigo = contador_jk_sketch()
    assert "bool leeEstado(int *valor, byte *mascara)" in codigo
    assert "if (antes != despues) return false;" in codigo
    # Y deja evidencia de la mascara cuando no coincide.
    assert "TEST:MASK=" in codigo


def test_el_reset_es_activo_en_alto():
    """El taller pide RESET que devuelve a 000 sin flanco: el sketch lo pulsa."""
    codigo = contador_jk_sketch()
    assert "digitalWrite(RST, HIGH)" in codigo
    assert "digitalWrite(RST, LOW)" in codigo
