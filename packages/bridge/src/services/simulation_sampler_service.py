"""Timed simulation sampling: does the LED emit at each requested instant.

Ports the sampler concept from netchuu's implementation: start the simulation,
take a screenshot at each requested offset (ms since start), and classify the
LED from the share of *lit* pixels (bright and saturated) in a window centred
on the **body** of the part. Measured live on blink-basico (2tMhkuosDyj): the
pin anchors land on the breadboard hole (861,484), 15 px off the LED that
lights up at (876,487), and that offset sits on white plastic with a constant
brightness of 208 - which is why a brightness threshold reported "on" for an
off LED.
"""

from __future__ import annotations

import asyncio
import base64
import io
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PIL import Image

from ..browser.browser_manager import BrowserManager
from ..config import logger
from .serial_service import SerialService
from .simulation_service import SimulationService
from .wiring_service import WiringService

# Un pixel del LED "emite" si es brillante **y** saturado: el brillo solo no
# distingue el plastico blanco de la protoboard (medido: 208 constante) de un
# LED encendido (207). Medido en blink-basico (2tMhkuosDyj) sobre el lente:
#   apagado  (128, 32, 32) -> max 128, saturacion 96  -> no emite (falta brillo)
#   encendido(207,132,132) -> max 207, saturacion 75  -> emite
#   plastico (208,208,208) -> max 208, saturacion 0   -> no emite (falta color)
LED_LIT_MIN_BRIGHTNESS = 150
LED_LIT_MIN_SATURATION = 40

# Fraccion de la ventana que debe estar emitiendo para decir "encendido".
# Medido en la ventana de 9x9 centrada en el cuerpo, en tres circuitos:
# apagado 0.000-0.025 (1-2 px de borde), encendido 0.52-0.59.
DEFAULT_LED_LIT_THRESHOLD = 0.12

# Lado (px) de la ventana cuadrada centrada en el cuerpo del LED.
LED_WINDOW_SIZE = 9

# Seconds SimulationService waits before verifying the simulation is active.
# With 0 it only sends the trigger and reports success=False
# ("Simulation trigger sent."), even though the simulation may be running.
START_WAIT_SECONDS = 5

# Fallback confirmation polling when start reports success=False: the
# simulation may still be active (verified via get_simulation_status).
START_CONFIRM_ATTEMPTS = 5
START_CONFIRM_INTERVAL_SECONDS = 0.2


