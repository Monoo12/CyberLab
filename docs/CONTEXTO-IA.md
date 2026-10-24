# NetLab — contexto completo del proyecto (para pasarle a una IA)

> **Para la IA que lee esto:** este documento es autocontenido. Describe un proyecto real (una
> estación interactiva de seguridad informática con un tablero de LEDs) con **énfasis en el circuito
> eléctrico**. Al final (§10) hay preguntas concretas. Respondé con recomendaciones **accionables**:
> valores de componentes, números de parte, qué pin va a dónde, qué línea del firmware cambiar, y una
> prioridad (crítico / importante / opcional). Si asumís algo que no está acá, decilo explícitamente.
> Respetá las decisiones marcadas como **fijas** (§5.1 y §7): no propongas cambiarlas salvo que sean
> un riesgo de seguridad eléctrica real, y en ese caso justificalo.
>
> Fuente de verdad: el repo `github.com/Monoo12/CyberLab` (rama `main`, commit `5bb3183`,
> 2026-10-14). Si este texto y el código difieren, manda el código.

---

## 1. Resumen en 30 segundos

- **Qué es:** una experiencia para una muestra/exposición. Un visitante se sienta en una PC
  ("TERMINAL") y cumple una misión de "hacking" guiada en ~5 minutos: escanear la red → encontrar un
  servidor → explotar una vulnerabilidad → leer un archivo secreto.
- **Lo físico:** un tablero (aprox. 1×1 m, según el historial del repo; a confirmar) con equipos de
  red reales (router + 2 switches) y cables de red. Junto al camino de los cables va una **tira LED
  WS2812B cortada en 4 tramos** que anima "por dónde viajan los datos" según lo que el visitante
  tipea.
- **Cómo se controla la luz:** la app de la PC le manda líneas de texto por **USB serial** a un
  **ESP8266 (NodeMCU)**, que maneja los 4 tramos (un pin de datos por tramo) con FastLED. **No se
  usa WiFi.**
- **Alimentación de los LEDs:** fuente switching **5 V / 10 A**. El firmware limita el consumo a 9 A.
  El ESP8266 se alimenta por el USB de la PC, no de la fuente; solo comparte GND con ella.
- **Riesgo eléctrico principal:** el ESP8266 saca datos a **3,3 V** y el WS2812B espera ≥3,5 V →
  hace falta un **level shifter 74AHCT125** (está en la lista de materiales).

---

## 2. La experiencia (qué ve el visitante)

1. Pantalla de espera (efecto "matrix"). LEDs: respiración verde tenue (`IDLE`).
2. Briefing + cronómetro de 5 min. LEDs: apagados (`OFF`).
3. `scan` → descubre los equipos de la red. LEDs: se enciende la ruta hacia cada equipo que aparece, uno
   tras otro (`DISCOVER`, barrido).
4. `inspect <ip>` / `connect <ip:80>` → puertos del objetivo / abre su web en el navegador. LEDs: ruta
   al objetivo fija (`FOCUS`).
5. `exploit <ip>` → ataca el login (3 métodos: credenciales filtradas en el HTML, inyección SQL, fuerza
   bruta con diccionario). LEDs: pulso ámbar intenso (`EXPLOIT`) y luego `FOCUS`.
6. `ls` / `cd` / `read /restricted/secret.txt` → lee el archivo secreto. LEDs: chase cyan
   (`TRANSFER`).
7. "Mission Complete". LEDs: todos los tramos en `TRANSFER`.

Hay 4 dificultades (fácil/medio/difícil/pro) y un "modo libre". Hay dos motores intercambiables:
**Simulado** (todo guionado, no toca la red; sirve para ensayar y como respaldo en vivo) y **Real**
(los comandos corren de verdad con nmap, HTTP y SSH contra el servidor). **La animación de LEDs es
idéntica en ambos motores**: la dispara la app, no se detecta tráfico de red.

---

## 3. Arquitectura general

```
                       ┌───────────────────────────── red Ethernet aislada (192.168.10.0/24) ─────────────────────────────┐
                       │                                                                                                   │
  PC TERMINAL (.10) ──cable── SWITCH-izq ──cable── ROUTER (.1) ──cable── SWITCH-der ──cable── FILE-SERVER (.20)            │
  (app Python)                                                                                (Docker: web :80 + SSH :2222)│
       │               └───────────────────────────────────────────────────────────────────────────────────────────────────┘
       │ USB (serial 115200 + 5 V para el micro)
       ▼
  ESP8266 NodeMCU ──4 líneas de datos──► level shifter 74AHCT125 ──► 4 tramos de tira WS2812B (uno por cable de red)
                                                                            ▲
                                       Fuente 5 V / 10 A ───────────────────┘ (+5 V y GND a los 4 tramos; GND común con el micro)
```

