"""Tipo `flip-flop-jk` (74HC73): contrato medido en vivo el 2026-11-14.

Hechos de la sonda (circuito desechable, borrado):
- `did 116723`, tipo visible "Dual J-K Flip-Flop [74HC73]".
- Dispara en **flanco de bajada** (el taller pide flancos de bajada).
- `R` es **activo en bajo**.
- `J = K = 1` bascula.
- El cableado guardado etiqueta los pines con nombres del DOM ("Clock 1"),
  mientras el modelo los nombra `1CP`.

Se cubre: did, traduccion al terminal real, rechazo de pines inventados,
tabla de pines del spec, posicion libre en la fila de integrados y alias
del cableado guardado.
"""

from __future__ import annotations

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import DID_BY_TYPE, BuildError, fixture_to_model_call
from tinkercad_brain.fase0.component_map import TYPE_MAP, fixture_type
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.spec import PIN_TABLE, SpecError, validate_spec

JK = "Dual J-K Flip-Flop [74HC73]"


def _fixture():
    return {
        "id": "sonda-jk",
        "title": "Sonda del 74HC73",
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "ff1", "type": "flip-flop-jk"},
        ],
        "nets": [
            ["uno.5V", "ff1.Vcc"],
            ["uno.GND1", "ff1.GND"],
            ["uno.5V", "ff1.1J"],
            ["uno.5V", "ff1.1K"],
            ["uno.D3", "ff1.1CP"],
            ["uno.D9", "ff1.1R"],
            ["ff1.1Q", "uno.D2"],
            ["ff1.1NQ", "uno.D4"],
            # Segunda mitad: J/K/CP a GND y R a 5V (inactiva, CMOS sin flotar).
            ["uno.GND1", "ff1.2J"],
            ["uno.GND1", "ff1.2K"],
            ["uno.GND1", "ff1.2CP"],
            ["uno.5V", "ff1.2R"],
            ["ff1.2Q", "uno.D5"],
            ["ff1.2NQ", "uno.D6"],
        ],
    }


def test_did_y_nombres_del_catalogo():
    assert DID_BY_TYPE["flip-flop-jk"] == 116723
    assert TYPE_MAP[JK] == "flip-flop-jk"
    assert fixture_type(JK) == "flip-flop-jk"


def test_model_call_emite_el_did_y_va_libre():
    call = fixture_to_model_call(_fixture())
    partes = {p["ref"]: p for p in call["parts"]}
    assert partes["ff1"]["did"] == 116723
    assert "free" in partes["ff1"]
    assert "at" not in partes["ff1"]


def test_los_cables_terminan_en_los_terminales_reales():
    call = fixture_to_model_call(_fixture())
    cables = {(w["from"], w["to"]) for w in call["wires"]}
    # El modelo usa los nombres canonicos del 74HC73 (name2terminal).
    assert ("uno.D3", "ff1.1CP") in cables or ("uno.D3", "ff1.Clock 1") in cables
    assert any(w[1].startswith("ff1.") for w in cables)


def test_el_builder_rechaza_un_pin_inventado():
    fixture = _fixture()
    fixture["nets"].append(["uno.D7", "ff1.9Q"])
    with pytest.raises(BuildError):
        fixture_to_model_call(fixture)


def test_spec_conoce_los_catorce_pines_y_rechaza_inventados():
    assert PIN_TABLE["flip-flop-jk"] == frozenset(
        {"1J", "1K", "1CP", "1R", "1Q", "1NQ",
         "2J", "2K", "2CP", "2R", "2Q", "2NQ", "Vcc", "GND"}
    )
    with pytest.raises(SpecError):
        validate_spec(
            {
                "parts": [{"ref": "ff1", "type": "flip-flop-jk",
                           "free": {"x": 560, "y": -230}}],
                "wires": [["ff1.9Q", "uno.D2"]],
            }
        )


def test_va_en_la_fila_de_integrados_libres():
    placements = plan_layout(_fixture())["placements"]
    assert placements["ff1"]["free"] == {"x": 560, "y": -230, "angle": 0}


def test_alias_del_cableado_guardado():
    inspect = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno", "pins": []},
            {"type": JK, "instance_id": "ff1", "pins": []},
        ],
        "wires": [
            {"source": {"component": JK, "instance_id": "ff1", "pin": "Power"},
             "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "5V"}},
            {"source": {"component": JK, "instance_id": "ff1", "pin": "Ground"},
             "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "GND"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D3"},
             "target": {"component": JK, "instance_id": "ff1", "pin": "Clock 1"}},
            {"source": {"component": JK, "instance_id": "ff1", "pin": "J 1"},
             "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "5V"}},
            {"source": {"component": JK, "instance_id": "ff1", "pin": "K 1"},
             "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "5V"}},
            {"source": {"component": JK, "instance_id": "ff1", "pin": "Reset 1"},
             "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D9"}},
            {"source": {"component": JK, "instance_id": "ff1", "pin": "Output 1"},
             "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D2"}},
            {"source": {"component": JK, "instance_id": "ff1", "pin": "Inverted Output 1"},
             "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D4"}},
        ],
    }
    nets = derive_nets(inspect)

    # derive_nets une por nodo compartido, asi que 5V aparece una sola vez y
    # las tres nets de alimentacion se funden; se comprueba pertenencia.
    def junto(a, b):
        return any(a in net and b in net for net in nets)

    assert junto("flipflopjk1.Vcc", "uno.5V")
    assert junto("flipflopjk1.GND", "uno.GND1")
    assert junto("flipflopjk1.1CP", "uno.D3")
    assert junto("flipflopjk1.1J", "uno.5V")
    assert junto("flipflopjk1.1K", "uno.5V")
    assert junto("flipflopjk1.1R", "uno.D9")
    assert junto("flipflopjk1.1Q", "uno.D2")
    assert junto("flipflopjk1.1NQ", "uno.D4")
