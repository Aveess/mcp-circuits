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
        # Fase 39: los carriles ya no son una numeracion unica (115 + lane*5).
        # Cada banda (arriba/abajo) lleva su propio contador y crece de 8 en 8.
        self.assertIn("sideLanes", js)
        self.assertIn("LANE_STEP", js)
        self.assertNotIn("115 + lane * 5", js)
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

    async def test_un_cable_recto_a_proposito_no_es_un_fallo(self):
        """Fase 41: el puente mide tambien los cables que no rutea.

        `routed: false, reason: "straight"` es un cable que ya nacia
        ortogonal (dos huecos de la placa, dos pines en la misma fila). Antes
        cualquier `routed: false` se volvia error de build y el circuito
        quedaba OK: False aunque el cable estuviera bien.
        """
        debug = [
            {"wire": "1g -> T+2", "routed": False, "reason": "straight",
             "points": [[-105, -25], [-75, -95]]},
        ]
        svc, _, _ = make_service({"placed": {}, "errors": [], "routed": 0,
                                  "route_debug": debug})
        res = await svc.build_from_holes(parts=self.PARTS, wires=[["1g", "T+2"]])
        self.assertEqual(res["errors"], [])
        self.assertTrue(res["success"])

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


class TestTermByNameExactPlusMinus(unittest.TestCase):
    def _run_term_by_name(self):
        import json
        import shutil
        import subprocess

        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        harness = r"""
const src = __SRC__;
const start = src.indexOf('const unwrap');
const end = src.indexOf('function termOffset');
if (start < 0 || end <= start) throw new Error('termByName chunk not found');
const termByName = new Function(src.slice(start, end) + '\nreturn termByName;')();
function dev(entries) {
  const content = {};
  for (const [k, id] of entries) content[k] = { val: { id } };
  return { name2terminal: { _content: content } };
}
// '+' first on purpose: the old norm('') bug resolved '-' to '+'.
const both = dev([['+', 'plus'], ['-', 'minus']]);
const onlyPlus = dev([['+', 'plus']]);
const pick = (r) => (r ? { name: r.name, id: r.term.id } : null);
console.log(JSON.stringify({
  plus: pick(termByName(both, '+')),
  minus: pick(termByName(both, '-')),
  missingMinus: pick(termByName(onlyPlus, '-')),
  emptyNormMissing: pick(termByName(onlyPlus, '++')),
}));
"""
        script = harness.replace("__SRC__", json.dumps(mbs._BUILD_JS))
        res = subprocess.run(
            [node, "-e", script], capture_output=True, text=True, timeout=30
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        import json as _json

        return _json.loads(res.stdout.strip().splitlines()[-1])

    def test_exact_plus_and_minus_resolve_to_their_own_terminals(self):
        out = self._run_term_by_name()
        self.assertEqual(out["plus"], {"name": "+", "id": "plus"})
        self.assertEqual(out["minus"], {"name": "-", "id": "minus"})

    def test_minus_without_exact_terminal_does_not_resolve_to_plus(self):
        out = self._run_term_by_name()
        self.assertIsNone(out["missingMinus"])
        self.assertIsNone(out["emptyNormMissing"])

    def test_build_js_exact_match_precedes_normalized_match(self):
        js = mbs._BUILD_JS
        segment = js[js.index("function termByName") : js.index("function termOffset")]
        self.assertIn("k === pin", segment)
        self.assertLess(segment.index("k === pin"), segment.index("norm(k) === norm(pin)"))
        self.assertIn("if (!norm(pin)) return null;", segment)


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
        # free terminal -> breadboard hole is orthogonally routed
        self.assertEqual(
            plan["wires"][0],
            {"from": "motor1.1", "to": "5e", "color": "blue", "route": True, "lane": 0},
        )

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
        self.assertIn("placed[part.ref] = { angle, holes: {}, free: { x: fx, y: fy },", js)
        # El nombre real que dejo el editor viaja en el placed (fase 39).
        self.assertIn("name: readName(dev, part.ref) }", js)
        # free branch runs (and continues) before the hole/insert-wire path
        self.assertLess(js.index("holes: {}, free:"), js.index("Register each leg"))

    def test_build_js_resolve_endpoint_free_falls_through_to_terminal(self):
        js = mbs._BUILD_JS
        self.assertIn("const holes = placed[ref].holes || {};", js)
        self.assertIn("Free parts have holes == {}", js)
        # after the hole lookup, the real device terminal is the fallback
        hole_lookup = js.index("const holes = placed[ref].holes || {};")
        self.assertLess(hole_lookup, js.index("const found = termByName(dev, pin);", hole_lookup))


def make_service_with_clear(build_return=None, clear_return=None, pending=None):
    mock_bm = MagicMock()
    mock_page = AsyncMock()
    pending_iter = iter(pending if pending is not None else [0] * 20)
    clear = clear_return if clear_return is not None else {
        "cleared": True, "removed_wires": 2, "removed_devices": 1,
        "kept_uno": True, "errors": [],
    }

    def _evaluate(*args, **kwargs):
        if args and args[0] == mbs._CLEAR_JS:
            return clear
        if len(args) >= 2 or "plan" in kwargs:
            return build_return
        return next(pending_iter, 0)

    mock_page.evaluate = AsyncMock(side_effect=_evaluate)
    mock_bm.get_page = AsyncMock(return_value=mock_page)
    return ModelBuildService(mock_bm), mock_bm, mock_page


class TestModelBuildClearExisting(unittest.IsolatedAsyncioTestCase):
    PARTS = [{"ref": "led1", "did": 58422, "at": "9i", "pin": "anode"}]
    PLACED = {"led1": {"angle": 0, "holes": {"anode": "9i", "cathode": "9j"}}}

    async def test_clear_true_runs_separate_clear_then_waits_then_builds(self):
        svc, _, mock_page = make_service_with_clear({"placed": self.PLACED, "errors": []})
        res = await svc.build_from_holes(parts=self.PARTS, wires=[], clear_existing=True)
        self.assertTrue(res["success"])
        self.assertTrue(res["cleared"])
        self.assertTrue(res["persisted"])
        calls = mock_page.evaluate.call_args_list
        self.assertEqual(calls[0].args[0], mbs._CLEAR_JS)
        self.assertEqual(len(calls[0].args), 1)  # separate edit, no plan
        # clear + 3 pending polls + build + 3 pending polls
        self.assertEqual(len(calls), 1 + 3 + 1 + 3)
        self.assertEqual(calls[4].args[0], mbs._BUILD_JS)

    async def test_clear_true_with_nothing_to_remove_still_builds(self):
        clear = {"cleared": True, "removed_wires": 0, "removed_devices": 0,
                 "kept_uno": False, "errors": []}
        svc, _, mock_page = make_service_with_clear(
            {"placed": self.PLACED, "errors": []}, clear_return=clear)
        res = await svc.build_from_holes(parts=self.PARTS, wires=[], clear_existing=True)
        self.assertTrue(res["success"])
        self.assertTrue(res["cleared"])
        self.assertEqual(mock_page.evaluate.call_args_list[0].args[0], mbs._CLEAR_JS)

    async def test_without_clear_existing_no_clear_call_and_cleared_false(self):
        svc, _, mock_page = make_service({"placed": {}, "errors": []})
        res = await svc.build_from_holes(parts=self.PARTS, wires=[])
        self.assertFalse(res["cleared"])
        self.assertTrue(all(c.args[0] != mbs._CLEAR_JS for c in mock_page.evaluate.call_args_list))
        mock_page.evaluate.assert_called_once()

    async def test_clear_persistence_timeout_aborts_build(self):
        svc, _, mock_page = make_service_with_clear(
            {"placed": self.PLACED, "errors": []}, pending=[7] * 100)
        with patch.object(mbs, "_PERSIST_POLL_S", 0.01), patch.object(
            mbs, "_PERSIST_TIMEOUT_S", 0.05):
            res = await svc.build_from_holes(parts=self.PARTS, wires=[], clear_existing=True)
        self.assertFalse(res["success"])
        self.assertTrue(res["cleared"])
        self.assertFalse(res["persisted"])
        self.assertEqual(res["persistence_pending"], 7)
        self.assertTrue(any("clear persistence" in e for e in res["errors"]))
        self.assertTrue(all(
            not (len(c.args) >= 2) for c in mock_page.evaluate.call_args_list))

    async def test_validation_failure_with_clear_does_not_touch_page(self):
        svc, mock_bm, _ = make_service_with_clear({"placed": {}, "errors": []})
        res = await svc.build_from_holes(
            parts=[{"ref": "led1", "did": 0, "at": "9i", "pin": "anode"}],
            wires=[], clear_existing=True)
        self.assertFalse(res["success"])
        self.assertFalse(res["cleared"])
        mock_bm.get_page.assert_not_called()

    def test_clear_js_keeps_only_d13_device_and_removes_wires_and_board(self):
        js = mbs._CLEAR_JS
        self.assertIn("hasD13", js)
        self.assertIn("'d13'", js)
        self.assertIn("data.wires.remove", js)
        self.assertIn("data.devices.remove", js)
        self.assertIn("rec()", js)
        self.assertIn("stopRec", js)
        # no did-based exemption: the breadboard (111211) must not be kept
        self.assertNotIn("111211", js)
        self.assertNotIn("132521", js)

    def _run_clear_js(self, with_devices):
        import json
        import shutil
        import subprocess

        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        harness = r"""
const clearSrc = __CLEAR__;
let rec = 0, stopRec = 0, saved = 0;
function dev(termNames) {
  const content = {};
  for (const n of termNames) content[n] = { val: { pinName: n } };
  return { name2terminal: { _content: content } };
}
const uno = dev(['D13', '5V']);
const led = dev(['anode', 'cathode']);
const bb = dev(['1a']);
const devicesContent = __DEVICES__;
const wiresContent = { w1: { val: { id: 'w1' } }, w2: { val: { id: 'w2' } } };
global.window = { circuit_editor: {
  root: { rec() { rec++; }, stopRec() { stopRec++; }, save() { saved++; } },
  data: {
    devices: { _content: devicesContent,
      remove(d) { for (const [k, e] of Object.entries(devicesContent)) if ((e.val || e) === d) delete devicesContent[k]; } },
    wires: { _content: wiresContent,
      remove(w) { for (const [k, e] of Object.entries(wiresContent)) if ((e.val || e) === w) delete wiresContent[k]; } },
  },
} };
const unoRef = uno, ledRef = led, bbRef = bb;
const fn = eval('(' + clearSrc + ')');
const out = fn();
console.log(JSON.stringify({ out, rec, stopRec, saved,
  keptUno: Object.values(devicesContent).some(e => (e.val || e) === unoRef),
  keptLed: Object.values(devicesContent).some(e => (e.val || e) === ledRef),
  keptBb: Object.values(devicesContent).some(e => (e.val || e) === bbRef),
  remainingWires: Object.keys(wiresContent).length }));
"""
        devices = (
            "{ u1: { val: uno }, l1: { val: led }, b1: { val: bb } }"
            if with_devices else "{}"
        )
        # uno/led/bb must be defined before devices literal is evaluated:
        # inject them ahead of the literal via placeholders order in harness.
        script = harness.replace("__CLEAR__", json.dumps(mbs._CLEAR_JS))
        script = script.replace("__DEVICES__", devices)
        res = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=30)
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout.strip().splitlines()[-1])

    def test_clear_js_execution_keeps_uno_removes_others(self):
        out = self._run_clear_js(with_devices=True)
        self.assertTrue(out["out"]["cleared"])
        self.assertTrue(out["out"]["kept_uno"])
        self.assertEqual(out["out"]["removed_devices"], 2)
        self.assertEqual(out["out"]["removed_wires"], 2)
        self.assertTrue(out["keptUno"])
        self.assertFalse(out["keptLed"])
        self.assertFalse(out["keptBb"])
        self.assertEqual(out["remainingWires"], 0)
        self.assertEqual((out["rec"], out["stopRec"], out["saved"]), (1, 1, 1))

    def test_clear_js_execution_with_no_devices(self):
        out = self._run_clear_js(with_devices=False)
        self.assertTrue(out["out"]["cleared"])
        self.assertFalse(out["out"]["kept_uno"])
        self.assertEqual(out["out"]["removed_devices"], 0)
        self.assertEqual(out["out"]["removed_wires"], 2)

    def test_clear_js_syntax_with_node_if_available(self):
        import shutil
        import subprocess
        import tempfile

        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(mbs._CLEAR_JS)
            path = f.name
        res = subprocess.run([node, "--check", path], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)