| Pieza | Qué es | Notas |
|---|---|---|
| **PC TERMINAL** | Windows o Linux. Corre la app del visitante (Python 3.11+, customtkinter, pyserial). | El ESP8266 se enchufa acá por USB. |
| **FILE-SERVER** | PC/mini-PC con Docker. Contenedor vulnerable a propósito (Flask en :80, SSH en host:2222). | Único servidor "real" en modo Real. |
| **Router** | TP-Link AX3000 (Archer o Deco), LAN `192.168.10.1`, sin WAN, WiFi apagado. | |
| **Switches** | 2× TP-Link TL-SG1008D (no administrables). | Dos por estética del tablero (izq/der). |
| **Micro** | ESP8266 NodeMCU, solo USB serial. | Elegido por el usuario; fijo. |
| **LEDs** | Tira WS2812B 5 V, 60 LED/m, rollo de 5 m; se usan 144 LEDs (~2,4 m). | 4 tramos, 4 pines. |
| **Fuente LEDs** | Switching 5 V / 10 A (50 W). | Fija. |

"WORKSTATION" (.30) y "SECURITY" (.40) aparecen en el mapa de la pantalla pero **no existen
físicamente** (solo en modo Simulado) y **no tienen tramo de LED**.

---

## 4. Software (resumen, solo lo necesario para entender el circuito)

- `app/` — app del visitante. La orquestación (terminal + mapa en pantalla + LEDs + tiempos) vive en
  `app/mission/flow.py`. Los backends (simulado/real) solo devuelven datos.
- `app/leds/controller.py` — abre el puerto serie (`pyserial`, 115200, timeout 0,2 s) y escribe
  líneas ASCII terminadas en `\n`. **No lee nada del micro** (no hay ACK ni handshake). Si no hay
  dispositivo, degrada a "modo log" (imprime las líneas en consola) y la app sigue funcionando.
- `app/leds/segments.py` — mapeo "a qué equipo voy → qué tramos enciendo". Es espejo del firmware.
- `firmware/netlab_leds/netlab_leds.ino` — sketch Arduino/FastLED (copia completa en el Anexo A).
- `tools/led_test.py` — prueba los LEDs sin la app (`--port COM3`, comando suelto o modo interactivo;
  espera 2 s tras abrir el puerto por el auto-reset del micro).
- `node/` — el servidor vulnerable (Docker). No tiene relación eléctrica con el tablero.
- Puerto serie configurado en `config.toml` → `[serial] enabled/port/baud` (`COM3` en Windows,
  `/dev/ttyUSB0` en Linux).

---

## 5. EL CIRCUITO (parte principal)

### 5.1 Decisiones fijas (tomadas por el usuario; no proponer cambiarlas)

| Decisión | Valor |
|---|---|
| Tira | WS2812B, 5 V, 60 LED/m, rollo de 5 m (~300 LEDs disponibles) |
| Micro | ESP8266 **NodeMCU 1.0 (ESP-12E)** |
| Enlace app→micro | **USB serial** únicamente (nunca WiFi), 115200 baud |
| Fuente | Switching **5 V / 10 A (50 W)** |
| Topología LED | **4 tramos**, **un pin de datos por tramo** (ver §5.3) |
| Largos medidos | T1 50 cm · T2 77 cm · T3 73 cm · T4 43 cm |
| Alimentación del micro | Por el USB de la PC TERMINAL (no desde la fuente de 5 V) |
| Plataforma | Todo debe funcionar con la PC TERMINAL en **Windows y en Linux** |

### 5.2 Lista de materiales (estado conocido)

| Componente | Detalle | Estado |
|---|---|---|
| Tira LED | WS2812B 5 V, 60 LED/m, 5 m. Variante (IP30/IP65, ancho de PCB, WS2812B vs WS2812B-V5) **desconocida** | Fijo |
| Microcontrolador | ESP8266 NodeMCU + cable USB **de datos**. Chip USB-serie (CH340 o CP2102) **desconocido** | Fijo |
| Fuente | Switching 5 V / 10 A, 50 W. Formato (gabinete metálico con borneras, adaptador, etc.) **desconocido** | Fijo |
| Level shifter | **74AHCT125** (4 buffers, uno por tramo). Alternativa citada: 74HCT245. Formato (DIP/SOIC/módulo) y si ya está comprado: **desconocido** | Previsto (en la lista de materiales) |
| Capacitor | 1000 µF en la alimentación de la tira. Ubicación y tensión nominal no definidas | "Opcional" en la lista |
| Cables / estaño | Calibres **no especificados** | — |
| Resistencias serie en datos | — | **No están en el diseño** |
| Pull-downs en datos | — | **No están en el diseño** |
| Fusibles | — | **No están en el diseño** |

### 5.3 Topología física del tablero

El camino de LEDs sigue exactamente el camino de los cables de red, en forma de **"U" invertida**.
Interpretación (a confirmar): TERMINAL y FILE-SERVER en los extremos de abajo, switches en las
esquinas de arriba, router arriba al centro.