class SimulationSamplerService:
    """Samples LED state at timed offsets during a running simulation."""

    def __init__(
        self,
        browser: Optional[BrowserManager] = None,
        simulation_service: Optional[SimulationService] = None,
        serial_service: Optional[SerialService] = None,
        wiring_service: Optional[WiringService] = None,
    ) -> None:
        self.browser = browser or BrowserManager.get_instance()
        self.simulation = simulation_service or SimulationService(self.browser)
        self.serial = serial_service or SerialService(self.browser)
        self.wiring = wiring_service or WiringService(self.browser)

    # ------------------------------------------------------------------ #
    # Brightness helpers (pure, unit-testable without a browser)
    # ------------------------------------------------------------------ #
    @staticmethod
    def window_bounds(
        image: Image.Image,
        x: int,
        y: int,
        window: int = LED_WINDOW_SIZE,
    ) -> Optional[Tuple[int, int, int, int]]:
        """Recorte ``(left, upper, right, lower)`` que se va a medir.

        Devuelve ``None`` cuando el punto cae **completamente fuera** de la
        captura: ahi no hay nada que medir y devolver 0.0 seria reportar como
        apagado un LED que nunca se vio (el lienzo de Tinkercad se puede
        panelear, asi que el pin resuelto puede quedar fuera del viewport).

        Cerca de un borde el recorte se achica (de 9x9 a menos). Eso es
        legitimo y se informa como ``window_px`` en cada muestra, para que una
        lectura de 3x3 no se confunda con una de 9x9.
        """
        img = image.convert("RGB")
        half = max(0, int(window) // 2)
        left = max(0, int(x) - half)
        upper = max(0, int(y) - half)
        right = min(img.width, int(x) + half + 1)
        lower = min(img.height, int(y) + half + 1)
        if right <= left or lower <= upper:
            return None
        return (left, upper, right, lower)

    @staticmethod
    def brightness_at(image: Image.Image, x: int, y: int, window: int = LED_WINDOW_SIZE) -> float:
        """Average of the per-pixel max RGB channel in a window around (x, y).

        The window is ``window`` x ``window`` px centred on (x, y), clamped to
        the image bounds. Returns a value in 0..255.
        """
        img = image.convert("RGB")
        bounds = SimulationSamplerService.window_bounds(img, x, y, window)
        if bounds is None:
            return 0.0
        left, upper, right, lower = bounds
        crop = img.crop((left, upper, right, lower))
        total = 0
        count = 0
        for px in range(crop.width):
            for py in range(crop.height):
                r, g, b = crop.getpixel((px, py))
                total += max(r, g, b)
                count += 1
        return total / count if count else 0.0

    @staticmethod
    def is_lit(pixel: Tuple[int, int, int]) -> bool:
        """True si el pixel parece un LED emitiendo (brillante y saturado)."""
        mx = max(pixel)
        mn = min(pixel)
        return mx > LED_LIT_MIN_BRIGHTNESS and (mx - mn) > LED_LIT_MIN_SATURATION

    @staticmethod
    def lit_fraction(
        image: Image.Image,
        x: int,
        y: int,
        window: int = LED_WINDOW_SIZE,
    ) -> Optional[float]:
        """Fraccion (0..1) de pixeles que emiten en la ventana centrada en (x, y).

        Devuelve ``None`` cuando la ventana cae fuera de la captura (ver
        ``window_bounds``): sin ventana no hay medida, y devolver 0.0 seria
        reportar apagado un LED que no se miro.
        """
        img = image.convert("RGB")
        bounds = SimulationSamplerService.window_bounds(img, x, y, window)
        if bounds is None:
            return None
        left, upper, right, lower = bounds
        crop = img.crop((left, upper, right, lower))
        total = 0
        lit = 0
        for px in range(crop.width):
            for py in range(crop.height):
                total += 1
                if SimulationSamplerService.is_lit(crop.getpixel((px, py))):
                    lit += 1
        return lit / total if total else 0.0

    @staticmethod
    def classify(lit_fraction: float, threshold: float = DEFAULT_LED_LIT_THRESHOLD) -> Tuple[bool, float]:
        """Clasifica una fraccion de pixeles encendidos.

        Returns ``(on, level)``: ``on`` es ``lit_fraction > threshold`` y
        ``level`` la fraccion recortada a 0..1 (0.0 sin emision, 1.0 ventana
        entera emitiendo). El umbral se expresa en la misma unidad: 0.12 es
        "12% de la ventana emitiendo".
        """
        fraction = max(0.0, float(lit_fraction))
        on = fraction > float(threshold)
        # level = 0 cuando no emite; si emite, la fraccion de ventana que emite.
        return on, (min(1.0, fraction) if on else 0.0)

    # ------------------------------------------------------------------ #
    # Browser-dependent helpers
    # ------------------------------------------------------------------ #
    async def _resolve_led_position(self, led_component: str) -> Optional[Dict[str, Any]]:
        """Localiza **el cuerpo** del LED en px de pantalla.

        ``resolve_terminal`` devuelve ahora la caja del grupo del device
        (``body``): el ancla de un terminal cae en el hueco de la protoboard,
        y en un LED eso puede quedar 15 px fuera del lente (medido en
        blink-basico: pines (843,492)/(879,477), LED encendido en (876,487)).
        Se prefiere el centro del cuerpo; sin cuerpo se cae al promedio de los
        pines y se informa ``source: "pins"`` para que el reporte lo sepa.

        Returns ``{"x", "y", "source", "body"}`` o ``None`` si no se localiza.
        """
        points: List[Tuple[int, int]] = []
        body: Optional[Dict[str, Any]] = None
        for pin in ("anode", "cathode"):
            try:
                res = await self.wiring.resolve_terminal(led_component, pin)
            except Exception as exc:  # browser/DOM errors must not propagate
                logger.debug(f"resolve_terminal({led_component!r}, {pin!r}) failed: {exc}")
                continue
            if not isinstance(res, dict) or not res.get("success"):
                continue
            if res.get("x") is not None and res.get("y") is not None:
                points.append((int(res["x"]), int(res["y"])))
            candidate = res.get("body")
            if (
                body is None
                and isinstance(candidate, dict)
                and int(candidate.get("width") or 0) > 0
                and int(candidate.get("height") or 0) > 0
            ):
                body = candidate

        if body is not None and body.get("cx") is not None and body.get("cy") is not None:
            return {
                "x": int(body["cx"]),
                "y": int(body["cy"]),
                "source": "body",
                "body": body,
            }
        if not points:
            return None
        return {
            "x": sum(p[0] for p in points) // len(points),
            "y": sum(p[1] for p in points) // len(points),
            "source": "pins",
            "body": None,
        }

    async def _capture_image(self) -> Image.Image:
        """Take a screenshot (reusing BrowserManager.take_screenshot) as PIL image."""
        shot = await self.browser.take_screenshot()
        if isinstance(shot, dict) and shot.get("base64"):
            return Image.open(io.BytesIO(base64.b64decode(shot["base64"])))
        if isinstance(shot, dict) and shot.get("path"):
            return Image.open(shot["path"])
        raise ValueError("Screenshot did not return image data (no base64/path).")

    async def _sim_time(self) -> Optional[str]:
        try:
            status = await self.simulation.get_simulation_status()
        except Exception:
            return None
        if isinstance(status, dict):
            return status.get("simulation_time") or status.get("sim_time")
        return None

    async def _simulation_is_active(self) -> bool:
        """True when get_simulation_status reports the simulation running."""
        try:
            status = await self.simulation.get_simulation_status()
        except Exception:
            return False
        if not isinstance(status, dict):
            return False
        if status.get("running") is not None:
            return bool(status.get("running"))
        if status.get("is_running") is not None:
            return bool(status.get("is_running"))
        state = str(status.get("status") or status.get("state") or "").strip().lower()
        return state in ("running", "active", "started")

    async def _confirm_simulation_active(self, start_res: Any) -> bool:
        """Confirm the simulation is actually active after starting it.

        ``start_simulation(wait_seconds=START_WAIT_SECONDS)`` already waits
        and verifies, so success=True is trusted. On success=False (e.g.
        "Simulation trigger sent.") the trigger may still have started the
        simulation: poll get_simulation_status instead of aborting outright.
        """
        if isinstance(start_res, dict) and start_res.get("success"):
            return True
        for attempt in range(START_CONFIRM_ATTEMPTS):
            if await self._simulation_is_active():
                return True
            if attempt + 1 < START_CONFIRM_ATTEMPTS:
                await asyncio.sleep(START_CONFIRM_INTERVAL_SECONDS)
        return bool(isinstance(start_res, dict) and start_res.get("running"))

    # ------------------------------------------------------------------ #
    # Main entry point
    # ------------------------------------------------------------------ #
    async def sample(
        self,
        samples_ms: Sequence[int],
        led_component: str = "LED",
        read_serial: bool = True,
        lit_threshold: float = DEFAULT_LED_LIT_THRESHOLD,
    ) -> Dict[str, Any]:
        """Sample the LED at each requested offset (ms) from simulation start.

        Returns ``{"samples": [{"at_ms", "led": {"on", "level", "lit",
        "brightness"}, "measured_at_px", "window_px", "sim_time"}],
        "led_position": {...}, "serial": str|None, "errors": [...]}``. Never
        raises for a missing LED: that is reported as ``led_position_unknown``.
        """
        errors: List[str] = []
        ordered = sorted(max(0, int(t)) for t in (samples_ms or []))

        # 1. Locate the LED BEFORE starting the simulation.
        position = await self._resolve_led_position(led_component)
        if position is None:
            errors.append(
                f"led_position_unknown: could not resolve screen position of "
                f"'{led_component}' (anode/cathode) before starting simulation"
            )
            return {"samples": [], "serial": None, "errors": errors}
        led_x, led_y = position["x"], position["y"]
        led_position = {"x": led_x, "y": led_y, "source": position["source"]}

        page = await self.browser.get_page()
        samples: List[Dict[str, Any]] = []
        serial_text: Optional[str] = None
        started = False
        try:
            # 2. Start the simulation with confirmation, reusing
            # SimulationService. wait_seconds=0 only sends the trigger and
            # reports success=False ("Simulation trigger sent."); waiting
            # lets the service verify the active state. If it still reports
            # failure, fall back to get_simulation_status: only abort when
            # the simulation is not actually active.
            start_res: Any = None
            start_error: Optional[str] = None
            try:
                start_res = await self.simulation.start_simulation(wait_seconds=START_WAIT_SECONDS)
            except Exception as exc:  # a raised start may still have triggered it
                start_error = str(exc)
            if not await self._confirm_simulation_active(start_res):
                if start_error is not None:
                    detail = start_error
                elif isinstance(start_res, dict):
                    detail = start_res.get("message") or start_res.get("error") or start_res
                else:
                    detail = start_res
                errors.append(f"simulation_start_failed: {detail}")
                return {"samples": [], "serial": None, "errors": errors}
            started = True
            # t0 is when the simulation was confirmed active, not the click.
            start_monotonic = time.monotonic()

            # 3. Sample at each requested instant, in ascending order.
            for at_ms in ordered:
                remaining_ms = at_ms - (time.monotonic() - start_monotonic) * 1000.0
                if remaining_ms > 0:
                    await page.wait_for_timeout(int(remaining_ms))
                bounds = None
                lit: Optional[float] = None
                brightness: Optional[float] = None
                try:
                    image = await self._capture_image()
                    bounds = self.window_bounds(image, led_x, led_y)
                    if bounds is None:
                        # Sin ventana no hay medida. Seguir reportaria "apagado"
                        # un LED que no esta en la captura: un falso negativo
                        # que hace mentir al oraculo.
                        errors.append(
                            f"led_offscreen: el pin del LED en ({led_x}, {led_y}) cae "
                            f"fuera de la captura de {image.width}x{image.height}; "
                            f"no se mide"
                        )
                        break
                    lit = self.lit_fraction(image, led_x, led_y)
                    brightness = self.brightness_at(image, led_x, led_y)
                    on, level = self.classify(lit, lit_threshold)
                except Exception as exc:
                    errors.append(f"sample_failed at {at_ms}ms: {exc}")
                    on, level = False, 0.0
                sample: Dict[str, Any] = {
                    "at_ms": int(at_ms),
                    "led": {
                        "on": bool(on),
                        "level": float(level),
                        "lit": None if lit is None else round(float(lit), 3),
                        "brightness": None if brightness is None else round(float(brightness), 1),
                    },
                    "measured_at_px": [led_x, led_y],
                    "sim_time": await self._sim_time(),
                }
                if bounds is not None:
                    sample["window_px"] = [bounds[2] - bounds[0], bounds[3] - bounds[1]]
                samples.append(sample)

            # 4a. Read serial output (still running) if requested.
            if read_serial:
                try:
                    serial_res = await self.serial.read_serial_monitor()
                    if isinstance(serial_res, dict):
                        serial_text = serial_res.get("raw_output")
                        if serial_text is None and serial_res.get("lines") is not None:
                            serial_text = "\n".join(serial_res["lines"])
                    elif serial_res is not None:
                        serial_text = str(serial_res)
                except Exception as exc:
                    errors.append(f"serial_read_failed: {exc}")
        finally:
            # 4b. Always stop the simulation once started.
            if started:
                try:
                    await self.simulation.stop_simulation()
                except Exception as exc:
                    errors.append(f"simulation_stop_failed: {exc}")

        return {
            "samples": samples,
            "led_position": led_position,
            "serial": serial_text,
            "errors": errors,
        }
