import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services import model_props_service as mps
from src.services.model_props_service import ModelPropsService

HC_SR04 = {"id": "42", "name": "DIST1", "type": "Ultrasonic Distance Sensor (4-pin)"}


def make_service(evaluate_return=None, pending=None):
    """Set call is evaluate(js, arg); persistence polls are evaluate(js)."""
    mock_bm = MagicMock()
    mock_page = AsyncMock()
    pending_iter = iter(pending if pending is not None else [0, 0, 0])

    def _evaluate(*args, **kwargs):
        if len(args) >= 2 or "arg" in kwargs:
            return evaluate_return
        return next(pending_iter, 0)

    mock_page.evaluate = AsyncMock(side_effect=_evaluate)
    mock_bm.get_page = AsyncMock(return_value=mock_page)
    return ModelPropsService(mock_bm), mock_bm, mock_page


class TestModelPropsValidation(unittest.IsolatedAsyncioTestCase):
    async def test_empty_component_name_rejected_without_touching_page(self):
        svc, mock_bm, _ = make_service()
        for bad in ("", "   ", None):
            res = await svc.set_property(bad, "Target Y", 100)
            self.assertFalse(res["success"], bad)
            self.assertFalse(res["persisted"], bad)
            self.assertTrue(any("component_name" in e for e in res["errors"]), bad)
        mock_bm.get_page.assert_not_called()

    async def test_empty_property_name_rejected_without_touching_page(self):
        svc, mock_bm, _ = make_service()
        for bad in ("", "   ", None):
            res = await svc.set_property("Potentiometer", bad, 0.5)
            self.assertFalse(res["success"], bad)
            self.assertFalse(res["persisted"], bad)
            self.assertTrue(any("property_name" in e for e in res["errors"]), bad)
        mock_bm.get_page.assert_not_called()


class TestModelPropsSetProperty(unittest.IsolatedAsyncioTestCase):
    async def test_device_not_found(self):
        svc, _, mock_page = make_service(
            {"status": "not_found", "component": None, "candidates": [],
             "errors": ["component not found: Nope"]}
        )
        res = await svc.set_property("Nope", "Target Y", 100)
        self.assertFalse(res["success"])
        self.assertFalse(res["persisted"])
        self.assertEqual(res["component"], "Nope")
        self.assertEqual(res["property"], "Target Y")
        self.assertEqual(res["value"], 100)
        self.assertTrue(any("not found" in e for e in res["errors"]))
        mock_page.evaluate.assert_called_once()  # no persistence polling

    async def test_ambiguous_returns_candidates_without_raising(self):
        candidates = [
            {"id": "1", "name": "Pot1", "type": "Potentiometer"},
            {"id": "2", "name": "Pot2", "type": "Potentiometer"},
        ]
        svc, _, mock_page = make_service(
            {"status": "ambiguous", "component": None, "candidates": candidates,
             "errors": ["ambiguous component name: Potentiometer"]}
        )
        res = await svc.set_property("Potentiometer", "Position", 0.5)
        self.assertFalse(res["success"])
        self.assertFalse(res["persisted"])
        self.assertEqual(res["candidates"], candidates)
        self.assertTrue(any("ambiguous" in e for e in res["errors"]))
        mock_page.evaluate.assert_called_once()

    async def test_happy_path_sets_and_persists(self):
        svc, _, mock_page = make_service(
            {"status": "ok", "component": HC_SR04, "candidates": [], "errors": []},
            pending=[1, 0, 0, 0],
        )
        with patch.object(mps, "_PERSIST_POLL_S", 0):
            res = await svc.set_property(
                "Ultrasonic Distance Sensor (4-pin)", "Target Y", 150, unit="cm"
            )
        self.assertTrue(res["success"])
        self.assertTrue(res["persisted"])
        self.assertEqual(res["component"], "DIST1")
        self.assertEqual(res["property"], "Target Y")
        self.assertEqual(res["value"], 150)
        self.assertEqual(res["errors"], [])
        # 1 set call + 4 persistence polls (1, then three consecutive 0s)
        self.assertEqual(mock_page.evaluate.call_count, 5)
        js, arg = mock_page.evaluate.call_args_list[0].args
        self.assertIn("setProperty", js)
        self.assertIn("rec()", js)
        self.assertIn("stopRec", js)
        self.assertEqual(
            arg,
            {"component_name": "Ultrasonic Distance Sensor (4-pin)",
             "property_name": "Target Y", "value": 150, "unit": "cm"},
        )

    async def test_value_and_default_unit_passed_as_is(self):
        svc, _, mock_page = make_service(
            {"status": "ok", "component": HC_SR04, "candidates": [], "errors": []}
        )
        with patch.object(mps, "_PERSIST_POLL_S", 0):
            res = await svc.set_property("DIST1", "Position", 0.25)
        self.assertTrue(res["success"])
        arg = mock_page.evaluate.call_args_list[0].args[1]
        self.assertEqual(arg["value"], 0.25)
        self.assertIsInstance(arg["value"], float)
        self.assertIsNone(arg["unit"])

    async def test_js_error_fails_without_polling(self):
        svc, _, mock_page = make_service(
            {"status": "error", "component": HC_SR04, "candidates": [],
             "errors": ["Error: unknown property Target Z"]}
        )
        res = await svc.set_property("DIST1", "Target Z", 1)
        self.assertFalse(res["success"])
        self.assertFalse(res["persisted"])
        self.assertTrue(any("unknown property" in e for e in res["errors"]))
        mock_page.evaluate.assert_called_once()

    async def test_invalid_js_response_fails(self):
        svc, _, _ = make_service(None)
        res = await svc.set_property("DIST1", "Target Y", 1)
        self.assertFalse(res["success"])
        self.assertFalse(res["persisted"])
        self.assertTrue(any("invalid response" in e for e in res["errors"]))

    async def test_persistence_timeout_fails(self):
        svc, _, _ = make_service(
            {"status": "ok", "component": HC_SR04, "candidates": [], "errors": []},
            pending=[3] * 1000,
        )
        with patch.object(mps, "_PERSIST_POLL_S", 0.01), patch.object(
            mps, "_PERSIST_TIMEOUT_S", 0.05
        ):
            res = await svc.set_property("DIST1", "Target Y", 10)
        self.assertFalse(res["success"])
        self.assertFalse(res["persisted"])
        self.assertEqual(res["persistence_pending"], 3)
        self.assertTrue(any("persistence timeout" in e for e in res["errors"]))

    def test_set_js_matches_by_name_or_type_inside_rec(self):
        js = mps._SET_PROP_JS
        self.assertIn("dev.setProperty(arg.property_name, null, arg.value, arg.unit ?? null)", js)
        self.assertIn("norm(info.name) === query", js)
        self.assertIn("norm(info.type) === query", js)
        self.assertIn("getDescription", js)