```
           SWITCH-izq ════ T2: 77 cm · 46 LEDs ════ ROUTER ════ T3: 73 cm · 43 LEDs ════ SWITCH-der
               ║                                                                            ║
        T1: 50 cm · 30 LEDs                                                          T4: 43 cm · 25 LEDs
               ║                                                                            ║
          TERMINAL (.10)                                                             FILE-SERVER (.20)

   Sentido lógico de todas las animaciones: TERMINAL ──► FILE-SERVER
```

| Tramo | id serial | Recorrido | Largo | LEDs | `#define` | Pin NodeMCU previsto |
|:---:|:---:|---|:---:|:---:|:---:|:---:|
| T1 | 0 | TERMINAL → switch-izq | 50 cm | 30 | `PIN_B0` | D1 (GPIO5) |
| T2 | 1 | switch-izq → router | 77 cm | 46 | `PIN_B1` | D2 (GPIO4) |
| T3 | 2 | router → switch-der | 73 cm | 43 | `PIN_B2` | D5 (GPIO14) |
| T4 | 3 | switch-der → FILE-SERVER | 43 cm | 25 | `PIN_B3` | D6 (GPIO12) |
| | | | **2,43 m** | **144** | | |

- A 60 LED/m hay un LED (y una marca de corte) cada ~1,67 cm; los LEDs son los que entran en cada
  largo, redondeando para abajo.
- Cada tramo es una tira independiente con 3 conexiones: +5 V, GND, DIN. **Los tramos no están
  encadenados en datos** (no hay DOUT→DIN entre tramos).
- En el firmware `BRANCH_REVERSED = {false, false, false, false}`: se asume que el DIN de cada tramo
  está del lado TERMINAL. Si un tramo quedó al revés, se corrige por software sin recablear.
- **No se sabe dónde va físicamente el ESP8266** (probablemente cerca de la TERMINAL, porque va por
  USB a esa PC). Si es así, las líneas de datos hasta el DIN de T3 y T4 podrían medir del orden de
  1–2 m siguiendo el recorrido. **Dato a confirmar** (ver §9).

### 5.4 Esquema eléctrico tal como está diseñado hoy

Diagrama de bloques:

```
  PC TERMINAL ══ USB ══► ESP8266 NodeMCU  (se alimenta del USB; NO conectado al +5 V de la fuente)
                          │D1      │D2      │D5       │D6          ← 3,3 V lógicos
                          ▼        ▼        ▼         ▼
                       ┌──────────────── 74AHCT125 ────────────────┐  VCC = +5 V de la fuente
                       │ 1A→1Y    2A→2Y    3A→3Y     4A→4Y         │  GND = GND común
                       └──┬────────┬────────┬─────────┬────────────┘
                          ▼        ▼        ▼         ▼              ← 5 V lógicos
                        DIN T1   DIN T2   DIN T3    DIN T4

  FUENTE 5V/10A  +5V ──► +5V T1 (inicio) · T2 (inicio y fin) · T3 (inicio y fin) · T4 (inicio) · VCC 74AHCT125
                 GND ──► GND T1..T4 (mismos puntos) · GND 74AHCT125 · GND del ESP8266  ← tierra común obligatoria
                         (+ capacitor 1000 µF entre +5V y GND, "opcional", sin ubicación definida)
```

Netlist (lo documentado + lo implícito marcado como tal):

| Nodo / conexión | Desde | Hacia | Fuente del dato |
|---|---|---|---|
| +5 V LEDs | Fuente V+ | +5 V de T1..T4 en el extremo DIN; T2 y T3 también en el extremo final ("inyección en ambos extremos") | Docs |
| GND | Fuente V− | GND de T1..T4 en los mismos puntos + GND del ESP8266 | Docs ("tierra común, error #1") |
| Datos T1 | ESP8266 D1 (GPIO5) | 74AHCT125 1A (pin 2) → 1Y (pin 3) → DIN T1 | Docs (pin del chip: estándar) |
| Datos T2 | ESP8266 D2 (GPIO4) | 2A (pin 5) → 2Y (pin 6) → DIN T2 | Docs |
| Datos T3 | ESP8266 D5 (GPIO14) | 3A (pin 9) → 3Y (pin 8) → DIN T3 | Docs |
| Datos T4 | ESP8266 D6 (GPIO12) | 4A (pin 12) → 4Y (pin 11) → DIN T4 | Docs |
| VCC 74AHCT125 (pin 14) | +5 V fuente | | Implícito (necesario para salir a 5 V) |
| GND 74AHCT125 (pin 7) | GND común | | Implícito |
| 1OE/2OE/3OE/4OE (pines 1, 4, 10, 13) | **No documentado** | (activos en bajo: deberían ir a GND) | **Falta** |
| Alimentación ESP8266 | USB de la PC | Vin/3V3 del NodeMCU **sin** conexión a la fuente | Docs ("nunca desde el 5 V de la fuente") |

Pinout de referencia del 74AHCT125 (DIP-14/SOIC-14): 1=1OE, 2=1A, 3=1Y, 4=2OE, 5=2A, 6=2Y, 7=GND,
8=3Y, 9=3A, 10=3OE, 11=4Y, 12=4A, 13=4OE, 14=VCC.

### 5.5 Presupuesto de potencia

