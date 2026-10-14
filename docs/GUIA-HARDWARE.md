# Guía de conexión del hardware

Sección especial para el momento de montar todo: la tira LED, el microcontrolador y los nodos.
El software ya está listo; esta guía explica cómo conectarlo al mundo físico.

> Ajustá siempre a tu tablero real. Los números (pines, cantidad de LEDs) son un punto de partida.

## 1. Cargar el firmware en el microcontrolador

1. Instalá el **Arduino IDE** y la librería **FastLED** (Gestor de librerías → "FastLED").
2. Abrí `firmware/cyberlab_leds/cyberlab_leds.ino`.
3. Elegí tu placa (Arduino UNO/Nano, ESP8266 NodeMCU o ESP32) y el puerto.
4. **Ajustá al tope del sketch** (ver sección 3): pines de datos y, si cortaste distinto, la cantidad
   de LEDs por rama.
5. Subí el sketch. Al abrir el Monitor Serie (115200 baud) podés tipear comandos a mano
   (`SEG:3:EXPLOIT`, `ALL:TRANSFER`, `OFF`).

Sin WiFi de por medio, cualquiera de las tres placas sirve igual: el micro solo lee texto del USB.

## 2. Cableado de la tira LED (WS2812B / NeoPixel)

La tira es **direccionable** (cada LED se prende solo) — imprescindible para el efecto de recorrido.

- Comprá **una sola tira** (ej. rollo de 5 m) y cortala en los **4 pedazos** (uno por tramo, ver §3).
  Usás ~2,4 m; el resto sobra.
- Cada pedazo tiene 3 cables: **5V**, **GND** y **DATA IN**. Mirá la **flecha** impresa: el dato
  entra por el lado de la flecha. Conectada al revés **no funciona**. Podés meter el DATA IN por el
  extremo que te quede más cómodo; si la animación sale al revés, se corrige con `BRANCH_REVERSED`.
- **5V y GND se comparten** entre todos los pedazos (todos a la misma fuente 5V).
- El **DATA de cada pedazo va a su propio pin** del micro (ver mapeo abajo).
- ⚠️ **Tierra común obligatoria**: el **GND del micro** tiene que estar unido al **GND de la fuente**
  que alimenta las tiras. Si no comparten tierra, la señal de datos se malinterpreta → LEDs que
  titilan o no prenden. Es el error #1.
- Si una cadena es larga, **inyectá 5V también al final** (no solo al principio) para que los últimos
  LEDs no se vean tenues o cambien de color por caída de tensión.

### Fuente de alimentación (5V / 10A, fija)
En el tablero van **144 LEDs** (los 4 tramos). Un WS2812B a blanco pleno consume ~60 mA → 144 LEDs
darían ~8,6 A en el peor caso teórico, dentro de la **fuente switching 5V / 10A (50 W)**. Igual el
**firmware limita el consumo** a 9 A (`FastLED.setMaxPowerInVoltsAndMilliamps(5, 9000)`): FastLED
autoescala el brillo en cada frame para no superar ese tope, así no hay riesgo de brownout ni de reset
del micro aunque alargues algún tramo.

- **Inyectá 5V en los dos extremos** de los tramos más largos (Tramo 2 y 3, ~75 cm): la tira pierde
  tensión de punta a punta y los últimos LEDs se ven tenues o cambian de color.
- No alimentes la tira desde el pin 5V del micro por USB: usá la fuente, con **GND común** con el micro.

### Nivel lógico de datos 3.3V → 5V (clave con ESP8266)
El **ESP8266 (NodeMCU) saca la señal de datos a 3.3V**, pero el WS2812B espera un "1" lógico de
~0.7×5V = **3.5V**. 3.3V queda justo por debajo del umbral → el primer LED puede leer mal y arruinar
toda la cadena (parpadeos, colores random, ramas muertas). Soluciones, de mejor a peor:

- **Level shifter 3.3→5V** en cada línea de datos (ej. **74AHCT125** o 74HCT245). Es lo recomendado.
- Alimentar la tira a **~4.3–4.5V** (un diodo en serie desde los 5V) para bajar su umbral — sirve en
  tramos cortos.
- Primer LED "sacrificable" muy cerca del micro: a veces engancha igual, pero es lo menos fiable.
- Arduino UNO/Nano (5V) no tienen este problema; con **ESP8266 poné el level shifter**.

## 3. Mapeo rama ↔ pin ↔ LEDs (espejo del software)

El firmware y `app/leds/segments.py` comparten el mismo mapeo. El tablero es una **cadena de 4 tramos**
en "U" invertida, con una tira por tramo:

| Rama (id) | Tramo | Recorrido físico | Largo | LEDs | Pin sketch | ESP8266 |
|:---:|:---:|---|:---:|:---:|:---:|:---:|
| 0 | Tramo 1 | **TERMINAL** → switch-izq | 50 cm | 30 | `PIN_B0` | `D1` (GPIO5) |
| 1 | Tramo 2 | switch-izq → router | 77 cm | 46 | `PIN_B1` | `D2` (GPIO4) |
| 2 | Tramo 3 | router → switch-der | 73 cm | 43 | `PIN_B2` | `D5` (GPIO14) |
| 3 | Tramo 4 | switch-der → **FILE-SERVER** | 43 cm | 25 | `PIN_B3` | `D6` (GPIO12) |

