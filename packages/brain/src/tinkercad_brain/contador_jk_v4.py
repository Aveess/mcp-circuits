"""Generador de la fixture `contador-0-7-jk-v4`: el contador **sin Arduino**.

La v3 (`kSakfQXHtmU`) funciona, pero el Uno se queda con dos trabajos: emitir
el serial de prueba y **mover EN y RESET** (D8 y D9). Este archivo quita el
microcontrolador y deja esos dos mandos en hardware, copiando la solucion del
diseno del taller del companero (`47d2dZVCX5m`, "taller flip-flops"):

- **EN**: un interruptor deslizante SPDT (`did 58458`) con el comun a las
  entradas J y K de las tres etapas, un extremo a GND y el otro a Vcc. Con el
  comun en GND, J=K=0 y los flip-flops conservan el estado (contador parado);
  con el comun en Vcc, J=K=1 y basculan con cada flanco (contador andando).
- **RESET**: un pulsador de cuatro patas (`did 144786`) del nodo de entrada
  del inversor `u1.6` a Vcc, con una resistencia de 10k de ese nodo a GND. En
  reposo la entrada del inversor es 0, su salida `u1.6Y` es 1 y las tres R de
  los JK quedan inactivas; al pulsar, la salida baja a 0 y los tres JK se
  ponen a 000. No hay reset permanente: el boton solo actua mientras se
  mantiene apretado, igual que en la placa del companero.

Todo lo demas es la v2/v3: mismo 555, mismos tres JK, mismo decodificador de
siete integrados, mismo display de catodo comun. El layout es `v3`, asi que
la alimentacion sigue saliendo de la pieza **Power Supply** y no del Uno
(que ya no existe).

Lo que se pierde, y hay que decirlo: **sin micro no hay monitor serial**. El
sketch no existe y el oraculo por serial tampoco. La unica evidencia de que
cuenta es la foto del display: 0, 1, 2 ... 7. Por eso la fixture no declara
`oracle_serial` ni `code_features`.

La v3 (`kSakfQXHtmU`) queda intacta; esto es un diseno nuevo.
"""

from __future__ import annotations

from tinkercad_brain.contador_jk_v2 import contador_jk_v2_fixture

__all__ = ["FIXTURE_ID", "contador_jk_v4_fixture"]

FIXTURE_ID = "contador-0-7-jk-v4"

# Posicion de las dos piezas sueltas: a la izquierda de la primera placa, en
# columna, alineadas con la fuente. El interruptor arriba y el pulsador abajo
# para que no se toquen los cuerpos ni los cables.
_FREE_AT = {
    "sw1": {"x": 450, "y": -250},
    "btn1": {"x": 450, "y": 250},
}

_EN_RESET_DOC = [
    "SIN ARDUINO (v4). El contador es 100 % hardware: 555 como reloj, tres",
    "74HC73 en cascada, el decodificador de compuertas y el display. La",
    "alimentacion viene de la pieza Power Supply, no de un micro.",
    "",
    "EN es el interruptor deslizante SW1: su terminal comun va a J y K de",
    "las tres etapas, un extremo a GND y el otro a Vcc. Con el comun en GND",
    "los flip-flops conservan el estado y el conteo se detiene; con el comun",
    "en Vcc basculan con cada flanco y el conteo sigue. SW1 nace en la",
    "posicion de Vcc: al abrir el diseno ya esta contando y deslizarlo lo",
    "detiene (medido en vivo: al reves el display se quedaba en 0).",
    "",
    "RESET es el pulsador SW2: esta entre Vcc y la entrada del inversor",
    "u1.6, que tiene una resistencia de 10k a GND (pull-down). En reposo",
    "esa entrada vale 0, la salida del inversor vale 1 y las tres R de los",
    "JK estan inactivas. Al apretar, la salida baja a 0 y los tres JK",
    "vuelven a 000 en el acto, sin esperar flanco de reloj.",
    "",
]

_SIN_SKETCH_DOC = [
    "No hay micro, no hay codigo y no hay monitor serial. La prueba de que",
    "cuenta es mirar el display: 0, 1, 2, 3, 4, 5, 6, 7 y otra vez 0, un",
    "digito por flanco de bajada del 555 (aproximadamente cada 0,4 s).",
    "",
]

_ORACLE = [
    "Esta version no tiene micro: no hay serial y el oraculo del runner no",
    "aplica. La verificacion es visual, con la simulacion corriendo:",
    "  - el display muestra los digitos 0..7 en orden y vuelve a 0;",
    "  - con EN en un extremo el numero se queda quieto y con EN en el otro",
    "    sigue contando;",
    "  - al apretar RESET el display salta a 0 y sigue desde ahi.",
]

_NOTES_EXTRA = [
    "- Si el display no se mueve nunca, lo primero es EN: con el comun del",
    "  interruptor en GND (J=K=0) el contador esta en pausa a proposito.",
    "  Cambiar el interruptor al otro extremo y volver a mirar.",
    "- Si el display esta clavado en 0 y no sale de ahi, el reset quedo",
    "  activo: revisar que la resistencia de 10k del nodo del pulsador vaya",
    "  a GND y no a Vcc. Con el pull-down al reves el inversor entrega 0",
    "  permanente y los JK no cuentan.",
    "- Sin Arduino no hay monitor serial. Si alguien pide TEST:DIGITO, ese",
    "  dato ya no existe en este circuito: se mira el display.",
]


