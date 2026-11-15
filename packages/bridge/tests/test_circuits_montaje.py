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

    async def test_si_la_espera_falla_se_declara_no_montado(self):
        """Antes se inspeccionaba igual; ahora se dice que no se pudo leer.

        El contrato viejo ("mejor un vacio declarado que una excepcion")
        producia `success: true` con 0 componentes: indistinguible de un
        circuito vacio de verdad. La fase 45 lo cambia por un error con
        causa (`editor_not_mounted`), que el runner ya sabe leer.
        """
        page = AsyncMock()
        page.url = "https://www.tinkercad.com/things/abc/editel"
        page.wait_for_function = AsyncMock(side_effect=RuntimeError("timeout"))
        page.evaluate = AsyncMock(
            return_value={"components": [{"type": "LED", "instance_id": "_1"}], "wires": []}
        )

        res = await _service(page).inspect_circuit()

        self.assertFalse(res["success"])
        self.assertEqual(res["reason"], "editor_not_mounted")
        self.assertEqual(res["components"], [])

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


class TestEditorQueNoMonto(unittest.IsolatedAsyncioTestCase):
    """Un editor atascado no es un circuito vacio.

    Medido el 2026-11-14: el servidor de Tinkercad sirvio el HTML del editor
    con `var shareprops;` vacio y el token en `null`. La pagina se queda en
    "Initializing" para siempre y `inspect_circuit` respondia
    `success: true` con 0 componentes: el runner lo leia como "no pude leer"
    (bien) pero sin causa, y el reporte no podia decir que el problema era
    el editor.
    """

    def _pagina_atascada(self):
        page = AsyncMock()
        page.url = "https://www.tinkercad.com/things/abc/editel"
        page.wait_for_function = AsyncMock(side_effect=TimeoutError("sin montar"))
        page.evaluate = AsyncMock(return_value={
            "editor": True, "data": False, "devices": 0, "canvas": False,
            "text": "Initializing",
        })
        return page

    async def test_no_finge_un_circuito_vacio_cuando_el_editor_no_monto(self):
        res = await _service(self._pagina_atascada()).inspect_circuit()

        self.assertFalse(res["success"])
        self.assertEqual(res["reason"], "editor_not_mounted")
        self.assertIn("Initializing", res["message"])
        self.assertEqual(res["components"], [])
        self.assertEqual(res["editor_state"]["text"], "Initializing")

    async def test_un_circuito_vacio_de_verdad_sigue_siendo_valido(self):
        """Montado y sin partes: eso si es un circuito vacio, no un error."""
        page = AsyncMock()
        page.url = "https://www.tinkercad.com/things/abc/editel"
        page.wait_for_function = AsyncMock(return_value=True)
        page.evaluate = AsyncMock(return_value={"components": [], "wires": []})

        res = await _service(page).inspect_circuit()

        self.assertTrue(res["success"])
        self.assertNotIn("reason", res)

    async def test_open_circuit_avisa_que_el_diseno_no_monto(self):
        page = AsyncMock()
        page.url = "https://www.tinkercad.com/things/abc/editel"
        page.wait_for_function = AsyncMock(side_effect=TimeoutError("sin montar"))
        page.evaluate = AsyncMock(return_value={
            "editor": True, "data": False, "devices": 0, "canvas": False,
            "text": "Initializing",
        })
        service = _service(page)
        service.browser.navigate = AsyncMock(return_value=page)
        service.browser.find_first_matching = AsyncMock(return_value=None)
        service.browser.close_code_panel = AsyncMock(return_value=True)

        res = await service.open_circuit("abc")

        self.assertFalse(res["mounted"])
        self.assertEqual(res["editor_state"]["text"], "Initializing")
        self.assertIn("did not mount", res["message"])
