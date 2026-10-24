# Rediseño: 4 modos de juego + LEDs vivos

Doc de diseño del rediseño de la experiencia (octubre 2026). Todos los modos corren sobre **el mismo
motor** (red → exploit → archivo) y animan **el mismo tablero de LEDs**; lo único que cambia es *cómo
entra el visitante* y *cuánto lo acompañamos*.

## El problema

El nivel "Fácil" ya asumía sentarse a **leer y teclear** una terminal. En la muestra, incluso gente que
sabía un poco de redes se trababa: las barreras eran **teclear comandos** y **no saber cuál es el próximo
paso**. La solución no es "una terminal más fácil", es ofrecer **modelos de interacción distintos**.

## Los 4 modos

| Modo | Para quién | Interacción | ¿Se puede perder? |
|---|---|---|---|
| 🟦 **Tarjetas** | No sabe nada | Botón grande por paso, **cero teclado**; el único botón activo es el próximo paso | No (con suspenso) |
| 🟩 **Guiado** | Se anima un poco | Terminal con el comando **ya escrito** (un Enter) + narración en lenguaje simple | No (con suspenso) |
| 🟥 **Experto** | Sabe de redes | La terminal real de hoy, con sus 4 dificultades (fácil→pro) | Sí (el de hoy) |
| 🧩 **Reto** | Reto / grupos | Escape room: acertijos con cronómetro; el tablero da las pistas; se elige o se tipea | Sí (se acaba el tiempo) |

El **operador** fija el modo (y la lección) en el menú de setup; no hay pantalla de selección para el
visitante. El menú habilita solo lo que aplica a cada modo. `Ctrl+M` vuelve al menú desde cualquier modo.

## El recorrido (Tarjetas / Guiado): 3 golpes

1. **MIRAR** — `scan` (+`inspect`): "¿qué hay conectado?" El tablero se enciende aparato por aparato.
2. **ENTRAR** — `exploit`: acá viven **la lección de la ronda** y el **suspenso**.
3. **LLEVARSE** — `ls` + `read`: se recupera el archivo secreto.

### El suspenso (golpe 2) — siempre termina bien

Overlay cinematográfico (`app/ui/suspense.py`) que combina los tres recursos y **no se puede perder**:
cuenta regresiva ("DEFENSA REINICIANDO") + contador de miles de claves probándose + barra de "INTRUSIÓN
DETECTADA". Clímax: casi-fallo en rojo → **ACCESO CONCEDIDO** en verde. LEDs: `EXPLOIT` → `ERROR` →
`TRANSFER`.

### La lección rota por ronda

`clave` (contraseña débil → vía *hydra*), `expuesto` (dato a la vista en la página → vía *leak*),
`login` (truco en el formulario → vía *sqli*). Con `rotar`, alterna una por ronda. La vía del backend
**coincide** con la lección, así la narración, el suspenso y la salida cuentan la misma historia.

## Reto (escape room)

4 acertijos (`app/mission/reto_flow.py`) donde el **tablero y los componentes físicos** (router,
switches, cable/canaleta) son las pistas:

1. Contar los **nodos** que titilan (switches + router).
2. **El cable roto** — aprovecha el LED 62 quemado como acertijo real del hardware.
3. Contar los **destellos del router** (se tipea; fresco cada ronda).
4. **Seguir la señal** por la canaleta hasta el router.

Input mixto (opción múltiple + tipear), cronómetro con penalidad por error y botón **PISTA** que vuelve
a mostrar la clave en las luces.

## LEDs vivos: todos los comandos animan

Antes `ping`, `telnet`, `arp`, `netstat`, `ls`, `cd` y los errores estaban **mudos**. Ahora cada comando
mueve el tablero. Se agregaron 4 animaciones **transitorias** al firmware (vuelven solas al estado
previo, como `PROCESS`):

- `PING` — eco que va y vuelve (`ping`, `netstat`).
- `SCAN` — flicker de escaneo de puertos (`telnet`).
- `BLIP` — ack breve de cualquier comando (`ls`, `cd`, comandos locales).
- `ERROR` — flash rojo (comando inválido / fallo).

> **Requiere reflashear el ESP** una vez con el `.ino` nuevo. Con firmware viejo esos tokens se tratan
> como `OFF` (el tramo queda negro; no rompe nada). Ver [docs/LEDS.md](LEDS.md).

## Arquitectura: qué se reusó y qué es nuevo

- **Reusado:** `backend/`, `leds/`, `netmap`, `models`, `exploits/`, `MatrixRain`, y la máquina de
  estados del `MissionController` (Experto/Guiado).
- **Nuevo:**
  - `app/ui/suspense.py` — overlay de suspenso (Tarjetas/Guiado).
  - `app/ui/tarjetas.py` + `app/mission/tarjetas_flow.py` — modo Tarjetas.
  - `app/ui/reto.py` + `app/mission/reto_flow.py` — modo Reto.
  - En `flow.py` (Experto/Guiado): texto fantasma (`terminal.suggest`), narración por paso, rama de
    suspenso en `exploit`, rotación de lección.
  - `config.modes.mode` / `config.modes.lesson` + flags `--mode` / `--lesson` + selectores en el menú.
  - Firmware: `PING/SCAN/BLIP/ERROR` (`isTransient`/`startTransient`).

Los tres controladores (`MissionController`, `TarjetasController`, `RetoController`) comparten el mismo
ciclo de vida (`enter_waiting` / `on_any_key` / `shutdown`), así la app los trata igual.
