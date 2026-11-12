"""Tester independiente ronda 6: sampler_client + sketches.

Adversarial, sin repetir las suites existentes. Los tests con prefijo
test_BUG_ documentan un fallo esperado: deben fallar hasta que
produccion se corrija (bug = test que falla + reporte).
"""
import json
import re

import pytest

from tinkercad_brain.sampler_client import simulate_and_verify, to_verifier_format
from tinkercad_brain.sketches import blink_sketch, pin_of_fixture, traffic_sketch
from tinkercad_brain.verifier import default_blink_contract, evaluate_contract


def _fake(payload, calls=None):
    def call(tool, arguments):
        if calls is not None:
            calls.append((tool, arguments))
        return payload if isinstance(payload, str) else json.dumps(payload)

    return call


def _good_payload(**overrides):
    payload = {
        "samples": [
            {"at_ms": 250, "led": {"on": True, "level": 0.9}, "sim_time": "00:00:00"},
            {"at_ms": 750, "led": {"on": False, "level": 0.0}, "sim_time": "00:00:01"},
        ],
        "serial": "READY\n",
        "errors": [],
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------- simulate_and_verify
def test_BUG_r6_errors_no_vacios_con_samples_buenas_no_debe_pasar():
    """El puente reporta errors no vacios: aunque las samples presentes
    cumplan el contrato, el resultado no puede ser passed=True en
    silencio. Esas samples pueden ser parciales/viejas; hoy simulate
    las evalua, pasa, y el error solo queda escondido dentro de raw."""
    payload = _good_payload(errors=["LED component not found in simulation"])
    result = simulate_and_verify(_fake(payload), default_blink_contract())
    assert result["passed"] is False


def test_r6_salida_json_lista_en_vez_de_dict_falla_sin_lanzar():
    result = simulate_and_verify(_fake('[{"at_ms": 250}]'), default_blink_contract())
    assert result["passed"] is False
    assert result["results"] == []
    assert "not a JSON object" in result["error"]


def test_r6_assertion_repetida_se_pide_una_sola_vez_y_se_evalua_dos_veces():
    calls = []
    assertion = {"type": "led", "ref": "led1", "at_ms": 250, "expect_on": True}
    contract = {"assertions": [dict(assertion), dict(assertion)]}
    result = simulate_and_verify(_fake(_good_payload(), calls), contract)
    assert calls[0][1]["samples_ms"] == [250]
    assert [r["ok"] for r in result["results"]] == [True, True]
    assert result["passed"] is True


def test_r6_at_ms_compartido_entre_tipos_usa_la_misma_muestra():
    calls = []
    contract = {
        "assertions": [
            {"type": "led", "ref": "led1", "at_ms": 250, "expect_on": True},
            {"type": "led_level", "ref": "led1", "at_ms": 250, "min_level": 0.5},
        ]
    }
    result = simulate_and_verify(_fake(_good_payload(), calls), contract)
    assert calls[0][1]["samples_ms"] == [250]
    assert result["passed"] is True


def test_r6_led_ref_distinto_del_default_extremo_a_extremo():
    contract = {
        "assertions": [
            {"type": "led", "ref": "led_rojo", "at_ms": 250, "expect_on": True},
            {"type": "led", "ref": "led_rojo", "at_ms": 750, "expect_on": False},
        ]
    }
    result = simulate_and_verify(_fake(_good_payload()), contract, led_ref="led_rojo")
    assert result["passed"] is True
    assert [r["ok"] for r in result["results"]] == [True, True]


# ---------------------------------------------------------- to_verifier_format
def test_r6_sample_sin_led_queda_sin_refs_y_el_verifier_falla_sin_lanzar():
    out = to_verifier_format({"samples": [{"at_ms": 250, "sim_time": "t"}], "serial": "x"})
    assert out["samples"] == [
        {"at_ms": 250, "sim_time": "t", "leds": {}, "servos": {}}
    ]
    contract = {
        "assertions": [{"type": "led", "ref": "led1", "at_ms": 250, "expect_on": True}]
    }
    result = evaluate_contract(contract, out)
    assert result["passed"] is False
    assert "missing led ref" in result["results"][0]["detail"]


def test_r6_led_sin_level_deja_none_y_solo_falla_la_assertion_de_nivel():
    out = to_verifier_format({"samples": [{"at_ms": 250, "led": {"on": True}}]})
    assert out["samples"][0]["leds"] == {"led1": {"on": True, "level": None}}
    contract = {
        "assertions": [
            {"type": "led", "ref": "led1", "at_ms": 250, "expect_on": True},
            {"type": "led_level", "ref": "led1", "at_ms": 250, "min_level": 0.5},
        ]
    }
    result = evaluate_contract(contract, out)
    assert [r["ok"] for r in result["results"]] == [True, False]
    assert result["passed"] is False


def test_r6_sim_time_ausente_queda_none_y_no_bloquea_la_evaluacion():
    out = to_verifier_format(
        {"samples": [{"at_ms": 250, "led": {"on": True, "level": 1.0}}]}
    )
    assert out["samples"][0]["sim_time"] is None
    contract = {
        "assertions": [{"type": "led", "ref": "led1", "at_ms": 250, "expect_on": True}]
    }
    assert evaluate_contract(contract, out)["passed"] is True


# ------------------------------------------------------------------- sketches
def test_r6_blink_on_ms_en_el_techo_exacto_60000_con_pin_13():
    sketch = blink_sketch(pin=13, on_ms=60000, off_ms=1)
    lines = [line.strip() for line in sketch.splitlines()]
    high = lines.index("digitalWrite(13, HIGH);")
    low = lines.index("digitalWrite(13, LOW);")
    assert lines[high + 1] == 'Serial.println("TEST:ON");'
    assert lines[high + 2] == "delay(60000);"
    assert lines[low + 2] == "delay(1);"


def test_r6_traffic_red_en_cero_es_rechazado():
    with pytest.raises(ValueError, match="pin fuera de 2..13"):
        traffic_sketch(red=0, yellow=10, green=9)


def test_r6_traffic_pines_permutados_apaga_los_otros_dos_en_cada_fase():
    sketch = traffic_sketch(red=9, yellow=11, green=10)
    writes = [
        (int(pin), level)
        for pin, level in re.findall(r"digitalWrite\((\d+), (HIGH|LOW)\)", sketch)
    ]
    assert writes == [
        (9, "HIGH"), (11, "LOW"), (10, "LOW"),
        (9, "LOW"), (11, "HIGH"), (10, "LOW"),
        (9, "LOW"), (11, "LOW"), (10, "HIGH"),
    ]


def test_r6_pin_of_fixture_cadena_rota_en_el_segundo_tramo():
    # Hay pin -> r1.1, pero r1.2 nunca llega al anodo (el anodo va a GND):
    # sin el tramo r1.2 -> led.anode no hay cadena y no debe mapear.
    fixture = {
        "nets": [
            ["uno.D13", "r1.1"],
            ["led1.anode", "uno.GND1"],
            ["led1.cathode", "uno.GND1"],
        ]
    }
    assert pin_of_fixture(fixture) == {}


def test_BUG_r6_dos_leds_compartiendo_resistencia_conserva_ambos():
    """r1.2 alimenta el anodo de led1 y de led2 (paralelo con una sola
    resistencia serie): ambos LEDs estan en el pin 13. Hoy el mapeo
    intermedio indexado por resistencia sobrescribe uno con el otro y
    sobrevive solo el ultimo segun el orden de las nets: un LED queda
    invisible para cualquier verificacion posterior."""
    for second, first in (("led1", "led2"), ("led2", "led1")):
        fixture = {
            "nets": [
                ["uno.D13", "r1.1"],
                ["r1.2", f"{second}.anode"],
                ["r1.2", f"{first}.anode"],
            ]
        }
        assert pin_of_fixture(fixture) == {"led1": 13, "led2": 13}


# --------------------------------------------------------------- consistencia
def test_r6_contrato_default_coincide_con_blink_500_500_documentado():
    """blink_sketch(13, 500, 500): HIGH en t=0, LOW en t=500, repite en
    t=1000. Los instantes del contrato default son los puntos medios
    (250 = mitad del ON, 750 = mitad del OFF), asi que coinciden."""
    sketch = blink_sketch(pin=13, on_ms=500, off_ms=500)
    assert [int(d) for d in re.findall(r"delay\((\d+)\)", sketch)] == [500, 500]
    contract = default_blink_contract()
    assert [(a["at_ms"], a["expect_on"]) for a in contract["assertions"]] == [
        (250, True),
        (750, False),
    ]
    assert 250 == 500 // 2
    assert 750 == 500 + 500 // 2
    sim = {
        "samples": [
            {"at_ms": 250, "sim_time": None, "leds": {"led1": {"on": True, "level": 1.0}}, "servos": {}},
            {"at_ms": 750, "sim_time": None, "leds": {"led1": {"on": False, "level": 0.0}}, "servos": {}},
        ],
        "serial": "",
    }
    assert evaluate_contract(contract, sim)["passed"] is True
