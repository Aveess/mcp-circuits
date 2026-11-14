"""Tester independiente ronda 13: LCD 16x2 en modo 4 bits (nivel 5).

Contratos juzgados sin repetir los tests de produccion:

- Geometria: los 16 pines del LCD caen en UNA fila, el hueco traducido por
  el builder coincide con el que impone el placement del layout (columna =
  ancla + offset) y ningun par de pines comparte hueco. LED- tiene que
  terminar en ancla+15 y la fila del ancla no puede cambiar.
- Oclusion: con un LCD en la placa, todo tipo montado en las filas que el
  cuerpo tapa (f/e/d/c) va a ``unplaced`` entero, nunca a medias; un LDR
  ocluido arrastra su resistencia divisora. Un segundo LCD tampoco entra.
  Los tipos de filas visibles (LED, resistencia, LED RGB, diodo) siguen
  entrando despues del bisel. Sin LCD el primer bloque sigue en columna 1.
- Builder: ancla distinta de "GND", pin inventado (DB9/Gnd) o type sin DID
  tienen que explotar con BuildError, y el type sin DID antes de invocar
  al puente.
- Refs: para el MISMO inspect, ``derive_nets`` y ``normalize_circuit``
  numeran el LCD igual ("lcd1"); los alias humanos de los cables reales
  (Ground/Power/Contrast/...) no cambian las nets.
- Punta a punta sin Tinkercad: inspect armado a mano con los placements del
  layout y los offsets del builder -> ``compare_connectivity == 1.0``.
- Sketch: la traza TEST:SEG viene de la MISMA variable que se imprime en
  el display; pines, periodo y titulo se validan en los bordes.
- Independencia de orden (ronda 12): mismo circuito fisico declarado en
  otro orden da el mismo score, incluso si eso cruza los refs.
"""
import copy
import json
import re
from pathlib import Path

import pytest

from tinkercad_brain import builder as builder_module
from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import (
    DID_BY_TYPE,
    BuildError,
    _translate_endpoint,
    build_circuit,
    fixture_to_model_call,
)
from tinkercad_brain.fase0.component_map import TYPE_MAP, fixture_type, known_slugs
from tinkercad_brain.fase0.metrics import compare_connectivity
from tinkercad_brain.fase0.normalize import normalize_circuit
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.sketches import lcd_counter_sketch

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_PATH = ROOT / "fixtures" / "fase0" / "circuits.json"

# Orden fisico real de los 16 terminales del LCD, de izquierda a derecha
# con el ancla "GND" en angle 0. Tabla propia del tester (no se importa de
# produccion: si el builder cambia de orden, esto tiene que romperse).
LCD_PINS = (
    "GND", "VDD", "VO", "RS", "RW", "E",
    "DB0", "DB1", "DB2", "DB3", "DB4", "DB5", "DB6", "DB7",
    "LED+", "LED-",
)

# Pin real que Tinkercad reporta en los wires -> pin de fixture.
_REAL_PIN = {
    "lcd-16x2": {pin: pin for pin in LCD_PINS},
    "resistor": {"1": "Terminal 1", "2": "Terminal 2"},
    "led": {"anode": "Anode", "cathode": "Cathode"},
}

# Nombre de type tal como lo reporta inspect_circuit, por slug.
_RAW_TYPE = {
    "lcd-16x2": "LCD 16 x 2",
    "resistor": "Resistor",
    "led": "LED",
}


def _fixture(fixture_id):
    circuits = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == fixture_id)


def _col(at):
    return int(at[:-1])


def _row(at):
    return at[-1]


def _holes(fixture, ref, pins=None):
    """Huecos reales de cada pin de ``ref`` segun layout + builder."""
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


# ------------------------------------------------------------- fixture

