"""Deterministic protoboard layout planner.

Assigns breadboard holes to components from a fixture circuit.
Board: columns 1-30, rows j-i-h-g-f above the gap, e-d-c-b-a below.
"""

BLOCK_WIDTH = 6
MAX_COLUMN = 30
# Blocks start at 1, 7, 13, 19: a block starting at 25 would need
# column 31 (start + BLOCK_WIDTH) as its end boundary, beyond the board.
LAST_BLOCK_START = 19
# First (leftmost) pin per 3-pin type, physical order left to right:
# servo gnd/vcc/signal, potentiometer 1/2/3, tmp36 vcc/vout/gnd,
# transistor-npn collector/base/emitter (live-verified on row c).
THREE_PIN_FIRST_PIN = {
    "servo": "gnd",
    "potentiometer": "1",
    "tmp36": "vcc",
    "transistor-npn": "collector",
}
THREE_PIN_PINS = 3
# Cursor advance per 3-pin block: 3 pin columns + 1 separation column.
THREE_PIN_WIDTH = 4
# HC-SR04 physical pin order left to right: vcc, trig, echo, gnd.
ULTRASONIC_PINS = 4
# Cursor advance per ultrasonic block: 4 pin columns + 1 separation column.
ULTRASONIC_WIDTH = 5
# Minimum start column for the HC-SR04: its body extends up and to the
# left from its pins on row d, so placed next to the LED block (columns
# 1-6, row i) the sensor body covers the LED on screen. Starting it at
# column 18 or later (right side of the board) keeps its body clear of
# components to its left; a cursor already past 18 is respected.
ULTRASONIC_MIN_COLUMN = 18
# LED RGB (common cathode): red pin at column B on row i, pins occupy
# B..B+3. Each series resistor is angle 90 (pin 2 lands 4 columns after
# pin 1), so pin 1 sits at a color-specific offset/row such that pin 2
# falls on its color column: red B, green B+3, blue B+2.
RGB_TYPE = "led-rgb-common-cathode"
RGB_RESISTOR_LAYOUT = {"red": (-4, "g"), "green": (-1, "h"), "blue": (-2, "j")}
# Footprint from the leftmost resistor pin (B-4) to the last RGB pin
# (B+3): 8 columns of cursor advance.
RGB_WIDTH = 8
# Piezo/buzzer (fixture slug "buzzer", did 114067), live-verified:
# anchoring its positive leg at <c>e with angle 0 puts the negative leg
# exactly at <c+5>e. The placement pin is the FIXTURE pin ("positive");
# builder maps it to the real terminal "+".
# Footprint 6 columns (5 of separation + 1 of clearance).
PIEZO_TYPE = "buzzer"
PIEZO_ANCHOR_PIN = "positive"
PIEZO_ROW = "e"
PIEZO_WIDTH = 6
# The piezo is drawn as a large disc centred on its anchor column, so to
# its left it covers the neighbouring components (live screen check:
# anchored at 1e it covered the button at column 7). Starting it at
# column 24 or later keeps the disc on the right edge; a cursor already
# past 24 is respected. Same rule as ULTRASONIC_MIN_COLUMN.
PIEZO_MIN_COLUMN = 24
# HC-SR04 + piezo juntos (medido en vivo en lcd-distancia): el modulo del
# sensor tambien se dibuja mucho mas ancho que sus pines. Con el sensor en
# 18d su cuerpo llegaba al disco del piezo anclado en 24e y tapaba el
# transductor derecho. Cuando ambos cuerpos grandes comparten placa, el
# sensor cede la mitad derecha y arranca en la columna 10 (su cuerpo
# termina antes del disco del piezo); un cursor ya pasado de 10 se respeta.
ULTRASONIC_MIN_COLUMN_WITH_PIEZO = 10
# Photoresistor/LDR (fixture slug "photoresistor", did 116691),
# live-verified: anchoring pin "1" at <c>e with angle 0 puts pin "2" at
# <c+1>e. Footprint 2 columns.
LDR_TYPE = "photoresistor"
LDR_ANCHOR_PIN = "1"
LDR_ROW = "e"
LDR_WIDTH = 2
# The photoresistor is also a large disc: anchored at 7e it covered the
# LED at column 5 on screen. Column 22 or later keeps it clear of blocks
# to its left; a cursor already past 22 is respected.
LDR_MIN_COLUMN = 22
# Parts whose body is a large disc: they are placed in a second pass so
# small components claim the centre/left of the board first.
LARGE_BODY_TYPES = (PIEZO_TYPE, LDR_TYPE)
# LDR divider resistor: angle 90 puts pin 2 four columns after pin 1, so
# pin 1 at c+3 lands pin 2 at c+7. Whole block advances 8 columns.
LDR_DIVIDER_OFFSET = 3
LDR_BLOCK_WIDTH = 8
# Diode on row g, angle 90 with pin "anode": live-verified that the
# cathode lands 4 columns before the anode (opposite to a resistor),
# so placing the anode at c+4 puts the cathode at c. Footprint c..c+4
# (5 columns) + 1 separation column, like a resistor block.
DIODE_WIDTH = 6
# DC motors are not placed on the board: they sit free to the right of
# it. Default free position; each extra motor shifts +120 in x so
# multiple motors do not stack on top of each other.
FREE_MOTOR_X = 560
FREE_MOTOR_Y = 60
FREE_MOTOR_STEP_X = 120
# L293D (did 112326) with enable1 at 17f, angle 180: pins span columns
# 10-17 on rows f (enable1..vs, 17 down to 10) and e (vss..enable2,
# 10 up to 17), crossing the centre gap.
L293D_START_COLUMN = 10
L293D_END_COLUMN = 17
# 9V batteries are free like motors, below them so they do not stack.
FREE_BATTERY_X = 560
FREE_BATTERY_Y = 300
FREE_BATTERY_STEP_X = 120
# LCD 16x2 (fixture slug "lcd-16x2", did 113878, type "LCD 16 x 2").
# It is NEVER mounted on the board: its body is ~25 columns wide and
# covered rows f..c, so nothing else could be built next to it. It is
# placed as a free module directly above the board (the board sits at
# x=870, y=0; y=-230 clears its top edge with the terminals facing down),
# and it consumes no columns: the rest of the board is laid out exactly
# as if the display were not in the fixture.
#
# Every free display module (LCD, 7-segment) shares one stack: they all
# sit on the same x and go upward in steps of 200, in fixture order, so
# no two bodies can overlap even when a circuit uses both kinds.
LCD_TYPE = "lcd-16x2"
FREE_MODULE_X = 870
FREE_MODULE_Y = -230
FREE_MODULE_STEP_Y = 200


