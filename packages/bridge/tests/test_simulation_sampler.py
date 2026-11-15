"""Tests for SimulationSamplerService: all browser access is mocked."""

import base64
import io
import unittest
from unittest.mock import AsyncMock, MagicMock

from PIL import Image

from src.services.simulation_sampler_service import (
    DEFAULT_LED_LIT_THRESHOLD,
    SimulationSamplerService,
)


# Colores medidos en vivo sobre blink-basico (2tMhkuosDyj), en el LED:
LED_OFF = (128, 32, 32)      # lente apagado
LED_ON = (207, 132, 132)     # lente encendido
PLASTICO = (208, 208, 208)   # plastico blanco de la protoboard


def _png_b64(color, size=(30, 30)):
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _make_service(images_b64, position=None, serial_text="LED ON", body=None):
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
        payload = {"success": True, "x": position[0], "y": position[1]}
        if body is not None:
            payload["body"] = body
        wiring.resolve_terminal = AsyncMock(return_value=payload)

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
    """El brillo medio no distingue un LED apagado del plastico blanco.

    Medido en blink-basico: el plastico de la protoboard ronda 208 de brillo
    siempre, el lente apagado 128 y el encendido 207. Un umbral de brillo no
    puede separar "208 plastico" de "207 LED encendido": por eso el clasificador
    cuenta pixeles **encendidos** (brillantes y saturados) en la ventana.
    """

    def test_led_apagado_no_cuenta_como_encendido(self):
        img = Image.new("RGB", (30, 30), LED_OFF)
        lit = SimulationSamplerService.lit_fraction(img, 15, 15)
        on, level = SimulationSamplerService.classify(lit)
        self.assertFalse(on)
        self.assertEqual(level, 0.0)

    def test_led_encendido_cuenta_como_encendido(self):
        img = Image.new("RGB", (30, 30), LED_ON)
        lit = SimulationSamplerService.lit_fraction(img, 15, 15)
        self.assertAlmostEqual(lit, 1.0)
        on, level = SimulationSamplerService.classify(lit)
        self.assertTrue(on)
        self.assertGreater(level, 0.0)
        self.assertLessEqual(level, 1.0)

    def test_el_plastico_blanco_no_cuenta_como_encendido(self):
        """El bug medido: el pin cae en el plastico (208) y el sampler decia ON."""
        img = Image.new("RGB", (30, 30), PLASTICO)
        lit = SimulationSamplerService.lit_fraction(img, 15, 15)
        on, _ = SimulationSamplerService.classify(lit)
        self.assertFalse(on)

    def test_un_pixel_brillante_pero_gris_no_cuenta(self):
        """Brillo sin saturacion es plastico/metal: no es un LED emitiendo."""
        img = Image.new("RGB", (30, 30), (230, 230, 230))
        self.assertEqual(SimulationSamplerService.lit_fraction(img, 15, 15), 0.0)

    def test_un_pixel_saturado_pero_oscuro_no_cuenta(self):
        """Un LED apagado es rojo oscuro (128,32,32): saturado, pero no emite."""
        img = Image.new("RGB", (30, 30), (128, 32, 32))
        self.assertEqual(SimulationSamplerService.lit_fraction(img, 15, 15), 0.0)

    def test_uses_max_channel_for_brightness(self):
        # Pure red pixel: max channel = 255 even though mean would be 85.
        img = Image.new("RGB", (30, 30), (255, 0, 0))
        self.assertEqual(SimulationSamplerService.brightness_at(img, 15, 15), 255.0)

    def test_threshold_is_configurable(self):
        on_default, _ = SimulationSamplerService.classify(0.5)
        on_high, level_high = SimulationSamplerService.classify(0.5, threshold=0.8)
        self.assertTrue(on_default)
        self.assertFalse(on_high)
        self.assertEqual(level_high, 0.0)
        # level = fraccion de la ventana que emite (cuando emite)
        _, level_mid = SimulationSamplerService.classify(DEFAULT_LED_LIT_THRESHOLD * 2)
        self.assertAlmostEqual(level_mid, DEFAULT_LED_LIT_THRESHOLD * 2, places=3)

    def test_una_ventana_fuera_de_la_captura_no_devuelve_fraccion(self):
        img = Image.new("RGB", (30, 30), LED_ON)
        self.assertIsNone(SimulationSamplerService.lit_fraction(img, 60, 15))