Supuestos: ~20 mA por canal a 255 en un WS2812B (~60 mA blanco pleno), brillo global del firmware
`setBrightness(140)` ≈ 55 %, ~1 mA de reposo por LED. Estimación para los **144 LEDs en la misma
animación** (el peor caso real es el `EXPLOIT` del FILE-SERVER, que enciende los 4 tramos):

| Estado | Color (R,G,B) | ≈ mA por LED | ≈ Total 144 LEDs |
|---|---|:---:|:---:|
| `OFF` | negro | ~1 (reposo) | ~0,15 A |
| `IDLE` (pico de la respiración) | (6,40,8) | ~3 | ~0,5 A |
| `FOCUS` | (20,120,30) | ~8 | ~1,2 A |
| `DISCOVER` (barrido, dura 0,9 s y pasa a FOCUS) | (40,255,40) | ~15 | ~2,2 A |
| `EXPLOIT` (pico del pulso) | (255,150,0) | ~18 | **~2,7 A** |
| `TRANSFER` (3 LEDs brillantes por tramo + fondo tenue) | (40,220,220)/(0,20,20) | — | ~0,7 A |
| Blanco pleno a brillo 140 (no ocurre) | (255,255,255) | ~33 | ~4,7 A |
| Blanco pleno a brillo 255 (teórico) | (255,255,255) | ~60 | ~8,6 A |

- El firmware llama `FastLED.setMaxPowerInVoltsAndMilliamps(5, 9000)`: FastLED **estima** (no mide)
  el consumo de cada frame y baja el brillo si superaría 9 A. Con las animaciones actuales nunca se
  activa; es una red de seguridad.
- Por tramo, el máximo es T2 (46 LEDs) en `EXPLOIT`: ~0,8 A.
- Corriente de falla: sin fusibles, un corto en cualquier tramo puede recibir la corriente máxima de
  la fuente (≥10 A).

### 5.6 Señal de datos

- WS2812B: protocolo de un hilo a 800 kHz; "1" lógico mínimo ≈ 0,7 × VDD = **3,5 V** con VDD = 5 V.
- ESP8266: salida de 3,3 V → por debajo del umbral. Por eso el **74AHCT125** (entradas TTL, VIH ≈ 2 V,
  alimentado a 5 V → salida 5 V).
- Alternativas que se mencionan en las docs (de peor fiabilidad): bajar la tira a ~4,3–4,5 V con un
  diodo en serie; o un "primer LED sacrificable" cerca del micro.
- Hoy **no hay** resistencia serie en la salida de datos, **no hay** pull-downs y **no se especificó**
  el largo ni el tipo de cable de datos (¿par con GND al lado? ¿cable plano? ¿UTP?).
- Al encender la fuente antes de que el micro arranque, o mientras el micro se reinicia (el NodeMCU se
  resetea cuando la app abre el puerto serie, por DTR/RTS), las entradas del shifter pueden quedar
  flotando.

### 5.7 Firmware (resumen; código completo en el Anexo A)

- FastLED, 4 controladores `WS2812B` con orden de color `GRB`, uno por pin.
- `BRANCH_COUNTS = {30, 46, 43, 25}`; `MAX_LEDS` se calcula solo (constexpr) con el mayor → 4 buffers
  de 46 LEDs.
- `setBrightness(140)` + `setMaxPowerInVoltsAndMilliamps(5, 9000)`.
- Loop no bloqueante: lee el serial byte a byte (buffer de línea `String`, máx. 64 caracteres) y cada
  16 ms (~60 fps) renderiza los 4 tramos y hace `FastLED.show()`.
- Animaciones calculadas desde `millis()`; cada tramo tiene su propio estado y su tiempo de inicio.
- **Pines en el código hoy:** `#define PIN_B0 2`, `PIN_B1 3`, `PIN_B2 4`, `PIN_B3 5` (valores pensados
  para Arduino UNO). Las docs indican **editarlos a mano** a `D1, D2, D5, D6` antes de subir a un
  ESP8266. Ver §8 sobre por qué esto es delicado.
- No hace `WiFi.mode(WIFI_OFF)`; no responde nada por serial (sin ACK, sin versión, sin heartbeat).

### 5.8 Protocolo serial y qué dispara cada cosa

Líneas ASCII terminadas en `\n`, 115200 baud, solo de la PC al micro:

| Comando | Efecto |
|---|---|
| `IDLE` | Todos los tramos: respiración verde tenue |
| `OFF` | Todo apagado |
| `SEG:<id>:<anim>` | Anima un tramo (`id` 0..3) |
| `ALL:<anim>` | Anima los 4 tramos |

`<anim>` = `DISCOVER` (barrido verde ~600 ms, a los 900 ms pasa solo a FOCUS) · `FOCUS` (verde fijo
medio) · `EXPLOIT` (pulso ámbar rápido) · `TRANSFER` (chase cyan, 1 LED cada 40 ms).

Ruta de tramos por destino (lo que la app enciende para "llegar" a un equipo):