class TestFreePartRouting(unittest.TestCase):
    FREE_REFS = ["motor1"]

    def test_free_to_hole_and_rail_routed(self):
        styled = plan_wire_style(
            [["motor1.1", "5e"], ["T-10", "motor1.2"]], free_refs=self.FREE_REFS)
        self.assertEqual([(w["route"], w["lane"]) for w in styled], [(True, 0), (True, 1)])

    def test_free_to_uno_routed_both_directions(self):
        styled = plan_wire_style(
            [["motor1.1", "uno.D9"], ["uno.GND", "motor1.2"]], free_refs=self.FREE_REFS)
        self.assertEqual([(w["route"], w["lane"]) for w in styled], [(True, 0), (True, 1)])

    def test_free_to_free_routed_but_hole_to_hole_not(self):
        """Fase 41: libre-libre se rutea; hueco-hueco sigue recto.

        Antes libre-libre tampoco se ruteaba y Tinkercad dibujaba la recta
        entre los dos pines: con los pines en filas distintas eso es una
        diagonal larga (555 -> compuerta) y el circuito se ve torcido. Los
        saltos cortos entre huecos de la misma placa se dejan rectos: son
        puentes sobre el plastico, no cables del circuito.
        """
        styled = plan_wire_style(
            [["motor1.1", "bat1.+"], ["5e", "6e"]], free_refs=["motor1", "bat1"])
        self.assertEqual([(w["route"], w["lane"]) for w in styled], [(True, 0), (False, -1)])

    def test_board_part_terminal_still_not_routed_without_free(self):
        styled = plan_wire_style([["led1.anode", "5e"], ["motor1.1", "5e"]])
        self.assertEqual([w["route"] for w in styled], [False, False])

    def test_lanes_shared_with_uno_routes_in_arrival_order(self):
        styled = plan_wire_style(
            [["uno.D13", "5i"], ["motor1.1", "6e"], ["uno.D2", "7e"]],
            free_refs=self.FREE_REFS)
        self.assertEqual([w["lane"] for w in styled], [0, 1, 2])

    def test_build_js_free_route_branch(self):
        js = mbs._BUILD_JS
        self.assertIn("isFreeEp", js)
        self.assertIn("free_pos_null", js)
        self.assertIn("pFree", js)
        # Fase 36: la cadena agrega el punto de escape lateral (pEscape) para
        # las partes cuyas terminales miran arriba; sin escape la lista queda
        # igual que antes.
        self.assertIn(
            "freeIsFrom ? chain : chain.slice().reverse()", js)
        self.assertIn("const chain = (pEscape ? [pEscape] : []).concat([pFree, pDestFree])", js)
        # El lado lo decide el hueco/parte libre respecto de la placa base
        # (BASE_Y = boards[0].y), no un ORIGIN fijo: hay varias placas.
        self.assertIn("const below = sideY > BASE_Y;", js)

    def _run_free_route(self, free_y, wire, did=999, ref="motor1",
                        free_x=560, lcd_pin=(1080, -295)):
        import json
        import shutil
        import subprocess

        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        harness = r"""
const src = __SRC__;
class Pt { constructor(x, y) { this.x = x; this.y = y; } }
const wiresMade = [];
class Wire {
  constructor(root, a, b, opts) { this.a = a; this.b = b; this.opts = opts; this.points = []; wiresMade.push(this); }
  addPoint(p, i) { this.points.push({ x: p.x, y: p.y, i }); return true; }
  updateNets() {}
}
function term(x, y, desc) {
  const t = { getBreadboardPos() { return new Pt(x, y); } };
  if (desc) t.bbDesc = desc;
  return t;
}
const bbTerm5e = term(765, 15, { x: -105, y: 15 });
const bbDev = {
  did: () => 111211,
  breadboard: () => ({ setPos() {}, setAngle() {}, pos: () => new Pt(870, 0) }),
  bbid2terminal: { _content: { t5e: { val: bbTerm5e } } },
  name2terminal: { _content: {} },
};
const unoDev = {
  did: () => 132521,
  breadboard: () => ({ setPos() {}, setAngle() {}, pos: () => new Pt(200, 0) }),
  name2terminal: { _content: { D13: { val: term(200, -50) }, D9: { val: term(200, -40) } } },
};
let motorPos = { x: 0, y: 0 };
const motorDev = {
  did: () => 999,
  breadboard: () => ({
    setPos(p) { motorPos = { x: p.x, y: p.y }; },
    setAngle() {},
    pos: () => new Pt(motorPos.x, motorPos.y),
  }),
  name2terminal: { _content: {
    '1': { val: { getBreadboardPos() { return new Pt(motorPos.x, motorPos.y); } } },
  } },
};
let lcdPos = { x: 0, y: 0 };
const lcdDev = {
  did: () => 113878,
  breadboard: () => ({
    setPos(p) { lcdPos = { x: p.x, y: p.y }; },
    setAngle() {},
    pos: () => new Pt(lcdPos.x, lcdPos.y),
  }),
  name2terminal: { _content: {
    DB5: { val: { getBreadboardPos() { return new Pt(__LCD_PIN_X__, __LCD_PIN_Y__); } } },
  } },
};
const data = {
  devices: { _content: {}, add(d) { this._content['d' + Object.keys(this._content).length] = { val: d }; } },
  wires: { _content: {}, add(w) { this._content['w' + Object.keys(this._content).length] = { val: w }; } },
  createDeviceInstance(did) {
    if (did === 132521) return unoDev;
    if (did === 111211) return bbDev;
    if (did === 113878) return lcdDev;
    return motorDev;
  },
};
global.window = {
  circuit_editor: { data, root: { rec() {}, stopRec() {}, save() {} } },
  Circuits: { BendableWireData: Wire },
};
const fn = eval('(' + src + ')');
const plan = {
  parts: [{ ref: __REF__, did: __DID__, free: { x: __FREE_X__, y: __FREE_Y__ } }],
  wires: [__WIRE__],
  code: null,
};
const out = fn(plan);
console.log(JSON.stringify({ out,
  points: wiresMade.length ? wiresMade[0].points : null }));
"""
        script = (
            harness.replace("__SRC__", json.dumps(mbs._BUILD_JS))
            .replace("__FREE_X__", json.dumps(free_x))
            .replace("__FREE_Y__", json.dumps(free_y))
            .replace("__DID__", json.dumps(did))
            .replace("__REF__", json.dumps(ref))
            .replace("__LCD_PIN_X__", json.dumps(lcd_pin[0]))
            .replace("__LCD_PIN_Y__", json.dumps(lcd_pin[1]))
            .replace("__WIRE__", json.dumps(wire))
        )
        res = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=30)
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout.strip().splitlines()[-1])

    def test_free_to_hole_below_board_produces_lane_points(self):
        out = self._run_free_route(
            300, {"from": "motor1.1", "to": "5e", "color": "blue", "route": True, "lane": 0})
        self.assertEqual(out["out"]["routed"], 1)
        self.assertEqual(out["out"]["route_debug"],
                         [{"wire": "motor1.1 -> 5e", "routed": True, "reason": "ok",
                           "points": [[560, 300], [560, 130], [765, 130], [765, 15]]}])
        # free (560,300) is below the board and beyond the band: the run uses
        # the band (y=+130), which passes between the board and the part.
        self.assertEqual(out["points"],
                         [{"x": 560, "y": 130, "i": 1}, {"x": 765, "y": 130, "i": 2}])

    def test_free_to_uno_above_board_produces_lane_points_reversed(self):
        out = self._run_free_route(
            -300, {"from": "uno.D9", "to": "motor1.1", "color": "blue", "route": True, "lane": 1})
        self.assertEqual(out["out"]["routed"], 1)
        # above -> the band (y=-130) sits between the board body and the
        # part at -300; per-side counting ignores the global lane number,
        # which only staggers the lateral escape.
        # points follow wire direction uno->free
        self.assertEqual(out["points"],
                         [{"x": 200, "y": -130, "i": 1}, {"x": 560, "y": -130, "i": 2}])

    # ------------------------------------------------ fase 36: escape lateral

    def test_lcd_sale_de_lado_antes_de_bajar(self):
        """El LCD tiene las terminales arriba: el primer punto es lateral."""
        out = self._run_free_route(
            -230, {"from": "lcd1.DB5", "to": "5e", "color": "blue", "route": True, "lane": 0},
            did=113878, ref="lcd1", free_x=1100)
        self.assertEqual(out["out"]["routed"], 1)
        # escape = origen (1100) - 154; el LCD vive en y=-230, fuera de la
        # banda, asi que el carril es la banda de arriba (-130); destino x 765
        self.assertEqual(out["points"], [
            {"x": 946, "y": -295, "i": 1},
            {"x": 946, "y": -130, "i": 2},
            {"x": 765, "y": -130, "i": 3},
        ])

    def test_el_escape_se_escalona_por_carril(self):
        out = self._run_free_route(
            -230, {"from": "lcd1.DB5", "to": "5e", "color": "blue", "route": True, "lane": 3},
            did=113878, ref="lcd1", free_x=1100)
        # 154 + 3*8 a la izquierda del origen; el y es el primer carril de la
        # banda de arriba (-130), porque cada banda cuenta por su lado.
        self.assertEqual(out["points"], [
            {"x": 922, "y": -295, "i": 1},
            {"x": 922, "y": -130, "i": 2},
            {"x": 765, "y": -130, "i": 3},
        ])

    def test_parte_libre_casi_sobre_el_borde_no_lleva_el_cable_a_la_placa(self):
        """El piezo de lcd-distancia vive en y=76: el carril no puede ir a 106.

        Correr el carril 30 mas alla de la parte lo metia dentro del cuerpo
        de la placa (y=106 < 110). El tramo tiene que limpiar las dos: baja
        a la banda (+130) y sube al pin desde afuera.
        """
        out = self._run_free_route(
            76, {"from": "buzzer1.1", "to": "uno.D13", "color": "black", "route": True, "lane": 0},
            did=999, ref="buzzer1", free_x=1250)
        self.assertEqual(out["points"], [
            {"x": 1250, "y": 130, "i": 1},
            {"x": 200, "y": 130, "i": 2},
        ])

    def test_parte_libre_dentro_de_la_banda_corre_el_carril(self):
        """Si la parte cae en la banda, el cable pasa por fuera, no por encima.

        A -120 la banda (-130) le pasaria por el cuerpo; el carril se corre
        30 mas alla (LANE_CLEAR) para salir por arriba.
        """
        out = self._run_free_route(
            -120, {"from": "motor1.1", "to": "5e", "color": "blue", "route": True, "lane": 0},
            did=999, ref="motor1", free_x=560)
        self.assertEqual(out["points"], [
            {"x": 560, "y": -150, "i": 1},
            {"x": 765, "y": -150, "i": 2},
        ])

    def test_sin_escape_el_cable_baja_directo_desde_el_pin(self):
        out = self._run_free_route(
            -230, {"from": "motor1.1", "to": "5e", "color": "blue", "route": True, "lane": 0},
            did=999, ref="motor1", free_x=560)
        # Sin tabla de escape: solo los dos puntos de carril, sin lateral.
        self.assertEqual(out["points"], [
            {"x": 560, "y": -130, "i": 1},
            {"x": 765, "y": -130, "i": 2},
        ])


