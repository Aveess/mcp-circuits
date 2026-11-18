"""Tester independiente ronda 3: adversarial spec/layout.

No repite test_spec.py ni test_layout.py: ataca extremos como wire (no
como at), variantes de orden en layout y consistencia spec<->layout.
Los test con prefijo test_BUG_ documentan un fallo esperado: deben
fallar hasta que produccion se corrija (bug = test que falla).
"""
import json
import re
from pathlib import Path

import pytest

from tinkercad_brain.layout import LayoutError, plan_layout
from tinkercad_brain.spec import SpecError, validate_spec

ROOT = Path(__file__).resolve().parents[1]
REAL_FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture(fixture_id):
    circuits = json.loads(REAL_FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == fixture_id)


def _base_spec():
    return {
        "title": "Blink",
        "parts": [
            {"ref": "led1", "type": "led", "at": "9i", "pin": "anode", "angle": 180},
            {"ref": "r1", "type": "resistor", "at": "5i", "pin": "1"},
        ],
        "wires": [["uno.D13", "5i"]],
        "code": "void setup() {}",
    }


# ---------------------------------------------------------------- spec: wires
@pytest.mark.parametrize(
    "endpoint",
    ["0a", "31a", "1k", "30k", "01a", "1A", "T-31", "T+31", "B-0", "X+", "X-12",
     "t-12", "T- 12", "5i ", " led1.anode", "led1.anode.extra", "uno.D13.extra"],
)
def test_r3_wire_endpoint_invalido_rechazado(endpoint):
    spec = _base_spec()
    spec["wires"] = [[endpoint, "5i"]]
    with pytest.raises(SpecError):
        validate_spec(spec)


@pytest.mark.parametrize("endpoint", ["led1.", "led1. ", "led1.  ", "r1."])
def test_r3_wire_ref_declarado_pin_vacio_rechazado(endpoint):
    spec = _base_spec()
    spec["wires"] = [[endpoint, "5i"]]
    with pytest.raises(SpecError):
        validate_spec(spec)


@pytest.mark.parametrize(
    "wire",
    [["uno.D13", "5i", "9i"], [], ["uno.D13"], "uno.D13", 42, None,
     {"from": "uno.D13"}, {"to": "5i"}, {"from": "uno.D13", "to": 5}],
)
def test_r3_wire_malformado_rechazado(wire):
    spec = _base_spec()
    spec["wires"] = [wire]
    with pytest.raises(SpecError):
        validate_spec(spec)


@pytest.mark.parametrize("endpoint", [123, None, True, ["5i"], {"x": 1}])
def test_r3_wire_endpoint_no_string_rechazado(endpoint):
    spec = _base_spec()
    spec["wires"] = [[endpoint, "5i"]]
    with pytest.raises(SpecError):
        validate_spec(spec)


@pytest.mark.parametrize("spec", ["texto", [], None, 42, 3.5, True])
def test_r3_spec_no_dict_rechazado(spec):
    with pytest.raises(SpecError):
        validate_spec(spec)


@pytest.mark.parametrize("at", [12, None, True, ["9i"], {"hole": "9i"}])
def test_r3_at_no_string_rechazado(at):
    spec = _base_spec()
    spec["parts"] = [{"ref": "led1", "type": "led", "at": at}]
    spec["wires"] = []
    with pytest.raises(SpecError):
        validate_spec(spec)


@pytest.mark.parametrize("pin", [True, False, "", "   "])
def test_r3_part_pin_invalido_rechazado(pin):
    spec = _base_spec()
    spec["parts"] = [{"ref": "r1", "type": "resistor", "at": "1a", "pin": pin}]
    spec["wires"] = []
    with pytest.raises(SpecError):
        validate_spec(spec)


def test_r3_huecos_borde_validos_como_wire():
    spec = _base_spec()
    spec["wires"] = [["1a", "30j"], ["T+30", "B-1"], ["T-", "B+"]]
    out = validate_spec(spec)
    assert len(out["wires"]) == 3


# ------------------------------------------------------- spec: bugs (fallan)
@pytest.mark.parametrize("code", [123, None, ["void"], {"src": "x"}, True])
def test_BUG_r3_code_no_string_debe_rechazarse(code):
    """Docstring de spec.py declara 'code': str; hoy se acepta cualquier cosa."""
    spec = _base_spec()
    spec["code"] = code
    with pytest.raises(SpecError):
        validate_spec(spec)


@pytest.mark.parametrize("title", [123, None, ["Blink"]])
def test_BUG_r3_title_no_string_debe_rechazarse(title):
    spec = _base_spec()
    spec["title"] = title
    with pytest.raises(SpecError):
        validate_spec(spec)


@pytest.mark.parametrize("angle", [45, 360, -90, 1, "90", None, True])
def test_BUG_r3_angle_fuera_de_0_90_180_270_debe_rechazarse(angle):
    """El planner solo emite 0/90/180; la spec deberia validar el mismo set."""
    spec = _base_spec()
    spec["parts"][0]["angle"] = angle
    with pytest.raises(SpecError):
        validate_spec(spec)


def test_BUG_r3_part_con_at_y_free_a_la_vez_debe_rechazarse():
    """El formato declara 'at'|'free' (excluyentes); hoy se aceptan ambos."""
    spec = _base_spec()
    spec["parts"][0]["free"] = {"x": 1, "y": 2}
    with pytest.raises(SpecError):
        validate_spec(spec)


def test_BUG_r3_dos_parts_en_el_mismo_hueco_debe_rechazarse():
    """Colision fisica: layout garantiza anclas unicas, el validador no."""
    spec = _base_spec()
    spec["parts"] = [
        {"ref": "led1", "type": "led", "at": "5i", "pin": "anode"},
        {"ref": "r1", "type": "resistor", "at": "5i", "pin": "1"},
    ]
    spec["wires"] = []
    with pytest.raises(SpecError):
        validate_spec(spec)