| Destino | Tramos (ids) |
|---|---|
| terminal | 0 |
| router | 0, 1 |
| fileserver | 0, 1, 2, 3 |
| workstation / security (solo simulado) | 0, 1, 2 |

La app manda **un `SEG:` por tramo** (no hay comando multi-tramo). Ejemplo de misión completa:

```
IDLE
OFF
SEG:0:DISCOVER SEG:1:DISCOVER                                   (scan: aparece el router; ~420 ms entre equipos)
SEG:0:DISCOVER                                                  (scan: terminal)
SEG:0:DISCOVER SEG:1:DISCOVER SEG:2:DISCOVER SEG:3:DISCOVER     (scan: file-server)
SEG:0:FOCUS SEG:1:FOCUS SEG:2:FOCUS SEG:3:FOCUS                 (inspect / connect)
SEG:0:EXPLOIT SEG:1:EXPLOIT SEG:2:EXPLOIT SEG:3:EXPLOIT         (exploit en curso)
SEG:0:FOCUS ... SEG:3:FOCUS                                     (acceso concedido)
SEG:0:TRANSFER ... SEG:3:TRANSFER                               (read secret.txt)
ALL:TRANSFER                                                    (Mission Complete)
```

El tráfico serial es mínimo (decenas de bytes por segundo como mucho).

### 5.9 Cómo se prueba hoy

1. Arduino IDE + soporte de placas ESP8266 + librería FastLED; placa "NodeMCU 1.0 (ESP-12E Module)".
2. Editar pines, subir el sketch, probar a mano desde el Monitor Serie (115200): `SEG:3:EXPLOIT`,
   `ALL:TRANSFER`, `OFF`.
3. `python tools/led_test.py --port COM3` (secuencia demo) o `--interactive`.
4. Tabla de fallas en `docs/GUIA-HARDWARE.md` §7 (sin GND común → parpadeos; sin shifter → colores
   random; flecha de DIN al revés → tramo muerto; etc.).

**Estado:** el diseño y los largos están definidos y medidos; **no hay registro** de que el tablero
ya esté soldado y probado, ni de síntomas observados.

---

## 6. Red (resumen)

- `192.168.10.0/24`. Router `.1`, TERMINAL `.10`, FILE-SERVER `.20` (reservas DHCP por MAC). `.30` y
  `.40` son decorativos/simulados.
- Cableado en árbol: router LAN1 → switch-izq (→ TERMINAL), router LAN2 → switch-der (→ FILE-SERVER).
  Los switches no se conectan entre sí (no tienen STP; un anillo tumba la red).
- Red **aislada de internet** (el servidor es vulnerable a propósito). El micro de LEDs **no** está en
  la red.

---

## 7. Restricciones transversales

- Todo debe correr con la TERMINAL en **Windows y Linux** (puerto `COMx` o `/dev/ttyUSB*`; en Linux
  el usuario necesita el grupo `dialout`).
- El modo **Simulado** tiene que seguir funcionando sin ningún hardware conectado.
- El protocolo serial y el mapeo de tramos son un **contrato** entre `app/leds/segments.py`,
  `app/ui/netmap.py` (`_SEG_LINKS`), el firmware y `docs/LEDS.md`. Si una recomendación cambia el
  protocolo, los ids o la cantidad de tramos, hay que actualizar los cuatro.
- No exponer el servidor vulnerable fuera de la red del laboratorio ni "arreglar" sus vulnerabilidades
  (son la gracia de la experiencia).
- Uso previsto: muestra pública, horas seguidas encendido, público cerca del tablero.

---

## 8. Observaciones de una revisión previa (a validar por vos)

Puntos que encontramos leyendo el código y las docs. Confirmalos, descartalos o mejorá la solución.

**Posiblemente críticos**

1. **Pines por defecto del sketch en ESP8266.** El código trae `2, 3, 4, 5`. En el ESP8266, GPIO3 es
   **RX0**, el pin por el que llegan los comandos del USB: si FastLED lo toma como salida, el micro
   dejaría de recibir comandos. GPIO2 es pin de *strapping* de arranque. Hoy depende de que quien
   arma se acuerde de editar los `#define`. Idea: `#if defined(ESP8266)` con los pines correctos por
   defecto.
2. **Numeración de pines de FastLED en ESP8266.** FastLED tiene varios órdenes de pines para ESP8266
   (RAW = número de GPIO, NODEMCU = número "Dx") y elige uno según defines de la placa, que cambian
   entre versiones del core. Si queda en orden NODEMCU, escribir `D1` (que vale 5) podría terminar en
   D5/GPIO14. Verificar con las versiones instaladas; una opción robusta es
   `#define FASTLED_ESP8266_RAW_PIN_ORDER` antes de `#include <FastLED.h>` y usar números de GPIO
   (5, 4, 14, 12).
3. **OE del 74AHCT125 sin documentar.** Son activos en bajo; si quedan al aire, el comportamiento del
   canal es indefinido.

**Importantes**