class TestFreeFreeRouting(unittest.TestCase):
    """Fase 41: cable entre dos partes libres, ruteado en Z.

    Sin esto el puente no tocaba el cable y Tinkercad dibujaba la recta entre
    los dos pines. Con los pines en filas distintas (555 en -215, compuerta
    en -245) la recta es una diagonal larga y el circuito se ve torcido.
    """

    def _run(self, parts, wire):
        import json
        import shutil
        import subprocess

        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        harness = r"""
const src = __SRC__;
class Pt { constructor(x, y) { this.x = x; this.y = y; } }
const wiresMade = [];
class Wire {
  constructor(root, a, b, opts) { this.a = a; this.b = b; this.points = []; wiresMade.push(this); }
  addPoint(p, i) { this.points.push({ x: p.x, y: p.y, i }); return true; }
  updateNets() {}
}
const PIN_SETS = __PINS__;
let callIdx = 0;
function makePart(pins, did) {
  const pos = { x: 0, y: 0 };
  const content = {};
  for (const [k, xy] of Object.entries(pins)) {
    content[k] = { val: { getBreadboardPos() { return new Pt(xy[0], xy[1]); } } };
  }
  return {
    did: () => did,
    breadboard: () => ({
      setPos(p) { pos.x = p.x; pos.y = p.y; },
      setAngle() {},
      pos: () => new Pt(pos.x, pos.y),
    }),
    setName() {},
    getName() { return 'x'; },
    name2terminal: { _content: content },
  };
}
const bbDev = {
  did: () => 111211,
  breadboard: () => ({ setPos() {}, setAngle() {}, pos: () => new Pt(870, 0) }),
  bbid2terminal: { _content: {} },
  name2terminal: { _content: {} },
};
const unoDev = {
  did: () => 132521,
  breadboard: () => ({ setPos() {}, setAngle() {}, pos: () => new Pt(200, 0) }),
  name2terminal: { _content: {} },
};
const data = {
  devices: { _content: {}, add() {} },
  wires: { _content: {}, add() {} },
  createDeviceInstance(did) {
    if (did === 111211) return bbDev;
    if (did === 132521) return unoDev;
    return makePart(PIN_SETS[callIdx++] || {}, __DIDS__[callIdx - 1] || 999);
  },
};
global.window = {
  circuit_editor: { data, root: { rec() {}, stopRec() {}, save() {} } },
  Circuits: { BendableWireData: Wire },
};
const fn = eval('(' + src + ')');
const plan = { parts: __PARTS__, wires: [__WIRE__], code: null };
const out = fn(plan);
console.log(JSON.stringify({ out, points: wiresMade.length ? wiresMade[0].points : null }));
"""
        script = (
            harness.replace("__SRC__", json.dumps(mbs._BUILD_JS))
            .replace("__PINS__", json.dumps([p["pins"] for p in parts]))
            .replace("__DIDS__", json.dumps([p.get("did", 999) for p in parts]))
            .replace("__PARTS__", json.dumps([
                {"ref": p["ref"], "did": p.get("did", 999), "free": p["free"]}
                for p in parts
            ]))
            .replace("__WIRE__", json.dumps(wire))
        )
        res = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=30)
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout.strip().splitlines()[-1])

    def test_dos_partes_libres_en_filas_distintas_se_rutean_en_z(self):
        out = self._run([
            {"ref": "t1", "free": {"x": 560, "y": -230}, "pins": {"OUT": [580, -215]}},
            {"ref": "u1", "free": {"x": 760, "y": -230}, "pins": {"1A": [740, -245]}},
        ], {"from": "t1.OUT", "to": "u1.1A", "color": "blue", "route": True, "lane": 0})
        self.assertEqual(out["out"]["errors"], [])
        # El quiebre va en la columna del medio (entre los dos cuerpos) y el
        # cable entra a cada pin por su propia fila: nada de diagonales.
        self.assertEqual(out["out"]["route_debug"], [{
            "wire": "t1.OUT -> u1.1A", "routed": True, "reason": "ok",
            "points": [[580, -215], [660, -215], [660, -245], [740, -245]],
        }])
        self.assertEqual(out["points"],
                         [{"x": 660, "y": -215, "i": 1}, {"x": 660, "y": -245, "i": 2}])

    def test_misma_parte_sale_por_el_lado_del_cuerpo(self):
        """Dos pines del mismo integrado: el quiebre va fuera del cuerpo."""
        out = self._run([
            {"ref": "u1", "free": {"x": 760, "y": -230},
             "pins": {"3Y": [780, -245], "4A": [770, -215]}},
        ], {"from": "u1.3Y", "to": "u1.4A", "color": "blue", "route": True, "lane": 0})
        self.assertEqual(out["out"]["errors"], [])
        # 760 (origen) - 70: la vertical corre a la izquierda del integrado.
        self.assertEqual(out["out"]["route_debug"], [{
            "wire": "u1.3Y -> u1.4A", "routed": True, "reason": "ok",
            "points": [[780, -245], [690, -245], [690, -215], [770, -215]],
        }])

    def test_una_parte_ancha_usa_su_escape_declarado(self):
        """El LCD mide ~250 de ancho: 70 no alcanza, se usa FREE_ESCAPE (-154)."""
        out = self._run([
            {"ref": "lcd1", "did": 113878, "free": {"x": 1100, "y": -230},
             "pins": {"RS": [1010, -215], "E": [1000, -245]}},
        ], {"from": "lcd1.RS", "to": "lcd1.E", "color": "blue", "route": True, "lane": 0})
        self.assertEqual(out["out"]["errors"], [])
        self.assertEqual(out["out"]["route_debug"], [{
            "wire": "lcd1.RS -> lcd1.E", "routed": True, "reason": "ok",
            "points": [[1010, -215], [946, -215], [946, -245], [1000, -245]],
        }])

    def test_misma_fila_no_agrega_quiebre(self):
        out = self._run([
            {"ref": "t1", "free": {"x": 560, "y": -230}, "pins": {"OUT": [580, -215]}},
            {"ref": "u1", "free": {"x": 760, "y": -230}, "pins": {"1A": [740, -215]}},
        ], {"from": "t1.OUT", "to": "u1.1A", "color": "blue", "route": True, "lane": 0})
        self.assertEqual(out["out"]["errors"], [])
        # Ya era ortogonal: se deja recto y se guarda la polilinea para que el
        # cerebro pueda medirla (sin quiebres duplicados).
        self.assertEqual(out["out"]["route_debug"], [{
            "wire": "t1.OUT -> u1.1A", "routed": True, "reason": "ok",
            "points": [[580, -215], [740, -215]],
        }])
        self.assertEqual(out["points"], [])


