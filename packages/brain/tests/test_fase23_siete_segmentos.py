"""Fase 23: contador 0-9 en display 7 segmentos.

Cubre tres piezas nuevas:
- layout: el display va libre fuera de la placa y las 7 resistencias
  caben repartidas entre la mitad superior (fila g) e inferior (fila e).
- sketch: tabla de digitos de anodo comun y escritura invertida.
- alias de pines: el cableado guardado usa A..G / Common y la fixture
  usa a..g / com1.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.sketches import SEVEN_SEG_DIGITS, seven_seg_sketch

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture():
    circuits = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == "siete-segmentos")


def test_fixture_existe_con_siete_resistencias():
    fixture = _fixture()
    tipos = [c["type"] for c in fixture["components"]]
    assert tipos.count("resistor") == 7
    assert tipos.count("seven-segment") == 1


def test_layout_display_libre_y_resistencias_en_dos_filas():
    layout = plan_layout(_fixture())
    placements = layout["placements"]

    assert "free" in placements["seg"]
    assert placements["seg"]["free"]["x"] == 870
    assert placements["seg"]["free"]["y"] == -230
    assert layout.get("unplaced") == []

    filas = [placements[f"r{i}"]["at"][-1] for i in range(1, 8)]
    assert filas.count("g") == 4
    assert filas.count("e") == 3


def test_layout_no_repite_huecos():
    layout = plan_layout(_fixture())
    huecos = [p["at"] for p in layout["placements"].values() if "at" in p]
    assert len(huecos) == len(set(huecos)) == 7


def test_tabla_de_digitos():
    assert len(SEVEN_SEG_DIGITS) == 10
    assert all(len(patron) == 7 for patron in SEVEN_SEG_DIGITS)
    # Todos los segmentos se encienden en el 8 y se apaga g en el 0.
    assert SEVEN_SEG_DIGITS[8] == (1, 1, 1, 1, 1, 1, 1)
    assert SEVEN_SEG_DIGITS[0] == (1, 1, 1, 1, 1, 1, 0)
    # El 1 solo usa b y c (indices 1 y 2).
    assert SEVEN_SEG_DIGITS[1] == (0, 1, 1, 0, 0, 0, 0)


def test_sketch_invierte_para_anodo_comun():
    codigo = seven_seg_sketch()
    assert "!DIGITOS[digito][i]" in codigo
    assert "void mostrar(byte digito)" in codigo
    assert "TEST:DIGITO=" in codigo
    # Los pines del sketch son los del fixture: D2..D8.
    assert "const byte PINES[7] = {2, 3, 4, 5, 6, 7, 8};" in codigo


def test_sketch_rechaza_pines_repetidos():
    with pytest.raises(ValueError):
        seven_seg_sketch(a=2, b=3, c=4, d=5, e=6, f=7, g=7)


def test_alias_de_pines_del_display():
    """El cableado real etiqueta A..G y Common; deben caer en a..g y com1."""
    inspect = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno", "pins": []},
            {"type": "7 Segment Display", "instance_id": "seg", "pins": []},
        ],
        "wires": [
            {
                "source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D2"},
                "target": {"component": "7 Segment Display", "instance_id": "seg", "pin": "A"},
            },
            {
                "source": {"component": "7 Segment Display", "instance_id": "seg", "pin": "Common"},
                "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "5V"},
            },
        ],
    }
    nets = derive_nets(inspect)
    # Los refs los deriva normalize_circuit; aqui interesa el mapeo de pines.
    assert ["sevensegment1.a", "uno.D2"] in nets
    assert ["sevensegment1.com1", "uno.5V"] in nets