4. **Largo de las líneas de datos** desde el micro hasta el DIN de cada tramo (posiblemente 1–2 m
   para T3/T4) sin resistencia serie ni retorno de GND junto a la señal. Alternativa a evaluar
   (cambiaría una decisión de diseño, solo si lo justifica): encadenar DOUT→DIN entre tramos
   consecutivos y usar un solo pin, separando los tramos por software.
5. **Sin fusibles** entre la fuente de 10 A y los tramos; calibre de los cables de alimentación no
   especificado.
6. **Estado de la tira con el micro apagado o reiniciándose** (entradas del shifter flotando →
   destellos o colores al azar). Idea: pull-downs en las entradas del shifter; orden de encendido.
7. **WiFi del ESP8266 no se apaga** explícitamente en el firmware (puede quedar activo por
   configuración persistida, con picos de consumo e interrupciones que afectan el timing).
8. **Sin realimentación**: la app no puede saber si el micro conectado es el correcto ni si está vivo.

**Menores**

9. Parser con `String` dinámico (riesgo bajo de fragmentación del heap; el largo está acotado a 64).
10. El capacitor de 1000 µF figura como "opcional" y sin ubicación.
11. El primer comando tras abrir el puerto puede perderse por el auto-reset del NodeMCU (hoy no importa
    porque el firmware arranca en `IDLE`, que coincide con lo que la app manda al iniciar).
12. Interrupciones durante `show()` en ESP8266 (`FASTLED_ALLOW_INTERRUPTS`): si aparecen parpadeos,
    es un parámetro a probar.

---

## 9. Datos que faltan (si los necesitás, asumí un valor razonable y decilo)

- Ubicación física del ESP8266 y del level shifter en el tablero; largo de cada línea de datos.
- De qué extremo entra el DIN en cada tramo.
- Ubicación de la fuente, largo y calibre de los cables de +5 V/GND, tipo de conectores (¿JST-SM de
  3 pines? ¿soldado?).
- Cómo se cablea la entrada de red eléctrica de la fuente (tensión local, gabinete, interruptor,
  fusible, puesta a tierra).
- Si la fuente tiene V− unido a tierra (afecta posibles lazos de tierra con la PC, que también va a
  tierra y comparte GND por USB).
- Si el 74AHCT125 ya está comprado y en qué formato.
- Variante del NodeMCU (CH340/CP2102; v2 Amica / v3 LoLin) y versiones del core ESP8266 y de FastLED.
- Variante exacta de la tira (IP30/IP65, ancho, WS2812B vs WS2812B-V5).
- Material del tablero, si hay difusor sobre la tira y cómo se fija.
- Si ya se montó algo y qué síntomas hubo.

---

## 10. Qué te pedimos

Respondé por secciones, priorizando (crítico / importante / opcional), con valores y números de parte:

1. **Esquema final**: validá o corregí el netlist de §5.4 y proponé el definitivo, incluyendo
   resistencias serie en datos (valor y dónde van), pull-downs, capacitores (valor, tensión, dónde),
   OE del 74AHCT125 y cualquier componente que falte.
2. **Distribución de energía**: calibre de cable para el bus de 5 V y para cada tramo, puntos de
   inyección necesarios de verdad con estas corrientes (§5.5), fusibles (tipo y valor, ¿uno por
   tramo?), y cuidados con la entrada de red de la fuente.
3. **Integridad de señal**: con las longitudes posibles de §5.3, ¿4 líneas paralelas desde un punto
   están bien o conviene encadenar? ¿Qué cable usar para datos y cómo llevar el GND?
4. **Tierras y secuencia de encendido**: micro por USB + LEDs por fuente con GND común; ¿qué pasa si
   se enciende uno antes que el otro? ¿Hace falta algo más?
5. **Firmware**: cambios concretos (con código) para los puntos 1, 2, 6, 7, 8, 9 y 12 de §8, sin
   romper el protocolo de §5.8.
6. **Puesta en marcha**: un procedimiento de prueba paso a paso con multímetro (qué medir y qué valor
   esperar) antes de conectar la PC y antes del evento.
7. Cualquier riesgo que no hayamos visto, pensando en un uso de muchas horas con público cerca.

---

## Anexo A — Firmware completo (`firmware/netlab_leds/netlab_leds.ino`, commit `5bb3183`)

