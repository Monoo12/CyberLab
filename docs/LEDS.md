# Hoja de referencia de LEDs (cue sheet)

Documenta **qué comando/evento enciende qué tramo (segmento) de LED y con qué animación**, para
programarlo/afinarlo en el firmware (`firmware/cyberlab_leds/cyberlab_leds.ino`). Es el espejo exacto
de `app/leds/segments.py` y de la orquestación en `app/mission/flow.py`.

## 1. Ramas / segmentos físicos

El tablero es una **cadena de 4 tramos** en "U" invertida (TERMINAL → switch-izq → router → switch-der →
FILE-SERVER), con **una tira por tramo** y cada tira en su propio pin del micro. El id de segmento es lo
que viaja por serial (`SEG:<id>:<anim>`); en el tablero se los llama Tramo 1 a 4.

| Segmento (id) | Tramo | Recorrido físico | Largo | LEDs | Pin firmware | Pin ESP8266 |
|:---:|:---:|---|:---:|:---:|:---:|:---:|
| **0** | Tramo 1 | **TERMINAL** ↔ switch-izq | 50 cm | 30 | `PIN_B0` | `D1` |
| **1** | Tramo 2 | switch-izq ↔ router | 77 cm | 46 | `PIN_B1` | `D2` |
| **2** | Tramo 3 | router ↔ switch-der | 73 cm | 43 | `PIN_B2` | `D5` |
| **3** | Tramo 4 | switch-der ↔ **FILE-SERVER** | 43 cm | 25 | `PIN_B3` | `D6` |

> Tira WS2812B 5V de 60 LED/m (1 LED cada ~1,67 cm). Los LEDs son los que **entran** en cada tramo
> medido (redondeado para abajo, cortando por las marcas): **144 en total, ~2,4 m** de los 5 m. Si al
> cortar contás otro número, poné el real en `BRANCH_COUNTS`. `MAX_LEDS` lo deriva el firmware solo.
> Las animaciones corren en el sentido TERMINAL → FILE-SERVER; si un tramo quedó con la flecha de
> datos al revés, poné `true` en su posición de `BRANCH_REVERSED` (no hace falta recablear).

## 2. Ruta de LEDs por dispositivo (desde la terminal)

Para "llegar" a un host se encienden **todos** los segmentos de su ruta:

| Dispositivo (role) | IP (default) | Segmentos que se encienden |
|---|---|---|
| terminal (vos) | 192.168.10.10 | **0** |
| router | 192.168.10.1 | **0 · 1** |
| fileserver | 192.168.10.20 | **0 · 1 · 2 · 3** |
| workstation | 192.168.10.30 | **0 · 1 · 2** (hasta el switch-der) |
| security | 192.168.10.40 | **0 · 1 · 2** (hasta el switch-der) |

WORKSTATION y SECURITY no tienen tramo propio en el tablero (solo existen en el modo Simulado): los LEDs
llegan hasta el switch-der y el último salto se ve solo en el mapa de la pantalla.

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
SEG:<id>:<anim>      -> anima una rama (id 0..3)
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
| `inspect <ip>` | ruta(role del ip) | `FOCUS` | `SEG:0:FOCUS` … `SEG:3:FOCUS` (ej. fileserver) |
| `connect <ip:puerto>` | ruta(role del ip) | `FOCUS` | idem inspect |
| `ping <ip>` | ruta(role del ip) | `FOCUS` | idem |
| `telnet <ip> <puerto>` | ruta(role del ip) | `FOCUS` | idem |
| `traceroute <ip>` | ruta(role del ip), **salto por salto** | `DISCOVER` | `SEG:0:DISCOVER` → (350 ms) `SEG:1:DISCOVER` → `SEG:2:DISCOVER` → `SEG:3:DISCOVER` |
| `exploit <ip>` — mientras corre | ruta(role del ip) | `EXPLOIT` | `SEG:0:EXPLOIT` … `SEG:3:EXPLOIT` |
| `exploit <ip>` — al lograr acceso | ruta(role del ip) | `FOCUS` | idem con `FOCUS` |
| `read` de una FLAG / `secret.txt` | ruta(role del host actual) | `TRANSFER` | `SEG:…:TRANSFER` |
| **Mission Complete** | todas | `TRANSFER` | `ALL:TRANSFER` |
| Reset / volver a espera | todas | `IDLE` | `IDLE` |
| Volver al menú / apagar | todas | `OFF` | `OFF` |

**Comandos que NO tocan los LEDs:** `arp`, `netstat`, `pwd`, `whoami`, `ls`, `cd`, `help`, `hint`,
`clear`, `menu`, e `inspect -v` (misma animación que `inspect`).

### Ejemplo real (secuencia de una misión al FILE-SERVER)
```
IDLE                         (espera)
OFF                          (arranca la misión)
SEG:0:DISCOVER SEG:1:DISCOVER                                 (scan: router)
SEG:0:DISCOVER                                                (scan: terminal)
SEG:0:DISCOVER SEG:1:DISCOVER SEG:2:DISCOVER SEG:3:DISCOVER   (scan: file-server)
SEG:0:DISCOVER SEG:1:DISCOVER SEG:2:DISCOVER                  (scan: workstation)
SEG:0:DISCOVER SEG:1:DISCOVER SEG:2:DISCOVER                  (scan: security)
SEG:0:FOCUS SEG:1:FOCUS SEG:2:FOCUS SEG:3:FOCUS               (inspect / connect al file-server)
SEG:0:EXPLOIT SEG:1:EXPLOIT SEG:2:EXPLOIT SEG:3:EXPLOIT       (exploit)
SEG:0:FOCUS SEG:1:FOCUS SEG:2:FOCUS SEG:3:FOCUS               (acceso concedido)
SEG:0:TRANSFER SEG:1:TRANSFER SEG:2:TRANSFER SEG:3:TRANSFER   (read secret.txt)
ALL:TRANSFER                 (Mission Complete)
```

## 6. Notas para el firmware

- El `.ino` ya implementa `IDLE/OFF/SEG/ALL` y las 4 animaciones (no bloqueantes con `millis()`).
- **`DISCOVER` termina en tenue y `FOCUS` en fijo**: es intencional — tras el barrido, el tramo queda
  suave; el foco lo pinta más fuerte cuando es el objetivo.
- La app manda **un `SEG:` por segmento**; el firmware anima cada rama de forma independiente, así que
  no importa el orden ni que lleguen varios seguidos.
- Si agregás un dispositivo/rama nuevo: sumá su entrada en `app/leds/segments.py`
  (`PATH_TO_ROLE`), su enlace en `app/ui/netmap.py` (`_SEG_LINKS`) y una rama/pin en el firmware
  (`NUM_BRANCHES`, `BRANCH_COUNTS`, `BRANCH_REVERSED`, buffer y `addLeds`) — y actualizá las secciones 1
  y 2 de este documento.
- **`MAX_LEDS` se deriva solo** del mayor de `BRANCH_COUNTS` (constexpr): no hay que ajustarlo a mano
  ni corres riesgo de desbordar los buffers si cambiás los largos.
- El consumo lo limita FastLED a 9 A para la fuente de 5V/10A (`setMaxPowerInVoltsAndMilliamps`): no
  toques eso salvo que cambies la fuente.
- Para probar sin la app: `python tools/led_test.py --port COM3 SEG:3:EXPLOIT` (ver `docs/GUIA-HARDWARE.md`).
