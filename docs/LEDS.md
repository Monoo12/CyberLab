# Hoja de referencia de LEDs (cue sheet)

Documenta **qué comando/evento enciende qué tramo (segmento) de LED y con qué animación**, para
programarlo/afinarlo en el firmware (`firmware/cyberlab_leds/cyberlab_leds.ino`). Es el espejo exacto
de `app/leds/segments.py` y de la orquestación en `app/mission/flow.py`.

## 1. Ramas / segmentos físicos

La topología es un árbol con **5 ramas de datos** (una tira por pin del micro). El id de segmento es
lo que viaja por serial (`SEG:<id>:<anim>`).

| Segmento (id) | Tramo físico | Pin firmware (default) | LEDs (est. 60/m, tablero 1 m) |
|:---:|---|:---:|:---:|
| **0** | router ↔ switch-izq ↔ **TERMINAL** | `PIN_B0` | ~50 (largo) |
| **1** | router ↔ switch-der (troncal) | `PIN_B1` | ~28 |
| **2** | switch-der ↔ **FILE-SERVER** | `PIN_B2` | ~30 |
| **3** | switch-der ↔ **WORKSTATION-01** | `PIN_B3` | ~24 |
| **4** | switch-der ↔ **SECURITY-SERVER** | `PIN_B4` | ~32 |

> Estimación para tablero 1×1 m con tira 60 LED/m (`BRANCH_COUNTS = {50,28,30,24,32}`, `MAX_LEDS 52`
> en el firmware). Medí los tramos reales y afiná; `MAX_LEDS` debe ser ≥ el mayor.

## 2. Ruta de LEDs por dispositivo (desde la terminal)

Para "llegar" a un host se encienden **todos** los segmentos de su ruta:

| Dispositivo (role) | IP (default) | Segmentos que se encienden |
|---|---|---|
| router | 192.168.10.1 | **0** |
| terminal (vos) | 192.168.10.10 | **0** |
| fileserver | 192.168.10.20 | **0 · 1 · 2** |
| workstation | 192.168.10.30 | **0 · 1 · 3** |
| security | 192.168.10.40 | **0 · 1 · 4** |

## 3. Animaciones (tokens del protocolo)

| Token | Sentido | Sugerencia visual en el firmware |
|---|---|---|
| `IDLE` | Espera (nadie jugando) | respiración/shimmer verde muy tenue |
| `OFF` | Apagado | negro |
| `DISCOVER` | Se descubre/recorre un tramo | barrido de encendido y queda tenue |
| `FOCUS` | Tramo en foco (objetivo actual) | verde fijo medio |
| `EXPLOIT` | Ataque en curso | pulso rápido ámbar/intenso |
| `TRANSFER` | Transferencia de datos (flag/archivo) | chase rápido cyan |

## 4. Protocolo serial (una línea por comando, `\n`, 115200 baud)

```
IDLE                 -> todas las ramas en espera
OFF                  -> apaga todo
SEG:<id>:<anim>      -> anima una rama (id 0..4)
ALL:<anim>           -> anima todas las ramas
```

## 5. Cue sheet — qué dispara cada comando/evento

`ruta(role)` = los segmentos de la sección 2 para ese host. La app manda **un `SEG:` por cada
segmento** de la ruta (no hay un comando "multi-segmento").

| Evento / comando | Segmentos | Animación | Serial que envía la app |
|---|---|---|---|
| Pantalla de espera (idle) | todos | `IDLE` | `IDLE` |
| Inicio de misión (briefing) | todos | `OFF` | `OFF` |
| `scan` — al descubrir cada host | ruta(role) de **cada** host, uno por uno | `DISCOVER` | `SEG:0:DISCOVER`, `SEG:1:DISCOVER`, … (por host, escalonado ~420 ms) |
| `inspect <ip>` | ruta(role del ip) | `FOCUS` | `SEG:0:FOCUS` `SEG:1:FOCUS` `SEG:2:FOCUS` (ej. fileserver) |
| `connect <ip:puerto>` | ruta(role del ip) | `FOCUS` | idem inspect |
| `ping <ip>` | ruta(role del ip) | `FOCUS` | idem |
| `telnet <ip> <puerto>` | ruta(role del ip) | `FOCUS` | idem |
| `traceroute <ip>` | ruta(role del ip), **salto por salto** | `DISCOVER` | `SEG:0:DISCOVER` → (350 ms) `SEG:1:DISCOVER` → `SEG:2:DISCOVER` … |
| `exploit <ip>` — mientras corre | ruta(role del ip) | `EXPLOIT` | `SEG:0:EXPLOIT` `SEG:1:EXPLOIT` `SEG:2:EXPLOIT` |
| `exploit <ip>` — al lograr acceso | ruta(role del ip) | `FOCUS` | idem con `FOCUS` |
| `read` de una FLAG / `secret.txt` | ruta(role del host actual) | `TRANSFER` | `SEG:…:TRANSFER` |
| **Mission Complete** | todas | `TRANSFER` | `ALL:TRANSFER` |
| Reset / volver a espera | todas | `IDLE` | `IDLE` |
| Volver al menú / apagar | todas | `OFF` | `OFF` |

**Comandos que NO tocan los LEDs:** `arp`, `netstat`, `pwd`, `whoami`, `ls`, `cd`, `help`, `hint`,
`clear`, `menu`, e `inspect -v` (misma animación que `inspect`).

### Ejemplo real (secuencia capturada de una misión al FILE-SERVER)
```
IDLE                         (espera)
OFF                          (arranca la misión)
SEG:0:DISCOVER               (scan: router/terminal)
SEG:0:DISCOVER SEG:1:DISCOVER SEG:2:DISCOVER   (scan: file-server)
SEG:0:DISCOVER SEG:1:DISCOVER SEG:3:DISCOVER   (scan: workstation)
SEG:0:DISCOVER SEG:1:DISCOVER SEG:4:DISCOVER   (scan: security)
SEG:0:FOCUS SEG:1:FOCUS SEG:2:FOCUS            (inspect / connect al file-server)
SEG:0:EXPLOIT SEG:1:EXPLOIT SEG:2:EXPLOIT      (exploit)
SEG:0:FOCUS SEG:1:FOCUS SEG:2:FOCUS            (acceso concedido)
SEG:0:TRANSFER SEG:1:TRANSFER SEG:2:TRANSFER   (read secret.txt)
ALL:TRANSFER                 (Mission Complete)
```

## 6. Notas para el firmware

- El `.ino` ya implementa `IDLE/OFF/SEG/ALL` y las 4 animaciones (no bloqueantes con `millis()`).
- **`DISCOVER` termina en tenue y `FOCUS` en fijo**: es intencional — tras el barrido, el tramo queda
  suave; el foco lo pinta más fuerte cuando es el objetivo.
- La app manda **un `SEG:` por segmento**; el firmware anima cada rama de forma independiente, así que
  no importa el orden ni que lleguen varios seguidos.
- Si agregás un dispositivo/rama nuevo: sumá su entrada en `app/leds/segments.py`
  (`PATH_TO_ROLE`) y una rama/pin en el firmware (`BRANCH_COUNTS`, `addLeds`) — y actualizá las
  secciones 1 y 2 de este documento.
- Para probar sin la app: `python tools/led_test.py --port COM3 SEG:2:EXPLOIT` (ver `docs/GUIA-HARDWARE.md`).