def test_r13_fixture_lcd_contador_carga_con_su_lcd_y_su_resistencia():
    fixture = _fixture("lcd-contador")

    assert [c["ref"] for c in fixture["components"]] == ["uno", "lcd1", "r1"]
    assert [c["type"] for c in fixture["components"]] == [
        "arduino-uno", "lcd-16x2", "resistor",
    ]
    assert fixture["code_features"] == [
        "LiquidCrystal", "begin", "print", "setCursor", "Serial",
    ]
    # La net de GND del LCD tiene 5 endpoints: GND, VO, RW, LED- y el Uno.
    gnd = next(net for net in fixture["nets"] if "lcd1.GND" in net)
    assert len(gnd) == 5
    assert set(gnd) == {
        "lcd1.GND", "lcd1.VO", "lcd1.RW", "lcd1.LED-", "uno.GND1",
    }
    # Modo 4 bits: solo DB4..DB7 van al Arduino.
    data_pins = {
        endpoint.split(".", 1)[1]
        for net in fixture["nets"]
        for endpoint in net
        if endpoint.startswith("lcd1.DB")
    }
    assert data_pins == {"DB4", "DB5", "DB6", "DB7"}


def test_r13_component_map_y_did_del_lcd():
    assert TYPE_MAP["LCD 16 x 2"] == "lcd-16x2"
    assert fixture_type("LCD 16 x 2") == "lcd-16x2"
    assert fixture_type("lcd 16 x 2") == "lcd-16x2"  # case-insensitive
    assert "lcd-16x2" in known_slugs()
    assert DID_BY_TYPE["lcd-16x2"] == 113878


# ---------------------------------------------------- geometria del LCD

def test_r13_geometria_los_16_pines_caen_en_una_fila_sin_repetir_hueco():
    fixture = dict(_fixture("lcd-contador"), nets=[])
    layout = plan_layout(fixture)
    placement = layout["placements"]["lcd1"]
    assert placement == {"at": "1j", "pin": "GND", "angle": 0}

    anchor_column = _col(placement["at"])
    anchor_row = _row(placement["at"])
    holes = _holes(
        dict(fixture, nets=[["uno.5V", f"lcd1.{pin}"] for pin in LCD_PINS]),
        "lcd1",
        pins=list(LCD_PINS),
    )

    assert set(holes) == set(LCD_PINS)
    for index, pin in enumerate(LCD_PINS):
        # columna = ancla + offset, misma fila que el ancla
        assert holes[pin] == f"{anchor_column + index}{anchor_row}", pin
        assert _row(holes[pin]) == anchor_row
        assert 1 <= _col(holes[pin]) <= 30
    # Ningun par de pines comparte hueco.
    assert len(set(holes.values())) == len(LCD_PINS)
    # Bordes explicitos del bloque.
    assert holes["GND"] == "1j"
    assert holes["VDD"] == "2j"
    assert holes["DB7"] == "14j"
    assert holes["LED+"] == "15j"
    assert holes["LED-"] == f"{anchor_column + 15}{anchor_row}" == "16j"


def test_r13_parts_del_lcd_usan_el_ancla_y_el_did_reales():
    parts = {
        p["ref"]: p for p in fixture_to_model_call(_fixture("lcd-contador"))["parts"]
    }
    assert parts["lcd1"] == {
        "ref": "lcd1",
        "did": 113878,
        "at": "1j",
        "pin": "GND",
        "angle": 0,
    }
    # Los huecos de todos los pines cableados de la fixture real.
    assert _holes(_fixture("lcd-contador"), "lcd1") == {
        "DB4": "11j", "DB5": "12j", "DB6": "13j", "DB7": "14j",
        "E": "6j", "GND": "1j", "LED+": "15j", "LED-": "16j",
        "RS": "4j", "RW": "5j", "VDD": "2j", "VO": "3j",
    }


# ------------------------------------------------------------- layout

def test_r13_layout_coloca_el_lcd_primero_y_el_bloque_despues_del_bisel():
    result = plan_layout(_fixture("lcd-contador"))

    assert result["unplaced"] == []
    assert result["placements"]["lcd1"] == {"at": "1j", "pin": "GND", "angle": 0}
    # 16 columnas de pines + bisel: la resistencia no puede caer antes de 19.
    assert _col(result["placements"]["r1"]["at"]) == 19

    lcd_columns = set(range(1, 19))
    resistor_holes = _holes(_fixture("lcd-contador"), "r1", pins=["1", "2"])
    resistor_columns = {_col(hole) for hole in resistor_holes.values()}
    assert lcd_columns.isdisjoint(resistor_columns)


