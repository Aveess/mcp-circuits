"""Espera del flush de ShareJS, compartida por build de modelo y codigo.

Tinkercad guarda el diseno con ShareJS: los cambios son operaciones que el
cliente encola y envia al servidor. Recargar la pagina antes de que la cola
se vacie descarta lo pendiente y el editor vuelve al estado anterior — medido
en vivo como "Code change reverted upon project reload" al inyectar un sketch
largo (2026-11-14).

El contrato ya vivia en ``model_build_service``; se movio aqui para que
``code_service`` lo use sin duplicar el sondeo ni la constante JS.
"""

from __future__ import annotations

import asyncio
import math
import time
from typing import Any, Optional, Tuple

from ..config import logger

__all__ = [
    "PENDING_JS",
    "PERSIST_TIMEOUT_S",
    "PERSIST_POLL_S",
    "PERSIST_REQUIRED_ZEROS",
    "PERSIST_STALL_POLLS",
    "pending_ops",
    "wait_for_persistence",
]

PERSIST_TIMEOUT_S = 30.0
PERSIST_POLL_S = 0.3
PERSIST_REQUIRED_ZEROS = 3
# Sondeos con el mismo valor para declarar la cola estancada (ver
# wait_for_persistence: un op residual permanente no impide el guardado).
PERSIST_STALL_POLLS = 10

# Devuelve las operaciones pendientes de ShareJS; 0 cuando shareJsDoc o
# numberPending no existen (en ese caso no hay nada pendiente por ese doc).
PENDING_JS = r"""
() => {
  try {
    const doc = window.circuit_editor?.root?.shareJsDoc;
    if (!doc || typeof doc.numberPending !== 'function') return 0;
    const n = doc.numberPending();
    return (typeof n === 'number' && isFinite(n)) ? n : 0;
  } catch (e) { return 0; }
}
"""


async def pending_ops(page: Any) -> int:
    """Operaciones pendientes ahora mismo (0 si no se puede saber).

    Un unico sondeo, para decidir si hace falta limpiar la cola antes de
    escribir el codigo. Un fallo de lectura se trata como 0: no se bloquea
    un build por no poder mirar.
    """
    try:
        raw = await page.evaluate(PENDING_JS)
    except Exception:
        return 0
    if isinstance(raw, (int, float)) and not isinstance(raw, bool) and math.isfinite(raw):
        return int(raw)
    return 0


async def wait_for_persistence(
    page: Any,
    timeout_s: float = PERSIST_TIMEOUT_S,
    poll_s: float = PERSIST_POLL_S,
    required_zeros: int = PERSIST_REQUIRED_ZEROS,
    stall_polls: int = PERSIST_STALL_POLLS,
) -> Tuple[bool, Optional[int]]:
    """Sondea ``shareJsDoc.numberPending()`` hasta ver 0 x ``required_zeros``.

    Devuelve ``(persisted, last_pending)``. ``last_pending`` es el ultimo valor
    numerico observado, o ``None`` si ningun sondeo devolvio un numero (por
    ejemplo, si todos lanzaron); un sondeo no numerico corta la racha de ceros.

    Un valor **estancado** cuenta como terminado. Medido el 2026-11-14: tras
    montar un integrado libre (74HC73) ``numberPending()`` se queda en 1 para
    siempre, y en 2 tras inyectar codigo, mientras los cables y las partes si
    llegan al servidor (una recarga los devuelve). El op residual no se envia
    nunca, asi que esperarlo agota el timeout y niega un guardado que ocurrio.
    Si el valor no cambia en ``stall_polls`` sondeos, el cliente ya no tiene
    nada nuevo que mandar: se devuelve ``(True, last)`` y la verificacion por
    recarga —que si distingue lo guardado de lo perdido— tiene la ultima
    palabra.
    """
    deadline = time.monotonic() + timeout_s
    stable_zeros = 0
    stalled = 0
    last: Optional[int] = None
    while True:
        try:
            raw = await page.evaluate(PENDING_JS)
        except Exception:
            raw = None
        if isinstance(raw, (int, float)) and not isinstance(raw, bool) and math.isfinite(raw):
            value = int(raw)
            stalled = stalled + 1 if value == last else 0
            last = value
            stable_zeros = stable_zeros + 1 if last == 0 else 0
            if stable_zeros >= required_zeros:
                return True, last
            if value > 0 and stalled >= stall_polls:
                logger.warning(
                    "ShareJS quedó con %d operación(es) sin confirmar tras %d "
                    "sondeos; se sigue y la recarga verifica qué se guardó.",
                    value,
                    stalled + 1,
                )
                return True, last
        else:
            stable_zeros = 0
            stalled = 0
        if time.monotonic() >= deadline:
            return False, last
        await asyncio.sleep(poll_s)
