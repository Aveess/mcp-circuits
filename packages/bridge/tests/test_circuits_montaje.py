"""`inspect_circuit` no puede responder "vacío" mientras la página monta.

Medido en vivo: tras `open_circuit`, `window.circuit_editor` ya existe pero
`#breadboardTab` y los devices del diseño tardan 1.4–4.5 s en aparecer. En
ese hueco `inspect_circuit` devolvía `success: true` con 0 componentes y 0
cables, y el runner (que sí distingue "no leí" de "0%") tenía que reintentar.

El arreglo es esperar aquí, en la fuente: `open_circuit` después de navegar y
`inspect_circuit` antes de evaluar. Best-effort: si la espera falla, se
inspecciona igual (mejor un vacío declarado que una excepción).
"""

import unittest
from unittest.mock import AsyncMock, MagicMock

from src.browser.browser_manager import BrowserManager
from src.services.circuits_service import CircuitsService


def _service(page):
    browser = MagicMock(spec=BrowserManager)
    browser.get_page = AsyncMock(return_value=page)
    service = CircuitsService(browser)
    service._get_current_title = AsyncMock(return_value="Circuito")
    return service


class TestEsperaDelMontaje(unittest.IsolatedAsyncioTestCase):
    async def test_inspect_espera_a_que_el_diseno_este_montado(self):
        page = AsyncMock()
        page.url = "https://www.tinkercad.com/things/abc/editel"
        page.evaluate = AsyncMock(return_value={"components": [], "wires": []})

        await _service(page).inspect_circuit()

        page.wait_for_function.assert_awaited()
        js = page.wait_for_function.await_args.args[0]
        self.assertIn("circuit_editor", js)
        self.assertIn("breadboardTab", js)
        self.assertGreater(page.wait_for_function.await_args.kwargs["timeout"], 0)

    async def test_la_espera_va_antes_de_leer_el_circuito(self):
        """Si se evalúa primero, el vacío ya se reportó: el orden importa."""
        orden = []
        page = AsyncMock()
        page.url = "https://www.tinkercad.com/things/abc/editel"

        async def esperar(*args, **kwargs):
            orden.append("espera")

        async def evaluar(*args, **kwargs):
            orden.append("evaluate")
            return {"components": [], "wires": []}

        page.wait_for_function = AsyncMock(side_effect=esperar)
        page.evaluate = AsyncMock(side_effect=evaluar)

        await _service(page).inspect_circuit()

        self.assertEqual(orden[0], "espera")

    async def test_si_la_espera_falla_se_inspecciona_igual(self):
        page = AsyncMock()
        page.url = "https://www.tinkercad.com/things/abc/editel"
        page.wait_for_function = AsyncMock(side_effect=RuntimeError("timeout"))
        page.evaluate = AsyncMock(
            return_value={"components": [{"type": "LED", "instance_id": "_1"}], "wires": []}
        )

        res = await _service(page).inspect_circuit()

        self.assertTrue(res["success"])
        self.assertEqual(len(res["components"]), 1)

    async def test_open_circuit_espera_el_montaje_antes_de_retornar(self):
        page = AsyncMock()
        page.url = "https://www.tinkercad.com/things/abc/editel"
        page.is_closed = MagicMock(return_value=True)

        service = _service(page)
        service.browser.navigate = AsyncMock(return_value=page)
        service.browser.find_first_matching = AsyncMock(return_value=object())
        service.browser.close_code_panel = AsyncMock()

        res = await service.open_circuit("abc")

        self.assertTrue(res["success"])
        page.wait_for_function.assert_awaited()


if __name__ == "__main__":
    unittest.main()
