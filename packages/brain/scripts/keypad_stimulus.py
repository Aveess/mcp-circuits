#!/usr/bin/env python3
"""Estimulo para el teclado 4x4: pulsaciones reales contra la simulacion.

El runner del proyecto arranca la simulacion y lee el serial, pero no puede
tocar el teclado. La cerradura solo demuestra algo si alguien pulsa teclas,
asi que el oraculo vive aqui: este script mantiene pulsada cada tecla el
tiempo suficiente para que el barrido la lea.

Hallazgo en vivo: **un click no registra la tecla**. El teclado de Tinkercad
solo cierra la matriz mientras el boton del mouse esta presionado, asi que
se usa ``mouse.down()`` / ``mouse.up()``. Un doble click tampoco sirve.

Prueba dos secuencias contra el mismo circuito:

1. la clave correcta (por defecto ``1234``) -> ``TEST:CLAVE=OK``;
2. cuatro veces la misma tecla -> ``TEST:CLAVE=FALLA``.

Uso:
    python scripts/keypad_stimulus.py <circuit_id> [--keys "x,y x,y x,y x,y"]

Las coordenadas son las de las teclas 1, 2, 3 y 4 en el encuadre que
Tinkercad elige al abrir el diseno. Los defaults son los del circuito
``g3KZdQc0DFu`` (cerradura-teclado).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Ruta del puente: `TINKERCAD_BRIDGE` manda, para que el repo corra en otra
# maquina sin editar el script. El default es el paquete hermano del monorepo.
BRIDGE = Path(
    os.environ.get("TINKERCAD_BRIDGE", str(REPO_ROOT.parent / "bridge"))
).expanduser()
sys.path.insert(0, str(BRIDGE))

from playwright.async_api import async_playwright  # noqa: E402

from src.config import PROFILE_DIR  # noqa: E402

# Capturas de la sonda: `TINKERCAD_SHOTS` manda, si no el temp del sistema.
SHOTS = Path(os.environ.get("TINKERCAD_SHOTS", tempfile.gettempdir())) / (
    "tinkercad-shots"
)

# Teclas 1, 2, 3 y 4 en el encuadre del circuito cerradura-teclado.
KEYS_DEFAULT = "755,310 800,310 850,310 755,356"


async def _serial(page):
    text = await page.evaluate("() => document.body.innerText")
    return [line.strip() for line in text.splitlines() if line.strip().startswith("TEST:")]


async def _linea_completa(page, prefijo, minimo, timeout_ms=2500):
    """Espera a que el serial termine de imprimir una linea.

    El monitor se lee del DOM: si se lee mientras el sketch esta a media
    impresion, la linea llega cortada (``TEST:PANTALLA=A`` en vez de
    ``ABIERTO``). Se sondea hasta que el valor tenga el largo esperado.
    """
    limite = timeout_ms
    while limite > 0:
        for line in reversed(await _serial(page)):
            if line.startswith(prefijo) and len(line) - len(prefijo) >= minimo:
                return line
        await page.wait_for_timeout(120)
        limite -= 120
    return None


async def _arrancar(page, circuit_id):
    await page.goto(
        f"https://www.tinkercad.com/things/{circuit_id}/editel",
        wait_until="domcontentloaded",
        timeout=60000,
    )
    await page.wait_for_timeout(10000)
    sim = page.locator(
        "a#SIMULATION_ID, a.js-toggleSimulation, a[data-event='simulate'], "
        "button:has-text('Start Simulation')"
    ).first
    await sim.click()
    await page.wait_for_timeout(3500)


async def _pulsar(page, xy, hold_ms=350):
    """Mantiene la tecla: un click solo no cierra la matriz del teclado."""
    await page.mouse.move(*xy)
    await page.mouse.down()
    await page.wait_for_timeout(hold_ms)
    await page.mouse.up()
    await page.wait_for_timeout(250)


async def _secuencia(page, coords, teclas, antes):
    for tecla in teclas:
        await _pulsar(page, coords[tecla])
    # La pantalla se imprime con print + println: se espera la linea entera.
    await _linea_completa(page, "TEST:PANTALLA=", 4)
    lineas = await _serial(page)
    return lineas[antes:]


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("circuit_id")
    parser.add_argument("--keys", default=KEYS_DEFAULT, help="coords de 1,2,3,4")
    parser.add_argument("--prefix", default="keypad")
    args = parser.parse_args()

    pares = [tuple(int(v) for v in par.split(",")) for par in args.keys.split()]
    if len(pares) != 4:
        parser.error("--keys necesita cuatro coordenadas: x,y x,y x,y x,y")
    coords = {tecla: xy for tecla, xy in zip("1234", pares)}

    SHOTS.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=True,
            viewport={"width": 1600, "height": 1000},
            args=["--disable-blink-features=AutomationControlled", "--enable-webgl"],
        )
        try:
            page = context.pages[0] if context.pages else await context.new_page()
            await _arrancar(page, args.circuit_id)
            print("reposo:", await _serial(page))

            antes = len(await _serial(page))
            bien = await _secuencia(page, coords, "1234", antes)
            ok_path = SHOTS / f"{args.prefix}_ok.png"
            await page.screenshot(path=str(ok_path))
            print("teclas 1-2-3-4:", bien, "->", ok_path)

            # El sketch muestra el resultado y bloquea 1.5 s: si se empieza
            # antes, la primera tecla del intento siguiente se pierde.
            await page.wait_for_timeout(1800)
            antes = len(await _serial(page))
            mal = await _secuencia(page, coords, "1111", antes)
            mal_path = SHOTS / f"{args.prefix}_falla.png"
            await page.screenshot(path=str(mal_path))
            print("teclas 1-1-1-1:", mal, "->", mal_path)

            errores = []
            if [l for l in bien if l.startswith("TEST:TECLA=")] != [
                "TEST:TECLA=1", "TEST:TECLA=2", "TEST:TECLA=3", "TEST:TECLA=4"
            ]:
                errores.append(f"lectura de teclas inesperada: {bien}")
            if "TEST:CLAVE=OK" not in bien:
                errores.append(f"la clave correcta no abrio: {bien}")
            if "TEST:CLAVE=FALLA" not in mal:
                errores.append(f"el codigo erroneo no fallo: {mal}")
            # Si el sketch escribe la pantalla, el oraculo la exige: el
            # display no se verifica solo con la captura.
            pantalla_ok = [l for l in bien if l.startswith("TEST:PANTALLA=")]
            if pantalla_ok and pantalla_ok[-1] != "TEST:PANTALLA=ABIERTO":
                errores.append(f"pantalla inesperada al abrir: {pantalla_ok[-1]}")
            pantalla_mal = [l for l in mal if l.startswith("TEST:PANTALLA=")]
            if pantalla_mal and pantalla_mal[-1] != "TEST:PANTALLA=DENEGADO":
                errores.append(f"pantalla inesperada al denegar: {pantalla_mal[-1]}")
            if errores:
                for error in errores:
                    print("FALLO:", error)
                return 1
            print("OK: 1234 -> CLAVE=OK y 1111 -> CLAVE=FALLA")
            return 0
        finally:
            await context.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
