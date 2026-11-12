"""Cliente del sampler del puente + glue con el verificador.

El puente expone ``tinkercad_simulate_samples`` con muestras en formato
``{"at_ms", "led": {"on", "level"}, "sim_time"}``; el verificador espera
``{"at_ms", "sim_time", "leds": {ref: {...}}, "servos": {...}}``.
Este módulo convierte entre ambos y ejecuta la verificación de punta a punta.
"""

from __future__ import annotations

import json

from tinkercad_brain.fase0.probe import ProbeStep, run_steps
from tinkercad_brain.verifier import evaluate_contract

_TIMED_TYPES = ("led", "led_level", "servo")
_DEFAULT_SAMPLES_MS = [250]


def to_verifier_format(sampler_output: dict, led_ref: str = "led1") -> dict:
    """Convierte la salida del puente al formato de ``evaluate_contract``.

    Convierte lo que haya aunque ``sampler_output["errors"]`` no esté
    vacío: la evaluación del contrato decide si eso pasa o no.
    """
    samples = []
    raw_samples = sampler_output.get("samples") if isinstance(sampler_output, dict) else None
    if isinstance(raw_samples, list):
        for sample in raw_samples:
            if not isinstance(sample, dict):
                continue
            led = sample.get("led")
            leds = {}
            if isinstance(led, dict):
                leds[led_ref] = {"on": led.get("on"), "level": led.get("level")}
            samples.append(
                {
                    "at_ms": sample.get("at_ms"),
                    "sim_time": sample.get("sim_time"),
                    "leds": leds,
                    "servos": {},
                }
            )
    serial = sampler_output.get("serial") if isinstance(sampler_output, dict) else None
    return {"samples": samples, "serial": serial if isinstance(serial, str) else ""}


def _samples_ms(contract: dict) -> list:
    times = set()
    assertions = contract.get("assertions") if isinstance(contract, dict) else None
    if isinstance(assertions, list):
        for assertion in assertions:
            if not isinstance(assertion, dict):
                continue
            if assertion.get("type") in _TIMED_TYPES and assertion.get("at_ms") is not None:
                times.add(assertion["at_ms"])
    return sorted(times) if times else list(_DEFAULT_SAMPLES_MS)


def simulate_and_verify(
    call_tool, contract: dict, led_ref: str = "led1", led_component: str = "LED"
) -> dict:
    """Pide muestras al puente y verifica el contrato contra ellas.

    Si el puente falla o su salida no es JSON parseable, devuelve
    ``{"passed": False, "results": [], "error": <texto>}``. En caso de
    éxito devuelve el resultado de ``evaluate_contract`` más ``raw``
    con la salida original (ya parseada) del puente.
    """
    steps = [
        ProbeStep(
            tool="tinkercad_simulate_samples",
            arguments={
                "samples_ms": _samples_ms(contract),
                "led_component": led_component,
                "read_serial": True,
            },
        )
    ]
    records = run_steps(steps, call_tool)
    record = records[0] if records else None
    if record is None:
        return {"passed": False, "results": [], "error": "no record from tinkercad_simulate_samples"}
    if not record.ok:
        return {"passed": False, "results": [], "error": record.output}
    try:
        parsed = json.loads(record.output)
    except (ValueError, TypeError) as exc:
        return {"passed": False, "results": [], "error": str(exc)}
    if not isinstance(parsed, dict):
        return {
            "passed": False,
            "results": [],
            "error": "tinkercad_simulate_samples output is not a JSON object",
        }
    result = evaluate_contract(contract, to_verifier_format(parsed, led_ref=led_ref))
    result["raw"] = parsed
    return result
