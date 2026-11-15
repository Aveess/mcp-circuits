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
                  "oracle", "oracle_serial", "notes"):
        assert entrada.get(clave) == generada.get(clave), clave


def test_ninguna_entrada_de_un_jk_queda_al_aire():
    """Medido en vivo: sin las tres R cableadas el contador no pasaba de 3.

    Una entrada CMOS al aire no es "0": es estado indefinido. Este test es el
    que habria cazado esa net faltante antes de gastar una corrida.
    """
    fixture = _fixture()
    entradas = {"1J", "1K", "1CP", "1R", "2J", "2K", "2CP", "2R"}
    cableados: dict[str, set[str]] = {}
    for net in fixture["nets"]:
        for endpoint in net:
            ref, pin = endpoint.split(".", 1)
            if pin in entradas:
                cableados.setdefault(ref, set()).add(pin)

    for component in fixture["components"]:
        if component["type"] != "flip-flop-jk":
            continue
        ref = component["ref"]
        assert cableados.get(ref, set()) == entradas, (
            f"{ref}: entradas sin cablear {sorted(entradas - cableados.get(ref, set()))}"
        )


def test_el_reset_llega_a_las_tres_r_por_el_inversor():
    nets = _fixture()["nets"]
    reset = next(net for net in nets if net[0] == "u5.4Y")
    assert set(reset[1:]) == {"ff1.1R", "ff2.1R", "ff2.2R"}


def test_el_reloj_de_cada_etapa_viene_del_bit_anterior():
    """Q0 relojea la segunda etapa y Q1 la tercera.

    Medido en vivo: sin estos dos cables el contador repite 0,1,2,3 porque
    Q2 nunca bascula (el sintoma que el punto 6 manda diagnosticar).
    """
    nets = _fixture()["nets"]

    def net_de(nodo):
        return next(net for net in nets if net[0] == nodo)

    assert "ff2.1CP" in net_de("ff1.1Q")
    assert "ff2.2CP" in net_de("ff2.1Q")
    # Y el Uno lee los tres bits para comprobar el conteo.
    assert "uno.D3" in net_de("ff1.1Q")
    assert "uno.D4" in net_de("ff2.1Q")
    assert "uno.D5" in net_de("ff2.2Q")
    # El reloj del 555 llega a la primera etapa y se lee en D2.
    assert net_de("t1.OUT") == ["t1.OUT", "ff1.1CP", "uno.D2"]


def test_cada_segmento_lo_mueve_el_inversor_no_la_salida_positiva():
    """El display es de anodo comun: con la salida positiva nunca enciende.

    Medido en vivo: leyendo la salida positiva el sketch recibia la mascara
    complementada (0 -> 0x40 en vez de 0x3F), o sea que el display colgaba de
    la compuerta equivocada.
    """
    fixture = _fixture()
    inversores = {g.out: g for g in GATES if g.out.startswith("n")}
    for seg in SEGMENT_OUTPUT:
        gate = inversores[f"n{seg}"]
        nodo = f"{gate.chip}.{gate.slot}Y"
        net = next(n for n in fixture["nets"] if n[0] == nodo)
        assert len(net) == 3, net
        assert net[1] == f"r{seg}.1"
        assert net[2].startswith("uno.")


def test_el_oraculo_lleva_las_ocho_marcas_en_orden():
    marcas = _fixture()["oracle_serial"]
    assert marcas == [
        "TEST:PERIODO=", "TEST:RESET=OK", "TEST:CICLO=OK", "TEST:EN0=OK",
        "TEST:REANUDA=OK", "TEST:RESET_MEDIO=OK", "TEST:DECODER=OK",
        "TEST:FIN=OK",
    ]
    codigo = __import__("importlib").import_module(
        "tinkercad_brain.sketches"
    ).contador_jk_sketch()
    posiciones = [codigo.index(marca) for marca in marcas if marca != "TEST:PERIODO="]
    assert posiciones == sorted(posiciones), "las marcas no estan en orden en el sketch"


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