if __name__ == "__main__":
    unittest.main()


class TestModelPropsEsperaElEditor(unittest.IsolatedAsyncioTestCase):
    """Las propiedades no pueden correr con la página a medio montar.

    Medido en la regresión de la fase 44: `set_component_property_model`
    devolvía `circuit_editor not available` para el HC-SR04 y tumbaba el
    build del sensor ultrasónico. Era una carrera, no el circuito.
    """

    def _service(self, sets):
        mock_bm = MagicMock()
        page = AsyncMock()
        pending = iter([0, 0, 0, 0])
        sets_iter = iter(sets)
        orden = []
        self._sets_args = []

        async def _wait_for_function(*args, **kwargs):
            orden.append("espera")

        async def _evaluate(*args, **kwargs):
            if len(args) >= 2 or "arg" in kwargs:
                orden.append("set")
                self._sets_args.append(args[1] if len(args) >= 2 else kwargs.get("arg"))
                return next(sets_iter)
            return next(pending, 0)

        page.wait_for_function = AsyncMock(side_effect=_wait_for_function)
        page.evaluate = AsyncMock(side_effect=_evaluate)
        mock_bm.get_page = AsyncMock(return_value=page)
        return ModelPropsService(mock_bm), page, orden

    async def test_espera_al_editor_antes_de_tocar_el_modelo(self):
        ok = {"status": "ok", "component": HC_SR04, "errors": []}
        svc, page, orden = self._service([ok])

        res = await svc.set_property("DIST1", "Target Y", -105)

        self.assertTrue(res["success"])
        page.wait_for_function.assert_awaited()
        self.assertEqual(orden[0], "espera")

    async def test_si_cae_en_la_guarda_reintenta_una_vez(self):
        guarda = {"status": "error", "component": None, "candidates": [],
                  "errors": ["circuit_editor not available"]}
        ok = {"status": "ok", "component": HC_SR04, "errors": []}
        svc, page, orden = self._service([guarda, ok])

        res = await svc.set_property("DIST1", "Target Y", -105)

        self.assertTrue(res["success"])
        # dos esperas: antes del primer intento y antes del reintento
        self.assertEqual(orden.count("espera"), 2)
        self.assertEqual(orden.count("set"), 2)
        # los argumentos no se pierden en el reintento
        self.assertEqual(self._sets_args[0]["value"], -105)
        self.assertEqual(self._sets_args[1]["value"], -105)

    async def test_si_la_guarda_persiste_el_error_se_reporta(self):
        guarda = {"status": "error", "component": None, "candidates": [],
                  "errors": ["circuit_editor not available"]}
        svc, _, _ = self._service([guarda, guarda])

        res = await svc.set_property("DIST1", "Target Y", -105)

        self.assertFalse(res["success"])
        self.assertFalse(res["persisted"])
        self.assertTrue(any("circuit_editor not available" in e for e in res["errors"]))
