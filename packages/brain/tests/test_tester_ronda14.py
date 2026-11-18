"""Tester independiente ronda 14: LCD libre + termometro TMP36 (fase 21).

No participe en el desarrollo de esta fase: todo lo de abajo se verifico
leyendo el codigo real (``layout.py``, ``builder.py``, ``sketches.py``) y
comparandolo con el contrato declarado, con tablas y oraculos PROPIOS (no
importo ``_LCD_REAL_PINS``, ``_THREE_PIN_PINS`` ni ninguna tabla privada del
builder: si cambian, estos tests tienen que romperse).

Contrato que se pone a prueba
-----------------------------
1. El LCD 16x2 ya no se ensarta en la protoboard: el layout lo emite como
   modulo libre ``{"free": {"x": 870, "y": -230, "angle": 0}}``, el segundo
   se apila en ``y=-430`` (paso 200), no consume columnas y ya no existe
   guarda de oclusion (los vecinos de placa se colocan igual).
2. El builder emite el part del LCD como ``{ref, did 113878, free}`` sin
   ``pin`` ni ``at``, y traduce sus nets a terminales reales. Dice tambien
   (en ``builder.py``) que el display sigue teniendo 3 pines en fila c
   cuando el TMP36 esta en la placa: vcc en el ancla, vout a +1 y gnd a +2.
3. Fixture ``lcd-temperatura``: TMP36 en la placa + LCD libre + resistencia
   del backlight; circuito real ``9hZJgbsYOC5`` con ``TEST:TEMP=24.78``.
4. Sketch ``lcd_temp_sketch``: misma formula que ``tmp36_sketch``, el
   ``TEST:TEMP`` sale de la MISMA variable que se pinta en el LCD, 2
   decimales, validaciones de pines / ``sensor_pin`` / ``period_ms``.

Hallazgo de esta ronda (LOW, no bloqueante): ver el ultimo test del archivo,
``test_r14_el_part_libre_del_lcd_es_aceptable_por_el_validador_de_specs``.
"""
import copy
import itertools
import json
import re
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import (
    DID_BY_TYPE,
    _translate_endpoint,
    fixture_to_model_call,
)
from tinkercad_brain.fase0.metrics import compare_connectivity
from tinkercad_brain.fase0.normalize import normalize_circuit
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.sketches import lcd_temp_sketch, tmp36_sketch
from tinkercad_brain.spec import SpecError, validate_spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_PATH = ROOT / "fixtures" / "fase0" / "circuits.json"
BENCHMARK_PATH = ROOT / "docs" / "benchmark.md"
VIVO_PATH = ROOT / "docs" / "fase0-vivo.md"

# Orden fisico de los 16 terminales del LCD, de izquierda a derecha. Tabla
# propia del tester: el LCD ya no va en la placa, pero sus terminales siguen
# siendo estos y en este orden.
LCD_TERMINALS = (
    "GND", "VDD", "VO", "RS", "RW", "E",
    "DB0", "DB1", "DB2", "DB3", "DB4", "DB5", "DB6", "DB7",
    "LED+", "LED-",
)

# Contrato de coordenadas del modulo libre.
LCD_FREE_ABOVE = {"free": {"x": 1100, "y": -230, "angle": 0}}
LCD_FREE_STACKED = {"free": {"x": 1100, "y": -430, "angle": 0}}

# Pines reales de los tipos que tocan la placa en este circuito (tabla
# propia, no importada de breadboard_nets).
REAL_PIN = {
    "tmp36": {"vcc": "Vcc", "vout": "Vout", "gnd": "Gnd"},
    "resistor": {"1": "Terminal 1", "2": "Terminal 2"},
    "lcd-16x2": {pin: pin for pin in LCD_TERMINALS},
}
RAW_TYPE = {
    "tmp36": "TMP36",
    "resistor": "Resistor",
    "lcd-16x2": "LCD 16 x 2",
}

UNO_INSTANCE = "uno_a"
BB_INSTANCE = "bb_a"


def _fixture(fixture_id):
    circuits = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == fixture_id)


def _all_fixtures():
    return json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))


def _col(hole):
    return int(hole[:-1])


def _row(hole):
    return hole[-1]


def _holes(fixture, ref, pins=None):
    """Huecos (o terminales) de cada pin cableado de ``ref``."""
    layout = plan_layout(fixture)
    placements = layout["placements"]
    type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}
    if pins is None:
        pins = {
            endpoint.split(".", 1)[1]
            for net in fixture["nets"]
            for endpoint in net
            if endpoint.split(".", 1)[0] == ref
        }
    return {
        pin: _translate_endpoint(f"{ref}.{pin}", placements, type_by_ref)
        for pin in sorted(pins)
    }


