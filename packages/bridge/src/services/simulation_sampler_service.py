"""Timed simulation sampling: LED brightness at requested simulation instants.

Ports the sampler concept from netchuu's implementation: start the simulation,
take a screenshot at each requested offset (ms since start), and classify the
LED as on/off from the pixel brightness around its known screen position.
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

# Brightness (average of the per-pixel max RGB channel, 0-255) above which an
# LED is classified as ON. netchuu measured ~128 for an OFF LED and 160-190
# for an ON LED in their implementation; the default below is the midpoint of
# that range. It MUST be recalibrated live against this bridge's screenshots,
# so it is a named constant / parameter rather than a magic number inline.
DEFAULT_LED_ON_THRESHOLD = 144.0

# Side (px) of the square window centred on the LED position that is averaged.
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
    def brightness_at(image: Image.Image, x: int, y: int, window: int = LED_WINDOW_SIZE) -> float:
        """Average of the per-pixel max RGB channel in a window around (x, y).

        The window is ``window`` x ``window`` px centred on (x, y), clamped to
        the image bounds. Returns a value in 0..255.
        """
        img = image.convert("RGB")
        half = max(0, int(window) // 2)
        left = max(0, int(x) - half)
        upper = max(0, int(y) - half)
        right = min(img.width, int(x) + half + 1)
        lower = min(img.height, int(y) + half + 1)
        if right <= left or lower <= upper:
            return 0.0
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
    def classify(brightness: float, threshold: float = DEFAULT_LED_ON_THRESHOLD) -> Tuple[bool, float]:
        """Classify a brightness reading.

        Returns ``(on, level)`` where ``on`` is ``brightness > threshold`` and
        ``level`` is normalised simply as
        ``clamp((brightness - threshold) / (255 - threshold), 0, 1)``:
        0.0 at/below the threshold, 1.0 at full brightness (255).
        """
        on = brightness > threshold
        denom = 255.0 - float(threshold)
        level = 0.0 if denom <= 0 else min(1.0, max(0.0, (brightness - float(threshold)) / denom))
        return on, level

    # ------------------------------------------------------------------ #
    # Browser-dependent helpers
    # ------------------------------------------------------------------ #
    async def _resolve_led_position(self, led_component: str) -> Optional[Tuple[int, int]]:
        """Resolve the LED screen position via WiringService.resolve_terminal.

        Averages the anode and cathode screen coordinates when both resolve
        (approximating the LED body centre); falls back to whichever terminal
        resolves. Returns None when neither can be located.
        """
        points: List[Tuple[int, int]] = []
        for pin in ("anode", "cathode"):
            try:
                res = await self.wiring.resolve_terminal(led_component, pin)
            except Exception as exc:  # browser/DOM errors must not propagate
                logger.debug(f"resolve_terminal({led_component!r}, {pin!r}) failed: {exc}")
                continue
            if isinstance(res, dict) and res.get("success") and res.get("x") is not None and res.get("y") is not None:
                points.append((int(res["x"]), int(res["y"])))
        if not points:
            return None
        return (
            sum(p[0] for p in points) // len(points),
            sum(p[1] for p in points) // len(points),
        )

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
        brightness_threshold: float = DEFAULT_LED_ON_THRESHOLD,
    ) -> Dict[str, Any]:
        """Sample the LED at each requested offset (ms) from simulation start.

        Returns ``{"samples": [{"at_ms", "led": {"on", "level"}, "sim_time"}],
        "serial": str|None, "errors": [...]}``. Never raises for a missing LED:
        that is reported as ``led_position_unknown`` in ``errors``.
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
        led_x, led_y = position

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
                try:
                    image = await self._capture_image()
                    brightness = self.brightness_at(image, led_x, led_y)
                    on, level = self.classify(brightness, brightness_threshold)
                except Exception as exc:
                    errors.append(f"sample_failed at {at_ms}ms: {exc}")
                    on, level = False, 0.0
                samples.append({
                    "at_ms": int(at_ms),
                    "led": {"on": bool(on), "level": float(level)},
                    "sim_time": await self._sim_time(),
                })

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

        return {"samples": samples, "serial": serial_text, "errors": errors}
