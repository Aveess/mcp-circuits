#!/usr/bin/env python3
"""Sonda: un interruptor deslizante creado por build_circuit_model + un LED.

Pregunta que contesta: las piezas creadas por el modelo, ¿son interactivas en la
simulacion? En la sonda `iXiA957AXba` los interruptores entraron por
`add_component` (paleta) y el clic si cambiaba el circuito. Aqui entran por el
mismo camino que el circuito del proyecto final.

Circuito: 5V -> sw1.2, GND -> sw1.1, comun -> 220 ohm -> LED -> GND.
En reposo el comun va a GND (LED apagado); al accionar, a 5V (LED encendido).

Uso:
    .venv/bin/python scripts/probe_switch_led.py --emit /ruta/probe-switch.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from tinkercad_brain.builder import fixture_to_model_call  # noqa: E402

FIXTURE = {
    "id": "probe-switch-modelo",
    "title": "BORRAR - sonda interruptor del modelo",
    "components": [
        {"ref": "ps1", "type": "power-supply"},
        {"ref": "sw1", "type": "slideswitch"},
        {"ref": "r1", "type": "resistor"},
        {"ref": "led1", "type": "led"},
    ],
    "layout": "v3",
    "boards": [{"kind": "small", "x": 870, "y": 0}],
    "wiring": "rails",
    "nets": [
        ["ps1.Vcc", "sw1.2"],
        ["ps1.GND", "sw1.1"],
        ["sw1.common", "r1.1"],
        ["r1.2", "led1.anode"],
        ["led1.cathode", "ps1.GND"],
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit", default="", help="ruta del JSON del plan")
    args = parser.parse_args()

    call = fixture_to_model_call(FIXTURE, code=None)
    plan = {
        "parts": call["parts"],
        "wires": call["wires"],
        "boards": call.get("boards") or [],
    }
    print("piezas:", len(plan["parts"]), "cables:", len(plan["wires"]))
    for part in plan["parts"]:
        print(" ", part.get("ref"), part.get("did"), part.get("at") or part.get("free"))
    if args.emit:
        Path(args.emit).write_text(json.dumps(plan, indent=1))
        print("escrito:", args.emit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
