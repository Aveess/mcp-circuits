# mcp-circuits

Servidor **MCP** para manejar el editor de Tinkercad Circuits desde un agente
(Claude Desktop, Cursor, OpenCode…) y la librería que decide **dónde** va cada
pieza y **verifica** que el circuito quedó como se pidió.

> **No afiliado con Autodesk.** Tinkercad es una marca de Autodesk. Este
> proyecto es personal y no oficial: maneja el editor web con un navegador
> automatizado porque no existe una API pública de Circuits.

## Qué hay aquí

| Paquete | Qué es | Lo necesitas para |
|---|---|---|
| [`packages/bridge`](packages/bridge) | El servidor MCP (50 tools): coloca piezas, cablea, pone el sketch, simula, lee el serial, saca capturas y mide fidelidad | Empezar. Es el que habla con Tinkercad |
| [`packages/brain`](packages/brain) | Librería de layout y verificación: elige huecos y placas, traduce la fixture a la llamada del puente, reconstruye el netlist, compara por equivalencia, valida el oráculo serial | Circuitos densos (integrados, varias placas, muchos cables) |

El puente funciona solo. El cerebro no: llama al puente.

## Arranque rápido

Requisitos: **Python 3.11+**, `git`, ~200 MB de disco para Chromium y **tu
cuenta de Tinkercad** (el navegador tiene que entrar una vez).

```bash
git clone https://github.com/Aveess/mcp-circuits.git
cd mcp-circuits
./setup.sh                      # venv + dependencias + Chromium
.venv/bin/python -m src.cli.login_cli   # una sola vez, con TU cuenta
```

`setup.sh` deja el puente en `.venv` y el cerebro instalado en modo editable.
En Windows: `.\setup.ps1`.

El login abre Chrome en la página de Tinkercad; al llegar al dashboard guarda
la sesión en `packages/bridge/.tinkercad_profile/`. **Esa carpeta es tu
contraseña**: no se comparte, no se versiona, no se pasa por chat.

## Conectarlo al agente

La ruta tiene que ser **absoluta**. El puente vive en `packages/bridge`.

OpenCode (`opencode.jsonc`):

```jsonc
"mcp": { "servers": { "tinkercad-circuits": {
  "type": "local",
  "command": ["/RUTA/A/mcp-circuits/.venv/bin/python", "-m", "src.main"]
}}}
```

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "tinkercad-circuits": {
      "command": "/RUTA/A/mcp-circuits/.venv/bin/python",
      "args": ["-m", "src.main"],
      "cwd": "/RUTA/A/mcp-circuits/packages/bridge"
    }
  }
}
```

Windows: `.venv\Scripts\python.exe` y rutas con doble barra invertida.

## Comprobar que quedó

```bash
.venv/bin/python packages/bridge/examples/check_mcp_stdio.py
# handshake: tinkercad-circuits 1.1.0 / tools: 50 / authenticated: True / OK
```

Suites:

```bash
cd packages/bridge && ../../.venv/bin/python -m unittest discover tests   # 364 tests
cd packages/brain  && ../../.venv/bin/python -m pytest -q                 # layout + verificación
```

## Antes de pedirle un circuito al agente

Dos documentos del puente son obligatorios, no decorativos:

- [`packages/bridge/AGENTS.md`](packages/bridge/AGENTS.md) — la fuente es la
  pieza *Power Supply*, rojo/negro no se usan para señales, sin Arduino salvo
  que haya programa, cables en ángulo recto.
- [`packages/bridge/RESTRICCIONES.md`](packages/bridge/RESTRICCIONES.md) — qué
  mide el editor y qué no, la geometría real de las placas y las trampas ya
  pagadas.

Sin esas dos, el circuito se ve bien en la foto y no funciona en la simulación.

## Flujo completo (opcional)

El cerebro trae un ejemplo punta a punta: una fixture describe piezas, nets y
layout; el cerebro la convierte en la llamada del puente, reconstruye el
netlist del circuito guardado, lo compara net por net y escribe un reporte.

```bash
.venv/bin/python packages/brain/scripts/demo_build.py blink-basico
```

Si el puente no está en `packages/bridge`, `TINKERCAD_BRIDGE=/ruta` manda.

## Lo que no se versiona

`.venv/`, `packages/bridge/.tinkercad_profile/` (credencial), `screenshots/`,
`.env`, y nada que salga de `~/jarvis_data/`.

## Créditos

| Repo | Licencia | Qué aportó |
|---|---|---|
| [`ezhil-kumaran/Tinkercad-mcp`](https://github.com/ezhil-kumaran/Tinkercad-mcp) | MIT | **Base directa del puente**: esqueleto del servidor MCP, capa de Playwright, catálogo, editor de código y casi todas las tools |
| [`sethski/tinkercad-mcp-server`](https://github.com/sethski/tinkercad-mcp-server) | MIT | Proyecto anterior (Node/TypeScript) del que sale la idea: manejar el editor real porque no hay API |

MIT. Ver [`LICENSE`](LICENSE).

## Estado y honestidad

Proyecto personal, sin garantías. No hay telemetría: si lo usas, cuéntalo en un
issue. Un build a la vez (un navegador, una sesión): dos en paralelo se pisan.
Si Tinkercad cambia el editor, algo se rompe — es el costo de no tener API.