def _shift(hole, columns):
    return f"{_col(hole) + columns}{_row(hole)}"


def _pairs(call):
    return [(w["from"], w["to"]) for w in call["wires"]]


def _endpoint(instance_id, pin):
    return {"component": instance_id, "pin": pin, "instance_id": instance_id}


# --------------------------------------------- inspect armado a mano

def _temperatura_inspect(order=("tmp1", "lcd1", "r1"), lcd_pin_names=None,
                         tmp_pin_names=None):
    """Inspect del circuito real armado a mano, sin Tinkercad.

    Se cablea como el circuito de verdad: cada pata de placa entra en su
    hueco (que sale del layout) y luego se encadenan los extremos de cada
    net de la fixture, traduciendo el LCD a su terminal real.
    """
    fixture = _fixture("lcd-temperatura")
    placements = plan_layout(fixture)["placements"]
    type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}

    instance = {"uno": UNO_INSTANCE}
    for ref in order:
        instance[ref] = f"i_{ref}"

    wires = []

    def wire(source, target):
        wires.append({"source": _endpoint(*source), "target": _endpoint(*target)})

    tmp_real = {pin: (tmp_pin_names or {}).get(pin, real)
                for pin, real in REAL_PIN["tmp36"].items()}
    lcd_real = {pin: (lcd_pin_names or {}).get(pin, pin) for pin in LCD_TERMINALS}

    # Patas de placa -> hueco.
    for ref in ("tmp1", "r1"):
        ctype = type_by_ref[ref]
        real_by_pin = tmp_real if ctype == "tmp36" else REAL_PIN[ctype]
        for pin, real in real_by_pin.items():
            hole = _translate_endpoint(f"{ref}.{pin}", placements, type_by_ref)
            wire((instance[ref], real), (BB_INSTANCE, hole))

    def mapped(endpoint):
        ref, pin = endpoint.split(".", 1)
        if ref == "uno":
            return (UNO_INSTANCE, pin)
        if type_by_ref[ref] == "lcd-16x2":
            return (instance[ref], lcd_real[pin])
        return (BB_INSTANCE,
                _translate_endpoint(endpoint, placements, type_by_ref))

    for net in fixture["nets"]:
        nodes = [mapped(endpoint) for endpoint in net]
        for first, second in zip(nodes, nodes[1:]):
            wire(first, second)

    components = [
        {"type": "Arduino Uno R3", "instance_id": UNO_INSTANCE, "pins": []},
        {"type": "Breadboard Small", "instance_id": BB_INSTANCE, "pins": []},
    ]
    for ref in order:
        components.append(
            {
                "type": RAW_TYPE[type_by_ref[ref]],
                "instance_id": instance[ref],
                "pins": [],
            }
        )
    return {"components": components, "wires": wires}


def _actual_from_inspect(inspect):
    return {
        "components": normalize_circuit(inspect, {"nets": []})["components"],
        "nets": derive_nets(inspect),
    }


def _score(inspect):
    fixture = _fixture("lcd-temperatura")
    return compare_connectivity(
        {"components": fixture["components"], "nets": fixture["nets"]},
        _actual_from_inspect(inspect),
    )


def _net_with(nets, endpoint):
    matches = [net for net in nets if endpoint in net]
    assert len(matches) == 1, (endpoint, matches)
    return matches[0]


# ------------------------------------------------------------- fixture

def test_r14_fixture_lcd_temperatura_tiene_su_lcd_su_sensor_y_su_resistencia():
    fixture = _fixture("lcd-temperatura")

    assert [c["ref"] for c in fixture["components"]] == [
        "uno", "tmp1", "lcd1", "r1",
    ]
    assert [c["type"] for c in fixture["components"]] == [
        "arduino-uno", "tmp36", "lcd-16x2", "resistor",
    ]
    # La net de GND del contrato: LCD (GND, VO, RW, LED-) + TMP36 + Uno.
    gnd = next(net for net in fixture["nets"] if "lcd1.GND" in net)
    assert len(gnd) == 6
    assert set(gnd) == {
        "lcd1.GND", "lcd1.VO", "lcd1.RW", "lcd1.LED-", "tmp1.gnd", "uno.GND1",
    }
    # La de 5V: LCD, resistencia, TMP36 y Uno.
    power = next(net for net in fixture["nets"] if "uno.5V" in net)
    assert len(power) == 4
    assert set(power) == {"uno.5V", "lcd1.VDD", "r1.1", "tmp1.vcc"}
    # Modo 4 bits: solo DB4..DB7 al Arduino; el sensor va a una analogica.
    data_pins = {
        endpoint.split(".", 1)[1]
        for net in fixture["nets"]
        for endpoint in net
        if endpoint.startswith("lcd1.DB")
    }
    assert data_pins == {"DB4", "DB5", "DB6", "DB7"}
    assert ["tmp1.vout", "uno.A0"] in fixture["nets"]
    # La resistencia es del backlight: LED+ por ella, no una senal.
    assert ["r1.2", "lcd1.LED+"] in fixture["nets"]


