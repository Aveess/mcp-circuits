# Tinkercad Circuits MCP Server (Python)

> Proyecto **no oficial**, sin relación con Autodesk. «Tinkercad» es marca de
> Autodesk y aquí solo se usa para decir qué editor automatiza. Úsalo con tu
> propia cuenta y a tu ritmo: un build a la vez.

A complete **Model Context Protocol (MCP)** server for automating **Autodesk Tinkercad Circuits** using Python, Playwright, and the official Python MCP SDK.

This server enables AI assistants (such as Claude Desktop, Cursor, Antigravity, or custom agents) to programmatically design, wire, code, simulate, and debug electronic circuits directly inside the Tinkercad web interface.

---

## 🤖 AI Agent Quick Reference & Prompts

* **[Agent Instructions (`instructions.md`)](instructions.md)** — Core tool usage rules, canonical component & pin names, and best practices.
* **[Agent Guide (`AGENT_GUIDE.md`)](AGENT_GUIDE.md)** — Full 1-call `tinkercad_build_circuit` examples, pinout references, and conversion formulas.
* **[Reglas para agentes (`AGENTS.md`)](AGENTS.md)** — Las reglas obligatorias al construir: alimentacion por fuente y rieles, verificacion real y errores ya pagados.
* **[Restricciones (`RESTRICCIONES.md`)](RESTRICCIONES.md)** — Lo que el editor mide y lo que no, geometria de las placas y limites duros. Para personas.

---

## 🚀 Key Features

* **Authentication & Session Persistence:**
  * One-time login via interactive Chrome window or credentials.
  * Preserves cookies, login tokens, and session state locally in `.tinkercad_profile/`.
  * Support for Autodesk SSO, Google Sign-in, and Tinkercad Classrooms / Nicknames.
* **Performance & Telemetry Route Blocking:**
  * Automatically intercepts and blocks heavy analytics, tracking, and telemetry network calls (Segment, Hotjar, Google Analytics, Optimizely, Datadog) to dramatically accelerate Tinkercad WebGL initialization and reduce CPU/memory load.
  * Bounded evaluation timeouts (12s) with instant SVG DOM fallbacks to eliminate long browser context hangs.
* **UI Pointer Interception Protection:**
  * Proactively collapses the visual Blocks Code Drawer upon circuit creation, opening, and before canvas interactions.
  * Automatically detects transparent Blockly canvas/overlay click interception and ensures seamless placement and wiring.
* **Collision-Avoidance Auto-Layout Engine:**
  * Prevents component stacking at default origin coordinates `(161, -76)`.
  * Automatically separates microcontrollers, breadboards, sensors, actuators, and passives into distinct, non-overlapping canvas zones with safe clearance ($\ge 140\text{px}$) so terminal hitboxes never collide.
* **Bi-directional Pin Alias Normalization:**
  * Seamlessly resolves internal model pin names (`pos`, `neg`) and visible SVG DOM labels (`Vcc`, `GND`, `Trigger`, `Echo`) for HC-SR04 ultrasonic sensors and piezos.
* **Circuit Design Management:**
  * List all existing circuits in your account with titles, IDs, and thumbnail URLs.
  * Open any circuit directly in the editor.
  * Create new circuit designs and rename them.
  * Capture workspace screenshots for visual multimodal inspection.
* **Component Placement & Property Control:**
  * Built-in component catalog (Arduino Uno R3, Micro:bit, Breadboard, Resistors, LEDs, RGB LEDs, Sensors, Motors, LCDs, etc.).
  * Place components onto the canvas at precise or auto-distributed coordinates.
  * Remove components from the workplane.
  * Configure component attributes (e.g., resistance `220 Ω`, LED color `Green`, capacitor values).
* **Pin-to-Pin Wiring:**
  * Route wires between component terminals/pins with custom wire colors (red, black, green, blue, yellow, etc.) and wire styles.
  * Delete wires.
* **Arduino Code Editor:**
  * Read existing sketch code.
  * Automatically switch from Blocks mode to C++ Text mode (handles confirmation dialogs).
  * Inject custom Arduino sketches with `setup()` and `loop()`.
* **Simulation & Diagnostics:**
  * Start and stop the in-browser AVR simulator.
  * Monitor simulation state, elapsed time, and error notifications.