```cpp
/* ==========================================================================
 * NetLab - firmware de la tira LED (Arduino / ESP8266 / ESP32)
 *
 * Recibe comandos de texto por USB serial desde la app del visitante y anima
 * los tramos ("ramas") de la red sobre el tablero. NO usa WiFi ni red: solo lee
 * lineas del Serial. Animaciones NO bloqueantes (maquina de estados con millis()),
 * asi la lectura serial nunca se congela.
 *
 * Protocolo (una linea por comando, terminada en \n):
 *   IDLE                -> shimmer/breathing tenue de espera (todas las ramas)
 *   OFF                 -> apaga todo
 *   SEG:<id>:<anim>     -> anima UNA rama.  id = 0..NUM_BRANCHES-1
 *   ALL:<anim>          -> anima TODAS las ramas
 *   <anim> = DISCOVER | FOCUS | EXPLOIT | TRANSFER
 *
 * Cableado (ver docs/GUIA-HARDWARE.md): una tira por rama, cada una a su pin de
 * datos. 5V y GND compartidos con la fuente; GND de la fuente unido al GND del
 * micro. Ajusta los pines, los largos (BRANCH_COUNTS) y el sentido
 * (BRANCH_REVERSED) al tablero real.
 *
 * Requiere la libreria FastLED.  El mapeo id->rama es espejo de
 * app/leds/segments.py (rama 0 = Tramo 1: terminal<->switch-izq, etc.).
 * ========================================================================== */

#include <FastLED.h>

#define NUM_BRANCHES 4

// --- Pines de datos por rama (AJUSTAR al hardware) -------------------------
// En placas tipo Arduino UNO/Nano: 2,3,4,5.  En ESP8266 (NodeMCU) usar
// D1,D2,D5,D6 (GPIO5,4,14,12).  En ESP32: casi cualquier GPIO de salida.
#define PIN_B0 2
#define PIN_B1 3
#define PIN_B2 4
#define PIN_B3 5

// --- Cantidad de LEDs por rama (largo real de cada tramo) -------------------
// Tira WS2812B 5V 60 LED/m (1 LED cada ~1,67 cm). El tablero es una cadena de
// 4 tramos; cada numero es la cantidad de LEDs que ENTRA en el tramo medido
// (redondeado para abajo, cortando por las marcas de la tira):
//   rama 0 = Tramo 1  TERMINAL   -> switch-izq   50 cm -> 30 LEDs
//   rama 1 = Tramo 2  switch-izq -> router       77 cm -> 46 LEDs
//   rama 2 = Tramo 3  router     -> switch-der   73 cm -> 43 LEDs
//   rama 3 = Tramo 4  switch-der -> FILE-SERVER  43 cm -> 25 LEDs
// Total 144 LEDs (~2,4 m de los 5 m). Si al cortar contas otro numero, pone el real.
constexpr int BRANCH_COUNTS[NUM_BRANCHES] = { 30, 46, 43, 25 };

// --- Sentido de cada rama ---------------------------------------------------
// Las animaciones recorren el camino TERMINAL -> FILE-SERVER. Si un tramo quedo
// con su DATA IN (la flecha) del lado opuesto, el barrido iria al reves: pone
// true en esa rama para invertirlo sin recablear.
constexpr bool BRANCH_REVERSED[NUM_BRANCHES] = { false, false, false, false };

// MAX_LEDS se deriva SOLO del mayor de BRANCH_COUNTS (dimensiona el buffer de
// cada rama). Asi los buffers nunca se desbordan aunque cambies los largos de
// arriba y te olvides de tocar otra cosa.
constexpr int _cmax2(int a, int b) { return a > b ? a : b; }
constexpr int _maxCount(int i = 0) {
  return i >= NUM_BRANCHES ? 0 : _cmax2(BRANCH_COUNTS[i], _maxCount(i + 1));
}
constexpr int MAX_LEDS = _maxCount();

// --- Estados de animacion ---------------------------------------------------
enum Anim { A_OFF = 0, A_IDLE, A_DISCOVER, A_FOCUS, A_EXPLOIT, A_TRANSFER };

CRGB leds0[MAX_LEDS], leds1[MAX_LEDS], leds2[MAX_LEDS], leds3[MAX_LEDS];
CRGB* const BRANCH_LEDS[NUM_BRANCHES] = { leds0, leds1, leds2, leds3 };

uint8_t  branchAnim[NUM_BRANCHES];
uint32_t branchT0[NUM_BRANCHES];

// Colores base
const CRGB C_GREEN = CRGB(40, 255, 40);
const CRGB C_DIMG  = CRGB(6, 40, 8);
const CRGB C_AMBER = CRGB(255, 150, 0);
const CRGB C_CYAN  = CRGB(40, 220, 220);

String rx;  // buffer de linea

void setAnim(int b, uint8_t a) {
  branchAnim[b] = a;
  branchT0[b] = millis();
}

void setup() {
  Serial.begin(115200);
  FastLED.addLeds<WS2812B, PIN_B0, GRB>(leds0, BRANCH_COUNTS[0]);
  FastLED.addLeds<WS2812B, PIN_B1, GRB>(leds1, BRANCH_COUNTS[1]);
  FastLED.addLeds<WS2812B, PIN_B2, GRB>(leds2, BRANCH_COUNTS[2]);
  FastLED.addLeds<WS2812B, PIN_B3, GRB>(leds3, BRANCH_COUNTS[3]);
  // Limite de consumo: la fuente es 5V/10A (50W). Con 144 LEDs el blanco pleno
  // rondaria 8,6A; igual FastLED autoescala el brillo en cada show() para no
  // pasar de 9000 mA (90%) si alargas tramos. Evita brownout/reset del micro. Es
  // independiente de setBrightness(): ese es el techo, esto es el limite de corriente.
  FastLED.setMaxPowerInVoltsAndMilliamps(5, 9000);
  FastLED.setBrightness(140);
  for (int b = 0; b < NUM_BRANCHES; b++) setAnim(b, A_IDLE);
  FastLED.clear(true);
}

// ---- Animaciones (todas calculan el frame en funcion de millis()) ----------
void renderBranch(int b) {
  CRGB* px = BRANCH_LEDS[b];
  int n = BRANCH_COUNTS[b];
  if (n <= 0) return;  // rama sin LEDs: nada que renderizar (evita % 0 y division por 0)
  uint32_t el = millis() - branchT0[b];

  switch (branchAnim[b]) {
    case A_OFF:
      fill_solid(px, n, CRGB::Black);
      break;

    case A_IDLE: {
      // respiracion lenta verde muy tenue
      uint8_t w = quadwave8((el / 12) & 0xFF);      // 0..255
      CRGB c = blend(CRGB::Black, C_DIMG, w);
      fill_solid(px, n, c);
      break;
    }

    case A_DISCOVER: {
      // barrido de encendido (~600ms) y luego queda tenue
      int lit = (el >= 600) ? n : (int)((el * n) / 600);
      for (int i = 0; i < n; i++) px[i] = (i < lit) ? C_GREEN : CRGB::Black;
      if (el >= 900) setAnim(b, A_FOCUS);
      break;
    }

    case A_FOCUS:
      fill_solid(px, n, CRGB(20, 120, 30));
      break;

    case A_EXPLOIT: {
      // pulso rapido ambar (recorrido "intenso")
      uint8_t w = triwave8((el / 3) & 0xFF);
      CRGB c = blend(CRGB(60, 20, 0), C_AMBER, w);
      fill_solid(px, n, c);
      break;
    }

    case A_TRANSFER: {
      // chase rapido cyan (transferencia de datos)
      int head = (el / 40) % n;
      for (int i = 0; i < n; i++) {
        int d = (head - i + n) % n;
        px[i] = (d < 3) ? blend(CRGB::Black, C_CYAN, 255 - d * 80) : CRGB(0, 20, 20);
      }
      break;
    }
  }

  // tramo cableado al reves: espejar el frame para que siga el sentido del camino
  if (BRANCH_REVERSED[b]) {
    for (int i = 0; i < n / 2; i++) {
      CRGB t = px[i];
      px[i] = px[n - 1 - i];
      px[n - 1 - i] = t;
    }
  }
}

uint8_t animFromToken(const String& t) {
  if (t == "DISCOVER") return A_DISCOVER;
  if (t == "FOCUS")    return A_FOCUS;
  if (t == "EXPLOIT")  return A_EXPLOIT;
  if (t == "TRANSFER") return A_TRANSFER;
  if (t == "IDLE")     return A_IDLE;
  return A_OFF;
}

void handleLine(String line) {
  line.trim();
  if (line.length() == 0) return;

  if (line == "IDLE") { for (int b = 0; b < NUM_BRANCHES; b++) setAnim(b, A_IDLE); return; }
  if (line == "OFF")  { for (int b = 0; b < NUM_BRANCHES; b++) setAnim(b, A_OFF);  return; }

  if (line.startsWith("ALL:")) {
    uint8_t a = animFromToken(line.substring(4));
    for (int b = 0; b < NUM_BRANCHES; b++) setAnim(b, a);
    return;
  }
  if (line.startsWith("SEG:")) {
    int c1 = line.indexOf(':');
    int c2 = line.indexOf(':', c1 + 1);
    if (c2 < 0) return;
    int id = line.substring(c1 + 1, c2).toInt();
    uint8_t a = animFromToken(line.substring(c2 + 1));
    if (id >= 0 && id < NUM_BRANCHES) setAnim(id, a);
    return;
  }
}

void loop() {
  // 1) leer comandos serial sin bloquear
  while (Serial.available()) {
    char ch = (char)Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (rx.length()) { handleLine(rx); rx = ""; }
    } else if (rx.length() < 64) {
      rx += ch;
    }
  }
  // 2) refrescar animaciones ~60fps
  static uint32_t last = 0;
  if (millis() - last >= 16) {
    last = millis();
    for (int b = 0; b < NUM_BRANCHES; b++) renderBranch(b);
    FastLED.show();
  }
}
```

## Anexo B — Lado PC del enlace serial (`app/leds/controller.py`, resumido)

```python
ser = serial.Serial(port, 115200, timeout=0.2)    # sin espera tras abrir (el NodeMCU se resetea)
def _send(line): ser.write((line + "\n").encode("ascii", "ignore"))   # solo escribe, nunca lee
idle()  -> "IDLE"      off() -> "OFF"
animate_segment(id, anim)    -> f"SEG:{id}:{anim}"
animate_segments(ids, anim)  -> un SEG por id
animate_all(anim)            -> f"ALL:{anim}"
# si no puede abrir el puerto o falla una escritura: pasa a "modo log" (print) y la app sigue
```
