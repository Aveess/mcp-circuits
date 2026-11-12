"""Direct model build service: place parts by breadboard holes via page.evaluate.

Unlike the SVG-click wiring path, this manipulates the editor's internal
model (netchuu technique): createDeviceInstance, breadboard setPos/setAngle,
and "insert" BendableWireData so each leg registers in its breadboard hole.
"""

from __future__ import annotations

import asyncio
import math
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from ..browser.browser_manager import BrowserManager
from ..config import logger

UNO_DID = 132521
BREADBOARD_DID = 111211

# ShareJS persistence polling (see ModelBuildService.build_from_holes).
_PERSIST_TIMEOUT_S = 30.0
_PERSIST_POLL_S = 0.3
_PERSIST_REQUIRED_ZEROS = 3

# Returns pending ShareJS ops; 0 when shareJsDoc/numberPending is unavailable
# (nothing can be pending through that doc in that case).
_PENDING_JS = r"""
() => {
  try {
    const doc = window.circuit_editor?.root?.shareJsDoc;
    if (!doc || typeof doc.numberPending !== 'function') return 0;
    const n = doc.numberPending();
    return (typeof n === 'number' && isFinite(n)) ? n : 0;
  } catch (e) { return 0; }
}
"""

_HOLE_RE = re.compile(r"^(?:[1-9]|[12][0-9]|30)[a-jA-J]$")
_RAIL_RE = re.compile(r"^[TBtb][+-](?:[1-9]|[12][0-9]|30)$")

# Rotating palette for signal wires (power/ground use black/red instead).
_WIRE_PALETTE = ["blue", "green", "orange", "yellow", "purple", "turquoise", "pink", "brown"]


