"""Fase 27: 555 en astable (R=10k, C=10uF) como reloj de ~14 Hz.

Contrato de la fase:

- el 555 va libre en el apilado de integrados y su capacitor tambien: los
  dos se cablean por terminal, sin geometria de huecos de protoboard;
- DIS, THR y TRIG quedan atados al nodo de tiempo, R va de Vcc al nodo y C
  del nodo a GND (astable de una sola resistencia);
- Reset a Vcc; OUT va a D2 y el Uno solo mide;
- el sketch emite ALTO/BAJO/FREQ y un veredicto explicito;
- los presets fijan 10k y 10uF pasando el prefijo como cuarto argumento.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import DID_BY_TYPE, BuildError, fixture_to_model_call
from tinkercad_brain.fase0.component_map import TYPE_MAP, fixture_type
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.runner import run_build
from tinkercad_brain.sketches import astable_555_sketch
from tinkercad_brain.spec import PIN_TABLE, SpecError, validate_spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture():
    circuits = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == "temporizador-555")


def test_la_fixture_tiene_555_resistor_y_capacitor():
    tipos = [c["type"] for c in _fixture()["components"]]
    assert tipos.count("timer-555") == 1
    assert tipos.count("resistor") == 1
    assert tipos.count("capacitor") == 1


def test_el_555_y_su_capacitor_van_libres_y_apilados():
    placements = plan_layout(_fixture())["placements"]

    assert placements["t1"]["free"] == {"x": 560, "y": -230, "angle": 0}
    assert placements["c1"]["free"] == {"x": 690, "y": -230, "angle": 0}
    assert "at" not in placements["t1"]
    assert "at" not in placements["c1"]
    assert plan_layout(_fixture()).get("unplaced") == []


def test_did_y_nombres_del_catalogo():
    assert DID_BY_TYPE["timer-555"] == 116689
    assert DID_BY_TYPE["capacitor"] == 57752
    assert TYPE_MAP["555 Timer"] == "timer-555"
    assert TYPE_MAP["Capacitor"] == "capacitor"
    assert fixture_type("Timer") == "timer-555"


def test_model_call_tres_partes_y_diez_cables():
    call = fixture_to_model_call(_fixture())

    assert len(call["parts"]) == 3  # el Uno lo crea el puente
    assert len(call["wires"]) == 10
    free = {p["ref"]: p for p in call["parts"] if "free" in p}
    assert free["t1"] == {"ref": "t1", "did": 116689,
                          "free": {"x": 560, "y": -230}, "angle": 0}
    assert free["c1"] == {"ref": "c1", "did": 57752,
                          "free": {"x": 690, "y": -230}, "angle": 0}


def test_el_nodo_de_tiempo_une_dis_thr_trig_y_el_capacitor():
    call = fixture_to_model_call(_fixture())
    puntas = {frozenset((w["from"], w["to"])) for w in call["wires"]}

    assert frozenset(("t1.DIS", "t1.THR")) in puntas
    assert frozenset(("t1.DIS", "t1.TRIG")) in puntas
    assert frozenset(("t1.DIS", "c1.1")) in puntas
    # El resistor esta en la placa: pin 1 al 5V y pin 2 al nodo (hueco g5).
    assert frozenset(("uno.5V", "1g")) in puntas
    assert frozenset(("t1.DIS", "5g")) in puntas


def test_el_builder_rechaza_un_pin_inventado_del_555():
    fixture = json.loads(json.dumps(_fixture()))
    fixture["nets"][3] = ["t1.OUTPUT", "uno.D2"]
    with pytest.raises(BuildError):
        fixture_to_model_call(fixture)


def test_el_sketch_mide_con_pulsein_y_emite_veredicto():
    codigo = astable_555_sketch()

    assert 'Serial.println("TEST:555=LISTO");' in codigo
    assert "pulseIn(OUT, HIGH, TIMEOUT)" in codigo
    assert "pulseIn(OUT, LOW, TIMEOUT)" in codigo
    assert 'Serial.print("TEST:555=ALTO,");' in codigo
    assert 'Serial.print("TEST:555=BAJO,");' in codigo
    assert 'Serial.print("TEST:555=FREQ,");' in codigo
    assert 'Serial.println(ok ? "TEST:555=OK" : "TEST:555=FAIL");' in codigo


def test_el_sketch_valida_pin_y_timeout():
    with pytest.raises(ValueError):
        astable_555_sketch(out_pin=99)
    with pytest.raises(ValueError):
        astable_555_sketch(timeout_us=0)
    with pytest.raises(ValueError):
        astable_555_sketch(timeout_us=True)


def test_alias_del_555_en_el_cableado_guardado():
    """El guardado usa Power/Reset/Ground/Discharge/Threshold/Trigger/Out."""
    inspect = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno", "pins": []},
            {"type": "555 Timer", "instance_id": "t1", "pins": []},
            {"type": "Capacitor", "instance_id": "c1", "pins": []},
            {"type": "Resistor", "instance_id": "r1", "pins": []},
        ],
        "wires": [
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "5V"},
             "target": {"component": "555 Timer", "instance_id": "t1", "pin": "Power"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "GND"},
             "target": {"component": "555 Timer", "instance_id": "t1", "pin": "Ground"}},
            {"source": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "5V"},
             "target": {"component": "555 Timer", "instance_id": "t1", "pin": "Reset"}},
            {"source": {"component": "555 Timer", "instance_id": "t1", "pin": "Discharge"},
             "target": {"component": "555 Timer", "instance_id": "t1", "pin": "Threshold"}},
            {"source": {"component": "555 Timer", "instance_id": "t1", "pin": "Discharge"},
             "target": {"component": "555 Timer", "instance_id": "t1", "pin": "Trigger"}},
            {"source": {"component": "555 Timer", "instance_id": "t1", "pin": "Discharge"},
             "target": {"component": "Capacitor", "instance_id": "c1", "pin": "Terminal 1"}},
            {"source": {"component": "Capacitor", "instance_id": "c1", "pin": "Terminal 2"},
             "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "GND"}},
            {"source": {"component": "555 Timer", "instance_id": "t1", "pin": "Out"},
             "target": {"component": "Arduino Uno R3", "instance_id": "uno", "pin": "D2"}},
        ],
    }
    grupos = {frozenset(net) for net in derive_nets(inspect)}

    assert frozenset({"uno.5V", "timer5551.Vcc", "timer5551.Reset"}) in grupos
    assert frozenset({"uno.GND1", "timer5551.GND", "capacitor1.2"}) in grupos
    assert frozenset(
        {"capacitor1.1", "timer5551.DIS", "timer5551.THR", "timer5551.TRIG"}
    ) in grupos
    assert frozenset({"timer5551.OUT", "uno.D2"}) in grupos


def test_spec_conoce_los_pines_del_555_y_del_capacitor():
    assert PIN_TABLE["timer-555"] == frozenset(
        {"CTRL", "Reset", "OUT", "THR", "GND", "DIS", "TRIG", "Vcc"}
    )
    assert PIN_TABLE["capacitor"] == frozenset({"1", "2"})

    with pytest.raises(SpecError):
        validate_spec(
            {
                "parts": [
                    {"ref": "t1", "type": "timer-555", "free": {"x": 560, "y": -230}},
                ],
                "wires": [["t1.THX", "uno.D2"]],
            }
        )


def _fake_call_tool(calls):
    def call_tool(tool, arguments):
        calls.append((tool, arguments))
        if tool == "tinkercad_create_circuit":
            return json.dumps({"circuit_id": "abc12345678"})
        if tool == "tinkercad_build_circuit_model":
            return json.dumps({"success": True, "persisted": True})
        if tool == "tinkercad_inspect_circuit":
            return json.dumps({"components": [], "wires": []})
        if tool == "tinkercad_read_serial_monitor":
            return ""
        return json.dumps({"success": True})

    return call_tool


def test_el_runner_pasa_el_prefijo_solo_cuando_la_fixture_lo_pide():
    calls = []
    presets = [
        {"component": "Resistor", "property": "resistance", "value": 10, "unit": "k"},
        {"component": "Capacitor", "property": "capacitance", "value": 10, "unit": "u"},
        {"component": "Comp X", "property": "Target Y", "value": -105},
    ]

    run_build(
        _fixture(), "// codigo", _fake_call_tool(calls), "555 presets",
        presets=presets, reuse=False, repair=False,
    )

    args = [a for t, a in calls if t == "tinkercad_set_component_property_model"]
    assert args == [
        {"component_name": "Resistor", "property_name": "resistance",
         "value": 10, "unit": "k"},
        {"component_name": "Capacitor", "property_name": "capacitance",
         "value": 10, "unit": "u"},
        # Sin unit se conserva la forma de siempre (3 claves).
        {"component_name": "Comp X", "property_name": "Target Y", "value": -105},
    ]