# Tipos que montan en las filas que tapa el cuerpo del LCD (f/e/d/c).
_OCCLUDED_CASES = {
    "buzzer": ([{"ref": "b1", "type": "buzzer"}], [["uno.D8", "b1.positive"]]),
    "photoresistor": (
        [{"ref": "ldr1", "type": "photoresistor"}], [["uno.A0", "ldr1.2"]],
    ),
    "ultrasonic-hcsr04": (
        [{"ref": "us1", "type": "ultrasonic-hcsr04"}],
        [["uno.D7", "us1.trig"], ["uno.D6", "us1.echo"]],
    ),
    "pushbutton": ([{"ref": "btn1", "type": "pushbutton"}], [["uno.D2", "btn1.1"]]),
    "servo": ([{"ref": "srv1", "type": "servo"}], [["uno.D9", "srv1.signal"]]),
    "potentiometer": (
        [{"ref": "pot1", "type": "potentiometer"}], [["uno.A0", "pot1.2"]],
    ),
    "tmp36": ([{"ref": "tmp1", "type": "tmp36"}], [["uno.A0", "tmp1.vout"]]),
    "transistor-npn": (
        [{"ref": "q1", "type": "transistor-npn"}], [["uno.D9", "q1.base"]],
    ),
    "l293d": ([{"ref": "drv1", "type": "l293d"}], [["uno.D9", "drv1.input1"]]),
}


@pytest.mark.parametrize("ctype", sorted(_OCCLUDED_CASES))
def test_r13_con_lcd_los_tipos_ocluidos_van_a_unplaced_enteros(ctype):
    components, nets = _OCCLUDED_CASES[ctype]
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "lcd1", "type": "lcd-16x2"},
        ]
        + components,
        "nets": nets,
    }
    result = plan_layout(fixture)

    # Solo se coloca el LCD: el tipo ocluido no queda a medias.
    assert set(result["placements"]) == {"lcd1"}
    assert result["unplaced"] == [components[0]["ref"]]
    # Y el builder se niega a construir el circuito incompleto.
    with pytest.raises(BuildError, match=components[0]["ref"]):
        fixture_to_model_call(fixture)


def test_r13_con_lcd_el_ldr_ocluido_arrastra_su_divisor():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "lcd1", "type": "lcd-16x2"},
            {"ref": "ldr1", "type": "photoresistor"},
            {"ref": "rdiv", "type": "resistor"},
        ],
        "nets": [["ldr1.2", "uno.A0", "rdiv.1"], ["uno.5V", "ldr1.1"]],
    }
    result = plan_layout(fixture)

    assert set(result["placements"]) == {"lcd1"}
    assert result["unplaced"] == ["ldr1", "rdiv"]
    with pytest.raises(BuildError, match="ldr1"):
        fixture_to_model_call(fixture)


def test_r13_un_segundo_lcd_queda_sin_colocar():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "lcd1", "type": "lcd-16x2"},
            {"ref": "lcd2", "type": "lcd-16x2"},
        ],
        "nets": [["uno.5V", "lcd1.VDD"], ["uno.5V", "lcd2.VDD"]],
    }
    result = plan_layout(fixture)

    assert result["placements"] == {"lcd1": {"at": "1j", "pin": "GND", "angle": 0}}
    assert result["unplaced"] == ["lcd2"]
    with pytest.raises(BuildError, match="lcd2"):
        fixture_to_model_call(fixture)


