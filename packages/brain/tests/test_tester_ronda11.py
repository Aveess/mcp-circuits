"""Tester independiente ronda 11: LED del ultrasonico, TMP36 y layout.

Contratos nuevos juzgados sin repetir los tests de produccion:
- La traza TEST:LED y el digitalWrite del LED deben ser la MISMA
  comparacion (misma variable, operador y umbral, ramas no invertidas).
- led_pin no puede pisar trig ni echo (como el resto de sketches, que
  rechazan pines repetidos: un echo en OUTPUT rompe pulseIn).
- En el loop, la distancia se calcula ANTES de escribir el LED.
- tmp36 default: la variable comparada contra 20 es la que sale de la
  formula (volts - 0.5) * 100 encadenada desde analogRead.
- Layout: un cursor ya en 20 no retrocede a 18; en 28 el sensor no
  entra; LED y ultrasonico quedan separados >= 12 columnas.
- CLI: select_code de sensor-ultrasonico trae TEST:LED=.
"""
import importlib.util
import json
import re
from pathlib import Path

import pytest

from tinkercad_brain.layout import plan_layout
from tinkercad_brain.sketches import tmp36_sketch, ultrasonic_sketch

ROOT = Path(__file__).resolve().parents[1]
REAL_FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture(fixture_id):
    circuits = json.loads(REAL_FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == fixture_id)


