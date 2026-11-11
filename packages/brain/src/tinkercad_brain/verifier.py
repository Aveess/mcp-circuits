"""Verificador de contrato de comportamiento (v2 §10).

"Verificar" es comparar el comportamiento simulado contra assertions
con tolerancia, no declarar éxito sin oráculo.

Regla: un contrato sin assertions no verifica nada, por lo que
``evaluate_contract`` devuelve ``passed=False`` en ese caso.
Verificar sin oráculo es fe.
"""

from __future__ import annotations


def _samples_by_ms(sim_result):
    samples = {}
    if not isinstance(sim_result, dict):
        return samples
    raw = sim_result.get("samples")
    if not isinstance(raw, list):
        return samples
    for sample in raw:
        if isinstance(sample, dict) and "at_ms" in sample:
            samples[sample["at_ms"]] = sample
    return samples


def _eval_led(assertion, samples):
    at_ms = assertion.get("at_ms")
    ref = assertion.get("ref")
    sample = samples.get(at_ms)
    if sample is None:
        return False, f"missing sample at_ms={at_ms}"
    leds = sample.get("leds")
    if not isinstance(leds, dict) or ref not in leds:
        return False, f"missing led ref {ref!r} at_ms={at_ms}"
    entry = leds[ref]
    if not isinstance(entry, dict) or "on" not in entry:
        return False, f"missing 'on' for led ref {ref!r} at_ms={at_ms}"
    expect_on = assertion.get("expect_on")
    actual = entry["on"]
    if actual == expect_on:
        return True, f"led {ref!r} at_ms={at_ms} on={actual} as expected"
    return False, f"led {ref!r} at_ms={at_ms} on={actual}, expected on={expect_on}"


def _eval_led_level(assertion, samples):
    at_ms = assertion.get("at_ms")
    ref = assertion.get("ref")
    sample = samples.get(at_ms)
    if sample is None:
        return False, f"missing sample at_ms={at_ms}"
    leds = sample.get("leds")
    if not isinstance(leds, dict) or ref not in leds:
        return False, f"missing led ref {ref!r} at_ms={at_ms}"
    entry = leds[ref]
    if not isinstance(entry, dict) or "level" not in entry:
        return False, f"missing 'level' for led ref {ref!r} at_ms={at_ms}"
    min_level = assertion.get("min_level")
    level = entry["level"]
    try:
        ok = level >= min_level
    except TypeError:
        return False, f"invalid level/min_level for led ref {ref!r} at_ms={at_ms}"
    if ok:
        return True, f"led {ref!r} at_ms={at_ms} level={level} >= min_level={min_level}"
    return False, f"led {ref!r} at_ms={at_ms} level={level} < min_level={min_level}"


def _eval_servo(assertion, samples):
    at_ms = assertion.get("at_ms")
    ref = assertion.get("ref")
    sample = samples.get(at_ms)
    if sample is None:
        return False, f"missing sample at_ms={at_ms}"
    servos = sample.get("servos")
    if not isinstance(servos, dict) or ref not in servos:
        return False, f"missing servo ref {ref!r} at_ms={at_ms}"
    actual = servos[ref]
    angle = assertion.get("angle")
    tolerance = assertion.get("tolerance", 5)
    if tolerance is None:
        tolerance = 5
    try:
        diff = abs(actual - angle)
        ok = diff <= tolerance
    except TypeError:
        return False, f"invalid angle for servo ref {ref!r} at_ms={at_ms}"
    if ok:
        return True, f"servo {ref!r} at_ms={at_ms} angle={actual} within {tolerance} of {angle}"
    return False, f"servo {ref!r} at_ms={at_ms} angle={actual} differs from {angle} by {diff} > tolerance {tolerance}"


def _eval_serial(assertion, sim_result):
    text = assertion.get("text")
    if not isinstance(text, str):
        return False, "missing serial text in assertion"
    serial = sim_result.get("serial") if isinstance(sim_result, dict) else None
    if not isinstance(serial, str):
        return False, "missing serial output"
    if text in serial:
        return True, f"serial contains {text!r}"
    return False, f"serial does not contain {text!r}"


def evaluate_contract(contract: dict, sim_result: dict) -> dict:
    """Evalúa un contrato contra un resultado de simulación.

    Un contrato sin assertions devuelve ``passed=False`` (con
    ``results`` vacío): verificar sin oráculo es fe.

    Nunca lanza excepción por muestras/refs ausentes en
    ``sim_result``; esas assertions quedan con ``ok=False``.
    """
    assertions = []
    if isinstance(contract, dict):
        raw = contract.get("assertions")
        if isinstance(raw, list):
            assertions = raw

    samples = _samples_by_ms(sim_result)
    results = []
    for assertion in assertions:
        if not isinstance(assertion, dict):
            results.append({"assertion": assertion, "ok": False, "detail": "unknown assertion type"})
            continue
        atype = assertion.get("type")
        if atype == "led":
            ok, detail = _eval_led(assertion, samples)
        elif atype == "led_level":
            ok, detail = _eval_led_level(assertion, samples)
        elif atype == "servo":
            ok, detail = _eval_servo(assertion, samples)
        elif atype == "serial_contains":
            ok, detail = _eval_serial(assertion, sim_result)
        else:
            ok, detail = False, "unknown assertion type"
        results.append({"assertion": assertion, "ok": bool(ok), "detail": detail})

    passed = bool(results) and all(r["ok"] for r in results)
    return {"passed": passed, "results": results}


def default_blink_contract(ref: str = "led1") -> dict:
    """Contrato blink 500/500: on a mitad del primer estado, off a mitad del segundo."""
    return {
        "assertions": [
            {"type": "led", "ref": ref, "at_ms": 250, "expect_on": True},
            {"type": "led", "ref": ref, "at_ms": 750, "expect_on": False},
        ]
    }
