"""Escape lateral de las partes libres con terminales arriba.

El LCD 16x2 (did 113878) tiene sus 16 terminales sobre el borde superior:
bajar en vertical desde el pin atraviesa su propio cuerpo. El puente lo
saca de lado antes de bajar, medido en vivo (ver docs/fase0-vivo.md).

Estos tests fijan el contrato de la tabla y su inyeccion en el JS: si la
tabla se escribe solo en el JS no hay forma de probarla sin abrir un
navegador, y ya nos costo una fase entera descubrirlo.
"""

from __future__ import annotations

import json
import unittest

from src.services.model_build_service import FREE_ESCAPE, _BUILD_JS

LCD_DID = 113878
# Medido en vivo: el cuerpo del LCD empieza 139 unidades a la izquierda del
# origen del modulo. El escape tiene que salir mas alla de ese borde.
LCD_BODY_LEFT = -139


class FreeEscapeTest(unittest.TestCase):
    def test_el_lcd_es_la_unica_parte_con_escape(self):
        self.assertEqual(set(FREE_ESCAPE), {LCD_DID})

    def test_el_escape_sale_fuera_del_cuerpo_por_la_izquierda(self):
        dx = FREE_ESCAPE[LCD_DID]["dx"]

        self.assertLessEqual(dx, LCD_BODY_LEFT - 5)
        # Sin pasarse: el teclado vecino arranca ~390 a la izquierda; mas de
        # 250 de escape lo pondria encima.
        self.assertGreaterEqual(dx, -250)

    def test_la_tabla_se_inyecta_en_el_js_y_no_queda_el_marcador(self):
        self.assertNotIn("__FREE_ESCAPE__", _BUILD_JS)
        self.assertIn(json.dumps({str(LCD_DID): FREE_ESCAPE[LCD_DID]}), _BUILD_JS)
        self.assertIn("const FREE_ESCAPE =", _BUILD_JS)

    def test_el_escape_se_escalona_por_carril(self):
        # Dos cables al mismo x se dibujan uno encima del otro: la salida se
        # corre 8 unidades por carril.
        self.assertIn("- lane * 8", _BUILD_JS)

    def test_el_escape_se_mide_desde_el_origen_y_no_desde_el_pin(self):
        # freeEntry es la posicion colocada de la parte; freePos es el pin.
        # Usar el pin daria una x distinta por terminal (abanico).
        self.assertIn("freeEntry.free.x", _BUILD_JS)


if __name__ == "__main__":
    unittest.main()