* **Serial Monitor:**
  * Open the Serial Monitor panel.
  * Read output streams printed via `Serial.print()` / `Serial.println()`.
  * Send input strings and commands to the simulated Arduino.
  * Clear the Serial Monitor log.

---

## 📦 Project Structure

```
Tinkercad-mcp/
├── .venv/                         # Python virtual environment
├── .tinkercad_profile/            # Persistent browser session & cookies (gitignored)
├── screenshots/                   # Workspace screenshots captured by tools
├── requirements.txt               # pip dependencies
├── pyproject.toml                 # Package definition & CLI entry points
├── src/
│   ├── config.py                  # Environment settings, timeouts, and URLs
│   ├── main.py                    # Stdio MCP server runner
│   ├── server.py                  # MCPServer instance and tool definitions
│   ├── browser/
│   │   ├── browser_manager.py     # Playwright persistent context & page lifecycle
│   │   └── selectors.py           # Robust DOM selectors for Tinkercad Circuits
│   ├── catalog/
│   │   └── components_catalog.py  # Electronic parts, pinouts, and default properties
│   ├── services/
│   │   ├── auth_service.py        # Login, signup, logout, auth status
│   │   ├── circuits_service.py    # List, open, create, rename circuits
│   │   ├── components_service.py  # Place, remove, configure components
│   │   ├── wiring_service.py      # Route wires between terminals
│   │   ├── code_service.py        # Read and inject Arduino C++ sketch code
│   │   ├── simulation_service.py  # Start, stop, and monitor simulator
│   │   ├── serial_service.py      # Serial monitor read, send, clear
│   │   └── composite_service.py   # High-level build_circuit workflow
│   └── cli/
│       ├── login_cli.py           # Interactive browser login helper
│       └── list_tools_cli.py      # Command to list and verify all MCP tools
└── tests/
    └── test_tools.py              # Unit tests for tools, catalog, and config
```

---

## 🛠️ Setup Instructions

### 1. Prerequisites
* **Python 3.10+** (Python 3.12 recommended)
* **pip** and **venv**

### 2. Virtual Environment & Dependencies
If not already created:
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Install Playwright Chromium browser
playwright install chromium
```

### 3. One-Time Authentication
Run the interactive login command to sign into your Tinkercad / Autodesk account:
```bash
python -m src.cli.login_cli
```
* A Google Chrome browser window will open at `https://www.tinkercad.com/login`.
* Log in with your Autodesk ID, Google account, or student nickname.
* Once you land on your Tinkercad dashboard, the CLI will automatically detect your login, save your session cookies in `.tinkercad_profile/`, and exit.

### 4. Verify Registered Tools
To inspect the 50 registered MCP tools:
```bash
python -m src.cli.list_tools_cli
```

### 5. Run Unit Tests
```bash
python -m unittest discover tests
```

### 6. Check the MCP Protocol Itself
The unit tests call the service layer directly. This script spawns the real
server over stdio, performs the MCP handshake, lists the tools and calls one
(no circuit is modified):
```bash
python examples/check_mcp_stdio.py
```
Expected output: `handshake: tinkercad-circuits 1.1.0`, `tools: 50`, `authenticated: True`, `OK`.

### 7. Run End-to-End Example (Optional)
To programmatically build, wire, program, and simulate a complete temperature-controlled servo circuit:
```bash
python examples/build_temperature_circuit.py
```

---

## 🤝 Cómo lo usa otra persona (clon, zip o copia directa)

El repo es público, así que hay tres formas de conseguirlo y las tres dan lo
mismo:

```bash
git clone https://github.com/Aveess/tinkercad-mcp-bridge.git   # con historial
git clone --depth 1 https://github.com/Aveess/tinkercad-mcp-bridge.git  # sin historial, más rápido
```

- **Descargar el ZIP**: botón *Code → Download ZIP* en GitHub, o
  `https://github.com/Aveess/tinkercad-mcp-bridge/archive/refs/heads/main.zip`.
  El ZIP no trae `.git`, así que no hay forma de que suban cambios al original.
- **`git archive`** desde una copia local: deja fuera `.git`, `.venv`,
  `.tinkercad_profile` y `screenshots`; son ~270 KB.

