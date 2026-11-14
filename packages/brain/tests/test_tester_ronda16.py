"""Tester independiente ronda 16: fase 23 (contador 0-9 en display 7 segmentos).

No participe en el desarrollo de esta fase. Todo lo de abajo se verifico
leyendo el codigo real (``layout.py``, ``builder.py``, ``breadboard_nets.py``,
``sketches.py``, ``runner.py``) y comparandolo con el contrato declarado, con
tablas y oraculos PROPIOS: las geometrias (resistencia = 4 columnas, LED = 1,
piezo = 5, HC-SR04 = 4 consecutivas) y la tabla de digitos estan reescritas
aqui a mano. Si esas tablas cambian, estos tests tienen que romperse.

Contrato que se pone a prueba
-----------------------------
1. Desborde de resistencias sueltas a la fila ``e``: 4 bloques arriba (fila
   ``g``, columnas 1/7/13/19) y hasta 4 abajo (fila ``e``, mismas columnas).
   Con 5, 6, 7 y 8 no se repite ningun hueco, ninguno cae fuera de 1..30 y
   ninguno pisa los huecos de un bloque LED ni el cuerpo del piezo. Con 9 o
   mas la sobrante se reporta en ``unplaced`` y no se coloca "como sea".
2. Regresion: las 15 fixtures anteriores (todas con <= 4 resistencias
   sueltas) siguen dando EXACTAMENTE los mismos placements de resistencia
   que antes de la fase 23, y ninguna desborda a la fila ``e`` salvo el
   divisor del LDR, que ya vivia ahi.
3. Alias del display: ``A..G``/``a..g``, ``DP``/``dp``, ``Common``/``com1``.
   Un pin desconocido NO se traduce a un segmento real; ``Common`` repetido
   en dos cables distintos no se pierde ni inventa una net: se unifica, que
   es lo que hace el cobre.
4. ``seven_seg_sketch``: pines 2..13 sin repetir, ``hold_ms`` en rango, y una
   tabla de exactamente 10 digitos de 7 bits igual a la de un display de 7
   segmentos estandar (orden a b c d e f g).
5. ``fixture_to_model_call`` de ``siete-segmentos``: 8 parts (el Uno lo crea
   el puente), 15 wires, display libre con ``angle`` a NIVEL DE PART y
   ``free`` reducido a ``{x, y}``.
6. La condicion nueva del runner: con una parte libre no se "repara" (rebuild
   solo de cables); sin partes libres el camino de reparacion sigue igual.

Hallazgos (detalle en el reporte de la ronda):

* MEDIA/ALTA: la suite del repo ya viene ROJA en HEAD (2 fallos ajenos a este
  archivo, ver ``tests/test_tester_ronda14.py`` y ``ronda15``: esperan 15
  filas en ``docs/benchmark.md`` y la fase 23 agrego la 16). Ninguno de estos
  tests depende de eso.
* MEDIA: el oraculo prometido ``TEST:DIGITO=0..9`` no cabe en la ventana de
  5 s del runner con ``hold_ms=1000``: la evidencia guardada solo trae 0..4.
* BAJA: el docstring de ``seven_seg_sketch`` dice "catodo comun" mientras el
  codigo emitido escribe para anodo comun.
* BAJA/latente: el display (y=-200) y el LCD (y=-230) comparten x=870 y solo
  los separan 30 px, con un paso de apilado de 200 px para cada modulo.

Correcciones aplicadas tras esta ronda (los tests de arriba se dejaron sin
``xfail`` porque ahora pasan):

* los dos tests del benchmark que fijaban 15 filas se actualizaron a 16;
* ``hold_ms`` bajo a 400 ms, asi que el ciclo de 10 digitos (4 s) cabe en la
  ventana de 5 s del runner y el oraculo ve 0..9;
* docstring y comentario de ``SEVEN_SEG_DIGITS`` dicen anodo comun;
* LCD y display comparten un unico apilado ``FREE_MODULE_*``: el display
  solo pasa a ``y=-230`` y, si coinciden, el segundo sube 200 px;
* ``PIN_TABLE`` ya tiene ``seven-segment`` y ``lcd-16x2``, asi que la spec
  tambien rechaza un pin inventado.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import BuildError, fixture_to_model_call
from tinkercad_brain.fase0.component_map import TYPE_MAP, fixture_type
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.runner import run_build
from tinkercad_brain.sketches import SEVEN_SEG_DIGITS, seven_seg_sketch
from tinkercad_brain.spec import SpecError, validate_spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_PATH = ROOT / "fixtures" / "fase0" / "circuits.json"
REPORT_PATH = ROOT / "docs" / "reportes" / "siete-segmentos.md"
BENCHMARK_PATH = ROOT / "docs" / "benchmark.md"
VIVO_PATH = ROOT / "docs" / "fase0-vivo.md"

SEVEN_SEG_FIXTURE = "siete-segmentos"
DISPLAY_DID = 129710
# Ventana que el runner deja correr la simulacion (runner.py:
# ``start_simulation`` con ``wait_seconds``).
RUNNER_SIMULATION_WINDOW_MS = 5000
# Pasos de apilado de los modulos libres, leidos de layout.py.
FREE_MODULE_STEP_Y = 200

HOLE_RE = re.compile(r"([1-9]|[12][0-9]|30)([a-j])")
COLUMN_RE = re.compile(r"(\d+)([a-j])")

# Tabla de digitos propia, escrita a mano con el orden fisico a b c d e f g.
# Es la de cualquier display de 7 segmentos: 1 = segmento encendido.
OWN_DIGITS = (
    "1111110",  # 0
    "0110000",  # 1
    "1101101",  # 2
    "1111001",  # 3
    "0110011",  # 4
    "1011011",  # 5
    "1011111",  # 6
    "1110000",  # 7
    "1111111",  # 8
    "1111011",  # 9
)

# Placements de TODAS las resistencias de las 15 fixtures previas a la fase
# 23. Congelados antes de tocar nada de esta ronda: es el contrato que el
# desborde a la fila ``e`` no podia romper.
RESISTOR_PLACEMENTS_BEFORE_PHASE23 = {
    "blink-basico": {"r1": {"at": "1g", "pin": "1", "angle": 90}},
    "boton-pullup": {"r1": {"at": "1g", "pin": "1", "angle": 90}},
    "semaforo-3-leds": {
        "r1": {"at": "1g", "pin": "1", "angle": 90},
        "r2": {"at": "7g", "pin": "1", "angle": 90},
        "r3": {"at": "13g", "pin": "1", "angle": 90},
    },
    "servo-potenciometro": {},
    "sensor-ultrasonico": {"r1": {"at": "1g", "pin": "1", "angle": 90}},
    "buzzer-activo": {},
    "ldr-divisor": {
        "r1": {"at": "1g", "pin": "1", "angle": 90},
        # Resistencia del divisor: viaja con el LDR desde antes de la fase 23.
        "r2": {"at": "25e", "pin": "1", "angle": 90},
    },
    "motor-dc-transistor": {"r1": {"at": "1g", "pin": "1", "angle": 90}},
    "led-rgb": {
        "r1": {"at": "1g", "pin": "1", "angle": 90},
        "r2": {"at": "4h", "pin": "1", "angle": 90},
        "r3": {"at": "3j", "pin": "1", "angle": 90},
    },
    "temperatura-tmp36": {"r1": {"at": "1g", "pin": "1", "angle": 90}},
    "motor-l293d-bateria": {},
    "parking-servo-ultrasonico-rgb": {
        "r1": {"at": "1g", "pin": "1", "angle": 90},
        "r2": {"at": "4h", "pin": "1", "angle": 90},
        "r3": {"at": "3j", "pin": "1", "angle": 90},
    },
    "lcd-contador": {"r1": {"at": "1g", "pin": "1", "angle": 90}},
    "lcd-temperatura": {"r1": {"at": "1g", "pin": "1", "angle": 90}},
    "lcd-distancia": {"r1": {"at": "1g", "pin": "1", "angle": 90}},
}

# Nombre real del display en inspect (evidencia de la fase 23).
RAW_DISPLAY_TYPE = "7 Segment Display"


# ------------------------------------------------------------- utilidades

def _fixtures():
    return json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))


def _fixture(fixture_id=SEVEN_SEG_FIXTURE):
    return next(c for c in _fixtures() if c["id"] == fixture_id)


def _resistor_fixture(count, extra=(), nets=None):
    """Fixture minima: el Uno, ``count`` resistencias sueltas y extras."""
    components = [{"ref": "uno", "type": "arduino-uno"}]
    components.extend(copy.deepcopy(list(extra)))
    components.extend(
        {"ref": f"r{index}", "type": "resistor"} for index in range(1, count + 1)
    )
    return {"components": components, "nets": nets or []}


def _types(fixture):
    return {c["ref"]: c["type"] for c in fixture["components"]}


def _resistor_placements(fixture):
    types = _types(fixture)
    placements = plan_layout(fixture)["placements"]
    return {ref: p for ref, p in placements.items() if types[ref] == "resistor"}


def _column(anchor):
    match = COLUMN_RE.fullmatch(anchor)
    assert match is not None, anchor
    return int(match.group(1)), match.group(2)


def _pin_holes(fixture):
    """{ref: {pin: hueco}} con geometria PROPIA (no la tabla del builder).

    Solo cubre los tipos que usa esta ronda: resistencia angle 90 (pin 2 a +4
    columnas, misma fila), LED (catodo a +1), piezo (negativo a +5), HC-SR04
    (4 pines consecutivos) y LDR (pin 2 a +1).
    """
    placements = plan_layout(fixture)["placements"]
    types = _types(fixture)
    holes = {}
    for ref, placement in placements.items():
        if "at" not in placement:
            continue  # modulo libre: no toca la placa
        column, row = _column(placement["at"])
        ctype = types[ref]
        if ctype == "resistor":
            assert placement["angle"] == 90, placement
            holes[ref] = {"1": f"{column}{row}", "2": f"{column + 4}{row}"}
        elif ctype == "led":
            holes[ref] = {"anode": f"{column}{row}", "cathode": f"{column + 1}{row}"}
        elif ctype == "buzzer":
            holes[ref] = {
                "positive": f"{column}{row}",
                "negative": f"{column + 5}{row}",
            }
        elif ctype == "ultrasonic-hcsr04":
            holes[ref] = {
                pin: f"{column + offset}{row}"
                for offset, pin in enumerate(("vcc", "trig", "echo", "gnd"))
            }
        elif ctype == "photoresistor":
            holes[ref] = {"1": f"{column}{row}", "2": f"{column + 1}{row}"}
    return holes


def _assert_no_shared_holes(fixture):
    owner = {}
    for ref, pins in _pin_holes(fixture).items():
        for pin, hole in pins.items():
            assert HOLE_RE.fullmatch(hole), (ref, pin, hole)
            assert hole not in owner, (hole, owner[hole], (ref, pin))
            owner[hole] = (ref, pin)
    return owner


def _segment_to_dpin(fixture):
    """{segmento: numero de pin digital} leido de las nets de la fixture."""
    nets = fixture["nets"]
    resistor_to_pin = {}
    for net in nets:
        for endpoint in net:
            match = re.fullmatch(r"uno\.D(\d+)", endpoint)
            if not match:
                continue
            other = [e for e in net if e != endpoint]
            for candidate in other:
                ref, _, pin = candidate.partition(".")
                if pin == "1":
                    resistor_to_pin[ref] = int(match.group(1))
    mapping = {}
    for net in nets:
        pins = [e.split(".", 1) for e in net if "." in e]
        segments = [pin for ref, pin in pins if ref == "seg"]
        resistors = [ref for ref, pin in pins if pin == "2" and ref in resistor_to_pin]
        for segment in segments:
            if resistors:
                mapping[segment] = resistor_to_pin[resistors[0]]
    return mapping


def _digits_table_from_code(code):
    rows = re.findall(
        r"^\s*\{([01]), ([01]), ([01]), ([01]), ([01]), ([01]), ([01])\},\s+//\s*(\d+)$",
        code,
        re.M,
    )
    table = {}
    for *bits, digit in rows:
        table[int(digit)] = "".join(bits)
    return table


def _pines_from_code(code):
    match = re.search(r"const byte PINES\[7\] = \{([^}]*)\};", code)
    assert match is not None, code
    return [int(value) for value in match.group(1).split(",")]


def _display_inspect(seg_pin, uno_pin="D2", extra_wires=()):
    components = [
        {"type": "Arduino Uno R3", "instance_id": "uno", "pins": []},
        {"type": RAW_DISPLAY_TYPE, "instance_id": "seg", "pins": []},
    ]
    wires = [
        {
            "source": {
                "component": "Arduino Uno R3", "instance_id": "uno", "pin": uno_pin,
            },
            "target": {
                "component": RAW_DISPLAY_TYPE, "instance_id": "seg", "pin": seg_pin,
            },
        }
    ]
    wires.extend(extra_wires)
    return {"components": components, "wires": wires}


def _display_nets(seg_pin, uno_pin="D2", extra_wires=()):
    return derive_nets(_display_inspect(seg_pin, uno_pin, extra_wires))


def _sin_acentos(text):
    """El documento vivo escribe "ánodo común"; los asserts no llevan tilde."""
    table = str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU")
    return text.translate(table)


# -------------------------------- 1. desborde de resistencias a la fila e

def test_r16_cuatro_resistencias_sueltas_caben_arriba_en_la_fila_g():
    layout = plan_layout(_resistor_fixture(4))

    assert layout["unplaced"] == []
    assert {ref: p["at"] for ref, p in layout["placements"].items()} == {
        "r1": "1g",
        "r2": "7g",
        "r3": "13g",
        "r4": "19g",
    }


def test_r16_la_quinta_resistencia_abre_la_fila_e_en_la_columna_1():
    layout = plan_layout(_resistor_fixture(5))

    assert layout["unplaced"] == []
    assert layout["placements"]["r5"] == {"at": "1e", "pin": "1", "angle": 90}
    # Las cuatro de arriba no se mueven por el desborde.
    assert [layout["placements"][f"r{i}"]["at"] for i in range(1, 5)] == [
        "1g", "7g", "13g", "19g",
    ]


@pytest.mark.parametrize("count", [5, 6, 7, 8])
def test_r16_de_cinco_a_ocho_resistencias_desbordan_sin_repetir_hueco(count):
    layout = plan_layout(_resistor_fixture(count))
    anchors = {
        ref: p["at"] for ref, p in layout["placements"].items()
    }

    assert layout["unplaced"] == []
    assert len(anchors) == count
    assert len(set(anchors.values())) == count, anchors
    rows = [anchor[-1] for anchor in anchors.values()]
    assert rows.count("g") == 4, anchors
    assert rows.count("e") == count - 4, anchors
    # Columnas del contrato: 1, 7, 13, 19 en cada fila.
    assert sorted(
        int(anchor[:-1]) for anchor in anchors.values() if anchor.endswith("g")
    ) == [1, 7, 13, 19]
    assert sorted(
        int(anchor[:-1]) for anchor in anchors.values() if anchor.endswith("e")
    ) == [1, 7, 13, 19][: count - 4]
    # Ni un hueco (pin 1 ni pin 2) compartido entre dos resistencias.
    _assert_no_shared_holes(_resistor_fixture(count))


@pytest.mark.parametrize("count", [5, 6, 7, 8])
def test_r16_una_resistencia_desbordada_no_saca_su_pata_de_la_placa(count):
    layout = plan_layout(_resistor_fixture(count))

    for ref, placement in layout["placements"].items():
        column, row = _column(placement["at"])
        assert row in ("e", "g"), (ref, placement)
        assert 1 <= column <= 30, (ref, placement)
        # pin 1 y pin 2 (a +4 columnas) tienen que caber en la placa.
        assert column + 4 <= 30, (ref, placement)


@pytest.mark.parametrize("count,unplaced", [(9, ["r9"]), (10, ["r9", "r10"])])
def test_r16_mas_de_ocho_resistencias_se_reportan_como_unplaced(count, unplaced):
    layout = plan_layout(_resistor_fixture(count))

    assert layout["unplaced"] == unplaced
    for ref in unplaced:
        assert ref not in layout["placements"]
    placed = {ref: p["at"] for ref, p in layout["placements"].items()}
    assert len(placed) == 8
    assert len(set(placed.values())) == 8


def test_r16_el_desborde_no_pisa_los_huecos_de_un_bloque_led():
    extra = [
        {"ref": "led1", "type": "led"},
        {"ref": "ra", "type": "resistor"},
        {"ref": "led2", "type": "led"},
        {"ref": "rb", "type": "resistor"},
    ]
    nets = [["ra.2", "led1.anode"], ["rb.2", "led2.anode"]]
    fixture = _resistor_fixture(5, extra=extra, nets=nets)

    layout = plan_layout(fixture)
    assert layout["unplaced"] == []
    # Los dos LED siguen en la fila i y las sueltas ya desbordaron a la e.
    assert layout["placements"]["led1"]["at"] == "5i"
    assert layout["placements"]["led2"]["at"] == "11i"
    assert [
        layout["placements"][f"r{i}"]["at"] for i in range(1, 6)
    ] == ["13g", "19g", "1e", "7e", "13e"]

    owner = _assert_no_shared_holes(fixture)
    led_holes = {
        hole
        for ref in ("led1", "led2")
        for hole in _pin_holes(fixture)[ref].values()
    }
    assert led_holes == {"5i", "6i", "11i", "12i"}
    for ref in ("r1", "r2", "r3", "r4", "r5", "ra", "rb"):
        assert led_holes.isdisjoint(_pin_holes(fixture)[ref].values()), ref
    assert len(owner) == len(set(owner))


def test_r16_ocho_resistencias_no_pisan_el_disco_del_piezo():
    fixture = _resistor_fixture(8, extra=[{"ref": "bz1", "type": "buzzer"}])
    layout = plan_layout(fixture)

    assert layout["unplaced"] == []
    assert layout["placements"]["bz1"] == {"at": "25e", "pin": "positive", "angle": 0}
    holes = _pin_holes(fixture)
    piezo = set(holes["bz1"].values())
    assert piezo == {"25e", "30e"}
    for index in range(1, 9):
        assert piezo.isdisjoint(holes[f"r{index}"].values()), index
    _assert_no_shared_holes(fixture)


def test_r16_el_desborde_es_determinista_y_no_depende_del_orden():
    fixture = _resistor_fixture(7)

    first = plan_layout(copy.deepcopy(fixture))
    second = plan_layout(copy.deepcopy(fixture))
    assert first == second

    reversed_fixture = copy.deepcopy(fixture)
    reversed_fixture["components"] = (
        reversed_fixture["components"][:1]
        + list(reversed(reversed_fixture["components"][1:]))
    )
    shuffled = plan_layout(reversed_fixture)
    assert sorted(p["at"] for p in shuffled["placements"].values()) == sorted(
        p["at"] for p in first["placements"].values()
    )


def test_r16_el_desborde_no_archiva_el_display_ni_la_quinta_resistencia():
    """Caso real de la fase: 7 resistencias sueltas + display libre = 7 + 0."""
    fixture = _fixture()
    layout = plan_layout(fixture)

    assert layout["unplaced"] == []
    rows = [layout["placements"][f"r{i}"]["at"][-1] for i in range(1, 8)]
    assert rows.count("g") == 4
    assert rows.count("e") == 3
    assert "free" in layout["placements"]["seg"]


# ------------------------- 2. regresion de las fixtures anteriores

@pytest.mark.parametrize(
    "fixture_id,expected", sorted(RESISTOR_PLACEMENTS_BEFORE_PHASE23.items())
)
def test_r16_las_fixtures_previas_conservan_sus_resistencias(fixture_id, expected):
    """<= 4 resistencias sueltas: misma fila g y mismas columnas que antes."""
    assert _resistor_placements(_fixture(fixture_id)) == expected


@pytest.mark.parametrize(
    "fixture_id", sorted(RESISTOR_PLACEMENTS_BEFORE_PHASE23)
)
def test_r16_ninguna_fixture_previa_desborda_a_la_fila_e(fixture_id):
    """La fila e solo la usa el divisor del LDR, como antes de la fase 23."""
    placements = _resistor_placements(_fixture(fixture_id))
    on_row_e = {
        ref: placement
        for ref, placement in placements.items()
        if placement["at"].endswith("e")
    }

    if fixture_id == "ldr-divisor":
        assert on_row_e == {"r2": {"at": "25e", "pin": "1", "angle": 90}}
    else:
        assert on_row_e == {}, (fixture_id, on_row_e)


@pytest.mark.parametrize(
    "fixture_id", sorted(RESISTOR_PLACEMENTS_BEFORE_PHASE23)
)
def test_r16_las_fixtures_previas_no_ganan_unplaced(fixture_id):
    assert plan_layout(_fixture(fixture_id))["unplaced"] == []


# -------------------------------- 3. alias de pines del display

@pytest.mark.parametrize(
    "raw_pin,expected",
    [
        ("A", "a"), ("B", "b"), ("C", "c"), ("D", "d"),
        ("E", "e"), ("F", "f"), ("G", "g"),
        ("a", "a"), ("b", "b"), ("g", "g"),
        ("DP", "dp"), ("dp", "dp"),
        ("Common", "com1"), ("Common 1", "com1"), ("Common 2", "com2"),
        ("com1", "com1"), ("com2", "com2"),
    ],
)
def test_r16_alias_de_pines_del_display(raw_pin, expected):
    assert _display_nets(raw_pin) == [[f"sevensegment1.{expected}", "uno.D2"]]


@pytest.mark.parametrize("pair", [("A", "a"), ("B", "b"), ("G", "g"), ("E", "e")])
def test_r16_el_alias_del_display_acepta_mayuscula_y_minuscula(pair):
    upper, lower = pair
    assert _display_nets(upper) == _display_nets(lower)


def test_r16_el_pin_common_repetido_en_dos_cables_unifica_la_net():
    """El mismo pin fisico en dos cables: una sola net, con lo que cuelga.

    Si un lado va a 5V y el otro a GND, el resultado es UN nodo con 5V y GND:
    el corto es visible para ``compare_connectivity`` (no se pierde).
    """
    extra = [
        {
            "source": {
                "component": "Arduino Uno R3", "instance_id": "uno", "pin": "GND1",
            },
            "target": {
                "component": RAW_DISPLAY_TYPE, "instance_id": "seg", "pin": "Common",
            },
        }
    ]
    nets = _display_nets("Common", uno_pin="5V", extra_wires=extra)

    assert len(nets) == 1, nets
    assert nets[0] == ["sevensegment1.com1", "uno.5V", "uno.GND1"]


def test_r16_el_pin_common_repetido_no_duplica_nets():
    extra = [
        {
            "source": {
                "component": "Arduino Uno R3", "instance_id": "uno", "pin": "5V",
            },
            "target": {
                "component": RAW_DISPLAY_TYPE, "instance_id": "seg", "pin": "Common",
            },
        }
    ]
    nets = _display_nets("Common", uno_pin="5V", extra_wires=extra)

    assert nets == [["sevensegment1.com1", "uno.5V"]]


@pytest.mark.parametrize("raw_pin", ["h", "H", "zzz", "Dp", "COMMON", "Common1"])
def test_r16_un_pin_desconocido_del_display_no_se_inventa(raw_pin):
    """Ni se traduce a un segmento real ni se pierde: queda tal cual."""
    nets = _display_nets(raw_pin)
    segments = set("abcdefg") | {"dp", "com1", "com2"}

    assert len(nets) == 1
    pin = nets[0][0].split(".", 1)[1]
    assert pin == raw_pin, nets
    assert pin not in segments, nets


# ------------------------------------- 4. seven_seg_sketch

@pytest.mark.parametrize(
    "overrides",
    [
        {"a": 1}, {"g": 14}, {"a": 0}, {"g": 20},
        {"a": True}, {"d": 2.5}, {"f": "7"},
    ],
)
def test_r16_el_sketch_rechaza_pines_fuera_de_rango(overrides):
    with pytest.raises(ValueError):
        seven_seg_sketch(**overrides)


@pytest.mark.parametrize(
    "overrides",
    [
        {"a": 2, "b": 2},
        {"g": 8, "f": 8},
        {"c": 5},
    ],
)
def test_r16_el_sketch_rechaza_pines_repetidos(overrides):
    with pytest.raises(ValueError):
        seven_seg_sketch(**overrides)


@pytest.mark.parametrize("hold_ms", [0, -1, 60001, True, "1000", 1.5])
def test_r16_el_sketch_rechaza_hold_ms_invalido(hold_ms):
    with pytest.raises(ValueError):
        seven_seg_sketch(hold_ms=hold_ms)


def test_r16_el_sketch_acepta_los_limites_de_pin_y_de_hold_ms():
    code = seven_seg_sketch(a=2, b=3, c=4, d=5, e=6, f=7, g=13, hold_ms=60000)
    assert _pines_from_code(code) == [2, 3, 4, 5, 6, 7, 13]
    assert "delay(60000);" in code


def test_r16_la_tabla_del_sketch_tiene_los_diez_digitos_correctos():
    code = seven_seg_sketch()
    table = _digits_table_from_code(code)

    assert sorted(table) == list(range(10))
    assert [table[digit] for digit in range(10)] == list(OWN_DIGITS)
    assert all(len(pattern) == 7 for pattern in table.values())
    assert len(set(table.values())) == 10  # ningun digito se repite
    assert table[0][6] == "0" and table[8] == "1111111"
    assert table[1] == "0110000"  # solo b y c


def test_r16_la_constante_de_digitos_coincide_con_la_tabla_emitida():
    code = seven_seg_sketch()
    table = _digits_table_from_code(code)

    assert [table[d] for d in range(10)] == [
        "".join(str(bit) for bit in pattern) for pattern in SEVEN_SEG_DIGITS
    ]
    assert len(SEVEN_SEG_DIGITS) == 10
    assert all(len(pattern) == 7 for pattern in SEVEN_SEG_DIGITS)


def test_r16_el_sketch_escribe_para_anodo_comun():
    code = seven_seg_sketch()

    # Comun a 5V: el segmento se enciende en LOW, asi que la salida invierte.
    assert "!DIGITOS[digito][i]" in code
    assert "anodo comun" in code.lower()
    assert "digitalWrite(PINES[i], DIGITOS[digito][i])" not in code
    assert "pinMode(PINES[i], OUTPUT);" in code
    assert "TEST:7SEG=LISTO" in code
    assert "TEST:DIGITO=" in code


def test_r16_los_pines_del_sketch_coinciden_con_el_cableado_de_la_fixture():
    """Contrato entre capas: si la tabla de pines no sigue los cables, el
    contador muestra el digito equivocado aunque la conectividad de 100%."""
    fixture = _fixture()
    segments = _segment_to_dpin(fixture)
    pines = _pines_from_code(seven_seg_sketch())

    assert sorted(segments) == list("abcdefg")
    assert pines == [segments[segment] for segment in "abcdefg"]
    assert pines == [2, 3, 4, 5, 6, 7, 8]


def test_r16_el_sketch_declara_las_features_de_la_fixture():
    fixture = _fixture()
    code = seven_seg_sketch()

    for feature in fixture["code_features"]:
        assert feature in code, feature


def test_r16_el_component_map_conocen_el_display_y_su_did():
    assert TYPE_MAP[RAW_DISPLAY_TYPE] == "seven-segment"
    assert fixture_type(RAW_DISPLAY_TYPE) == "seven-segment"
    assert fixture_type("7 segment display") == "seven-segment"


def test_r16_el_docstring_del_sketch_no_contradice_el_anodo_comun():
    docstring = seven_seg_sketch.__doc__ or ""

    assert "anodo" in docstring.lower(), docstring
    assert "catodo" not in docstring.lower(), docstring


# ------------------------------ 5. fixture_to_model_call del display

def test_r16_la_fixture_del_display_se_traduce_en_8_parts_y_15_cables():
    call = fixture_to_model_call(_fixture())

    assert len(call["parts"]) == 8  # el Uno lo crea el puente
    assert len(call["wires"]) == 15
    refs = [part["ref"] for part in call["parts"]]
    assert sorted(refs) == ["r1", "r2", "r3", "r4", "r5", "r6", "r7", "seg"]
    for wire in call["wires"]:
        assert set(wire) == {"from", "to", "color"}
        assert wire["from"] != wire["to"]


def test_r16_el_display_va_libre_con_el_angulo_a_nivel_de_part():
    call = fixture_to_model_call(_fixture())
    part = next(p for p in call["parts"] if p["ref"] == "seg")

    assert part == {
        "ref": "seg",
        "did": DISPLAY_DID,
        "free": {"x": 870, "y": -230},
        "angle": 0,
    }
    assert set(part["free"]) == {"x", "y"}


def test_r16_los_cables_del_display_terminan_en_sus_terminales_reales():
    call = fixture_to_model_call(_fixture())
    display_pins = sorted(
        endpoint.split(".", 1)[1]
        for wire in call["wires"]
        for endpoint in (wire["from"], wire["to"])
        if endpoint.startswith("seg.")
    )

    # Siete segmentos + el comun: ni un pin inventado.
    assert display_pins == ["a", "b", "c", "com1", "d", "e", "f", "g"]
    power = [
        wire for wire in call["wires"] if "uno.5V" in (wire["from"], wire["to"])
    ]
    assert len(power) == 1
    assert set(power[0].values()) == {"seg.com1", "uno.5V", "red"}


def test_r16_los_huecos_de_las_resistencias_son_validos_y_unicos():
    call = fixture_to_model_call(_fixture())
    resistors = [p for p in call["parts"] if p["did"] == 53184]

    anchors = [part["at"] for part in resistors]
    assert len(anchors) == len(set(anchors)) == 7
    for anchor in anchors:
        assert HOLE_RE.fullmatch(anchor), anchor
        column, _row = _column(anchor)
        assert column + 4 <= 30, anchor
    for wire in call["wires"]:
        for endpoint in (wire["from"], wire["to"]):
            if endpoint.startswith("seg."):
                continue
            assert HOLE_RE.fullmatch(endpoint) or endpoint.startswith("uno."), endpoint


def test_r16_el_builder_rechaza_un_pin_inventado_del_display():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "seg", "type": "seven-segment"},
        ],
        "nets": [["uno.D9", "seg.zzz"]],
    }

    with pytest.raises(BuildError) as error:
        fixture_to_model_call(fixture)
    assert "seg.zzz" in str(error.value)


def test_r16_el_display_usa_los_diez_terminales_cuando_se_cablean():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "seg", "type": "seven-segment"},
        ],
        "nets": [
            ["uno.D2", "seg.a"], ["uno.D3", "seg.b"], ["uno.D4", "seg.c"],
            ["uno.D5", "seg.d"], ["uno.D6", "seg.e"], ["uno.D7", "seg.f"],
            ["uno.D8", "seg.g"], ["uno.D9", "seg.dp"],
            ["seg.com1", "uno.5V"], ["seg.com2", "uno.GND1"],
        ],
    }
    call = fixture_to_model_call(fixture)
    pairs = {(w["from"], w["to"]): w["color"] for w in call["wires"]}

    assert len(call["parts"]) == 1  # solo el display: el Uno no es part
    assert pairs[("seg.com1", "uno.5V")] == "red"
    assert pairs[("seg.com2", "uno.GND1")] == "black"
    assert ("uno.D9", "seg.dp") in pairs


def test_r16_nueve_resistencias_no_se_construyen_a_medias():
    fixture = _fixture()
    fixture["components"].append({"ref": "r8", "type": "resistor"})
    fixture["components"].append({"ref": "r9", "type": "resistor"})

    with pytest.raises(BuildError) as error:
        fixture_to_model_call(fixture)
    assert "sin layout para" in str(error.value)
    assert "r9" in str(error.value)


def test_r16_el_model_call_no_es_una_spec_y_la_spec_si_caza_pines_mudos():
    """Dos capas distintas, documentadas aqui para que nadie las confunda.

    El model call del puente usa ``did``; la spec declarativa usa ``type``.
    ``validate_spec`` rechaza el model call por construccion (no es un bug de
    esta fase). La spec, en cambio, ya tiene ``PIN_TABLE`` para
    ``seven-segment``: un pin inventado del display se rechaza igual que en
    el builder.
    """
    call = fixture_to_model_call(_fixture())

    with pytest.raises(Exception) as error:
        validate_spec(
            {
                "parts": call["parts"],
                "wires": [[w["from"], w["to"]] for w in call["wires"]],
            }
        )
    assert "type desconocido" in str(error.value)

    translated = [
        {
            "ref": part["ref"],
            "type": "seven-segment" if part["ref"] == "seg" else "resistor",
            **({"free": part["free"]} if "free" in part else {"at": part["at"]}),
            "pin": part.get("pin"),
            "angle": part["angle"],
        }
        for part in call["parts"]
    ]
    for part in translated:
        if part["pin"] is None:
            part.pop("pin")
    validated = validate_spec({"parts": translated, "wires": []})
    assert validated["parts"][0]["free"] == {"x": 870, "y": -230}

    # Un pin que el display no tiene (ni el builder ni la spec lo aceptan).
    with pytest.raises(SpecError) as invented:
        validate_spec(
            {
                "parts": [
                    {"ref": "seg", "type": "seven-segment",
                     "free": {"x": 870, "y": -230}},
                ],
                "wires": [["seg.zzz", "uno.D2"]],
            }
        )
    assert "zzz" in str(invented.value)


# --------------------------------------------------- 6. runner: partes libres

def _fake_call_tool(inspect_data=None):
    calls = []

    def call_tool(tool, arguments):
        calls.append((tool, arguments))
        if tool == "tinkercad_list_circuits":
            return json.dumps({"circuits": []})
        if tool == "tinkercad_create_circuit":
            return json.dumps({"circuit_id": "abc123XYZ"})
        if tool == "tinkercad_inspect_circuit":
            return json.dumps(inspect_data if inspect_data is not None else {})
        if tool == "tinkercad_read_serial_monitor":
            return "TEST:7SEG=LISTO\n"
        return json.dumps({"success": True, "persisted": True})

    call_tool.calls = calls
    return call_tool


def _builds(call_tool):
    return [c for c in call_tool.calls if c[0] == "tinkercad_build_circuit_model"]


def test_r16_con_parte_libre_el_runner_no_intenta_reparar():
    call_tool = _fake_call_tool()

    result = run_build(_fixture(), None, call_tool, "Siete segmentos")

    assert result["fidelity"]["score"] < 0.99
    assert result["fidelity"]["shorts"] == []
    assert result["repair_attempted"] is False
    assert result["fidelity_before_repair"] is None
    assert len(_builds(call_tool)) == 1
    assert result["ok"] is False


def test_r16_sin_partes_libres_el_runner_sigue_reparando():
    call_tool = _fake_call_tool()

    result = run_build(_fixture("blink-basico"), None, call_tool, "Blink")

    assert result["repair_attempted"] is True
    assert result["fidelity_before_repair"]["score"] < 0.99
    builds = _builds(call_tool)
    assert len(builds) == 2
    assert builds[1][1]["parts"] == []
    assert "clear_existing" not in builds[1][1]


def test_r16_cualquier_parte_libre_desactiva_la_reparacion_no_solo_el_display():
    """Alcance real de la condicion: motor DC y bateria tambien son ``free``.

    ``motor-dc-transistor`` no tiene display y aun asi ya no repara. Es la
    consecuencia (razonable: el borrado limpio tambien se lleva el motor) pero
    conviene tenerla clavada porque afecta a 4 de las 16 fixtures.
    """
    call_tool = _fake_call_tool()

    result = run_build(
        _fixture("motor-dc-transistor"), None, call_tool, "Motor"
    )

    assert result["repair_attempted"] is False
    assert len(_builds(call_tool)) == 1


def test_r16_solo_el_display_libre_basta_para_desactivar_la_reparacion():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "seg", "type": "seven-segment"},
            {"ref": "r1", "type": "resistor"},
        ],
        "nets": [["uno.D2", "r1.1"], ["r1.2", "seg.a"], ["seg.com1", "uno.5V"]],
    }
    call_tool = _fake_call_tool()

    result = run_build(fixture, None, call_tool, "Display suelto")

    assert result["repair_attempted"] is False
    assert len(_builds(call_tool)) == 1


# ------------------------------------------- 7. docs y evidencia guardada

def test_r16_el_benchmark_lista_los_circuitos_y_el_display_al_100():
    text = BENCHMARK_PATH.read_text(encoding="utf-8")
    rows = re.findall(r"^\|\s*(\d+)\s*\|", text, re.M)

    # La fase 24 agrego la fila 17: el benchmark crece con cada fase.
    assert [int(number) for number in rows] == list(range(1, 21))
    line = next(line for line in text.splitlines() if "gfgLntRuWJv" in line)
    assert "100%" in line
    assert "7 segmentos" in line


def test_r16_el_reporte_guardado_es_del_circuito_y_del_100():
    text = REPORT_PATH.read_text(encoding="utf-8")

    assert "gfgLntRuWJv" in text
    assert "100.0%" in text
    assert "Sin fallos" in text


def test_r16_el_oraculo_prometido_cubre_de_0_a_9():
    code = seven_seg_sketch()
    delays = [int(value) for value in re.findall(r"delay\((\d+)\);", code)]
    assert delays == [400]
    cycle_ms = len(OWN_DIGITS) * delays[0]
    assert cycle_ms <= RUNNER_SIMULATION_WINDOW_MS, (
        f"el ciclo completo son {cycle_ms} ms y la ventana del runner es "
        f"{RUNNER_SIMULATION_WINDOW_MS} ms"
    )

    report = REPORT_PATH.read_text(encoding="utf-8")
    for digit in range(10):
        assert f"TEST:DIGITO={digit}" in report, digit


def test_r16_el_documento_vivo_trae_la_fase_23_y_sus_dos_lecciones():
    text = _sin_acentos(VIVO_PATH.read_text(encoding="utf-8"))
    parts = text.split("## Fase 23", 1)

    assert len(parts) == 2, "falta la seccion de la fase 23"
    body = parts[1].split("\n## ", 1)[0]
    assert "gfgLntRuWJv" in body
    assert "anodo comun" in body.lower()
    assert "fila `e`" in body
    assert "A..G" in body and "Common" in body


# --------------------------- 8. modulos libres: apilado del display

def test_r16_dos_displayes_libres_se_apilan_sin_compartir_posicion():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "seg1", "type": "seven-segment"},
            {"ref": "seg2", "type": "seven-segment"},
        ],
        "nets": [],
    }
    placements = plan_layout(fixture)["placements"]

    first = placements["seg1"]["free"]
    second = placements["seg2"]["free"]
    assert first["x"] == second["x"] == 870
    assert first["y"] - second["y"] == FREE_MODULE_STEP_Y
    assert len({(f["x"], f["y"]) for f in (first, second)}) == 2


def test_r16_lcd_y_display_no_comparten_el_mismo_espacio_libre():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "lcd1", "type": "lcd-16x2"},
            {"ref": "seg", "type": "seven-segment"},
        ],
        "nets": [],
    }
    placements = plan_layout(fixture)["placements"]
    lcd = placements["lcd1"]["free"]
    display = placements["seg"]["free"]

    assert (lcd["x"], lcd["y"]) != (display["x"], display["y"])
    assert abs(lcd["y"] - display["y"]) >= FREE_MODULE_STEP_Y, (lcd, display)
