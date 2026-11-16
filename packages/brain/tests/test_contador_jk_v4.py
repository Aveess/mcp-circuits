"""Fixture `contador-0-7-jk-v4`: el contador **sin Arduino**.

La v3 funciona, pero el Uno se quedaba con dos trabajos ajenos al conteo:
mover EN (D8) y RESET (D9) y emitir el serial de prueba. La v4 quita el
microcontrolador y deja esos dos mandos en hardware, copiando la solucion del
diseno del taller del companero (`47d2dZVCX5m`, "taller flip-flops"):

- EN es un interruptor deslizante SPDT: comun a las J y K de las tres etapas,
  un extremo a GND y el otro a Vcc.
- RESET es un pulsador de Vcc a la entrada del inversor `u1.6`, con una
  resistencia de 10k a GND.

Lo que estos tests protegen:

- la v3 **no se toca**: se reconstruye y se compara con su generador;
- no queda ni un endpoint `uno.*` en las nets ni en los cables (el Uno lo
  crea el puente siempre, pero no se cablea nada a el);
- el comun del interruptor aparece en **una sola** net; duplicarlo generaba
  conflictos de media columna y un corto con el 5V;
- el pulsador usa **dos lados distintos**: el modelo tiene dos patas por lado
  unidas internamente, y cablear dos del mismo lado puentea el boton;
- la alimentacion sale de la fuente y de los terminales de las partes libres,
  nunca de un pin del micro;
- los pines libres se traducen a las **claves** del modelo, no a los nombres
  que muestra la UI: medido en vivo, `termByName` resuelve por clave exacta y
  "Common"/"Terminal 2a" no existen como clave.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tinkercad_brain.builder import BuildError, fixture_to_model_call
from tinkercad_brain.contador_jk_v2 import contador_jk_v2_fixture
from tinkercad_brain.contador_jk_v3 import contador_jk_v3_fixture
from tinkercad_brain.contador_jk_v4 import FIXTURE_ID, contador_jk_v4_fixture
from tinkercad_brain.layout_v2 import column_conflicts
from tinkercad_brain.layout_v3 import plan_layout_v3, plan_nets_v3

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "fase0" / "circuits.json"


def _fixture() -> dict:
    return contador_jk_v4_fixture()


def _endpoints(fixture: dict) -> list[str]:
    return [endpoint for net in fixture["nets"] for endpoint in net]


def test_la_entrada_del_repositorio_es_la_que_genera_el_modulo():
    circuits = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    entrada = next((c for c in circuits if c["id"] == FIXTURE_ID), None)
    assert entrada is not None, f"falta {FIXTURE_ID} en circuits.json"

    generada = _fixture()
    claves = (
        "title", "layout", "boards", "components", "nets", "doc", "oracle",
        "oracle_serial", "notes", "sim_wait_seconds", "free_parts",
        "no_arduino",
    )
    for clave in claves:
        assert entrada.get(clave) == generada.get(clave), clave
    # Sin micro no hay features de codigo ni sketch que prometer.
    assert "code_features" not in entrada


def test_la_fixture_no_tiene_arduino_ni_cablea_a_sus_pines():
    fixture = _fixture()

    assert fixture["id"] == FIXTURE_ID
    assert fixture["layout"] == "v3"
    assert not any(c["type"] == "arduino-uno" for c in fixture["components"])
    assert not any(
        endpoint == "uno" or endpoint.startswith("uno.")
        for endpoint in _endpoints(fixture)
    )


def test_la_v3_sigue_intacta():
    v3 = contador_jk_v3_fixture()

    # La v3 ya cambio su 5V del Uno por la fuente, pero sigue cableando EN,
    # RESET y las lecturas al micro.
    assert any("ps1.Vcc" in net for net in v3["nets"])
    assert any("uno.GND1" in net for net in v3["nets"])
    assert any("uno.D8" in net for net in v3["nets"])
    assert any("uno.D9" in net for net in v3["nets"])
    assert any(c["type"] == "arduino-uno" for c in v3["components"])


def test_el_comun_del_interruptor_esta_en_una_sola_net_con_las_seis_jk():
    fixture = _fixture()

    con_comun = [net for net in fixture["nets"] if "sw1.common" in net]
    assert len(con_comun) == 1, "el comun del interruptor duplicado es un corto"
    net = con_comun[0]
    for entrada in ("ff1.1J", "ff1.1K", "ff2.1J", "ff2.1K", "ff2.2J", "ff2.2K"):
        assert entrada in net, entrada


def test_el_interruptor_cuelga_de_vcc_y_gnd():
    fixture = _fixture()

    def net_de(endpoint: str) -> list[str]:
        return next(net for net in fixture["nets"] if endpoint in net)

    # El Slideswitch nace con el comun en la clave `1` (medido en vivo,
    # 2026-11-15). Ese extremo va a Vcc para que el diseno cuente al abrirlo;
    # con `1` a GND el display se quedaba en 0 y habia que deslizarlo a mano
    # (visto en el build 3akmw1EaG0p).
    assert "sw1.1" in net_de("ps1.Vcc")
    assert "sw1.2" in net_de("ps1.GND")
    # Los extremos del SPDT no se pueden juntar: seria un corto de la fuente.
    assert net_de("sw1.1") is not net_de("sw1.2")


def test_el_reset_es_pulsador_con_pull_down_a_gnd():
    fixture = _fixture()

    senal = next(net for net in fixture["nets"] if "btn1.1" in net)
    assert set(senal) == {"btn1.1", "rpd.1", "u1.6A"}
    assert "btn1.2" in next(net for net in fixture["nets"] if "ps1.Vcc" in net)
    assert "rpd.2" in next(net for net in fixture["nets"] if "ps1.GND" in net)


def test_una_pata_esta_en_una_sola_net():
    vistas: dict[str, list[str]] = {}
    for net in _fixture()["nets"]:
        for endpoint in net:
            anterior = vistas.get(endpoint)
            assert anterior is None, (
                f"{endpoint} esta en dos nets ({anterior} y {net}): eso es un corto"
            )
            vistas[endpoint] = net


def test_el_builder_traduce_los_pines_libres_a_las_claves_del_modelo():
    """Medido en vivo: `termByName` resuelve por clave exacta, no por nombre.

    Si vuelve "Common" o "Terminal 2a" el build falla con
    `route_failed: endpoint_not_resolved` (sonda cTHoVOIqZD6).
    """
    call = fixture_to_model_call(_fixture(), code=None)
    por_ref = {part["ref"]: part for part in call["parts"]}

    for ref, did in (("sw1", 58458), ("btn1", 144786), ("ps1", 111724)):
        assert por_ref[ref]["did"] == did, ref
        assert "free" in por_ref[ref], ref

    cables = [
        (wire["from"], wire["to"]) for wire in call["wires"]
    ]
    assert ("sw1.3", "b1/13j") in cables  # 3 = Common
    assert any(from_ == "btn1.4" for from_, _ in cables)  # 4 = Terminal 2a
    assert any(from_ == "btn1.2" for from_, _ in cables)  # 2 = Terminal 1a
    assert not any(from_ == "sw1.common" for from_, _ in cables)
    assert not any(from_ == "btn1.1" for from_, _ in cables)


def test_las_dos_patas_del_pulsador_son_de_lados_distintos():
    """`1` y `2` comparten nodo interno, igual que `3` y `4`.

    La clave 4 (Terminal 2a) y la 2 (Terminal 1a) estan en lados opuestos.
    """
    from tinkercad_brain.builder import _FREE_PART_PINS

    boton = _FREE_PART_PINS["pushbutton"]
    assert boton["1"] in ("3", "4")
    assert boton["2"] in ("1", "2")


def test_el_layout_resuelve_sin_errores_ni_conflictos():
    fixture = _fixture()
    plan = plan_layout_v3(fixture)
    assert plan["errors"] == []
    assert plan["unplaced"] == []

    nets = plan_nets_v3(fixture, plan["placements"])
    assert nets["errors"] == []
    assert column_conflicts(nets) == []
    assert len(nets["wires"]) > 150


def test_la_alimentacion_sale_de_la_fuente_y_de_las_partes_libres():
    fixture = _fixture()
    nets = plan_nets_v3(fixture, plan_layout_v3(fixture)["placements"])

    alimentacion = [
        wire for wire in nets["wires"] if wire["net"] in ("5V", "GND")
    ]
    assert alimentacion
    for wire in alimentacion:
        for extremo in (wire["from"], wire["to"]):
            assert not extremo.startswith("uno."), wire
    assert any(wire["from"] == "ps1.Vcc" for wire in alimentacion)
    assert any(wire["from"] == "ps1.GND" for wire in alimentacion)
    assert any(wire["from"] == "sw1.1" for wire in alimentacion)
    assert any(wire["from"] == "btn1.2" for wire in alimentacion)


def test_sin_micro_no_se_promete_oraculo_serial():
    fixture = _fixture()

    assert fixture["oracle_serial"] == []
    assert "sketch" not in fixture
    assert "TEST:" not in " ".join(fixture["oracle"])


def test_el_builder_rechaza_una_v4_sin_fuente():
    fixture = _fixture()
    sin_fuente = {
        **fixture,
        "components": [c for c in fixture["components"] if c["ref"] != "ps1"],
    }
    with pytest.raises(BuildError):
        fixture_to_model_call(sin_fuente, code=None)


def test_el_reporte_no_habla_de_un_sketch_que_no_existe():
    """Sin micro no hay sketch: el reporte lo dice, no lo da por sentado."""
    from tinkercad_brain.documenter import render_build_report

    texto = render_build_report(
        title="Contador v4",
        circuit_url="https://www.tinkercad.com/things/3akmw1EaG0p/editel",
        fidelity={"score": 1.0},
        sim_summary="{}",
        records=[],
        oracle={
            "expected": [],
            "found": [],
            "missing": [],
            "ok": True,
            "has_code": False,
            "serial_required": False,
            "serial_lines": 0,
        },
    )
    assert "sin sketch" in texto
    assert "el sketch no usa" not in texto


def test_el_runner_marca_que_no_hay_codigo():
    """`run_build` con `code=None` deja `oracle["has_code"] = False`."""
    from tinkercad_brain.runner import run_build

    def call_tool(tool, arguments):
        if tool == "tinkercad_create_circuit":
            return json.dumps({"circuit_id": "abc12345678"})
        if tool == "tinkercad_build_circuit_model":
            return json.dumps({"success": True, "persisted": True})
        if tool == "tinkercad_inspect_circuit":
            return json.dumps({"components": [], "wires": []})
        return json.dumps({"success": True})

    resultado = run_build(_fixture(), None, call_tool, "Contador v4")

    assert resultado["oracle"]["has_code"] is False
    assert resultado["oracle"]["serial_required"] is False


def test_el_build_pide_quitar_el_uno_que_sobra():
    """El puente crea el Uno siempre; `no_arduino` lo quita al final."""
    fixture = _fixture()

    assert fixture["no_arduino"] is True
    assert fixture_to_model_call(fixture, code=None)["remove_unused_uno"] is True


def test_el_builder_rechaza_no_arduino_si_hay_un_pin_del_uno_cableado():
    fixture = _fixture()
    nets = [list(net) for net in fixture["nets"]]
    nets[0] = nets[0] + ["uno.D13"]

    with pytest.raises(BuildError):
        fixture_to_model_call({**fixture, "nets": nets}, code=None)


def test_la_v4_no_es_la_v2():
    v2 = contador_jk_v2_fixture()
    v4 = _fixture()

    assert len(v4["components"]) == len(v2["components"]) + 3  # +ps1, sw1, btn1, rpd -uno
    assert any("uno.D2" in net for net in v2["nets"])
    assert not any("uno.D2" in net for net in v4["nets"])
