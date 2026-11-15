"""Esperar a que el editor exista antes de tocar el modelo del circuito.

El JS de build, limpieza y propiedades arranca con
``if (!ce || !ce.data) return {errors: ['circuit_editor not available']}``.
Si la pagina todavia no monto el editor (o se esta re-renderizando tras una
navegacion), la tool se reporta como fallida sin que el circuito tenga nada
malo: le paso a `buzzer-activo` en la regresion de la fase 41 y a
`set_component_property_model` en la de la fase 44.

Este modulo centraliza la espera para que las tres tools usen la misma
senal y ninguna se olvide.
"""

from __future__ import annotations

from typing import Any

from ..config import logger

EDITOR_READY_JS = (
    "() => !!(window.circuit_editor && window.circuit_editor.data "
    "&& window.circuit_editor.data.devices)"
)
EDITOR_READY_TIMEOUT_S = 15.0


async def wait_for_editor(page: Any, timeout_s: float = EDITOR_READY_TIMEOUT_S) -> bool:
    """Espera a que el editor exista en la pagina. Best-effort, no lanza."""
    try:
        await page.wait_for_function(EDITOR_READY_JS, timeout=timeout_s * 1000)
        return True
    except Exception as exc:  # timeout, pagina cerrada, js deshabilitado
        logger.debug(f"editor ready wait failed: {exc}")
        return False


def editor_guard_hit(result: Any) -> bool:
    """True si el JS se corto en la guarda de `circuit_editor`."""
    if not isinstance(result, dict):
        return False
    return any(
        "circuit_editor not available" in str(e) for e in (result.get("errors") or [])
    )