def _norm_token(s: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def _is_uno_endpoint(ep: str) -> bool:
    if "." not in ep:
        return False
    return _norm_token(ep.split(".", 1)[0]) == "uno"


def _is_breadboard_endpoint(ep: str) -> bool:
    s = str(ep or "").strip()
    return bool(_HOLE_RE.match(s) or _RAIL_RE.match(s))


def _convention_color(ep: str) -> Optional[str]:
    """black for GND/ground/negative rail, red for 5V/3V3/VIN/positive rail."""
    s = str(ep or "").strip()
    if _RAIL_RE.match(s):
        return "black" if "-" in s else "red"
    pin = _norm_token(s.split(".", 1)[1] if "." in s else s)
    if not pin:
        return None
    if "gnd" in pin or "tierra" in pin or "ground" in pin:
        return "black"
    if (
        "5v" in pin
        or "3v3" in pin
        or "33v" in pin
        or pin in ("vin", "vcc", "vdd")
        or pin.startswith("vin")
    ):
        return "red"
    return None


def plan_wire_style(wires: Any) -> List[Dict[str, Any]]:
    """Normalize wires to {"from", "to", "color", "route", "lane"} dicts.

    Accepts pairs ``[a, b]`` and objects ``{"from", "to", "color"}``.
    Color: explicit color wins; else GND/negative rail -> black,
    5V/3V3/VIN/positive rail -> red, else a rotating palette that never
    repeats the immediately previous wire's color. ``route`` is True only
    for Uno <-> breadboard hole/rail wires (hole<->hole stays straight);
    routed wires get distinct lanes 0, 1, 2, ... in arrival order, and
    non-routed wires get lane -1.
    """
    styled: List[Dict[str, Any]] = []
    lane = 0
    palette_idx = 0
    prev_color: Optional[str] = None
    for wire in wires or []:
        explicit: Any = None
        if isinstance(wire, dict):
            frm, to = wire.get("from", ""), wire.get("to", "")
            explicit = wire.get("color")
        elif isinstance(wire, (list, tuple)) and len(wire) >= 2:
            frm, to = wire[0], wire[1]
        else:
            frm, to = wire, ""
        frm = str(frm or "").strip()
        to = str(to or "").strip()

        if isinstance(explicit, str) and explicit.strip():
            color = explicit.strip().lower()
        else:
            conv = [_convention_color(frm), _convention_color(to)]
            if "black" in conv:
                color = "black"
            elif "red" in conv:
                color = "red"
            else:
                color = _WIRE_PALETTE[palette_idx % len(_WIRE_PALETTE)]
                if color == prev_color:
                    palette_idx += 1
                    color = _WIRE_PALETTE[palette_idx % len(_WIRE_PALETTE)]
                palette_idx += 1

        route = (_is_uno_endpoint(frm) and _is_breadboard_endpoint(to)) or (
            _is_breadboard_endpoint(frm) and _is_uno_endpoint(to)
        )
        wire_lane = lane if route else -1
        if route:
            lane += 1
        styled.append(
            {"from": frm, "to": to, "color": color, "route": route, "lane": wire_lane}
        )
        prev_color = color
    return styled

_BUILD_JS = r"""
(plan) => {
  const errors = [];
  const placed = {};
  let routed = 0;
  const ce = window.circuit_editor;
  if (!ce || !ce.data) return { placed, errors: ['circuit_editor not available'], routed };
  const data = ce.data;
  const root = ce.root;
  const ORIGIN = { x: 870, y: 0 };
  const ROW_Y = { j: -55, i: -45, h: -35, g: -25, f: -15, e: 15, d: 25, c: 35, b: 45, a: 55 };
  const RAIL_Y = { 'T-': -95, 'T+': -85, 'B-': 85, 'B+': 95 };
  const UNO_DID = 132521, BB_DID = 111211;

  const unwrap = (e) => (e && e.val !== undefined ? e.val : e);
  const devices = () => Object.entries(data.devices?._content || {})
    .map(([id, e]) => ({ id, dev: unwrap(e) }));
  const didOf = (dev) => Number(typeof dev.did === 'function' ? dev.did() : dev.did);
  const findByDid = (did) => devices().find(d => didOf(d.dev) === did) || null;
  const norm = (s) => String(s || '').toLowerCase().replace(/[^a-z0-9]/g, '');

  function ensureDevice(did) {
    const found = findByDid(did);
    if (found) return found.dev;
    const dev = data.createDeviceInstance(did);
    if (dev && data.devices && typeof data.devices.add === 'function') {
      try { data.devices.add(dev); } catch (e) {}
    }
    return dev;
  }

  function holeRel(col, row) {
    return { x: -145 + 10 * (col - 1), y: ROW_Y[row] };
  }
  function parseHole(s) {
    const m = String(s || '').trim().match(/^([1-9]|[12][0-9]|30)([a-j])$/i);
    return m ? { col: parseInt(m[1], 10), row: m[2].toLowerCase() } : null;
  }
  function holeName(col, y) {
    for (const [row, ry] of Object.entries(ROW_Y)) {
      if (Math.abs(y - ry) < 3) return '' + col + row;
    }
    for (const [rail, ry] of Object.entries(RAIL_Y)) {
      if (Math.abs(y - ry) < 3) return rail + col;
    }
    return null;
  }
  function bbTerminal(bbDev, col, y) {
    const target = holeRel(col, 'a');
    const map = bbDev?.bbid2terminal?._content || bbDev?.name2terminal?._content || {};
    for (const e of Object.values(map)) {
      const t = unwrap(e);
      const d = t?.bbDesc || t?.breadboardDescription;
      if (d && Math.abs(d.x - target.x) < 3 && Math.abs(d.y - y) < 3) return t;
    }
    return null;
  }
  function termByName(dev, pin) {
    const map = dev?.name2terminal?._content || {};
    for (const [k, e] of Object.entries(map)) {
      if (norm(k) === norm(pin)) return { name: k, term: unwrap(e) };
    }
    for (const [k, e] of Object.entries(map)) {
      const t = unwrap(e);
      if (norm(t?.pinName || t?.name || '') === norm(pin)) return { name: k, term: t };
    }
    return null;
  }
  function termOffset(t) {
    const d = t?.bbDesc || t?.breadboardDescription;
    if (d && isFinite(d.x) && isFinite(d.y)) return { x: Number(d.x), y: Number(d.y) };
    try {
      const p = typeof t?.pos === 'function' ? t.pos() : t?.pos;
      if (p && isFinite(p.x) && isFinite(p.y)) return { x: Number(p.x), y: Number(p.y) };
    } catch (e) {}
    return null;
  }
  const rot = (p, deg) => {
    const r = deg * Math.PI / 180, c = Math.cos(r), s = Math.sin(r);
    return { x: p.x * c - p.y * s, y: p.x * s + p.y * c };
  };

  let bbDev = null;
  try { if (root && typeof root.rec === 'function') root.rec(); } catch (e) {}
  try {
    const uno = ensureDevice(UNO_DID);
    bbDev = ensureDevice(BB_DID);
    try {
      const bb = bbDev.breadboard();
      if (bb && typeof bb.setPos === 'function') bb.setPos({ x: ORIGIN.x, y: ORIGIN.y });
    } catch (e) {}

    const byRef = { uno: uno };
    for (const part of (plan.parts || [])) {
      try {
        const anchor = parseHole(part.at);
        if (!anchor) { errors.push(part.ref + ': invalid hole ' + part.at); continue; }
        const dev = data.createDeviceInstance(part.did);
        if (dev && data.devices && typeof data.devices.add === 'function') {
          try { data.devices.add(dev); } catch (e) {}
        }
        byRef[part.ref] = dev;
        const bb = typeof dev.breadboard === 'function' ? dev.breadboard() : dev.breadboard;
        if (!bb || typeof bb.setPos !== 'function') {
          errors.push(part.ref + ': no breadboard placement'); continue;
        }
        const pinNames = Object.keys(dev.name2terminal?._content || {});
        const anchorEntry = termByName(dev, part.pin) || (pinNames.length ? { name: pinNames[0], term: unwrap(dev.name2terminal._content[pinNames[0]]) } : null);
        if (!anchorEntry) { errors.push(part.ref + ': no terminals'); continue; }
        const angles = (part.angle !== undefined && part.angle !== null) ? [part.angle] : [0, 90, 180, 270];
        let ok = null;
        for (const angle of angles) {
          if (typeof bb.setAngle === 'function') bb.setAngle(angle);
          const aOff = termOffset(anchorEntry.term);
          if (!aOff) break;
          const aRot = rot(aOff, angle);
          const rel = holeRel(anchor.col, anchor.row);
          const pos = { x: ORIGIN.x + rel.x - aRot.x, y: ORIGIN.y + rel.y - aRot.y };
          bb.setPos(pos);
          const holes = {};
          let all = true;
          for (const name of pinNames) {
            const t = unwrap(dev.name2terminal._content[name]);
            const off = termOffset(t);
            if (!off) { all = false; break; }
            const abs = rot(off, angle);
            const lx = pos.x + abs.x - ORIGIN.x, ly = pos.y + abs.y - ORIGIN.y;
            const col = Math.round((lx + 145) / 10) + 1;
            if (Math.abs(lx - (-145 + 10 * (col - 1))) > 3) { all = false; break; }
            const h = holeName(col, ly);
            if (!h) { all = false; break; }
            holes[name] = h;
          }
          if (all) { ok = { angle, holes }; break; }
        }
        if (!ok) { errors.push(part.ref + ': no angle fits all pins in holes'); continue; }
        // Register each leg in its breadboard hole with an insert wire.
        for (const [name, h] of Object.entries(ok.holes)) {
          const t = unwrap(dev.name2terminal._content[name]);
          const parsed = parseHole(h);
          let bt = null;
          if (parsed) bt = bbTerminal(bbDev, parsed.col, ROW_Y[parsed.row]);
          else {
            const rm = String(h).match(/^([TB][+-])(\d+)$/);
            if (rm) bt = bbTerminal(bbDev, parseInt(rm[2], 10), RAIL_Y[rm[1]]);
          }
          if (t && bt && window.Circuits?.BendableWireData) {
            const w = new window.Circuits.BendableWireData(root, t, bt, { insert: true });
            if (data.wires && typeof data.wires.add === 'function') data.wires.add(w);
            if (w && typeof w.updateNets === 'function') w.updateNets();
          }
        }
        placed[part.ref] = ok;
      } catch (e) { errors.push(part.ref + ': ' + e.toString()); }
    }

    function resolveEndpoint(ep) {
      const s = String(ep || '').trim();
      const hole = parseHole(s);
      if (hole) return bbTerminal(bbDev, hole.col, ROW_Y[hole.row]);
      const rail = s.match(/^([TB])([+-])(\d{1,2})$/i);
      if (rail) return bbTerminal(bbDev, parseInt(rail[3], 10), RAIL_Y[(rail[1].toUpperCase() + rail[2])]);
      const dot = s.indexOf('.');
      if (dot > 0) {
        const ref = s.slice(0, dot), pin = s.slice(dot + 1);
        const dev = byRef[ref] || (norm(ref) === 'uno' ? uno : null);
        if (!dev) return null;
        if (norm(ref) !== 'uno' && placed[ref]) {
          const h = placed[ref].holes[pin] || Object.entries(placed[ref].holes)
            .find(([k]) => norm(k) === norm(pin))?.[1];
          const parsed = h ? parseHole(h) : null;
          if (parsed) return bbTerminal(bbDev, parsed.col, ROW_Y[parsed.row]);
        }
        const found = termByName(dev, pin);
        return found ? found.term : null;
      }
      return null;
    }

    const WIRE_PALETTE = ['blue', 'green', 'orange', 'yellow', 'purple', 'turquoise', 'pink', 'brown'];
    function wireSpec(raw) {
      if (Array.isArray(raw)) return { from: raw[0], to: raw[1] };
      if (raw && typeof raw === 'object') return { from: raw.from, to: raw.to, color: raw.color, route: raw.route, lane: raw.lane };
      return { from: raw, to: '' };
    }
    function isUnoEp(ep) {
      const s = String(ep || '').trim(), dot = s.indexOf('.');
      return dot > 0 && norm(s.slice(0, dot)) === 'uno';
    }
    function isBbEp(ep) {
      return !!parseHole(ep) || /^[TB][+-]\d{1,2}$/i.test(String(ep || '').trim());
    }
    function convColor(ep) {
      const s = String(ep || '').trim();
      if (/^[TB][+-]\d{1,2}$/i.test(s)) return s.includes('-') ? 'black' : 'red';
      const pin = norm(s.includes('.') ? s.slice(s.indexOf('.') + 1) : s);
      if (!pin) return null;
      if (pin.includes('gnd') || pin.includes('tierra') || pin.includes('ground')) return 'black';
      if (pin.includes('5v') || pin.includes('3v3') || pin.includes('33v') || pin === 'vin' || pin === 'vcc' || pin === 'vdd' || pin.startsWith('vin')) return 'red';
      return null;
    }
    function bbAbs(ep) {
      const hole = parseHole(ep);
      if (hole) { const rel = holeRel(hole.col, hole.row); return { x: ORIGIN.x + rel.x, y: ORIGIN.y + rel.y }; }
      const rail = String(ep || '').trim().match(/^([TB])([+-])(\d{1,2})$/i);
      if (rail) return { x: ORIGIN.x - 145 + 10 * (parseInt(rail[3], 10) - 1), y: ORIGIN.y + RAIL_Y[rail[1].toUpperCase() + rail[2]] };
      return null;
    }
    function isUpperBb(ep) {
      const hole = parseHole(ep);
      if (hole) return ['j', 'i', 'h', 'g', 'f'].includes(hole.row);
      return /^T/i.test(String(ep || '').trim());
    }
    function devPos(dev) {
      try {
        const bb = typeof dev.breadboard === 'function' ? dev.breadboard() : dev.breadboard;
        const p = bb && (typeof bb.pos === 'function' ? bb.pos() : bb.pos);
        if (p && isFinite(p.x) && isFinite(p.y)) return { x: Number(p.x), y: Number(p.y) };
      } catch (e) {}
      return null;
    }
    function termAbs(dev, term) {
      const d = term?.bbDesc || term?.breadboardDescription;
      if (d && isFinite(d.x) && isFinite(d.y)) {
        const base = devPos(dev), off = { x: Number(d.x), y: Number(d.y) };
        return base ? { x: base.x + off.x, y: base.y + off.y } : off;
      }
      try {
        const p = typeof term?.pos === 'function' ? term.pos() : term?.pos;
        if (p && isFinite(p.x) && isFinite(p.y)) return { x: Number(p.x), y: Number(p.y) };
      } catch (e) {}
      return null;
    }

    let fallbackLane = 0, paletteIdx = 0, prevColor = null;
    for (const rawWire of (plan.wires || [])) {
      const spec = wireSpec(rawWire);
      const from = String(spec.from || '').trim(), to = String(spec.to || '').trim();
      try {
        let color = (typeof spec.color === 'string' && spec.color.trim()) ? spec.color.trim().toLowerCase() : null;
        if (!color) {
          const conv = [convColor(from), convColor(to)];
          if (conv.includes('black')) color = 'black';
          else if (conv.includes('red')) color = 'red';
          else {
            color = WIRE_PALETTE[paletteIdx % WIRE_PALETTE.length];
            if (color === prevColor) { paletteIdx++; color = WIRE_PALETTE[paletteIdx % WIRE_PALETTE.length]; }
            paletteIdx++;
          }
        }
        prevColor = color;
        const shouldRoute = (typeof spec.route === 'boolean') ? spec.route
          : ((isUnoEp(from) && isBbEp(to)) || (isBbEp(from) && isUnoEp(to)));
        let lane = (typeof spec.lane === 'number' && spec.lane >= 0) ? spec.lane : -1;
        if (shouldRoute) {
          if (lane < 0) lane = fallbackLane;
          fallbackLane = Math.max(fallbackLane, lane + 1);
        }
        const a = resolveEndpoint(from), b = resolveEndpoint(to);
        if (!a || !b) { errors.push('wire ' + from + ' -> ' + to + ': endpoint not resolved'); continue; }
        if (window.Circuits?.BendableWireData) {
          const w = new window.Circuits.BendableWireData(root, a, b, { color });
          if (data.wires && typeof data.wires.add === 'function') data.wires.add(w);
          let didRoute = false;
          if (shouldRoute && w && typeof w.addPoint === 'function') {
            const fromIsUno = isUnoEp(from);
            const unoPos = termAbs(uno, fromIsUno ? a : b);
            const destPos = bbAbs(fromIsUno ? to : from);
            if (unoPos && destPos) {
              const laneY = isUpperBb(fromIsUno ? to : from)
                ? ORIGIN.y - 115 - lane * 5
                : ORIGIN.y + 115 + lane * 5;
              const pUno = { x: unoPos.x, y: laneY }, pDest = { x: destPos.x, y: laneY };
              try {
                for (const pt of (fromIsUno ? [pUno, pDest] : [pDest, pUno])) w.addPoint(pt);
                didRoute = true;
              } catch (e) {}
            }
          }
          if (didRoute) routed++;
          if (w && typeof w.updateNets === 'function') w.updateNets();
        } else { errors.push('wire ' + from + ': BendableWireData unavailable'); }
      } catch (e) { errors.push('wire ' + from + ': ' + e.toString()); }
    }

    if (plan.code) {
      try {
        const props = uno?.properties?._content || {};
        for (const e of Object.values(props)) {
          const p = unwrap(e);
          if (p && (p.name === 'Code' || p.unit === 'code')) {
            if (typeof p.setValue === 'function') p.setValue(plan.code); else p.value = plan.code;
          }
        }
      } catch (e) {}
    }
  } catch (e) {
    errors.push(e.toString());
  } finally {
    try { if (root && typeof root.stopRec === 'function') root.stopRec(); } catch (e) {}
    try { if (root && typeof root.save === 'function') root.save(); } catch (e) {}
  }
  return { placed, errors, routed };
}
"""


class ModelBuildService:
    """Build circuits by holes directly in the editor's internal model."""

    def __init__(self, browser: Optional[BrowserManager] = None) -> None:
        self.browser = browser or BrowserManager.get_instance()

    async def _wait_for_persistence(self, page: Any) -> Tuple[bool, Optional[int]]:
        """Poll shareJsDoc.numberPending() until 0 x _PERSIST_REQUIRED_ZEROS.

        Returns (persisted, last_pending). last_pending is the last numeric
        value observed, or None if no poll ever returned a number (e.g. every
        poll raised); a non-numeric/raising poll resets the zero streak.
        """
        deadline = time.monotonic() + _PERSIST_TIMEOUT_S
        stable_zeros = 0
        last: Optional[int] = None
        while True:
            try:
                raw = await page.evaluate(_PENDING_JS)
            except Exception:
                raw = None
            if isinstance(raw, (int, float)) and not isinstance(raw, bool) and math.isfinite(raw):
                last = int(raw)
                stable_zeros = stable_zeros + 1 if last == 0 else 0
                if stable_zeros >= _PERSIST_REQUIRED_ZEROS:
                    return True, last
            else:
                stable_zeros = 0
            if time.monotonic() >= deadline:
                return False, last
            await asyncio.sleep(_PERSIST_POLL_S)

    async def build_from_holes(
        self,
        parts: list[dict],
        wires: list,
        code: str | None = None,
    ) -> dict:
        """Place parts so their pins land in breadboard holes, then wire endpoints.

        ``wires`` accepts pairs ``[a, b]`` and objects
        ``{"from": a, "to": b, "color": ...}``; see ``plan_wire_style``.

        Returns {"success": bool, "placed": {...}, "errors": [...],
        "persisted": bool, "routed": int} plus
        "persistence_pending": int|None on timeout.

        Persistence contract (ShareJS edits are lost if the editor reloads
        before they flush, per netchuu):
        - Validation failure / invalid JS response: no page edit happened,
          ``persisted`` is False and the page is untouched (validation only).
        - ``placed`` empty: no polling. ``persisted`` is True vacuously —
          no placed part can be lost on reload. ``success`` is
          ``not errors`` (JS errors still fail the build).
        - ``placed`` non-empty: poll ``circuit_editor.root.shareJsDoc
          .numberPending()`` (missing doc/function counts as 0 in the JS
          itself) every ~0.3s until it returns 0 three times in a row, up
          to 30s. On success ``persisted`` is True and ``success`` is
          ``not errors``. On timeout ``persisted`` is False,
          ``persistence_pending`` holds the last observed pending count
          (None if never numeric), a "persistence timeout ..." warning is
          appended to ``errors``, and ``success`` is forced False.
        """
        errors: List[str] = []
        for part in parts or []:
            if not isinstance(part, dict):
                errors.append(f"invalid part (not an object): {part!r}")
                continue
            ref = part.get("ref", "?")
            did = part.get("did")
            if type(did) is not int or did <= 0:
                errors.append(f"part '{ref}': did must be int > 0, got {did!r}")
            at = part.get("at")
            if not isinstance(at, str) or not _HOLE_RE.match(at.strip()):
                errors.append(f"part '{ref}': invalid 'at' hole {at!r} (expected 1-30 + a-j)")
            angle = part.get("angle")
            if angle is not None and angle not in (0, 90, 180, 270):
                errors.append(f"part '{ref}': angle must be one of 0/90/180/270, got {angle!r}")

        if errors:
            return {
                "success": False,
                "placed": {},
                "errors": errors,
                "persisted": False,
                "routed": 0,
            }

        page = await self.browser.get_page()
        plan: Dict[str, Any] = {
            "parts": parts or [],
            "wires": plan_wire_style(wires),
            "code": code,
        }
        result = await page.evaluate(_BUILD_JS, plan)
        if not isinstance(result, dict):
            return {
                "success": False,
                "placed": {},
                "errors": ["model build returned invalid response"],
                "persisted": False,
                "routed": 0,
            }

        js_errors = list(result.get("errors") or [])
        placed = result.get("placed") or {}
        raw_routed = result.get("routed")
        routed = (
            int(raw_routed)
            if isinstance(raw_routed, (int, float)) and not isinstance(raw_routed, bool)
            else 0
        )
        logger.info(f"Model build placed={list(placed)} errors={js_errors}")
        if not placed:
            return {
                "success": not js_errors,
                "placed": placed,
                "errors": js_errors,
                "persisted": True,
                "routed": routed,
            }

        persisted, last_pending = await self._wait_for_persistence(page)
        if persisted:
            return {
                "success": not js_errors,
                "placed": placed,
                "errors": js_errors,
                "persisted": True,
                "routed": routed,
            }
        return {
            "success": False,
            "placed": placed,
            "errors": js_errors
            + [
                "persistence timeout: shareJsDoc.numberPending() still "
                f"{last_pending} after {_PERSIST_TIMEOUT_S:g}s; "
                "placed parts may be lost on reload"
            ],
            "persisted": False,
            "persistence_pending": last_pending,
            "routed": routed,
        }
