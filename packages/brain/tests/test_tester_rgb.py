"""Tester independiente, ronda RGB. No repetir fixtures de los tests de
desarrollo: aqui se sigue el camino completo net -> resistencia -> hueco
y se cruzan layout, builder, derive_nets, sketch y CLI entre si.
"""
import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import BuildError, fixture_to_model_call
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.sketches import rgb_cycle_sketch

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = json.loads((ROOT / "fixtures/fase0/circuits.json").read_text(encoding="utf-8"))
RGB_FIXTURE = next(f for f in FIXTURES if f["id"] == "led-rgb")

# Orden fisico del DID 58456: red, cathode, BLUE, GREEN (azul antes que verde).
PHYSICAL_ORDER = ("red", "cathode", "blue", "green")


def _shift(hole, cols):
    m = re.fullmatch(r"(\d+)([a-j])", hole)
    return f"{int(m.group(1)) + cols}{m.group(2)}"


def _fixture_rgb_pin(fixture, color):
    """Pin del Uno que alimenta `color` segun las nets de la fixture."""
    resistor = None
    for net in fixture["nets"]:
        if f"rgb1.{color}" in net:
            resistor = next(e.split(".")[0] for e in net if e.endswith(".2"))
    for net in fixture["nets"]:
        if f"{resistor}.1" in net:
            return next(e for e in net if e.startswith("uno."))
    raise AssertionError(f"sin pin Uno para {color}")


# --- La trampa verde/azul: camino completo pin a pin -----------------------

def test_full_path_green_is_at_plus3_and_blue_at_plus2_on_real_fixture():
    layout = plan_layout(copy.deepcopy(RGB_FIXTURE))
    at = layout["placements"]["rgb1"]["at"]
    assert layout["placements"]["rgb1"]["pin"] == "red"
    holes = {color: _shift(at, i) for i, color in enumerate(PHYSICAL_ORDER)}

    model = fixture_to_model_call(copy.deepcopy(RGB_FIXTURE))
    wires = {(w["from"], w["to"]) for w in model["wires"]}
    placements = layout["placements"]

    def pin2(ref):
        return _shift(placements[ref]["at"], 4)

    # Fixture real: D9->r1->red, D10->r2->green, D11->r3->blue.
    assert _fixture_rgb_pin(RGB_FIXTURE, "red") == "uno.D9"
    assert _fixture_rgb_pin(RGB_FIXTURE, "green") == "uno.D10"
    assert _fixture_rgb_pin(RGB_FIXTURE, "blue") == "uno.D11"

    assert ("uno.D10", placements["r2"]["at"]) in wires
    assert (pin2("r2"), holes["green"]) in wires
    assert holes["green"] == _shift(at, 3)

    assert ("uno.D11", placements["r3"]["at"]) in wires
    assert (pin2("r3"), holes["blue"]) in wires
    assert holes["blue"] == _shift(at, 2)

    assert ("uno.D9", placements["r1"]["at"]) in wires
    assert (pin2("r1"), holes["red"]) in wires
    assert (holes["cathode"], "uno.GND1") in wires
    assert holes["green"] != holes["blue"]


def test_builder_part_anchor_is_terminal_red_with_rgb_did():
    model = fixture_to_model_call(copy.deepcopy(RGB_FIXTURE))
    rgb = next(p for p in model["parts"] if p["ref"] == "rgb1")
    assert rgb["did"] == 58456
    assert rgb["pin"] == "terminal-red"
    assert rgb["at"] == plan_layout(copy.deepcopy(RGB_FIXTURE))["placements"]["rgb1"]["at"]


# --- Layout adversarial -----------------------------------------------------

def test_layout_color_follows_nets_not_ref_names_or_component_order():
    # Refs y orden elegidos para engañar a una asignacion por nombre/orden:
    # el primer resistor listado es el del azul, el ultimo el del rojo.
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "rgb1", "type": "led-rgb-common-cathode"},
            {"ref": "raaa", "type": "resistor"},
            {"ref": "rmmm", "type": "resistor"},
            {"ref": "rzzz", "type": "resistor"},
        ],
        "nets": [
            ["rzzz.2", "rgb1.blue"],
            ["rmmm.2", "rgb1.green"],
            ["raaa.2", "rgb1.red"],
            ["rgb1.cathode", "uno.GND1"],
        ],
    }
    result = plan_layout(fixture)
    assert result["unplaced"] == []
    base = int(re.match(r"\d+", result["placements"]["rgb1"]["at"]).group())
    row_of = {ref: p["at"][-1] for ref, p in result["placements"].items()}
    assert row_of["raaa"] == "g"   # rojo
    assert row_of["rmmm"] == "h"   # verde
    assert row_of["rzzz"] == "j"   # azul
    # El pin 2 de cada resistencia cae en la columna de su color fisico.
    pin_col = {"raaa": base, "rmmm": base + 3, "rzzz": base + 2}
    for ref, col in pin_col.items():
        at = result["placements"][ref]["at"]
        assert int(re.match(r"\d+", at).group()) + 4 == col


