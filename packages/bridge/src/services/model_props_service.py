"""Set component properties directly in the editor's internal model.

Unlike the UI path (ComponentsService.set_component_property), this does not
need the component selected nor the inspector popover visible: it resolves
the device in ``circuit_editor.data.devices`` and calls
``device.setProperty(name, null, value, unit)`` inside ``root.rec()`` /
``root.stopRec()`` (netchuu pageSetProps technique), then waits for ShareJS
persistence like ModelBuildService.

Persistence polling reuses _PENDING_JS and the timing constants from
model_build_service; the small poll loop itself is duplicated here (rather
than instantiating ModelBuildService just to borrow its private method).
"""

from __future__ import annotations

import asyncio
import math
import time
from typing import Any, List, Optional

from ..browser.browser_manager import BrowserManager
from ..config import logger
from .editor_guard import editor_guard_hit, wait_for_editor
from .model_build_service import _PENDING_JS, _PERSIST_POLL_S, _PERSIST_REQUIRED_ZEROS, _PERSIST_TIMEOUT_S

_SET_PROP_JS = r"""
(arg) => {
  const errors = [];
  const ce = window.circuit_editor;
  if (!ce || !ce.data) return { status: 'error', component: null, candidates: [], errors: ['circuit_editor not available'] };
  const data = ce.data;
  const root = ce.root;
  const unwrap = (e) => (e && e.val !== undefined ? e.val : e);
  const norm = (s) => String(s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  const query = norm(arg.component_name);

  const describe = (id, dev) => {
    let type = '';
    try {
      const desc = typeof dev.getDescription === 'function' ? dev.getDescription() : null;
      type = desc?.device?.name || desc?.footprint_name || '';
    } catch (e) {}
    let name = '';
    try { name = String(typeof dev.name === 'function' ? dev.name() : (dev.name || '')); } catch (e) {}
    return { id: String(id), name, type: String(type || '') };
  };

  const entries = Object.entries(data.devices?._content || {})
    .map(([id, e]) => ({ id, dev: unwrap(e) }));
  const candidates = [];
  for (const { id, dev } of entries) {
    if (!dev) continue;
    const info = describe(id, dev);
    if (norm(info.name) === query || norm(info.type) === query) {
      candidates.push({ ...info, dev });
    }
  }
  const pub = (c) => ({ id: c.id, name: c.name, type: c.type });

  if (!candidates.length) {
    return { status: 'not_found', component: null, candidates: [],
             errors: ['component not found: ' + arg.component_name] };
  }
  if (candidates.length > 1) {
    return { status: 'ambiguous', component: null, candidates: candidates.map(pub),
             errors: ['ambiguous component name: ' + arg.component_name] };
  }

  const target = candidates[0];
  const dev = target.dev;
  try { if (root && typeof root.rec === 'function') root.rec(); } catch (e) {}
  try {
    if (typeof dev.setProperty !== 'function') {
      errors.push('setProperty not available on device ' + (target.name || target.type || target.id));
    } else {
      dev.setProperty(arg.property_name, null, arg.value, arg.unit ?? null);
    }
  } catch (e) {
    errors.push(e.toString());
  } finally {
    try { if (root && typeof root.stopRec === 'function') root.stopRec(); } catch (e) {}
    try { if (root && typeof root.save === 'function') root.save(); } catch (e) {}
  }
  return { status: errors.length ? 'error' : 'ok', component: pub(target),
           candidates: [], errors };
}
"""


class ModelPropsService:
    """Set a property on a device resolved by visible type or instance name."""

    def __init__(self, browser: Optional[BrowserManager] = None) -> None:
        self.browser = browser or BrowserManager.get_instance()

    async def _wait_for_persistence(self, page: Any):
        """Poll shareJsDoc.numberPending() to 0 (pattern: model_build_service)."""
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

    async def set_property(
        self,
        component_name: str,
        property_name: str,
        value: Any,
        unit: str | None = None,
    ) -> dict:
        """Set ``property_name`` on the unique device matching ``component_name``.

        Matching is exact (case/punctuation-insensitive) against the device's
        instance name or its visible type (e.g. "Ultrasonic Distance Sensor
        (4-pin)"). Returns {"success", "component", "property", "value",
        "persisted", "errors"} plus "candidates" when the name is ambiguous.
        ``value`` is passed to the model as-is (str/int/float).
        """
        base: dict = {
            "success": False,
            "component": component_name,
            "property": property_name,
            "value": value,
            "persisted": False,
            "errors": [],
        }
        if not isinstance(component_name, str) or not component_name.strip():
            return {**base, "errors": ["component_name must be a non-empty string"]}
        if not isinstance(property_name, str) or not property_name.strip():
            return {**base, "errors": ["property_name must be a non-empty string"]}

        page = await self.browser.get_page()
        args = {
            "component_name": component_name,
            "property_name": property_name,
            "value": value,
            "unit": unit,
        }
        # El JS de propiedades arranca con la guarda `circuit_editor not
        # available`: si la pagina se esta montando, la tool fallaba sin que
        # el circuito tuviera nada malo (regresion de la fase 44). Se espera
        # al editor y, si aun asi aparece la guarda, se reintenta una vez.
        await wait_for_editor(page)
        result = await page.evaluate(_SET_PROP_JS, args)
        if editor_guard_hit(result):
            await wait_for_editor(page)
            result = await page.evaluate(_SET_PROP_JS, args)
        if not isinstance(result, dict):
            return {**base, "errors": ["model setProperty returned invalid response"]}

        errors: List[str] = [str(e) for e in (result.get("errors") or [])]
        comp = result.get("component")
        if isinstance(comp, dict):
            label = comp.get("name") or comp.get("type") or comp.get("id") or component_name
        elif isinstance(comp, str) and comp:
            label = comp
        else:
            label = component_name
        status = result.get("status")

        if status == "ambiguous":
            return {
                **base,
                "errors": errors or [f"ambiguous component name: {component_name}"],
                "candidates": [c for c in (result.get("candidates") or []) if isinstance(c, dict)],
            }
        if status == "not_found" or not result.get("component"):
            return {**base, "errors": errors or [f"component not found: {component_name}"]}
        if errors or status != "ok":
            return {**base, "component": label, "errors": errors or ["setProperty failed"]}

        logger.info(f"Model setProperty {label}.{property_name}={value!r} unit={unit!r}")
        persisted, last_pending = await self._wait_for_persistence(page)
        if persisted:
            return {**base, "success": True, "component": label, "persisted": True, "errors": []}
        return {
            **base,
            "component": label,
            "errors": [
                "persistence timeout: shareJsDoc.numberPending() still "
                f"{last_pending} after {_PERSIST_TIMEOUT_S:g}s; "
                "property may be lost on reload"
            ],
            "persistence_pending": last_pending,
        }
