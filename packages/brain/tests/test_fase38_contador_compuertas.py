"""Fase 38b: contador 0-7 lento con reloj 555 y compuertas AND/OR/XOR.

Dos contratos:
1. El cableado de las compuertas hace de verdad un AND (reloj x MARCHA) y un
   OR (con el pulsador) antes de entrar a D2. Se comprueba evaluando la red
   net a net para las 8 combinaciones de entrada, no leyendo el dibujo.
2. El display no comparte altura con la fila de integrados: con 3 chips el
   ancla se corre a la derecha; con un solo chip se queda en 870.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from tinkercad_brain import sketches  # noqa: E402
from tinkercad_brain.builder import fixture_to_model_call  # noqa: E402
from tinkercad_brain.layout import (  # noqa: E402
    FREE_MODULE_X,
    IC_DISPLAY_CLEARANCE,
    plan_layout,
)

FIXTURES = REPO / "fixtures" / "fase0" / "circuits.json"
NEW = "contador-555-compuertas"


def _fixtures():
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def _fixture(fixture_id):
    return next(f for f in _fixtures() if f.get("id") == fixture_id)


def _nets_by_pin(fixture):
    pin_net = {}
    for index, net in enumerate(fixture["nets"]):
        for endpoint in net:
            pin_net[endpoint] = index
    return pin_net


def _evaluar(fixture, clk, marcha, boton):
    """Evalua la red logica hasta punto fijo y devuelve el valor de D2."""
    nets = fixture["nets"]
    pin_net = _nets_by_pin(fixture)
    values = {"uno.5V": 1, "uno.GND1": 0}
    values["uno.D8"] = marcha  # MARCHA lo maneja el sketch
    values["t1.OUT"] = clk

    # El pulsador va a GND con pull-up: sin apretar la linea queda en 1.
    values["btn1.2"] = 0
    values["btn1.1"] = 0 if boton else 1

    def val(pin):
        if pin in values:
            return values[pin]
        net = pin_net.get(pin)
        if net is None:
            return None
        for endpoint in nets[net]:
            if endpoint in values:
                return values[endpoint]
        return None  # aun no resuelto: las compuertas se evaluan por vueltas

    def set_all(pin, value):
        values[pin] = value
        for endpoint in nets[pin_net[pin]]:
            values[endpoint] = value

    gates = []
    for gate in ("1", "2", "3", "4"):
        gates.append(("u1", gate, lambda a, b: 1 - (a & b)))  # 74HC00 NAND
        gates.append(("u2", gate, lambda a, b: a ^ b))  # 74HC86 XOR

    for _ in range(12):
        for ref, gate, fn in gates:
            a = val(f"{ref}.{gate}A")
            b = val(f"{ref}.{gate}B")
            if a is None or b is None:
                continue
            out = fn(a, b)
            if val(f"{ref}.{gate}Y") != out:
                set_all(f"{ref}.{gate}Y", out)

    return val("uno.D2")


def test_la_fixture_existe_y_es_la_fase_38():
    fixture = _fixture(NEW)
    types = [c["type"] for c in fixture["components"]]
    assert "timer-555" in types
    assert "nand-gate" in types and "xor-gate" in types
    assert "seven-segment" in types and "pushbutton" in types
    assert fixture.get("wiring") == "rails"


def test_cada_endpoint_de_la_fixture_apunta_a_una_pieza_declarada():
    fixture = _fixture(NEW)
    refs = {c["ref"] for c in fixture["components"]}
    for net in fixture["nets"]:
        for endpoint in net:
            ref, pin = endpoint.split(".", 1)
            assert ref in refs, endpoint
            assert pin, endpoint


def test_el_and_el_or_y_el_pulsador_son_los_que_dicen_las_compuertas():
    fixture = _fixture(NEW)
    for clk in (0, 1):
        for marcha in (0, 1):
            for boton in (0, 1):
                esperado = (clk and marcha) or boton
                assert _evaluar(fixture, clk, marcha, boton) == int(esperado), (
                    clk,
                    marcha,
                    boton,
                )


def test_el_sketch_cuenta_flancos_y_pinta_0_a_7():
    code = sketches.gate_counter_sketch()

    assert "TEST:DIGITO=" in code
    assert "TEST:COMPUERTAS=LISTO" in code
    assert "const byte PASO = 2;" in code
    assert "const byte MARCHA = 8;" in code
    assert "pinMode(BOTON, INPUT_PULLUP);" in code
    # Tabla completa 0..7 y solo esos digitos.
    assert "const byte DIGITOS[8][7]" in code
    for digit in range(8):
        assert f"// {digit}" in code
    # Anodo comun: el pin se escribe invertido respecto de la tabla logica.
    assert "digitalWrite(PINES[i], !DIGITOS[valor][i]);" in code


def test_los_pines_del_sketch_son_los_mismos_que_los_cables():
    fixture = _fixture(NEW)
    nets = [set(net) for net in fixture["nets"]]
    type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}

    def unidos(a, b):
        return any({a, b} <= net for net in nets)

    def resistor_entre(a, b):
        """Resistencia serie: a -> rN.1 y rN.2 -> b (misma ref)."""
        for net in nets:
            if a not in net:
                continue
            for endpoint in net:
                ref, _, pin = endpoint.partition(".")
                if type_by_ref.get(ref) != "resistor" or pin != "1":
                    continue
                other = [e for e in nets if f"{ref}.2" in e]
                if other and b in other[0]:
                    return True
        return False

    for segment, pin in zip("abcdefg", (4, 5, 6, 7, 9, 10, 11)):
        # Cada segmento pasa por su resistencia de 220: sin ella el display
        # estalla en el simulador (fase 39).
        assert resistor_entre(f"uno.D{pin}", "seg." + segment), segment
    assert unidos("t1.OUT", "u1.1A")
    assert unidos("uno.D8", "u1.1B")
    assert unidos("u1.4Y", "uno.D2")
    # El pulsador cuelga de D12 (INPUT_PULLUP) y su nodo entra al OR: sin
    # pull-up la linea queda flotante y el paso manual no funciona.
    assert unidos("uno.D12", "u1.4B") and unidos("btn1.1", "u1.4B")


def test_el_modelo_del_puente_cablea_todas_las_piezas():
    fixture = _fixture(NEW)
    call = fixture_to_model_call(fixture)

    refs = {part["ref"] for part in call["parts"]}
    # El Uno no viaja en `parts`: es la placa del modelo.
    assert refs == {c["ref"] for c in fixture["components"]} - {"uno"}
    assert call["wires"], "sin cables no hay circuito"
    # El display y los integrados van libres; la placa lleva el pulsador y
    # las dos resistencias.
    free = {part["ref"] for part in call["parts"] if "free" in part}
    assert {"seg", "u1", "u2", "t1", "c1"} <= free
    assert {"btn1", "r1"} <= refs - free


def test_el_display_no_se_monta_sobre_la_fila_de_integrados():
    fixture = _fixture(NEW)
    plan = plan_layout(fixture)
    display = plan["placements"]["seg"]["free"]
    chips = [
        plan["placements"][ref]["free"]["x"]
        for ref in ("t1", "u1", "u2")
    ]

    assert all(abs(display["x"] - x) >= IC_DISPLAY_CLEARANCE for x in chips), (
        display["x"],
        chips,
    )
    assert display["x"] == max(chips) + IC_DISPLAY_CLEARANCE


def test_con_un_solo_integrado_el_display_no_se_mueve():
    """desplazador-595 es el caso ya verificado: 595 en 560 y display en 870
    (310 de aire). La regla nueva no puede tocar ese circuito."""
    plan = plan_layout(_fixture("desplazador-595"))
    assert plan["placements"]["seg"]["free"]["x"] == FREE_MODULE_X


def test_sin_integrados_el_display_se_queda_en_870():
    plan = plan_layout(_fixture("siete-segmentos"))
    assert plan["placements"]["seg"]["free"]["x"] == FREE_MODULE_X