def contador_jk_v4_fixture() -> dict:
    """La v2 sin el Uno, con EN por interruptor y RESET por pulsador."""
    fixture = contador_jk_v2_fixture()
    fixture["id"] = FIXTURE_ID
    fixture["title"] = (
        "Contador 0-7 v4: sin Arduino, EN por interruptor y RESET por pulsador"
    )
    fixture["layout"] = "v3"

    # --- Piezas: se va el Uno, entran la fuente, el switch, el pulsador y la
    # resistencia del pull-down. -------------------------------------
    components = [
        component
        for component in fixture["components"]
        if component["type"] != "arduino-uno"
    ]
    components = [
        {"ref": "ps1", "type": "power-supply"},
        {"ref": "sw1", "type": "slideswitch"},
        {"ref": "btn1", "type": "pushbutton"},
        {"ref": "rpd", "type": "resistor"},
        *components,
    ]
    fixture["components"] = components

    # --- Nets: se quitan TODAS las lecturas del Uno y se recablean EN y
    # RESET. Nada mas cambia. ---------------------------------------
    nets: list[list[str]] = []
    for net in fixture["nets"]:
        limpia = []
        for endpoint in net:
            if endpoint == "uno.D8":
                # EN: el comun del interruptor ocupa el lugar del pin del Uno.
                limpia.append("sw1.common")
            elif not endpoint.startswith("uno."):
                limpia.append(endpoint)
        if len(limpia) < 2:
            continue
        nets.append(limpia)

    # Alimentacion: la fuente es la unica. El 5V del Uno ya se fue con las
    # lecturas; su GND tambien. `ps1.Vcc` y `ps1.GND` entran aqui.
    for net in nets:
        upper = {endpoint.split(".", 1)[-1].upper() for endpoint in net}
        if upper & {"VCC", "5V"}:
            net.append("ps1.Vcc")
            # El interruptor del EN y el pulsador del RESET tambien comen de
            # la fuente: un extremo de cada uno va a positivo.
            #
            # OJO con cual extremo del switch: medido en vivo (2026-11-15),
            # el Slideswitch nace con el comun en la clave `1`. Cablear el
            # `1` a GND deja el contador detenido al abrir el diseno y hay
            # que deslizarlo a mano para verlo contar (paso en el build
            # 3akmw1EaG0p: el display se quedo en 0 cuarenta segundos).
            # Por eso el `1` (posicion de reposo) va a Vcc: el circuito
            # cuenta solo y deslizarlo lo detiene, que es lo demostrable.
            net.extend(["sw1.1", "btn1.2"])
        if upper & {"GND", "GND1", "GND2", "COM1", "COM2"}:
            net.append("ps1.GND")
            # El otro extremo del switch y la resistencia del pull-down.
            net.extend(["sw1.2", "rpd.2"])

    # EN: el comun del interruptor reemplaza a uno.D8 (ya esta en su net).

    # RESET: el nodo del pulsador (con su pull-down) reemplaza a uno.D9 en la
    # entrada del inversor. La salida u1.6Y ya la dejo armada la v2.
    nets.append(["btn1.1", "rpd.1", "u1.6A"])

    fixture["nets"] = nets
    fixture["free_parts"] = dict(_FREE_AT)
    # El build siempre crea el Uno; con este campo el puente lo quita al
    # final porque ningun cable lo usa. Es la unica forma de que el lienzo
    # quede sin micro, que es lo que pide un circuito 100 % hardware.
    fixture["no_arduino"] = True

    # Sin micro no hay sketch, ni marcas de serial, ni features de codigo.
    fixture.pop("code_features", None)
    fixture["oracle_serial"] = []
    fixture["sim_wait_seconds"] = 30

    # La v2 explica EN/RESET por pines del Uno y el sketch que anuncia cada
    # digito; en la v4 nada de eso existe. En vez de filtrar lineas sueltas
    # (quedaban frases a medias), el bloque se arma por tramos: lo que sigue
    # siendo cierto del contador, lo nuevo de EN/RESET, el decodificador y el
    # display tal cual, y los capacitores.
    base = list(fixture["doc"])
    doc = [base[0].replace("(v2)", "(v4, sin Arduino)"), ""]
    doc += base[2:8]          # descripcion del contador y de los JK
    doc += _EN_RESET_DOC
    doc += base[12:51]        # decodificador, display y tabla de verdad
    doc += _SIN_SKETCH_DOC
    doc += base[63:]          # los dos capacitores insertados
    # El parrafo del display hablaba de lo que "lee el sketch"; sin micro, el
    # que manda el segmento es el nodo de la compuerta.
    doc = [
        linea.replace(
            "luce con HIGH, asi que el sketch lee el nodo de la compuerta tal cual",
            "luce con HIGH: el nodo de la compuerta es el que manda el segmento",
        ).replace(
            "(en la v1 habia un inversor y se leia LOW)",
            "(en la v1 habia un inversor y se activaba con LOW)",
        )
        for linea in doc
    ]
    fixture["doc"] = doc
    fixture["oracle"] = _ORACLE
    fixture["notes"] = list(fixture["notes"]) + _NOTES_EXTRA
    return fixture