def test_r13_con_lcd_led_y_resistencia_todo_se_coloca_sin_compartir_hueco():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "lcd1", "type": "lcd-16x2"},
            {"ref": "led1", "type": "led"},
            {"ref": "r1", "type": "resistor"},
        ],
        "nets": [
            ["uno.D9", "r1.1"],
            ["r1.2", "led1.anode"],
            ["led1.cathode", "uno.GND1"],
            ["uno.5V", "lcd1.VDD"],
        ],
    }
    result = plan_layout(fixture)

    assert result["unplaced"] == []
    assert set(result["placements"]) == {"lcd1", "led1", "r1"}
    assert _col(result["placements"]["r1"]["at"]) == 19
    assert result["placements"]["led1"]["at"] == "23i"
    assert fixture_to_model_call(fixture)["parts"]

    # Ningun hueco usado por dos partes distintas.
    used = {}
    for ref in ("lcd1", "led1", "r1"):
        for pin, hole in _holes(fixture, ref).items():
            assert hole not in used, (ref, pin, hole, used.get(hole))
            used[hole] = (ref, pin)


def test_r13_el_lcd_se_coloca_primero_sin_importar_donde_se_declare():
    lcd = {"ref": "lcd1", "type": "lcd-16x2"}
    led = {"ref": "led1", "type": "led"}
    resistor = {"ref": "r1", "type": "resistor"}
    nets = [["r1.2", "led1.anode"]]

    results = []
    for order in ([lcd, led, resistor], [led, resistor, lcd], [resistor, lcd, led]):
        fixture = {
            "components": [{"ref": "uno", "type": "arduino-uno"}] + order,
            "nets": nets,
        }
        results.append(plan_layout(fixture))

    for result in results:
        assert result["unplaced"] == []
        assert result["placements"]["lcd1"] == {
            "at": "1j", "pin": "GND", "angle": 0,
        }
        assert result["placements"]["r1"]["at"] == "19g"
        assert result["placements"]["led1"]["at"] == "23i"
    assert all(result == results[0] for result in results)


def test_r13_lcd_convive_con_las_partes_libres_del_layout():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "lcd1", "type": "lcd-16x2"},
            {"ref": "motor1", "type": "dc-motor"},
            {"ref": "bat1", "type": "battery-9v"},
        ],
        "nets": [
            ["uno.D9", "motor1.positive"],
            ["motor1.negative", "uno.GND1"],
            ["bat1.positive", "uno.VIN"],
            ["bat1.negative", "uno.GND1"],
        ],
    }
    layout = plan_layout(fixture)

    assert layout["unplaced"] == []
    assert layout["placements"]["lcd1"] == {"at": "1j", "pin": "GND", "angle": 0}
    assert "free" in layout["placements"]["motor1"]
    assert "free" in layout["placements"]["bat1"]
    # El LCD no puede terminar con placement libre ni cambiar de ancla.
    parts = {p["ref"]: p for p in fixture_to_model_call(fixture)["parts"]}
    assert parts["lcd1"] == {
        "ref": "lcd1", "did": 113878, "at": "1j", "pin": "GND", "angle": 0,
    }


def test_r13_model_call_del_lcd_contador_solo_usa_huecos_y_pines_del_uno():
    call = fixture_to_model_call(_fixture("lcd-contador"))
    holes = set()
    for wire in call["wires"]:
        assert wire["from"] != wire["to"]
        for text in (wire["from"], wire["to"]):
            if text.startswith("uno."):
                continue
            match = re.fullmatch(r"(\d+)([a-j])", text)
            assert match, text
            assert 1 <= int(match.group(1)) <= 30
            holes.add(text)

    # 12 pines cableados del LCD + las dos patas de la resistencia.
    assert holes == (
        {f"{column}j" for column in (1, 2, 3, 4, 5, 6, 11, 12, 13, 14, 15, 16)}
        | {"19g", "23g"}
    )


def test_r13_sin_lcd_el_primer_bloque_sigue_en_la_columna_1():
    result = plan_layout(_fixture("blink-basico"))

    assert result == {
        "placements": {
            "r1": {"at": "1g", "pin": "1", "angle": 90},
            "led1": {"at": "5i", "pin": "anode", "angle": 180},
        },
        "unplaced": [],
    }


