"""Cable entre dos protoboards apiladas: quiebre por el hueco de en medio.

La v4 del contador tiene la placa chica **encima** de la primera placa grande
(para que el interruptor y el pulsador queden a un cable corto). Ahora dos
huecos de placas distintas casi nunca comparten `y`: la recta que dibuja
Tinkercad seria una diagonal larga cruzando las dos protoboards.

El puente rutea esos cables con dos quiebres: sale del hueco al carril que
cae en el aire entre las dos placas, corre en horizontal y baja al otro hueco.
El carril se mide desde el **borde de la placa de abajo**, que es la que hay
que rodear, y se escalona de a 8 como la banda de las partes libres.

Se prueba sobre el texto del JS (como `test_free_escape`): un cable de placa a
placa solo se ve abriendo un navegador, y ya costo una fase entera descubrir
que la tabla vivia solo en el JS.
"""

from __future__ import annotations

import unittest

from src.services.model_build_service import _BUILD_JS, plan_wire_style


class CrossBoardRoutingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.js = _BUILD_JS

    def test_dos_huecos_de_placas_distintas_se_rutean(self):
        # Sin esto el cable entra al camino "recto" y sale diagonal.
        self.assertIn("function crossBoardPair(from, to)", self.js)
        self.assertIn("|| crossBoardPair(from, to)", self.js)

    def test_el_plan_marca_como_ruteado_el_cable_entre_placas_apiladas(self):
        """La decision real la toma Python: `route` viaja en el plan.

        El JS respeta `spec.route` cuando viene booleano, asi que agregar la
        regla solo en JS no servia: el build seguia tendiendo la diagonal
        (medido el 2026-11-16: 12 saltos rectos y solo 2 cables ruteados).

        Solo se rutea si las placas **no comparten `y`**: las dos placas
        grandes estan las dos en y=0 y sus puentes de borde ya salian
        horizontales; marcarlos ruteados los metia en el lint de "tramo sobre
        la placa" y el build fallo con 12 violaciones ese mismo dia.
        """
        apiladas = [{"x": 870, "y": 0}, {"x": 1570, "y": 0}, {"x": 870, "y": -360}]
        styled = plan_wire_style(
            [
                ["b1/28a", "b2/10a"],   # placas 1 y 2: apiladas -> quiebre
                ["5g", "8c"],           # misma placa: puente corto, recto
                ["b1/11h", "b2/19h"],   # placas 1 y 2
                ["12a", "b1/39a"],      # placas 0 y 1: misma altura, recto
            ],
            boards=apiladas,
        )
        self.assertTrue(styled[0]["route"])
        self.assertFalse(styled[1]["route"])
        self.assertTrue(styled[2]["route"])
        self.assertFalse(styled[3]["route"])
        self.assertGreaterEqual(styled[0]["lane"], 0)
        self.assertEqual(styled[1]["lane"], -1)

    def test_sin_boards_se_mantiene_el_ruteo_viejo(self):
        # Los llamadores viejos no pasan `boards`: no hay altura que comparar,
        # asi que el cable entre placas se deja recto como antes.
        styled = plan_wire_style([["b1/28a", "b2/10a"]])
        self.assertFalse(styled[0]["route"])

    def test_las_piezas_libres_no_cuentan_como_placa(self):
        # `ps1.Vcc` no es de ninguna placa: su ruteo lo decide la rama de
        # partes libres, no la de placas.
        styled = plan_wire_style(
            [["ps1.Vcc", "b2/T+1"], ["sw1.2", "rpd.2"]], free_refs=["ps1", "sw1", "rpd"]
        )
        self.assertTrue(styled[0]["route"])   # libre -> hueco
        self.assertTrue(styled[1]["route"])   # libre -> libre

    def test_los_rieles_de_placas_apiladas_tambien_se_rutean(self):
        styled = plan_wire_style(
            [["B+60", "b2/T+1"]],
            boards=[{"x": 870, "y": 0}, {"x": 1570, "y": 0}, {"x": 870, "y": -360}],
        )
        self.assertTrue(styled[0]["route"])

    def test_la_pareja_es_entre_placas_distintas_y_no_dentro_de_una(self):
        # Un salto dentro de la misma placa (`5g -> 8c`) se deja recto a
        # proposito: es un puente corto sobre el plastico.
        self.assertIn("a !== b", self.js)
        self.assertIn("return a !== null && b !== null && a !== b;", self.js)

    def test_el_carril_se_mide_desde_la_placa_de_abajo(self):
        # `Math.max(yA, yB)` es la placa de abajo (y crece hacia abajo).
        self.assertIn("Math.max(yA, yB) - LANE_BASE", self.js)
        self.assertIn("- sideLanes.top * LANE_STEP", self.js)

    def test_misma_altura_sigue_siendo_una_recta(self):
        # Dos placas a la misma `y` (placa 0 y placa 1) ya se dibujaban bien.
        self.assertIn("Math.abs(posA.y - posB.y) < 1", self.js)
        self.assertIn("routePoints = [[posA.x, posA.y], [posB.x, posB.y]];", self.js)

    def test_la_polilinea_reportada_tiene_los_dos_quiebres(self):
        # El cerebro mide diagonales y tramos sobre placa con esta polilinea.
        self.assertIn("[pA.x, pA.y],\n                                 [pB.x, pB.y]", self.js)

    def test_el_build_reporta_los_puntos_que_guardo_el_editor(self):
        """`route_debug[*].actual` es la medida del dibujo, no la intencion.

        Medido el 2026-11-16 en `3akmw1EaG0p`: dos cables entre placas
        guardaron puntos que el build no calculo (coordenadas fraccionarias
        `k/97`) y uno de ellos salio dibujado en diagonal, mientras
        `route_debug[*].points` -la polilinea que pidio el build- era
        ortogonal. Sin esta lectura el lint del cerebro dice "0 diagonales"
        sobre un dibujo torcido.
        """
        self.assertIn("function wireActualPoints(w)", self.js)
        self.assertIn("actual: actual", self.js)
        # Lee la lista real de puntos del cable, no la polilinea intentada.
        self.assertIn("const list = w && w.objects;", self.js)
        self.assertIn("o.endpoint()", self.js)

    def test_el_js_sigue_siendo_javascript_valido(self):
        import shutil
        import subprocess
        import tempfile

        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write("(" + self.js + ")")
            path = f.name
        res = subprocess.run([node, "--check", path], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)


