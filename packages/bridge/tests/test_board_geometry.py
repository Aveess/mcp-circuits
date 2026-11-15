"""Geometria de la breadboard grande (did 116648) en el puente.

El puente nacio cableado a la placa Small: 30 columnas, x de -145 a 145 y
riel T+/T-/B+/B-. La placa grande mide 62 columnas utiles (x -295..315) y
sus rieles no sirven (los dos de abajo comparten nombre y nodo), asi que
la geometria pasa a ser una tabla por did, inyectada en el JS.

Numeros medidos en vivo el 2026-11-15 sobre un diseno desechable; ver
docs/superpowers/specs/2026-11-15-layout-v2-design.md.
"""

from __future__ import annotations

import json
import unittest

from src.services.model_build_service import _BUILD_JS, board_kinds, hole_x, ROW_Y
from src.services.model_build_service import _is_breadboard_endpoint

SMALL = 111211
LARGE = 116648


class BoardGeometryTest(unittest.TestCase):
    def test_la_placa_grande_tiene_62_columnas_utiles(self):
        big = board_kinds()[LARGE]

        self.assertEqual(big["columns"], 62)
        self.assertEqual(hole_x(LARGE, 1), -295)
        self.assertEqual(hole_x(LARGE, 62), 315)

    def test_las_filas_son_las_mismas_en_las_dos_placas(self):
        # Medido: la grande tiene las filas invertidas *de nombre* (A abajo),
        # pero el paso es identico. El puente habla en y, no en nombres.
        self.assertEqual(ROW_Y["a"], 55)
        self.assertEqual(ROW_Y["e"], 15)
        self.assertEqual(ROW_Y["f"], -15)
        self.assertEqual(ROW_Y["j"], -55)

    def test_la_placa_grande_no_publica_rieles(self):
        # Los dos rieles de abajo comparten nombre "X" y el mismo nodo: usarlos
        # para alimentacion seria un corto silencioso. La v2 va por medias
        # columnas.
        self.assertEqual(board_kinds()[LARGE]["rails"], {})

    def test_la_placa_chica_sigue_con_30_columnas_y_sus_rieles(self):
        small = board_kinds()[SMALL]

        self.assertEqual(small["columns"], 30)
        self.assertEqual(hole_x(SMALL, 1), -145)
        self.assertEqual(hole_x(SMALL, 30), 145)
        self.assertEqual(
            small["rails"], {"T-": -95, "T+": -85, "B-": 85, "B+": 95}
        )

    def test_la_tabla_se_inyecta_en_el_js(self):
        # Si la tabla vive solo en el JS no se puede probar sin navegador.
        self.assertNotIn("__BOARD_KINDS__", _BUILD_JS)
        self.assertIn(json.dumps({str(k): v for k, v in board_kinds().items()}), _BUILD_JS)

    def test_el_js_ya_no_tiene_la_geometria_fija_de_la_chica(self):
        self.assertNotIn("const BB_DID = 111211", _BUILD_JS)
        self.assertNotIn("-145 + 10 * (col - 1)", _BUILD_JS)


class HoleValidationTest(unittest.TestCase):
    """La validacion de Python tambien tiene que dejar pasar las 62 columnas.

    Si el `at` de una pieza se rechaza antes de llegar a la pagina, la placa
    grande no sirve de nada: paso justo asi en el primer sondeo (un 74HC08
    anclado en `32e` fue rechazado con "expected 1-30").
    """

    def test_acepta_huecos_hasta_la_columna_62(self):
        self.assertTrue(_is_breadboard_endpoint("62e"))
        self.assertTrue(_is_breadboard_endpoint("32e"))
        self.assertTrue(_is_breadboard_endpoint("b1/62e"))

    def test_sigue_rechazando_lo_que_no_existe(self):
        self.assertFalse(_is_breadboard_endpoint("63e"))
        self.assertFalse(_is_breadboard_endpoint("0e"))
        self.assertFalse(_is_breadboard_endpoint("ee"))


if __name__ == "__main__":
    unittest.main()