# ------------------------------------------------------------ builder

def _patched_layout(monkeypatch, overrides):
    """Fuerza placements por ref manteniendo el resto del layout real."""
    real_plan_layout = builder_module.plan_layout

    def patched(fixture):
        layout = real_plan_layout(fixture)
        placements = {ref: dict(p) for ref, p in layout["placements"].items()}
        for ref, changes in overrides.items():
            if ref in placements:
                placements[ref].update(changes)
        return {"placements": placements, "unplaced": list(layout["unplaced"])}

    monkeypatch.setattr(builder_module, "plan_layout", patched)


def test_r13_ancla_distinta_de_gnd_es_build_error(monkeypatch):
    for bad_anchor in ("VDD", "RS", "Ground", "1j"):
        _patched_layout(monkeypatch, {"lcd1": {"pin": bad_anchor}})
        with pytest.raises(BuildError, match="ancla") as excinfo:
            fixture_to_model_call(_fixture("lcd-contador"))
        assert "lcd1" in str(excinfo.value)


@pytest.mark.parametrize("bad_pin", ["DB9", "Gnd", "gnd", "DB10", "LED"])
def test_r13_pin_desconocido_del_lcd_es_build_error(bad_pin):
    fixture = copy.deepcopy(_fixture("lcd-contador"))
    fixture["nets"] = [["uno.D12", f"lcd1.{bad_pin}"]]

    with pytest.raises(BuildError, match=bad_pin) as excinfo:
        fixture_to_model_call(fixture)
    assert "lcd1" in str(excinfo.value)


def test_r13_tipo_sin_did_es_build_error_antes_de_tocar_el_puente(monkeypatch):
    monkeypatch.setattr(
        builder_module,
        "DID_BY_TYPE",
        {k: v for k, v in DID_BY_TYPE.items() if k != "lcd-16x2"},
    )
    calls = []

    def call_tool(tool, arguments):
        calls.append((tool, arguments))
        return '{"success": true}'

    with pytest.raises(BuildError, match="DID") as excinfo:
        build_circuit(_fixture("lcd-contador"), "code", call_tool)
    assert "lcd-16x2" in str(excinfo.value)
    assert calls == []


# -------------------------------------------- refs: nets vs components

_HUMAN_WIRE_NAMES = {
    "GND": "Ground",
    "VDD": "Power",
    "VO": "Contrast",
    "RS": "Register Select",
    "RW": "Read/Write",
    "E": "Enable",
    "LED+": "LED Anode",
    "LED-": "LED Cathode",
}

_LCD_HOLES = {
    "GND": "1j", "VDD": "2j", "VO": "3j", "RS": "4j", "RW": "5j", "E": "6j",
    "DB4": "11j", "DB5": "12j", "DB6": "13j", "DB7": "14j",
    "LED+": "15j", "LED-": "16j",
}

UNO_INSTANCE = "uno_a"
BB_INSTANCE = "bb_a"
LCD_INSTANCE = "lcd_a"
RESISTOR_INSTANCE = "r_a"


def _endpoint(instance_id, pin):
    return {"component": instance_id, "pin": pin, "instance_id": instance_id}