# ------------------------------------------- geometria del LCD libre

def test_r14_layout_del_termometro_lcd_libre_tmp36_en_fila_c_y_r_en_g():
    result = plan_layout(_fixture("lcd-temperatura"))

    assert result["unplaced"] == []
    assert result["placements"]["lcd1"] == LCD_FREE_ABOVE
    assert result["placements"]["tmp1"] == {"at": "7c", "pin": "vcc", "angle": 0}
    assert result["placements"]["r1"] == {"at": "1g", "pin": "1", "angle": 90}

    # Tres pines de TMP36 en fila c, consecutivos, y la resistencia en g.
    tmp_holes = _holes(_fixture("lcd-temperatura"), "tmp1")
    assert tmp_holes == {"vcc": "7c", "vout": "8c", "gnd": "9c"}
    assert {_row(hole) for hole in tmp_holes.values()} == {"c"}
    resistor_holes = _holes(_fixture("lcd-temperatura"), "r1")
    assert resistor_holes == {"1": "1g", "2": "5g"}
    assert {_row(hole) for hole in resistor_holes.values()} == {"g"}

    # Ni huecos ni columnas compartidas entre sensor y resistencia.
    assert set(tmp_holes.values()).isdisjoint(resistor_holes.values())
    assert {_col(h) for h in tmp_holes.values()}.isdisjoint(
        {_col(h) for h in resistor_holes.values()}
    )
    # Y todo dentro de la placa real.
    for hole in list(tmp_holes.values()) + list(resistor_holes.values()):
        assert 1 <= _col(hole) <= 30, hole
        assert _row(hole) in "abcdefghij", hole


def test_r14_el_lcd_no_aporta_huecos_ni_consume_columnas():
    fixture = _fixture("lcd-temperatura")
    without_lcd = {
        "components": [c for c in fixture["components"] if c["ref"] != "lcd1"],
        "nets": [],
    }

    layout = plan_layout(fixture)
    placement = layout["placements"]["lcd1"]
    assert placement == LCD_FREE_ABOVE
    assert set(placement) == {"free"}
    assert "at" not in placement and "pin" not in placement

    # Los placements de placa son EXACTAMENTE los del circuito sin display.
    board_only = {
        ref: placed
        for ref, placed in layout["placements"].items()
        if ref != "lcd1"
    }
    assert board_only == plan_layout(without_lcd)["placements"]
    # Y el primer bloque de placa sigue arrancando en la columna 1.
    assert min(_col(p["at"]) for p in board_only.values()) == 1

    # Sus 16 terminales se traducen al terminal, nunca a un hueco.
    type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}
    for pin in LCD_TERMINALS:
        translated = _translate_endpoint(
            f"lcd1.{pin}", layout["placements"], type_by_ref
        )
        assert translated == f"lcd1.{pin}"
        assert re.fullmatch(r"\d+[a-j]", translated) is None


def test_r14_las_coordenadas_del_lcd_no_pisan_la_placa_ni_a_otro_lcd():
    layout = plan_layout(_fixture("lcd-temperatura"))
    lcd_free = layout["placements"]["lcd1"]["free"]

    # El display flota ARRIBA de la placa (que vive en y=0): no comparte
    # origen con ella.
    assert (lcd_free["x"], lcd_free["y"]) != (0, 0)
    assert lcd_free["y"] < 0

    # Ni con ningun otro modulo libre del mismo circuito.
    others = [
        (placed["free"]["x"], placed["free"]["y"])
        for ref, placed in layout["placements"].items()
        if ref != "lcd1" and "free" in placed
    ]
    assert others == []
    assert (lcd_free["x"], lcd_free["y"]) not in others

    # Dos displays: mismo x, apilados en y con paso 200 (cuerpos sin pisarse).
    two = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "lcd1", "type": "lcd-16x2"},
            {"ref": "lcd2", "type": "lcd-16x2"},
            {"ref": "motor1", "type": "dc-motor"},
            {"ref": "bat1", "type": "battery-9v"},
        ],
        "nets": [],
    }
    result = plan_layout(two)
    assert result["unplaced"] == []
    assert result["placements"]["lcd1"] == LCD_FREE_ABOVE
    assert result["placements"]["lcd2"] == LCD_FREE_STACKED
    spots = [
        (placed["free"]["x"], placed["free"]["y"])
        for placed in result["placements"].values()
    ]
    assert len(spots) == len(set(spots)) == 4
    assert (
        result["placements"]["lcd1"]["free"]["y"]
        - result["placements"]["lcd2"]["free"]["y"]
        == 200
    )