def test_layout_shared_resistor_for_two_colors_is_fully_unplaced():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "rgb1", "type": "led-rgb-common-cathode"},
            {"ref": "rshared", "type": "resistor"},
            {"ref": "rblue", "type": "resistor"},
        ],
        "nets": [
            ["uno.D9", "rshared.1"], ["rshared.2", "rgb1.red"],
            ["uno.D10", "rshared.1"], ["rshared.2", "rgb1.green"],
            ["uno.D11", "rblue.1"], ["rblue.2", "rgb1.blue"],
            ["rgb1.cathode", "uno.GND1"],
        ],
    }
    result = plan_layout(copy.deepcopy(fixture))
    assert result["placements"] == {}
    assert set(result["unplaced"]) == {"rgb1", "rshared", "rblue"}
    with pytest.raises(BuildError):
        fixture_to_model_call(fixture)


def test_layout_rgb_after_four_led_blocks_is_unplaced_without_stomping():
    components = [{"ref": "uno", "type": "arduino-uno"}]
    nets = []
    for k in range(1, 5):
        components += [
            {"ref": f"led{k}", "type": "led"},
            {"ref": f"rl{k}", "type": "resistor"},
        ]
        nets += [[f"rl{k}.2", f"led{k}.anode"], [f"led{k}.cathode", "uno.GND1"]]
    components += [{"ref": "rgb1", "type": "led-rgb-common-cathode"}] + [
        {"ref": f"r{i}", "type": "resistor"} for i in (1, 2, 3)
    ]
    nets += [["r1.2", "rgb1.red"], ["r2.2", "rgb1.green"], ["r3.2", "rgb1.blue"]]

    result = plan_layout({"components": components, "nets": nets})

    assert set(result["unplaced"]) == {"rgb1", "r1", "r2", "r3"}
    # Los 4 bloques LED quedan intactos en sus bloques de 6 columnas.
    for k in range(1, 5):
        start = 1 + 6 * (k - 1)
        assert result["placements"][f"rl{k}"]["at"] == f"{start}g"
        assert result["placements"][f"led{k}"]["at"] == f"{start + 4}i"
    anchors = [p["at"] for p in result["placements"].values()]
    assert len(anchors) == len(set(anchors)) == 8


def test_layout_rgb_and_its_resistors_share_no_hole():
    layout = plan_layout(copy.deepcopy(RGB_FIXTURE))
    placements = layout["placements"]
    occupied = []
    for i in range(4):
        occupied.append(_shift(placements["rgb1"]["at"], i))
    for ref in ("r1", "r2", "r3"):
        occupied.append(placements[ref]["at"])          # pin 1
        occupied.append(_shift(placements[ref]["at"], 4))  # pin 2
    assert len(occupied) == 10
    assert len(set(occupied)) == 10
    anchor_holes = [p["at"] for p in placements.values()]
    assert len(set(anchor_holes)) == 4


# --- derive_nets: LED comun + RGB en el mismo circuito ----------------------

def _ep(comp, pin, iid):
    return {"component": comp, "pin": pin, "instance_id": iid}


def _comp(type_, iid):
    return {"type": type_, "instance_id": iid, "name": "x", "pins": []}


def test_derive_nets_common_led_and_rgb_do_not_contaminate_each_other():
    bb, uno, led, rgb = "Breadboard Small", "Arduino Uno R3", "LED", "LED RGB"
    data = {
        "components": [
            _comp(uno, "u1"), _comp(bb, "bb1"), _comp(led, "l1"), _comp(rgb, "g1"),
        ],
        "wires": [
            {"source": _ep(rgb, "Red", "g1"), "target": _ep(uno, "D9", "u1")},
            {"source": _ep(rgb, "Green", "g1"), "target": _ep(uno, "D10", "u1")},
            {"source": _ep(rgb, "Blue", "g1"), "target": _ep(uno, "D11", "u1")},
            {"source": _ep(led, "Anode", "l1"), "target": _ep(uno, "D13", "u1")},
            # Ambas catodos a tierra por la misma columna alta del protoboard.
            {"source": _ep(led, "Cathode", "l1"), "target": _ep(bb, "j20", "bb1")},
            {"source": _ep(rgb, "Cathode", "g1"), "target": _ep(bb, "f20", "bb1")},
            {"source": _ep(bb, "j20", "bb1"), "target": _ep(bb, "z20", "bb1")},
            {"source": _ep(uno, "GND", "u1"), "target": _ep(bb, "z1", "bb1")},
        ],
    }
    nets = derive_nets(data)
    by_uno = {}
    for net in nets:
        for ep_ in net:
            if ep_.startswith("uno."):
                by_uno.setdefault(ep_, net)

    def suffixes(net):
        return {e.rsplit(".", 1)[1] for e in net if not e.startswith("uno.")}

    assert suffixes(by_uno["uno.D9"]) == {"red"}
    assert suffixes(by_uno["uno.D10"]) == {"green"}
    assert suffixes(by_uno["uno.D11"]) == {"blue"}
    # El LED comun conserva su identidad: anode en D13, sin .red/.green/.blue.
    assert by_uno["uno.D13"] == ["led1.anode", "uno.D13"]
    ground = by_uno["uno.GND1"]
    assert "led1.cathode" in ground
    assert any(e.endswith(".cathode") and not e.startswith(("led1", "uno")) for e in ground)
    assert not any(e.endswith((".red", ".green", ".blue", ".anode")) for e in ground)
    assert not any(e.endswith((".Red", ".Green", ".Blue")) for n in nets for e in n)


