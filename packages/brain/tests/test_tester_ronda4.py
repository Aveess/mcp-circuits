"""Tester independiente ronda 4: breadboard_nets / verifier / builder.

Adversarial, sin repetir las suites existentes. Los tests con prefijo
test_BUG_ documentan un fallo esperado: deben fallar hasta que
produccion se corrija (bug = test que falla + reporte).
"""
import json
import re
from pathlib import Path

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import build_circuit, fixture_to_model_call
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.verifier import evaluate_contract

ROOT = Path(__file__).resolve().parents[1]
REAL_FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"
HOLE_RE = re.compile(r"^([1-9]|[12][0-9]|30)[a-j]$")


def _fixture(fixture_id):
    circuits = json.loads(REAL_FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == fixture_id)


def _comp(type_, instance_id):
    return {"type": type_, "instance_id": instance_id, "name": "1", "pins": []}


def _ep(comp, pin):
    return {"component": comp[0], "pin": pin, "instance_id": comp[1]}


def _wire(source, target):
    return {"source": source, "target": target}


# ------------------------------------------------------------- derive_nets
def test_r4_sin_protoboard_blink_directo_deriva_las_tres_nets():
    # Primer blink sin placa: wires directos componente<->componente.
    uno, r, led = ("Arduino Uno R3", "u1"), ("Resistor", "r_a"), ("LED", "l_a")
    data = {
        "components": [_comp(*uno), _comp(*r), _comp(*led)],
        "wires": [
            _wire(_ep(uno, "D13"), _ep(r, "Terminal 1")),
            _wire(_ep(r, "Terminal 2"), _ep(led, "Anode")),
            _wire(_ep(led, "Cathode"), _ep(uno, "GND")),
        ],
    }
    assert derive_nets(data) == [
        ["led1.anode", "r1.2"],
        ["led1.cathode", "uno.GND1"],
        ["r1.1", "uno.D13"],
    ]


def test_r4_mitades_solo_se_unen_con_cable_explicito_entre_huecos():
    uno, bb, r = ("Arduino Uno R3", "u1"), ("Breadboard Small", "bb1"), ("Resistor", "r_a")
    base = {
        "components": [_comp(*uno), _comp(*bb), _comp(*r)],
        "wires": [
            _wire(_ep(uno, "D13"), _ep(bb, "i1")),   # mitad superior, col 1
            _wire(_ep(r, "Terminal 1"), _ep(bb, "a1")),  # mitad inferior, col 1
        ],
    }
    # Misma columna, mitades distintas, sin puente: no hay net (singleton fuera).
    assert derive_nets(base) == []
    # Solo el cable explicito hueco<->hueco cruza el canal central.
    bridged = json.loads(json.dumps(base))
    bridged["wires"].append(_wire(_ep(bb, "e1"), _ep(bb, "f1")))
    assert derive_nets(bridged) == [["r1.1", "uno.D13"]]


def test_r4_dos_rieles_de_letras_distintas_no_se_mezclan():
    uno, bb = ("Arduino Uno R3", "u1"), ("Breadboard Small", "bb1")
    r, led = ("Resistor", "r_a"), ("LED", "l_a")
    data = {
        "components": [_comp(*uno), _comp(*bb), _comp(*r), _comp(*led)],
        "wires": [
            _wire(_ep(uno, "D13"), _ep(bb, "z1")),
            _wire(_ep(r, "Terminal 1"), _ep(bb, "z9")),
            _wire(_ep(uno, "GND"), _ep(bb, "y1")),
            _wire(_ep(led, "Cathode"), _ep(bb, "y9")),
        ],
    }
    # Si el riel ignorara la letra, saldria una unica net de 4 extremos.
    assert derive_nets(data) == [
        ["led1.cathode", "uno.GND1"],
        ["r1.1", "uno.D13"],
    ]


def test_r4_inspect_sin_wires_devuelve_vacio_sin_reventar():
    comps = [_comp("LED", "l_a")]
    assert derive_nets({"components": comps}) == []
    assert derive_nets({"components": comps, "wires": None}) == []
    assert derive_nets({"components": comps, "wires": []}) == []


def test_BUG_r4_endpoint_de_tipo_desconocido_no_debe_inventar_endpoint():
    """Un endpoint que no esta en components no es un nodo real: hoy se
    fabrica un ref (p. ej. 'mysterygadget1.Data') y una net falsa."""
    data = {
        "components": [_comp("Arduino Uno R3", "u1")],
        "wires": [
            _wire(
                _ep(("Arduino Uno R3", "u1"), "D13"),
                _ep(("Mystery Gadget", "ghost"), "Data"),
            )
        ],
    }
    assert derive_nets(data) == []


def test_BUG_r4_endpoint_con_instance_id_fantasma_no_debe_crear_otro_led():
    """instance_id ausente en components con tipo conocido: hoy se asigna
    un ref nuevo (led2) en vez de descartar el endpoint no identificado."""
    data = {
        "components": [_comp("Arduino Uno R3", "u1"), _comp("LED", "led_real")],
        "wires": [
            _wire(
                _ep(("Arduino Uno R3", "u1"), "D13"),
                _ep(("LED", "ghost_no_declarado"), "Anode"),
            )
        ],
    }
    assert derive_nets(data) == []


# -------------------------------------------------------- evaluate_contract
def _sim_cercano():
    return {
        "samples": [
            {"at_ms": 249, "leds": {"led1": {"on": True, "level": 0.9}}},
            {"at_ms": 251, "leds": {"led1": {"on": True, "level": 0.9}}},
        ],
        "serial": None,
    }


