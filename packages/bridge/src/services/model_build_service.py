"""Direct model build service: place parts by breadboard holes via page.evaluate.

Unlike the SVG-click wiring path, this manipulates the editor's internal
model (netchuu technique): createDeviceInstance, breadboard setPos/setAngle,
and "insert" BendableWireData so each leg registers in its breadboard hole.
"""

from __future__ import annotations

import asyncio
import json
import math
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from ..browser.browser_manager import BrowserManager
from ..config import logger
from .editor_guard import (
    EDITOR_READY_JS,
    EDITOR_READY_TIMEOUT_S,
    editor_guard_hit,
    wait_for_editor,
)
from .sharejs import (
    PENDING_JS,
    PERSIST_POLL_S,
    PERSIST_REQUIRED_ZEROS,
    PERSIST_TIMEOUT_S,
    wait_for_persistence,
)

UNO_DID = 132521
BREADBOARD_DID = 111211

# Geometria de las dos breadboards del catalogo. Medida en vivo el 2026-11-15
# (ver docs/superpowers/specs/2026-11-15-layout-v2-design.md):
#   - Small (111211): 30 columnas, x -145..145, con rieles T+/T-/B+/B-.
#   - Large (116648): 62 columnas utiles (x -295..315; el modelo nombra
#     "A98/A99" las dos extremas -315/-305 y no se usan) y SIN rieles
#     utilizables: los dos de abajo comparten nombre "X" y el mismo nodo.
# Las filas son las mismas en las dos (paso 10, a = +55 ... j = -55); la
# grande las nombra al reves (A = -55) pero el puente trabaja en y.
ROW_Y: Dict[str, int] = {
    "j": -55,
    "i": -45,
    "h": -35,
    "g": -25,
    "f": -15,
    "e": 15,
    "d": 25,
    "c": 35,
    "b": 45,
    "a": 55,
}

BOARD_KINDS: Dict[int, Dict[str, Any]] = {
    BREADBOARD_DID: {
        "columns": 30,
        "x0": -145,
        "rails": {"T-": -95, "T+": -85, "B-": 85, "B+": 95},
    },
    116648: {"columns": 62, "x0": -295, "rails": {}},
}


def board_kinds() -> Dict[int, Dict[str, Any]]:
    """Copia de la tabla: los tests no pueden mutar la geometria del build."""
    return {did: {**kind, "rails": dict(kind["rails"])} for did, kind in BOARD_KINDS.items()}


def hole_x(did: int, col: int) -> int:
    """x relativa al origen de la placa del hueco ``col`` (1-based)."""
    kind = BOARD_KINDS[did]
    return kind["x0"] + 10 * (col - 1)

# ShareJS persistence polling. El sondeo vive en sharejs.py porque tambien lo
# usa la inyeccion de codigo (un sketch largo se perdia al recargar con la
# cola sin vaciar). Se mantienen estos nombres para no romper a quien los lee
# (model_props_service y los tests que los parchean).
_PERSIST_TIMEOUT_S = PERSIST_TIMEOUT_S
_PERSIST_POLL_S = PERSIST_POLL_S
_PERSIST_REQUIRED_ZEROS = PERSIST_REQUIRED_ZEROS
_PENDING_JS = PENDING_JS

# La espera del editor vive en editor_guard para que build, limpieza y
# propiedades usen la misma senal (fase 44: props se la habia olvidado).
_EDITOR_READY_JS = EDITOR_READY_JS
_EDITOR_READY_TIMEOUT_S = EDITOR_READY_TIMEOUT_S

# Con mas de una placa el hueco lleva prefijo "bN/" (p. ej. "b1/5g"): sin el,
# "5g" no dice a que protoboard pertenece y el cable caeria en la primera.
_BOARD_PREFIX = r"(?:b[1-9]/)?"
_HOLE_RE = re.compile(rf"^{_BOARD_PREFIX}(?:[1-9]|[12][0-9]|30)[a-jA-J]$")
_RAIL_RE = re.compile(rf"^{_BOARD_PREFIX}[TBtb][+-](?:[1-9]|[12][0-9]|30)$")

# Rotating palette for signal wires (power/ground use black/red instead).
_WIRE_PALETTE = ["blue", "green", "orange", "yellow", "purple", "turquoise", "pink", "brown"]

# Tope de protoboards por circuito: mas de tres y el lienzo deja de leerse.
_MAX_BOARDS = 3

# Partes libres cuyas terminales miran hacia ARRIBA: bajar en vertical desde
# el pin atraviesa su propio cuerpo y el cable parece nacer en el borde.
# El cable sale primero de lado, `dx` unidades desde el ORIGEN del modulo
# (no desde cada pin: cada pin daria una x distinta y el abanico cruzaria a
# los vecinos), y despues baja por el carril. Medido en vivo con el LCD
# 16x2 (did 113878): su cuerpo empieza 139 unidades a la izquierda del
# origen, asi que -154 lo deja 15 afuera. Ver docs/fase0-vivo.md, fase 36.
FREE_ESCAPE: Dict[int, Dict[str, int]] = {113878: {"dx": -154}}