class TestEditorReady(unittest.IsolatedAsyncioTestCase):
    """El build no puede evaluarse antes de que el editor exista.

    En la regresion de las 28 fixtures, `buzzer-activo` fallo 1 de 28 con
    `circuit_editor not available`: el JS corrio cuando la pagina todavia no
    habia montado el editor. El circuito ya estaba bien (100% de fidelidad,
    serial correcto) y el build se reportaba como fallido igual: un fallo
    intermitente que ensucia el benchmark.
    """

    PARTS = [{"ref": "led1", "did": 58422, "at": "9i", "pin": "anode"}]
    GUARD = {"success": False, "placed": {}, "errors": ["circuit_editor not available"],
             "persisted": False, "routed": 0, "route_debug": []}
    GOOD = {"success": True, "placed": {}, "errors": [], "persisted": True,
            "routed": 1, "route_debug": []}

    def _svc(self, results, clear_return=None):
        mock_bm = MagicMock()
        mock_page = AsyncMock()
        builds = iter(results)
        clear = clear_return if clear_return is not None else {
            "cleared": True, "removed_wires": 0, "removed_devices": 0,
            "kept_uno": True, "errors": [],
        }

        def _evaluate(*args, **kwargs):
            js = args[0] if args else ""
            if isinstance(js, str) and "removed_devices" in js:
                return clear
            if len(args) >= 2 or "plan" in kwargs:
                return next(builds)
            return 0

        mock_page.evaluate = AsyncMock(side_effect=_evaluate)
        mock_page.wait_for_function = AsyncMock(return_value=None)
        mock_bm.get_page = AsyncMock(return_value=mock_page)
        return ModelBuildService(mock_bm), mock_page

    async def test_espera_al_editor_antes_de_construir(self):
        svc, page = self._svc([self.GOOD])
        await svc.build_from_holes(parts=self.PARTS, wires=[])
        page.wait_for_function.assert_awaited()
        expr = page.wait_for_function.await_args.args[0]
        self.assertIn("circuit_editor", expr)

    async def test_si_el_editor_no_estaba_se_reintenta_una_vez(self):
        svc, page = self._svc([self.GUARD, self.GOOD])
        res = await svc.build_from_holes(parts=self.PARTS, wires=[])
        self.assertTrue(res["success"], res["errors"])
        self.assertEqual(res["errors"], [])
        self.assertEqual(page.wait_for_function.await_count, 2)

    async def test_dos_guardas_seguidas_se_reportan_como_fallo(self):
        """Reintentar una vez, no en bucle: si sigue sin editor, se informa."""
        svc, page = self._svc([self.GUARD, self.GUARD])
        res = await svc.build_from_holes(parts=self.PARTS, wires=[])
        self.assertFalse(res["success"])
        self.assertIn("circuit_editor not available", res["errors"])

    async def test_un_error_que_no_es_del_editor_no_se_reintenta(self):
        svc, page = self._svc([{**self.GOOD, "success": False, "errors": ["hole 99z not found"]}])
        res = await svc.build_from_holes(parts=self.PARTS, wires=[])
        self.assertFalse(res["success"])
        self.assertEqual(page.wait_for_function.await_count, 1)

    async def test_la_limpieza_tambien_espera_al_editor(self):
        """Borrar antes de que exista el editor dejaria el circuito a medias."""
        svc, page = self._svc([self.GOOD])
        await svc.build_from_holes(parts=self.PARTS, wires=[], clear_existing=True)
        # Una espera antes de limpiar y otra antes de construir.
        self.assertGreaterEqual(page.wait_for_function.await_count, 2)
        first_evaluate = page.evaluate.await_args_list[0].args[0]
        self.assertIn("removed_devices", first_evaluate)

    async def test_si_la_limpieza_cae_en_la_guarda_se_reintenta(self):
        """Limpiar dos veces es idempotente: la guarda corta antes de tocar."""
        guard_clear = {"cleared": False, "removed_wires": 0, "removed_devices": 0,
                       "kept_uno": False, "errors": ["circuit_editor not available"]}
        ok_clear = {"cleared": True, "removed_wires": 2, "removed_devices": 1,
                    "kept_uno": True, "errors": []}
        svc, page = self._svc([self.GOOD])
        calls = {"n": 0}

        def _evaluate(*args, **kwargs):
            js = args[0] if args else ""
            if isinstance(js, str) and "removed_devices" in js:
                calls["n"] += 1
                return guard_clear if calls["n"] == 1 else ok_clear
            if len(args) >= 2 or "plan" in kwargs:
                return self.GOOD
            return 0

        page.evaluate = AsyncMock(side_effect=_evaluate)
        res = await svc.build_from_holes(parts=self.PARTS, wires=[], clear_existing=True)
        self.assertEqual(calls["n"], 2)
        self.assertTrue(res["cleared"])
        self.assertTrue(res["success"], res["errors"])


