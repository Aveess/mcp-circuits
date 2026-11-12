"""Tests for SimulationSamplerService: all browser access is mocked."""

import base64
import io
import unittest
from unittest.mock import AsyncMock, MagicMock

from PIL import Image

from src.services.simulation_sampler_service import (
    DEFAULT_LED_ON_THRESHOLD,
    SimulationSamplerService,
)


def _png_b64(color, size=(30, 30)):
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _make_service(images_b64, position=None, serial_text="LED ON"):
    """Build a sampler with mocked browser / wiring / simulation / serial."""
    browser = MagicMock()
    page = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    browser.get_page = AsyncMock(return_value=page)
    browser.take_screenshot = AsyncMock(
        side_effect=[{"base64": b64, "path": "shot.png"} for b64 in images_b64]
    )

    wiring = MagicMock()
    if position is None:
        wiring.resolve_terminal = AsyncMock(
            return_value={"success": False, "error": "terminal_lookup_failed"}
        )
    else:
        wiring.resolve_terminal = AsyncMock(
            return_value={"success": True, "x": position[0], "y": position[1]}
        )

    simulation = MagicMock()
    simulation.start_simulation = AsyncMock(return_value={"success": True, "running": True})
    simulation.stop_simulation = AsyncMock(return_value={"success": True, "running": False})
    simulation.get_simulation_status = AsyncMock(
        return_value={"running": True, "simulation_time": "00:00:01"}
    )

    serial = MagicMock()
    serial.read_serial_monitor = AsyncMock(
        return_value={"success": True, "raw_output": serial_text, "lines": [serial_text]}
    )

    service = SimulationSamplerService(
        browser=browser,
        simulation_service=simulation,
        serial_service=serial,
        wiring_service=wiring,
    )
    return service, browser, wiring, simulation, serial


class TestBrightnessComputation(unittest.TestCase):
    def test_dark_image_is_off(self):
        img = Image.new("RGB", (30, 30), (10, 10, 10))
        brightness = SimulationSamplerService.brightness_at(img, 15, 15)
        self.assertLess(brightness, DEFAULT_LED_ON_THRESHOLD)
        on, level = SimulationSamplerService.classify(brightness)
        self.assertFalse(on)
        self.assertEqual(level, 0.0)

    def test_bright_image_is_on(self):
        img = Image.new("RGB", (30, 30), (200, 200, 200))
        brightness = SimulationSamplerService.brightness_at(img, 15, 15)
        self.assertGreater(brightness, DEFAULT_LED_ON_THRESHOLD)
        on, level = SimulationSamplerService.classify(brightness)
        self.assertTrue(on)
        self.assertGreater(level, 0.0)
        self.assertLessEqual(level, 1.0)

    def test_uses_max_channel(self):
        # Pure red pixel: max channel = 255 even though mean would be 85.
        img = Image.new("RGB", (30, 30), (255, 0, 0))
        self.assertEqual(SimulationSamplerService.brightness_at(img, 15, 15), 255.0)

    def test_threshold_is_configurable(self):
        on_default, _ = SimulationSamplerService.classify(150.0)
        on_high, level_high = SimulationSamplerService.classify(150.0, threshold=200.0)
        self.assertTrue(on_default)
        self.assertFalse(on_high)
        self.assertEqual(level_high, 0.0)
        # Level normalisation: halfway between threshold and 255 -> 0.5
        _, level_mid = SimulationSamplerService.classify((144.0 + 255.0) / 2, threshold=144.0)
        self.assertAlmostEqual(level_mid, 0.5, places=2)


