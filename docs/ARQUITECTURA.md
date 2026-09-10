# Arquitectura

Doc técnica breve: mapa de módulos, la interfaz de backend, el protocolo serial, cómo extender, y la
justificación de **Docker (nodo)** vs **PyInstaller (app)**.

## Mapa de módulos

```
app/
  main.py            entrypoint (carga config -> MissionApp)
  config.py          carga/valida config.toml (tomllib) + overrides CLI; base_dir consciente de PyInstaller
  backend/
    base.py          NetworkBackend (ABC) + connect() (navegador real) comun
    simulated.py     SimulatedBackend  (respuestas guionadas + sleeps)
    real.py          RealBackend       (nmap, paramiko SSH, exploits)
    browser.py       apertura del navegador real en modo app (multiplataforma)
    models.py        dataclasses (Host, PortResult, ExploitResult, ...)
  exploits/          html_leak.py / sqli.py / bruteforce.py   (3 metodos, usados por RealBackend)
  leds/
    controller.py    LedController (serial; degrada a modo log sin dispositivo)
    segments.py      mapeo enlace logico -> segmento LED (espejo del firmware)
  ui/
    app.py           MissionApp (root customtkinter; vistas setup/mision/espera)
    setup_menu.py    3 toggles + Start
    terminal.py      TerminalPanel (typewriter, input, tags de color)
    netmap.py        NetworkMapPanel (Canvas; anima nodos/tramos)
    matrix.py        MatrixRain (pantalla de espera)
    theme.py         paleta y fuentes
  mission/
    flow.py          MissionController (maquina de estados, hilos, timers, pistas)
    commands.py      parser + lista blanca (regex) + validacion de IP
    script.py        todo el texto visible (espanol), ASCII art, pistas
firmware/cyberlab_leds/cyberlab_leds.ino   FastLED multi-pin + parser serial
node/                el FILE-SERVER vulnerable (Docker: Flask + SSH)
tools/               led_test.py, build_app.py
```

## Principio central: orquestación en la app, no en el backend

Los backends (`simulated`/`real`) son **puros de red/datos**: `scan/inspect/exploit/ls/read` devuelven
dataclasses y nada más. La sincronía visual (terminal + mapa + LEDs + tiempos) vive en el
`MissionController`. Así el **show es idéntico** corra el motor Real o el Simulado, y confiable en vivo:
la misma app que ejecuta la acción le avisa al micro qué tramo animar (no depende de sniffing).

### Interfaz `NetworkBackend`
Terminal y mapa hablan siempre con esta interfaz sin saber cuál corre atrás (patrón Strategy):

```python
class NetworkBackend(ABC):
    def scan() -> ScanResult
    def inspect(ip) -> InspectResult
    def exploit(method) -> ExploitResult      # "leak" | "sqli" | "hydra"
    def ls(path) -> LsResult
    def read(path) -> ReadResult
    def connect(ip, port)                      # comun: abre el navegador real
```

### Concurrencia (GUI que no se congela)
Las llamadas de red corren en un **hilo worker**; el resultado vuelve al hilo de Tk por una
`queue.Queue` poleada con `root.after()`. Nunca se toca Tk desde el worker. Un error de red se
muestra en rojo y sugiere pasar a Simulado.

### Seguridad del input
`commands.py` valida cada línea contra una **lista blanca de regex** (comandos guiados + sintaxis real), extrae
argumentos tipados y verifica que la IP esté en el CIDR del lab. Ningún texto del visitante llega a
una shell: los `subprocess` usan listas de argumentos (sin `shell=True`) y SSH/HTTP van
parametrizados.

## Protocolo serial de LEDs (app ↔ firmware)

Líneas de texto terminadas en `\n` (115200 baud). `app/leds/segments.py` y el `.ino` comparten el
mapeo de ids.

| Comando | Efecto |
|---|---|
| `IDLE` | shimmer de espera (todas las ramas) |
| `OFF` | apaga todo |
| `SEG:<id>:<anim>` | anima una rama (`id` 0..4) |
| `ALL:<anim>` | anima todas |

`<anim>` = `DISCOVER` (barrido), `FOCUS` (fijo), `EXPLOIT` (pulso ámbar), `TRANSFER` (chase cyan).
Animaciones **no bloqueantes** en el firmware (máquina de estados con `millis()`).

## Cómo extender

- **Nuevo comando**: agregar patrón en `commands.py`, texto en `script.py`, handler en `flow.py`, y
  método en `NetworkBackend` (+ ambas implementaciones).
- **Nuevo nodo/rama**: sumar `[[hosts]]` en `config.toml`, entrada en `segments.PATH_TO_ROLE`, y una
  rama/pin en el firmware (`BRANCH_COUNTS`, `addLeds`).
- **Nueva vulnerabilidad**: módulo en `exploits/`, caso en `RealBackend.exploit` y en
  `SimulatedBackend.exploit`.

## Docker (nodo) vs PyInstaller (app): por qué y cómo

### Por qué el **nodo** va en Docker
- **Reproducibilidad**: la misma imagen del FILE-SERVER corre en cualquier equipo que haga de nodo
  (si mañana lo cambian, `docker compose up` y listo). No hay "en mi máquina andaba".
- **Reset trivial**: recrear el contenedor deja el estado **siempre limpio** entre visitantes
  (`node/reset.sh`). No hay que limpiar sesiones ni archivos a mano.
- **Aislamiento**: la web y el SSH son **vulnerables a propósito**; encapsularlos en un contenedor en
  la red aislada del lab acota el riesgo.

### Cómo usar Docker (nodo)
```bash
cd node
docker compose up -d --build      # levantar
./reset.sh                        # resetear a estado limpio
```
IPs/puertos/credenciales se fijan en `docker-compose.yml` (variables `LAB_*`) y deben **coincidir**
con `config.toml` de la app. Verificar que `nmap -sn <cidr>` descubre el nodo.

### Por qué la **app** NO va en Docker (va como bundle PyInstaller)
La app necesita tres cosas del equipo real que Docker no da limpio, sobre todo en Windows:
1. **GUI** (tkinter/customtkinter necesita display).
2. **USB serial** al micro — el passthrough de USB a contenedores **no funciona en Docker Desktop de
   Windows**, justo el escenario de "cualquier PC".
3. **Abrir el navegador real** del host en `connect`.

Por eso la app se distribuye como **bundle PyInstaller** (`tools/build_app.py`, `cyberlab.spec`):
carpeta autocontenida que corre sin instalar Python, con `config.toml` **externo y editable** al lado
del ejecutable. Es **multiplataforma** (código sin supuestos de un solo SO), pero PyInstaller **no
cross-compila**: se genera un bundle en Windows (`.exe`) y otro en Linux (ELF). Misma base de código,
dos artefactos.