class TestSampleFlow(unittest.IsolatedAsyncioTestCase):
    async def test_samples_returned_in_ascending_order(self):
        images = [_png_b64(LED_OFF), _png_b64(LED_ON), _png_b64(LED_OFF)]
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
        images = [_png_b64(LED_OFF), _png_b64(LED_ON)]
        service, *_ = _make_service(images, position=(15, 15))
        result = await service.sample([100, 250])
        self.assertFalse(result["samples"][0]["led"]["on"])
        self.assertEqual(result["samples"][0]["led"]["level"], 0.0)
        self.assertTrue(result["samples"][1]["led"]["on"])
        self.assertGreater(result["samples"][1]["led"]["level"], 0.0)

    async def test_custom_threshold_through_sample(self):
        """El umbral es la fraccion de la ventana que debe emitir."""
        images = [_png_b64(LED_ON), _png_b64(LED_ON)]
        service, *_ = _make_service(images, position=(15, 15))
        result = await service.sample([100], lit_threshold=1.5)  # imposible
        self.assertFalse(result["samples"][0]["led"]["on"])
        result = await service.sample([100], lit_threshold=0.01)
        self.assertTrue(result["samples"][0]["led"]["on"])

    async def test_serial_included_by_default(self):
        service, _, _, _, serial = _make_service([_png_b64(LED_ON)], position=(15, 15))
        result = await service.sample([100])
        self.assertEqual(result["serial"], "LED ON")
        serial.read_serial_monitor.assert_awaited_once()

    async def test_serial_excluded_when_disabled(self):
        service, _, _, _, serial = _make_service([_png_b64(LED_ON)], position=(15, 15))
        result = await service.sample([100], read_serial=False)
        self.assertIsNone(result["serial"])
        serial.read_serial_monitor.assert_not_awaited()

    async def test_start_unconfirmed_but_status_active_still_samples(self):
        # Live regression: start reports success=False ("Simulation trigger
        # sent.") yet the simulation is in fact running.
        service, browser, wiring, sim, serial = _make_service(
            [_png_b64(LED_ON)], position=(15, 15)
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
        service, _, wiring, sim, _ = _make_service([_png_b64(LED_ON)], position=(15, 15))
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


class TestVentanaMedida(unittest.IsolatedAsyncioTestCase):
    """El sampler no puede confundir "no lo vi" con "estaba apagado".

    `brightness_at` recorta una ventana de 9x9 centrada en el pin y la clampa
    al borde de la captura. Si el LED queda **fuera** de la captura (el lienzo
    de Tinkercad se puede panelear), el recorte queda vacio y la lectura da
    0.0: el LED se reporta apagado sin haberlo mirado nunca. Eso es un falso
    negativo que hace mentir al oraculo.
    """

    async def test_un_led_fuera_de_la_captura_no_se_reporta_como_apagado(self):
        service, _, _, sim, _ = _make_service(
            [_png_b64(LED_ON)], position=(2000, 100))
        result = await service.sample([100])
        self.assertEqual(result["samples"], [])
        self.assertTrue(any("led_offscreen" in e for e in result["errors"]), result["errors"])
        # La simulacion se arranco y se paro igual: no queda corriendo.
        sim.stop_simulation.assert_awaited_once()

    async def test_cada_muestra_dice_que_ventana_midio(self):
        service, *_ = _make_service([_png_b64(LED_ON)], position=(15, 15))
        result = await service.sample([100])
        self.assertEqual(result["samples"][0]["window_px"], [9, 9])

    async def test_led_pegado_al_borde_mide_una_ventana_menor(self):
        """Cerca del borde el recorte se achica: se mide y se informa igual."""
        service, *_ = _make_service([_png_b64(LED_ON)], position=(1, 1))
        result = await service.sample([100])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["samples"][0]["window_px"], [6, 6])
        self.assertTrue(result["samples"][0]["led"]["on"])

    async def test_una_imagen_mas_pequena_que_la_ventana_se_mide_completa(self):
        service, *_ = _make_service([_png_b64((220, 220, 220), size=(4, 4))], position=(2, 2))
        result = await service.sample([100])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["samples"][0]["window_px"], [4, 4])

    def test_window_bounds_devuelve_none_solo_si_no_hay_nada_que_medir(self):
        img = Image.new("RGB", (30, 30), (10, 10, 10))
        self.assertEqual(SimulationSamplerService.window_bounds(img, 15, 15), (11, 11, 20, 20))
        self.assertIsNone(SimulationSamplerService.window_bounds(img, 60, 15))
        self.assertIsNone(SimulationSamplerService.window_bounds(img, -20, 15))


class TestCuerpoDelLed(unittest.IsolatedAsyncioTestCase):
    """Donde se mide: el cuerpo del LED, no el hueco donde entra la pata.

    Medido en blink-basico (2tMhkuosDyj): el ancla del anodo cae en (843,492),
    el catodo en (879,477) y su promedio (861,484) queda sobre el plastico
    blanco de la protoboard, 15 px a la izquierda del LED que se enciende en
    (876,487). Promediar pines no da el cuerpo: da el hueco.
    """

    BODY = {"x": 869, "y": 475, "width": 12, "height": 23, "cx": 875, "cy": 486}

    async def test_usa_el_centro_del_cuerpo_cuando_esta_disponible(self):
        service, *_ = _make_service(
            [_png_b64(LED_ON, size=(1000, 700))], position=(843, 492), body=self.BODY)
        result = await service.sample([100])
        self.assertEqual(result["led_position"]["x"], 875)
        self.assertEqual(result["led_position"]["y"], 486)
        self.assertEqual(result["led_position"]["source"], "body")
        self.assertEqual(result["samples"][0]["measured_at_px"], [875, 486])

    async def test_sin_cuerpo_cae_al_promedio_de_pines_y_lo_dice(self):
        service, *_ = _make_service(
            [_png_b64(LED_ON, size=(1000, 700))], position=(843, 492))
        result = await service.sample([100])
        self.assertEqual(result["led_position"]["x"], 843)
        self.assertEqual(result["led_position"]["y"], 492)
        self.assertEqual(result["led_position"]["source"], "pins")

    async def test_un_cuerpo_vacio_no_se_usa(self):
        """Un body con ancho 0 no es geometria: mejor el pin que un punto falso."""
        service, *_ = _make_service(
            [_png_b64(LED_ON, size=(1000, 700))], position=(843, 492),
            body={"x": 0, "y": 0, "width": 0, "height": 0, "cx": 0, "cy": 0})
        result = await service.sample([100])
        self.assertEqual(result["led_position"]["source"], "pins")
        self.assertEqual(result["samples"][0]["measured_at_px"], [843, 492])


if __name__ == "__main__":
    unittest.main()
