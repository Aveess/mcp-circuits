"""Tester independiente ronda 13: LCD 16x2 en modo 4 bits (nivel 5).

Contrato NUEVO de la fase 21 (verificado en vivo). El LCD 16x2 ya NO se
monta en la protoboard: su cuerpo mide ~25 columnas y tapaba las filas
f..c, asi que con el display puesto no se podia colocar junto a un sensor,
un boton ni un divisor. Ahora se emite SIEMPRE como modulo libre arriba de
la placa -- ``{"free": {"x": 1100, "y": -230, "angle": 0}}`` (x=1100 desde
la fase 36, para que el escape lateral no cruce el teclado), el segundo en
y=-430 -- sin ``pin`` ni ``at``, y sus cables van por terminal real
(``lcd1.RS``, ``lcd1.DB4``...) en vez de por huecos. Como consecuencia:
no reserva columnas (el primer bloque de placa arranca en la columna 1) y
no hay guarda de oclusion: piezo, LDR, ultrasonic, pushbutton, 3-pin y
L293D se colocan normalmente junto al LCD.

Tests reescritos en esta pasada (mismo poder de deteccion, contrato nuevo):

- geometria de 16 huecos en ``1j`` -> LCD libre con coordenadas exactas y
  cero consumo de columnas (comparado contra el mismo circuito sin LCD);
- part anclado en hueco con DID -> part ``free`` sin ``at``/``pin``;
- reserva de columnas y bisel -> el primer bloque de placa cae en columna 1;
- tipos ocluidos a ``unplaced`` y LDR ocluido arrastrando el divisor ->
  LCD + pushbutton / ultrasonic / LDR-divisor se colocan TODOS, sin solape
  de columnas ni huecos compartidos;
- segundo LCD sin colocar -> segundo LCD apilado en y=-430, ninguno
  ``unplaced``;
- "el LCD se coloca primero sin importar donde se declare" -> el LCD en
  cualquier posicion del array da el MISMO layout;
- "convive con partes libres" -> LCD, motor y bateria son libres y ninguno
  pisa la posicion de otro;
- "model call solo usa huecos" -> el LCD no tiene ``pin``/``at``, los
  huecos de las demas partes son validos (1-30, a-j) y los cables al LCD
  son terminales reales, nunca huecos;
- ancla distinta de "GND" -> solo aplica al camino de compatibilidad con
  ``at`` (la rama sigue en builder.py); en el camino libre un pin invalido
  ("DB9") sigue siendo BuildError.

Se mantienen de la ronda 13: fixture lcd-contador y component map, alias de
pines (Ground/Power/Contrast/Register Select/Read/Write/Enable/LED
Anode/LED Cathode y gnd/vcc), refs de ``derive_nets`` == ``normalize_circuit``,
``compare_connectivity == 1.0`` del fixture armando el inspect a mano,
BuildError de type sin DID antes de tocar el puente, validaciones del sketch
``lcd_counter`` e independencia de orden de declaracion.
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

# Orden fisico real de los 16 terminales del LCD, de izquierda a derecha.
# Tabla propia del tester (no se importa de produccion: si el builder cambia
# de orden o inventa un terminal, esto tiene que romperse). El LCD ya no se
# monta en la placa, pero el orden de sus terminales sigue siendo el mismo.
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


def _board_columns(fixture, ref):
    """Columnas de placa que ocupa ``ref`` (sus pines cableados)."""
    return {_col(hole) for hole in _holes(fixture, ref).values()}


def _assert_board_side_by_side(fixture, refs, allowed_column_sharing=()):
    """Ningun hueco de placa usado dos veces y columnas disjuntas.

    ``allowed_column_sharing`` son pares que comparten columna a proposito
    (un LED con su resistencia en serie: filas distintas, misma columna).
    """
    shared_ok = {frozenset(pair) for pair in allowed_column_sharing}
    used = {}
    for ref in refs:
        for pin, hole in _holes(fixture, ref).items():
            assert hole not in used, (ref, pin, hole, used.get(hole))
            used[hole] = (ref, pin)
    for index, ref in enumerate(refs):
        for other in refs[index + 1:]:
            if frozenset({ref, other}) in shared_ok:
                continue
            assert _board_columns(fixture, ref).isdisjoint(
                _board_columns(fixture, other)
            ), (ref, other)


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


# ------------------------------------------------- LCD como modulo libre

LCD_FREE_ABOVE = {"free": {"x": 1100, "y": -230, "angle": 0}}
LCD_FREE_STACKED = {"free": {"x": 1100, "y": -430, "angle": 0}}


def test_r13_el_lcd_es_un_modulo_libre_y_no_consume_columnas_de_placa():
    fixture = _fixture("lcd-contador")
    # El mismo circuito sin el display: no hay nada mas que cambie.
    without_lcd = {
        "components": [c for c in fixture["components"] if c["ref"] != "lcd1"],
        "nets": [],
    }

    layout = plan_layout(fixture)
    placement = layout["placements"]["lcd1"]

    # Coordenadas exactas del contrato y ni `at` ni `pin`: el display no se
    # monta en la placa, flota como modulo arriba de ella.
    assert placement == LCD_FREE_ABOVE
    assert set(placement) == {"free"}
    assert placement["free"]["angle"] == 0

    # Cero consumo de columnas: los placements de placa son identicos a los
    # del circuito sin LCD.
    board_only = {r: p for r, p in layout["placements"].items() if r != "lcd1"}
    assert board_only == plan_layout(without_lcd)["placements"]
    assert board_only["r1"] == {"at": "1g", "pin": "1", "angle": 90}
    assert _board_columns(fixture, "r1") == {1, 5}

    # Los 16 terminales se traducen al terminal real del display, nunca a
    # un hueco de la protoboard.
    type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}
    for pin in LCD_PINS:
        assert (
            _translate_endpoint(f"lcd1.{pin}", layout["placements"], type_by_ref)
            == f"lcd1.{pin}"
        )


def test_r13_parts_del_lcd_son_libres_y_conservan_el_did():
    parts = {
        p["ref"]: p for p in fixture_to_model_call(_fixture("lcd-contador"))["parts"]
    }
    assert parts["lcd1"] == {
        "ref": "lcd1",
        "did": 113878,
        "free": {"x": 1100, "y": -230},
        "angle": 0,
    }
    # Ni hueco ni ancla: el puente lo coloca por coordenadas.
    assert "at" not in parts["lcd1"]
    assert "pin" not in parts["lcd1"]
    # La resistencia si va en la placa, y su bloque arranca en la columna 1.
    assert parts["r1"] == {
        "ref": "r1",
        "did": 53184,
        "at": "1g",
        "pin": "1",
        "angle": 90,
    }
    # La traduccion de los pines cableados del LCD es identidad (terminal).
    type_by_ref = {c["ref"]: c["type"] for c in _fixture("lcd-contador")["components"]}
    placements = plan_layout(_fixture("lcd-contador"))["placements"]
    wired = {
        endpoint.split(".", 1)[1]
        for net in _fixture("lcd-contador")["nets"]
        for endpoint in net
        if endpoint.startswith("lcd1.")
    }
    for pin in wired:
        assert _translate_endpoint(f"lcd1.{pin}", placements, type_by_ref) == (
            f"lcd1.{pin}"
        )


# ------------------------------------------------------------- layout

def test_r13_el_primer_bloque_de_placa_arranca_en_la_columna_1():
    fixture = _fixture("lcd-contador")
    result = plan_layout(fixture)

    assert result["unplaced"] == []
    assert result["placements"]["lcd1"] == LCD_FREE_ABOVE
    # Ya no hay reserva de 16 columnas + bisel: la resistencia usa 1g.
    assert result["placements"]["r1"] == {"at": "1g", "pin": "1", "angle": 90}
    resistor_holes = _holes(fixture, "r1", pins=["1", "2"])
    assert resistor_holes == {"1": "1g", "2": "5g"}
    # Y la placa sigue cabiendo en el rango real de huecos.
    for hole in resistor_holes.values():
        assert 1 <= _col(hole) <= 30
        assert _row(hole) in "abcdefghij"


# Lo que antes quedaba ocluido por el cuerpo del display y ahora convive
# con el: boton, sensor ultrasonico y LDR con su divisor.
_LCD_COMPANION_CASES = {
    "pushbutton": (
        [{"ref": "btn1", "type": "pushbutton"}],
        [["uno.D2", "btn1.1"]],
    ),
    "ultrasonic-hcsr04": (
        [{"ref": "us1", "type": "ultrasonic-hcsr04"}],
        [["uno.D7", "us1.trig"], ["uno.D6", "us1.echo"]],
    ),
    "ldr-divisor": (
        [{"ref": "ldr1", "type": "photoresistor"}, {"ref": "rdiv", "type": "resistor"}],
        [["ldr1.2", "uno.A0", "rdiv.1"], ["uno.5V", "ldr1.1"]],
    ),
}


@pytest.mark.parametrize("case", sorted(_LCD_COMPANION_CASES))
def test_r13_con_lcd_los_vecinos_de_placa_se_colocan_todos(case):
    companions, nets = _LCD_COMPANION_CASES[case]
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "lcd1", "type": "lcd-16x2"},
        ]
        + companions,
        "nets": nets,
    }
    result = plan_layout(fixture)

    # Nada queda sin colocar y el LCD sigue siendo modulo libre.
    assert result["unplaced"] == []
    assert result["placements"]["lcd1"] == LCD_FREE_ABOVE
    assert set(result["placements"]) == {"lcd1"} | {
        c["ref"] for c in companions
    }
    for component in companions:
        assert "at" in result["placements"][component["ref"]], component["ref"]

    # Sin solape: ni huecos ni columnas compartidas entre las partes de placa.
    _assert_board_side_by_side(fixture, [c["ref"] for c in companions])

    # Y el circuito completo se puede construir.
    assert fixture_to_model_call(fixture)["parts"]


def test_r13_con_lcd_la_placa_entera_convive_sin_solape_de_columnas():
    """El caso que el cuerpo del display impedia: sensores + boton + LDR."""
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "lcd1", "type": "lcd-16x2"},
            {"ref": "btn1", "type": "pushbutton"},
            {"ref": "us1", "type": "ultrasonic-hcsr04"},
            {"ref": "ldr1", "type": "photoresistor"},
            {"ref": "rdiv", "type": "resistor"},
            {"ref": "led1", "type": "led"},
            {"ref": "rl1", "type": "resistor"},
        ],
        "nets": [
            ["uno.D2", "btn1.1"],
            ["uno.D7", "us1.trig"],
            ["uno.D6", "us1.echo"],
            ["ldr1.2", "uno.A0", "rdiv.1"],
            ["uno.5V", "ldr1.1"],
            ["uno.D9", "rl1.1"],
            ["rl1.2", "led1.anode"],
            ["led1.cathode", "uno.GND1"],
        ],
    }
    result = plan_layout(fixture)

    assert result["unplaced"] == []
    assert result["placements"]["lcd1"] == LCD_FREE_ABOVE
    board_refs = ["btn1", "us1", "ldr1", "rdiv", "led1", "rl1"]
    assert set(result["placements"]) == {"lcd1"} | set(board_refs)

    # El LED y su resistencia comparten columna a proposito; el resto no.
    _assert_board_side_by_side(
        fixture, board_refs, allowed_column_sharing=[("led1", "rl1")]
    )
    # Ningun bloque se sale de la placa.
    for ref in board_refs:
        for hole in _holes(fixture, ref).values():
            assert 1 <= _col(hole) <= 30, (ref, hole)
            assert _row(hole) in "abcdefghij", (ref, hole)

    call = fixture_to_model_call(fixture)
    parts = {p["ref"]: p for p in call["parts"]}
    assert "pin" not in parts["lcd1"] and "at" not in parts["lcd1"]
    assert all("at" in parts[ref] for ref in board_refs)


def test_r13_con_lcd_el_ldr_y_su_divisor_se_colocan_juntos():
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

    assert result["unplaced"] == []
    assert result["placements"]["lcd1"] == LCD_FREE_ABOVE

    ldr_holes = _holes(fixture, "ldr1", pins=["1", "2"])
    divider_holes = _holes(fixture, "rdiv", pins=["1", "2"])
    # El sensor sigue entrando en la placa: sus dos terminales caen en la
    # misma fila, en columnas consecutivas.
    assert _row(ldr_holes["1"]) == _row(ldr_holes["2"])
    assert _col(ldr_holes["2"]) == _col(ldr_holes["1"]) + 1
    # Y el divisor viaja con el: arranca despues del sensor, en su fila, y
    # el bloque entero no se sale del ancho que le toca.
    assert _col(divider_holes["1"]) > _col(ldr_holes["2"])
    assert _row(divider_holes["1"]) == _row(ldr_holes["1"])
    assert _col(divider_holes["1"]) - _col(ldr_holes["1"]) + 3 <= 8
    assert _col(divider_holes["2"]) <= 30

    _assert_board_side_by_side(fixture, ["ldr1", "rdiv"])
    assert fixture_to_model_call(fixture)["parts"]


def test_r13_dos_lcd_se_apilan_arriba_y_ninguno_queda_sin_colocar():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "lcd1", "type": "lcd-16x2"},
            {"ref": "lcd2", "type": "lcd-16x2"},
        ],
        "nets": [["uno.5V", "lcd1.VDD"], ["uno.5V", "lcd2.VDD"]],
    }
    result = plan_layout(fixture)

    assert result["unplaced"] == []
    assert result["placements"] == {
        "lcd1": LCD_FREE_ABOVE,
        "lcd2": LCD_FREE_STACKED,
    }
    # Mismo x, escalonado en y, mismo angulo: los cuerpos no se pisan.
    assert result["placements"]["lcd2"]["free"]["x"] == 1100
    assert (
        result["placements"]["lcd1"]["free"]["y"]
        - result["placements"]["lcd2"]["free"]["y"]
        == 200
    )

    parts = {p["ref"]: p for p in fixture_to_model_call(fixture)["parts"]}
    for ref in ("lcd1", "lcd2"):
        assert "at" not in parts[ref] and "pin" not in parts[ref]
        # Contrato del puente: `free` es {x, y} y el angulo va a nivel de
        # part. El placement interno del layout lo lleva dentro de `free`.
        placement_free = dict(result["placements"][ref]["free"])
        assert placement_free.pop("angle", None) == parts[ref].get("angle")
        assert parts[ref]["free"] == placement_free


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
    assert result["placements"]["lcd1"] == LCD_FREE_ABOVE
    # Bloque LED+resistencia en las primeras columnas, sin bisel de por medio.
    assert result["placements"]["r1"] == {"at": "1g", "pin": "1", "angle": 90}
    assert result["placements"]["led1"] == {
        "at": "5i", "pin": "anode", "angle": 180,
    }
    assert fixture_to_model_call(fixture)["parts"]

    # Ningun hueco usado por dos partes de placa distintas (el LCD no usa
    # huecos: sus cables son terminales).
    used = {}
    for ref in ("led1", "r1"):
        for pin, hole in _holes(fixture, ref).items():
            assert hole not in used, (ref, pin, hole, used.get(hole))
            used[hole] = (ref, pin)


def test_r13_el_lcd_da_igual_en_cualquier_posicion_del_array():
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
        assert result["placements"]["lcd1"] == LCD_FREE_ABOVE
        assert result["placements"]["r1"]["at"] == "1g"
        assert result["placements"]["led1"]["at"] == "5i"
    # Literalmente el mismo layout, sin importar el indice en el array.
    assert all(result == results[0] for result in results)


def test_r13_el_lcd_convive_con_las_partes_libres_sin_pisar_su_posicion():
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
    # Los tres son modulos libres, cada uno en su posicion.
    free_spots = [p["free"] for p in layout["placements"].values()]
    assert layout["placements"]["lcd1"] == LCD_FREE_ABOVE
    assert "free" in layout["placements"]["motor1"]
    assert "free" in layout["placements"]["bat1"]
    assert len(free_spots) == 3
    assert len({(spot["x"], spot["y"]) for spot in free_spots}) == 3

    parts = {p["ref"]: p for p in fixture_to_model_call(fixture)["parts"]}
    for ref in ("lcd1", "motor1", "bat1"):
        assert "at" not in parts[ref] and "pin" not in parts[ref]
    assert parts["lcd1"]["free"] == {"x": 1100, "y": -230}
    assert parts["lcd1"]["angle"] == 0


def test_r13_model_call_del_lcd_es_por_terminal_y_los_huecos_son_validos():
    call = fixture_to_model_call(_fixture("lcd-contador"))
    parts = {p["ref"]: p for p in call["parts"]}

    # El LCD no trae hueco ni ancla: se coloca por coordenadas.
    assert "at" not in parts["lcd1"]
    assert "pin" not in parts["lcd1"]
    assert parts["lcd1"]["free"] == {"x": 1100, "y": -230}
    assert parts["lcd1"]["angle"] == 0

    holes = set()
    lcd_terminals = set()
    for wire in call["wires"]:
        assert wire["from"] != wire["to"]
        for text in (wire["from"], wire["to"]):
            if text.startswith("uno."):
                continue
            if text.startswith("lcd1."):
                lcd_terminals.add(text.split(".", 1)[1])
                continue
            # Lo que no es el Uno ni el LCD tiene que ser un hueco real.
            match = re.fullmatch(r"([0-9]+)([a-j])", text)
            assert match, text
            assert 1 <= int(match.group(1)) <= 30, text
            holes.add(text)

    # Solo las dos patas de la resistencia tocan la protoboard.
    assert holes == {"1g", "5g"}
    # Y el LCD se cablea por sus terminales reales, nunca por huecos.
    assert lcd_terminals == {
        "GND", "VDD", "VO", "RS", "RW", "E",
        "DB4", "DB5", "DB6", "DB7", "LED+", "LED-",
    }
    assert lcd_terminals <= set(LCD_PINS)


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

def _patched_layout(monkeypatch, placements_by_ref):
    """Fuerza placements por ref (reemplaza, no fusiona) manteniendo el resto."""
    real_plan_layout = builder_module.plan_layout

    def patched(fixture):
        layout = real_plan_layout(fixture)
        placements = {ref: dict(p) for ref, p in layout["placements"].items()}
        for ref, placement in placements_by_ref.items():
            placements[ref] = dict(placement)
        return {"placements": placements, "unplaced": list(layout["unplaced"])}

    monkeypatch.setattr(builder_module, "plan_layout", patched)


def test_r13_camino_de_compatibilidad_con_at_exige_el_ancla_gnd(monkeypatch):
    """La rama vieja (LCD montado en la placa) sigue viva y sigue exigiendo GND."""
    fixture = _fixture("lcd-contador")

    # Con `at` y ancla GND el builder todavia deriva los 16 huecos.
    _patched_layout(
        monkeypatch, {"lcd1": {"at": "1j", "pin": "GND", "angle": 0}}
    )
    call = fixture_to_model_call(fixture)
    parts = {p["ref"]: p for p in call["parts"]}
    assert parts["lcd1"] == {
        "ref": "lcd1", "did": 113878, "at": "1j", "pin": "GND", "angle": 0,
    }
    texts = {text for wire in call["wires"] for text in (wire["from"], wire["to"])}
    # GND=1j, RS=4j, DB4=11j, LED-=16j: el ancla mas el offset de cada pin.
    assert {"1j", "4j", "11j", "16j"} <= texts

    # Cualquier otro ancla en ese camino tiene que explotar.
    for bad_anchor in ("VDD", "RS", "Ground", "1j"):
        _patched_layout(
            monkeypatch, {"lcd1": {"at": "1j", "pin": bad_anchor, "angle": 0}}
        )
        with pytest.raises(BuildError, match="ancla") as excinfo:
            fixture_to_model_call(fixture)
        assert "lcd1" in str(excinfo.value)


def test_r13_en_el_camino_libre_un_pin_invalido_sigue_siendo_build_error():
    fixture = copy.deepcopy(_fixture("lcd-contador"))
    # El layout por defecto es el libre: no hay `at`, solo terminales.
    assert plan_layout(fixture)["placements"]["lcd1"] == {
        "free": {"x": 1100, "y": -230, "angle": 0}
    }
    fixture["nets"] = [["uno.D12", "lcd1.DB9"]]

    with pytest.raises(BuildError, match="DB9") as excinfo:
        fixture_to_model_call(fixture)
    assert "lcd1" in str(excinfo.value)


@pytest.mark.parametrize("bad_pin", ["DB9", "Gnd", "gnd", "DB10", "LED"])
def test_r13_pin_desconocido_del_lcd_es_build_error(bad_pin):
    fixture = copy.deepcopy(_fixture("lcd-contador"))
    assert "free" in plan_layout(fixture)["placements"]["lcd1"]
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

UNO_INSTANCE = "uno_a"
BB_INSTANCE = "bb_a"
LCD_INSTANCE = "lcd_a"
RESISTOR_INSTANCE = "r_a"


def _endpoint(instance_id, pin):
    return {"component": instance_id, "pin": pin, "instance_id": instance_id}


def _hand_built_inspect(pin_names=None):
    """Inspect de lcd-contador armado a mano (sin Tinkercad).

    Contrato de la fase 21: el LCD es modulo libre, asi que sus cables van
    de terminal a terminal (o al hueco de la resistencia) y no pasan por
    huecos propios. La resistencia si esta en la placa (1g/5g).
    ``pin_names`` reetiqueta los pines del LCD como lo hacen los cables.
    """
    names = dict(pin_names or {})
    wires = []

    def wire(source, target):
        wires.append(
            {"source": _endpoint(*source), "target": _endpoint(*target)}
        )

    def lcd(pin):
        return (LCD_INSTANCE, names.get(pin, pin))

    # Pata de la resistencia -> sus dos huecos.
    wire((RESISTOR_INSTANCE, "Terminal 1"), (BB_INSTANCE, "1g"))
    wire((RESISTOR_INSTANCE, "Terminal 2"), (BB_INSTANCE, "5g"))

    # 5V -> VDD del LCD -> pata 1 de la resistencia (hueco 1g).
    wire((UNO_INSTANCE, "5V"), lcd("VDD"))
    wire(lcd("VDD"), (BB_INSTANCE, "1g"))
    # LED+ por la resistencia de 220 (pata 2 en 5g).
    wire(lcd("LED+"), (BB_INSTANCE, "5g"))
    # Net de GND con sus 5 endpoints, encadenados por los terminales.
    wire(lcd("GND"), lcd("VO"))
    wire(lcd("VO"), lcd("RW"))
    wire(lcd("RW"), lcd("LED-"))
    wire(lcd("LED-"), (UNO_INSTANCE, "GND"))
    # Senales del modo 4 bits, directo al terminal del display.
    wire((UNO_INSTANCE, "D12"), lcd("RS"))
    wire((UNO_INSTANCE, "D11"), lcd("E"))
    wire((UNO_INSTANCE, "D5"), lcd("DB4"))
    wire((UNO_INSTANCE, "D4"), lcd("DB5"))
    wire((UNO_INSTANCE, "D3"), lcd("DB6"))
    wire((UNO_INSTANCE, "D2"), lcd("DB7"))

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