class LayoutError(Exception):
    """Raised when a fixture cannot be interpreted for layout."""


def _parse_endpoint(endpoint):
    if not isinstance(endpoint, str) or "." not in endpoint:
        return None, None
    ref, pin = endpoint.split(".", 1)
    return ref, pin


def _led_resistor_pairs(components, nets):
    if nets is not None and not isinstance(nets, list):
        raise LayoutError("fixture 'nets' must be a list")
    type_by_ref = {c["ref"]: c["type"] for c in components}
    led_to_resistor = {}
    leds_without_resistor = set()
    used_resistors = set()
    for net in nets or []:
        led_refs = []
        resistor_refs = []
        for endpoint in net:
            ref, pin = _parse_endpoint(endpoint)
            if ref is None:
                continue
            if type_by_ref.get(ref) == "led" and pin == "anode":
                if ref not in led_refs:
                    led_refs.append(ref)
            elif type_by_ref.get(ref) == "resistor" and pin in ("1", "2"):
                if ref not in resistor_refs:
                    resistor_refs.append(ref)
        for led_ref in led_refs:
            if led_ref in led_to_resistor:
                continue
            resistor_ref = next(
                (r for r in resistor_refs if r not in used_resistors), None
            )
            if resistor_ref is not None:
                led_to_resistor[led_ref] = resistor_ref
                used_resistors.add(resistor_ref)
                leds_without_resistor.discard(led_ref)
            elif resistor_refs:
                leds_without_resistor.add(led_ref)
    return led_to_resistor, leds_without_resistor


