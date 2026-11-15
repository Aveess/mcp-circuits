"""Fixture `contador-0-7-jk`: el circuito completo del taller 3.

El test es la red de seguridad del generador: la entrada de `circuits.json`
tiene que ser identica a lo que produce `contador_jk_fixture()` (si divergen,
el mensaje dice cual), todo pin tiene que existir en su tipo, cada segmento
tiene que llevar su resistencia serie y el layout tiene que respetar las
posiciones ya probadas.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tinkercad_brain.builder import _series_resistor_errors, fixture_to_model_call
from tinkercad_brain.contador_jk import FIXTURE_ID, contador_jk_fixture
from tinkercad_brain.decoder7 import GATES, SEGMENT_OUTPUT, XOR_GATES
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.spec import PIN_TABLE, validate_spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture():
    return contador_jk_fixture()


def _entrada():
    circuits = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return next((c for c in circuits if c["id"] == FIXTURE_ID), None)


def test_la_entrada_del_repositorio_es_la_que_genera_el_modulo():
    entrada = _entrada()
    assert entrada is not None, "falta contador-0-7-jk en circuits.json"
    generada = _fixture()
    for clave in ("components", "nets", "wiring", "code_features", "doc",
                  "oracle", "notes"):
        assert entrada.get(clave) == generada.get(clave), clave


def test_cada_pin_existe_en_su_tipo():
    fixture = _fixture()
    tipo = {c["ref"]: c["type"] for c in fixture["components"]}
    for net in fixture["nets"]:
        for endpoint in net:
            ref, pin = endpoint.split(".", 1)
            if ref == "uno":
                continue
            tabla = PIN_TABLE.get(tipo[ref])
            assert tabla is not None, f"tipo sin tabla de pines: {tipo[ref]}"
            assert pin in tabla, f"{endpoint} no existe en {tipo[ref]}"


def test_nets_sin_duplicados_y_con_dos_extremos():
    fixture = _fixture()
    for net in fixture["nets"]:
        assert len(net) >= 2, net
        assert len(set(net)) == len(net), net


def test_ningun_segmento_cuelga_sin_resistencia_serie():
    assert _series_resistor_errors(_fixture()) == []


def test_layout_en_la_fila_de_integrados_y_el_display_a_la_derecha():
    layout = plan_layout(_fixture())
    assert layout.get("unplaced") == []
    placements = layout["placements"]
    assert placements["t1"]["free"]["x"] == 560
    assert placements["ff1"]["free"]["x"] == 760
    assert placements["ff2"]["free"]["x"] == 960
    assert placements["c1"]["free"]["x"] == 690
    assert placements["c2"]["free"]["x"] == 690
    # Ultimo integrado en 2560; el display 300 mas alla.
    assert placements["seg"]["free"]["x"] == 2860


def test_el_modelo_cabe_en_los_limites_del_build():
    call = fixture_to_model_call(_fixture())
    # El Uno lo coloca el build; las demas partes salen de la fixture.
    assert len(call["parts"]) == len(_fixture()["components"]) - 1
    assert len(call["wires"]) <= 150


def test_validate_spec_acepta_la_fixture():
    fixture = _fixture()
    placements = plan_layout(fixture)["placements"]
    parts = []
    for component in fixture["components"]:
        ref = component["ref"]
        if ref == "uno":
            continue
        placement = placements[ref]
        if "free" in placement:
            parts.append({"ref": ref, "type": component["type"],
                          "free": {"x": placement["free"]["x"],
                                   "y": placement["free"]["y"]}})
        else:
            parts.append({"ref": ref, "type": component["type"],
                          "at": placement["at"]})
    validate_spec(
        {"parts": parts, "wires": [net for net in fixture["nets"] if len(net) == 2]}
    )


def test_el_decodificador_esta_completo_en_el_cableado():
    fixture = _fixture()
    nets = fixture["nets"]
    # Cada salida de compuerta que se usa tiene su net, y cada segmento pasa
    # por su resistencia y llega al display.
    for gate in GATES + XOR_GATES:
        consumidores = [
            (g.chip, g.slot)
            for g in GATES + XOR_GATES
            for entrada in (g.a, g.b)
            if entrada == gate.out
        ]
        nodo = f"{gate.chip}.{gate.slot}Y"
        if consumidores:
            assert any(net[0] == nodo and len(net) > 1 for net in nets), nodo
    for seg in SEGMENT_OUTPUT:
        assert any(net[-1] == f"seg.{seg}" for net in nets), seg


@pytest.mark.parametrize("net", _fixture()["nets"])
def test_ninguna_net_mezcla_dos_fuentes_de_alimentacion(net):
    fuentes = {e for e in net if e.startswith("uno.") and e in {"uno.5V", "uno.GND1"}}
    assert len(fuentes) <= 1, net


def test_el_pipeline_sabe_construirla():
    """Sin registro en demo_build la fixture se montaria sin sketch ni valores."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "demo_build", ROOT / "scripts" / "demo_build.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)

    assert modulo._SKETCH_BY_FIXTURE[FIXTURE_ID] == "contador_jk_sketch"
    presets = modulo.select_presets(_fixture())
    por_ref = {p["component"]: p for p in presets}
    assert por_ref["r1"]["value"] == 10 and por_ref["r1"]["unit"] == "k"
    assert por_ref["r2"]["value"] == 68 and por_ref["r2"]["unit"] == "k"
    assert por_ref["c1"]["unit"] == "u" and por_ref["c2"]["unit"] == "n"
    for seg in "abcdefg":
        assert por_ref[f"r{seg}"]["value"] == 220
    assert "TEST:FIN=OK" in (modulo.select_code(_fixture()) or "")
