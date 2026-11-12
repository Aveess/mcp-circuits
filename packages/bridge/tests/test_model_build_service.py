import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services import model_build_service as mbs
from src.services.model_build_service import ModelBuildService, plan_wire_style


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
        # evaluate receives the styled plan, not the raw pairs
        self.assertEqual(
            plan["wires"],
            [
                {"from": "uno.D13", "to": "5i", "color": "blue", "route": True, "lane": 0},
                {"from": "led1.anode", "to": "T-10", "color": "black", "route": False, "lane": -1},
            ],
        )
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


class TestPlanWireStyle(unittest.TestCase):
    def test_pair_backwards_compatible_and_routed_uno_to_hole(self):
        self.assertEqual(
            plan_wire_style([["uno.D13", "5i"]]),
            [{"from": "uno.D13", "to": "5i", "color": "blue", "route": True, "lane": 0}],
        )

    def test_object_wire_with_explicit_color_kept(self):
        self.assertEqual(
            plan_wire_style([{"from": "uno.D2", "to": "3e", "color": "White"}]),
            [{"from": "uno.D2", "to": "3e", "color": "white", "route": True, "lane": 0}],
        )

    def test_object_wire_without_color_gets_convention_or_palette(self):
        styled = plan_wire_style([{"from": "uno.GND", "to": "T-1"}, {"from": "uno.D2", "to": "3e"}])
        self.assertEqual([w["color"] for w in styled], ["black", "blue"])

    def test_hole_to_hole_not_routed(self):
        styled = plan_wire_style([["5e", "10j"], ["T+5", "1a"]])
        self.assertEqual([(w["route"], w["lane"]) for w in styled], [(False, -1), (False, -1)])

    def test_uno_to_rail_and_reversed_hole_to_uno_routed(self):
        styled = plan_wire_style([["uno.5V", "T+10"], ["7a", "uno.D3"]])
        self.assertEqual([(w["route"], w["lane"]) for w in styled], [(True, 0), (True, 1)])
        self.assertEqual(styled[0]["color"], "red")

    def test_component_endpoint_not_routed(self):
        styled = plan_wire_style([["led1.anode", "9i"], ["uno.D2", "led1.anode"]])
        self.assertTrue(all(not w["route"] and w["lane"] == -1 for w in styled))

    def test_lanes_only_consumed_by_routed_in_arrival_order(self):
        styled = plan_wire_style(
            [["5e", "6e"], ["uno.D2", "5e"], ["1a", "2a"], ["uno.D3", "6e"]]
        )
        self.assertEqual([w["lane"] for w in styled], [-1, 0, -1, 1])

    def test_ground_and_negative_rail_black(self):
        for wire in (
            ["uno.GND", "5e"],
            ["uno.AGND", "5e"],
            ["uno.tierra", "5e"],
            ["5e", "B-3"],
            ["uno.D2", "T-10"],
        ):
            self.assertEqual(plan_wire_style([wire])[0]["color"], "black", wire)

    def test_power_and_positive_rail_red(self):
        for wire in (
            ["uno.5V", "5e"],
            ["uno.3.3V", "5e"],
            ["uno.3V3", "5e"],
            ["uno.VIN", "5e"],
            ["5e", "T+3"],
            ["uno.D2", "B+10"],
        ):
            self.assertEqual(plan_wire_style([wire])[0]["color"], "red", wire)

    def test_explicit_color_beats_convention(self):
        styled = plan_wire_style([{"from": "uno.GND", "to": "T-1", "color": "purple"}])
        self.assertEqual(styled[0]["color"], "purple")

    def test_palette_rotates_without_immediate_repeat(self):
        wires = [[f"uno.D{i}", "5e"] for i in range(2, 11)]
        colors = [w["color"] for w in plan_wire_style(wires)]
        self.assertEqual(colors[:8], mbs._WIRE_PALETTE)
        self.assertEqual(colors[8], "blue")  # wraps; previous was brown
        for prev, cur in zip(colors, colors[1:]):
            self.assertNotEqual(prev, cur)

    def test_palette_skips_previous_explicit_color(self):
        styled = plan_wire_style(
            [
                {"from": "uno.D2", "to": "5e", "color": "blue"},
                ["uno.D3", "6e"],
                ["uno.D4", "7e"],
            ]
        )
        self.assertEqual([w["color"] for w in styled], ["blue", "green", "orange"])

    def test_empty_and_none_wires(self):
        self.assertEqual(plan_wire_style([]), [])
        self.assertEqual(plan_wire_style(None), [])


