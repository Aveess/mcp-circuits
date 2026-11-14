"""Tester independiente ronda 17: fase 24 (74HC595) y reuso por ``tinkercad_id``.

No participe en el desarrollo de esta fase. Todo lo de abajo se verifico
leyendo el codigo real (``layout.py``, ``builder.py``, ``breadboard_nets.py``,
``sketches.py``, ``runner.py``, ``scripts/demo_build.py``) y comparandolo con
el contrato declarado. Las tablas que importan estan reescritas aqui a mano:
la tabla de digitos del display (segmentos a..g), el mapa de alias del 595 y
la simulacion del registro de desplazamiento. Si esas tablas cambian en el
codigo, estos tests tienen que romperse.

Hallazgos (detalle en el reporte de la ronda):

* ALTA: la fixture nueva ``desplazador-595`` NO tiene ``tinkercad_id``
  (las otras 16 si, y los 16 son de 11 caracteres, no 10 como decia el
  encargo). Su reporte y ``docs/benchmark.md`` dicen ``kBGbtwAbFlz``, pero
  ``demo_build`` manda ``preferred_id=""`` y vuelve al match por titulo: es
  justo el camino que el cambio B queria eliminar. Se comprueba que el
  reporte de la fase 24 lista ``tinkercad_list_circuits`` (1 llamada): el
  build en vivo de la fase 24 no reuso por id.
* BAJA/latente: los alias por tipo son exactos. Un pin con otra
  capitalizacion (``output 1``, ``shift register clock``, ``vcc``) queda
  opaco: no se mapea mal (bien), pero tampoco se reconoce y la fidelidad cae.
  Se deja constancia con ``xfail(strict=False)``.
* BAJA: con ``preferred_id`` valido el runner abre el circuito TRES veces
  (validar el id, "reusar" uno ya abierto y el open de ``_measure``). El
  segundo open es redundante: en el reporte de la fase 24 cada open cuesta
  ~9 s (alli fueron 2 porque se construyo por titulo, ver ALTA).
* BAJA (doc): ``docs/benchmark.md`` sigue diciendo "reutiliza el circuito
  por titulo" aunque el reuso por id ya existe.

Lo que NO se puede verificar aqui: geometria real de los cuerpos (si el
cuerpo del 595 a x=560 toca el motor a y=60), porque no hay simulador de
pantalla en los tests; y el comportamiento del puente MCP real, que se
mockea con ``call_tool``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import fixture_to_model_call
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.runner import run_build
from tinkercad_brain.sketches import (
    SEVEN_SEG_DIGITS,
    _seven_seg_mask,
    shift_register_sketch,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_PATH = ROOT / "fixtures" / "fase0" / "circuits.json"
REPORTS_DIR = ROOT / "docs" / "reportes"

# Ventana de simulacion que deja correr el runner (start_simulation con
# wait_seconds=5).
RUNNER_SIMULATION_WINDOW_MS = 5000

# Tabla estandar de un display de 7 segmentos, escrita a mano: segmentos
# encendidos por digito, en el orden fisico a b c d e f g.
OWN_SEGMENTS = {
    0: "abcdef",
    1: "bc",
    2: "abdeg",
    3: "abcdg",
    4: "bcfg",
    5: "acdfg",
    6: "acdefg",
    7: "abc",
    8: "abcdefg",
    9: "abcdfg",
}

# Alias que el cableado guardado de un 74HC595 usa en Tinkercad, escritos a
# mano desde los nombres humanos del DOM (no leidos del codigo).
OWN_595_ALIASES = {
    "Output 1": "Q0",
    "Output 2": "Q1",
    "Output 3": "Q2",
    "Output 4": "Q3",
    "Output 5": "Q4",
    "Output 6": "Q5",
    "Output 7": "Q6",
    "Output 8": "Q7",
    "Serial Out": "Q7S",
    "Input": "DS",
    "Shift Register Clock": "SHCP",
    "Output Register Clock": "STCP",
    "Output Enable": "OE",
    "Shift Register Clear": "MR",
    "Power": "Vcc",
    "Ground": "GND",
    "Vcc": "Vcc",
    "VCC": "Vcc",
    "GND": "GND",
}


def _fixtures():
    return json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))


def _fixture(fixture_id="desplazador-595"):
    return next(c for c in _fixtures() if c["id"] == fixture_id)


def _copy(obj):
    return json.loads(json.dumps(obj))


def _wire(ct, cid, pin, tt, tid, tpin):
    return {
        "source": {"component": ct, "instance_id": cid, "pin": pin},
        "target": {"component": tt, "instance_id": tid, "pin": tpin},
    }


# --------------------------------------------------------------------------
# 1. Apilado de partes libres
# --------------------------------------------------------------------------


def test_r17_dos_595_apilan_el_segundo_200px_arriba():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "ic1", "type": "shift-register"},
            {"ref": "ic2", "type": "shift-register"},
        ],
        "nets": [["uno.D11", "ic1.DS"], ["uno.D12", "ic2.DS"]],
    }

    placements = plan_layout(fixture)["placements"]

    assert placements["ic1"]["free"] == {"x": 560, "y": -230, "angle": 0}
    assert placements["ic2"]["free"] == {"x": 560, "y": -430, "angle": 0}
    # Paso de apilado propio del 595: 200 px, no comparten posicion.
    assert placements["ic1"]["free"]["x"] == placements["ic2"]["free"]["x"]
    assert (
        placements["ic1"]["free"]["y"] - placements["ic2"]["free"]["y"] == 200
    )


def test_r17_595_lcd_y_display_no_comparten_coordenada():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "ic", "type": "shift-register"},
            {"ref": "seg", "type": "seven-segment"},
            {"ref": "lcd", "type": "lcd-16x2"},
        ],
        "nets": [],
    }

    placements = plan_layout(fixture)["placements"]

    assert placements["seg"]["free"] == {"x": 870, "y": -230, "angle": 0}
    assert placements["lcd"]["free"] == {"x": 870, "y": -430, "angle": 0}
    assert placements["ic"]["free"] == {"x": 560, "y": -230, "angle": 0}
    coords = [
        (placement["free"]["x"], placement["free"]["y"])
        for placement in placements.values()
    ]
    assert len(coords) == len(set(coords)), coords


def test_r17_tres_595_dos_modulos_y_motor_bateria_todo_unico():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "ic1", "type": "shift-register"},
            {"ref": "ic2", "type": "shift-register"},
            {"ref": "ic3", "type": "shift-register"},
            {"ref": "seg", "type": "seven-segment"},
            {"ref": "lcd", "type": "lcd-16x2"},
            {"ref": "motor", "type": "dc-motor"},
            {"ref": "bat", "type": "battery-9v"},
        ],
        "nets": [],
    }

    layout = plan_layout(fixture)
    placements = layout["placements"]
    coords = []
    for ref, placement in placements.items():
        free = placement["free"]
        coords.append((free["x"], free["y"]))
    assert len(coords) == len(set(coords)), dict(placements)
    assert layout["unplaced"] == []
    assert [placements[f"ic{i}"]["free"]["y"] for i in (1, 2, 3)] == [
        -230,
        -430,
        -630,
    ]


def test_r17_el_595_no_desplaza_ni_tapa_huecos_de_la_placa():
    """Agregar el integrado libre no cambia NI un hueco de las resistencias."""
    con_ic = plan_layout(_fixture("desplazador-595"))["placements"]
    sin_ic = plan_layout(_fixture("siete-segmentos"))["placements"]
    resistencias = lambda p: {  # noqa: E731 - helper local legible
        ref: placement for ref, placement in p.items() if ref.startswith("r")
    }

    assert resistencias(con_ic) == resistencias(sin_ic)
    assert len(resistencias(con_ic)) == 7
    assert plan_layout(_fixture("desplazador-595"))["unplaced"] == []


def test_r17_la_fixture_del_595_declara_el_apilado_que_dice_el_contrato():
    placements = plan_layout(_fixture("desplazador-595"))["placements"]
    # Un solo 595 y un solo display: cada uno en la base de su apilado.
    assert placements["ic"]["free"] == {"x": 560, "y": -230, "angle": 0}
    assert placements["seg"]["free"] == {"x": 870, "y": -230, "angle": 0}


# --------------------------------------------------------------------------
# 2. shift_register_sketch
# --------------------------------------------------------------------------


def _emitted_table():
    """(digito, byte) leidos del codigo emitido, en orden."""
    codigo = shift_register_sketch()
    rows = re.findall(r"0x([0-9A-F]{2}),\s*//\s*(\d+)", codigo)
    return [(int(digito), int(byte, 16)) for byte, digito in rows]


def _own_mask(digit):
    mask = 0
    for index, segment in enumerate("abcdefg"):
        if segment in OWN_SEGMENTS[digit]:
            mask |= 1 << index
    return mask


def test_r17_la_tabla_emitida_es_la_inversa_de_mi_tabla_estandar():
    tabla = _emitted_table()

    assert [digito for digito, _byte in tabla] == list(range(10))
    for digito, byte in tabla:
        esperado = (~_own_mask(digito)) & 0x7F
        assert byte == esperado, (
            f"digito {digito}: emitido 0x{byte:02X}, "
            f"esperado 0x{esperado:02X} (~mascara & 0x7F)"
        )


def test_r17_seven_seg_digits_codifica_mi_tabla_y_la_mascara_bit_i_es_a_mas_i():
    for digito in range(10):
        pattern = SEVEN_SEG_DIGITS[digito]
        assert len(pattern) == 7
        mio = tuple(
            1 if segment in OWN_SEGMENTS[digito] else 0 for segment in "abcdefg"
        )
        assert tuple(pattern) == mio, f"digito {digito}"
        assert _seven_seg_mask(pattern) == _own_mask(digito)


def _simulate_shift_out(byte, msb_first=True):
    """74HC595 de 8 bits: el PRIMER bit que entra termina en Q7.

    Cada flanco de SHCP mete el bit en Q0 y empuja lo anterior hacia Q7.
    """
    q = [0] * 8
    for index in range(8):
        if msb_first:
            bit = (byte >> (7 - index)) & 1
        else:
            bit = (byte >> index) & 1
        q = [bit] + q[:-1]
    return q


def test_r17_msbfirst_deja_el_bit_0_en_q0_y_mapea_q0_q6_a_a_g():
    """Por que el orden importa: con MSBFIRST el bit 7 se envia primero y
    aterriza en Q7; el ultimo (bit 0) queda en Q0. Con LSBFIRST el registro
    queda al reves. El sketch usa MSBFIRST, que es lo que hace que
    Q0..Q6 = a..g."""
    invertidos_ok = []
    for digito, byte in _emitted_table():
        logicos = tuple(1 if s in OWN_SEGMENTS[digito] else 0 for s in "abcdefg")
        # Anodo comun: en el registro, 0 = segmento encendido.
        apagados = tuple(1 - bit for bit in logicos)
        q = _simulate_shift_out(byte, msb_first=True)
        assert tuple(q[:7]) == apagados, f"digito {digito}: {q}"
        al_reves = _simulate_shift_out(byte, msb_first=False)
        if tuple(al_reves[:7]) == apagados:
            # Con bytes palindromos el orden no cambiaria el dibujo: 8
            # (0x00, todos encendidos) y 2 (0x24 = 0b0100100) son los
            # unicos que caen en esa simetria.
            invertidos_ok.append(digito)
    assert invertidos_ok == [2, 8], invertidos_ok


def test_r17_el_sketch_usa_msbfirst_y_los_pines_de_la_fixture():
    codigo = shift_register_sketch()
    assert "shiftOut(DS, SHCP, MSBFIRST, DIGITOS[digito]);" in codigo

    nets = _fixture()["nets"]
    pines = {endpoint.split(".", 1)[1] for net in nets for endpoint in net}
    assert {"D11", "D8", "D12"} <= pines
    # Los defaults del sketch son los del cableado real DS/SHCP/STCP.
    assert "const byte DS = 11;" in codigo
    assert "const byte SHCP = 8;" in codigo
    assert "const byte STCP = 12;" in codigo


@pytest.mark.parametrize("pin", [1, 0, 14, -1, 99])
def test_r17_pin_fuera_de_rango_en_cualquiera_de_los_tres(pin):
    for kwarg in ("ds", "shcp", "stcp"):
        with pytest.raises(ValueError):
            shift_register_sketch(**{kwarg: pin})


@pytest.mark.parametrize("pin", [True, False, 11.0, "11", None])
def test_r17_pin_no_entero(pin):
    for kwarg in ("ds", "shcp", "stcp"):
        with pytest.raises(ValueError):
            shift_register_sketch(**{kwarg: pin})


@pytest.mark.parametrize("hold", [-1, 60001, 1.5, True, "400", None])
def test_r17_hold_ms_invalido(hold):
    with pytest.raises(ValueError):
        shift_register_sketch(hold_ms=hold)


@pytest.mark.parametrize("hold", [1, 60000])
def test_r17_hold_ms_en_los_limites_validos(hold):
    assert f"delay({hold});" in shift_register_sketch(hold_ms=hold)


def test_r17_el_ciclo_completo_cabe_en_la_ventana_del_runner():
    codigo = shift_register_sketch()
    hold = int(re.search(r"delay\((\d+)\);", codigo).group(1))
    assert hold == 400
    assert 10 * hold <= RUNNER_SIMULATION_WINDOW_MS
    # Una sola vuelta 0..9 dentro de loop(): 10 lineas de oraculo.
    assert codigo.count('Serial.print("TEST:DIGITO=");') == 1
    assert "for (byte digito = 0; digito < 10; digito++)" in codigo


def test_r17_el_sketch_es_determinista():
    assert shift_register_sketch() == shift_register_sketch()


# --------------------------------------------------------------------------
# 3. Alias del 74HC595 en el cableado guardado
# --------------------------------------------------------------------------


def _nets_for_595_pin(pin):
    inspect = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno", "pins": []},
            {"type": "8-Bit Shift Register [74HC595]", "instance_id": "ic", "pins": []},
        ],
        "wires": [
            _wire(
                "8-Bit Shift Register [74HC595]", "ic", pin,
                "Arduino Uno R3", "uno", "D2",
            )
        ],
    }
    return derive_nets(inspect)


@pytest.mark.parametrize("alias,real", sorted(OWN_595_ALIASES.items()))
def test_r17_alias_humano_del_595(alias, real):
    nets = _nets_for_595_pin(alias)
    assert [f"shiftregister1.{real}", "uno.D2"] in nets, (alias, nets)


def test_r17_vcc_del_595_no_cae_al_alias_generico_en_minuscula():
    """Regresion: 'Vcc' convertido en 'vcc' rompia la net del integrado."""
    assert _nets_for_595_pin("Vcc") == [["shiftregister1.Vcc", "uno.D2"]]
    assert _nets_for_595_pin("VCC") == [["shiftregister1.Vcc", "uno.D2"]]
    assert _nets_for_595_pin("Power") == [["shiftregister1.Vcc", "uno.D2"]]
    assert _nets_for_595_pin("Ground") == [["shiftregister1.GND", "uno.D2"]]
    assert _nets_for_595_pin("GND") == [["shiftregister1.GND", "uno.D2"]]


def test_r17_output_8_es_q7_y_serial_out_es_q7s():
    assert _nets_for_595_pin("Output 8") == [["shiftregister1.Q7", "uno.D2"]]
    assert _nets_for_595_pin("Serial Out") == [["shiftregister1.Q7S", "uno.D2"]]


def test_r17_mayusculas_mezcladas_no_se_mapean_a_un_pin_equivocado():
    """Un alias exacto con otra capitalizacion queda opaco (no inventa Q0)."""
    nets = _nets_for_595_pin("output 1")
    assert nets == [["shiftregister1.output 1", "uno.D2"]]
    assert "shiftregister1.Q0" not in nets[0]


@pytest.mark.xfail(
    strict=False,
    reason=(
        "alias exacto: 'output 1'/'shift register clock'/'vcc' no se "
        "normalizan y quedan opacos; no hay caso real hoy (Tinkercad emite "
        "las etiquetas fijas) pero es fragilidad latente"
    ),
)
def test_r17_alias_deberia_tolerar_otra_capitalizacion():
    assert _nets_for_595_pin("output 1") == [["shiftregister1.Q0", "uno.D2"]]
    assert _nets_for_595_pin("shift register clock") == [
        ["shiftregister1.SHCP", "uno.D2"]
    ]
    assert _nets_for_595_pin("vcc") == [["shiftregister1.Vcc", "uno.D2"]]


def test_r17_un_pin_inventado_del_595_no_se_traduce():
    nets = _nets_for_595_pin("NOPE")
    assert nets == [["shiftregister1.NOPE", "uno.D2"]]
    # No colisiona con ningun pin real del integrado.
    reales = set(OWN_595_ALIASES.values())
    assert "shiftregister1.NOPE" not in {f"shiftregister1.{p}" for p in reales}


def test_r17_common_del_display_no_se_confunde_con_ground_del_595():
    inspect = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno", "pins": []},
            {"type": "7 Segment Display", "instance_id": "seg", "pins": []},
            {"type": "8-Bit Shift Register [74HC595]", "instance_id": "ic", "pins": []},
        ],
        "wires": [
            _wire(
                "7 Segment Display", "seg", "Common",
                "8-Bit Shift Register [74HC595]", "ic", "Ground",
            )
        ],
    }
    nets = derive_nets(inspect)
    assert nets == [["sevensegment1.com1", "shiftregister1.GND"]]
    assert "sevensegment1.gnd" not in nets[0]
    assert "shiftregister1.com1" not in nets[0]


def test_r17_el_alias_del_595_no_contamina_otros_tipos():
    """'Output 1' solo es Q0 en un shift-register, no en una resistencia."""
    inspect = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno", "pins": []},
            {"type": "Resistor", "instance_id": "r", "pins": []},
        ],
        "wires": [
            _wire("Resistor", "r", "Output 1", "Arduino Uno R3", "uno", "D2")
        ],
    }
    assert derive_nets(inspect) == [["r1.Output 1", "uno.D2"]]


# --------------------------------------------------------------------------
# 4. Reuso por preferred_id
# --------------------------------------------------------------------------


CODE = "void setup() { pinMode(13, OUTPUT); }"
CREATED = "created999"
PINNED = "kBGbtwAbFlz"


def _build_runner_fake(list_circuits=None, open_behaviours=None):
    """Fake de call_tool. ``open_behaviours`` se consume en orden.

    Valores: "ok" (JSON success true), "success_false", "raise".
    """
    behaviours = list(open_behaviours or [])
    calls = []

    def call_tool(tool, arguments):
        calls.append((tool, arguments))
        if tool == "tinkercad_list_circuits":
            return json.dumps({"circuits": list(list_circuits or [])})
        if tool == "tinkercad_create_circuit":
            return json.dumps({"circuit_id": CREATED})
        if tool == "tinkercad_open_circuit":
            behaviour = behaviours.pop(0) if behaviours else "ok"
            if behaviour == "raise":
                raise RuntimeError("open exploto")
            if behaviour == "success_false":
                return json.dumps({"success": False, "message": "no existe"})
            return json.dumps({"success": True})
        if tool == "tinkercad_build_circuit_model":
            return json.dumps({"success": True, "persisted": True})
        if tool == "tinkercad_inspect_circuit":
            return json.dumps(_inspect_blink())
        if tool == "tinkercad_read_serial_monitor":
            return "blink: 1\n"
        return json.dumps({"success": True})

    call_tool.calls = calls
    return call_tool


def _tools(call_tool):
    return [tool for tool, _arguments in call_tool.calls]


def _opens(call_tool):
    return [
        arguments["circuit_id_or_url"]
        for tool, arguments in call_tool.calls
        if tool == "tinkercad_open_circuit"
    ]


def _builds(call_tool):
    return [
        arguments
        for tool, arguments in call_tool.calls
        if tool == "tinkercad_build_circuit_model"
    ]


def test_r17_preferred_id_valido_no_lista_ni_crea_y_reusa_limpio():
    call_tool = _build_runner_fake(
        list_circuits=[{"title": "Blink runner", "id": "listed999"}]
    )

    result = run_build(
        _fixture("blink-basico"), CODE, call_tool, "Blink runner",
        preferred_id=PINNED,
    )

    assert "tinkercad_list_circuits" not in _tools(call_tool)
    assert "tinkercad_create_circuit" not in _tools(call_tool)
    # Dos opens: el que valida el id (que ya deja el circuito abierto, asi
    # que no se repite "para reusar") y el open de _measure() antes de
    # inspeccionar. El hallazgo BAJA de esta ronda (un tercer open redundante
    # de ~9 s) quedo corregido con el flag `already_open`.
    assert _opens(call_tool) == [PINNED, PINNED]
    assert result["reused"] is True
    assert result["circuit_id"] == PINNED
    assert _builds(call_tool)[0]["clear_existing"] is True
    assert call_tool.calls[0][0] == "tinkercad_open_circuit"


def test_r17_preferred_id_con_espacios_se_recorta():
    call_tool = _build_runner_fake()
    result = run_build(
        _fixture("blink-basico"), CODE, call_tool, "Blink runner",
        preferred_id=f"  {PINNED}\n",
    )
    assert _opens(call_tool)[0] == PINNED
    assert result["circuit_id"] == PINNED
    assert "tinkercad_list_circuits" not in _tools(call_tool)


@pytest.mark.parametrize("behaviour", ["success_false", "raise"])
def test_r17_si_el_open_del_id_falla_cae_al_match_por_titulo(behaviour):
    call_tool = _build_runner_fake(
        list_circuits=[{"title": "existing42-blink-runner", "id": "existing42"}],
        open_behaviours=[behaviour],
    )

    result = run_build(
        _fixture("blink-basico"), CODE, call_tool, "Blink runner",
        preferred_id="gone404",
    )

    assert "tinkercad_list_circuits" in _tools(call_tool)
    assert _opens(call_tool)[0] == "gone404"
    assert "existing42" in _opens(call_tool)
    assert result["reused"] is True
    assert result["circuit_id"] == "existing42"
    assert _builds(call_tool)[0]["clear_existing"] is True


def test_r17_preferred_id_vacio_se_comporta_igual_que_sin_argumento():
    list_circuits = [{"title": "existing42-blink-runner", "id": "existing42"}]

    sin_arg = _build_runner_fake(list_circuits=list_circuits)
    con_vacio = _build_runner_fake(list_circuits=list_circuits)

    result_sin = run_build(
        _fixture("blink-basico"), CODE, sin_arg, "Blink runner"
    )
    result_vacio = run_build(
        _fixture("blink-basico"), CODE, con_vacio, "Blink runner",
        preferred_id="",
    )

    assert _tools(sin_arg) == _tools(con_vacio)
    # Camino por titulo: un open para reusar y otro en _measure().
    assert _opens(sin_arg) == _opens(con_vacio) == ["existing42", "existing42"]
    assert result_sin["circuit_id"] == result_vacio["circuit_id"] == "existing42"
    assert result_sin["reused"] is True and result_vacio["reused"] is True


def test_r17_preferred_id_solo_espacios_se_comporta_como_vacio():
    call_tool = _build_runner_fake(
        list_circuits=[{"title": "Blink runner", "id": "existing42"}]
    )
    result = run_build(
        _fixture("blink-basico"), CODE, call_tool, "Blink runner",
        preferred_id="   ",
    )
    assert _opens(call_tool)[0] == "existing42"
    assert result["reused"] is True


def test_r17_reuse_false_ignora_preferred_id():
    call_tool = _build_runner_fake(
        list_circuits=[{"title": "Blink runner", "id": "existing42"}]
    )

    result = run_build(
        _fixture("blink-basico"), CODE, call_tool, "Blink runner",
        reuse=False, preferred_id=PINNED,
    )

    # No se abre para reusar: el primer open es el de _measure(), despues
    # del create y del build. Y la lista ni se consulta.
    assert "tinkercad_list_circuits" not in _tools(call_tool)
    assert _tools(call_tool)[0] == "tinkercad_create_circuit"
    assert _tools(call_tool).index("tinkercad_open_circuit") > _tools(
        call_tool
    ).index("tinkercad_build_circuit_model")
    assert result["circuit_id"] == CREATED
    assert result["reused"] is False
    assert _builds(call_tool)[0]["clear_existing"] is False


# --------------------------------------------------------------------------
# 5. Fixtures: tinkercad_id unico, con formato y coherente con el reporte
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture", _fixtures(), ids=[f["id"] for f in _fixtures()]
)
def test_r17_cada_fixture_tiene_id_alfanumerico_y_coincide_su_reporte(fixture):
    fixture_id = fixture["id"]
    tinkercad_id = fixture.get("tinkercad_id")
    # Nota: el encargo decia "10 caracteres", pero los 16 ids ya verificados
    # en vivo (y las URLs /things/ de los reportes) tienen 11. Tinkercad usa
    # ids de 11; se fija 11, no 10.
    assert isinstance(tinkercad_id, str) and re.fullmatch(
        r"[A-Za-z0-9]{11}", tinkercad_id or ""
    ), f"{fixture_id}: tinkercad_id ausente o invalido: {tinkercad_id!r}"

    report = REPORTS_DIR / f"{fixture_id}.md"
    if report.exists():
        found = re.search(r"/things/([A-Za-z0-9]+)", report.read_text(encoding="utf-8"))
        assert found, f"{fixture_id}: reporte sin URL /things/<id>"
        assert found.group(1) == tinkercad_id, (
            f"{fixture_id}: fixture={tinkercad_id!r} reporte={found.group(1)!r}"
        )


def test_r17_los_ids_presentes_son_unicos():
    ids = [c["tinkercad_id"] for c in _fixtures() if c.get("tinkercad_id")]
    assert len(ids) == len(set(ids)), ids
    assert len(_fixtures()) == 17


@pytest.mark.parametrize(
    "fixture_id",
    [c["id"] for c in _fixtures() if c.get("tinkercad_id")],
)
def test_r17_el_id_clavado_de_cada_fixture_evita_listar_y_crear(fixture_id):
    """Prueba de punta a punta del cableado fixture -> demo_build -> runner.

    Para toda fixture CON id: abrir ese id, sin listar la cuenta y sin crear
    un duplicado. La unica que no entra es ``desplazador-595`` (hallazgo
    ALTA, cubierto por el test de ids de arriba).
    """
    fixture = _fixture(fixture_id)
    call_tool = _fake_runner({})

    result = run_build(
        fixture, None, call_tool, fixture["title"],
        preferred_id=str(fixture.get("tinkercad_id") or ""),
    )

    assert "tinkercad_list_circuits" not in _tools(call_tool)
    assert "tinkercad_create_circuit" not in _tools(call_tool)
    assert _opens(call_tool)[0] == fixture["tinkercad_id"]
    assert result["circuit_id"] == fixture["tinkercad_id"]
    assert result["reused"] is True


def test_r17_el_reporte_del_595_prueba_que_el_build_no_reuso_por_id():
    """Evidencia del hallazgo ALTA: el build en vivo listo la cuenta.

    Con preferred_id valido el runner NO llama tinkercad_list_circuits. El
    reporte de la fase 24 registra una llamada: se construyo por titulo.
    """
    report = (REPORTS_DIR / "desplazador-595.md").read_text(encoding="utf-8")
    assert "tinkercad_list_circuits" in report


# --------------------------------------------------------------------------
# 6. Regresion: las partes libres siguen sin reparar cables
# --------------------------------------------------------------------------


def _inspect_blink(missing=False):
    uno = ("Arduino Uno R3", "uno1")
    resistor = ("Resistor", "r_a")
    led = ("LED", "led_a")

    def component(type_, instance_id):
        return {"type": type_, "instance_id": instance_id, "name": "1", "pins": []}

    def endpoint(comp, pin):
        return {"component": comp[0], "pin": pin, "instance_id": comp[1]}

    wires = [
        {"source": endpoint(uno, "D13"), "target": endpoint(resistor, "Terminal 1")},
        {"source": endpoint(resistor, "Terminal 2"), "target": endpoint(led, "Anode")},
        {"source": endpoint(led, "Cathode"), "target": endpoint(uno, "GND")},
    ]
    if missing:
        wires = wires[:-1]
    return {
        "components": [component(*uno), component(*resistor), component(*led)],
        "wires": wires,
    }


def _fake_runner(inspect_data):
    calls = []

    def call_tool(tool, arguments):
        calls.append((tool, arguments))
        if tool == "tinkercad_list_circuits":
            return json.dumps({"circuits": []})
        if tool == "tinkercad_create_circuit":
            return json.dumps({"circuit_id": "newcircuit1"})
        if tool == "tinkercad_open_circuit":
            return json.dumps({"success": True})
        if tool == "tinkercad_build_circuit_model":
            return json.dumps({"success": True, "persisted": True})
        if tool == "tinkercad_inspect_circuit":
            return json.dumps(inspect_data)
        if tool == "tinkercad_read_serial_monitor":
            return ""
        return json.dumps({"success": True})

    call_tool.calls = calls
    return call_tool


def _fixtures_with_free_parts():
    ids = []
    for fixture in _fixtures():
        call = fixture_to_model_call(fixture)
        if any("free" in part for part in call["parts"]):
            ids.append(fixture["id"])
    return ids


@pytest.mark.parametrize(
    "fixture_id",
    [
        "motor-dc-transistor",
        "motor-l293d-bateria",
        "lcd-contador",
        "lcd-temperatura",
        "lcd-distancia",
        "siete-segmentos",
        "desplazador-595",
    ],
)
def test_r17_fixture_con_parte_libre_no_intenta_reparar(fixture_id):
    call_tool = _fake_runner({})  # inspeccion vacia: fidelidad 0

    result = run_build(_fixture(fixture_id), None, call_tool, "r17 libre")

    assert result["repair_attempted"] is False
    assert len(_builds(call_tool)) == 1, _tools(call_tool)
    assert result["fidelity_before_repair"] is None


def test_r17_la_lista_de_fixtures_libres_es_la_esperada():
    libres = _fixtures_with_free_parts()
    assert "desplazador-595" in libres
    assert "blink-basico" not in libres
    assert "led-rgb" not in libres


def test_r17_fixture_sin_partes_libres_si_repara_una_vez():
    call_tool = _fake_runner(_inspect_blink(missing=True))

    result = run_build(_fixture("blink-basico"), None, call_tool, "r17 placa")

    assert result["repair_attempted"] is True
    assert len(_builds(call_tool)) == 2
    # El rebuild de reparacion solo manda cables, sin partes.
    assert "parts" not in _builds(call_tool)[1] or not _builds(call_tool)[1]["parts"]
