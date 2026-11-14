"""Tester independiente ronda 9: L293D a 180 + autocorreccion del runner.

Sin monkeypatch sobre produccion: builder/layout/derive reales sobre la
fixture real y sinteticas. Si un test falla, es un bug contra produccion.
"""
import json
import re
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import BuildError, fixture_to_model_call
from tinkercad_brain.fase0.metrics import compare_connectivity
from tinkercad_brain.fase0.normalize import normalize_circuit
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.runner import run_build

ROOT = Path(__file__).resolve().parents[1]
REAL_FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"
CID = "r9circuit"

# Geometria 180 verificable: ancla enable1=17f; f decrece, e crece.
L293D_HOLES_180 = {
    "enable1": "17f", "input1": "16f", "output1": "15f", "gnd": "14f",
    "gnd1": "13f", "output2": "12f", "input2": "11f", "vs": "10f",
    "vss": "17e", "input4": "16e", "output4": "15e", "gnd3": "14e",
    "gnd2": "13e", "output3": "12e", "input3": "11e", "enable2": "10e",
}
# Pin opuesto en la misma columna (otra mitad del canal).
OPPOSITE = {
    "17f": "17e", "16f": "16e", "15f": "15e", "14f": "14e",
    "13f": "13e", "12f": "12e", "11f": "11e", "10f": "10e",
}


def _fixture(fixture_id="motor-l293d-bateria"):
    circuits = json.loads(REAL_FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == fixture_id)


def _hole(ep):
    return ep if re.fullmatch(r"\d+[a-j]", ep or "") else None


def _wire_pairs(call):
    return {frozenset((w["from"], w["to"])) for w in call["wires"]}