def _load_demo():
    spec = importlib.util.spec_from_file_location(
        "demo_build_r11", ROOT / "scripts" / "demo_build.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _col(at):
    return int(at[:-1])


def _loop(sketch):
    return sketch.split("void loop() {", 1)[1]


# -------------------------------------------- misma comparacion LED/traza

_LED_WRITE = re.compile(
    r"digitalWrite\((\d+),\s*(.+?)\s*\?\s*HIGH\s*:\s*LOW\)"
)
_LED_TRACE = re.compile(
    r'Serial\.println\((.+?)\s*\?\s*"TEST:LED=ON"\s*:\s*"TEST:LED=OFF"\)'
)


def _led_conditions(sketch):
    write = _LED_WRITE.search(sketch)
    trace = _LED_TRACE.search(sketch)
    assert write is not None, "sin digitalWrite ternario del LED"
    assert trace is not None, "sin traza TEST:LED=ON/OFF ternaria"
    return int(write.group(1)), write.group(2).strip(), trace.group(1).strip()


@pytest.mark.parametrize(
    "kwargs, led_pin, threshold_text",
    [
        ({}, 13, "40.0"),
        ({"trig": 8, "echo": 12, "led_pin": 9, "threshold_cm": 25.5}, 9, "25.5"),
        ({"threshold_cm": 2.0}, 13, "2.0"),
        ({"threshold_cm": 400.0}, 13, "400.0"),
        ({"led_pin": 5, "threshold_cm": 17}, 5, "17.0"),
    ],
)
def test_r11_led_write_y_traza_son_la_misma_comparacion(kwargs, led_pin, threshold_text):
    pin, write_cond, trace_cond = _led_conditions(ultrasonic_sketch(**kwargs))
    assert pin == led_pin
    # Si difieren en umbral/operador, el oraculo serial miente sobre el LED.
    assert write_cond == trace_cond
    assert write_cond == f"distancia < {threshold_text}"


def test_r11_defaults_led_13_y_umbral_40_en_ambas_ramas():
    sketch = ultrasonic_sketch()
    assert "pinMode(13, OUTPUT)" in sketch
    pin, write_cond, trace_cond = _led_conditions(sketch)
    assert pin == 13
    assert write_cond == trace_cond == "distancia < 40.0"


# ------------------------------------------------------- pines pisados

@pytest.mark.parametrize(
    "kwargs",
    [
        {"led_pin": 7},                      # == trig default
        {"led_pin": 6},                      # == echo default (INPUT pisado a OUTPUT)
        {"trig": 8, "echo": 12, "led_pin": 8},
        {"trig": 8, "echo": 12, "led_pin": 12},
    ],
)
def test_r11_led_pin_igual_a_trig_o_echo_es_rechazado(kwargs):
    with pytest.raises(ValueError):
        ultrasonic_sketch(**kwargs)


# ------------------------------------------------------------ bordes

@pytest.mark.parametrize("threshold_cm", [2, 2.0, 400, 400.0])
def test_r11_umbrales_borde_2_y_400_pasan_en_write_y_traza(threshold_cm):
    _, write_cond, trace_cond = _led_conditions(
        ultrasonic_sketch(threshold_cm=threshold_cm)
    )
    assert write_cond == trace_cond


@pytest.mark.parametrize("threshold_cm", [1.9, 1.99, 400.01, 401])
def test_r11_umbrales_fuera_de_2_a_400_no_pasan(threshold_cm):
    with pytest.raises(ValueError):
        ultrasonic_sketch(threshold_cm=threshold_cm)


# ------------------------------------------------- orden en el loop

@pytest.mark.parametrize(
    "kwargs", [{}, {"trig": 8, "echo": 12, "led_pin": 9, "threshold_cm": 10.0}]
)
def test_r11_distancia_se_calcula_antes_de_escribir_el_led(kwargs):
    loop = _loop(ultrasonic_sketch(**kwargs))
    i_pulse = loop.index("pulseIn(")
    i_dist = loop.index("float distancia =")
    i_write = loop.index("digitalWrite(", loop.index("float distancia ="))
    # El primer digitalWrite tras medir es el del LED; antes estan los del trig.
    led_pin = kwargs.get("led_pin", 13)
    assert f"digitalWrite({led_pin}," in loop[i_dist:]
    i_led_write = loop.index(f"digitalWrite({led_pin},", i_dist)
    i_trace = loop.index("TEST:LED=ON")
    assert i_pulse < i_dist < i_led_write < i_trace
    assert i_write == i_led_write


def test_r11_ningun_write_del_led_antes_de_medir_en_el_loop():
    loop = _loop(ultrasonic_sketch())
    before_measure = loop.split("float distancia =", 1)[0]
    assert "digitalWrite(13," not in before_measure
    assert "TEST:LED" not in before_measure


# ---------------------------------------------------------------- tmp36

def test_r11_tmp36_default_umbral_20_sobre_la_temp_de_la_formula():
    sketch = tmp36_sketch()
    lectura = re.search(r"int (\w+) = analogRead\(A0\);", sketch)
    volts = re.search(r"float (\w+) = (\w+) \* 5\.0/1023\.0;", sketch)
    temp = re.search(r"float (\w+) = \((\w+) - 0\.5\) \* 100\.0;", sketch)
    write = re.search(r"digitalWrite\(13, (\w+) > ([\d.]+) \? HIGH : LOW\)", sketch)
    assert lectura and volts and temp and write
    # Cadena de datos: analogRead -> volts -> temp -> comparacion.
    assert volts.group(2) == lectura.group(1)
    assert temp.group(2) == volts.group(1)
    assert write.group(1) == temp.group(1)
    assert write.group(2) == "20.0"
    # La traza publica la misma variable que decide el LED.
    assert f"Serial.println({temp.group(1)});" in sketch


# ---------------------------------------------------------------- layout

def _led_blocks(count):
    components = [{"ref": "uno", "type": "arduino-uno"}]
    nets = []
    for i in range(1, count + 1):
        components += [
            {"ref": f"led{i}", "type": "led"},
            {"ref": f"r{i}", "type": "resistor"},
        ]
        nets.append([f"r{i}.2", f"led{i}.anode"])
    return components, nets


def test_r11_ultrasonico_con_cursor_en_20_no_retrocede_a_18():
    components, nets = _led_blocks(3)  # cursor tras bloques: 19
    components += [
        {"ref": "btn1", "type": "pushbutton"},  # ocupa 19 -> cursor 20
        {"ref": "us1", "type": "ultrasonic-hcsr04"},
    ]
    result = plan_layout({"components": components, "nets": nets})
    assert result["placements"]["btn1"]["at"] == "19f"  # cursor queda en 20
    us_at = result["placements"]["us1"]["at"]
    assert _col(us_at) == 20
    assert _col(us_at) >= 18
    us_cols = set(range(_col(us_at), _col(us_at) + 4))
    assert us_cols.isdisjoint(range(1, 20))  # ni bloques LED ni boton
    assert result["unplaced"] == []


def test_r11_ultrasonico_con_cursor_en_28_no_entra():
    components, nets = _led_blocks(4)  # cursor tras bloques: 25
    components += [
        {"ref": f"btn{i}", "type": "pushbutton"} for i in range(1, 4)
    ]  # ocupan 25, 26, 27 -> cursor 28
    components.append({"ref": "us1", "type": "ultrasonic-hcsr04"})
    result = plan_layout({"components": components, "nets": nets})
    assert result["placements"]["btn3"]["at"] == "27f"  # cursor queda en 28
    assert "us1" not in result["placements"]  # 28..31 excede la columna 30
    assert result["unplaced"] == ["us1"]


def test_r11_led_y_ultrasonico_separados_al_menos_12_columnas():
    result = plan_layout(_fixture("sensor-ultrasonico"))
    led_col = _col(result["placements"]["led1"]["at"])
    us_col = _col(result["placements"]["us1"]["at"])
    assert us_col >= 18
    assert us_col - led_col >= 12


# ------------------------------------------------------------------- CLI

def test_r11_select_code_sensor_ultrasonico_trae_oraculo_led():
    demo = _load_demo()
    code = demo.select_code(demo.find_fixture("sensor-ultrasonico"))
    assert code is not None
    assert "TEST:LED=" in code
    assert "TEST:DIST=" in code
    assert code == ultrasonic_sketch()