class TestModelBuildRouting(unittest.IsolatedAsyncioTestCase):
    PARTS = [{"ref": "led1", "did": 58422, "at": "9i", "pin": "anode"}]

    def test_build_js_has_orthogonal_routing_and_color(self):
        js = mbs._BUILD_JS
        self.assertIn("addPoint", js)
        self.assertIn("lane * 5", js)
        self.assertIn("{ color }", js)
        self.assertIn("routed", js)
        self.assertIn("wireSpec", js)  # accepts objects as well as pairs

    def test_build_js_uses_getbreadboardpos_and_indexed_addpoint(self):
        # Weak content check by necessity: the suite has no JS runtime for
        # the real editor API, so it can only pin the required call shapes.
        js = mbs._BUILD_JS
        self.assertIn("getBreadboardPos", js)  # tried before bbDesc/pos fallbacks
        self.assertLess(js.index("getBreadboardPos"), js.index("term?.bbDesc"))
        self.assertIn("p.constructor", js)  # coord ctor from breadboard().pos()
        self.assertRegex(js, r"addPoint\(C \? new C\(pt\.x, pt\.y\) : pt, i \+ 1\)")
        self.assertIn("[pUno, pDest]", js)
        self.assertIn("route_failed", js)  # addPoint errors surface, not swallowed

    def test_build_js_route_debug_and_wire_direction_order(self):
        js = mbs._BUILD_JS
        self.assertIn("route_debug", js)
        for reason in ("uno_pos_null", "dest_pos_null", "addpoint_error", "endpoint_not_resolved", "ok"):
            self.assertIn(reason, js)
        # Points follow wire direction: Uno-as-"to" must start at dest.
        self.assertIn("fromIsUno ? [pUno, pDest] : [pDest, pUno]", js)
        self.assertIn("addPoint returned false", js)  # silent rejection surfaces

    def test_build_js_termabs_fallbacks_for_gnd(self):
        js = mbs._BUILD_JS
        self.assertIn("breadboardDescription", js)
        self.assertIn("breadboardPos", js)
        self.assertIn("termOffset(term)", js)  # device pos + terminal offset
        self.assertIn("devPos(dev)", js)

    def test_build_js_syntax_with_node_if_available(self):
        import shutil
        import subprocess
        import tempfile

        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(mbs._BUILD_JS)
            path = f.name
        res = subprocess.run([node, "--check", path], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)

    async def test_evaluate_receives_styled_plan_for_dict_wires(self):
        svc, _, mock_page = make_service({"placed": {}, "errors": [], "routed": 1})
        res = await svc.build_from_holes(
            parts=self.PARTS,
            wires=[{"from": "uno.5V", "to": "T+5", "color": "orange"}],
        )
        plan = mock_page.evaluate.call_args_list[0].args[1]
        self.assertEqual(
            plan["wires"],
            [{"from": "uno.5V", "to": "T+5", "color": "orange", "route": True, "lane": 0}],
        )
        self.assertEqual(res["routed"], 1)

    async def test_routed_propagates_with_placed(self):
        placed = {"led1": {"angle": 0, "holes": {"anode": "9i", "cathode": "9j"}}}
        svc, _, _ = make_service({"placed": placed, "errors": [], "routed": 3})
        res = await svc.build_from_holes(parts=self.PARTS, wires=[["uno.D13", "5i"]])
        self.assertTrue(res["persisted"])
        self.assertEqual(res["routed"], 3)

    async def test_routed_defaults_to_zero_when_js_omits_it(self):
        svc, _, _ = make_service({"placed": {}, "errors": []})
        res = await svc.build_from_holes(parts=self.PARTS, wires=[])
        self.assertEqual(res["routed"], 0)
        self.assertTrue(res["success"])

    async def test_validation_failure_has_routed_zero(self):
        svc, mock_bm, _ = make_service()
        res = await svc.build_from_holes(
            parts=[{"ref": "led1", "did": 0, "at": "9i", "pin": "anode"}], wires=[]
        )
        self.assertEqual(res["routed"], 0)
        self.assertEqual(res["route_debug"], [])
        mock_bm.get_page.assert_not_called()

    async def test_route_debug_ok_propagates(self):
        debug = [{"wire": "uno.D13 -> 1g", "routed": True, "reason": "ok"}]
        svc, _, _ = make_service({"placed": {}, "errors": [], "routed": 1, "route_debug": debug})
        res = await svc.build_from_holes(parts=self.PARTS, wires=[["uno.D13", "1g"]])
        self.assertEqual(res["route_debug"], debug)
        self.assertEqual(res["errors"], [])
        self.assertTrue(res["success"])

    async def test_route_debug_failed_ground_adds_route_failed_error(self):
        # Regression: 6i -> uno.GND1 was straight/diagonal with no error.
        debug = [
            {"wire": "uno.D13 -> 1g", "routed": True, "reason": "ok"},
            {"wire": "6i -> uno.GND1", "routed": False, "reason": "uno_pos_null"},
        ]
        svc, _, _ = make_service({"placed": {}, "errors": [], "routed": 1, "route_debug": debug})
        res = await svc.build_from_holes(
            parts=self.PARTS, wires=[["uno.D13", "1g"], ["6i", "uno.GND1"]]
        )
        self.assertEqual(res["route_debug"], debug)
        self.assertTrue(any("route_failed" in e and "uno.GND1" in e for e in res["errors"]))
        self.assertFalse(res["success"])

    async def test_route_debug_defaults_empty_when_js_omits_it(self):
        svc, _, _ = make_service({"placed": {}, "errors": []})
        res = await svc.build_from_holes(parts=self.PARTS, wires=[])
        self.assertEqual(res["route_debug"], [])

    async def test_route_debug_js_route_failed_not_duplicated(self):
        debug = [{"wire": "6i -> uno.GND1", "routed": False, "reason": "uno_pos_null"}]
        svc, _, _ = make_service(
            {"placed": {}, "errors": ["wire 6i -> uno.GND1: route_failed: uno_pos_null"],
             "routed": 0, "route_debug": debug}
        )
        res = await svc.build_from_holes(parts=self.PARTS, wires=[["6i", "uno.GND1"]])
        self.assertEqual(len([e for e in res["errors"] if "route_failed" in e]), 1)
        self.assertFalse(res["success"])


