# Guía de conexión del hardware

Sección especial para el momento de montar todo: la tira LED, el microcontrolador y los nodos.
El software ya está listo; esta guía explica cómo conectarlo al mundo físico.

> Ajustá siempre a tu tablero real. Los números (pines, cantidad de LEDs) son un punto de partida.

## 1. Cargar el firmware en el microcontrolador

1. Instalá el **Arduino IDE** y la librería **FastLED** (Gestor de librerías → "FastLED").
2. Abrí `firmware/cyberlab_leds/cyberlab_leds.ino`.
3. Elegí tu placa (Arduino UNO/Nano, ESP8266 NodeMCU o ESP32) y el puerto.
4. **Ajustá al tope del sketch** (ver sección 3): pines de datos y cantidad de LEDs por rama.
5. Subí el sketch. Al abrir el Monitor Serie (115200 baud) podés tipear comandos a mano
   (`SEG:2:EXPLOIT`, `ALL:TRANSFER`, `OFF`).

Sin WiFi de por medio, cualquiera de las tres placas sirve igual: el micro solo lee texto del USB.

## 2. Cableado de la tira LED (WS2812B / NeoPixel)

La tira es **direccionable** (cada LED se prende solo) — imprescindible para el efecto de recorrido.

- Comprá **una sola tira** (ej. rollo de 5 m) y cortala en los **5 pedazos** (uno por rama). No hacen
  falta 5 tiras separadas.
- Cada pedazo tiene 3 cables: **5V**, **GND** y **DATA IN**. Mirá la **flecha** impresa: el dato
  entra por el lado de la flecha. Conectada al revés **no funciona**.
- **5V y GND se comparten** entre todos los pedazos (todos a la misma fuente 5V).
- El **DATA de cada pedazo va a su propio pin** del micro (ver mapeo abajo).
- ⚠️ **Tierra común obligatoria**: el **GND del micro** tiene que estar unido al **GND de la fuente**
  que alimenta las tiras. Si no comparten tierra, la señal de datos se malinterpreta → LEDs que
  titilan o no prenden. Es el error #1.
- Si una cadena es larga, **inyectá 5V también al final** (no solo al principio) para que los últimos
  LEDs no se vean tenues o cambien de color por caída de tensión.

### Cuánta tira y qué fuente (tablero de 1×1 m, tira 60 LED/m)
- Los 5 tramos suman **~2,5–3 m** de tira → un **rollo de 5 m** te da margen de sobra (usás ~2,7 m,
  el resto queda para pruebas). Se corta cada 1 LED (~1,7 cm).
- A 60 LED/m eso son **~150–170 LEDs**. Un WS2812B a blanco pleno consume ~60 mA; el pico teórico
  sería alto, pero con brillo al ~55% y colores (no blanco) el consumo real es ~2–4 A. Usá una
  **fuente 5V de ≥ 5 A** (6 A ideal). *No* hace falta una de 20 A (eso es para 300 LEDs en blanco).
- No alimentes la tira desde el pin 5V del micro por USB: usá la fuente, con **GND común** con el micro.

## 3. Mapeo rama ↔ pin ↔ LEDs (espejo del software)

El firmware y `app/leds/segments.py` comparten el mismo mapeo. Hay **5 ramas** (una tira por rama):

| Rama (id) | Tramo físico | Pin por defecto | LEDs (est. 60/m, tablero 1 m) |
|---|---|---|---|
| 0 | router → switch-izq → **TERMINAL** | `PIN_B0` (D2/GPIO) | ~50 (tramo largo) |
| 1 | router → switch-der | `PIN_B1` | ~28 |
| 2 | switch-der → **FILE-SERVER** | `PIN_B2` | ~30 |
| 3 | switch-der → WORKSTATION-01 | `PIN_B3` | ~24 |
| 4 | switch-der → SECURITY-SERVER | `PIN_B4` | ~32 |

- Son **estimaciones** del layout escalado a 1 m con 60 LED/m (total ~164). Medí cada tramo con la
  tira puesta y afiná. El firmware ya trae estos valores (`BRANCH_COUNTS = {50,28,30,24,32}`, `MAX_LEDS 52`).
- Ajustá **dos cosas** en el sketch: `PIN_B0..PIN_B4` (a los pines que uses) y `BRANCH_COUNTS`
  (al largo real de cada tramo). `MAX_LEDS` debe ser **≥ el mayor** de `BRANCH_COUNTS`.
- Pines sugeridos por placa: Arduino UNO/Nano → 2,3,4,5,6. ESP8266 (NodeMCU) → D1,D2,D5,D6,D7
  (GPIO5,4,14,12,13). ESP32 → casi cualquier GPIO de salida.

**Por qué 5 tiras y no una sola:** una tira es una cadena en línea, no se ramifica sola. En el
tablero hay dos bifurcaciones (router→2 switches y switch-der→3 dispositivos). Usar un pin por rama
es lo más simple de cablear y de debuggear. FastLED maneja los 5 pines a la vez sin problema.

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
python tools/led_test.py --port COM3 SEG:2:EXPLOIT   # un comando puntual
python tools/led_test.py --port COM3 --interactive   # tipear comandos
```

Deberías ver: barrido al `DISCOVER`, tramo fijo al `FOCUS`, pulso ámbar al `EXPLOIT`, chase cyan al
`TRANSFER`, y `OFF` apaga todo. Si una rama no responde, revisá su pin de datos y la tierra común.

## 6. Conectar los nodos a la red

1. Armá el árbol físico: rosetas → switches → router, y los dispositivos (FILE-SERVER, etc.) a las
   bocas del switch derecho, la terminal al switch izquierdo (como el diagrama).
2. Asigná IPs fijas (o reservas DHCP) que coincidan con la sección `[[hosts]]` de `config.toml`.
3. En el equipo FILE-SERVER: `cd node && docker compose up -d --build`.
4. Verificá que la PC lo descubre: `nmap -sn 192.168.10.0/24` debería listar sus IPs.
5. Pasá la app a **Real** (`--engine real` o el menú).

## 7. Resolución de problemas

| Síntoma | Causa probable / arreglo |
|---|---|
| LEDs titilan o no prenden | **Falta tierra común** entre fuente y micro. Unir GND. |
| Solo prende el principio de una tira | Cadena larga sin re-inyección de 5V; inyectar 5V al final. |
| Colores equivocados | Orden de color; probar `RGB` en vez de `GRB` en `addLeds<...>`. |
| Una rama entera muerta | Flecha de DATA al revés, o pin equivocado en el sketch. |
| El micro no aparece en el puerto | Cable USB solo-carga (usar uno de datos), o falta el driver CH340/CP210x. |
| `scan` no devuelve hosts (modo real) | `nmap` no instalado, red mal cableada, o IPs fuera del CIDR de `config.toml`. |
| `ls`/`read` fallan (modo real) | SSH del nodo caído, o `ssh_user`/clave no coinciden con el contenedor. |
| Nada anda en vivo | Cambiar a **modo Simulado** (fallback) y seguir la muestra. |