def test_r4_led_at_ms_inexacto_falla_aunque_haya_muestras_cercanas():
    contract = {"assertions": [
        {"type": "led", "ref": "led1", "at_ms": 250, "expect_on": True},
    ]}
    out = evaluate_contract(contract, _sim_cercano())
    assert out["passed"] is False
    assert out["results"][0]["ok"] is False
    assert "250" in out["results"][0]["detail"]


def test_r4_sim_result_sin_samples_no_revienta_y_falla():
    out = evaluate_contract(
        {"assertions": [{"type": "led", "ref": "led1", "at_ms": 250, "expect_on": True}]},
        {"serial": "READY"},
    )
    assert out["passed"] is False
    assert out["results"][0]["ok"] is False


def test_r4_serial_none_no_revienta_y_falla():
    out = evaluate_contract(
        {"assertions": [{"type": "serial_contains", "text": "READY"}]},
        _sim_cercano(),
    )
    assert out["passed"] is False
    assert out["results"][0]["ok"] is False


def test_r4_tolerancia_negativa_nunca_pasa_ni_con_angulo_exacto():
    sim = {"samples": [{"at_ms": 0, "servos": {"s1": 90}}]}
    out = evaluate_contract(
        {"assertions": [
            {"type": "servo", "ref": "s1", "at_ms": 0, "angle": 90, "tolerance": -1},
        ]},
        sim,
    )
    assert out["passed"] is False
    assert out["results"][0]["ok"] is False


def test_r4_assertions_que_no_es_lista_no_verifica_nada():
    for bad in ({"type": "led"}, "led", 42):
        out = evaluate_contract({"assertions": bad}, _sim_cercano())
        assert out["passed"] is False
        assert out["results"] == []


# ------------------------------------------------------------------ builder
def test_r4_semaforo_tres_ramas_sin_colision_y_nueve_nets_cubiertas():
    fixture = _fixture("semaforo-3-leds")
    result = fixture_to_model_call(fixture, code="void setup() {}")
    placements = plan_layout(fixture)["placements"]

    assert len(result["parts"]) == 6  # 3 LED + 3 resistencias, uno no es part
    assert {p["ref"] for p in result["parts"]} == {
        "led_rojo", "led_amarillo", "led_verde", "r1", "r2", "r3",
    }
    anchors = [p["at"] for p in result["parts"]]
    assert len(anchors) == len(set(anchors)), f"anclas repetidas: {anchors}"
    assert anchors == [placements[p["ref"]]["at"] for p in result["parts"]]

    # 9 nets de 2 extremos -> exactamente 9 wires, todos huecos/uno validos.
    assert len(fixture["nets"]) == 9
    assert len(result["wires"]) == 9
    for w in result["wires"]:
        for end in (w["from"], w["to"]):
            assert end.startswith("uno.") or HOLE_RE.match(end), end


def test_r4_catodo_directo_a_gnd_genera_wire_a_hueco_valido():
    fixture = _fixture("blink-basico")
    result = fixture_to_model_call(fixture)
    cathode_wires = [w for w in result["wires"] if w["to"] == "uno.GND1"]
    assert len(cathode_wires) == 1
    hole = cathode_wires[0]["from"]
    assert HOLE_RE.match(hole)
    # Catodo = anodo (at del LED) desplazado una columna, misma fila.
    led_at = plan_layout(fixture)["placements"]["led1"]["at"]
    assert hole == f"{int(led_at[:-1]) + 1}{led_at[-1]}"


def test_r4_build_circuit_excepcion_en_paso1_queda_ok_false_sin_reventar():
    calls = []

    def exploding_call_tool(tool, arguments):
        calls.append(tool)
        if tool == "tinkercad_build_circuit_model":
            raise RuntimeError("bridge exploded step1")
        return json.dumps({"components": []})

    result = build_circuit(_fixture("blink-basico"), None, exploding_call_tool)

    # Comportamiento esperado segun probe.run_steps: registra y sigue.
    assert calls == ["tinkercad_build_circuit_model", "tinkercad_inspect_circuit"]
    assert len(result["records"]) == 2
    assert result["records"][0].ok is False
    assert "bridge exploded step1" in result["records"][0].output
    assert result["records"][1].ok is True
    assert result["model_result"] == "bridge exploded step1"


# ------------------------------------------------------- consistencia cruzada
def test_r4_blink_wires_coinciden_con_placements():
    fixture = _fixture("blink-basico")
    placements = plan_layout(fixture)["placements"]
    result = fixture_to_model_call(fixture)
    wires = result["wires"]

    r_at = placements["r1"]["at"]          # pin 1 de r1
    led_at = placements["led1"]["at"]      # anodo de led1
    r_pin2 = f"{int(r_at[:-1]) + 4}{r_at[-1]}"
    led_cathode = f"{int(led_at[:-1]) + 1}{led_at[-1]}"

    # El wire al hueco del anodo debe ser exactamente el `at` del LED, etc.
    assert wires == [
        {"from": led_cathode, "to": "uno.GND1", "color": "black"},
        {"from": r_pin2, "to": led_at, "color": "blue"},
        {"from": "uno.D13", "to": r_at, "color": "green"},
    ]
    # Ningun part comparte hueco ancla con el extremo derivado de otro pin.
    derived = {r_pin2, led_cathode}
    assert derived.isdisjoint({r_at, led_at})
