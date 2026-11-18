"""Generador de la fixture `contador-0-7-jk-v3` (taller 3, puntos 5 y 6).

Mismo sistema que la v2: mismo decodificador, mismos JK en cascada, misma tabla
de verdad y el mismo sketch. La v3 cambia **una sola cosa**: la alimentacion.

En la v1 y la v2 el 5V salia del pin del Uno y se repartia en estrella (v1) o
por filas de bus (v2). La v3 pone una pieza **Power Supply** al costado de la
placa y reparte con la regla que Eddie fijo para siempre (ver `layout_v3`):

- rojo de ``ps1.Vcc`` al riel positivo, negro de ``ps1.GND`` al negativo;
- dos cables al borde opuesto para alimentar el otro extremo de la placa;
- cada pieza toca el riel de su propia mitad, en su columna;
- la segunda placa se alimenta de la primera, no de la fuente.

El ``GND`` del Uno se queda en la net de tierra (es la referencia comun de las
medidas), pero su **5V ya no alimenta nada**: la fuente es la unica.

La v1 (`4bJNKia4pfj`) y la v2 (`jWUw1co8IZH`) no se tocan.
"""

from __future__ import annotations

from tinkercad_brain.contador_jk_v2 import contador_jk_v2_fixture

__all__ = ["FIXTURE_ID", "contador_jk_v3_fixture"]

FIXTURE_ID = "contador-0-7-jk-v3"

_DOC_EXTRA = [
    "",
    "ALIMENTACION (v3). La fuente es la pieza Power Supply que esta a la",
    "izquierda de la primera placa, no el 5V del Uno: un cable ROJO de su",
    "positivo al riel positivo y uno NEGRO de su tierra al negativo; del",
    "borde derecho salen otros dos (rojo al riel positivo del otro extremo,",
    "negro al negativo) para que la placa entera quede alimentada. Cada",
    "integrado toca el riel de su propia mitad con un cable corto en su",
    "misma columna, y la segunda placa se alimenta de la primera con los",
    "mismos dos cables. Rojo es siempre positivo y negro siempre tierra:",
    "un cable rojo de senal es un error de armado.",
    "",
    "El par de rieles de ABAJO de la placa grande es un solo nodo en el",
    "modelo (sus dos filas se llaman X), asi que no se usa para positivo y",
    "tierra a la vez: la mitad de abajo se alimenta con una bajada al borde",
    "derecho y una fila de bus. En una placa chica, que si tiene los cuatro",
    "rieles separados, la bajada va de riel a riel.",
    "",
    "La tierra del Uno sigue en la net de tierra (es la referencia de las",
    "lecturas analogicas); su pin de 5V queda sin usar.",
]

_NOTES_EXTRA = [
    "- Si el circuito no arranca, lo primero es la fuente: el LED de la",
    "  placa tiene que encender. Sin rojo en el riel positivo y negro en el",
    "  negativo, todo lo demas es ruido.",
    "- Si una parte de la placa esta muerta y la otra no, falta el puente",
    "  del borde opuesto: el riel de arriba esta alimentado y el de abajo",
    "  no. En la placa grande ese puente es la bajada de la ultima columna",
    "  mas la fila de bus.",
    "- Un cable rojo o negro que no sea de alimentacion es un error de",
    "  armado, no una decision de dibujo: los colores son la unica forma de",
    "  leer la alimentacion en una foto.",
]


def contador_jk_v3_fixture() -> dict:
    """La v2 con la fuente de poder en lugar del 5V del Uno."""
    fixture = contador_jk_v2_fixture()
    fixture["id"] = FIXTURE_ID
    fixture["title"] = (
        "Contador 0-7 v3: alimentacion por fuente y rieles"
    )
    fixture["layout"] = "v3"

    nets = [list(net) for net in fixture["nets"]]
    for net in nets:
        if "uno.5V" in net:
            net[net.index("uno.5V")] = "ps1.Vcc"
        if "uno.GND1" in net:
            net.append("ps1.GND")
    fixture["nets"] = nets

    fixture["components"] = [
        {"ref": "ps1", "type": "power-supply"},
        *fixture["components"],
    ]

    doc = list(fixture["doc"])
    if doc and doc[0].startswith("Taller 3"):
        doc[0] = doc[0].replace("(v2)", "(v3)")
    fixture["doc"] = doc + _DOC_EXTRA
    fixture["notes"] = list(fixture["notes"]) + _NOTES_EXTRA
    return fixture
