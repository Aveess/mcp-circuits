"""Tipos y etiquetas de los chips AND/OR/NOT (74HC08/74HC32/74HC04).

Medido en vivo el 2026-11-15 en la placa grande (disenos desechables
`2rI5SQHDHcD` y `fAjTrnXZDLS`):

- `inspect` reporta el tipo con el nombre del catalogo y el did:
  ``Quad AND gate [74HC08]``, ``Quad OR gate [74HC32]``, ``Hex Inverter [74HC04]``.
- `inspect` nombra los pines ``1A/1B/1Y...`` y el inversor ``1A/1Y ... 6A/6Y``.
- el **guardado** usa etiquetas humanas: ``Input nA``/``Input nB``/``Output n``
  para AND y OR, y ``Input n``/``Output n`` para el inversor (una sola entrada
  por compuerta).

La fidelidad se mide sobre los nombres guardados: si el alias falta, esos pines
no resuelven y la conectividad cae aunque el cableado sea perfecto.
"""

from __future__ import annotations

import pytest

from tinkercad_brain.breadboard_nets import _PIN_ALIASES_BY_TYPE
from tinkercad_brain.builder import DID_BY_TYPE, _TYPE_BY_SLUG
from tinkercad_brain.fase0.component_map import fixture_type


def test_etiqueta_guardada_de_las_compuertas_nuevas():
    assert _PIN_ALIASES_BY_TYPE["and-gate"]["Input 1A"] == "1A"
    assert _PIN_ALIASES_BY_TYPE["or-gate"]["Output 3"] == "3Y"
    assert _PIN_ALIASES_BY_TYPE["and-gate"]["Power"] == "Vcc"
    assert _PIN_ALIASES_BY_TYPE["and-gate"]["Ground"] == "GND"
    # El inversor tiene una sola entrada por compuerta: no hay "1B".
    assert _PIN_ALIASES_BY_TYPE["not-gate"]["Input 2"] == "2A"
    assert "1B" not in _PIN_ALIASES_BY_TYPE["not-gate"].values()


def test_el_inversor_tiene_las_seis_compuertas():
    inversor = _PIN_ALIASES_BY_TYPE["not-gate"]

    for n in range(1, 7):
        assert inversor[f"Input {n}"] == f"{n}A"
        assert inversor[f"Output {n}"] == f"{n}Y"
    assert "Input 7" not in inversor


def test_inspect_resuelve_el_tipo_de_cada_chip():
    # Los tres textos medidos tienen que caer en el slug de la fixture; si no,
    # _canonical_type los deja como "quad-and-gate-[74hc08]" y no hay alias.
    assert fixture_type("Quad AND gate [74HC08]") == "and-gate"
    assert fixture_type("Quad OR gate [74HC32]") == "or-gate"
    assert fixture_type("Hex Inverter [74HC04]") == "not-gate"


def test_cada_tipo_nuevo_tiene_did_y_nombre():
    for tipo, did in (("and-gate", 116702), ("or-gate", 116721), ("not-gate", 116701)):
        assert DID_BY_TYPE[tipo] == did
        assert tipo in _TYPE_BY_SLUG


@pytest.mark.parametrize("tipo", ["and-gate", "or-gate", "not-gate"])
def test_el_alias_no_pisa_la_electricidad(tipo):
    # Vcc y GND tienen que quedar en mayuscula: el alias generico los dejaria
    # en "vcc"/"gnd" y romperia la net de alimentacion (paso con el 595).
    alias = _PIN_ALIASES_BY_TYPE[tipo]

    assert alias["Power"] == "Vcc"
    assert alias["Ground"] == "GND"