> **Tu cuenta, no la mía.** El servidor no tiene cuenta propia: maneja **tu**
> navegador con **tu** sesión de Tinkercad. Los diseños que construyas van a tu
> cuenta. No copies ni pidas un `.tinkercad_profile/` ajeno: sería operar
> sobre la cuenta de esa persona, y quien te lo diera te estaría dando su
> contraseña. Ese perfil está en `.gitignore`: no viaja en el repo ni en el
> ZIP.
>
> **Reglas del juego.** Si algo falla, abre un issue con el mensaje de error y
> lo que estabas construyendo. Un build a la vez (un navegador, una sesión):
> dos en paralelo se pisan.

### Puesta en marcha (5 pasos)

1. Clonar o descomprimir el zip en una carpeta propia. Necesitas Python 3.10 o más.
2. Crear el entorno e instalar:
   ```bash
   cd tinkercad-mcp-bridge
   python -m venv .venv
   source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   playwright install chromium
   ```
3. Entrar a Tinkercad con **su** cuenta (abre Chrome; la sesión queda en su
   `.tinkercad_profile/`, que no se comparte):
   ```bash
   python -m src.cli.login_cli
   ```
4. Conectar su cliente MCP al **python del venv**, con `cwd` en esa carpeta (ver
   "Connecting to MCP Clients" aquí abajo). En OpenCode:
   ```jsonc
   "mcp": { "servers": { "tinkercad-circuits": {
     "type": "local",
     "command": ["/ruta/a/tinkercad-mcp-bridge/.venv/bin/python", "-m", "src.main"]
   }}}
   ```
5. Comprobar que quedó bien, antes de pedirle nada al agente:
   ```bash
   python examples/check_mcp_stdio.py
   # handshake: tinkercad-circuits 1.1.0 / tools: 50 / authenticated: True / OK
   ```

### Lo primero que tiene que leer

- [AGENTS.md](./AGENTS.md) — las reglas obligatorias al construir: la fuente es
  la pieza *Power Supply*, rojo/negro no se usan para señales, sin Arduino
  salvo que haya programa, y los cables van en ángulo recto.
- [RESTRICCIONES.md](./RESTRICCIONES.md) — qué mide el editor y qué no, la
  geometría real de las placas y las trampas ya pagadas.

Sin esas dos, el circuito se ve bien en la foto y no funciona en la
simulación. Es el error que más caro sale.

### Lo que NO se le manda nunca

`.venv/` (pesa y se rompe entre máquinas), `.tinkercad_profile/` (es su
contraseña), `screenshots/` (no aporta) y, si el zip se genera desde el repo,
tampoco `.git/`. `git archive` ya deja todo eso fuera; el zip de entrega son
~270 KB.

### Si además quiere el flujo completo