def test_r14_el_lcd_ya_no_oculta_al_vecino_de_placa():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "lcd1", "type": "lcd-16x2"},
            {"ref": "tmp1", "type": "tmp36"},
            {"ref": "r1", "type": "resistor"},
            {"ref": "btn1", "type": "pushbutton"},
        ],
        "nets": [
            ["uno.D12", "lcd1.RS"],
            ["uno.5V", "tmp1.vcc"],
            ["tmp1.vout", "uno.A0"],
            ["btn1.1", "uno.D2"],
            ["uno.D13", "r1.1"],
        ],
    }
    result = plan_layout(fixture)

    assert result["unplaced"] == []
    assert result["placements"]["lcd1"] == LCD_FREE_ABOVE
    for ref in ("tmp1", "r1", "btn1"):
        assert "at" in result["placements"][ref], ref

    used = {}
    for ref in ("tmp1", "r1", "btn1"):
        for pin, hole in _holes(fixture, ref).items():
            assert hole not in used, (ref, pin, hole, used.get(hole))
            used[hole] = (ref, pin)
    for hole in used:
        assert 1 <= _col(hole) <= 30, hole
        assert _row(hole) in "abcdefghij", hole
    # Y el circuito entero se puede construir.
    assert {p["ref"] for p in fixture_to_model_call(fixture)["parts"]} == {
        "lcd1", "tmp1", "r1", "btn1",
    }


# ------------------------------------------------------- model call

def test_r14_parts_del_termometro_lcd_libre_y_pines_reales():
    parts = {p["ref"]: p for p in fixture_to_model_call(
        _fixture("lcd-temperatura"))["parts"]}

    assert parts["lcd1"] == {
        "ref": "lcd1",
        "did": 113878,
        "free": {"x": 1100, "y": -230},
        "angle": 0,
    }
    assert "at" not in parts["lcd1"] and "pin" not in parts["lcd1"]
    # El TMP36 sigue en la placa con su ancla real "Vcc" en la fila c.
    assert parts["tmp1"] == {
        "ref": "tmp1", "did": 112324, "at": "7c", "pin": "Vcc", "angle": 0,
    }
    assert parts["r1"] == {
        "ref": "r1", "did": 53184, "at": "1g", "pin": "1", "angle": 90,
    }
    # Cada part de placa trae un hueco valido.
    for ref in ("tmp1", "r1"):
        assert re.fullmatch(r"([1-9]|[12][0-9]|30)[a-j]", parts[ref]["at"])
    assert DID_BY_TYPE["lcd-16x2"] == 113878
    assert DID_BY_TYPE["tmp36"] == 112324


def test_r14_cada_cable_del_lcd_va_por_terminal_y_ninguno_por_hueco():
    call = fixture_to_model_call(_fixture("lcd-temperatura"))

    lcd_terminals = set()
    for wire in call["wires"]:
        for text in (wire["from"], wire["to"]):
            if text.startswith("lcd1."):
                pin = text.split(".", 1)[1]
                assert pin in LCD_TERMINALS, pin
                lcd_terminals.add(pin)
    # 12 pines cableados del display (los DB0..DB3 no se usan en 4 bits).
    assert lcd_terminals == {
        "GND", "VDD", "VO", "RS", "RW", "E",
        "DB4", "DB5", "DB6", "DB7", "LED+", "LED-",
    }
    # Ningun extremo del display cae en un hueco.
    for wire in call["wires"]:
        for text in (wire["from"], wire["to"]):
            if text.startswith("lcd1."):
                assert not re.fullmatch(r"\d+[a-j]", text)


def test_r14_cada_cable_al_tmp36_y_a_la_resistencia_va_por_hueco():
    fixture = _fixture("lcd-temperatura")
    call = fixture_to_model_call(fixture)
    placements = plan_layout(fixture)["placements"]

    # Ningun cable puede terminar en "tmp1.x" / "r1.x": la placa se cablea
    # por hueco.
    texts = {text for wire in call["wires"] for text in (wire["from"], wire["to"])}
    assert not {t for t in texts if t.startswith(("tmp1.", "r1."))}

    anchor = placements["tmp1"]["at"]
    # Offset fisico de 3 pines en fila: vcc en el ancla, vout +1, gnd +2.
    vcc, vout, gnd = anchor, _shift(anchor, 1), _shift(anchor, 2)
    pairs = _pairs(call)
    assert (vcc, vout) not in pairs and (vcc, gnd) not in pairs  # no inventa uniones
    # Contrato fase 22: las nets de 3+ extremos cuelgan en estrella del hub
    # (uno.5V / uno.GND1), no en cadena. Por eso cada pata va directo al Uno.
    assert ("uno.5V", "lcd1.VDD") in pairs
    assert ("uno.5V", "1g") in pairs
    assert ("uno.5V", vcc) in pairs
    # vout a la analogica, gnd a la tierra comun.
    assert (vout, "uno.A0") in pairs
    assert ("uno.GND1", gnd) in pairs
    # Backlight por la resistencia: LED+ a la pata 2 (5g).
    assert ("5g", "lcd1.LED+") in pairs
    # Y todos los huecos usados estan dentro de la placa.
    for text in texts:
        match = re.fullmatch(r"(\d+)([a-j])", text)
        if match:
            assert 1 <= int(match.group(1)) <= 30, text