- A 60 LED/m hay un LED (y una marca de corte) cada ~1,67 cm. Los LEDs de la tabla son los que **entran**
  en cada tramo medido, redondeando para abajo: **144 en total**. Ya están cargados en `BRANCH_COUNTS`;
  si al cortar contás otro número, poné el real.
- Ajustá en el sketch los pines `PIN_B0..PIN_B3` a los que uses (en el NodeMCU: `D1`, `D2`, `D5`, `D6`).
  **`MAX_LEDS` no se toca a mano**: el firmware lo deriva del mayor de `BRANCH_COUNTS`, así los buffers
  nunca se desbordan.
- **Sentido**: las animaciones recorren el camino TERMINAL → FILE-SERVER (el barrido y el chase avanzan
  hacia el file-server). Si un tramo quedó con el DATA IN del lado contrario, poné `true` en su lugar de
  `BRANCH_REVERSED` en vez de recablear.
- WORKSTATION y SECURITY (solo modo Simulado) no tienen tramo: al apuntarles se encienden los tramos 1–3
  (hasta el switch-der).
- Pines sugeridos por placa: Arduino UNO/Nano → 2,3,4,5. ESP8266 (NodeMCU) → D1,D2,D5,D6
  (GPIO5,4,14,12). ESP32 → casi cualquier GPIO de salida.

**Por qué 4 tiras y no una sola:** cada tramo termina en un equipo distinto (switch o router) y se
anima por separado según el host al que apuntás. Un pin por tramo es lo más simple de cablear y de
debuggear (si un tramo falla, los otros siguen), y FastLED maneja los 4 pines a la vez sin problema.

## 4. Conectar el micro a la PC y configurar el puerto

1. Enchufá el micro por **USB** a la PC de la muestra.
2. Averiguá el puerto:
   - Windows: Administrador de dispositivos → "Puertos (COM y LPT)" → `COMx`.
   - Linux: `ls /dev/ttyUSB* /dev/ttyACM*` (suele ser `/dev/ttyUSB0`).
3. Poné ese valor en `config.toml`:
   ```toml
   [serial]
   enabled = true
   port    = "COM3"      # o "/dev/ttyUSB0"
   baud    = 115200
   ```
   En Linux puede hacer falta permisos del puerto: `sudo usermod -aG dialout $USER` (y volver a entrar).

## 5. Probar los LEDs sin la app

```bash
python tools/led_test.py --port COM3                 # secuencia demo
python tools/led_test.py --port COM3 SEG:3:EXPLOIT   # un comando puntual
python tools/led_test.py --port COM3 --interactive   # tipear comandos
```

Deberías ver: barrido al `DISCOVER`, tramo fijo al `FOCUS`, pulso ámbar al `EXPLOIT`, chase cyan al
`TRANSFER`, y `OFF` apaga todo. Si una rama no responde, revisá su pin de datos y la tierra común.

## 6. Conectar los nodos a la red

1. Armá la red física siguiendo los tramos: TERMINAL → switch izquierdo → router → switch derecho →
   FILE-SERVER (el router va con un cable a cada switch; los switches no se conectan entre sí).
2. Asigná IPs fijas (o reservas DHCP) que coincidan con la sección `[[hosts]]` de `config.toml`.
3. En el equipo FILE-SERVER: `cd node && docker compose up -d --build`.
4. Verificá que la PC lo descubre: `nmap -sn 192.168.10.0/24` debería listar sus IPs.
5. Pasá la app a **Real** (`--engine real` o el menú).

## 7. Resolución de problemas

| Síntoma | Causa probable / arreglo |
|---|---|
| LEDs titilan o no prenden | **Falta tierra común** entre fuente y micro. Unir GND. |
| LEDs titilan / colores random (ESP8266) | Señal de datos a 3.3V bajo el umbral del WS2812B; poné un **level shifter 3.3→5V** (ver §2). |
| Solo prende el principio de una tira | Tramo largo sin re-inyección de 5V; inyectar 5V al final. |
| La animación de un tramo va al revés | DATA IN del otro lado: poné `true` en ese tramo de `BRANCH_REVERSED`. |
| Los últimos LEDs de un tramo no prenden | `BRANCH_COUNTS` menor que los LEDs reales: contalos y corregí el número. |
| Colores equivocados | Orden de color; probar `RGB` en vez de `GRB` en `addLeds<...>`. |
| Una rama entera muerta | Flecha de DATA al revés, o pin equivocado en el sketch. |
| El micro no aparece en el puerto | Cable USB solo-carga (usar uno de datos), o falta el driver CH340/CP210x. |
| `scan` no devuelve hosts (modo real) | `nmap` no instalado, red mal cableada, o IPs fuera del CIDR de `config.toml`. |
| `ls`/`read` fallan (modo real) | SSH del nodo caído, o `ssh_user`/clave no coinciden con el contenedor. |
| Nada anda en vivo | Cambiar a **modo Simulado** (fallback) y seguir la muestra. |
