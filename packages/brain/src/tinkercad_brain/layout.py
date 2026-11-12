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
# LED RGB (common cathode): red pin at column B on row i, pins occupy
# B..B+3. Each series resistor is angle 90 (pin 2 lands 4 columns after
# pin 1), so pin 1 sits at a color-specific offset/row such that pin 2
# falls on its color column: red B, green B+3, blue B+2.
RGB_TYPE = "led-rgb-common-cathode"
RGB_RESISTOR_LAYOUT = {"red": (-4, "g"), "green": (-1, "h"), "blue": (-2, "j")}
# Footprint from the leftmost resistor pin (B-4) to the last RGB pin
# (B+3): 8 columns of cursor advance.
RGB_WIDTH = 8
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
        ):
            units.append((order[ref], None, ref))
    units.sort(key=lambda unit: unit[0])

    next_column = 1
    for _, led_ref, resistor_ref in units:
        if next_column > LAST_BLOCK_START:
            if resistor_ref:
                unplaced.append(resistor_ref)
            if led_ref:
                unplaced.append(led_ref)
            continue
        column = next_column
        next_column += BLOCK_WIDTH
        if resistor_ref:
            placements[resistor_ref] = {"at": f"{column}g", "pin": "1", "angle": 90}
        if led_ref:
            placements[led_ref] = {"at": f"{column + 4}i", "pin": "anode", "angle": 180}

    # Pushbuttons, 3-pin parts and the HC-SR04, after the LED/resistor
    # blocks. All share the next_column cursor (LED block: 6, pushbutton:
    # 1, 3-pin: 4, ultrasonic: 5, diode: 6), so no two blocks share a start
    # column or overlap in range. DC motors are free and consume no columns.
    motor_count = 0
    for component in components:
        ref, ctype = component["ref"], component["type"]
        if ctype == "arduino-uno" or ref in placements:
            continue
        if ctype == RGB_TYPE:
            if ref in unsupported_rgb:
                continue
            base = next_column + 4
            if base - 4 < 1 or base + 3 > MAX_COLUMN:
                unplaced.append(ref)
                for resistor_ref in rgb_to_resistors[ref].values():
                    if resistor_ref not in unplaced:
                        unplaced.append(resistor_ref)
                continue
            placements[ref] = {"at": f"{base}i", "pin": "red", "angle": 0}
            for color, (offset, row) in RGB_RESISTOR_LAYOUT.items():
                resistor_ref = rgb_to_resistors[ref][color]
                placements[resistor_ref] = {
                    "at": f"{base + offset}{row}",
                    "pin": "1",
                    "angle": 90,
                }
            # Registers B..B+3 (and the resistor columns before them):
            # the next block starts after the last RGB pin.
            next_column = base + 4
        elif ctype == "pushbutton":
            if next_column > MAX_COLUMN:
                unplaced.append(ref)
            else:
                placements[ref] = {"at": f"{next_column}f", "pin": "1", "angle": 0}
                next_column += 1
        elif ctype in THREE_PIN_FIRST_PIN:
            if next_column + THREE_PIN_PINS - 1 > MAX_COLUMN:
                unplaced.append(ref)
            else:
                placements[ref] = {
                    "at": f"{next_column}c",
                    "pin": THREE_PIN_FIRST_PIN[ctype],
                    "angle": 0,
                }
                next_column += THREE_PIN_WIDTH
        elif ctype == "ultrasonic-hcsr04":
            if next_column + ULTRASONIC_PINS - 1 > MAX_COLUMN:
                unplaced.append(ref)
            else:
                placements[ref] = {
                    "at": f"{next_column}d",
                    "pin": "vcc",
                    "angle": 0,
                }
                next_column += ULTRASONIC_WIDTH
        elif ctype == "diode":
            if next_column + 4 > MAX_COLUMN:
                unplaced.append(ref)
            else:
                placements[ref] = {
                    "at": f"{next_column + 4}g",
                    "pin": "anode",
                    "angle": 90,
                }
                next_column += DIODE_WIDTH
        elif ctype == "dc-motor":
            placements[ref] = {
                "free": {
                    "x": FREE_MOTOR_X + motor_count * FREE_MOTOR_STEP_X,
                    "y": FREE_MOTOR_Y,
                }
            }
            motor_count += 1
        elif ctype not in ("led", "resistor"):
            unplaced.append(ref)

    unplaced.sort(key=lambda ref: order[ref])
    return {"placements": placements, "unplaced": unplaced}