def test_r14_el_model_call_del_lcd_no_inventa_ni_pierde_cables():
    fixture = _fixture("lcd-temperatura")
    call = fixture_to_model_call(fixture)
    pairs = _pairs(call)

    # Un cable por par consecutivo de cada net de la fixture.
    assert len(pairs) == sum(len(net) - 1 for net in fixture["nets"]) == 16
    assert len(set(pairs)) == len(pairs)
    for first, second in pairs:
        assert first != second
        assert isinstance(first, str) and isinstance(second, str)
    # El cable que cierra la tierra al Uno va negro; el de 5V, rojo.
    colors = {(w["from"], w["to"]): w["color"] for w in call["wires"]}
    assert colors[("uno.5V", "lcd1.VDD")] == "red"
    assert colors[("uno.GND1", "9c")] == "black"
    # Todos los parts de la fixture estan, una sola vez, menos el Uno.
    refs = [p["ref"] for p in call["parts"]]
    assert sorted(refs) == ["lcd1", "r1", "tmp1"]
    assert len(refs) == len(set(refs))


def test_r14_el_model_call_no_muta_la_fixture_ni_es_inestable():
    fixture = _fixture("lcd-temperatura")
    before = copy.deepcopy(fixture)

    first = fixture_to_model_call(fixture, code="void setup() {}")
    second = fixture_to_model_call(fixture, code="void setup() {}")

    assert fixture == before
    assert first == second
    assert first["code"] == "void setup() {}"


# ------------------------------------- conectividad extremo a extremo

def test_r14_conectividad_del_termometro_sin_tinkercad_es_1_0():
    result = _score(_temperatura_inspect())

    assert result["missing_components"] == []
    assert result["extra_components"] == []
    assert result["shorts"] == []
    assert result["components_score"] == 1.0
    assert result["connectivity_score"] == 1.0
    assert result["score"] == 1.0


def test_r14_las_dos_nets_largas_quedan_completas_al_leer_el_circuito():
    actual = _actual_from_inspect(_temperatura_inspect())
    nets = actual["nets"]

    tmp_ref = next(
        ref
        for ref in {endpoint.split(".", 1)[0] for net in nets for endpoint in net}
        if ref.startswith("tmp")
    )
    gnd = _net_with(nets, "uno.GND1")
    assert set(gnd) == {
        "lcd1.GND", "lcd1.VO", "lcd1.RW", "lcd1.LED-",
        f"{tmp_ref}.gnd", "uno.GND1",
    }
    assert len(gnd) == 6

    power = _net_with(nets, "uno.5V")
    assert set(power) == {"uno.5V", "lcd1.VDD", "r1.1", f"{tmp_ref}.vcc"}
    assert len(power) == 4


def test_r14_los_nombres_humanos_de_los_cables_dan_las_mismas_nets():
    canonical = _actual_from_inspect(_temperatura_inspect())
    # Los cables del circuito real etiquetan el LCD con nombres humanos y
    # el TMP36 como lo reporta inspect (Power / Vout / GND).
    relabeled = _actual_from_inspect(
        _temperatura_inspect(
            lcd_pin_names={
                "GND": "Ground",
                "VDD": "Power",
                "VO": "Contrast",
                "RS": "Register Select",
                "RW": "Read/Write",
                "E": "Enable",
                "LED+": "LED Anode",
                "LED-": "LED Cathode",
            },
            tmp_pin_names={"vcc": "Power", "vout": "Vout", "gnd": "GND"},
        )
    )

    assert relabeled["nets"] == canonical["nets"]
    result = _score(
        _temperatura_inspect(
            lcd_pin_names={"GND": "Ground", "VDD": "Power"},
            tmp_pin_names={"vcc": "Power", "gnd": "GND"},
        )
    )
    assert result["score"] == 1.0
    assert result["shorts"] == []