class TestMultiBoardValidation(unittest.IsolatedAsyncioTestCase):
    async def test_plan_carries_boards_and_single_board_default(self):
        # Cada placa viaja con su `did`: la geometria (columnas y rieles)
        # depende de la placa, y el JS no puede adivinarla por la posicion.
        # Sin `did` explicito el plan dice Small (111211).
        svc, _, page = make_service(evaluate_return={"placed": {}, "errors": []})
        await svc.build_from_holes(
            parts=[], wires=[],
            boards=[{"x": 870, "y": 0}, {"x": 1270, "y": 40}])
        plan = page.evaluate.await_args_list[-1].args[1]
        self.assertEqual(plan["boards"],
                         [{"x": 870.0, "y": 0.0, "did": 111211},
                          {"x": 1270.0, "y": 40.0, "did": 111211}])

        svc, _, page = make_service(evaluate_return={"placed": {}, "errors": []})
        await svc.build_from_holes(parts=[], wires=[])
        plan = page.evaluate.await_args_list[-1].args[1]
        self.assertEqual(plan["boards"], [{"x": 870.0, "y": 0.0, "did": 111211}])

    async def test_la_placa_grande_viaja_con_su_did(self):
        svc, _, page = make_service(evaluate_return={"placed": {}, "errors": []})
        await svc.build_from_holes(
            parts=[], wires=[], boards=[{"x": 870, "y": 0, "did": 116648}])
        plan = page.evaluate.await_args_list[-1].args[1]
        self.assertEqual(plan["boards"], [{"x": 870.0, "y": 0.0, "did": 116648}])

    async def test_un_did_de_placa_desconocido_no_toca_la_pagina(self):
        svc, _, page = make_service()
        res = await svc.build_from_holes(
            parts=[], wires=[], boards=[{"x": 870, "y": 0, "did": 123456}])
        self.assertFalse(res["success"])
        self.assertTrue(any("did" in e for e in res["errors"]), res["errors"])
        self.assertFalse(page.evaluate.await_count)

    async def test_board_limit_rejects_before_touching_page(self):
        svc, _, page = make_service()
        res = await svc.build_from_holes(
            parts=[], wires=[],
            boards=[{"x": 870 + 400 * i, "y": 0} for i in range(4)])
        self.assertFalse(res["success"])
        self.assertTrue(any(str(mbs._MAX_BOARDS) in e for e in res["errors"]))
        page.evaluate.assert_not_awaited()

    async def test_board_entry_validation(self):
        svc, _, page = make_service()
        for bad in ({"x": "870", "y": 0}, {"x": 870}, 870):
            res = await svc.build_from_holes(parts=[], wires=[], boards=[bad])
            self.assertFalse(res["success"], bad)
            self.assertTrue(any("'x' and 'y' must be numbers" in e for e in res["errors"]))
        page.evaluate.assert_not_awaited()

    async def test_part_board_must_be_declared_and_int(self):
        svc, _, page = make_service()
        cases = [
            ([{"ref": "r1", "did": 53184, "at": "b1/5g", "board": 2}], "has no entry in boards"),
            ([{"ref": "r1", "did": 53184, "at": "b1/5g", "board": "1"}], "'board' must be int"),
            ([{"ref": "r1", "did": 53184, "at": "b1/5g", "board": -1}], "'board' must be int"),
        ]
        for parts, expected in cases:
            res = await svc.build_from_holes(
                parts=parts, wires=[], boards=[{"x": 870, "y": 0}, {"x": 1270, "y": 0}])
            self.assertFalse(res["success"], parts)
            self.assertTrue(any(expected in e for e in res["errors"]), res["errors"])
        page.evaluate.assert_not_awaited()

    async def test_hole_prefix_must_match_part_board(self):
        svc, _, page = make_service()
        boards = [{"x": 870, "y": 0}, {"x": 1270, "y": 0}]
        for part in (
            {"ref": "r1", "did": 53184, "at": "b1/5g"},                 # board omitted
            {"ref": "r1", "did": 53184, "at": "5g", "board": 1},        # prefix omitted
            {"ref": "r1", "did": 53184, "at": "b1/5g", "board": 0},
        ):
            res = await svc.build_from_holes(parts=[part], wires=[], boards=boards)
            self.assertFalse(res["success"], part)
            self.assertTrue(any("belongs to board" in e for e in res["errors"]), res["errors"])
        page.evaluate.assert_not_awaited()

    async def test_prefixed_hole_accepted_with_matching_board(self):
        svc, _, page = make_service(evaluate_return={"placed": {}, "errors": []})
        res = await svc.build_from_holes(
            parts=[{"ref": "r1", "did": 53184, "at": "b1/5g", "board": 1}],
            wires=[], boards=[{"x": 870, "y": 0}, {"x": 1270, "y": 0}])
        self.assertTrue(res["success"], res["errors"])
        plan = page.evaluate.await_args_list[-1].args[1]
        self.assertEqual(plan["parts"][0]["board"], 1)

    async def test_placed_devuelve_el_nombre_real_que_dejo_el_editor(self):
        """Tinkercad deduplica: pedir "r2" con otro "r2" deja "r21".

        El build lee el nombre despues de asignarlo y lo devuelve en
        ``placed[ref].name``; el cerebro usa ese mapa como identidad porque
        el nombre ya no se puede suponer igual a la ref.
        """
        svc, _, _ = make_service(evaluate_return={
            "placed": {"r2": {"angle": 0, "holes": {}, "name": "r21"}},
            "errors": [],
        })
        res = await svc.build_from_holes(
            parts=[{"ref": "r2", "did": 53184, "at": "9d", "pin": "1"}],
            wires=[])
        self.assertTrue(res["success"], res["errors"])
        self.assertEqual(res["placed"]["r2"]["name"], "r21")

    def test_build_js_lee_el_nombre_despues_de_asignarlo(self):
        js = mbs._BUILD_JS
        self.assertIn("const readName = (dev, fallback) =>", js)
        self.assertGreaterEqual(js.count("name: readName(dev, part.ref)"), 2)
        # setName se llama antes de leer: si el editor lo cambia, se reporta
        # el que quedo, no el que se pidio.
        self.assertLess(js.index("dev.setName(part.ref)"),
                        js.index("name: readName(dev, part.ref)"))

    def test_build_js_resolves_board_prefixes_and_names_parts(self):
        js = mbs._BUILD_JS
        self.assertIn("const bbDevFor = (board) =>", js)
        self.assertIn("boardOrigin(", js)
        self.assertIn("hole board mismatch", js)
        self.assertIn("b([1-9])", js)  # "bN/5g" prefix in parseHole
        # Con 8 resistencias, "Resistor" es ambiguo para set_component_property:
        # cada parte lleva el nombre de su ref.
        self.assertGreaterEqual(js.count("dev.setName(part.ref)"), 2)


