# NetLab

Experiencia interactiva de seguridad informática para una muestra: el visitante cumple una misión de
"hacking" guiada (escanear la red → encontrar un servidor → explotar una vulnerabilidad → recuperar
un archivo secreto) mientras un tablero físico con LEDs anima el recorrido de las comunicaciones
sobre el cableado real.

Los comandos (`scan`, `inspect`, `connect`, `exploit`, `ls`, `read`) son **reales** contra la red y
el nodo; existe además un **modo Simulado** completo para desarrollar y ensayar sin hardware (y como
fallback en vivo).

> **¿Armás el lab desde cero?** Guía visual paso a paso (LEDs, servidores, red y config):
> **https://monoo12.github.io/CyberLab/docs/ARMADO.html**

## Componentes

| Carpeta | Qué es |
|---|---|
| `app/` | App de escritorio del visitante (Python + customtkinter): terminal, mapa de red, LEDs. |
| `firmware/` | Sketch Arduino/ESP (FastLED) que anima la tira LED por USB serial. |
| `node/` | FILE-SERVER vulnerable dockerizado (Flask + SSH) con 3 vulnerabilidades. |
| `tools/` | `led_test.py` (probar LEDs) y `build_app.py` (bundle PyInstaller). |
| `docs/` | Manual de usuario, guía de conexión de hardware y arquitectura. |

## Arranque rápido (modo Simulado, sin hardware)

```bash
python -m pip install -r requirements.txt
cp config.example.toml config.toml
python -m app.main --engine simulated
```

Se abre el menú de setup (panel visual, motor Real/Simulado, dificultad Fácil/Medio/Difícil) y luego la
misión. `F11` alterna pantalla completa; `Esc` sale de pantalla completa.

Flags útiles: `--autostart` (salta el menú, modo kiosco), `--difficulty medio`, `--free` (modo libre), `--no-visual`.

## Instalacion en Linux (scripts)

En un equipo nuevo (Debian/Ubuntu/Raspberry Pi OS), con internet la primera vez:

```bash
# PC del visitante (terminal): clona el repo, instala la app y deja un lanzador
curl -fsSL https://raw.githubusercontent.com/Monoo12/CyberLab/main/scripts/setup-terminal.sh | bash

# Equipo FILE-SERVER: instala Docker, construye y enciende el nodo + accesos ON/OFF
curl -fsSL https://raw.githubusercontent.com/Monoo12/CyberLab/main/scripts/setup-fileserver.sh | bash
```

Luego: terminal → `./run-terminal.sh` (en el **menú** elegís Simulado/Real, dificultad, Modo libre); file-server → `node/fileserver.sh on|off|reset|status`. Los flags (`--autostart`, `--engine`…) son opcionales, sobre todo para kiosco.

## Instalacion en Windows (scripts .bat)

Requisitos previos: **Python 3.11+** (python.org, con Tkinter) en la terminal; **Docker Desktop** (modo Linux containers) en el file-server.

```bat
rem PC del visitante (terminal): crea el venv e instala la app
scripts\setup-terminal.bat

rem Equipo FILE-SERVER: construye, levanta y VERIFICA el nodo
scripts\setup-fileserver.bat
```

Luego: terminal → `run-terminal.bat` (doble clic); file-server → `node\fileserver.bat on|off|reset|status|logs`. Para modo real: instalá **nmap con Npcap** y corré la app como administrador (el `scan` lo necesita).

## Modo Real (en la red del laboratorio)

1. Levantar el nodo en el equipo FILE-SERVER: `cd node && docker compose up -d --build`.
2. Ajustar `config.toml` (IPs, `[serial].port`, credenciales — deben coincidir con las del nodo).
3. `nmap` instalado en la PC de la muestra (para `scan`/`inspect`).
4. `python -m app.main --engine real`.

Detalle completo (credenciales que deben coincidir, pre-flight, troubleshooting): [docs/DESPLIEGUE-REAL.md](docs/DESPLIEGUE-REAL.md).

## Empaquetado portable (cualquier PC, Windows o Linux)

```bash
python -m pip install -r requirements-dev.txt
python tools/build_app.py           # genera dist/NetLab/ (correr en cada SO)
```

`config.toml` queda **externo y editable** junto al ejecutable. PyInstaller no cross-compila: generar
un bundle en Windows y otro en Linux.

## Documentación

- **[Guía visual de armado desde 0](https://monoo12.github.io/CyberLab/docs/ARMADO.html)** — LEDs + servidores + red + config, paso a paso, renderizada en GitHub Pages. Fuente: [docs/ARMADO.html](docs/ARMADO.html).
- [docs/MANUAL-USUARIO.md](docs/MANUAL-USUARIO.md) — operar la estación en la muestra.
- [docs/GUIA-HARDWARE.md](docs/GUIA-HARDWARE.md) — conectar la tira LED, el micro y los nodos.
- [docs/DESPLIEGUE-REAL.md](docs/DESPLIEGUE-REAL.md) — pasar a modo real (nodo, credenciales, checklist).
- [docs/RED-ROUTER.md](docs/RED-ROUTER.md) — configurar el router TP-Link AX3000 y los switches.
- [docs/LEDS.md](docs/LEDS.md) — qué comando enciende qué segmento de LED (para el firmware).
- [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) — módulos, protocolo serial, Docker vs PyInstaller.
- [docs/CONTEXTO-IA.md](docs/CONTEXTO-IA.md) — contexto completo del proyecto (foco en el circuito) para pasarle a otra IA y pedir recomendaciones.

> El nodo es **inseguro por diseño** (vulnerable a propósito). Usarlo solo en la red aislada del
> laboratorio, nunca en producción ni expuesto a internet.