def _norm_token(s: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def _is_uno_endpoint(ep: str) -> bool:
    if "." not in ep:
        return False
    return _norm_token(ep.split(".", 1)[0]) == "uno"


def _is_breadboard_endpoint(ep: str) -> bool:
    s = str(ep or "").strip()
    return bool(_HOLE_RE.match(s) or _RAIL_RE.match(s))


def _is_free_endpoint(ep: str, free_norms: set) -> bool:
    if "." not in str(ep or "") or not free_norms:
        return False
    return _norm_token(str(ep).split(".", 1)[0]) in free_norms


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


def plan_wire_style(wires: Any, free_refs: Any = None) -> List[Dict[str, Any]]:
    """Normalize wires to {"from", "to", "color", "route", "lane"} dicts.

    Accepts pairs ``[a, b]`` and objects ``{"from", "to", "color"}``.
    Color: explicit color wins; else GND/negative rail -> black,
    5V/3V3/VIN/positive rail -> red, else a rotating palette that never
    repeats the immediately previous wire's color. ``route`` is True for
    Uno <-> breadboard hole/rail wires, free-part terminal <-> breadboard
    hole/rail or Uno wires, and free-part <-> free-part wires (hole<->hole
    stays straight);
    routed wires get distinct lanes 0, 1, 2, ... in arrival order, and
    non-routed wires get lane -1. ``free_refs`` holds the refs of parts
    placed with ``free`` (unknown/free-less callers keep the old routes).
    """
    free_norms = {_norm_token(r) for r in (free_refs or []) if _norm_token(r)}
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

        route = (
            (_is_uno_endpoint(frm) and _is_breadboard_endpoint(to))
            or (_is_breadboard_endpoint(frm) and _is_uno_endpoint(to))
            or (
                _is_free_endpoint(frm, free_norms)
                and (_is_breadboard_endpoint(to) or _is_uno_endpoint(to))
            )
            or (
                _is_free_endpoint(to, free_norms)
                and (_is_breadboard_endpoint(frm) or _is_uno_endpoint(frm))
            )
            # Dos partes libres (555 -> compuerta, compuerta -> capacidad):
            # sin ruteo Tinkercad dibuja la recta entre los dos pines y el
            # circuito se ve torcido. El puente decide si hace falta el
            # quiebre (pines en la misma fila ya son ortogonales).
            or (
                _is_free_endpoint(frm, free_norms)
                and _is_free_endpoint(to, free_norms)
            )
        )
        wire_lane = lane if route else -1
        if route:
            lane += 1
        styled.append(
            {"from": frm, "to": to, "color": color, "route": route, "lane": wire_lane}
        )
        prev_color = color
    return styled

_CLEAR_JS = r"""
() => {
  const errors = [];
  let removed_wires = 0;
  let removed_devices = 0;
  let kept_uno = false;
  const ce = window.circuit_editor;
  if (!ce || !ce.data) return { cleared: false, removed_wires, removed_devices, kept_uno, errors: ['circuit_editor not available'] };
  const data = ce.data;
  const root = ce.root;
  const unwrap = (e) => (e && e.val !== undefined ? e.val : e);
  const norm = (s) => String(s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  function hasD13(dev) {
    const map = dev?.name2terminal?._content || {};
    for (const [k, e] of Object.entries(map)) {
      const t = unwrap(e);
      if (norm(k) === 'd13' || norm(t?.pinName || t?.name || '') === 'd13') return true;
    }
    return false;
  }
  try { if (root && typeof root.rec === 'function') root.rec(); } catch (e) {}
  try {
    const wireEntries = Object.values(data.wires?._content || {});
    for (const entry of wireEntries) {
      const w = unwrap(entry);
      if (!w) continue;
      try {
        if (data.wires && typeof data.wires.remove === 'function') { data.wires.remove(w); removed_wires++; }
        else if (typeof w.remove === 'function') { w.remove(); removed_wires++; }
        else errors.push('wire remove unavailable');
      } catch (e) { errors.push('wire remove: ' + e.toString()); }
    }
    const devEntries = Object.entries(data.devices?._content || {})
      .map(([id, e]) => ({ id, dev: unwrap(e) }));
    for (const { dev } of devEntries) {
      if (!dev) continue;
      if (hasD13(dev)) { kept_uno = true; continue; }
      try {
        if (data.devices && typeof data.devices.remove === 'function') { data.devices.remove(dev); removed_devices++; }
        else if (typeof dev.remove === 'function') { dev.remove(); removed_devices++; }
        else errors.push('device remove unavailable');
      } catch (e) { errors.push('device remove: ' + e.toString()); }
    }
  } catch (e) {
    errors.push(e.toString());
  } finally {
    try { if (root && typeof root.stopRec === 'function') root.stopRec(); } catch (e) {}
    try { if (root && typeof root.save === 'function') root.save(); } catch (e) {}
  }
  return { cleared: errors.length === 0, removed_wires, removed_devices, kept_uno, errors };
}
"""

_BUILD_JS = r"""
(plan) => {
  const errors = [];
  const placed = {};
  const route_debug = [];
  let routed = 0;
  const ce = window.circuit_editor;
  if (!ce || !ce.data) return { placed, errors: ['circuit_editor not available'], routed, route_debug };
  const data = ce.data;
  const root = ce.root;
  const ORIGIN = { x: 870, y: 0 };
  // Geometria por placa (columnas, x del primer hueco, rieles). La inyecta
  // Python desde BOARD_KINDS: una sola tabla, probada sin navegador.
  // Small (111211): 30 columnas, x -145..145, rieles T+/T-/B+/B-.
  // Large (116648): 62 columnas utiles (x -295..315) y sin rieles usables.
  const BOARD_KINDS = __BOARD_KINDS__;
  const DEFAULT_BB_DID = 111211;
  // Placas: plan.boards = [{x, y, did}, ...]. La primera es la de siempre
  // (870, 0); una parte pide otra con "board": N y sus huecos viajan como
  // "bN/<hueco>". Todos los cables usan el y de la primera placa como
  // referencia de carril, asi que las placas se colocan a la misma altura.
  // `did` decide la geometria (30 o 62 columnas): Small 111211, Large 116648.
  const BOARDS = (Array.isArray(plan.boards) && plan.boards.length)
    ? plan.boards.map((b) => ({
        x: Number(b.x),
        y: Number(b.y),
        did: (b.did !== undefined && b.did !== null) ? Number(b.did) : DEFAULT_BB_DID,
      }))
    : [{ x: ORIGIN.x, y: ORIGIN.y, did: DEFAULT_BB_DID }];
  const boardOrigin = (index) => {
    const b = BOARDS[index];
    return (b && isFinite(b.x) && isFinite(b.y)) ? b : BOARDS[0];
  };
  // Separacion entre carriles (los cables se dibujan encima uno de otro con
  // menos de 8) y base a la que arranca la banda por encima/debajo de la
  // placa. El reparto por lado se lleva aparte: cada banda usa sus propios
  // numeros, asi que la de arriba no se come el espacio de la de abajo.
  //
  // LANE_BASE tiene que superar el cuerpo de la protoboard (filas -55..+55
  // y rieles -95..+95, plastico hasta ~110): con 115 el cable pasaba a 5
  // unidades del borde y se veia pegado a la placa. LANE_CLEAR es la
  // holgura que se le deja a una parte libre que caiga dentro de la banda.
  const LANE_BASE = 130, LANE_STEP = 8, LANE_CLEAR = 30;
  // Cable entre dos partes libres: no hay carril ni placa de por medio, asi
  // que el quiebre va en la columna del medio (o al lado del cuerpo cuando
  // las dos terminales son de la misma parte). FREE_FREE_ESCAPE es la
  // distancia al cuerpo del integrado (~35 de medio ancho) para no pasarle
  // por encima.
  const FREE_FREE_ESCAPE = 70;
  const ROW_Y = { j: -55, i: -45, h: -35, g: -25, f: -15, e: 15, d: 25, c: 35, b: 45, a: 55 };
  const UNO_DID = 132521;
  // Partes libres con terminales arriba (LCD 16x2): el cable sale de lado
  // antes de bajar. La tabla la inyecta Python desde FREE_ESCAPE.
  const FREE_ESCAPE = __FREE_ESCAPE__;

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

  function boardKind(index) {
    const b = BOARDS[index] || BOARDS[0];
    const kind = b ? BOARD_KINDS[String(b.did)] : null;
    return kind || BOARD_KINDS[String(DEFAULT_BB_DID)];
  }
  function holeRel(col, row, boardIndex) {
    const kind = boardKind(boardIndex || 0);
    return { x: kind.x0 + 10 * (col - 1), y: ROW_Y[row] };
  }
  function parseHole(s) {
    const m = String(s || '').trim().match(/^(?:b([1-9])\/)?(\d{1,2})([a-j])$/i);
    if (!m) return null;
    const board = m[1] ? parseInt(m[1], 10) : 0;
    const col = parseInt(m[2], 10);
    // El tope de columnas depende de la placa: 30 en la Small, 62 en la
    // grande. Un hueco fuera de rango no existe y no debe resolver a nada.
    if (!(col >= 1 && col <= boardKind(board).columns)) return null;
    return { board, col, row: m[3].toLowerCase() };
  }
  function parseRail(s) {
    const m = String(s || '').trim().match(/^(?:b([1-9])\/)?([TB])([+-])(\d{1,2})$/i);
    if (!m) return null;
    const board = m[1] ? parseInt(m[1], 10) : 0;
    const side = m[2].toUpperCase() + m[3];
    const col = parseInt(m[4], 10);
    const kind = boardKind(board);
    // La grande no publica rieles: "T+5" sobre ella no es un destino valido.
    if (!(side in (kind.rails || {}))) return null;
    if (!(col >= 1 && col <= kind.columns)) return null;
    return { board, side, col };
  }
  function holeName(col, y, boardIndex) {
    const kind = boardKind(boardIndex || 0);
    for (const [row, ry] of Object.entries(ROW_Y)) {
      if (Math.abs(y - ry) < 3) return '' + col + row;
    }
    for (const [rail, ry] of Object.entries(kind.rails || {})) {
      if (Math.abs(y - ry) < 3) return rail + col;
    }
    return null;
  }
  function bbTerminal(bbDev, col, y, boardIndex) {
    const target = holeRel(col, 'a', boardIndex);
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
      if (k === pin) return { name: k, term: unwrap(e) };
    }
    for (const [k, e] of Object.entries(map)) {
      const t = unwrap(e);
      if (t?.pinName === pin || t?.name === pin) return { name: k, term: t };
    }
    if (!norm(pin)) return null;
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

  let bbDevs = [];
  const bbDevFor = (board) => bbDevs[board] || bbDevs[0] || null;
  try { if (root && typeof root.rec === 'function') root.rec(); } catch (e) {}
  try {
    const uno = ensureDevice(UNO_DID);
    // Una protoboard por entrada de plan.boards: la primera reutiliza la que
    // ya exista (o la crea); las demas se crean siempre y se colocan en su
    // origen. clear_existing borra todas, incluidas las sobrantes.
    // La reutilizacion respeta el `did`: no se puede reciclar una Small donde
    // el plan pide una Large (cambian columnas y rieles).
    const existingBoards = devices()
      .filter((d) => !!BOARD_KINDS[String(didOf(d.dev))])
      .map((d) => d.dev);
    const claimedBoards = new Set();
    bbDevs = BOARDS.map((origin) => {
      let dev = existingBoards.find((d) => !claimedBoards.has(d) && didOf(d) === origin.did);
      if (dev) claimedBoards.add(dev);
      if (!dev) {
        dev = data.createDeviceInstance(origin.did);
        if (dev && data.devices && typeof data.devices.add === 'function') {
          try { data.devices.add(dev); } catch (e) {}
        }
      }
      try {
        const bb = typeof dev.breadboard === 'function' ? dev.breadboard() : dev.breadboard;
        if (bb && typeof bb.setPos === 'function') bb.setPos({ x: origin.x, y: origin.y });
      } catch (e) {}
      return dev;
    });

    const byRef = { uno: uno };
    // Nombre real que quedo en cada device. Tinkercad deduplica: si el
    // documento ya tiene un "r2" (aunque sea de un build anterior que se
    // esta borrando), setName("r2") deja "r21". El nombre lo decide el
    // editor, no nosotros, asi que se lee despues de asignarlo y se devuelve:
    // el verificador lo usa como identidad en vez de adivinar por posicion.
    const readName = (dev, fallback) => {
      try {
        const n = (typeof dev.getName === 'function') ? dev.getName()
          : ((typeof dev.name === 'function') ? dev.name() : dev.name);
        const s = String((n && n.val !== undefined) ? n.val : (n == null ? '' : n));
        if (s) return s;
      } catch (e) {}
      return fallback;
    };
    for (const part of (plan.parts || [])) {
      try {
        const boardIndex = (Number.isInteger(part.board) && part.board > 0) ? part.board : 0;
        const boardDev = bbDevFor(boardIndex);
        const boardAt = boardOrigin(boardIndex);
        const hasFree = part.free !== undefined && part.free !== null;
        const hasAt = part.at !== undefined && part.at !== null && String(part.at).trim() !== '';
        if (hasFree && hasAt) { errors.push(part.ref + ': cannot specify both at and free'); continue; }
        if (hasFree) {
          const fx = part.free?.x, fy = part.free?.y;
          if (typeof fx !== 'number' || typeof fy !== 'number' || !isFinite(fx) || !isFinite(fy)) {
            errors.push(part.ref + ': free requires numeric x and y'); continue;
          }
          const dev = data.createDeviceInstance(part.did);
          if (!dev) { errors.push(part.ref + ': device creation failed'); continue; }
          if (data.devices && typeof data.devices.add === 'function') {
            try { data.devices.add(dev); } catch (e) {}
          }
          byRef[part.ref] = dev;
          const bb = typeof dev.breadboard === 'function' ? dev.breadboard() : dev.breadboard;
          if (!bb || typeof bb.setPos !== 'function') {
            errors.push(part.ref + ': no breadboard placement'); continue;
          }
          const angle = (part.angle !== undefined && part.angle !== null) ? part.angle : 0;
          try {
            if (typeof dev.setName === 'function') dev.setName(part.ref);
            else if (typeof bb.setName === 'function') bb.setName(part.ref);
            else dev.name = part.ref;
          } catch (e) {}
          if (typeof bb.setAngle === 'function') bb.setAngle(angle);
          bb.setPos({ x: fx, y: fy });
          // Free part: no legs in holes, so no insert wires are created.
          placed[part.ref] = { angle, holes: {}, free: { x: fx, y: fy },
                               name: readName(dev, part.ref) };
          continue;
        }
        const anchor = parseHole(part.at);
        if (!anchor) { errors.push(part.ref + ': invalid hole ' + part.at); continue; }
        if (anchor.board !== boardIndex) { errors.push(part.ref + ': hole board mismatch ' + part.at); continue; }
        const dev = data.createDeviceInstance(part.did);
        if (dev && data.devices && typeof data.devices.add === 'function') {
          try { data.devices.add(dev); } catch (e) {}
        }
        byRef[part.ref] = dev;
        // Nombre = ref de la fixture: las propiedades se fijan despues por
        // nombre y, con varias piezas del mismo tipo (7 resistencias de un
        // display), "Resistor" es ambiguo y el preset se pierde.
        try {
          if (typeof dev.setName === 'function') dev.setName(part.ref);
          else dev.name = part.ref;
        } catch (e) {}
        const bb = typeof dev.breadboard === 'function' ? dev.breadboard() : dev.breadboard;
        if (!bb || typeof bb.setPos !== 'function') {
          errors.push(part.ref + ': no breadboard placement'); continue;
        }
        const pinNames = Object.keys(dev.name2terminal?._content || {});
        const anchorEntry = termByName(dev, part.pin) || (pinNames.length ? { name: pinNames[0], term: unwrap(dev.name2terminal._content[pinNames[0]]) } : null);
        if (!anchorEntry) { errors.push(part.ref + ': no terminals'); continue; }
        const angles = (part.angle !== undefined && part.angle !== null) ? [part.angle] : [0, 90, 180, 270];
        const kind = boardKind(boardIndex);
        let ok = null;
        for (const angle of angles) {
          if (typeof bb.setAngle === 'function') bb.setAngle(angle);
          const aOff = termOffset(anchorEntry.term);
          if (!aOff) break;
          const aRot = rot(aOff, angle);
          const rel = holeRel(anchor.col, anchor.row, boardIndex);
          const pos = { x: boardAt.x + rel.x - aRot.x, y: boardAt.y + rel.y - aRot.y };
          bb.setPos(pos);
          const holes = {};
          let all = true;
          for (const name of pinNames) {
            const t = unwrap(dev.name2terminal._content[name]);
            const off = termOffset(t);
            if (!off) { all = false; break; }
            const abs = rot(off, angle);
            const lx = pos.x + abs.x - boardAt.x, ly = pos.y + abs.y - boardAt.y;
            const col = Math.round((lx - kind.x0) / 10) + 1;
            if (col < 1 || col > kind.columns) { all = false; break; }
            if (Math.abs(lx - (kind.x0 + 10 * (col - 1))) > 3) { all = false; break; }
            const h = holeName(col, ly, boardIndex);
            if (!h) { all = false; break; }
            holes[name] = h;
          }
          if (all) { ok = { angle, holes, board: boardIndex }; break; }
        }
        if (!ok) { errors.push(part.ref + ': no angle fits all pins in holes'); continue; }
        // Register each leg in its breadboard hole with an insert wire.
        for (const [name, h] of Object.entries(ok.holes)) {
          const t = unwrap(dev.name2terminal._content[name]);
          const parsed = parseHole(h);
          let bt = null;
          if (parsed) bt = bbTerminal(boardDev, parsed.col, ROW_Y[parsed.row], boardIndex);
          else {
            const rm = String(h).match(/^([TB][+-])(\d+)$/);
            if (rm && kind.rails[rm[1]] !== undefined) {
              bt = bbTerminal(boardDev, parseInt(rm[2], 10), kind.rails[rm[1]], boardIndex);
            }
          }
          if (t && bt && window.Circuits?.BendableWireData) {
            const w = new window.Circuits.BendableWireData(root, t, bt, { insert: true });
            if (data.wires && typeof data.wires.add === 'function') data.wires.add(w);
            if (w && typeof w.updateNets === 'function') w.updateNets();
          }
        }
        placed[part.ref] = { angle: ok.angle, holes: ok.holes, board: ok.board,
                             name: readName(dev, part.ref) };
      } catch (e) { errors.push(part.ref + ': ' + e.toString()); }
    }

    function resolveEndpoint(ep) {
      const s = String(ep || '').trim();
      const hole = parseHole(s);
      if (hole) return bbTerminal(bbDevFor(hole.board), hole.col, ROW_Y[hole.row], hole.board);
      const rail = parseRail(s);
      if (rail) return bbTerminal(bbDevFor(rail.board), rail.col, boardKind(rail.board).rails[rail.side], rail.board);
      const dot = s.indexOf('.');
      if (dot > 0) {
        const ref = s.slice(0, dot), pin = s.slice(dot + 1);
        const dev = byRef[ref] || (norm(ref) === 'uno' ? uno : null);
        if (!dev) return null;
        if (norm(ref) !== 'uno' && placed[ref]) {
          const holes = placed[ref].holes || {};
          const h = holes[pin] || Object.entries(holes)
            .find(([k]) => norm(k) === norm(pin))?.[1];
          const parsed = h ? parseHole(h) : null;
          if (parsed) return bbTerminal(bbDevFor(parsed.board), parsed.col, ROW_Y[parsed.row], parsed.board);
          // Free parts have holes == {}: fall through to the real terminal.
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
      return !!parseHole(ep) || !!parseRail(ep);
    }
    function epRef(ep) {
      const s = String(ep || '').trim(), dot = s.indexOf('.');
      return dot > 0 ? s.slice(0, dot) : '';
    }
    function placedEntryForEp(ep) {
      const ref = epRef(ep);
      if (!ref) return null;
      for (const [k, v] of Object.entries(placed)) {
        if (norm(k) === norm(ref)) return v;
      }
      return null;
    }
    function isFreeEp(ep) {
      const entry = placedEntryForEp(ep);
      return !!(entry && entry.free);
    }
    function devForEp(ep) {
      const ref = epRef(ep);
      if (!ref) return null;
      if (byRef[ref]) return byRef[ref];
      for (const [k, dev] of Object.entries(byRef)) {
        if (norm(k) === norm(ref)) return dev;
      }
      return null;
    }
    function convColor(ep) {
      const s = String(ep || '').trim();
      const rail = parseRail(s);
      if (rail) return rail.side.includes('-') ? 'black' : 'red';
      const pin = norm(s.includes('.') ? s.slice(s.indexOf('.') + 1) : s);
      if (!pin) return null;
      if (pin.includes('gnd') || pin.includes('tierra') || pin.includes('ground')) return 'black';
      if (pin.includes('5v') || pin.includes('3v3') || pin.includes('33v') || pin === 'vin' || pin === 'vcc' || pin === 'vdd' || pin.startsWith('vin')) return 'red';
      return null;
    }
    function bbAbs(ep) {
      const hole = parseHole(ep);
      if (hole) {
        const rel = holeRel(hole.col, hole.row, hole.board), org = boardOrigin(hole.board);
        return { x: org.x + rel.x, y: org.y + rel.y };
      }
      const rail = parseRail(ep);
      if (rail) {
        const kind = boardKind(rail.board), org = boardOrigin(rail.board);
        return { x: org.x + kind.x0 + 10 * (rail.col - 1), y: org.y + kind.rails[rail.side] };
      }
      return null;
    }
    // Posicion absoluta de un extremo, para poder medir un cable aunque no se
    // haya ruteado: la polilinea de un cable recto tambien sirve para cazar
    // diagonales sin abrir el navegador a mirar pixeles.
    function epPos(ep, term) {
      const entry = placedEntryForEp(ep);
      const s = String(ep || '').trim(), dot = s.indexOf('.');
      const pin = dot > 0 ? s.slice(dot + 1) : '';
      if (entry && entry.holes && pin) {
        const h = entry.holes[pin] || Object.entries(entry.holes)
          .find(([k]) => norm(k) === norm(pin))?.[1];
        const p = h ? bbAbs(h) : null;
        if (p) return p;
      }
      const bb = bbAbs(ep);
      if (bb) return bb;
      const dev = devForEp(ep);
      if (dev) return termAbs(dev, term);
      return null;
    }
    function isUpperBb(ep) {
      const hole = parseHole(ep);
      if (hole) return ['j', 'i', 'h', 'g', 'f'].includes(hole.row);
      const rail = parseRail(ep);
      if (rail) return rail.side[0] === 'T';
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
      const xy = (v) => {
        try {
          const p = (typeof v === 'function') ? v() : v;
          if (p && isFinite(p.x) && isFinite(p.y)) return { x: Number(p.x), y: Number(p.y) };
          if (Array.isArray(p) && p.length >= 2 && isFinite(p[0]) && isFinite(p[1])) return { x: Number(p[0]), y: Number(p[1]) };
        } catch (e) {}
        return null;
      };
      try {
        if (term && typeof term.getBreadboardPos === 'function') {
          const p = xy(term.getBreadboardPos());
          if (p) return p;
        } else if (term && term.getBreadboardPos) {
          const p = xy(term.getBreadboardPos);
          if (p) return p;
        }
      } catch (e) {}
      try { const p = xy(term?.breadboardPos); if (p) return p; } catch (e) {}
      const base = devPos(dev);
      const desc = xy(term?.bbDesc || term?.breadboardDescription);
      const off = desc || termOffset(term);
      if (base && off) {
        let angle = 0;
        try {
          const bb = typeof dev.breadboard === 'function' ? dev.breadboard() : dev.breadboard;
          const a = bb && (typeof bb.angle === 'function' ? bb.angle() : (typeof bb.getAngle === 'function' ? bb.getAngle() : bb.angle));
          if (isFinite(a)) angle = Number(a);
        } catch (e) {}
        const r = angle ? rot(off, angle) : off;
        return { x: base.x + r.x, y: base.y + r.y };
      }
      if (desc) return desc;
      try { const p = xy(typeof term?.pos === 'function' ? term.pos() : term?.pos); if (p) return p; } catch (e) {}
      if (off) return off;
      return null;
    }
    function coordCtor() {
      for (const dev of [bbDevs[0], uno]) {
        try {
          const bb = typeof dev?.breadboard === 'function' ? dev.breadboard() : dev?.breadboard;
          const p = bb && (typeof bb.pos === 'function' ? bb.pos() : bb.pos);
          if (p && typeof p.constructor === 'function' && p.constructor !== Object) return p.constructor;
        } catch (e) {}
      }
      return null;
    }

    // Bandas por lado: cada cable ruteado toma el siguiente carril de SU
    // banda (arriba/abajo), no el de una numeracion unica. Asi la mitad de
    // los cables van por encima de la placa y la otra mitad por debajo, y
    // ninguna banda crece por culpa de la otra.
    const BASE_Y = BOARDS[0].y;
    const sideLanes = { top: 0, bottom: 0 };
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
          : (((isUnoEp(from) && isBbEp(to)) || (isBbEp(from) && isUnoEp(to)))
            || ((isFreeEp(from) && (isBbEp(to) || isUnoEp(to)))
              || (isFreeEp(to) && (isBbEp(from) || isUnoEp(from))))
            || (isFreeEp(from) && isFreeEp(to)));
        let lane = (typeof spec.lane === 'number' && spec.lane >= 0) ? spec.lane : -1;
        if (shouldRoute) {
          if (lane < 0) lane = fallbackLane;
          fallbackLane = Math.max(fallbackLane, lane + 1);
        }
        const wireLabel = from + ' -> ' + to;
        const a = resolveEndpoint(from), b = resolveEndpoint(to);
        if (!a || !b) {
          if (shouldRoute) {
            route_debug.push({ wire: wireLabel, routed: false, reason: 'endpoint_not_resolved' });
            errors.push('wire ' + wireLabel + ': route_failed: endpoint_not_resolved');
          } else { errors.push('wire ' + wireLabel + ': endpoint not resolved'); }
          continue;
        }
        if (window.Circuits?.BendableWireData) {
          const w = new window.Circuits.BendableWireData(root, a, b, { color });
          if (data.wires && typeof data.wires.add === 'function') data.wires.add(w);
          let didRoute = false;
          let routePoints = null;
          if (shouldRoute) {
            let reason = null;
            if (!w || typeof w.addPoint !== 'function') {
              reason = 'addpoint_unavailable';
            } else if (isFreeEp(from) && isFreeEp(to)) {
              // Las dos puntas son partes libres (integrados, capacitor): el
              // cable sale del pin, corre hasta una columna libre entre las
              // dos partes y entra al otro pin. Sin esto Tinkercad dibuja la
              // recta pin-a-pin y el circuito se ve torcido.
              const posA = termAbs(devForEp(from), a);
              const posB = termAbs(devForEp(to), b);
              if (!posA) reason = 'free_pos_null';
              else if (!posB) reason = 'dest_pos_null';
              else if (Math.abs(posA.y - posB.y) < 1) {
                // Misma fila: el cable recto ya es ortogonal, no hay quiebre
                // que agregar (y agregarlo dejaria dos puntos encima).
                routePoints = [[posA.x, posA.y], [posB.x, posB.y]];
                didRoute = true;
              } else {
                const samePart = norm(epRef(from)) === norm(epRef(to));
                const entryA = placedEntryForEp(from);
                const baseX = (entryA && entryA.free && isFinite(entryA.free.x))
                  ? Number(entryA.free.x) : posA.x;
                // Si la parte declara escape (LCD, cuerpo ancho) se usa ese;
                // si no, el cuerpo de un integrado se salva con 70.
                let escA = null;
                try {
                  const esc = FREE_ESCAPE[didOf(devForEp(from))];
                  if (esc) escA = baseX + esc.dx;
                } catch (e) {}
                const splitX = samePart
                  ? (escA === null ? baseX - FREE_FREE_ESCAPE : escA)
                  : (posA.x + posB.x) / 2;
                const chain = [{ x: splitX, y: posA.y },
                               { x: splitX, y: posB.y }];
                const C = coordCtor();
                try {
                  for (let i = 0; i < chain.length; i++) {
                    const pt = chain[i];
                    const r = w.addPoint(C ? new C(pt.x, pt.y) : pt, i + 1);
                    if (r === false) throw new Error('addPoint returned false');
                  }
                  routePoints = [[posA.x, posA.y]].concat(
                    chain.map((p) => [p.x, p.y]), [[posB.x, posB.y]]);
                  didRoute = true;
                } catch (e) {
                  reason = 'addpoint_error: ' + e.toString();
                }
              }
            } else if (isFreeEp(from) || isFreeEp(to)) {
              const freeIsFrom = isFreeEp(from);
              const freeEp = freeIsFrom ? from : to;
              const destEp = freeIsFrom ? to : from;
              const freeDev = devForEp(freeEp);
              const freePos = freeDev ? termAbs(freeDev, freeIsFrom ? a : b) : null;
              const destPos = isBbEp(destEp) ? bbAbs(destEp)
                : (isUnoEp(destEp) ? termAbs(uno, freeIsFrom ? b : a) : null);
              if (!freePos) reason = 'free_pos_null';
              else if (!destPos) reason = 'dest_pos_null';
              else {
                const freeEntry = placedEntryForEp(freeEp);
                const sideY = (freeEntry && freeEntry.free && isFinite(freeEntry.free.y))
                  ? Number(freeEntry.free.y) : freePos.y;
                const below = sideY > BASE_Y;
                // El corredor es la banda de siempre: cae entre el cuerpo de
                // la placa (±110) y los integrados que viven arriba
                // (y=-230). Si la parte libre esta DENTRO de la banda (o casi
                // sobre el borde, como el piezo en y=76), el carril se corre
                // 30 mas alla de la parte... pero nunca hacia la placa: el
                // tramo tiene que limpiar las dos cosas.
                const topBase = (sideY < BASE_Y - LANE_BASE)
                  ? BASE_Y - LANE_BASE : Math.min(BASE_Y - LANE_BASE, sideY - LANE_CLEAR);
                const bottomBase = (sideY > BASE_Y + LANE_BASE)
                  ? BASE_Y + LANE_BASE : Math.max(BASE_Y + LANE_BASE, sideY + LANE_CLEAR);
                const laneY = below
                  ? bottomBase + sideLanes.bottom * LANE_STEP
                  : topBase - sideLanes.top * LANE_STEP;
                if (below) sideLanes.bottom++; else sideLanes.top++;
                // Si el pin vive arriba del cuerpo, primero se sale de lado
                // (a la altura del pin, fuera del cuerpo) y despues se baja.
                // La salida se mide desde el ORIGEN de la parte (no desde el
                // pin: cada pin daria una x distinta y el abanico cruzaria
                // los cuerpos vecinos) y se escalona por carril para que los
                // cables no se dibujen uno encima de otro.
                let escBase = null;
                try {
                  const esc = FREE_ESCAPE[didOf(freeDev)];
                  if (esc) {
                    escBase = (freeEntry && freeEntry.free && isFinite(freeEntry.free.x))
                      ? Number(freeEntry.free.x) + esc.dx
                      : freePos.x + esc.dx;
                  }
                } catch (e) {}
                const escapeX = (escBase === null) ? freePos.x : escBase - lane * 8;
                const pEscape = (escBase === null) ? null : { x: escapeX, y: freePos.y };
                const pFree = { x: escapeX, y: laneY }, pDestFree = { x: destPos.x, y: laneY };
                const C = coordCtor();
                try {
                  const chain = (pEscape ? [pEscape] : []).concat([pFree, pDestFree]);
                  const pts = freeIsFrom ? chain : chain.slice().reverse();
                  for (let i = 0; i < pts.length; i++) {
                    const pt = pts[i];
                    const r = w.addPoint(C ? new C(pt.x, pt.y) : pt, i + 1);
                    if (r === false) throw new Error('addPoint returned false');
                  }
                  // Polilinea completa del cable (extremo, quiebres, extremo)
                  // para que el cerebro pueda medir cruces sin mirar pixeles.
                  const startPt = freeIsFrom ? freePos : destPos;
                  const endPt = freeIsFrom ? destPos : freePos;
                  routePoints = [[startPt.x, startPt.y]].concat(
                    pts.map((p) => [p.x, p.y]), [[endPt.x, endPt.y]]);
                  didRoute = true;
                } catch (e) {
                  reason = 'addpoint_error: ' + e.toString();
                }
              }
            } else {
              const fromIsUno = isUnoEp(from);
              const unoPos = termAbs(uno, fromIsUno ? a : b);
              const destPos = bbAbs(fromIsUno ? to : from);
              if (!unoPos) reason = 'uno_pos_null';
              else if (!destPos) reason = 'dest_pos_null';
              else {
                const upper = isUpperBb(fromIsUno ? to : from);
                const laneY = upper
                  ? BASE_Y - LANE_BASE - sideLanes.top * LANE_STEP
                  : BASE_Y + LANE_BASE + sideLanes.bottom * LANE_STEP;
                if (upper) sideLanes.top++; else sideLanes.bottom++;
                const pUno = { x: unoPos.x, y: laneY }, pDest = { x: destPos.x, y: laneY };
                const C = coordCtor();
                try {
                  // Points must follow wire direction (a -> b): when the
                  // Uno is the "to" end, order is destination-first.
                  const pts = fromIsUno ? [pUno, pDest] : [pDest, pUno];
                  for (let i = 0; i < pts.length; i++) {
                    const pt = pts[i];
                    const r = w.addPoint(C ? new C(pt.x, pt.y) : pt, i + 1);
                    if (r === false) throw new Error('addPoint returned false');
                  }
                  const startPt = fromIsUno ? unoPos : destPos;
                  const endPt = fromIsUno ? destPos : unoPos;
                  routePoints = [[startPt.x, startPt.y]].concat(
                    pts.map((p) => [p.x, p.y]), [[endPt.x, endPt.y]]);
                  didRoute = true;
                } catch (e) {
                  reason = 'addpoint_error: ' + e.toString();
                }
              }
            }
            if (didRoute) {
              route_debug.push({ wire: wireLabel, routed: true, reason: 'ok',
                                 points: routePoints });
            } else {
              route_debug.push({ wire: wireLabel, routed: false, reason: reason || 'unknown' });
              errors.push('wire ' + wireLabel + ': route_failed: ' + (reason || 'unknown'));
            }
          } else {
            // Cable recto (salto corto en la placa, pines en la misma fila):
            // la polilinea se guarda igual, asi el cerebro mide diagonales
            // tambien en los cables que el puente no toca.
            const pA = epPos(from, a), pB = epPos(to, b);
            if (pA && pB) {
              route_debug.push({ wire: wireLabel, routed: false, reason: 'straight',
                                 points: [[pA.x, pA.y], [pB.x, pB.y]] });
            }
          }
          if (didRoute) routed++;
          if (w && typeof w.updateNets === 'function') w.updateNets();
        } else if (shouldRoute) {
          route_debug.push({ wire: wireLabel, routed: false, reason: 'bendable_wire_unavailable' });
          errors.push('wire ' + wireLabel + ': route_failed: bendable_wire_unavailable');
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
  return { placed, errors, routed, route_debug };
}
"""

# La tabla de escapes se escribe una sola vez (FREE_ESCAPE) y se inyecta en
# el JS que corre en la pagina. Las claves JSON son strings y el JS las
# indexa igual: FREE_ESCAPE[113878] busca "113878".
_BUILD_JS = _BUILD_JS.replace(
    "__FREE_ESCAPE__",
    json.dumps({str(did): esc for did, esc in FREE_ESCAPE.items()}),
)

# Misma idea para la geometria de las placas: una tabla sola, inyectada, y el
# JS la consulta por el did de la placa del indice que pida la pieza.
_BUILD_JS = _BUILD_JS.replace(
    "__BOARD_KINDS__",
    json.dumps({str(did): kind for did, kind in BOARD_KINDS.items()}),
)


class ModelBuildService:
    """Build circuits by holes directly in the editor's internal model."""

    def __init__(self, browser: Optional[BrowserManager] = None) -> None:
        self.browser = browser or BrowserManager.get_instance()

    async def _wait_for_editor(self, page: Any) -> bool:
        """Espera a que el editor exista antes de tocar el modelo.

        El build y la limpieza corren dentro del modelo del editor; si la
        pagina aun no lo monto, ambos devuelven ``circuit_editor not
        available``. Eso no es culpa del circuito: se espera antes de
        evaluar y, si aun asi aparece la guarda, se reintenta una vez.
        """
        return await wait_for_editor(page)

    @staticmethod
    def _editor_guard_hit(result: Any) -> bool:
        """True si el JS se corto en la guarda de `circuit_editor`."""
        return editor_guard_hit(result)

    async def _wait_for_persistence(self, page: Any) -> Tuple[bool, Optional[int]]:
        """Poll shareJsDoc.numberPending() until 0 x _PERSIST_REQUIRED_ZEROS.

        Returns (persisted, last_pending). last_pending is the last numeric
        value observed, or None if no poll ever returned a number (e.g. every
        poll raised); a non-numeric/raising poll resets the zero streak.

        The loop itself lives in ``sharejs.wait_for_persistence``; the module
        constants are passed at call time so tests can shorten them.
        """
        return await wait_for_persistence(
            page,
            timeout_s=_PERSIST_TIMEOUT_S,
            poll_s=_PERSIST_POLL_S,
            required_zeros=_PERSIST_REQUIRED_ZEROS,
        )

    async def build_from_holes(
        self,
        parts: list[dict],
        wires: list,
        code: str | None = None,
        clear_existing: bool = False,
        boards: list[dict] | None = None,
    ) -> dict:
        """Place parts so their pins land in breadboard holes, then wire endpoints.

        A part may instead be free (off-breadboard, e.g. DC motor / 9V
        battery): ``{"ref": ..., "did": ..., "free": {"x": 560, "y": 60},
        "angle": 0}`` places it at editor coordinates with no insert wires;
        its wire endpoints (``ref.pin``) resolve to its real terminals.
        A part with both ``at`` and ``free``, or a ``free`` without numeric
        ``x``/``y``, is reported in ``errors`` (no exception, page untouched).

        ``boards`` places one Breadboard Small per entry (``[{"x":870,"y":0},
        {"x":1270,"y":0}]``); a part selects one with ``"board": N`` (default
        0) and its holes may carry the matching ``"bN/"`` prefix. With a
        single board the prefixed form is accepted too, so a plan does not
        have to strip it.

        ``wires`` accepts pairs ``[a, b]`` and objects
        ``{"from": a, "to": b, "color": ...}``; see ``plan_wire_style``.

        With ``clear_existing=True``, a separate registered edit first
        removes every wire and every device except the Uno (the device
        with a D13 terminal; the breadboard is removed too and recreated
        by the build if the plan needs it), then waits for persistence
        before building. The result always carries ``"cleared": bool``.

        Returns {"success": bool, "placed": {...}, "errors": [...],
        "persisted": bool, "routed": int, "route_debug": [...],
        "cleared": bool} plus
        "persistence_pending": int|None on timeout. ``route_debug`` holds
        one {"wire", "routed", "reason"} entry per routable wire; a
        routable wire that could not be routed also adds a
        "route_failed: ..." error (never silent).

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
        board_list: List[Dict[str, Any]] = []
        for index, board in enumerate(boards or []):
            if not isinstance(board, dict) or not all(
                isinstance(board.get(k), (int, float)) and not isinstance(board.get(k), bool)
                for k in ("x", "y")
            ):
                errors.append(f"board {index}: 'x' and 'y' must be numbers, got {board!r}")
                continue
            did = board.get("did", BREADBOARD_DID)
            if type(did) is not int or did not in BOARD_KINDS:
                errors.append(
                    f"board {index}: 'did' must be one of {sorted(BOARD_KINDS)}, got {did!r}"
                )
                continue
            board_list.append({"x": float(board["x"]), "y": float(board["y"]), "did": did})
        if len(board_list) > _MAX_BOARDS:
            errors.append(f"at most {_MAX_BOARDS} boards are supported, got {len(board_list)}")
        for part in parts or []:
            if not isinstance(part, dict):
                errors.append(f"invalid part (not an object): {part!r}")
                continue
            ref = part.get("ref", "?")
            did = part.get("did")
            if type(did) is not int or did <= 0:
                errors.append(f"part '{ref}': did must be int > 0, got {did!r}")
            at = part.get("at")
            free = part.get("free")
            has_free = free is not None
            has_at = at is not None and str(at).strip() != ""
            if has_free and has_at:
                errors.append(f"part '{ref}': specify only one of 'at' and 'free', not both")
            if has_free:
                def _num(v: Any) -> bool:
                    return (
                        isinstance(v, (int, float))
                        and not isinstance(v, bool)
                        and math.isfinite(v)
                    )

                if not isinstance(free, dict) or not (
                    _num(free.get("x")) and _num(free.get("y"))
                ):
                    errors.append(
                        f"part '{ref}': 'free' requires numeric x and y, got {free!r}"
                    )
            elif not isinstance(at, str) or not _HOLE_RE.match(at.strip()):
                errors.append(f"part '{ref}': invalid 'at' hole {at!r} (expected 1-30 + a-j)")
            board = part.get("board")
            if board is not None and (type(board) is not int or board < 0):
                errors.append(f"part '{ref}': 'board' must be int >= 0, got {board!r}")
            elif isinstance(board, int) and board_list and board >= len(board_list):
                errors.append(
                    f"part '{ref}': 'board' {board} has no entry in boards ({len(board_list)})"
                )
            # El prefijo del hueco y el campo board deben coincidir: si no, el
            # JS rechazaria la parte despues de haber empezado a construir.
            if has_at and not has_free and isinstance(at, str):
                prefix = re.match(r"^b([1-9])/", at.strip())
                hole_board = int(prefix.group(1)) if prefix else 0
                declared = board if type(board) is int else 0
                if hole_board != declared:
                    errors.append(
                        f"part '{ref}': hole {at!r} belongs to board {hole_board} "
                        f"but 'board' is {declared}"
                    )
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
                "route_debug": [],
                "cleared": False,
            }

        page = await self.browser.get_page()
        cleared = False
        if clear_existing:
            await self._wait_for_editor(page)
            clear_result = await page.evaluate(_CLEAR_JS)
            if self._editor_guard_hit(clear_result):
                # Misma guarda que el build: limpiar dos veces es idempotente
                # (la guarda corta antes de tocar nada), asi que reintentar es
                # seguro y evita un build fallido por un re-render.
                logger.warning("clear hit editor guard; waiting and retrying once")
                await self._wait_for_editor(page)
                clear_result = await page.evaluate(_CLEAR_JS)
            if not isinstance(clear_result, dict):
                return {
                    "success": False,
                    "placed": {},
                    "errors": ["circuit clear returned invalid response"],
                    "persisted": False,
                    "routed": 0,
                    "route_debug": [],
                    "cleared": False,
                }
            clear_errors = [str(e) for e in (clear_result.get("errors") or [])]
            cleared = clear_result.get("cleared") is True and not clear_errors
            if not cleared:
                return {
                    "success": False,
                    "placed": {},
                    "errors": clear_errors or ["circuit clear failed"],
                    "persisted": False,
                    "routed": 0,
                    "route_debug": [],
                    "cleared": False,
                }
            cleared = True
            clear_persisted, clear_pending = await self._wait_for_persistence(page)
            if not clear_persisted:
                return {
                    "success": False,
                    "placed": {},
                    "errors": [
                        "clear persistence timeout: shareJsDoc.numberPending() still "
                        f"{clear_pending} after {_PERSIST_TIMEOUT_S:g}s; "
                        "cleared devices/wires may reappear on reload"
                    ],
                    "persisted": False,
                    "persistence_pending": clear_pending,
                    "routed": 0,
                    "route_debug": [],
                    "cleared": True,
                }
        free_refs = [
            part.get("ref")
            for part in (parts or [])
            if isinstance(part, dict) and part.get("free") is not None
        ]
        plan: Dict[str, Any] = {
            "boards": board_list or [{"x": 870.0, "y": 0.0, "did": BREADBOARD_DID}],
            "parts": parts or [],
            "wires": plan_wire_style(wires, free_refs=free_refs),
            "code": code,
        }
        await self._wait_for_editor(page)
        result = await page.evaluate(_BUILD_JS, plan)
        if self._editor_guard_hit(result):
            # El editor se desmonto justo al evaluar (re-render): se espera y
            # se reintenta una vez. La guarda corta ANTES de tocar nada, asi
            # que reintentar no duplica partes ni cables.
            logger.warning("build hit editor guard; waiting and retrying once")
            await self._wait_for_editor(page)
            result = await page.evaluate(_BUILD_JS, plan)
        if not isinstance(result, dict):
            return {
                "success": False,
                "placed": {},
                "errors": ["model build returned invalid response"],
                "persisted": False,
                "routed": 0,
                "route_debug": [],
                "cleared": cleared,
            }

        js_errors = list(result.get("errors") or [])
        raw_debug = result.get("route_debug")
        route_debug: List[Dict[str, Any]] = (
            [dict(e) for e in raw_debug if isinstance(e, dict)]
            if isinstance(raw_debug, list)
            else []
        )
        for entry in route_debug:
            if entry.get("routed") is False:
                label = entry.get("wire") or "?"
                reason = entry.get("reason") or "unknown"
                # "straight" no es un fallo: es un cable que ya nacia
                # ortogonal (dos huecos de la placa, dos pines en la misma
                # fila). Se mide igual y el cerebro decide si es diagonal.
                if reason == "straight":
                    continue
                if not any(
                    "route_failed" in str(e) and str(label) in str(e) for e in js_errors
                ):
                    js_errors.append(f"route_failed: {label}: {reason}")
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
                "route_debug": route_debug,
                "cleared": cleared,
            }

        persisted, last_pending = await self._wait_for_persistence(page)
        if persisted:
            return {
                "success": not js_errors,
                "placed": placed,
                "errors": js_errors,
                "persisted": True,
                "routed": routed,
                "route_debug": route_debug,
                "cleared": cleared,
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
            "route_debug": route_debug,
            "cleared": cleared,
        }