def test_r14_los_refs_de_derive_nets_y_normalize_coinciden_en_el_lcd():
    inspect = _temperatura_inspect()
    normalized = normalize_circuit(inspect, {"nets": []})
    nets = derive_nets(inspect)

    normalized_refs = {c["ref"] for c in normalized["components"]}
    derived_refs = {endpoint.split(".", 1)[0] for net in nets for endpoint in net}
    assert derived_refs == normalized_refs
    assert "lcd1" in derived_refs
    assert not {ref for ref in derived_refs if ref.startswith("lcd")} - {"lcd1"}
    assert "lcd16x21" not in derived_refs


# ------------------------- independencia de orden (regresion ronda 12)

def test_r14_el_orden_de_declaracion_no_cambia_layout_ni_score():
    fixture = _fixture("lcd-temperatura")
    base_layout = plan_layout(fixture)
    refs = [c["ref"] for c in fixture["components"] if c["ref"] != "uno"]
    assert base_layout["placements"]["tmp1"]["at"] == "7c"

    for order in itertools.permutations(refs):
        reordered = {
            "components": [{"ref": "uno", "type": "arduino-uno"}]
            + [
                next(c for c in fixture["components"] if c["ref"] == ref)
                for ref in order
            ],
            "nets": fixture["nets"],
        }
        # El layout es literalmente el mismo, sin importar el indice.
        assert plan_layout(reordered) == base_layout, order
        result = _score(_temperatura_inspect(order=order))
        assert result["score"] == 1.0, (order, result)
        assert result["shorts"] == [], order


def test_r14_el_orden_de_las_nets_no_cambia_la_conectividad():
    fixture = _fixture("lcd-temperatura")
    reversed_fixture = copy.deepcopy(fixture)
    reversed_fixture["nets"] = list(reversed(fixture["nets"]))

    assert fixture_to_model_call(reversed_fixture)["wires"] == (
        fixture_to_model_call(fixture)["wires"]
    )
    assert _score(_temperatura_inspect())["score"] == 1.0


# ------------------------------------------------------------ sketch

def test_r14_el_test_temp_sale_de_la_misma_variable_que_pinta_el_lcd():
    sketch = lcd_temp_sketch()

    formatted = re.search(r"dtostrf\((\w+), 0, 2, (\w+)\);", sketch)
    assert formatted, sketch
    source_variable, text_buffer = formatted.groups()
    assert source_variable == "temp"

    line = re.search(
        r'snprintf\((\w+), sizeof\(\1\), "T=%s C", (\w+)\);', sketch
    )
    assert line, sketch
    line_buffer, snprintf_value = line.groups()
    assert snprintf_value == text_buffer
    assert f"lcd.print({line_buffer});" in sketch
    assert f"lcd.print({source_variable});" not in sketch

    trace = re.search(
        r'Serial\.print\("TEST:TEMP="\);\s*Serial\.println\((\w+)\);', sketch
    )
    assert trace, sketch
    assert trace.group(1) == text_buffer
    # Un solo TEST:TEMP, y sale del mismo buffer de 2 decimales.
    assert sketch.count('"TEST:TEMP="') == 1


def test_r14_la_formula_del_tmp36_es_identica_a_la_del_sketch_tmp36():
    lcd = lcd_temp_sketch()
    plain = tmp36_sketch()

    patterns = (
        r"int lectura = analogRead\([^)]*\);",
        r"float volts = [^;]*;",
        r"float temp = [^;]*;",
    )
    for pattern in patterns:
        assert re.search(pattern, lcd), (pattern, lcd)
        assert re.search(pattern, lcd).group(0) == re.search(
            pattern, plain
        ).group(0), pattern


def test_r14_el_valor_del_lcd_va_a_dos_decimales_y_la_linea_se_llena():
    sketch = lcd_temp_sketch()

    # dtostrf(valor, ancho, decimales, buffer): 2 decimales.
    assert re.search(r"dtostrf\(temp, 0, 2, \w+\);", sketch)
    # El texto que se pinta usa ese buffer.
    assert 'snprintf(linea, sizeof(linea), "T=%s C", temp_txt);' in sketch
    # La linea se rellena a 16 columnas y se termina en NUL.
    assert "for (int i = strlen(linea); i < 16; i++) {" in sketch
    assert "linea[16] = '\\0';" in sketch
    assert "lcd.setCursor(0, 1);" in sketch
    assert "lcd.begin(16, 2);" in sketch
    # Includes reales del sketch (dtostrf/snprintf necesitan stdlib/stdio).
    for header in ("LiquidCrystal.h", "stdio.h", "stdlib.h"):
        assert f"#include <{header}>" in sketch
        assert sketch.count(f"#include <{header}>") == 1