def _rgb_color_resistors(components, nets):
    """Map each RGB ref to {color: resistor_ref} via `rX.2 - rgb.<color>` nets."""
    type_by_ref = {c["ref"]: c["type"] for c in components}
    mapping = {}
    used_resistors = set()
    for net in nets or []:
        rgb_endpoints = []
        resistor_refs = []
        for endpoint in net:
            ref, pin = _parse_endpoint(endpoint)
            if ref is None:
                continue
            if type_by_ref.get(ref) == RGB_TYPE and pin in RGB_RESISTOR_LAYOUT:
                rgb_endpoints.append((ref, pin))
            elif type_by_ref.get(ref) == "resistor" and pin == "2":
                if ref not in resistor_refs:
                    resistor_refs.append(ref)
        for rgb_ref, color in rgb_endpoints:
            colors = mapping.setdefault(rgb_ref, {})
            if color in colors:
                continue
            resistor_ref = next(
                (r for r in resistor_refs if r not in used_resistors), None
            )
            if resistor_ref is not None:
                colors[color] = resistor_ref
                used_resistors.add(resistor_ref)
    return mapping


def _ldr_divider_resistors(components, nets, reserved):
    """Map each LDR ref to the resistor on the same net as its pin "2".

    That resistor is the divider's middle node and must travel with the
    LDR, not as a standalone block. `reserved` are resistors already
    claimed by the LED/RGB rules.
    """
    type_by_ref = {c["ref"]: c["type"] for c in components}
    mapping = {}
    used = set(reserved)
    for component in components:
        if component["type"] != LDR_TYPE:
            continue
        ldr_ref = component["ref"]
        for net in nets or []:
            endpoints = [_parse_endpoint(endpoint) for endpoint in net]
            if not any(
                ref == ldr_ref and pin in ("2", "terminal-2")
                for ref, pin in endpoints
            ):
                continue
            resistor_ref = next(
                (
                    ref
                    for ref, _pin in endpoints
                    if ref is not None
                    and type_by_ref.get(ref) == "resistor"
                    and ref not in used
                ),
                None,
            )
            if resistor_ref is not None:
                mapping[ldr_ref] = resistor_ref
                used.add(resistor_ref)
                break
    return mapping


# Display 7 segmentos (fixture slug "siete-segmentos", did 129710): 10
# terminales y un cuerpo que taparia media placa, asi que va libre en el
# mismo apilado que el LCD (FREE_MODULE_*).
SEVEN_SEG_TYPE = "seven-segment"

# Tipos que van como modulo libre en el apilado de arriba, en el orden en
# que aparecen en la fixture.
FREE_MODULE_TYPES = (LCD_TYPE, SEVEN_SEG_TYPE)

# Integrados que van libres a la izquierda del display, a la misma altura y
# apilados hacia arriba: el 74HC595 (16 pines) y las compuertas logicas de 14
# pines (74HC86 XOR, 74HC00 NAND). Sus terminales se cablean directo, sin
# huecos de protoboard. Comparten un solo apilado en orden de fixture.
SHIFT_REGISTER_TYPE = "shift-register"
LOGIC_GATE_TYPES = ("xor-gate", "nand-gate", "flip-flop-d")
IC_STACK_TYPES = (SHIFT_REGISTER_TYPE,) + LOGIC_GATE_TYPES
FREE_SHIFT_REGISTER_X = 560
FREE_SHIFT_REGISTER_Y = -230
FREE_SHIFT_REGISTER_STEP_Y = 200

def _first_free_window(occupied_columns, width):
    """First start column whose `width` columns are all free, or None."""
    for start in range(1, MAX_COLUMN - width + 2):
        if not any(
            col in occupied_columns for col in range(start, start + width)
        ):
            return start
    return None


