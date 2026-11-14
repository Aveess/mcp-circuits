#!/usr/bin/env python3
"""Estimulo para los sensores que el runner no puede mover.

Algunos componentes de Tinkercad no tienen un valor fijo: el PIR entrega
``HIGH`` cuando algo **se mueve** dentro de su cono. El runner del proyecto
solo puede arrancar la simulacion y leer el serial, asi que para esos
sensores el oraculo necesita un paso de interaccion.

Este script:

1. abre el circuito y arranca la simulacion;
2. selecciona el PIR para que aparezca su cono de deteccion;
3. arrastra el punto de deteccion dentro del cono (eso es "movimiento");
4. muestrea el serial y guarda un screenshot en el momento en que el
   sketch reporta el cambio de estado;
5. suelta el punto y comprueba que el estado vuelve a reposo.

Uso:
    python scripts/pir_stimulus.py <circuit_id> [--click X,Y] [--dot X,Y]

Las coordenadas dependen del encuadre que Tinkercad elige al abrir el
diseno; los defaults son los del circuito ``dgFz6r0k1xV`` (alarma-pir).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

BRIDGE = Path(
    "/home/usuario/Documentos/StartUp/TInkercad/tinkercad-mcp"
).expanduser()
sys.path.insert(0, str(BRIDGE))

from playwright.async_api import async_playwright  # noqa: E402

from src.config import PROFILE_DIR  # noqa: E402

SHOTS = Path("/tmp/opencode")


async def _serial(page):
    text = await page.evaluate("() => document.body.innerText")
    return [line.strip() for line in text.splitlines() if line.strip().startswith("TEST:")]


async def _arrancar(page, circuit_id):
    await page.goto(
        f"https://www.tinkercad.com/things/{circuit_id}/editel",
        wait_until="domcontentloaded",
        timeout=60000,
    )
    await page.wait_for_timeout(10000)
    panel = page.locator(
        "a#CODE_EDITOR_ID, a.js-toggle_code_panel, a[data-event='code-editor']"
    ).first
    try:
        classes = await panel.get_attribute("class") or ""
        if "active" in classes or "selected" in classes:
            await panel.click()
            await page.wait_for_timeout(1200)
    except Exception:
        pass
    sim = page.locator(
        "a#SIMULATION_ID, a.js-toggleSimulation, a[data-event='simulate'], "
        "button:has-text('Start Simulation')"
    ).first
    await sim.click()
    await page.wait_for_timeout(3500)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("circuit_id")
    parser.add_argument("--click", default="823,405", help="centro del PIR en pantalla")
    parser.add_argument("--dot", default="821,252", help="punto de deteccion del cono")
    parser.add_argument("--prefix", default="pir_stimulus")
    args = parser.parse_args()
    click = tuple(int(v) for v in args.click.split(","))
    dot = tuple(int(v) for v in args.dot.split(","))

    async with async_playwright() as pw:
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=True,
            viewport={"width": 1600, "height": 1000},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--enable-webgl",
            ],
        )
        try:
            page = context.pages[0] if context.pages else await context.new_page()
            await _arrancar(page, args.circuit_id)
            antes = await _serial(page)
            print("reposo:", antes)

            await page.mouse.click(*click)
            await page.wait_for_timeout(800)

            await page.mouse.move(*dot)
            await page.mouse.down()
            detectado = None
            for x, y in ((760, 220), (710, 270), (780, 300), (900, 280), (950, 230)):
                await page.mouse.move(x, y, steps=8)
                await page.wait_for_timeout(400)
                lineas = await _serial(page)
                if any(line.endswith("=1") for line in lineas) and detectado is None:
                    detectado = lineas
                    SHOTS.mkdir(parents=True, exist_ok=True)
                    path = SHOTS / f"{args.prefix}_detectado.png"
                    await page.screenshot(path=str(path))
                    print("movimiento:", lineas[-3:], "->", path)
            await page.mouse.up()
            await page.wait_for_timeout(1500)
            despues = await _serial(page)
            print("tras soltar:", despues[-3:])

            if detectado is None:
                print("FALLO: el PIR no reporto movimiento")
                return 1
            if not any(line.endswith("=0") for line in despues[-3:]):
                print("FALLO: no volvio a reposo")
                return 1
            print("OK: reposo -> movimiento -> reposo")
            return 0
        finally:
            await context.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
