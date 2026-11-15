"""Tests del sondeo de persistencia de ShareJS compartido por build y codigo.

El contrato importa: recargar la pagina antes de que la cola se vacie descarta
el cambio (medido en vivo con un sketch largo), y un sondeo que falla no puede
contarse como "cero pendientes" — seria declarar guardado lo que no se miro.
"""

import unittest
from unittest.mock import AsyncMock, patch

from src.services import model_build_service
from src.services.sharejs import PENDING_JS, wait_for_persistence


class _Page:
    """Pagina falsa: devuelve valores en orden y repite el ultimo."""

    def __init__(self, values):
        self.values = list(values)
        self.calls = 0

    async def evaluate(self, script):
        self.calls += 1
        if script is not PENDING_JS:
            raise AssertionError("se esperaba el sondeo de numberPending()")
        if len(self.values) > 1:
            return self.values.pop(0)
        return self.values[0]


class _RaisingPage:
    def __init__(self):
        self.calls = 0

    async def evaluate(self, script):
        self.calls += 1
        raise RuntimeError("target closed")


class TestWaitForPersistence(unittest.IsolatedAsyncioTestCase):
    async def test_espera_tres_ceros_seguidos(self):
        page = _Page([2, 1, 0, 0, 0])
        persisted, last = await wait_for_persistence(page, poll_s=0)
        self.assertTrue(persisted)
        self.assertEqual(last, 0)
        self.assertEqual(page.calls, 5)

    async def test_un_valor_distinto_de_cero_corta_la_racha(self):
        page = _Page([0, 0, 1, 0, 0, 0])
        persisted, last = await wait_for_persistence(page, poll_s=0)
        self.assertTrue(persisted)
        self.assertEqual(page.calls, 6)

    async def test_timeout_devuelve_el_ultimo_pendiente(self):
        page = _Page([3])
        persisted, last = await wait_for_persistence(page, timeout_s=0, poll_s=0)
        self.assertFalse(persisted)
        self.assertEqual(last, 3)

    async def test_un_sondeo_que_falla_no_cuenta_como_cero(self):
        page = _RaisingPage()
        persisted, last = await wait_for_persistence(page, timeout_s=0, poll_s=0)
        self.assertFalse(persisted)
        self.assertIsNone(last)

    async def test_un_booleano_no_es_un_conteo(self):
        page = _Page([True])
        persisted, last = await wait_for_persistence(page, timeout_s=0, poll_s=0)
        self.assertFalse(persisted)
        self.assertIsNone(last)


class TestModelBuildUsaElCompartido(unittest.IsolatedAsyncioTestCase):
    async def test_el_build_delega_en_el_helper(self):
        service = model_build_service.ModelBuildService.__new__(
            model_build_service.ModelBuildService
        )
        page = object()
        with patch(
            "src.services.model_build_service.wait_for_persistence",
            new=AsyncMock(return_value=(True, 0)),
        ) as helper:
            result = await service._wait_for_persistence(page)
        self.assertEqual(result, (True, 0))
        helper.assert_awaited_once()
        self.assertIs(helper.await_args.args[0], page)


if __name__ == "__main__":
    unittest.main()