class TestTwoBoardRouting(unittest.TestCase):
    HARNESS = r"""
const src = __SRC__;
class Pt { constructor(x, y) { this.x = x; this.y = y; } }
const wiresMade = [];
class Wire {
  constructor(root, a, b, opts) { this.a = a; this.b = b; this.points = []; wiresMade.push(this); }
  addPoint(p, i) { this.points.push({ x: p.x, y: p.y, i }); return true; }
  updateNets() {}
}
function mkBb(x, y) {
  let pos = new Pt(x, y);
  const term = (dx, dy) => ({ val: {
    getBreadboardPos() { return new Pt(pos.x + dx, pos.y + dy); },
    bbDesc: { x: dx, y: dy },
  } });
  return {
    did: () => 111211,
    breadboard: () => ({
      setPos(p) { pos = new Pt(p.x, p.y); },
      setAngle() {},
      pos: () => pos,
    }),
    bbid2terminal: { _content: {
      '5e': term(-105, 15),
      '5g': term(-105, -25),
      '10g': term(-55, -25),
      'T+10': term(-55, -85),
    } },
    name2terminal: { _content: {} },
  };
}
const unoDev = {
  did: () => 132521,
  breadboard: () => ({ setPos() {}, setAngle() {}, pos: () => new Pt(200, 0) }),
  name2terminal: { _content: { D13: { val: { getBreadboardPos() { return new Pt(200, -50); } } } } },
};
const frame = [mkBb(870, 0), mkBb(1270, 0)];
let nextBoard = 0;
const data = {
  devices: { _content: {}, add(d) { this._content['d' + Object.keys(this._content).length] = { val: d }; } },
  wires: { _content: {}, add(w) { this._content['w' + Object.keys(this._content).length] = { val: w }; } },
  createDeviceInstance(did) {
    if (did === 132521) return unoDev;
    return frame[nextBoard++];
  },
};
global.window = {
  circuit_editor: { data, root: { rec() {}, stopRec() {}, save() {} } },
  Circuits: { BendableWireData: Wire },
};
const fn = eval('(' + src + ')');
const plan = __PLAN__;
const out = fn(plan);
console.log(JSON.stringify({ out,
  points: wiresMade.length ? wiresMade[0].points : null,
  all: wiresMade.map((w) => w.points) }));
"""

    def _run(self, plan):
        import json
        import shutil
        import subprocess

        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        script = self.HARNESS.replace("__SRC__", json.dumps(mbs._BUILD_JS)).replace(
            "__PLAN__", json.dumps(plan))
        res = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=30)
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout.strip().splitlines()[-1])

    def test_wire_to_b1_hole_lands_on_second_board(self):
        out = self._run({
            "boards": [{"x": 870, "y": 0}, {"x": 1270, "y": 0}],
            "parts": [],
            "wires": [{"from": "uno.D13", "to": "b1/5e", "color": "blue",
                       "route": True, "lane": 0}],
            "code": None,
        })
        self.assertEqual(out["out"]["routed"], 1, out["out"]["errors"])
        # board 2 origin x=1270, column 5 -> 1270-145+40 = 1165; row e below
        # the gap -> bottom band y=+130 (clears the 110-wide board body)
        self.assertEqual(out["points"],
                         [{"x": 200, "y": 130, "i": 1}, {"x": 1165, "y": 130, "i": 2}])

    def test_top_band_rails_with_prefix_keep_top_lane(self):
        out = self._run({
            "boards": [{"x": 870, "y": 0}, {"x": 1270, "y": 0}],
            "parts": [],
            "wires": [{"from": "uno.D13", "to": "b1/T+10", "color": "red",
                       "route": True, "lane": 0}],
            "code": None,
        })
        self.assertEqual(out["out"]["routed"], 1, out["out"]["errors"])
        # rail T+ of board 2: x=1270-145+90=1215, y=-85; upper rail -> top band
        self.assertEqual(out["points"],
                         [{"x": 200, "y": -130, "i": 1}, {"x": 1215, "y": -130, "i": 2}])

    def test_bn_rail_no_comparte_banda_con_hueco(self):
        """Arriba y abajo crecen por separado: 2 cables arriba no empujan abajo."""
        out = self._run({
            "boards": [{"x": 870, "y": 0}, {"x": 1270, "y": 0}],
            "parts": [],
            "wires": [
                {"from": "uno.D13", "to": "b1/5g", "color": "blue", "route": True, "lane": 0},
                {"from": "uno.D13", "to": "b1/10g", "color": "green", "route": True, "lane": 1},
                {"from": "uno.D13", "to": "b1/5e", "color": "orange", "route": True, "lane": 2},
            ],
            "code": None,
        })
        self.assertEqual(out["out"]["routed"], 3, out["out"]["errors"])
        ys = [w[0]["y"] for w in out["all"]]
        # dos en la banda de arriba (-130, -138) y uno abajo (+130)
        self.assertEqual(ys, [-130, -138, 130])


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

    def test_tool_exposes_clear_existing_default_false(self):
        import inspect

        from src.server import server

        tool = next(
            t
            for t in server._tool_manager.list_tools()
            if t.name == "tinkercad_build_circuit_model"
        )
        self.assertIn("clear_existing", tool.parameters["properties"])
        param = inspect.signature(tool.fn).parameters["clear_existing"]
        self.assertEqual(param.default, False)


if __name__ == "__main__":
    unittest.main()
