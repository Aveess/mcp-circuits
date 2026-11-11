import unittest
from unittest.mock import AsyncMock, MagicMock

from src.services.model_build_service import ModelBuildService


def make_service(evaluate_return=None):
    mock_bm = MagicMock()
    mock_page = AsyncMock()
    mock_page.evaluate = AsyncMock(return_value=evaluate_return)
    mock_bm.get_page = AsyncMock(return_value=mock_page)
    return ModelBuildService(mock_bm), mock_bm, mock_page


class TestModelBuildValidation(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_did_rejected_without_touching_page(self):
        svc, mock_bm, _ = make_service()
        for bad in (0, -1, "58422", None, True, 58.5):
            res = await svc.build_from_holes(
                parts=[{"ref": "led1", "did": bad, "at": "9i", "pin": "anode"}],
                wires=[],
            )
            self.assertFalse(res["success"], bad)
            self.assertTrue(res["errors"], bad)
        mock_bm.get_page.assert_not_called()

    async def test_invalid_at_rejected_without_touching_page(self):
        svc, mock_bm, _ = make_service()
        for bad in ("31a", "0a", "9k", "i9", "", None, "T-10"):
            res = await svc.build_from_holes(
                parts=[{"ref": "led1", "did": 58422, "at": bad, "pin": "anode"}],
                wires=[],
            )
            self.assertFalse(res["success"], bad)
            self.assertTrue(any("at" in e for e in res["errors"]), bad)
        mock_bm.get_page.assert_not_called()

    async def test_valid_hole_bounds_accepted(self):
        svc, _, mock_page = make_service({"placed": {}, "errors": []})
        for good in ("1a", "30j", "15e"):
            res = await svc.build_from_holes(
                parts=[{"ref": "r1", "did": 53184, "at": good, "pin": "1"}],
                wires=[],
            )
            self.assertTrue(res["success"], good)
        self.assertEqual(mock_page.evaluate.call_count, 3)


class TestModelBuildEvaluate(unittest.IsolatedAsyncioTestCase):
    async def test_evaluate_called_once_with_plan(self):
        placed = {"led1": {"angle": 180, "holes": {"anode": "9i", "cathode": "9j"}}}
        svc, _, mock_page = make_service({"placed": placed, "errors": []})
        parts = [{"ref": "led1", "did": 58422, "at": "9i", "pin": "anode", "angle": 180}]
        wires = [["uno.D13", "5i"], ["led1.anode", "T-10"]]
        res = await svc.build_from_holes(parts=parts, wires=wires, code="void setup(){}")
        self.assertTrue(res["success"])
        self.assertEqual(res["placed"], placed)
        self.assertEqual(res["errors"], [])
        mock_page.evaluate.assert_called_once()
        args = mock_page.evaluate.call_args.args
        js, plan = args[0], args[1]
        self.assertIn("createDeviceInstance", js)
        self.assertIn("BendableWireData", js)
        self.assertIn("insert", js)
        self.assertIn("rec()", js)
        self.assertIn("stopRec", js)
        self.assertEqual(plan["parts"], parts)
        self.assertEqual(plan["wires"], wires)
        self.assertEqual(plan["code"], "void setup(){}")

    async def test_js_errors_propagate_as_success_false(self):
        svc, _, _ = make_service({"placed": {}, "errors": ["led1: no angle fits"]})
        res = await svc.build_from_holes(
            parts=[{"ref": "led1", "did": 58422, "at": "9i", "pin": "anode"}],
            wires=[],
        )
        self.assertFalse(res["success"])
        self.assertEqual(res["errors"], ["led1: no angle fits"])

    async def test_code_defaults_to_none_in_plan(self):
        svc, _, mock_page = make_service({"placed": {}, "errors": []})
        await svc.build_from_holes(
            parts=[{"ref": "r1", "did": 53184, "at": "5e", "pin": "1"}], wires=[]
        )
        plan = mock_page.evaluate.call_args.args[1]
        self.assertIsNone(plan["code"])


if __name__ == "__main__":
    unittest.main()