# ------------------------------------------------------------------- layout
def test_r3_fixture_sin_nets_no_revienta():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "r1", "type": "resistor"},
        ]
    }
    result = plan_layout(fixture)
    assert result["placements"]["led1"] == {"at": "5i", "pin": "anode", "angle": 180}
    assert result["placements"]["r1"] == {"at": "7g", "pin": "1", "angle": 90}
    assert result["unplaced"] == []


def test_r3_fixture_nets_none_no_revienta():
    fixture = {
        "components": [{"ref": "led1", "type": "led"}],
        "nets": None,
    }
    result = plan_layout(fixture)
    assert result["placements"]["led1"]["at"] == "5i"


def test_r3_led_resistencia_por_pin1_resistor_primero_mismo_bloque():
    # Variante no cubierta: r aparece antes que el LED en components.
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "r1", "type": "resistor"},
            {"ref": "led1", "type": "led"},
        ],
        "nets": [["led1.anode", "r1.1"]],
    }
    result = plan_layout(fixture)
    assert result["placements"]["r1"] == {"at": "1g", "pin": "1", "angle": 90}
    assert result["placements"]["led1"] == {"at": "5i", "pin": "anode", "angle": 180}
    assert result["unplaced"] == []


def test_r3_cuatro_leds_y_boton_columna_valida_y_anclas_unicas():
    components = [
        {"ref": "uno", "type": "arduino-uno"},
        {"ref": "btn1", "type": "pushbutton"},
    ]
    nets = []
    for i in range(1, 5):
        components += [
            {"ref": f"led{i}", "type": "led"},
            {"ref": f"r{i}", "type": "resistor"},
        ]
        nets.append([f"r{i}.2", f"led{i}.anode"])
    result = plan_layout({"components": components, "nets": nets})
    btn = result["placements"]["btn1"]
    column = int(re.match(r"(\d+)", btn["at"]).group(1))
    assert 1 <= column <= 30
    assert btn == {"at": "25f", "pin": "1", "angle": 0}
    anchors = [p["at"] for p in result["placements"].values()]
    assert len(anchors) == len(set(anchors))
    assert result["unplaced"] == []


def test_r3_boton_tras_bloques_no_duplica_ancla_de_bloque_led():
    fixture = _fixture("boton-pullup")
    result = plan_layout(fixture)
    anchors = [p["at"] for p in result["placements"].values()]
    assert len(anchors) == len(set(anchors))
    led_leds = [p["at"] for r, p in result["placements"].items() if r.startswith("led")]
    assert result["placements"]["btn1"]["at"] not in led_leds


# ------------------------------------------------------- layout: bugs (fallan)
def test_BUG_r3_dos_leds_compartiendo_resistencia_segundo_sin_proteccion():
    """Una sola r en las nets de led1 y led2: led2 no debe colocarse como
    si tuviera resistencia serie; debe ir a unplaced (o LayoutError)."""
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "led2", "type": "led"},
            {"ref": "r1", "type": "resistor"},
        ],
        "nets": [["r1.2", "led1.anode"], ["r1.2", "led2.anode"]],
    }
    result = plan_layout(fixture)
    assert "led2" in result["unplaced"]
    assert "led2" not in result["placements"]


@pytest.mark.parametrize(
    "components",
    [
        [{"ref": "led1", "type": "led"}, {"ref": "led1", "type": "led"},
         {"ref": "r1", "type": "resistor"}],
        [{"ref": "led1", "type": "led"}, {"ref": "led1", "type": "resistor"}],
        [{"ref": "r1", "type": "resistor"}, {"ref": "r1", "type": "resistor"}],
    ],
)
def test_BUG_r3_components_ref_duplicado_debe_rechazarse(components):
    """Hoy el dict por ref colapsa duplicados y sobrescribe placements."""
    fixture = {"components": components, "nets": [["r1.2", "led1.anode"]]}
    with pytest.raises(LayoutError):
        plan_layout(fixture)


@pytest.mark.parametrize("nets", ["led1.anode", {"led1": "r1"}, 42])
def test_BUG_r3_nets_no_lista_debe_rechazarse(nets):
    """nets con tipo erroneo hoy se ignora en silencio (string itera chars)."""
    fixture = {"components": [{"ref": "led1", "type": "led"}], "nets": nets}
    with pytest.raises(LayoutError):
        plan_layout(fixture)


# ------------------------------------------------- consistencia spec<->layout
def _spec_desde_plan(fixture):
    plan = plan_layout(fixture)
    type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}
    parts = [
        {"ref": ref, "type": type_by_ref[ref], "at": p["at"],
         "pin": p["pin"], "angle": p["angle"]}
        for ref, p in plan["placements"].items()
    ]
    return {"title": fixture.get("title", "x"), "parts": parts,
            "wires": fixture.get("nets", []), "code": "void setup() {}"}, plan


def test_r3_consistencia_blink_salida_del_planner_es_spec_valida():
    spec, plan = _spec_desde_plan(_fixture("blink-basico"))
    assert plan["unplaced"] == []
    out = validate_spec(spec)
    assert {p["ref"] for p in out["parts"]} == {"led1", "r1"}


def test_r3_consistencia_boton_salida_del_planner_es_spec_valida():
    spec, plan = _spec_desde_plan(_fixture("boton-pullup"))
    assert plan["unplaced"] == []
    out = validate_spec(spec)
    assert {p["ref"] for p in out["parts"]} == {"led1", "r1", "btn1"}