def _hand_built_inspect(pin_names=None):
    """Inspect de lcd-contador armado a mano (sin Tinkercad).

    Usa los huecos del layout (LCD anclado en 1j) y los offsets reales del
    builder: GND=1j .. LED-=16j para el LCD y 19g/23g para la resistencia.
    ``pin_names`` reetiqueta los pines del LCD como lo hacen los cables.
    """
    names = dict(pin_names or {})
    wires = []

    def wire(source, target):
        wires.append(
            {"source": _endpoint(*source), "target": _endpoint(*target)}
        )

    # Pata de la parte -> hueco (lo que el puente agrega al colocarla).
    for pin, hole in _LCD_HOLES.items():
        wire((LCD_INSTANCE, names.get(pin, pin)), (BB_INSTANCE, hole))
    wire((RESISTOR_INSTANCE, "Terminal 1"), (BB_INSTANCE, "19g"))
    wire((RESISTOR_INSTANCE, "Terminal 2"), (BB_INSTANCE, "23g"))

    # 5V -> VDD del LCD -> pin 1 de la resistencia.
    wire((UNO_INSTANCE, "5V"), (BB_INSTANCE, "2j"))
    wire((BB_INSTANCE, "2j"), (BB_INSTANCE, "19g"))
    # Net de GND con sus 5 endpoints encadenados por la protoboard.
    wire((BB_INSTANCE, "1j"), (BB_INSTANCE, "3j"))
    wire((BB_INSTANCE, "3j"), (BB_INSTANCE, "5j"))
    wire((BB_INSTANCE, "5j"), (BB_INSTANCE, "16j"))
    wire((BB_INSTANCE, "16j"), (UNO_INSTANCE, "GND"))
    # LED+ por la resistencia de 220.
    wire((BB_INSTANCE, "23g"), (BB_INSTANCE, "15j"))
    # Senales del modo 4 bits.
    wire((UNO_INSTANCE, "D12"), (BB_INSTANCE, "4j"))
    wire((UNO_INSTANCE, "D11"), (BB_INSTANCE, "6j"))
    wire((UNO_INSTANCE, "D5"), (BB_INSTANCE, "11j"))
    wire((UNO_INSTANCE, "D4"), (BB_INSTANCE, "12j"))
    wire((UNO_INSTANCE, "D3"), (BB_INSTANCE, "13j"))
    wire((UNO_INSTANCE, "D2"), (BB_INSTANCE, "14j"))

    return {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": UNO_INSTANCE, "pins": []},
            {"type": "Breadboard Small", "instance_id": BB_INSTANCE, "pins": []},
            {"type": "LCD 16 x 2", "instance_id": LCD_INSTANCE, "pins": []},
            {"type": "Resistor", "instance_id": RESISTOR_INSTANCE, "pins": []},
        ],
        "wires": wires,
    }


def test_r13_refs_de_derive_nets_y_normalize_coinciden_para_el_lcd():
    inspect = _hand_built_inspect()
    normalized = normalize_circuit(inspect, {"nets": []})
    nets = derive_nets(inspect)

    normalized_refs = {c["ref"] for c in normalized["components"]}
    assert normalized_refs == {"uno", "lcd1", "r1"}
    derived_refs = {endpoint.split(".", 1)[0] for net in nets for endpoint in net}
    assert derived_refs == normalized_refs
    # Ni el fallback "lcd16x21" ni el slug crudo del type.
    assert not {ref for ref in derived_refs if ref.startswith("lcd")} - {"lcd1"}
    assert "lcd16x21" not in derived_refs

    # Cada pata cableada aparece bajo el ref que normalize le dio.
    assert any("lcd1.VDD" in net for net in nets)
    assert any("r1.2" in net and "lcd1.LED+" in net for net in nets)


def test_r13_alias_humanos_de_los_cables_dan_las_mismas_nets():
    identity = derive_nets(_hand_built_inspect())
    human = derive_nets(_hand_built_inspect(_HUMAN_WIRE_NAMES))
    lowercase = derive_nets(_hand_built_inspect({"GND": "gnd", "VDD": "vcc"}))

    # Los 8 nombres humanos y gnd/vcc no pueden abrir nets nuevas:
    # sin ese alias el LCD queda con los endpoints opacos y la
    # conectividad se cae aunque el cableado este perfecto.
    assert human == identity
    assert lowercase == identity
    assert any(
        {"lcd1.GND", "lcd1.VO", "lcd1.RW", "lcd1.LED-", "uno.GND1"} == set(net)
        for net in identity
    )


def test_r13_conectividad_lcd_contador_extremo_a_extremo_es_1_0():
    inspect = _hand_built_inspect()
    actual = {
        "components": normalize_circuit(inspect, {"nets": []})["components"],
        "nets": derive_nets(inspect),
    }
    expected = {
        "components": _fixture("lcd-contador")["components"],
        "nets": _fixture("lcd-contador")["nets"],
    }

    result = compare_connectivity(expected, actual)

    assert result["missing_components"] == []
    assert result["extra_components"] == []
    assert result["shorts"] == []
    assert result["components_score"] == 1.0
    assert result["connectivity_score"] == 1.0
    assert result["score"] == 1.0


