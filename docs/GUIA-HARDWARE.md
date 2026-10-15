# Guía de conexión del hardware

Sección especial para el momento de montar todo: la tira LED, el microcontrolador y los nodos.
El software ya está listo; esta guía explica cómo conectarlo al mundo físico.

> Ajustá siempre a tu tablero real. Los números (pines, cantidad de LEDs) son un punto de partida.

## 1. Cargar el firmware en el microcontrolador

1. Instalá el **Arduino IDE** y la librería **FastLED** (Gestor de librerías → "FastLED").
2. Abrí `firmware/cyberlab_leds/cyberlab_leds.ino`.
3. Elegí tu placa (Arduino UNO/Nano, ESP8266 NodeMCU o ESP32) y el puerto.
4. **Revisá el tope del sketch** (ver sección 3): el pin de datos (en ESP8266 ya viene en `D1`) y, si
   cortaste distinto, la cantidad de LEDs por tramo.
5. Subí el sketch. Al abrir el Monitor Serie (115200 baud) podés tipear comandos a mano
   (`SEG:3:EXPLOIT`, `ALL:TRANSFER`, `OFF`).

Sin WiFi de por medio, cualquiera de las tres placas sirve igual: el micro solo lee texto del USB.

## 2. Cableado de la tira LED (WS2812B / NeoPixel)

La tira es **direccionable** (cada LED se prende solo) — imprescindible para el efecto de recorrido.

- Los 4 tramos forman **una sola cadena** de 144 LEDs en **un único pin** de datos: TERMINAL → switch-izq
  → router → switch-der → FILE-SERVER. Cada LED se controla por separado igual (cada WS2812B tiene su
  propio chip y le pasa el resto del dato al siguiente), así que los tramos son solo **rangos de LEDs**.
- Si el canal del tablero es continuo, ni siquiera hace falta cortar: un pedazo de 144 LEDs del rollo
  de 5 m. Si cortás en tramos, uní cada corte con 3 cables (**5V**, **GND**, **DATA**).
- Mirá la **flecha** impresa: el dato va en ese sentido. Todas las flechas tienen que apuntar hacia el
  FILE-SERVER y el **DATA IN va del lado de la TERMINAL** (LED 0). En cada unión, el **DATA OUT** del
  último LED de un tramo va al **DATA IN** del primero del siguiente; una flecha al revés corta todo lo
  que viene después. Si la cadena arrancara del lado del FILE-SERVER, poné `STRIP_REVERSED = true`.
- **5V y GND** van a la fuente 5V (ver inyección abajo).
- ⚠️ **Tierra común obligatoria**: el **GND del micro** tiene que estar unido al **GND de la fuente**
  que alimenta las tiras. Si no comparten tierra, la señal de datos se malinterpreta → LEDs que
  titilan o no prenden. Es el error #1.
- La cadena mide ~2,4 m: **inyectá 5V en los dos extremos** (no solo al principio) para que los últimos
  LEDs no se vean tenues o cambien de color por caída de tensión.

### Fuente de alimentación (5V / 10A, fija)
En el tablero van **144 LEDs** (los 4 tramos). Un WS2812B a blanco pleno consume ~60 mA → 144 LEDs
darían ~8,6 A en el peor caso teórico, dentro de la **fuente switching 5V / 10A (50 W)**. Igual el
**firmware limita el consumo** a 9 A (`FastLED.setMaxPowerInVoltsAndMilliamps(5, 9000)`): FastLED
autoescala el brillo en cada frame para no superar ese tope, así no hay riesgo de brownout ni de reset
del micro aunque alargues algún tramo.

- **Inyectá 5V en los dos extremos** de la cadena (lado TERMINAL y lado FILE-SERVER) y, si podés, también
  en el medio (a la altura del router): la tira pierde tensión de punta a punta y los últimos LEDs se
  ven tenues o cambian de color.
- No alimentes la tira desde el pin 5V del micro por USB: usá la fuente, con **GND común** con el micro.

### Nivel lógico de datos 3.3V → 5V (clave con ESP8266)
El **ESP8266 (NodeMCU) saca la señal de datos a 3.3V**, pero el WS2812B espera un "1" lógico de
~0.7×5V = **3.5V**. 3.3V queda justo por debajo del umbral → el primer LED puede leer mal y arruinar
toda la cadena (parpadeos, colores random, LEDs que no prenden). Soluciones, de mejor a peor:

- **Level shifter 3.3→5V** en la línea de datos (ej. **74AHCT125**; alcanza con 1 de sus 4 canales). Es
  lo recomendado.
- Alimentar la tira a **~4.3–4.5V** (un diodo en serie desde los 5V) para bajar su umbral — sirve en
  tramos cortos.
