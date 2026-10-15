/* ==========================================================================
 * Cyber Lab - firmware de la tira LED (Arduino / ESP8266 / ESP32)
 *
 * Recibe comandos de texto por USB serial desde la app del visitante y anima
 * los tramos de la red sobre el tablero. NO usa WiFi ni red: solo lee lineas
 * del Serial. Animaciones NO bloqueantes (maquina de estados con millis()),
 * asi la lectura serial nunca se congela.
 *
 * Protocolo (una linea por comando, terminada en \n):
 *   IDLE                  -> shimmer/breathing tenue de espera (toda la tira)
 *   OFF                   -> apaga todo
 *   SEG:<id>:<anim>       -> anima UN tramo.  id = 0..NUM_BRANCHES-1
 *   ALL:<anim>            -> anima TODOS los tramos
 *   PIX:<rangos>:<anim>   -> anima solo esos LEDs y apaga el resto
 *   ADD:<rangos>:<anim>   -> anima esos LEDs sin tocar el resto
 *   <anim>   = DISCOVER | FOCUS | EXPLOIT | TRANSFER | IDLE | OFF
 *   <rangos> = LEDs sueltos o rangos inclusivos separados por coma, contando
 *              desde 0 en el extremo de la TERMINAL. Ej: PIX:0-9,40-50:FOCUS
 *   SEG/ALL/IDLE/OFF vuelven al modo tramos (borran los rangos de PIX/ADD).
 *
 * Cableado (ver docs/GUIA-HARDWARE.md): UNA sola tira encadenada (el DATA OUT
 * de un tramo va al DATA IN del siguiente) en un unico pin de datos. 5V y GND a
 * la fuente; GND de la fuente unido al GND del micro. Cada tramo es un rango de
 * LEDs de esa tira (BRANCH_COUNTS).
 *
 * Requiere la libreria FastLED.  El mapeo id->tramo es espejo de
 * app/leds/segments.py (id 0 = Tramo 1: terminal<->switch-izq, etc.).
 * ========================================================================== */

// En ESP8266 los numeros de pin son GPIO (asi D1 = GPIO5 sea cual sea la placa
// elegida en el IDE). No afecta a otras placas.
#define FASTLED_ESP8266_RAW_PIN_ORDER
#include <FastLED.h>

// --- Pin de datos (AJUSTAR si usas otro) ------------------------------------
// ESP8266 (NodeMCU): 5 = GPIO5 = pin D1.  Arduino UNO/Nano: cualquier digital
// (ej. 6).  ESP32: casi cualquier GPIO de salida.
#if defined(ESP8266)
#define DATA_PIN 5
#else
#define DATA_PIN 6
#endif

#define NUM_BRANCHES 4

// --- Cantidad de LEDs por tramo (largo real de cada tramo) ------------------
// Tira WS2812B 5V 60 LED/m (1 LED cada ~1,67 cm). El tablero es una cadena de
// 4 tramos; cada numero es la cantidad de LEDs que ENTRA en el tramo medido
// (redondeado para abajo, cortando por las marcas de la tira):
//   id 0 = Tramo 1  TERMINAL   -> switch-izq   50 cm -> 30 LEDs  (LED   0..29)
//   id 1 = Tramo 2  switch-izq -> router       77 cm -> 46 LEDs  (LED  30..75)
//   id 2 = Tramo 3  router     -> switch-der   73 cm -> 43 LEDs  (LED  76..118)
//   id 3 = Tramo 4  switch-der -> FILE-SERVER  43 cm -> 25 LEDs  (LED 119..143)
// Total 144 LEDs (~2,4 m de los 5 m). Si al cortar contas otro numero, pone el real.
const int BRANCH_COUNTS[NUM_BRANCHES] = { 30, 46, 43, 25 };

// --- Sentido de la tira -----------------------------------------------------
// Los numeros de LED cuentan desde la TERMINAL (LED 0) hacia el FILE-SERVER y las
// animaciones avanzan en ese sentido. Lo normal es meter el DATA IN por el extremo
// de la TERMINAL. Si la cadena arranca del lado del FILE-SERVER, pone true: el
// firmware da vuelta todo y los numeros siguen contando desde la TERMINAL.
const bool STRIP_REVERSED = false;

// Tope del buffer: el rollo entero (5 m x 60 LED/m). El largo real (numLeds) y el
// inicio de cada tramo se calculan solos en setup() a partir de BRANCH_COUNTS.
#define MAX_LEDS 300

// Maximo de rangos simultaneos de PIX/ADD (los de mas se ignoran).
#define MAX_PIX_ZONES 8

// --- Estados de animacion ---------------------------------------------------
// (los tipos van antes de cualquier funcion: el IDE de Arduino genera los
// prototipos arriba de la primera funcion y tienen que conocer Zone)
enum Anim { A_OFF = 0, A_IDLE, A_DISCOVER, A_FOCUS, A_EXPLOIT, A_TRANSFER };

// Una zona es un rango de LEDs que se anima como una unidad.
struct Zone {
  int      start;  // primer LED (contando desde la TERMINAL)
  int      len;
  uint8_t  anim;
  uint32_t t0;
};

CRGB leds[MAX_LEDS];
int  numLeds = 0;                 // suma de BRANCH_COUNTS (tope MAX_LEDS)
Zone branches[NUM_BRANCHES];      // los tramos fijos (SEG/ALL/IDLE/OFF)
Zone pixZones[MAX_PIX_ZONES];     // rangos libres (PIX/ADD), van encima
int  pixCount = 0;