class TestModelBuildFreeParts(unittest.IsolatedAsyncioTestCase):
    FREE = {"ref": "motor1", "did": 114158, "free": {"x": 560, "y": 60}, "angle": 0}
    PLACED = {"motor1": {"angle": 0, "holes": {}, "free": {"x": 560, "y": 60}}}

    async def test_free_part_accepted_without_at_or_pin(self):
        svc, _, mock_page = make_service({"placed": self.PLACED, "errors": []})
        res = await svc.build_from_holes(parts=[self.FREE], wires=[["motor1.1", "5e"]])
        self.assertTrue(res["success"])
        self.assertTrue(res["persisted"])
        self.assertEqual(res["placed"], self.PLACED)
        plan = mock_page.evaluate.call_args_list[0].args[1]
        self.assertEqual(plan["parts"], [self.FREE])
        # wire to a free terminal is not routed (no breadboard endpoint)
        self.assertEqual(plan["wires"][0]["route"], False)

    async def test_free_part_float_and_negative_coords_accepted(self):
        svc, _, _ = make_service({"placed": {}, "errors": []})
        part = {"ref": "bat1", "did": 123, "free": {"x": 560.5, "y": -10}}
        res = await svc.build_from_holes(parts=[part], wires=[])
        self.assertTrue(res["success"], res["errors"])

    async def test_free_mixed_with_at_part_accepted(self):
        svc, _, mock_page = make_service({"placed": {}, "errors": []})
        parts = [self.FREE, {"ref": "led1", "did": 58422, "at": "9i", "pin": "anode"}]
        res = await svc.build_from_holes(parts=parts, wires=[])
        self.assertTrue(res["success"], res["errors"])
        self.assertEqual(mock_page.evaluate.call_args_list[0].args[1]["parts"], parts)

    async def test_at_and_free_together_rejected_without_touching_page(self):
        svc, mock_bm, _ = make_service()
        part = {"ref": "motor1", "did": 114158, "at": "9i", "free": {"x": 560, "y": 60}}
        res = await svc.build_from_holes(parts=[part], wires=[])
        self.assertFalse(res["success"])
        self.assertTrue(any("free" in e and "at" in e for e in res["errors"]), res["errors"])
        self.assertEqual(res["placed"], {})
        self.assertFalse(res["persisted"])
        mock_bm.get_page.assert_not_called()

    async def test_free_without_numeric_xy_rejected_without_touching_page(self):
        svc, mock_bm, _ = make_service()
        for bad in ({}, {"x": 560}, {"y": 60}, {"x": "560", "y": 60},
                    {"x": 560, "y": None}, {"x": True, "y": 60},
                    {"x": float("nan"), "y": 60}, "560,60", 560, [560, 60]):
            res = await svc.build_from_holes(
                parts=[{"ref": "motor1", "did": 114158, "free": bad}], wires=[]
            )
            self.assertFalse(res["success"], bad)
            self.assertTrue(any("free" in e for e in res["errors"]), (bad, res["errors"]))
        mock_bm.get_page.assert_not_called()

    def test_build_js_free_branch_places_without_insert_wires(self):
        js = mbs._BUILD_JS
        self.assertIn("part.free", js)
        self.assertIn("cannot specify both at and free", js)
        self.assertIn("free requires numeric x and y", js)
        self.assertIn("setName(part.ref)", js)
        self.assertIn("setAngle(angle)", js)
        self.assertIn("bb.setPos({ x: fx, y: fy })", js)
        self.assertIn("placed[part.ref] = { angle, holes: {}, free: { x: fx, y: fy } }", js)
        # free branch runs (and continues) before the hole/insert-wire path
        self.assertLess(js.index("holes: {}, free:"), js.index("Register each leg"))

    def test_build_js_resolve_endpoint_free_falls_through_to_terminal(self):
        js = mbs._BUILD_JS
        self.assertIn("const holes = placed[ref].holes || {};", js)
        self.assertIn("Free parts have holes == {}", js)
        # after the hole lookup, the real device terminal is the fallback
        hole_lookup = js.index("const holes = placed[ref].holes || {};")
        self.assertLess(hole_lookup, js.index("const found = termByName(dev, pin);", hole_lookup))


class TestBuildCircuitModelToolSchema(unittest.TestCase):
    def test_tool_wires_schema_accepts_dict_wires(self):
        import inspect

        from src.server import server

        tool = next(
            t
            for t in server._tool_manager.list_tools()
            if t.name == "tinkercad_build_circuit_model"
        )
        wires = tool.parameters["properties"]["wires"]
        items = wires.get("items", {})
        # List[List[str]] forces each wire to be an array of strings and
        # rejects dict wires such as {"from": "6i", "to": ..., "color": ...}.
        self.assertNotEqual(items.get("type"), "array")
        ann = str(inspect.signature(tool.fn).parameters["wires"].annotation)
        self.assertNotIn("List[List[str]]", ann)


if __name__ == "__main__":
    unittest.main()