class TestSampleFlow(unittest.IsolatedAsyncioTestCase):
    async def test_samples_returned_in_ascending_order(self):
        images = [_png_b64((10, 10, 10)), _png_b64((200, 200, 200)), _png_b64((10, 10, 10))]
        service, browser, wiring, sim, serial = _make_service(images, position=(15, 15))
        result = await service.sample([500, 100, 250])
        self.assertEqual([s["at_ms"] for s in result["samples"]], [100, 250, 500])
        self.assertEqual(result["errors"], [])
        sim.start_simulation.assert_awaited_once()
        sim.stop_simulation.assert_awaited_once()
        self.assertEqual(browser.take_screenshot.await_count, 3)
        for s in result["samples"]:
            self.assertIn("sim_time", s)
            self.assertIn("on", s["led"])
            self.assertGreaterEqual(s["led"]["level"], 0.0)
            self.assertLessEqual(s["led"]["level"], 1.0)

    async def test_dark_then_bright_classification_through_sample(self):
        images = [_png_b64((10, 10, 10)), _png_b64((220, 220, 220))]
        service, *_ = _make_service(images, position=(15, 15))
        result = await service.sample([100, 250])
        self.assertFalse(result["samples"][0]["led"]["on"])
        self.assertEqual(result["samples"][0]["led"]["level"], 0.0)
        self.assertTrue(result["samples"][1]["led"]["on"])
        self.assertGreater(result["samples"][1]["led"]["level"], 0.0)

    async def test_custom_threshold_through_sample(self):
        images = [_png_b64((170, 170, 170))]
        service, *_ = _make_service(images, position=(15, 15))
        result = await service.sample([100], brightness_threshold=200.0)
        self.assertFalse(result["samples"][0]["led"]["on"])

    async def test_serial_included_by_default(self):
        service, _, _, _, serial = _make_service([_png_b64((200, 200, 200))], position=(15, 15))
        result = await service.sample([100])
        self.assertEqual(result["serial"], "LED ON")
        serial.read_serial_monitor.assert_awaited_once()

    async def test_serial_excluded_when_disabled(self):
        service, _, _, _, serial = _make_service([_png_b64((200, 200, 200))], position=(15, 15))
        result = await service.sample([100], read_serial=False)
        self.assertIsNone(result["serial"])
        serial.read_serial_monitor.assert_not_awaited()

    async def test_start_unconfirmed_but_status_active_still_samples(self):
        # Live regression: start reports success=False ("Simulation trigger
        # sent.") yet the simulation is in fact running.
        service, browser, wiring, sim, serial = _make_service(
            [_png_b64((200, 200, 200))], position=(15, 15)
        )
        sim.start_simulation = AsyncMock(
            return_value={"success": False, "running": False, "message": "Simulation trigger sent."}
        )
        sim.get_simulation_status = AsyncMock(
            return_value={"running": True, "simulation_time": "00:00:01"}
        )
        result = await service.sample([100])
        sim.start_simulation.assert_awaited_once_with(wait_seconds=5)
        self.assertEqual(len(result["samples"]), 1)
        self.assertEqual(result["samples"][0]["at_ms"], 100)
        self.assertTrue(result["samples"][0]["led"]["on"])
        self.assertEqual(result["errors"], [])
        browser.take_screenshot.assert_awaited_once()
        sim.stop_simulation.assert_awaited_once()

    async def test_start_failed_and_status_inactive_aborts_without_raising(self):
        service, browser, wiring, sim, serial = _make_service([], position=(15, 15))
        sim.start_simulation = AsyncMock(
            return_value={"success": False, "running": False, "message": "Simulation trigger sent."}
        )
        sim.get_simulation_status = AsyncMock(
            return_value={"running": False, "simulation_time": "00:00:00"}
        )
        result = await service.sample([100, 250])  # must not raise
        sim.start_simulation.assert_awaited_once_with(wait_seconds=5)
        self.assertEqual(result["samples"], [])
        self.assertIsNone(result["serial"])
        self.assertTrue(any("simulation_start_failed" in e for e in result["errors"]))
        browser.take_screenshot.assert_not_awaited()
        sim.stop_simulation.assert_not_awaited()
        serial.read_serial_monitor.assert_not_awaited()

    async def test_unknown_led_position_reports_error_without_raising(self):
        service, browser, wiring, sim, serial = _make_service([], position=None)
        result = await service.sample([100, 250])  # must not raise
        self.assertEqual(result["samples"], [])
        self.assertIsNone(result["serial"])
        self.assertTrue(any("led_position_unknown" in e for e in result["errors"]))
        sim.start_simulation.assert_not_awaited()
        sim.stop_simulation.assert_not_awaited()
        browser.take_screenshot.assert_not_awaited()

    async def test_led_located_before_simulation_starts(self):
        service, _, wiring, sim, _ = _make_service([_png_b64((200, 200, 200))], position=(15, 15))
        order = []
        wiring.resolve_terminal = AsyncMock(
            side_effect=lambda *a, **k: order.append("resolve") or {"success": True, "x": 15, "y": 15}
        )
        sim.start_simulation = AsyncMock(
            side_effect=lambda **k: order.append("start") or {"success": True, "running": True}
        )
        await service.sample([100])
        self.assertEqual(order[0], "resolve")
        self.assertIn("start", order)


if __name__ == "__main__":
    unittest.main()
