#!/usr/bin/env python3
"""CLI punta a punta: fixture -> runner -> puente MCP real (stdio) -> reporte.

Uso:
    python scripts/demo_build.py <fixture_id> [--bridge PATH] [--title TITULO]

La conexion MCP es perezosa: importar este modulo (y correr los tests
unitarios) no requiere el paquete ``mcp`` ni red ni navegador.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tinkercad_brain import sketches  # noqa: E402
from tinkercad_brain.documenter import render_build_report  # noqa: E402

DEFAULT_FIXTURES_PATH = REPO_ROOT / "fixtures" / "fase0" / "circuits.json"
DEFAULT_BRIDGE_PATH = Path("~/Documentos/StartUp/TInkercad/tinkercad-mcp").expanduser()
REPORTS_DIR = REPO_ROOT / "docs" / "reportes"

# fixture_id -> presets a aplicar tras el build (valor calibrado en vivo)
_PRESETS_BY_FIXTURE = {
    "sensor-ultrasonico": [
        {
            "component": "Ultrasonic Distance Sensor (4-pin)",
            "property": "Target Y",
            "value": -105,
        }
    ],
}


def select_presets(fixture: dict):
    """Presets de la fixture, o None si no tiene ninguno."""
    presets = _PRESETS_BY_FIXTURE.get(fixture.get("id"))
    return [dict(p) for p in presets] if presets else None


# fixture_id -> nombre de la funcion en tinkercad_brain.sketches
_SKETCH_BY_FIXTURE = {
    "blink-basico": "blink_sketch",
    "semaforo-3-leds": "traffic_sketch",
    "servo-potenciometro": "servo_knob_sketch",
    "sensor-ultrasonico": "ultrasonic_sketch",
    "temperatura-tmp36": "tmp36_sketch",
    "led-rgb": "rgb_cycle_sketch",
    "motor-dc-transistor": "motor_sketch",
    "motor-l293d-bateria": "motor_driver_sketch",
    "boton-pullup": "button_led_sketch",
    "parking-servo-ultrasonico-rgb": "parking_servo_sketch",
}


def load_fixtures(path=DEFAULT_FIXTURES_PATH) -> list:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_fixture(fixture_id: str, fixtures: list | None = None) -> dict:
    if fixtures is None:
        fixtures = load_fixtures()
    for fixture in fixtures:
        if isinstance(fixture, dict) and fixture.get("id") == fixture_id:
            return fixture
    disponibles = ", ".join(
        str(f.get("id")) for f in fixtures if isinstance(f, dict)
    ) or "ninguna"
    raise LookupError(
        f"fixture no encontrada: {fixture_id!r} (disponibles: {disponibles})"
    )


def select_code(fixture: dict) -> str | None:
    """Codigo Arduino para la fixture, o None si no hay sketch conocido.

    La busqueda es dinamica sobre ``sketches`` para que una funcion aun
    no fusionada (p. ej. ``tmp36_sketch``) se use en cuanto exista.
    """
    name = _SKETCH_BY_FIXTURE.get(fixture.get("id"))
    if not name:
        return None
    builder = getattr(sketches, name, None)
    return builder() if callable(builder) else None


def bridge_launch_spec(bridge_path=DEFAULT_BRIDGE_PATH) -> dict:
    """Comando puro (sin MCP) para lanzar el puente por stdio."""
    bridge = Path(bridge_path).expanduser()
    return {
        "command": str(bridge / ".venv" / "bin" / "python"),
        "args": ["-m", "src.main"],
        "cwd": str(bridge),
    }


def _result_text(result) -> str:
    parts = []
    for item in getattr(result, "content", None) or []:
        text = getattr(item, "text", None)
        parts.append(text if isinstance(text, str) else str(item))
    return "\n".join(parts)


def run_via_bridge(fixture: dict, code: str | None, title: str, bridge_path=DEFAULT_BRIDGE_PATH) -> dict:
    """Envuelve ``run_build`` conectando al puente real via MCP stdio.

    El import de ``mcp`` (y de ``runner``) es perezoso, dentro de esta
    funcion. ``call_tool`` es sincrono, como espera el runner: el loop
    asyncio de la sesion MCP vive en un hilo aparte.
    """
    import asyncio
    import threading

    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    from tinkercad_brain.runner import run_build

    spec = bridge_launch_spec(bridge_path)
    params = StdioServerParameters(
        command=spec["command"], args=list(spec["args"]), cwd=spec["cwd"]
    )

    loop = asyncio.new_event_loop()
    ready = threading.Event()
    holder: dict = {}

    def _loop_thread() -> None:
        asyncio.set_event_loop(loop)

        async def _open():
            transport_cm = stdio_client(params)
            read_stream, write_stream = await transport_cm.__aenter__()
            session_cm = ClientSession(read_stream, write_stream)
            session = await session_cm.__aenter__()
            await session.initialize()
            holder.update(
                transport_cm=transport_cm, session_cm=session_cm, session=session
            )

        try:
            loop.run_until_complete(_open())
        except Exception as exc:  # noqa: BLE001 - se relanza en el hilo principal
            holder["error"] = exc
        finally:
            ready.set()
        if "error" not in holder:
            loop.run_forever()

    thread = threading.Thread(target=_loop_thread, daemon=True)
    thread.start()
    ready.wait()
    if "error" in holder:
        loop.close()
        raise RuntimeError(
            f"no se pudo conectar con el puente en {spec['cwd']}: {holder['error']}"
        ) from holder["error"]

    def call_tool(name, arguments):
        future = asyncio.run_coroutine_threadsafe(
            holder["session"].call_tool(name, dict(arguments or {})), loop
        )
        result = future.result()
        text = _result_text(result)
        if getattr(result, "isError", False):
            raise RuntimeError(text or f"la tool {name} devolvio un error")
        return text

    try:
        return run_build(
            fixture, code, call_tool, title, presets=select_presets(fixture)
        )
    finally:

        async def _close():
            try:
                await holder["session_cm"].__aexit__(None, None, None)
            finally:
                await holder["transport_cm"].__aexit__(None, None, None)

        try:
            asyncio.run_coroutine_threadsafe(_close(), loop).result(timeout=30)
        except Exception:  # noqa: BLE001 - cierre best-effort
            pass
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=10)
        loop.close()


def _records_as_dicts(records) -> list[dict]:
    normalized = []
    for record in records or []:
        if isinstance(record, dict):
            normalized.append(record)
        elif dataclasses.is_dataclass(record):
            normalized.append(dataclasses.asdict(record))
        else:
            normalized.append(
                {
                    "tool": getattr(record, "tool", "unknown"),
                    "ok": getattr(record, "ok", False),
                    "elapsed_s": getattr(record, "elapsed_s", 0.0),
                    "output": getattr(record, "output", ""),
                }
            )
    return normalized


def write_report(result: dict, fixture: dict, title: str, reports_dir=REPORTS_DIR) -> Path:
    fidelity = result.get("fidelity") or {}
    serial = result.get("serial")
    sim_summary = serial if isinstance(serial, str) and serial else "sin datos"
    report = render_build_report(
        title,
        result.get("url") or "",
        fidelity if isinstance(fidelity, dict) else {},
        sim_summary,
        _records_as_dicts(result.get("records")),
    )
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{fixture['id']}.md"
    path.write_text(report, encoding="utf-8")
    return path


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Construye una fixture en Tinkercad via el puente MCP.")
    parser.add_argument("fixture_id", help="id de la fixture en fixtures/fase0/circuits.json")
    parser.add_argument("--bridge", default=str(DEFAULT_BRIDGE_PATH), help="ruta del puente tinkercad-mcp")
    parser.add_argument("--title", default=None, help="titulo del circuito (defecto: el de la fixture)")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        fixture = find_fixture(args.fixture_id)
    except (LookupError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    code = select_code(fixture)
    if code is None:
        print(
            f"Error: la fixture {args.fixture_id!r} no tiene sketch conocido "
            "(sin sketch); no se construye.",
            file=sys.stderr,
        )
        return 2

    title = args.title or fixture.get("title") or args.fixture_id
    result = run_via_bridge(fixture, code, title, bridge_path=args.bridge)
    report_path = write_report(result, fixture, title)

    fidelity = result.get("fidelity") or {}
    score = fidelity.get("score") if isinstance(fidelity, dict) else None
    score_text = f"{float(score) * 100:.1f}%" if score is not None else "sin medir"
    print(f"URL: {result.get('url') or ''}")
    print(f"Score: {score_text}")
    print(f"OK: {bool(result.get('ok'))}")
    print(f"Reporte: {report_path}")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
