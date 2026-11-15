"""Serial monitor service: opening serial monitor drawer, reading serial output, and sending commands."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from ..browser.browser_manager import BrowserManager
from ..browser.selectors import CODE_SELECTORS, EDITOR_SELECTORS, SERIAL_SELECTORS
from ..config import logger


class SerialService:
    """Controls the Arduino Serial Monitor in Tinkercad Circuits."""

    def __init__(self, browser: Optional[BrowserManager] = None) -> None:
        self.browser = browser or BrowserManager.get_instance()

    async def open_serial_monitor(self) -> Dict[str, Any]:
        """Open or toggle the Serial Monitor drawer."""
        page = await self.browser.get_page()
        await self._ensure_code_panel_open(page)

        toggle_btn = await self.browser.find_first_matching(SERIAL_SELECTORS["toggle_btn"], timeout=3000, page=page)
        if toggle_btn:
            await toggle_btn.click()
            await page.wait_for_timeout(800)
            return {"success": True, "message": "Toggled Serial Monitor panel."}

        return {"success": False, "message": "Could not find Serial Monitor toggle button."}

    async def read_serial_monitor(self, last_n_lines: int = 50) -> Dict[str, Any]:
        """Read the logged output from the Arduino Serial Monitor."""
        try:
            last_n_lines = max(1, min(int(last_n_lines), 1000))
        except (ValueError, TypeError):
            last_n_lines = 50

        page = await self.browser.get_page()
        await self._ensure_serial_monitor_open(page)

        # Scrape text from serial output log
        output_text = await page.evaluate("""
            () => {
                const selectors = [
                    '.js-code_editor__serial-monitor__content',
                    '.js-code_panel__serial__text',
                    '.code_panel__serial__content__text',
                    '.serial-output',
                    'textarea.serial-log',
                    '[data-testid="serial-output"]',
                    '.serial-messages',
                    '.monitor-content',
                    '.serial-monitor-log'
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el) {
                        return el.value || el.innerText || el.textContent;
                    }
                }
                return "";
            }
        """)

        lines = [line for line in (output_text or "").splitlines() if line.strip()]
        selected_lines = lines[-last_n_lines:] if last_n_lines and len(lines) > last_n_lines else lines

        return {
            "success": True,
            "total_lines": len(lines),
            "lines": selected_lines,
            "raw_output": "\n".join(selected_lines),
            "message": f"Retrieved {len(selected_lines)} lines from Serial Monitor.",
        }

    async def send_serial_monitor(self, text: str, append_newline: bool = True) -> Dict[str, Any]:
        """Send a string/command to the Arduino via the Serial Monitor."""
        page = await self.browser.get_page()
        await self._ensure_serial_monitor_open(page)

        input_field = await self.browser.find_first_matching(SERIAL_SELECTORS["input_field"], timeout=3000, page=page)
        if not input_field:
            return {"success": False, "message": "Could not find Serial Monitor input box."}

        # Type message
        await input_field.click()
        await input_field.fill(text)
        await page.wait_for_timeout(200)

        # Send via button or Enter
        send_btn = await self.browser.find_first_matching(SERIAL_SELECTORS["send_btn"], timeout=1000, page=page)
        if send_btn:
            await send_btn.click()
        else:
            await input_field.press("Enter")

        await page.wait_for_timeout(500)
        logger.info(f"Sent serial input: '{text}'")

        return {
            "success": True,
            "sent_text": text,
            "message": f"Successfully sent '{text}' to Serial Monitor.",
        }

    async def clear_serial_monitor(self) -> Dict[str, Any]:
        """Clear the Serial Monitor output display."""
        page = await self.browser.get_page()
        await self._ensure_serial_monitor_open(page)

        clear_btn = await self.browser.find_first_matching(SERIAL_SELECTORS["clear_btn"], timeout=2000, page=page)
        if clear_btn:
            await clear_btn.click()
            await page.wait_for_timeout(300)
            return {"success": True, "message": "Serial Monitor cleared."}

        # Fallback evaluate to clear value
        await page.evaluate("""
            () => {
                const el = document.querySelector(
                    '.js-code_editor__serial-monitor__content, .js-code_panel__serial__text, .code_panel__serial__content__text, .serial-output, textarea.serial-log, [data-testid="serial-output"]'
                );
                if (el) {
                    if (el.value !== undefined) el.value = '';
                    if (el.innerText !== undefined) el.innerText = '';
                    if (el.textContent !== undefined) el.textContent = '';
                }
            }
        """)
        return {"success": True, "message": "Serial Monitor cleared via DOM."}

    async def _ensure_code_panel_open(self, page) -> None:
        """Helper to ensure the code panel is open."""
        is_active = await page.locator(
            "a#CODE_EDITOR_ID.active, .js-toggle_code_panel.active, a.circ_btn.active[data-event='code-editor']"
        ).count() > 0
        if is_active:
            return

        panel = await self.browser.find_first_matching(CODE_SELECTORS["panel"], timeout=1000, page=page)
        if not panel:
            code_btn = await self.browser.find_first_matching(EDITOR_SELECTORS["code_toggle_btn"], timeout=2000, page=page)
            if code_btn:
                await code_btn.click()
                await page.wait_for_timeout(1000)

    # Apertura del panel: si el editor tapa el boton (medido 2026-11-14),
    # Playwright agota 35 s reintentando. El fallback despacha el clic desde
    # el DOM, que no pasa por hit-testing.
    _SERIAL_IS_OPEN_JS = """
        () => {
            const textEl = document.querySelector(
                '.js-code_editor__serial-monitor__content, .code_panel__serial__content__text, .code_panel__serial__content'
            );
            if (textEl && textEl.offsetHeight > 0) return true;
            const arrow = document.querySelector('.js-code_panel__serial__arrow');
            if (arrow && arrow.classList.contains('code_panel__serial__arrow__up')) return true;
            return false;
        }
    """
    _SERIAL_CLICK_JS = """
        () => {
            const btn = document.querySelector(
                'a#SERIAL_MONITOR_ID, a.js-toggle_serial_monitor, a[data-event="serial-monitor"], .serial-monitor-toggle'
            );
            if (!btn) return false;
            btn.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
            return true;
        }
    """
    _serial_open_poll_attempts = 10
    _serial_open_poll_ms = 300

    async def _serial_monitor_open(self, page) -> bool:
        """True si el panel del monitor serial esta desplegado."""
        try:
            return bool(await page.evaluate(self._SERIAL_IS_OPEN_JS))
        except Exception:
            return False

    async def _click_serial_toggle_js(self, page) -> bool:
        """Clic sintetico sobre el boton del monitor (evita el hit-testing)."""
        try:
            return bool(await page.evaluate(self._SERIAL_CLICK_JS))
        except Exception as exc:
            logger.debug(f"Serial toggle JS click failed: {exc}")
            return False

    async def _ensure_serial_monitor_open(self, page) -> None:
        """Helper to ensure the serial monitor drawer is open."""
        await self._ensure_code_panel_open(page)

        if await self._serial_monitor_open(page):
            return

        toggle_btn = await self.browser.find_first_matching(SERIAL_SELECTORS["toggle_btn"], timeout=2000, page=page)
        if toggle_btn is not None:
            try:
                # 2.5 s basta para saber si el puntero llega: si el editor lo
                # tapa, Playwright reintenta hasta el timeout y cada reintento
                # cuesta medio minuto en un build de 4 minutos.
                await toggle_btn.click(timeout=2500)
                await page.wait_for_timeout(800)
            except Exception as exc:
                # No es un selector equivocado: el boton esta ahi y el editor
                # intercepta el puntero. Se despacha el clic desde el DOM.
                logger.warning(
                    "Serial monitor toggle click intercepted "
                    f"({str(exc).splitlines()[0][:120]}); usando clic sintetico."
                )
                await self._click_serial_toggle_js(page)
        else:
            await self._click_serial_toggle_js(page)

        for _ in range(self._serial_open_poll_attempts):
            if await self._serial_monitor_open(page):
                return
            await page.wait_for_timeout(self._serial_open_poll_ms)
        logger.warning(
            "El monitor serial no se abrio tras el clic (directo y sintetico); "
            "se leera lo que haya en el panel."
        )

