# Hoja de referencia de LEDs (cue sheet)

Documenta **qué comando/evento enciende qué tramo (segmento) de LED y con qué animación**, para
programarlo/afinarlo en el firmware (`firmware/netlab_leds/netlab_leds.ino`). Es el espejo exacto
de `app/leds/segments.py` y de la orquestación en `app/mission/flow.py`.

## 1. Tramos / segmentos físicos

El tablero es **una sola tira de 68 LEDs encadenada** en "U" invertida (TERMINAL → switch-izq → router →
switch-der → FILE-SERVER), en un único pin del micro (`D1` en el NodeMCU). Cada tramo es un **rango de
LEDs** de esa tira y entre tramo y tramo hay **un LED de nodo** (el switch o el router). El id de
segmento es lo que viaja por serial (`SEG:<id>:<anim>`); en el tablero se los llama Tramo 1 a 4.

Los números de LED van **desde 0** en el extremo de la TERMINAL (así los usan `PIX`/`ADD`); entre
paréntesis, la cuenta a mano desde 1.

| Zona | Recorrido físico | LEDs | Números de LED |
|---|---|:---:|:---:|
| **Segmento 0** · Tramo 1 | **TERMINAL** → switch-izq | 13 | 0–12 (1–13) |
| Nodo 0 · switch-izq | titila "procesando" | 1 | 13 (14) |
| **Segmento 1** · Tramo 2 | switch-izq → router | 20 | 14–33 (15–34) |
| Nodo 1 · router | titila "procesando" | 1 | 34 (35) |
| **Segmento 2** · Tramo 3 | router → switch-der | 19 | 35–53 (36–54) |
| Nodo 2 · switch-der | titila "procesando" | 1 | 54 (55) |
| **Segmento 3** · Tramo 4 | switch-der → **FILE-SERVER** | 13 | 55–67 (56–68) |

> **El LED 62 (63 contando a mano) está dañado y no se prende nunca**, con ningún comando: el firmware
> lo fuerza a negro en cada frame (`DEAD_LEDS`).
>
> Los largos de los tramos están en `BRANCH_COUNTS` (sin contar los nodos); el inicio de cada tramo y
> nodo se recalcula solo. Las animaciones corren en el sentido TERMINAL → FILE-SERVER; si la cadena
> arranca del lado del FILE-SERVER, poné `STRIP_REVERSED = true` (no hace falta recablear).

### Nodos (switch / router)

Cada vez que un `SEG:<id>:<anim>` enciende un tramo, el **nodo del final de ese tramo titila en blanco
~2,5 s** (simula que el switch o el router procesa el paquete) y después queda igual que el tramo. El
tramo 4 llega al FILE-SERVER y no tiene nodo. Con `OFF`/`IDLE` los nodos siguen a la tira sin titilar.
La app no manda nada extra para esto: alcanza con los `SEG` de siempre.

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
| `PROCESS` | Un nodo procesa (switch/router) | titila blanco ~2,5 s y vuelve a como estaba |

## 4. Protocolo serial (una línea por comando, `\n`, 115200 baud)

```
IDLE                 -> toda la tira en espera
OFF                  -> apaga todo
SEG:<id>:<anim>      -> anima un tramo (id 0..3); su nodo del final titila y lo sigue
ALL:<anim>           -> anima todos los tramos (con sus nodos)
NODE:<id>:<anim>     -> anima solo un nodo (0 switch-izq, 1 router, 2 switch-der)  (ej. NODE:1:PROCESS)
PIX:<rangos>:<anim>  -> anima solo esos LEDs y apaga el resto   (ej. PIX:0-12,35-53:FOCUS)
ADD:<rangos>:<anim>  -> anima esos LEDs sin tocar el resto       (ej. ADD:55-67:EXPLOIT)
```

`<rangos>`: LEDs sueltos o rangos inclusivos separados por coma, contando desde 0 en el lado de la
TERMINAL (hasta 8 rangos). En `PIX`/`ADD` también vale `<anim>` = `OFF` o `IDLE` (ej. `ADD:40-50:OFF`
apaga solo esos). Cualquier `SEG`/`ALL`/`NODE`/`IDLE`/`OFF` vuelve al modo tramos y borra los rangos. La
app usa `IDLE/OFF/SEG/ALL`; `NODE`/`PIX`/`ADD` son para pruebas y efectos a mano.

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

- El `.ino` ya implementa `IDLE/OFF/SEG/ALL/PIX/ADD` y las 4 animaciones (no bloqueantes con
  `millis()`). Cada tramo y cada rango de `PIX`/`ADD` es una "zona" que se anima por su cuenta (el
  barrido y el chase recorren solo esa zona).
- **`DISCOVER` termina en tenue y `FOCUS` en fijo**: es intencional — tras el barrido, el tramo queda
  suave; el foco lo pinta más fuerte cuando es el objetivo.
- La app manda **un `SEG:` por segmento**; el firmware anima cada tramo de forma independiente, así que
  no importa el orden ni que lleguen varios seguidos.
- Si agregás un tramo nuevo: sumá su entrada en `app/leds/segments.py` (`PATH_TO_ROLE`), su enlace en
  `app/ui/netmap.py` (`_SEG_LINKS`) y su largo en el firmware (`NUM_BRANCHES` y `BRANCH_COUNTS`, en el
  orden de la cadena) — y actualizá las secciones 1 y 2 de este documento.
- **El inicio de cada tramo y el total se calculan solos** a partir de `BRANCH_COUNTS` en `setup()`; el
  buffer (`MAX_LEDS`) alcanza para el rollo entero de 300 LEDs, así que cambiar largos no desborda nada.
- El consumo lo limita FastLED a 9 A para la fuente de 5V/10A (`setMaxPowerInVoltsAndMilliamps`): no
  toques eso salvo que cambies la fuente.
- Para probar sin la app: `python tools/led_test.py --port COM3 SEG:3:EXPLOIT` o
  `... "PIX:0-12,35-53:FOCUS"` (ver `docs/GUIA-HARDWARE.md`).
- Para revisar el tablero entero (tramos, nodos y LED dañado) en un solo paso:
  `python tools/tablero_test.py` (ver la sección 7).

## 7. Prueba del tablero completo

`tools/tablero_test.py` manda los comandos con el mismo `LedController` que usa la app, así que también
prueba la conexión real. Fases (se puede correr una sola con `--fase N`):

1. **Tramos uno por uno**: cada tramo se prende verde y el nodo de su final titila blanco y queda verde.
2. **Nodos solos**: los LEDs 14, 35 y 55 (a mano) titilan de a uno y se apagan.
3. **LED dañado**: toda la tira verde menos el 63; después solo del 61 al 65, con el 63 apagado en el medio.
4. **Ruta completa** (como un `traceroute` al FILE-SERVER): tramo, nodo procesando, tramo, y así hasta el final.