- Primer LED "sacrificable" muy cerca del micro: a veces engancha igual, pero es lo menos fiable.
- Arduino UNO/Nano (5V) no tienen este problema; con **ESP8266 poné el level shifter**.

## 3. Mapeo tramo ↔ LEDs (espejo del software)

El firmware y `app/leds/segments.py` comparten el mismo mapeo. El tablero es **una sola tira de 144
LEDs** en "U" invertida, en el pin `D1` (GPIO5) del NodeMCU; cada tramo es un rango de esa tira, contando
desde la TERMINAL:

| Tramo (id) | Recorrido físico | Largo | LEDs | Números de LED |
|:---:|---|:---:|:---:|:---:|
| T1 (0) | **TERMINAL** → switch-izq | 50 cm | 30 | 0–29 |
| T2 (1) | switch-izq → router | 77 cm | 46 | 30–75 |
| T3 (2) | router → switch-der | 73 cm | 43 | 76–118 |
| T4 (3) | switch-der → **FILE-SERVER** | 43 cm | 25 | 119–143 |

- A 60 LED/m hay un LED (y una marca de corte) cada ~1,67 cm. Los LEDs de la tabla son los que **entran**
  en cada tramo medido, redondeando para abajo. Ya están cargados en `BRANCH_COUNTS`; si al cortar
  contás otro número, poné el real: los rangos de los tramos siguientes se corren solos.
- El pin es `DATA_PIN` (en ESP8266 ya viene en `5` = `D1`). En Arduino UNO/Nano usa el 6. El buffer
  alcanza para el rollo entero (300 LEDs), así que podés cambiar los largos sin tocar nada más.
- WORKSTATION y SECURITY (solo modo Simulado) no tienen tramo: al apuntarles se encienden los tramos 1–3
  (hasta el switch-der).

**LEDs sueltos:** además de animar tramos enteros, el firmware acepta rangos de LEDs:

```
PIX:0-9,40-50:FOCUS     -> prende 0..9 y 40..50 (inclusive) y apaga el resto
ADD:119-143:EXPLOIT     -> anima 119..143 sin tocar lo que ya está prendido
ADD:40-50:OFF           -> apaga 40..50 y deja el resto como está
```

Hasta 8 rangos a la vez, separados por coma (también LEDs sueltos: `PIX:5,12,30:FOCUS`). Cualquier
`SEG`/`ALL`/`IDLE`/`OFF` vuelve al modo tramos y borra esos rangos. La app usa solo los tramos; los rangos
sirven para probar y para efectos a mano.

**Por qué una sola cadena:** un solo pin y un solo canal del level shifter, menos cables y nada que
invertir por tramo. La contra: si se corta una unión o se quema un LED, se apaga todo lo que viene
después de ese punto (ver §7).

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
python tools/led_test.py --port COM3 PIX:0-9,40-50:FOCUS   # LEDs sueltos
python tools/led_test.py --port COM3 --interactive   # tipear comandos
```

Deberías ver: barrido al `DISCOVER`, tramo fijo al `FOCUS`, pulso ámbar al `EXPLOIT`, chase cyan al
`TRANSFER`, y `OFF` apaga todo. Para ubicar los tramos, `PIX:0-0:FOCUS`, `PIX:29-30:FOCUS`, etc. prenden
el borde exacto de cada uno. Si desde un punto en adelante no prende nada, revisá la unión de DATA ahí.

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
| Toda la animación va al revés | La cadena arranca del lado del FILE-SERVER: `STRIP_REVERSED = true`. |
| Un tramo prende LEDs del siguiente (rangos corridos) | `BRANCH_COUNTS` no coincide con lo cortado: contá los LEDs de cada tramo y corregí. |
| Los últimos LEDs de la tira no prenden | La suma de `BRANCH_COUNTS` es menor que los LEDs reales: corregí los números. |
| Colores equivocados | Orden de color; probar `RGB` en vez de `GRB` en `addLeds<...>`. |
| Desde un LED en adelante no prende nada | Unión DATA OUT → DATA IN cortada o al revés en ese punto, o ese LED quemado. |
| No prende ningún LED | Pin equivocado en el sketch, DATA IN del lado equivocado, o falta tierra común. |
| El micro no aparece en el puerto | Cable USB solo-carga (usar uno de datos), o falta el driver CH340/CP210x. |
| `scan` no devuelve hosts (modo real) | `nmap` no instalado, red mal cableada, o IPs fuera del CIDR de `config.toml`. |
| `ls`/`read` fallan (modo real) | SSH del nodo caído, o `ssh_user`/clave no coinciden con el contenedor. |
| Nada anda en vivo | Cambiar a **modo Simulado** (fallback) y seguir la muestra. |