# --- rgb_cycle_sketch: fases, LOW de los otros dos, orden -------------------

def _phases(sketch):
    parts = re.split(r'Serial\.println\("TEST:COLOR=(\w+)"\);', sketch)
    # parts: [prefijo, nombre1, cuerpo1, nombre2, cuerpo2, ...]
    out = []
    for i in range(1, len(parts), 2):
        # Los digitalWrite de la fase van ANTES de su Serial.println: mirar atras.
        before = parts[i - 1]
        writes = [(int(p), s) for p, s in re.findall(r"digitalWrite\((\d+), (HIGH|LOW)\)", before)]
        out.append((parts[i], writes))
    return out


def test_rgb_cycle_each_phase_turns_off_the_other_two_in_rgb_order():
    sketch = rgb_cycle_sketch(red=3, green=5, blue=6, dwell_ms=250)
    phases = _phases(sketch)
    assert [name for name, _ in phases] == ["RED", "GREEN", "BLUE"]
    expected_high = {"RED": 3, "GREEN": 5, "BLUE": 6}
    for name, writes in phases:
        highs = [p for p, s in writes if s == "HIGH"]
        lows = [p for p, s in writes if s == "LOW"]
        assert highs == [expected_high[name]]
        assert sorted(lows) == sorted({3, 5, 6} - {expected_high[name]})
    assert sketch.index("TEST:COLOR=RED") < sketch.index("TEST:COLOR=GREEN")
    assert sketch.index("TEST:COLOR=GREEN") < sketch.index("TEST:COLOR=BLUE")


# --- Consistencia punta a punta ---------------------------------------------

def test_model_wires_resimulated_by_holes_reconnect_each_uno_pin_to_its_color():
    model = fixture_to_model_call(copy.deepcopy(RGB_FIXTURE))
    placements = plan_layout(copy.deepcopy(RGB_FIXTURE))["placements"]

    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    def col_key(hole):
        m = re.fullmatch(r"(\d+)([a-j])", hole)
        half = "low" if m.group(2) in "abcde" else "high"
        return ("col", m.group(1), half)

    # Pin fisico -> hueco, con el orden red/cathode/blue/green del DID.
    pin_hole = {}
    for i, color in enumerate(PHYSICAL_ORDER):
        pin_hole[f"rgb1.{color}"] = _shift(placements["rgb1"]["at"], i)
    for ref in ("r1", "r2", "r3"):
        pin_hole[f"{ref}.1"] = placements[ref]["at"]
        pin_hole[f"{ref}.2"] = _shift(placements[ref]["at"], 4)
        union(f"{ref}.1", f"{ref}.2")  # cuerpo de la resistencia

    for endpoint, hole in pin_hole.items():
        union(endpoint, hole)
        union(hole, col_key(hole))
    for wire in model["wires"]:
        a, b = wire["from"], wire["to"]
        for end in (a, b):
            if re.fullmatch(r"\d+[a-j]", end):
                union(end, col_key(end))
        union(a, b)

    for color in ("red", "green", "blue"):
        uno_pin = _fixture_rgb_pin(RGB_FIXTURE, color)
        assert find(uno_pin) == find(f"rgb1.{color}"), color
        for other in ("red", "green", "blue"):
            if other != color:
                assert find(uno_pin) != find(f"rgb1.{other}"), (color, other)
    assert find("uno.GND1") == find("rgb1.cathode")


def test_cli_demo_real_sketch_matches_fixture_pin_per_color():
    spec = importlib.util.spec_from_file_location(
        "demo_build_tester", ROOT / "scripts/demo_build.py"
    )
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)

    fixture = demo.find_fixture("led-rgb")
    code = demo.select_code(fixture)
    assert code is not None and code == rgb_cycle_sketch()
    phases = _phases(code)
    assert [name for name, _ in phases] == ["RED", "GREEN", "BLUE"]
    high_by_color = {
        name: next(p for p, s in writes if s == "HIGH") for name, writes in phases
    }
    for color, phase in (("red", "RED"), ("green", "GREEN"), ("blue", "BLUE")):
        assert _fixture_rgb_pin(fixture, color) == f"uno.D{high_by_color[phase]}"