# ----------------------------------------------------------- sketches

def test_r13_sketch_traza_y_display_usan_la_misma_variable():
    sketch = lcd_counter_sketch()

    # Un solo contador y una sola sentencia que lo incrementa.
    declarations = re.findall(r"unsigned long (\w+) = 0;", sketch)
    assert declarations == ["segundos"]
    assert sketch.count("segundos = segundos + 1;") == 1
    assert len(re.findall(r"segundos\s*=", sketch)) == 2  # declaracion + incremento

    # El display imprime un buffer construido a partir de ESA variable.
    fill = re.search(
        r'snprintf\((\w+), sizeof\(\1\), "t=%lus", (\w+)\);', sketch
    )
    assert fill, sketch
    buffer_name, printed_variable = fill.groups()
    assert printed_variable == "segundos"
    assert f"lcd.print({buffer_name});" in sketch
    assert f"lcd.print({printed_variable});" not in sketch

    # Y la traza del serial publica el mismo valor, no otro.
    trace = re.search(
        r'Serial\.print\("TEST:SEG="\);\s*Serial\.println\((\w+)\);', sketch
    )
    assert trace, sketch
    assert trace.group(1) == printed_variable


def test_r13_sketch_include_y_constructor_con_literales():
    sketch = lcd_counter_sketch()
    assert "#include <LiquidCrystal.h>" in sketch
    assert "LiquidCrystal lcd(12, 11, 5, 4, 3, 2);" in sketch
    assert "lcd.begin(16, 2);" in sketch
    assert sketch.count("#include <LiquidCrystal.h>") == 1

    custom = lcd_counter_sketch(rs=7, en=6, d4=9, d5=10, d6=11, d7=12)
    assert "LiquidCrystal lcd(7, 6, 9, 10, 11, 12);" in custom
    assert "LiquidCrystal lcd(12, 11, 5, 4, 3, 2);" not in custom


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"rs": 12, "en": 12}, "repetidos"),
        ({"d4": 5, "d5": 5}, "repetidos"),
        ({"rs": 1}, "fuera de"),
        ({"rs": 14}, "fuera de"),
        ({"d7": 0}, "fuera de"),
        ({"en": True}, "fuera de"),
        ({"d4": 12.0}, "fuera de"),
        ({"d5": "5"}, "fuera de"),
    ],
)
def test_r13_sketch_rechaza_pines_invalidos(kwargs, match):
    with pytest.raises(ValueError, match=match):
        lcd_counter_sketch(**kwargs)


@pytest.mark.parametrize("period_ms", [100, 60000, 1000])
def test_r13_sketch_acepta_periodos_en_rango_y_los_usa(period_ms):
    sketch = lcd_counter_sketch(period_ms=period_ms)
    assert f"delay({period_ms});" in sketch


@pytest.mark.parametrize("period_ms", [99, 60001, 0, -1000, True, False, 1000.0])
def test_r13_sketch_rechaza_periodos_fuera_de_rango(period_ms):
    with pytest.raises(ValueError, match="period_ms"):
        lcd_counter_sketch(period_ms=period_ms)


def test_r13_sketch_titulo_de_16_caracteres_pasa_y_17_no():
    sixteen = "0123456789ABCDEF"
    sketch = lcd_counter_sketch(title=sixteen)
    assert f'lcd.print("{sixteen}");' in sketch

    with pytest.raises(ValueError, match="16"):
        lcd_counter_sketch(title=sixteen + "G")


@pytest.mark.parametrize("title", ["", 'a"b', "a\\b", "a\nb", "a\rb", 7, None])
def test_r13_sketch_rechaza_titulos_peligrosos(title):
    with pytest.raises(ValueError, match="title"):
        lcd_counter_sketch(title=title)