if __name__ == "__main__":
    unittest.main()


class SameBoardBendTest(unittest.TestCase):
    """Codo dentro de la MISMA placa: el tap al riel de la columna vecina.

    La placa grande no tiene hueco de riel en las columnas 6, 12, 18, 24, 30,
    31, 37... Un interruptor anclado en 17 deja su pata de 5V en la 18, asi
    que el cable al riel tiene que entrar por `T+17`: recto saldria inclinado
    10 unidades en x y 70 en y (medido en el proyecto final, 2026-11-16).

    La decision se toma en Python y viaja en el plan como `route: true`; el JS
    le agrega **un** quiebre en L. Un cable de la misma placa sin esa marca
    sigue recto: es un puente corto sobre el plastico y asi se quiere.
    """

    def test_un_route_explicito_manda_sobre_la_heuristica(self):
        styled = plan_wire_style(
            [{"from": "b2/18e", "to": "b2/T+17", "color": "red", "route": True}],
            boards=[{"x": 870, "y": 0}, {"x": 1570, "y": 0}],
        )
        self.assertTrue(styled[0]["route"])
        self.assertGreaterEqual(styled[0]["lane"], 0)

    def test_sin_la_marca_el_puente_de_la_misma_placa_queda_recto(self):
        styled = plan_wire_style(
            [{"from": "5g", "to": "8c", "color": "green"}],
            boards=[{"x": 870, "y": 0}],
        )
        self.assertFalse(styled[0]["route"])
        self.assertEqual(styled[0]["lane"], -1)

    def test_el_js_sabe_doblar_dos_huecos_de_una_misma_placa(self):
        js = _BUILD_JS
        self.assertIn("epBoard(from) === epBoard(to)", js)
        self.assertIn("const corner = { x: posA.x, y: posB.y };", js)
