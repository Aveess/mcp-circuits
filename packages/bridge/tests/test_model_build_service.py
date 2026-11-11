import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services import model_build_service as mbs
from src.services.model_build_service import ModelBuildService


def make_service(evaluate_return=None, pending=None):
    """Build call is evaluate(js, plan); persistence polls are evaluate(js).

    pending: iterable of numberPending() values for the polls (default: 0).
    """
    mock_bm = MagicMock()
    mock_page = AsyncMock()
    pending_iter = iter(pending if pending is not None else [0, 0, 0])

    def _evaluate(*args, **kwargs):
        if len(args) >= 2 or "plan" in kwargs:
            return evaluate_return
        return next(pending_iter, 0)

    mock_page.evaluate = AsyncMock(side_effect=_evaluate)
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
        self.assertTrue(res["persisted"])
        self.assertEqual(res["placed"], placed)
        self.assertEqual(res["errors"], [])
        # 1 build call + 3 persistence polls returning 0
        self.assertEqual(mock_page.evaluate.call_count, 4)
        args = mock_page.evaluate.call_args_list[0].args
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
        plan = mock_page.evaluate.call_args_list[0].args[1]
        self.assertIsNone(plan["code"])


class TestModelBuildPersistence(unittest.IsolatedAsyncioTestCase):
    PARTS = [{"ref": "led1", "did": 58422, "at": "9i", "pin": "anode"}]
    PLACED = {"led1": {"angle": 0, "holes": {"anode": "9i", "cathode": "9j"}}}

    async def test_waits_for_three_consecutive_zeros(self):
        # A non-zero between zeros must reset the stability counter.
        svc, _, mock_page = make_service(
            {"placed": self.PLACED, "errors": []}, pending=[2, 0, 1, 0, 0, 0]
        )
        with patch.object(mbs, "_PERSIST_POLL_S", 0), patch.object(
            mbs, "_PERSIST_TIMEOUT_S", 5
        ):
            res = await svc.build_from_holes(parts=self.PARTS, wires=[])
        self.assertTrue(res["success"])
        self.assertTrue(res["persisted"])
        self.assertNotIn("persistence_pending", res)
        self.assertEqual(mock_page.evaluate.call_count, 1 + 6)

    async def test_pending_js_guards_missing_sharejsdoc(self):
        self.assertIn("shareJsDoc", mbs._PENDING_JS)
        self.assertIn("numberPending", mbs._PENDING_JS)

    async def test_timeout_marks_not_persisted_and_fails(self):
        svc, _, mock_page = make_service(
            {"placed": self.PLACED, "errors": []}, pending=[7] * 1000
        )
        with patch.object(mbs, "_PERSIST_POLL_S", 0.01), patch.object(
            mbs, "_PERSIST_TIMEOUT_S", 0.05
        ):
            res = await svc.build_from_holes(parts=self.PARTS, wires=[])
        self.assertFalse(res["success"])
        self.assertFalse(res["persisted"])
        self.assertEqual(res["persistence_pending"], 7)
        self.assertEqual(res["placed"], self.PLACED)
        self.assertTrue(any("persistence" in e for e in res["errors"]))
        self.assertGreater(mock_page.evaluate.call_count, 1)

    async def test_empty_placed_without_errors_skips_polling(self):
        svc, _, mock_page = make_service({"placed": {}, "errors": []})
        res = await svc.build_from_holes(parts=self.PARTS, wires=[])
        self.assertTrue(res["success"])
        self.assertTrue(res["persisted"])  # vacuous: nothing placed to lose
        mock_page.evaluate.assert_called_once()

    async def test_empty_placed_with_errors_skips_polling_and_fails(self):
        svc, _, mock_page = make_service(
            {"placed": {}, "errors": ["led1: no angle fits"]}
        )
        res = await svc.build_from_holes(parts=self.PARTS, wires=[])
        self.assertFalse(res["success"])
        self.assertIn("persisted", res)
        mock_page.evaluate.assert_called_once()

    async def test_validation_failure_includes_persisted(self):
        svc, mock_bm, _ = make_service()
        res = await svc.build_from_holes(
            parts=[{"ref": "led1", "did": 0, "at": "9i", "pin": "anode"}], wires=[]
        )
        self.assertFalse(res["success"])
        self.assertFalse(res["persisted"])
        mock_bm.get_page.assert_not_called()


if __name__ == "__main__":
    unittest.main()
