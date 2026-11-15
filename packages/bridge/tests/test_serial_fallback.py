"""El monitor serial se abre aunque el editor intercepte el clic.

Medido el 2026-11-14: con el diseno recien montado, `.root_container.js-editor`
tapa `a#SERIAL_MONITOR_ID` y `Locator.click` se queda 35 s reintentando hasta
agotar el timeout. El boton existe y es el correcto: el problema es el
hit-testing de Playwright, no el selector.

El fallback despacha un `MouseEvent` desde el propio DOM, que no pasa por el
hit-testing. Es best-effort: si aun asi el panel no se abre, se registra y el
que llama decide (el runner falla por `serial_nonempty`).
"""

import unittest
from unittest.mock import AsyncMock, MagicMock

from src.browser.browser_manager import BrowserManager
from src.services.serial_service import SerialService


class _Boton:
    def __init__(self, error=None):
        self.error = error
        self.clicks = 0

    async def click(self, **kwargs):
        self.clicks += 1
        if self.error is not None:
            raise self.error


class _Page:
    """Pagina falsa: registra los JS y devuelve una cola de resultados."""

    def __init__(self, resultados, boton=None):
        self.resultados = list(resultados)
        self.scripts = []
        self.wait_for_timeout = AsyncMock()

    async def evaluate(self, script):
        self.scripts.append(script)
        return self.resultados.pop(0) if self.resultados else self.resultados_default

    @property
    def resultados_default(self):
        return False


class TestFallbackDelMonitorSerial(unittest.IsolatedAsyncioTestCase):
    async def _servicio(self, page, boton):
        browser = MagicMock(spec=BrowserManager)
        browser.get_page = AsyncMock(return_value=page)
        browser.find_first_matching = AsyncMock(return_value=boton)
        service = SerialService(browser)
        service._ensure_code_panel_open = AsyncMock()
        return service

    async def test_clic_interceptado_cae_al_clic_sintetico(self):
        page = _Page([False, True, True])
        boton = _Boton(error=RuntimeError("subtree intercepts pointer events"))
        service = await self._servicio(page, boton)

        await service._ensure_serial_monitor_open(page)

        self.assertEqual(boton.clicks, 1)
        sinteticos = [s for s in page.scripts if "dispatchEvent" in s]
        self.assertEqual(len(sinteticos), 1)
        self.assertIn("js-toggle_serial_monitor", sinteticos[0])

    async def test_clic_normal_no_usa_el_sintetico(self):
        page = _Page([False, True])
        boton = _Boton()
        service = await self._servicio(page, boton)

        await service._ensure_serial_monitor_open(page)

        self.assertEqual(boton.clicks, 1)
        self.assertFalse([s for s in page.scripts if "dispatchEvent" in s])

    async def test_si_no_hay_boton_lanza_el_clic_sintetico(self):
        page = _Page([False, True, True])
        service = await self._servicio(page, None)

        await service._ensure_serial_monitor_open(page)

        self.assertTrue([s for s in page.scripts if "dispatchEvent" in s])

    async def test_panel_que_no_abre_no_revienta(self):
        page = _Page([False, True, False, False, False, False])
        boton = _Boton(error=RuntimeError("intercepted"))
        service = await self._servicio(page, boton)
        # La espera por alto se acorta: 2 intentos.
        service._serial_open_poll_attempts = 2
        service._serial_open_poll_ms = 0

        await service._ensure_serial_monitor_open(page)  # no debe lanzar


if __name__ == "__main__":
    unittest.main()