// Colores base
const CRGB C_GREEN = CRGB(40, 255, 40);
const CRGB C_DIMG  = CRGB(6, 40, 8);
const CRGB C_AMBER = CRGB(255, 150, 0);
const CRGB C_CYAN  = CRGB(40, 220, 220);

String rx;  // buffer de linea

void setAnim(Zone& z, uint8_t a) {
  z.anim = a;
  z.t0 = millis();
}

void setAllBranches(uint8_t a) {
  pixCount = 0;  // volver al modo tramos
  for (int b = 0; b < NUM_BRANCHES; b++) setAnim(branches[b], a);
}

void setup() {
  Serial.begin(115200);
  for (int b = 0; b < NUM_BRANCHES; b++) {
    int n = BRANCH_COUNTS[b];
    if (n < 0) n = 0;
    if (numLeds + n > MAX_LEDS) n = MAX_LEDS - numLeds;  // nunca pasarse del buffer
    branches[b].start = numLeds;
    branches[b].len = n;
    numLeds += n;
  }
  FastLED.addLeds<WS2812B, DATA_PIN, GRB>(leds, numLeds);
  // Limite de consumo: la fuente es 5V/10A (50W). Con 144 LEDs el blanco pleno
  // rondaria 8,6A; igual FastLED autoescala el brillo en cada show() para no
  // pasar de 9000 mA (90%) si alargas tramos. Evita brownout/reset del micro. Es
  // independiente de setBrightness(): ese es el techo, esto es el limite de corriente.
  FastLED.setMaxPowerInVoltsAndMilliamps(5, 9000);
  FastLED.setBrightness(140);
  setAllBranches(A_IDLE);
  FastLED.clear(true);
}

// ---- Animaciones (todas calculan el frame en funcion de millis()) ----------
void renderZone(Zone& z) {
  CRGB* px = leds + z.start;
  int n = z.len;
  if (n <= 0) return;  // zona sin LEDs: nada que renderizar (evita % 0 y division por 0)
  uint32_t el = millis() - z.t0;

  switch (z.anim) {
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
      if (el >= 900) setAnim(z, A_FOCUS);
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
}

uint8_t animFromToken(const String& t) {
  if (t == "DISCOVER") return A_DISCOVER;
  if (t == "FOCUS")    return A_FOCUS;
  if (t == "EXPLOIT")  return A_EXPLOIT;
  if (t == "TRANSFER") return A_TRANSFER;
  if (t == "IDLE")     return A_IDLE;
  return A_OFF;
}

// "0-9,40-50,77" -> una zona por rango. Inclusivos, recortados al largo de la tira.
void addRanges(const String& spec, uint8_t a) {
  int pos = 0;
  while (pos < (int)spec.length() && pixCount < MAX_PIX_ZONES) {
    int comma = spec.indexOf(',', pos);
    if (comma < 0) comma = spec.length();
    String r = spec.substring(pos, comma);
    pos = comma + 1;
    r.trim();
    if (r.length() == 0) continue;
    int dash = r.indexOf('-', 1);
    long from = r.toInt();
    long to = (dash < 0) ? from : r.substring(dash + 1).toInt();
    if (from > to) { long t = from; from = to; to = t; }
    if (to < 0 || from >= numLeds) continue;
    if (from < 0) from = 0;
    if (to >= numLeds) to = numLeds - 1;
    Zone& z = pixZones[pixCount++];
    z.start = (int)from;
    z.len = (int)(to - from + 1);
    setAnim(z, a);
  }
}

void handleLine(String line) {
  line.trim();
  if (line.length() == 0) return;

  if (line == "IDLE") { setAllBranches(A_IDLE); return; }
  if (line == "OFF")  { setAllBranches(A_OFF);  return; }

  if (line.startsWith("ALL:")) {
    setAllBranches(animFromToken(line.substring(4)));
    return;
  }
  if (line.startsWith("SEG:")) {
    int c1 = line.indexOf(':');
    int c2 = line.indexOf(':', c1 + 1);
    if (c2 < 0) return;
    int id = line.substring(c1 + 1, c2).toInt();
    uint8_t a = animFromToken(line.substring(c2 + 1));
    if (id >= 0 && id < NUM_BRANCHES) {
      pixCount = 0;  // volver al modo tramos
      setAnim(branches[id], a);
    }
    return;
  }
  if (line.startsWith("PIX:") || line.startsWith("ADD:")) {
    int c2 = line.lastIndexOf(':');
    if (c2 <= 4) return;
    uint8_t a = animFromToken(line.substring(c2 + 1));
    if (line.startsWith("PIX:")) {
      // reemplaza: apaga toda la tira y deja solo estos rangos
      setAllBranches(A_OFF);
    }
    addRanges(line.substring(4, c2), a);
    return;
  }
}

void loop() {
  // 1) leer comandos serial sin bloquear
  while (Serial.available()) {
    char ch = (char)Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (rx.length()) { handleLine(rx); rx = ""; }
    } else if (rx.length() < 128) {
      rx += ch;
    }
  }
  // 2) refrescar animaciones ~60fps: primero los tramos, encima los rangos PIX/ADD
  static uint32_t last = 0;
  if (millis() - last >= 16) {
    last = millis();
    for (int b = 0; b < NUM_BRANCHES; b++) renderZone(branches[b]);
    for (int i = 0; i < pixCount; i++) renderZone(pixZones[i]);
    // cadena cableada desde el FILE-SERVER: espejar para seguir contando desde la TERMINAL
    if (STRIP_REVERSED) {
      for (int i = 0; i < numLeds / 2; i++) {
        CRGB t = leds[i];
        leds[i] = leds[numLeds - 1 - i];
        leds[numLeds - 1 - i] = t;
      }
    }
    FastLED.show();
  }
}