def test_r14_los_defaults_del_sketch_coinciden_con_el_cableado_de_la_fixture():
    fixture = _fixture("lcd-temperatura")
    sketch = lcd_temp_sketch()

    pin_by_lcd_pin = {}
    for net in fixture["nets"]:
        uno_pins = [e.split(".", 1)[1] for e in net if e.startswith("uno.D")]
        if not uno_pins:
            continue  # nets de 5V/GND: no llevan una senal digital
        lcd_pins = [e.split(".", 1)[1] for e in net if e.startswith("lcd1.")]
        for lcd_pin in lcd_pins:
            pin_by_lcd_pin[lcd_pin] = uno_pins[0]
    assert set(pin_by_lcd_pin) == {
        "RS", "E", "DB4", "DB5", "DB6", "DB7",
    }, pin_by_lcd_pin

    def number(uno_pin):
        return int(uno_pin[1:])

    constructor = re.search(r"LiquidCrystal lcd\(([\d, ]+)\);", sketch)
    assert constructor, sketch
    rs, en, d4, d5, d6, d7 = [int(v) for v in constructor.group(1).split(",")]
    assert (rs, en) == (
        number(pin_by_lcd_pin["RS"]), number(pin_by_lcd_pin["E"]),
    )
    assert (d4, d5, d6, d7) == tuple(
        number(pin_by_lcd_pin[pin]) for pin in ("DB4", "DB5", "DB6", "DB7")
    )

    analog = re.search(r"analogRead\((A\d)\);", sketch)
    assert analog
    sensor_net = next(net for net in fixture["nets"] if "tmp1.vout" in net)
    assert f"uno.{analog.group(1)}" in sensor_net

    # Ajustar solo los digitales no toca el sensor ni el periodo.
    custom = lcd_temp_sketch(rs=7, en=6, d4=9, d5=10, d6=11, d7=12)
    assert "LiquidCrystal lcd(7, 6, 9, 10, 11, 12);" in custom
    assert f"analogRead({analog.group(1)});" in custom
    assert lcd_temp_sketch(sensor_pin="A3", period_ms=250).count(
        "analogRead(A3);"
    ) == 1
    assert "delay(250);" in lcd_temp_sketch(sensor_pin="A3", period_ms=250)


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"rs": 11}, "repetidos"),          # choca con el default en=11
        ({"d4": 5, "d5": 5}, "repetidos"),
        ({"d6": 3, "d7": 3}, "repetidos"),
        ({"rs": 1}, "fuera de"),
        ({"rs": 14}, "fuera de"),
        ({"en": 0}, "fuera de"),
        ({"d7": 99}, "fuera de"),
        ({"en": True}, "fuera de"),
        ({"d4": 12.0}, "fuera de"),
        ({"d5": "5"}, "fuera de"),
        ({"d6": None}, "fuera de"),
    ],
)
def test_r14_el_sketch_rechaza_pines_invalidos(kwargs, match):
    with pytest.raises(ValueError, match=match):
        lcd_temp_sketch(**kwargs)


@pytest.mark.parametrize("sensor_pin", ["A6", "A-1", "D0", "a0", "0", 7, None])
def test_r14_el_sketch_rechaza_sensor_pin_fuera_de_a0_a5(sensor_pin):
    with pytest.raises(ValueError, match="sensor_pin"):
        lcd_temp_sketch(sensor_pin=sensor_pin)


@pytest.mark.parametrize("sensor_pin", ["A0", "A1", "A2", "A3", "A4", "A5"])
def test_r14_el_sketch_acepta_todas_las_analogicas(sensor_pin):
    sketch = lcd_temp_sketch(sensor_pin=sensor_pin)
    assert f"analogRead({sensor_pin});" in sketch


@pytest.mark.parametrize("period_ms", [200, 60000, 500])
def test_r14_el_sketch_acepta_periodos_en_rango_y_los_usa(period_ms):
    assert f"delay({period_ms});" in lcd_temp_sketch(period_ms=period_ms)


@pytest.mark.parametrize(
    "period_ms", [199, 60001, 0, -1, True, False, 500.0, "500", None]
)
def test_r14_el_sketch_rechaza_periodos_fuera_de_rango(period_ms):
    with pytest.raises(ValueError, match="period_ms"):
        lcd_temp_sketch(period_ms=period_ms)


def test_r14_el_sketch_es_determinista():
    assert lcd_temp_sketch() == lcd_temp_sketch()
    assert lcd_temp_sketch().endswith("}\n")
    # Sin el contador de la ronda 13 ni restos de otras plantillas.
    sketch = lcd_temp_sketch()
    assert "segundos" not in sketch
    assert 'Serial.println("READY");' not in sketch


# --------------------------------------------------------------- docs

