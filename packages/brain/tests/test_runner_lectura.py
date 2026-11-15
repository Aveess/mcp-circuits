"""El runner no puede confundir "no lo pude leer" con "0% de fidelidad".

Pasó en vivo: tras reconstruir `blink-basico`, el `inspect` devolvió 0
componentes y 0 cables (la página se estaba recargando) y el runner reportó
`Score: 0.0%` / `OK: False` con el circuito perfecto. Un 0% es una acusación;
"no leí" es otra cosa y el reporte tiene que decirlo.

`_measure` reabre el circuito y reintenta la inspección unas pocas veces
cuando la fixture tiene componentes y la lectura vino vacía. Si aun así no
llega nada, la medida lleva `read_failed` y el build falla por
`fidelity_readable`, no por un cero mudo.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from tinkercad_brain.runner import run_build

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"
TITLE = "Blink lectura"
CIRCUIT_ID = "abc123"


def _fixture():
    """`blink-basico` de verdad: 2 componentes con net y 3 cables."""
    circuits = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == "blink-basico")


def _inspect_blink():
    """Lo que devuelve `inspect_circuit` cuando la página ya cargó."""
    uno = ("Arduino Uno R3", "uno1")
    r = ("Resistor", "r_a")
    led = ("LED", "led_a")

    def comp(type_, instance_id):
        return {"type": type_, "instance_id": instance_id, "name": "1", "pins": []}

    def ep(component, pin):
        return {"component": component[0], "pin": pin, "instance_id": component[1]}

    def wire(source, target):
        return {"source": source, "target": target}

    return {
        "success": True,
        "detected_components_count": 3,
        "components": [comp(*uno), comp(*r), comp(*led)],
        "wires": [
            wire(ep(uno, "D13"), ep(r, "Terminal 1")),
            wire(ep(r, "Terminal 2"), ep(led, "Anode")),
            wire(ep(led, "Cathode"), ep(uno, "GND")),
        ],
    }


def _inspect_vacio():
    """Lo que devuelve mientras la página se recarga: éxito y nada dentro."""
    return {
        "success": True,
        "detected_components_count": 0,
        "components": [],
        "wires": [],
    }


def _call_tool(inspects, build_output=None):
    """call_tool falso: inspects en orden; el último se repite."""
    pending = list(inspects)

    def call_tool(tool, arguments):
        if tool == "tinkercad_inspect_circuit":
            return json.dumps(pending.pop(0) if len(pending) > 1 else pending[0])
        if tool == "tinkercad_build_circuit_model":
            if build_output is not None:
                return json.dumps(build_output)
            return json.dumps(
                {"success": True, "persisted": True, "routed": 3, "route_debug": [], "errors": []}
            )
        if tool == "tinkercad_read_serial_monitor":
            return "TEST:ON\n"
        return json.dumps({"success": True})

    return call_tool


def _run(inspects, build_output=None, **kwargs):
    return run_build(
        _fixture(),
        None,
        _call_tool(inspects, build_output=build_output),
        TITLE,
        preferred_id=CIRCUIT_ID,
        **kwargs,
    )


def test_una_lectura_vacia_se_reintenta_y_termina_bien(monkeypatch):
    """El primer inspect llega vacío (recarga); el segundo ya trae el circuito."""
    sleeps = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    result = _run([_inspect_vacio(), _inspect_blink()])

    assert result["fidelity"]["score"] == 1.0
    assert result["fidelity"]["read_attempts"] == 2
    assert result["fidelity"]["read_failed"] is False
    assert result["checks"]["fidelity_readable"] is True
    assert result["ok"] is True
    assert len(sleeps) == 1


def test_una_lectura_buena_no_se_reintenta_ni_espera(monkeypatch):
    sleeps = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    result = _run([_inspect_blink()])

    assert result["fidelity"]["score"] == 1.0
    assert result["fidelity"]["read_attempts"] == 1
    assert result["checks"]["fidelity_readable"] is True
    assert sleeps == []


def test_si_la_lectura_sigue_vacia_se_dice_y_no_se_reporta_un_cero_mudo(monkeypatch):
    sleeps = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    result = _run([_inspect_vacio()])

    assert result["fidelity"]["read_failed"] is True
    assert result["fidelity"]["read_attempts"] >= 2
    assert result["checks"]["fidelity_readable"] is False
    assert result["ok"] is False
    # Reintentó de verdad: una espera entre intentos.
    assert len(sleeps) >= 1


def test_un_circuito_que_de_verdad_esta_vacio_no_se_reintenta():
    """Si la fixture no declara componentes, un vacío es la verdad, no un fallo."""
    fixture = {"id": "vacio", "title": "Vacío", "components": [], "nets": []}
    result = run_build(
        fixture, None, _call_tool([_inspect_vacio()]), "Vacío", preferred_id=CIRCUIT_ID
    )
    assert result["fidelity"]["read_failed"] is False
    assert result["checks"]["fidelity_readable"] is True


def test_si_el_build_fallo_no_se_culpa_a_la_lectura(monkeypatch):
    """Un build fallido puede dejar el circuito vacio de verdad.

    Reportar "no se pudo leer" ahi seria cambiar una causa por otra: el
    motivo real es que el build no se aplico.
    """
    sleeps = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    result = _run(
        [_inspect_vacio()],
        build_output={"success": False, "errors": ["no se pudo colocar"]},
    )

    assert result["fidelity"]["read_failed"] is False
    assert result["checks"]["fidelity_readable"] is True
    assert result["checks"]["build_ok"] is False
    assert result["ok"] is False
    assert sleeps == []


def test_el_reporte_dice_que_no_se_pudo_leer_en_vez_de_acusar_al_cableado():
    from tinkercad_brain.documenter import render_build_report

    reporte = render_build_report(
        "Blink",
        "https://www.tinkercad.com/things/abc123/editel",
        {"score": 0.0, "read_attempts": 3, "read_failed": True},
        "sin serial",
        [],
    )
    assert "no se pudo leer" in reporte
    assert "no mide el cableado" in reporte