def _components_of_wires(call, pin_hole):
    """Componentes conexas del grafo de wires + identidades pin<->hueco."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    for endpoint, hole in pin_hole.items():
        union(endpoint, hole)
    for w in call["wires"]:
        union(w["from"], w["to"])
    groups = {}
    for node in list(parent):
        groups.setdefault(find(node), set()).add(node)
    return list(groups.values())


def _same_group(groups, a, b):
    return any(a in g and b in g for g in groups)


# ---------------------------------------------------------------- builder

def test_r9_l293d_180_los_16_huecos_exactos_f_decrece_e_crece():
    pins = list(L293D_HOLES_180)
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "drv1", "type": "l293d"},
        ],
        "nets": [[f"uno.T{i:02d}", f"drv1.{pin}"] for i, pin in enumerate(pins)],
    }
    assert plan_layout(fixture)["placements"]["drv1"] == {
        "at": "17f", "pin": "enable1", "angle": 180,
    }
    call = fixture_to_model_call(fixture)
    assert call["parts"] == [
        {"ref": "drv1", "did": 112326, "at": "17f", "pin": "Enable1", "angle": 180}
    ]
    hole_by_uno = {}
    for w in call["wires"]:
        hole = _hole(w["from"]) or _hole(w["to"])
        uno = w["to"] if hole == w["from"] else w["from"]
        hole_by_uno[uno] = hole
    assert {pin: hole_by_uno[f"uno.T{i:02d}"] for i, pin in enumerate(pins)} \
        == L293D_HOLES_180
    f_cols = [int(L293D_HOLES_180[p][:-1]) for p in
              ("enable1", "input1", "output1", "gnd", "gnd1", "output2", "input2", "vs")]
    e_cols = [int(L293D_HOLES_180[p][:-1]) for p in
              ("vss", "input4", "output4", "gnd3", "gnd2", "output3", "input3", "enable2")]
    assert f_cols == list(range(17, 9, -1))
    assert e_cols == list(range(17, 9, -1))


def test_r9_fixture_real_caminos_vs_bateria_y_vss_5v_sin_intercambio():
    fixture = _fixture()
    assert len(fixture["nets"]) == 11
    assert plan_layout(fixture)["unplaced"] == []

    call = fixture_to_model_call(fixture)
    pairs = _wire_pairs(call)
    by_pair = {frozenset((w["from"], w["to"])): w["color"] for w in call["wires"]}

    # Camino completo (no solo presencia suelta): Vs=10f es Power 2 y lo
    # alimenta la bateria; Vss=17e es Power 1 y lo alimentan los 5V.
    assert frozenset(("bat1.+", "10f")) in pairs
    assert frozenset(("uno.5V", "17e")) in pairs
    assert by_pair[frozenset(("bat1.+", "10f"))] == "red"
    assert by_pair[frozenset(("uno.5V", "17e"))] == "red"
    # Los intercambiados serian el bug historico: bateria->Vss o 5V->Vs.
    assert frozenset(("bat1.+", "17e")) not in pairs
    assert frozenset(("uno.5V", "10f")) not in pairs

    pin_hole = {f"drv1.{p}": h for p, h in L293D_HOLES_180.items()}
    pin_hole.update({"bat1.positive": "bat1.+", "bat1.negative": "bat1.-",
                     "motor1.positive": "motor1.1", "motor1.negative": "motor1.2"})
    groups = _components_of_wires(call, pin_hole)
    # Tierra comun de 3 extremos de la fixture: GND1, drv1.gnd, bat1.negative.
    assert _same_group(groups, "uno.GND1", "drv1.gnd")
    assert _same_group(groups, "uno.GND1", "bat1.negative")
    assert _same_group(groups, "drv1.gnd", "bat1.negative")
    # Y cada alimentacion llega a SU pin, sin cortarse con la otra ni tierra.
    assert _same_group(groups, "bat1.positive", "drv1.vs")
    assert _same_group(groups, "uno.5V", "drv1.vss")
    assert not _same_group(groups, "bat1.positive", "uno.GND1")
    assert not _same_group(groups, "bat1.positive", "drv1.vss")
    assert not _same_group(groups, "uno.5V", "drv1.vs")


def test_r9_ningun_wire_f_e_misma_columna_salvo_puente_gnd_pedido():
    # Fixture real: ningun wire une directamente f con e de igual columna.
    call = fixture_to_model_call(_fixture())
    for w in call["wires"]:
        a, b = _hole(w["from"]), _hole(w["to"])
        if a and b:
            assert not (a[-1] == "f" and OPPOSITE[a] == b), w
            assert not (b[-1] == "f" and OPPOSITE[b] == a), w

    # Sintetica que SI pide todos los GND del chip en una sola net.
    # Contrato actualizado (fase 22): las nets de 3+ extremos se emparejan en
    # estrella desde el hub (aqui uno.GND1), no en cadena. Por eso ya no se
    # genera ningun cable gnd-gnd entre filas f/e; si apareciera uno, solo
    # seria admisible entre pines gnd*.
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "drv1", "type": "l293d"},
            {"ref": "bat1", "type": "battery-9v"},
        ],
        "nets": [[
            "uno.GND1", "drv1.gnd", "drv1.gnd1", "drv1.gnd2", "drv1.gnd3",
            "bat1.negative",
        ]],
    }
    call = fixture_to_model_call(fixture)
    pin_by_hole = {h: p for p, h in L293D_HOLES_180.items()}
    bridges = []
    for w in call["wires"]:
        a, b = _hole(w["from"]), _hole(w["to"])
        if a and b and {a[-1], b[-1]} == {"f", "e"} and a[:-1] == b[:-1]:
            bridges.append((a, b))
    assert not bridges  # todo cuelga de uno.GND1, sin cadenas internas
    for a, b in bridges:
        assert pin_by_hole[a].startswith("gnd")
        assert pin_by_hole[b].startswith("gnd")


def test_r9_segundo_l293d_sin_columnas_queda_fuera_y_builder_no_construye_a_medias():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "drv1", "type": "l293d"},
            {"ref": "drv2", "type": "l293d"},
        ],
        "nets": [["uno.D9", "drv1.enable1"], ["uno.D10", "drv2.enable1"]],
    }
    layout = plan_layout(fixture)
    assert layout["placements"]["drv1"] == {"at": "17f", "pin": "enable1", "angle": 180}
    assert layout["unplaced"] == ["drv2"]
    with pytest.raises(BuildError, match="drv2"):
        fixture_to_model_call(fixture)


# ------------------------------------------------------------- derive_nets

def _comp(type_, instance_id):
    return {"type": type_, "instance_id": instance_id, "name": "1", "pins": []}


def _ep(component, pin, instance_id):
    return {"component": component, "pin": pin, "instance_id": instance_id}


def _wire(source, target):
    return {"source": source, "target": target}


def test_r9_derive_nombres_internos_power1_no_es_power2_ni_filtra_a_otros_tipos():
    drv = "H-bridge Motor Driver [L293D]"
    # Power 2 cableado ANTES que Power 1 a proposito: un alias por prefijo
    # o por orden confundiria Vs (bateria) con Vss (logica 5V).
    data = {
        "components": [
            _comp(drv, "drv_a"), _comp("Arduino Uno R3", "uno1"),
            _comp("Resistor", "r_a"),
        ],
        "wires": [
            _wire(_ep(drv, "Power 2", "drv_a"), _ep("Arduino Uno R3", "A5", "uno1")),
            _wire(_ep(drv, "Power 1", "drv_a"), _ep("Arduino Uno R3", "5V", "uno1")),
            _wire(_ep(drv, "Enable 1 & 2", "drv_a"), _ep("Arduino Uno R3", "D9", "uno1")),
            _wire(_ep(drv, "Enable 3 & 4", "drv_a"), _ep("Arduino Uno R3", "D10", "uno1")),
            _wire(_ep(drv, "Input 1", "drv_a"), _ep("Arduino Uno R3", "D7", "uno1")),
            _wire(_ep(drv, "Output 1", "drv_a"), _ep("Arduino Uno R3", "D2", "uno1")),
            # Mismos literales en otro tipo: el alias es solo del L293D.
            _wire(_ep("Resistor", "Power 1", "r_a"), _ep("Arduino Uno R3", "D3", "uno1")),
            _wire(_ep("Resistor", "Power 2", "r_a"), _ep("Arduino Uno R3", "D4", "uno1")),
        ],
    }
    nets = derive_nets(data)
    assert ["l293d1.vs", "uno.A5"] in nets
    assert ["l293d1.vss", "uno.5V"] in nets
    assert ["l293d1.enable1", "uno.D9"] in nets
    assert ["l293d1.enable2", "uno.D10"] in nets
    assert ["l293d1.input1", "uno.D7"] in nets
    assert ["l293d1.output1", "uno.D2"] in nets
    assert ["r1.Power 1", "uno.D3"] in nets
    assert ["r1.Power 2", "uno.D4"] in nets
    flat = {ep for net in nets for ep in net}
    assert not any(ep.startswith("l293d1.") and (" " in ep or "&" in ep) for ep in flat)


_LIVE_PIN = {
    "drv1": {"enable1": "Enable 1 & 2", "enable2": "Enable 3 & 4",
             "vss": "Power 1", "vs": "Power 2", "input1": "Input 1",
             "input2": "Input 2", "input3": "Input 3", "input4": "Input 4",
             "output1": "Output 1", "output2": "Output 2",
             "output3": "Output 3", "output4": "Output 4",
             "gnd": "gnd", "gnd1": "gnd1", "gnd2": "gnd2", "gnd3": "gnd3"},
    "bat1": {"positive": "Positive", "negative": "Negative",
             "+": "Positive", "-": "Negative"},
    "motor1": {"positive": "Terminal 1", "negative": "Terminal 2",
               "1": "Terminal 1", "2": "Terminal 2"},
    "pot1": {"1": "Terminal 1", "2": "Wiper", "3": "Terminal 2"},
}
_LIVE_COMP = {
    "uno": ("Arduino Uno R3", "uno1"), "bb": ("Breadboard Small", "bb1"),
    "drv1": ("H-bridge Motor Driver [L293D]", "drv_a"),
    "bat1": ("9V Battery", "bat_a"), "motor1": ("DC Motor", "mot_a"),
    "pot1": ("Potentiometer", "pot_a"),
}


def _live_ep(endpoint):
    if _hole(endpoint):
        return _ep("Breadboard Small", endpoint, "bb1")
    ref, pin = endpoint.split(".", 1)
    if ref == "uno":
        return _ep("Arduino Uno R3", "GND" if pin == "GND1" else pin, "uno1")
    type_, inst = _LIVE_COMP[ref]
    return _ep(type_, _LIVE_PIN[ref][pin], inst)


def test_r9_roundtrip_180_builder_inspect_derive_fidelidad_1_sin_cruce_de_mitades():
    fixture = _fixture()
    call = fixture_to_model_call(fixture)
    wires = [_wire(_live_ep(w["from"]), _live_ep(w["to"])) for w in call["wires"]]
    # Pines clavados en sus huecos 180 (drv) y 1c..3c (pot).
    for pin, hole in L293D_HOLES_180.items():
        wires.append(_wire(_live_ep(f"drv1.{pin}"), _live_ep(hole)))
    for pin, hole in (("1", "1c"), ("2", "2c"), ("3", "3c")):
        wires.append(_wire(_live_ep(f"pot1.{pin}"), _live_ep(hole)))
    data = {
        "components": [_comp(t, i) for t, i in _LIVE_COMP.values()],
        "wires": wires,
    }
    nets = derive_nets(data)
    actual = {"components": normalize_circuit(data, {"nets": []})["components"],
              "nets": nets}
    result = compare_connectivity(fixture, actual)
    assert result["shorts"] == []
    assert result["score"] == 1.0

    def net_of(ep):
        return next((set(n) for n in nets if ep in n), set())

    # Misma columna, mitades distintas: jamas en la misma net derivada.
    assert net_of("l293d1.enable1") == {"l293d1.enable1", "uno.D9"}
    assert net_of("l293d1.vss") == {"l293d1.vss", "potentiometer1.1", "uno.5V"}
    assert net_of("l293d1.vs") == {"battery9v1.positive", "l293d1.vs"}
    assert net_of("l293d1.gnd") == {
        "battery9v1.negative", "l293d1.gnd", "potentiometer1.3", "uno.GND1",
    }
    for f_pin, e_pin in (("enable1", "vss"), ("vs", "enable2"),
                         ("input1", "input4"), ("output1", "output4")):
        assert f"l293d1.{e_pin}" not in net_of(f"l293d1.{f_pin}")


# ------------------------------------------------------------------ runner

def _inspect_blink(wires_kind="full"):
    uno, r, led = ("Arduino Uno R3", "uno1"), ("Resistor", "r_a"), ("LED", "led_a")

    def e(comp, pin):
        return _ep(comp[0], pin, comp[1])

    wires = [
        _wire(e(uno, "D13"), e(r, "Terminal 1")),
        _wire(e(r, "Terminal 2"), e(led, "Anode")),
        _wire(e(led, "Cathode"), e(uno, "GND")),
    ]
    if wires_kind == "missing":
        wires = wires[:-1]
    elif wires_kind == "empty":
        wires = []
    elif wires_kind == "short":
        wires = wires + [_wire(e(uno, "D13"), e(uno, "GND"))]
    return {"components": [_comp(*uno), _comp(*r), _comp(*led)], "wires": wires}


def _fake(inspect_sequence, build_outputs=None, preset_output=None):
    calls = []
    state = {"inspect": 0, "build": 0}

    def call_tool(tool, arguments):
        calls.append((tool, arguments))
        if tool == "tinkercad_create_circuit":
            return json.dumps({"circuit_id": CID})
        if tool == "tinkercad_build_circuit_model":
            if build_outputs:
                out = build_outputs[min(state["build"], len(build_outputs) - 1)]
                state["build"] += 1
                return out
            return json.dumps({"success": True, "persisted": True})
        if tool == "tinkercad_set_component_property_model" and preset_output is not None:
            return preset_output
        if tool == "tinkercad_inspect_circuit":
            idx = min(state["inspect"], len(inspect_sequence) - 1)
            state["inspect"] += 1
            return json.dumps(inspect_sequence[idx])
        if tool == "tinkercad_read_serial_monitor":
            return "ok\n"
        return json.dumps({"success": True})

    call_tool.calls = calls
    return call_tool


def _tools(call_tool):
    return [t for t, _ in call_tool.calls]


def test_r9_con_cortos_no_hay_segundo_build_ni_segundo_inspect():
    fixture = _fixture("blink-basico")
    call_tool = _fake([_inspect_blink("short")])

    result = run_build(fixture, None, call_tool, "r9 corto")

    assert result["fidelity"]["shorts"]
    assert result["repair_attempted"] is False
    assert result["fidelity_before_repair"] is None
    assert result["ok"] is False
    assert _tools(call_tool).count("tinkercad_build_circuit_model") == 1
    assert _tools(call_tool).count("tinkercad_inspect_circuit") == 1
    assert _tools(call_tool).count("tinkercad_open_circuit") == 1


def test_r9_repair_que_empeora_reporta_la_final_y_conserva_la_primera():
    fixture = _fixture("blink-basico")
    call_tool = _fake([_inspect_blink("missing"), _inspect_blink("empty")])

    result = run_build(fixture, None, call_tool, "r9 empeora")

    assert result["repair_attempted"] is True
    builds = [a for t, a in call_tool.calls if t == "tinkercad_build_circuit_model"]
    assert len(builds) == 2
    assert builds[1] == {"parts": [], "wires": fixture_to_model_call(fixture)["wires"]}
    before, final = result["fidelity_before_repair"], result["fidelity"]
    assert before["connectivity_score"] == pytest.approx(2 / 3)
    assert before["score"] > final["score"]
    # La reportada es la peor real (la del reintento), no la mejor.
    assert final["connectivity_score"] == 0.0
    assert final["score"] == pytest.approx(0.5)
    assert result["ok"] is False


def test_r9_preset_success_false_en_json_no_aborta_pero_queda_como_fallo_en_records():
    # Contrato del docstring: un preset que falla "queda en records y no
    # aborta". Un JSON {"success": false} es un fallo del preset: debe
    # verse como record fallido, no como un paso ok mas.
    fixture = _fixture("blink-basico")
    call_tool = _fake(
        [_inspect_blink()],
        preset_output=json.dumps({"success": False, "error": "propiedad invalida"}),
    )
    presets = [{"component": "Comp X", "property": "Nope", "value": 1}]

    result = run_build(fixture, None, call_tool, "r9 preset", presets=presets)

    tools = _tools(call_tool)
    assert tools.count("tinkercad_inspect_circuit") == 1  # no aborto
    assert "tinkercad_start_simulation" in tools
    preset_records = [
        r for r in result["records"]
        if r.tool == "tinkercad_set_component_property_model"
    ]
    assert len(preset_records) == 1
    assert preset_records[0].ok is False


def test_r9_segundo_build_de_repair_con_success_false_no_puede_dar_ok():
    # Como el primer build (test existente): success:false obliga ok=False
    # aunque la re-medicion salga perfecta. El re-cableado tambien es un
    # build: su success:false no puede quedar invisible.
    fixture = _fixture("blink-basico")
    call_tool = _fake(
        [_inspect_blink("missing"), _inspect_blink()],
        build_outputs=[
            json.dumps({"success": True, "persisted": True}),
            json.dumps({"success": False, "error": "repair no persistio"}),
        ],
    )

    result = run_build(fixture, None, call_tool, "r9 repair roto")

    assert result["repair_attempted"] is True
    assert result["fidelity"]["score"] == 1.0
    assert result["ok"] is False