def test_r14_el_benchmark_lista_los_circuitos_y_los_del_lcd():
    # Contrato actualizado (fase 22): el benchmark crecio a 15 circuitos con
    # el medidor de distancia (blN5d8qCr2z). Los dos del LCD siguen siendo
    # el 13 y el 14.
    text = BENCHMARK_PATH.read_text(encoding="utf-8")

    rows = re.findall(
        r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([A-Za-z0-9]+)\s*\|", text, re.M
    )
    numbers = [int(number) for number, _title, _cid in rows]
    # La fase 35 agrega la fila 27 (control de acceso con servo).
    assert len(rows) == 28, (len(rows), numbers)  # fase 38: contador 555+compuertas
    assert numbers == list(range(1, 29))  # fase 38: fila 28

    ids = {cid: title for _number, title, cid in rows}
    assert "cpySiVSE9vr" in ids and "LCD" in ids["cpySiVSE9vr"]
    assert "9hZJgbsYOC5" in ids
    assert "tmp36" in ids["9hZJgbsYOC5"].lower() or "term" in ids[
        "9hZJgbsYOC5"
    ].lower()
    # Los circuitos con display (13, 14 y 15) van al 100%.
    assert ids["cpySiVSE9vr"] and ids["9hZJgbsYOC5"] and ids["blN5d8qCr2z"]
    for cid in ("cpySiVSE9vr", "9hZJgbsYOC5", "blN5d8qCr2z"):
        line = next(line for line in text.splitlines() if f"| {cid} |" in line)
        assert "100%" in line, line
    # Y el oraculo del termometro es el del reporte real.
    assert "TEST:TEMP=24.78" in text


def test_r14_fase0_vivo_explica_el_cambio_de_contrato_del_lcd():
    text = VIVO_PATH.read_text(encoding="utf-8")

    section = text.split("Fase 21: el LCD pasa a modulo libre", 1)
    assert len(section) == 2, "falta la seccion de la fase 21"
    body = section[1]

    # Coordenadas, apilado, desaparicion de la reserva de columnas y de la
    # guarda de oclusion, y la rama de compatibilidad del builder.
    assert '"x": 870' in body and '"y": -230' in body
    assert "-430" in body
    assert "reserva de columnas" in body
    assert "oclusion" in body
    assert "terminal real" in body
    assert "compatibilidad" in body
    # Los dos circuitos que quedaron al 100% con el contrato nuevo.
    assert "lcd-contador" in body and "lcd-temperatura" in body
    assert "9hZJgbsYOC5" in body


# ---------------------------------------------------------- caso raro

def test_r14_un_lcd_solo_no_rompe_el_layout_ni_el_model_call():
    alone = {"components": [{"ref": "lcd1", "type": "lcd-16x2"}]}

    layout = plan_layout(alone)
    assert layout == {"placements": {"lcd1": LCD_FREE_ABOVE}, "unplaced": []}

    call = fixture_to_model_call(alone)
    assert call["parts"] == [
        {"ref": "lcd1", "did": 113878,
         "free": {"x": 1100, "y": -230}, "angle": 0}
    ]
    assert call["wires"] == []
    assert call["code"] is None

    # Con nets vacias y con nets internas del propio display.
    assert fixture_to_model_call(dict(alone, nets=[]))["wires"] == []
    internal = dict(alone, nets=[["lcd1.GND", "lcd1.VO", "lcd1.RW"]])
    internal_call = fixture_to_model_call(internal)
    # Una net interna de 3 terminales del display: estrella desde el primero.
    assert _pairs(internal_call) == [
        ("lcd1.GND", "lcd1.VO"), ("lcd1.GND", "lcd1.RW"),
    ]
    assert internal_call["parts"][0]["free"] == {"x": 1100, "y": -230}
    assert internal_call["parts"][0]["angle"] == 0


# -------------------------------------------- hallazgo LOW de la ronda

def test_r14_el_part_libre_del_lcd_es_aceptable_por_el_validador_de_specs():
    """LOW: el builder y ``spec.validate_spec`` no comparten el esquema.

    ``test_builder.py`` fija la convencion de que el model call, envuelto con
    los types, se puede validar con ``validate_spec``. Hoy el part libre del
    LCD trae ``{"x", "y", "angle"}`` y el validador exige exactamente
    ``{"x", "y"}`` (el angulo, en la spec, va a nivel de part). Ningun camino
    de ejecucion valida el model call todavia, por eso es LOW: no rompe el
    build en Tinkercad, pero deja dos esquemas del mismo concepto que no se
    pueden redondear.
    """
    call = fixture_to_model_call(_fixture("lcd-temperatura"))
    lcd_part = next(p for p in call["parts"] if p["ref"] == "lcd1")

    try:
        validate_spec(
            {
                "parts": [
                    {"ref": "lcd1", "type": "lcd-16x2", "free": lcd_part["free"]}
                ],
                "wires": [],
            }
        )
    except SpecError as exc:  # pragma: no cover - se reporta como hallazgo
        pytest.fail(
            "el part libre que emite el builder no pasa validate_spec: "
            f"{exc}"
        )