# ---------------------- regresion de orden: mismo circuito, mismo score

def _emulate_inspect(fixture, declaration_order):
    """Inspect equivalente declarando las partes en otro orden."""
    layout = plan_layout(fixture)
    assert layout["unplaced"] == [], layout["unplaced"]
    placements = layout["placements"]
    type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}
    call = fixture_to_model_call(fixture)

    components = [
        {"type": "Arduino Uno R3", "instance_id": UNO_INSTANCE, "pins": []},
        {"type": "Breadboard Small", "instance_id": BB_INSTANCE, "pins": []},
    ]
    instance_by_ref = {}
    for ref in declaration_order:
        instance_by_ref[ref] = f"i_{ref}"
        components.append(
            {
                "type": _RAW_TYPE[type_by_ref[ref]],
                "instance_id": instance_by_ref[ref],
                "pins": [],
            }
        )

    wires = []

    def wire(source, target):
        wires.append(
            {"source": _endpoint(*source), "target": _endpoint(*target)}
        )

    for ref in declaration_order:
        wired_pins = {
            endpoint.split(".", 1)[1]
            for net in fixture["nets"]
            for endpoint in net
            if endpoint.split(".", 1)[0] == ref
        }
        for pin in sorted(wired_pins):
            hole = _translate_endpoint(f"{ref}.{pin}", placements, type_by_ref)
            wire(
                (instance_by_ref[ref], _REAL_PIN[type_by_ref[ref]][pin]),
                (BB_INSTANCE, hole),
            )

    for model_wire in call["wires"]:
        endpoints = []
        for text in (model_wire["from"], model_wire["to"]):
            if text.startswith("uno."):
                endpoints.append((UNO_INSTANCE, text.split(".", 1)[1]))
            elif re.fullmatch(r"\d+[a-j]", text):
                endpoints.append((BB_INSTANCE, text))
            else:
                ref, _, pin = text.partition(".")
                endpoints.append(
                    (
                        instance_by_ref[ref],
                        _REAL_PIN[type_by_ref[ref]][pin],
                    )
                )
        wire(endpoints[0], endpoints[1])

    return {"components": components, "wires": wires}


def _order_fixture():
    """Dos LEDs con resistencia: las resistencias son distinguibles."""
    return {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "r1", "type": "resistor"},
            {"ref": "led2", "type": "led"},
            {"ref": "r2", "type": "resistor"},
        ],
        "nets": [
            ["uno.D9", "r1.1"],
            ["r1.2", "led1.anode"],
            ["led1.cathode", "uno.GND1"],
            ["uno.D10", "r2.1"],
            ["r2.2", "led2.anode"],
            ["led2.cathode", "uno.GND1"],
        ],
    }


def _score(fixture, declaration_order):
    inspect = _emulate_inspect(fixture, declaration_order)
    actual = {
        "components": normalize_circuit(inspect, {"nets": []})["components"],
        "nets": derive_nets(inspect),
    }
    return compare_connectivity(fixture, actual)


def test_r13_el_orden_de_declaracion_no_cambia_el_score():
    fixture = _order_fixture()
    original = _score(fixture, ["led1", "r1", "led2", "r2"])
    assert original["score"] == 1.0, original
    assert original["shorts"] == []

    swapped = _score(fixture, ["led2", "r2", "led1", "r1"])
    interleaved = _score(fixture, ["r2", "led2", "r1", "led1"])

    for result in (swapped, interleaved):
        assert result["shorts"] == []
        assert result["connectivity_score"] == 1.0, result
        assert result["score"] == original["score"]

    # El orden cruzado cambia de verdad que ref tiene cada resistencia
    # fisica: el test tiene dientes, un emparejamiento posicional fallaria.
    crossed = _emulate_inspect(fixture, ["r2", "led2", "r1", "led1"])
    crossed_refs = [c["ref"] for c in normalize_circuit(crossed, {"nets": []})["components"]]
    assert crossed_refs == ["uno", "r1", "led1", "r2", "led2"]