def plan_layout(fixture: dict) -> dict:
    if not isinstance(fixture, dict):
        raise LayoutError("fixture must be a dict")
    components = fixture.get("components")
    if not isinstance(components, list):
        raise LayoutError("fixture must have a 'components' list")
    for component in components:
        if not isinstance(component, dict) or "ref" not in component or "type" not in component:
            raise LayoutError("each component must have 'ref' and 'type'")
    seen_refs = set()
    for component in components:
        ref = component["ref"]
        if ref in seen_refs:
            raise LayoutError(f"duplicate component ref: {ref!r}")
        seen_refs.add(ref)
    nets = fixture.get("nets")
    if nets is not None and not isinstance(nets, list):
        raise LayoutError("fixture 'nets' must be a list")

    order = {c["ref"]: i for i, c in enumerate(components)}
    type_by_ref = {c["ref"]: c["type"] for c in components}
    led_to_resistor, leds_without_resistor = _led_resistor_pairs(components, nets)
    rgb_to_resistors = _rgb_color_resistors(components, nets)
    rgb_refs = [c["ref"] for c in components if c["type"] == RGB_TYPE]
    unsupported_rgb = {
        ref
        for ref in rgb_refs
        if set(rgb_to_resistors.get(ref, {})) != set(RGB_RESISTOR_LAYOUT)
    }
    # Resistors bound to an RGB (by their color net) never go through the
    # generic LED/standalone rules. For a broken RGB, leftover resistors
    # that are not LED-paired are part of the set: nothing is half-built.
    rgb_resistor_refs = {
        r for colors in rgb_to_resistors.values() for r in colors.values()
    }
    if unsupported_rgb:
        led_paired = set(led_to_resistor.values())
        for component in components:
            ref = component["ref"]
            if (
                component["type"] == "resistor"
                and ref not in led_paired
                and ref not in rgb_resistor_refs
            ):
                rgb_resistor_refs.add(ref)

    placements = {}
    unplaced = []
    for ref in rgb_refs:
        if ref in unsupported_rgb:
            unplaced.append(ref)
            unplaced.extend(
                r
                for r in rgb_to_resistors.get(ref, {}).values()
                if r not in unplaced
            )
    if unsupported_rgb:
        for ref in rgb_resistor_refs:
            if ref not in unplaced:
                unplaced.append(ref)

    # LDR divider resistors are placed with their LDR, never standalone.
    ldr_to_resistor = _ldr_divider_resistors(
        components, nets, set(led_to_resistor.values()) | rgb_resistor_refs
    )
    ldr_divider_resistors = set(ldr_to_resistor.values())

    # Displays are free modules above the board: they take no columns and
    # hide nothing, so every other part is placed normally. They share a
    # single stack (see FREE_MODULE_*) so an LCD and a 7-segment display in
    # the same circuit never land on top of each other.
    free_module_count = 0
    for component in components:
        if component["type"] not in FREE_MODULE_TYPES:
            continue
        placements[component["ref"]] = {
            "free": {
                "x": FREE_MODULE_X,
                "y": FREE_MODULE_Y - free_module_count * FREE_MODULE_STEP_Y,
                "angle": 0,
            }
        }
        free_module_count += 1

    # Los integrados no comparten apilado con los displays: van a la
    # izquierda, a la altura del primero, para que sus cables no crucen el
    # display. Varios integrados se apilan de 200 en 200.
    shift_count = 0
    for component in components:
        if component["type"] not in IC_STACK_TYPES:
            continue
        placements[component["ref"]] = {
            "free": {
                "x": FREE_SHIFT_REGISTER_X,
                "y": FREE_SHIFT_REGISTER_Y - shift_count * FREE_SHIFT_REGISTER_STEP_Y,
                "angle": 0,
            }
        }
        shift_count += 1

    # Block units: each LED with its series resistor, plus standalone
    # resistors. Ordered by first appearance of any member in the fixture.
    units = []
    paired_resistors = set(led_to_resistor.values())
    for component in components:
        ref, ctype = component["ref"], component["type"]
        if ctype == "led":
            if ref in leds_without_resistor:
                unplaced.append(ref)
                continue
            resistor = led_to_resistor.get(ref)
            members = [ref] + ([resistor] if resistor else [])
            units.append((min(order[m] for m in members), ref, resistor))
        elif (
            ctype == "resistor"
            and ref not in paired_resistors
            and ref not in rgb_resistor_refs
            and ref not in ldr_divider_resistors
        ):
            units.append((order[ref], None, ref))
    units.sort(key=lambda unit: unit[0])

    occupied_columns = set()
    has_piezo = any(component["type"] == PIEZO_TYPE for component in components)

    def skip_occupied(start, footprint_width):
        while any(
            col in occupied_columns
            for col in range(start, start + footprint_width)
        ):
            start += 1
        return start

    next_column = 1
    next_column_lower = 1

    for _, led_ref, resistor_ref in units:
        used_lower = False
        if next_column > LAST_BLOCK_START:
            # Standalone resistors (no LED) can spill to the lower half of
            # the board: the 7-segment needs seven of them and only four
            # blocks fit above the gap. LED blocks stay above the gap.
            if led_ref or next_column_lower > LAST_BLOCK_START:
                if resistor_ref:
                    unplaced.append(resistor_ref)
                if led_ref:
                    unplaced.append(led_ref)
                continue
            column = next_column_lower
            next_column_lower += BLOCK_WIDTH
            used_lower = True
        else:
            column = next_column
            next_column += BLOCK_WIDTH
        occupied_columns.update(range(column, column + BLOCK_WIDTH))
        if resistor_ref:
            row = "e" if used_lower else "g"
            placements[resistor_ref] = {"at": f"{column}{row}", "pin": "1", "angle": 90}
        if led_ref:
            placements[led_ref] = {"at": f"{column + 4}i", "pin": "anode", "angle": 180}

    # Pushbuttons, 3-pin parts and the HC-SR04, after the LED/resistor
    # blocks. All share the next_column cursor (LED block: 6, pushbutton:
    # 1, 3-pin: 4, ultrasonic: 5, diode: 6), so no two blocks share a start
    # column or overlap in range. DC motors are free and consume no columns.
    # Large-body parts (piezo, LDR) are placed in a second pass: their
    # discs are drawn centred on the anchor and cover neighbours to the
    # left, so small parts claim the centre/left first and the disc ends
    # up on the right edge.
    def place_piezo(ref):
        nonlocal next_column
        start = skip_occupied(
            max(next_column, PIEZO_MIN_COLUMN), PIEZO_WIDTH
        )
        if start + PIEZO_WIDTH - 1 > MAX_COLUMN:
            unplaced.append(ref)
        else:
            placements[ref] = {
                "at": f"{start}{PIEZO_ROW}",
                "pin": PIEZO_ANCHOR_PIN,
                "angle": 0,
            }
            occupied_columns.update(range(start, start + PIEZO_WIDTH))
            next_column = start + PIEZO_WIDTH

    def place_ldr(ref):
        nonlocal next_column
        divider_ref = ldr_to_resistor.get(ref)
        width = LDR_BLOCK_WIDTH if divider_ref else LDR_WIDTH
        start = skip_occupied(max(next_column, LDR_MIN_COLUMN), width)
        if start + width - 1 > MAX_COLUMN:
            unplaced.append(ref)
            if divider_ref is not None:
                unplaced.append(divider_ref)
        else:
            placements[ref] = {
                "at": f"{start}{LDR_ROW}",
                "pin": LDR_ANCHOR_PIN,
                "angle": 0,
            }
            occupied_columns.update(range(start, start + LDR_WIDTH))
            if divider_ref is not None:
                placements[divider_ref] = {
                    "at": f"{start + LDR_DIVIDER_OFFSET}{LDR_ROW}",
                    "pin": "1",
                    "angle": 90,
                }
                occupied_columns.update(
                    range(start, start + LDR_BLOCK_WIDTH)
                )
            next_column = start + width

    motor_count = 0
    battery_count = 0
    for component in components:
        ref, ctype = component["ref"], component["type"]
        if ctype in ("arduino-uno", LCD_TYPE) or ref in placements:
            continue
        if ctype in LARGE_BODY_TYPES:
            continue
        if ctype == RGB_TYPE:
            if ref in unsupported_rgb:
                continue
            start = skip_occupied(next_column, RGB_WIDTH)
            if start + RGB_WIDTH - 1 > MAX_COLUMN:
                # Cursor already passed the board or the tail does not
                # fit: backfill the first free RGB window so placement
                # does not depend on component order.
                start = _first_free_window(occupied_columns, RGB_WIDTH)
            if start is None:
                unplaced.append(ref)
                for resistor_ref in rgb_to_resistors[ref].values():
                    if resistor_ref not in unplaced:
                        unplaced.append(resistor_ref)
                continue
            base = start + 4
            placements[ref] = {"at": f"{base}i", "pin": "red", "angle": 0}
            for color, (offset, row) in RGB_RESISTOR_LAYOUT.items():
                resistor_ref = rgb_to_resistors[ref][color]
                placements[resistor_ref] = {
                    "at": f"{base + offset}{row}",
                    "pin": "1",
                    "angle": 90,
                }
            # Registers B..B+3 (and the resistor columns before them):
            # the next block starts after the last RGB pin. A backfilled
            # RGB never rewinds the shared cursor.
            occupied_columns.update(range(base - 4, base + 4))
            next_column = max(next_column, base + 4)
        elif ctype == "l293d":
            l293d_columns = set(range(L293D_START_COLUMN, L293D_END_COLUMN + 1))
            if l293d_columns & occupied_columns:
                unplaced.append(ref)
            else:
                placements[ref] = {
                    "at": f"{L293D_END_COLUMN}f",
                    "pin": "enable1",
                    "angle": 180,
                }
                occupied_columns.update(l293d_columns)
        elif ctype == "pushbutton":
            next_column = skip_occupied(next_column, 1)
            if next_column > MAX_COLUMN:
                unplaced.append(ref)
            else:
                placements[ref] = {"at": f"{next_column}f", "pin": "1", "angle": 0}
                occupied_columns.add(next_column)
                next_column += 1
        elif ctype in THREE_PIN_FIRST_PIN:
            next_column = skip_occupied(next_column, THREE_PIN_PINS)
            if next_column + THREE_PIN_PINS - 1 > MAX_COLUMN:
                unplaced.append(ref)
            else:
                placements[ref] = {
                    "at": f"{next_column}c",
                    "pin": THREE_PIN_FIRST_PIN[ctype],
                    "angle": 0,
                }
                occupied_columns.update(
                    range(next_column, next_column + THREE_PIN_PINS)
                )
                next_column += THREE_PIN_WIDTH
        elif ctype == "ultrasonic-hcsr04":
            min_column = (
                ULTRASONIC_MIN_COLUMN_WITH_PIEZO
                if has_piezo
                else ULTRASONIC_MIN_COLUMN
            )
            start = skip_occupied(max(next_column, min_column), ULTRASONIC_PINS)
            if start + ULTRASONIC_PINS - 1 > MAX_COLUMN:
                unplaced.append(ref)
            else:
                placements[ref] = {
                    "at": f"{start}d",
                    "pin": "vcc",
                    "angle": 0,
                }
                occupied_columns.update(
                    range(start, start + ULTRASONIC_PINS)
                )
                next_column = start + ULTRASONIC_WIDTH
        elif ctype == "diode":
            next_column = skip_occupied(next_column, 5)
            if next_column + 4 > MAX_COLUMN:
                unplaced.append(ref)
            else:
                placements[ref] = {
                    "at": f"{next_column + 4}g",
                    "pin": "anode",
                    "angle": 90,
                }
                occupied_columns.update(range(next_column, next_column + 5))
                next_column += DIODE_WIDTH
        elif ctype == "dc-motor":
            placements[ref] = {
                "free": {
                    "x": FREE_MOTOR_X + motor_count * FREE_MOTOR_STEP_X,
                    "y": FREE_MOTOR_Y,
                }
            }
            motor_count += 1
        elif ctype == "battery-9v":
            placements[ref] = {
                "free": {
                    "x": FREE_BATTERY_X + battery_count * FREE_BATTERY_STEP_X,
                    "y": FREE_BATTERY_Y,
                }
            }
            battery_count += 1
        elif ctype not in ("led", "resistor"):
            unplaced.append(ref)

    # Second pass: large-body parts, in fixture order, once every other
    # type has claimed its columns.
    for component in components:
        ref, ctype = component["ref"], component["type"]
        if ref in placements:
            continue
        if ctype == PIEZO_TYPE:
            place_piezo(ref)
        elif ctype == LDR_TYPE:
            place_ldr(ref)

    unplaced.sort(key=lambda ref: order[ref])
    return {"placements": placements, "unplaced": unplaced}
