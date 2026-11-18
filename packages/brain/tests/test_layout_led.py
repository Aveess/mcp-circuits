"""Soporte de LED en el layout v2 (proyecto final, banco de 5 LEDs).

La huella no se deduce de ningun datasheet: se midio en vivo el 2026-11-17 en
una sonda desechable (7qLmhgFGPeP, ya borrada). Lo que se fija aca es que la
tabla del layout siga siendo la medida y que el plan de un LED con su
resistencia en serie salga limpio:

- las dos patas caen en medias columnas distintas (si no, el LED se auto-cortocircuita);
- el net ``r.2 -> led.anode`` es un puente corto que NO pasa por el hueco del
  catodo (eso es lo que se arregla girando la pieza 180 grados);
- dos LEDs no comparten media columna.
"""

from tinkercad_brain import boards, layout_v2


def _fixture(componentes):
    return {
        "components": componentes,
        "nets": [["r1.1"], ["r1.2", "led1.anode"], ["led1.cathode"]],
        "boards": [{"kind": "large", "x": 870, "y": 0}],
    }


def _plan(fixture):
    layout = layout_v2.plan_layout_v2(fixture)
    nets = layout_v2.plan_nets_v2(fixture, layout["placements"])
    return layout, nets


def test_la_huella_del_led_pone_las_dos_patas_en_medias_columnas_distintas():
    huella = boards.footprint_for("led")
    anode = huella["anode"]
    cathode = huella["cathode"]
    assert boards.half(anode[1]) == boards.half(cathode[1])      # misma mitad
    assert anode[0] != cathode[0]                                # otra columna
    # Si el ancla y el catodo quedaran en la MISMA media columna, la pieza se
    # cortocircuitaria sola: el nodo los une por dentro de la placa.
    assert (anode[0], boards.half(anode[1])) != (cathode[0], boards.half(cathode[1]))


def test_un_led_con_su_resistencia_planea_sin_errores_ni_conflictos():
    fixture = _fixture([
        {"ref": "r1", "type": "resistor"},
        {"ref": "led1", "type": "led"},
    ])
    layout, nets = _plan(fixture)

    assert layout["unplaced"] == []
    assert layout["errors"] == []
    assert layout_v2.column_conflicts(nets) == []

    # El LED queda en la placa, anclado por el anodo en la fila `i`, y girado
    # 180 para que el anodo quede a la izquierda (al lado de la resistencia).
    colocado = layout["placements"]["led1"]
    assert colocado["board"] == 0
    assert colocado["at"].endswith("i")
    assert colocado["pin"] == "anode"
    assert colocado["angle"] == 180


def test_el_puente_al_anodo_no_pasa_por_el_hueco_del_catodo():
    """El cable corto `r1.2 -> led1.anode` no puede cruzar el catodo.

    Un cable que pasa por encima de un hueco de otro net se ve como un corto
    aunque el simulador no lo conecte: es el defecto que obligo a girar el LED.
    """
    fixture = _fixture([
        {"ref": "r1", "type": "resistor"},
        {"ref": "led1", "type": "led"},
    ])
    layout, nets = _plan(fixture)

    _, col_catodo, fila_catodo = nets["leg_holes"]["led1.cathode"]
    puentes = [w for w in nets["wires"] if w["net"] == "r1.2"]
    assert puentes, "el net r1.2 -> led1.anode no tendio ningun cable"

    for cable in puentes:
        columnas = [int(h[:-1]) for h in (cable["from"], cable["to"]) if "." not in h]
        filas = [h[-1] for h in (cable["from"], cable["to"]) if "." not in h]
        if not columnas:
            continue
        cruza = min(columnas) <= col_catodo <= max(columnas)
        misma_mitad = any(boards.half(f) == boards.half(fila_catodo) for f in filas)
        assert not (cruza and misma_mitad), (
            f"el cable {cable['from']} -> {cable['to']} pasa por el hueco del catodo"
        )


def test_dos_leds_seguidos_no_comparten_media_columna():
    fixture = _fixture([
        {"ref": "r1", "type": "resistor"},
        {"ref": "led1", "type": "led"},
        {"ref": "r2", "type": "resistor"},
        {"ref": "led2", "type": "led"},
    ])
    layout, nets = _plan(fixture)

    assert layout["unplaced"] == []
    assert layout["errors"] == []
    assert layout_v2.column_conflicts(nets) == []

    medias = []
    for ref in ("led1", "led2"):
        for pin in ("anode", "cathode"):
            board_index, col, row = nets["leg_holes"][f"{ref}.{pin}"]
            medias.append((board_index, col, boards.half(row)))
    assert len(medias) == len(set(medias)), f"dos patas en la misma media columna: {medias}"
