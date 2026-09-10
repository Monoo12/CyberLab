# Cyber Lab

Experiencia interactiva de ciberseguridad para una muestra: el visitante cumple una misión de
"hacking" guiada (escanear la red → encontrar un servidor → explotar una vulnerabilidad → recuperar
un archivo secreto) mientras un tablero físico con LEDs anima el recorrido de las comunicaciones
sobre el cableado real.

Los comandos (`scan`, `inspect`, `connect`, `exploit`, `ls`, `read`) son **reales** contra la red y
el nodo; existe además un **modo Simulado** completo para desarrollar y ensayar sin hardware (y como
fallback en vivo).

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

Flags útiles: `--autostart` (salta el menú, modo kiosco), `--difficulty medio`, `--no-visual`.

## Modo Real (en la red del laboratorio)

1. Levantar el nodo en el equipo FILE-SERVER: `cd node && docker compose up -d --build`.
2. Ajustar `config.toml` (IPs, `[serial].port`, credenciales — deben coincidir con las del nodo).
3. `nmap` instalado en la PC de la muestra (para `scan`/`inspect`).
4. `python -m app.main --engine real`.

## Empaquetado portable (cualquier PC, Windows o Linux)

```bash
python -m pip install -r requirements-dev.txt
python tools/build_app.py           # genera dist/CyberLab/ (correr en cada SO)
```

`config.toml` queda **externo y editable** junto al ejecutable. PyInstaller no cross-compila: generar
un bundle en Windows y otro en Linux.

## Documentación

- [docs/MANUAL-USUARIO.md](docs/MANUAL-USUARIO.md) — operar la estación en la muestra.
- [docs/GUIA-HARDWARE.md](docs/GUIA-HARDWARE.md) — conectar la tira LED, el micro y los nodos.
- [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) — módulos, protocolo serial, Docker vs PyInstaller.

> El nodo es **inseguro por diseño** (vulnerable a propósito). Usarlo solo en la red aislada del
> laboratorio, nunca en producción ni expuesto a internet.
