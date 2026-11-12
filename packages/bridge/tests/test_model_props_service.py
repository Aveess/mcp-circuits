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
