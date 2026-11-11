"""Direct model build service: place parts by breadboard holes via page.evaluate.

Unlike the SVG-click wiring path, this manipulates the editor's internal
model (netchuu technique): createDeviceInstance, breadboard setPos/setAngle,
and "insert" BendableWireData so each leg registers in its breadboard hole.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ..browser.browser_manager import BrowserManager
from ..config import logger

UNO_DID = 132521
BREADBOARD_DID = 111211

_HOLE_RE = re.compile(r"^(?:[1-9]|[12][0-9]|30)[a-jA-J]$")

_BUILD_JS = r"""
(plan) => {
  const errors = [];
  const placed = {};
  const ce = window.circuit_editor;
  if (!ce || !ce.data) return { placed, errors: ['circuit_editor not available'] };
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

    for (const pair of (plan.wires || [])) {
      try {
        const a = resolveEndpoint(pair[0]), b = resolveEndpoint(pair[1]);
        if (!a || !b) { errors.push('wire ' + pair[0] + ' -> ' + pair[1] + ': endpoint not resolved'); continue; }
        if (window.Circuits?.BendableWireData) {
          const w = new window.Circuits.BendableWireData(root, a, b, {});
          if (data.wires && typeof data.wires.add === 'function') data.wires.add(w);
          if (w && typeof w.updateNets === 'function') w.updateNets();
        } else { errors.push('wire ' + pair[0] + ': BendableWireData unavailable'); }
      } catch (e) { errors.push('wire ' + pair[0] + ': ' + e.toString()); }
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
  return { placed, errors };
}
"""


class ModelBuildService:
    """Build circuits by holes directly in the editor's internal model."""

    def __init__(self, browser: Optional[BrowserManager] = None) -> None:
        self.browser = browser or BrowserManager.get_instance()

    async def build_from_holes(
        self,
        parts: list[dict],
        wires: list[list[str]],
        code: str | None = None,
    ) -> dict:
        """Place parts so their pins land in breadboard holes, then wire endpoints.

        Returns {"success": bool, "placed": {...}, "errors": [...]}.
        Invalid parts (bad did/at) are rejected without touching the page.
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
            return {"success": False, "placed": {}, "errors": errors}

        page = await self.browser.get_page()
        plan: Dict[str, Any] = {"parts": parts or [], "wires": wires or [], "code": code}
        result = await page.evaluate(_BUILD_JS, plan)
        if not isinstance(result, dict):
            return {"success": False, "placed": {}, "errors": ["model build returned invalid response"]}

        js_errors = list(result.get("errors") or [])
        placed = result.get("placed") or {}
        logger.info(f"Model build placed={list(placed)} errors={js_errors}")
        return {"success": not js_errors, "placed": placed, "errors": js_errors}