Con el MCP solo, el agente construye a partir de un plan JSON (piezas, cables
por hueco y `boards`). El que **genera** esos planes desde una fixture es otro
repo público, [`Aveess/tinkercad-brain`](https://github.com/Aveess/tinkercad-brain),
del mismo autor. Se clona igual y apunta al puente con `TINKERCAD_BRIDGE`.

## 🔌 Connecting to MCP Clients

### A. Claude Desktop
Add this to your `claude_desktop_config.json` (`%APPDATA%\Claude\claude_desktop_config.json` on Windows, or `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "tinkercad-circuits": {
      "command": "python",
      "args": ["-m", "src.main"],
      "cwd": "/path/to/Tinkercad-mcp"
    }
  }
}
```

> **Windows Note**: Use absolute path to the venv Python executable, for example:
> `"command": "C:\\path\\to\\Tinkercad-mcp\\.venv\\Scripts\\python.exe"` and `"cwd": "C:\\path\\to\\Tinkercad-mcp"`.
> **macOS / Linux Note**: Use `"command": "/path/to/Tinkercad-mcp/.venv/bin/python"` and `"cwd": "/path/to/Tinkercad-mcp"`.

### B. Cursor (.cursor/mcp.json)
Create or edit `.cursor/mcp.json` in your project workspace:

```json
{
  "mcpServers": {
    "tinkercad": {
      "command": "python",
      "args": ["-m", "src.main"],
      "cwd": "/path/to/Tinkercad-mcp"
    }
  }
}
```

### C. Testing with MCP Inspector
You can test the server interactively via the official MCP Inspector:
```bash
npx @modelcontextprotocol/inspector .venv/Scripts/python.exe -m src.main
```

---

## ⚠️ Known Limitations & Operational Notes

Read this before reporting a bug. These are properties of Tinkercad's editor and simulator, not of the MCP.

1. **The simulator runs slower than real time.** A freshly loaded page advances at ~0.05× real time; once settled it goes to 0.2–1× depending on circuit size (a 23-part circuit with seven logic ICs stays around 0.2–1×). Consequence: a sketch that needs 20 s of simulated time can take **minutes** of wall clock. Never declare a circuit dead after a fixed `sleep`: start the simulation, read the serial monitor, and poll until the expected marks appear, with a time cap.
2. **Opening a design sometimes leaves the editor unmounted.** The page stays in "Initializing" and there are zero components in the model. `tinkercad_open_circuit` now **reloads up to 3 times by itself** before giving up (`mount_attempts` in the response says how many it needed). If it still fails, the tools report it explicitly (`success: false`, `reason: "editor_not_mounted"`, plus `editor_state`) instead of returning an empty circuit. That is a Tinkercad server hiccup, not a wiring error.
3. **One browser, one session.** The persistent profile (`.tinkercad_profile/`) holds a single logged-in context. Do not run two builds in parallel against the same account: they fight over the same page. Wait for one to finish.
4. **The login is per machine and per person.** `python -m src.cli.login_cli` stores that user's Autodesk session in `.tinkercad_profile/`. Treat that folder as a password: whoever copies it is logged in as its owner until the session expires. It is gitignored, created with mode `700`, and the cookie file itself is `600`, so other OS users cannot read it. Never commit it, zip it, or send it to someone else — and never run the server with a colleague's profile: every tool would operate on *their* account. Each person logs in on their own machine and nothing about that account leaves it (the server only talks to `tinkercad.com` and its API, no third-party endpoint).
5. **Saving code is debounced.** `tinkercad_set_code` waits for the ShareJS flush and re-reads the editor to confirm. ShareJS can leave a residual pending op that stays at 1 forever; it does not block saving, and a page reload returns it to 0.
6. **Component names are not identities.** The editor renames duplicates on rebuild (`r2` becomes `r21`). Always use the names returned by the build (`placed[ref].name`) instead of assuming your refs survived.
7. **Display/part orientation matters.** A 7-segment display only fits a large breadboard at 180°, which swaps its pins (`a`↔`d`, `b`↔`e`, `c`↔`f`). Electrically it can be perfect and still show mirror-image digits: verify orientation with a screenshot, not only with the netlist.

## 📚 Complete Tools Reference (50 Tools)

### 1. Authentication & Session
* `tinkercad_auth_status()`: Checks if current session is authenticated.
* `tinkercad_login(username, password, interactive, timeout_seconds)`: Performs interactive or automated login and caches session.
* `tinkercad_open_signup(interactive)`: Opens Tinkercad account creation page.
* `tinkercad_logout()`: Logs out and clears stored session cookies.
* `tinkercad_restart_browser(headless)`: Restarts or recovers the persistent Playwright browser context using `.tinkercad_profile/` without needing to restart the MCP server process. Automatically closes stale/crashed contexts and opens a clean, connected session.

### 2. Circuit Design Management
* `tinkercad_list_circuits()`: Lists all existing circuit designs in the account (titles, IDs, URLs, thumbnails).
* `tinkercad_open_circuit(circuit_id_or_url)`: Opens an existing circuit in the editor.
* `tinkercad_create_circuit(title)`: Creates a new circuit and loads the editor.
* `tinkercad_get_circuit_info()`: Retrieves active circuit title, URL, component count, and simulation state.
* `tinkercad_inspect_circuit()`: Performs semantic circuit inspection returning structured components, pins with `connected_to` metadata, and wire connections without taking screenshots.
* `tinkercad_rename_circuit(new_title)`: Renames the currently open circuit.
* `tinkercad_take_screenshot(filename, full_page)`: Captures a PNG screenshot of the workspace.
* `tinkercad_switch_workspace_view(view)`: Switches the editor view between `'circuits'` (breadboard view), `'schematic'` (schematic diagram), and `'components'` (BOM component list).
* `tinkercad_zoom_canvas(action, steps)`: Zooms the canvas (`action` `fit` or `zoom`, `steps` how many notches) to expand the workspace or fit all components.
* `tinkercad_delete_circuit(circuit_id_or_url, circuit_id)`: Deletes a circuit design from the account (moves it to the recycle bin). Used to clean up probe/test circuits.
* `tinkercad_validate_circuit_pre_simulation()`: Performs comprehensive pre-simulation checks: verifies component integrity, checks wire endpoints, detects electrical overcurrent violations (>40 mA limits), verifies motor driver presence, and checks Arduino code mode (Text vs Blocks).

### 3. Component Management
* `tinkercad_list_available_components(category, search)`: Lists electronic components with pinouts and properties.
* `tinkercad_add_component(component_name, x, y, required_pins, min_pins)`: Places a component on canvas by exact stable identity, rejects ambiguous matches and hidden chevrons, verifies pin counts and required pins (e.g. 4-pin HC-SR04 vs 3-pin sensor), and cleans up mismatched components automatically.
* `tinkercad_remove_component(component_name, x, y)`: Deletes a component from the canvas.
* `tinkercad_set_component_property(property_name, value, unit)`: Adjusts component attributes (resistance, color, name).
* `tinkercad_set_component_property_model(component_name, property_name, value, unit)`: Sets a property directly in the editor's internal model, without selecting the part on canvas. This is the reliable path for calibrated values (a 555 resistor to `22k`, a display to `common=cathode`) and the only one that survives components being re-created by a rebuild. For magnitudes, `unit` is the setProperty **prefix** (`k`, `u`, `n`, `m`) rather than the full unit string; for other properties it is whatever the model expects (e.g. `cm`).

### 4. Wiring & Connections
* `tinkercad_connect_verified_netlist(connections, circuit_id, clear_existing, verify_each, verify_persistence)`: Verified, instance-aware netlist wiring workflow. Resolves exact instance IDs (e.g. `_269`, `_291`), normalizes pin aliases (`vcc`/`power`/`pos` -> power, `gnd`/`ground`/`neg` -> ground, `out`/`signal` -> signal, `anode`/`cathode`), scopes terminal resolution strictly to each component's SVG element, rejects power-to-ground shorts (`short_circuit=true`), same-component self-wires, direct motor connections, duplicate pairs, and suspicious mappings (`stale_terminal_mapping=true`). Wires one connection at a time with instant model verification and confirms all connections survive post-reload cloud persistence.
* `tinkercad_resolve_terminal(component, pin, component_name)`: Resolves a component terminal's exact SVG identity and canvas screen coordinates.
* `tinkercad_connect_component_pins(source_component, source_pin, target_component, target_pin, color, allow_unsafe_direct)`: Semantically connects two named component pins, enforces electrical safety by rejecting direct motor connections to MCU I/O pins (>40 mA violation), resolves coordinates via SVG transforms with fallback to internal connection API, and automatically routes via Breadboard when ground pins are exhausted.
* `tinkercad_connect_and_verify_wires(connections, circuit_id_or_url, clear_existing_wires, code, expected_wire_count, verify_after_each, reload_after_each, verify_persistence, run_schematic_erc)`: Robust multi-wire orchestration tool. Accepts connections as dicts or list-of-lists (e.g. `[["Arduino Uno R3", "D2", "Ultrasonic Distance Sensor (4-pin)", "trig", "blue"], ...]`). Dynamically discovers terminals with `getScreenCTM`, skips duplicate existing connections, optionally clears messy wiring (`clear_existing_wires=True`), optionally uploads and verifies sketch code (`code="..."`), allocates distinct Arduino GND pins, settles autosave, verifies post-reload persistence, checks expected wire counts, and executes Schematic Electrical Rule Checks (ERC) to prevent shorts and floating pins.
* `tinkercad_delete_wire_between(source_component, source_pin, target_component, target_pin)`: Finds and deletes a specific wire connecting two component pins semantically without needing canvas coordinates. Strictly removes wire via internal model and UI dispatch without blind `Delete` keypresses, preventing accidental component deletion.
* `tinkercad_clear_circuit_wires(component_name, verify_persistence)`: Clears all wires in the circuit canvas (or all wires attached to a specific component) to cleanly reset messy wiring in a single call. Uses native Playwright `path.wire-segment` UI element deletion and internal model cleanup with autosave debounce wait (4.5s) to guarantee cloud persistence across page reloads.
* `tinkercad_check_electrical_safety()`: Validates electrical ratings across all circuit wires, detecting ATmega328P 40 mA pin limit violations, inductive load isolation, missing motor drivers, and missing external battery supplies.
* `tinkercad_route_pin_via_breadboard(component, pin, rail, color, microcontroller_name)`: Routes a component pin to a Breadboard power or ground rail when microcontroller pins are full or conflicted, ensuring a common rail linked to the microcontroller.
* `tinkercad_connect_pins(from_x, from_y, to_x, to_y, color, wire_type)`: (Low-level) Connects two terminals with a colored wire by screen coordinates and verifies wire creation.
* `tinkercad_move_connection(source_component, source_pin, old_target_component, old_target_pin, new_target_component, new_target_pin, color)`: Moves an existing wire connection from an old target pin to a new target pin and verifies both removal and creation.
* `tinkercad_delete_wire(x, y)`: Clicks on a wire and deletes it with strict safety guards: verifies `elementFromPoint(x, y)` is a wire segment, aborts with `destructive_action_prevented` if targeting a component (e.g. Breadboard, Servo, PIR), and clears focus if a component is accidentally selected.

### 5. Arduino Code Editor
* `tinkercad_get_code()`: Reads the sketch source code from the live CodeMirror editor (prioritizing CodeMirror over hidden textareas).
* `tinkercad_set_code(code, ensure_text_mode, verify_persistence)`: Switches to Text mode, updates the live CodeMirror model, and verifies persistence across project reload.

### 6. Simulation Control
* `tinkercad_start_simulation(wait_seconds)`: Starts the circuit simulation and waits for active state.
* `tinkercad_stop_simulation()`: Stops the simulation.
* `tinkercad_get_simulation_status()`: Checks whether simulation is running, elapsed time, and errors.
* `tinkercad_simulate_samples(samples_ms, led_component, read_serial, lit_threshold)`: Starts the simulation and samples a visual component state (an LED by default) at the given millisecond offsets, returning on/off per sample; `samples_ms` is required. Useful as a functional oracle when the circuit has no serial output. It measures the rendered part (body pixels, `lit_threshold` default 0.12), not the model.

### 7. Serial Monitor
* `tinkercad_open_serial_monitor()`: Opens the Serial Monitor panel.
* `tinkercad_read_serial_monitor(last_n_lines)`: Reads output lines from the Serial Monitor.
* `tinkercad_send_serial_monitor(text)`: Transmits input commands to the Arduino.
* `tinkercad_clear_serial_monitor()`: Clears the Serial Monitor log.

### 8. Composite Workflows
* `tinkercad_build_circuit(title, components_json, wires_json, arduino_code, run_simulation)`: High-level tool to build, wire, program, and simulate a circuit in a single operation.
* `tinkercad_build_circuit_model(parts, wires, code, boards, clear_existing, remove_unused_uno)`: Builds a circuit by **breadboard holes** directly in the editor's internal model: every part is placed at a hole address (`b1/12e`), every wire is a hole-to-hole or pin-to-hole pair, and the tool verifies persistence and returns the real part names. This is the path used for dense circuits (74HC chips inserted in a breadboard, 7-segment displays at 180°, capacitors on a second board) where canvas clicks are not precise enough. `boards` describes the breadboards (kind `large` with did 116648 and 640 usable holes, or `small` with did 111211 and 30 columns, plus the `x`/`y`/`start` origin); parts accept a `board` index and an `angle`. `remove_unused_uno=True` deletes the Arduino the build always creates when no wire of the plan touches it, which is what a 100% hardware circuit wants (result includes `removed_uno`). Requires `parts` and `wires`, and does not create the design: open or create one first.
* `tinkercad_change_pin_and_update_code(component, component_pin, old_microcontroller_pin, new_microcontroller_pin, code_symbol, microcontroller_name, wire_color, verify_persistence)`: Atomically moves a physical wire connection to a new microcontroller pin and updates the pin number in the Arduino sketch with verified persistence.
* `tinkercad_add_servo_with_distance_control(distance_threshold, angle_when_near, angle_when_far, signal_pin)`: Adds a Micro Servo, connects signal, power (5V), and ground (GND) to Arduino, and injects distance-triggered positioning code with persistence verification.
* `tinkercad_build_robot_car(title, distance_threshold_cm, motor_driver_model, run_simulation)`: Builds an obstacle-avoiding 4-motor robot car using safe electrical architecture: Arduino Uno, 4 DC motors, L293D H-bridge motor driver, 4-pin HC-SR04 ultrasonic sensor, Breadboard Small with power/ground rails, 9V external motor supply, common ground, and verified persistent obstacle-stop Arduino code.

### 9. Schematic Analysis & Connection Verification (ERC)
* `tinkercad_get_schematic_svg(save_path, switch_to_schematic, return_to_view)`: Switches to schematic view, captures the complete standalone schematic SVG diagram (with component symbols, designators, and wire paths), and saves it to disk (`screenshots/schematic_<timestamp>.svg`).
* `tinkercad_inspect_schematic_connections()`: Traces the complete electrical netlist from the schematic and circuit model using Union-Find, grouping mutually connected pins into canonical Electrical Nets (`Net_1`, `Net_2`, etc.) and identifying unconnected pins.
* `tinkercad_verify_schematic_connections(strict)`: Performs Electrical Rule Checks (ERC) on the schematic connections to detect:
  * **Power-to-Ground Short Circuits:** Flags catastrophic direct shorts between power rails (5V, 3.3V, VIN, VCC) and ground rails (GND, GND1, GND2, GND3).
  * **Component Self-Shorts:** Flags 2-terminal devices (Piezo, LED, Resistor, Motor, Capacitor) where both pins are tied to the exact same net.
  * **Floating Power or Ground:** Flags active sensors and ICs (HC-SR04 Ultrasonic VCC/GND, PIR, TMP36, Servo, Motor Driver, LCD) left unconnected.
  * **Pin Connection Conflicts:** Flags passive devices (such as Piezo (+)) improperly bridged to 3 or more conflicting pins.
  * Provides actionable step-by-step fix recommendations for every violation.

---

## 💡 Example AI Prompts

> **"Check my Tinkercad login status, and list all my circuit designs."**

> **"Create a new circuit named 'Arduino Blink Test', add an Arduino Uno R3 and a Red LED, wire D13 to the LED anode and GND to cathode, upload the blink sketch, and start the simulation."**

> **"Read the serial monitor output from my running circuit and report the temperature readings."**

---

## 📜 Créditos y linaje

Este servidor **no se escribió desde cero**. Es un fork con cambios propios de:

| Proyecto | Licencia | Qué aporta |
|---|---|---|
| [`ezhil-kumaran/Tinkercad-mcp`](https://github.com/ezhil-kumaran/Tinkercad-mcp) | MIT | **Base directa de este repo.** El esqueleto del servidor MCP, la capa de Playwright, el catálogo de componentes, el editor de código y casi todas las 50 tools |
| [`sethski/tinkercad-mcp-server`](https://github.com/sethski/tinkercad-mcp-server) | MIT | Proyecto anterior (Node/TypeScript) del que sale la idea y el enfoque: Tinkercad no tiene API, así que se maneja el editor real con un navegador automatizado |

Lo que **sí** es de este fork, y por eso está aquí: el build por huecos de
protoboard directo en el modelo del editor (`tinkercad_build_circuit_model`),
el ruteo ortogonal por carriles con bandas y corredores, el sampler de
simulación por píxel del cuerpo de la pieza, `tinkercad_delete_circuit`, la
portabilidad a Linux y toda la documentación en español (`AGENTS.md`,
`RESTRICCIONES.md`).

Si reutilizas este repo, conserva también estos créditos y el aviso de
copyright original: la licencia MIT lo exige.

---

## 📄 License
MIT License. Ver [`LICENSE`](LICENSE).

