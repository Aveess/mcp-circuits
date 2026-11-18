"""Fixture `contador-0-7-jk-v3`: la v2 con la alimentacion por fuente y rieles.

La v3 no cambia el sistema: mismo reloj 555, mismos JK en cascada, mismo
decodificador y el mismo sketch. Cambia **una** cosa, la que Eddie fijo como
regla: la fuente es una pieza Power Supply y el reparto va por los rieles de la
placa, con rojo para el positivo y negro para la tierra.

Lo que estos tests protegen:

- la v1 y la v2 **no se tocan**: siguen generando lo suyo (esto se comprueba
  tambien desde el lado de la v3, comparando net por net);
- la entrada de `circuits.json` es la que genera el modulo, o el build en vivo
  arma un circuito que ningun test aprobo;
- el 5V del Uno no alimenta nada: si vuelve, vuelve la estrella que la regla
  quiere eliminar;
- el display sigue en catodo comun y girado 180 grados con la pata opuesta,
  que es lo unico que hace que el numero se lea derecho.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tinkercad_brain.builder import BuildError, fixture_to_model_call
from tinkercad_brain.contador_jk_v2 import contador_jk_v2_fixture
from tinkercad_brain.contador_jk_v3 import FIXTURE_ID, contador_jk_v3_fixture
from tinkercad_brain.layout_v3 import plan_layout_v3, plan_nets_v3
from tinkercad_brain.sketches import contador_jk_v2_sketch

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "fase0" / "circuits.json"


def _fixture() -> dict:
    return contador_jk_v3_fixture()


def test_la_entrada_del_repositorio_es_la_que_genera_el_modulo():
    circuits = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    entrada = next((c for c in circuits if c["id"] == FIXTURE_ID), None)
    assert entrada is not None, f"falta {FIXTURE_ID} en circuits.json"

    generada = _fixture()
    claves = (
        "title", "layout", "boards", "components", "nets", "doc", "oracle",
        "oracle_serial", "notes", "sim_wait_seconds", "code_features",
    )
    for clave in claves:
        assert entrada.get(clave) == generada.get(clave), clave


def test_la_fixture_declara_layout_v3_y_las_tres_placas_de_la_v2():
    fixture = _fixture()

    assert fixture["id"] == FIXTURE_ID
    assert fixture["layout"] == "v3"
    assert [b["kind"] for b in fixture["boards"]] == ["large", "large", "small"]
    assert [b["x"] for b in fixture["boards"]] == [870, 1570, 2100]
    assert {"ref": "ps1", "type": "power-supply"} in fixture["components"]


def test_la_fuente_reemplaza_al_5v_del_uno_en_la_net_y_nada_mas():
    v2 = contador_jk_v2_fixture()
    v3 = _fixture()

    assert len(v3["nets"]) == len(v2["nets"])
    for antes, despues in zip(v2["nets"], v3["nets"]):
        esperado = ["ps1.Vcc" if e == "uno.5V" else e for e in antes]
        if "uno.GND1" in antes:
            esperado = esperado + ["ps1.GND"]
        assert despues == esperado

    # El generador de la v3 no reescribe la v2: es el contrato con lo entregado.
    assert any("uno.5V" in net for net in contador_jk_v2_fixture()["nets"])


def test_una_pata_esta_en_una_sola_net():
    fixture = _fixture()
    vistas: dict[str, str] = {}
    for net in fixture["nets"]:
        for endpoint in net:
            anterior = vistas.get(endpoint)
            assert anterior is None, (
                f"{endpoint} esta en dos nets ({anterior} y {net}): eso es un corto"
            )
            vistas[endpoint] = ",".join(net)


def test_el_5v_del_uno_no_aparece_en_ningun_cable():
    nets = plan_nets_v3(_fixture(), plan_layout_v3(_fixture())["placements"])

    for wire in nets["wires"]:
        assert "uno.5V" not in (wire["from"], wire["to"]), wire


def test_el_builder_arma_la_llamada_con_la_fuente_libre_y_sus_dos_cables():
    call = fixture_to_model_call(_fixture(), code="// v3")

    por_ref = {part["ref"]: part for part in call["parts"]}
    assert "uno" not in por_ref, "el Uno lo crea el puente, no va como part"
    assert por_ref["ps1"]["did"] == 111724
    assert por_ref["ps1"]["free"] == {"x": 450.0, "y": 0.0}
    assert "at" not in por_ref["ps1"]

    fuente = [
        wire for wire in call["wires"]
        if wire["from"].startswith("ps1.") or wire["to"].startswith("ps1.")
    ]
    assert len(fuente) == 2, "la fuente alimenta una sola placa con dos cables"
    assert {wire["color"] for wire in fuente} == {"red", "black"}


def test_el_builder_rechaza_una_v3_sin_fuente():
    fixture = _fixture()
    sin_fuente = {
        **fixture,
        "components": [c for c in fixture["components"] if c["ref"] != "ps1"],
    }
    with pytest.raises(BuildError):
        fixture_to_model_call(sin_fuente)


def test_el_display_sigue_en_catodo_comun_y_girado():
    fixture = _fixture()

    nets = [" ".join(net) for net in fixture["nets"]]
    assert not any("seg.com2" in net for net in nets), (
        "Tinkercad guarda las dos patas como Common y declararlas las dos baja "
        "la fidelidad sin que falte un cable"
    )
    gnd = next(net for net in nets if "seg.com1" in net)
    assert "uno.GND1" in gnd

    placements = plan_layout_v3(fixture)["placements"]
    assert placements["seg"]["angle"] == 180


def test_el_sketch_es_el_de_la_v2_y_no_corre_pruebas():
    v2 = contador_jk_v2_sketch()

    # Mismo sketch: la v3 no toca el sistema, solo la alimentacion.
    assert "TEST:DIGITO=" in v2
    assert "pruebaCiclo" not in v2 and "pruebaReset" not in v2
