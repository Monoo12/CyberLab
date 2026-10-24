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
 *                            Si el tramo termina en un nodo (switch/router), ese
 *                            LED titila NODE_PROCESS_MS ("procesando") y despues
 *                            queda igual que el tramo.
 *   ALL:<anim>            -> anima TODOS los tramos (con sus nodos, como SEG)
 *   NODE:<id>:<anim>      -> anima solo el LED de un nodo. id = 0..NUM_NODES-1
 *                            Con PROCESS titila y vuelve a como estaba.
 *   PIX:<rangos>:<anim>   -> anima solo esos LEDs y apaga el resto
 *   ADD:<rangos>:<anim>   -> anima esos LEDs sin tocar el resto
 *   <anim>   = DISCOVER | FOCUS | EXPLOIT | TRANSFER | PROCESS | IDLE | OFF
 *              | PING (eco que va y vuelve) | SCAN (escaneo de puertos, flicker)
 *              | BLIP (ack rapido de un comando) | ERROR (flash rojo)
 *              PING/SCAN/BLIP/ERROR son TRANSITORIAS: animan un rato y despues
 *              vuelven solas al estado que tenia la zona (como PROCESS).
 *   <rangos> = LEDs sueltos o rangos inclusivos separados por coma, contando
 *              desde 0 en el extremo de la TERMINAL. Ej: PIX:0-9,40-50:FOCUS
 *   SEG/ALL/NODE/IDLE/OFF vuelven al modo tramos (borran los rangos de PIX/ADD).
 *   Los LEDs de DEAD_LEDS no se prenden nunca, con ningun comando.
 *
 * Cableado (ver docs/GUIA-HARDWARE.md): UNA sola tira encadenada (el DATA OUT
 * de un tramo va al DATA IN del siguiente) en un unico pin de datos. 5V y GND a
 * la fuente; GND de la fuente unido al GND del micro. Cada tramo y cada nodo es
 * un rango de LEDs de esa tira (BRANCH_COUNTS).
 *
 * Requiere la libreria FastLED.  El mapeo id->tramo/nodo es espejo de
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
#define NUM_NODES    3

// --- Tablero real: 68 LEDs en una sola cadena -------------------------------
// Cada tramo es un rango de LEDs y entre tramo y tramo hay 1 LED de nodo (el
// switch o el router) que titila cuando pasa trafico. El nodo k va justo
// despues del tramo k; el ultimo tramo llega al FILE-SERVER y no tiene nodo.
// Numeracion desde 0 (el "LED 1" contando a mano es el 0 aca):
//   id 0 = Tramo 1  TERMINAL   -> switch-izq   13 LEDs  (LED  0..12)
//          Nodo 0   switch-izq                  1 LED   (LED 13)
//   id 1 = Tramo 2  switch-izq -> router       20 LEDs  (LED 14..33)
//          Nodo 1   router                      1 LED   (LED 34)
//   id 2 = Tramo 3  router     -> switch-der   19 LEDs  (LED 35..53)
//          Nodo 2   switch-der                  1 LED   (LED 54)
//   id 3 = Tramo 4  switch-der -> FILE-SERVER  13 LEDs  (LED 55..67)
// Total 68. Si cambia el tablero, ajusta estos numeros (sin contar los nodos).
const int BRANCH_COUNTS[NUM_BRANCHES] = { 13, 20, 19, 13 };

// LEDs danados (numeracion desde 0): quedan siempre apagados.
// 62 = el "LED 63" contando a mano, en el Tramo 4.
const int DEAD_LEDS[] = { 62 };
const int NUM_DEAD = sizeof(DEAD_LEDS) / sizeof(DEAD_LEDS[0]);

// Cuanto titila un nodo al "procesar" y cada cuanto cambia el parpadeo (ms).
#define NODE_PROCESS_MS 2500
#define NODE_BLINK_MS   120

// --- Sentido de la tira -----------------------------------------------------
// Los numeros de LED cuentan desde la TERMINAL (LED 0) hacia el FILE-SERVER y las
// animaciones avanzan en ese sentido. Lo normal es meter el DATA IN por el extremo
// de la TERMINAL. Si la cadena arranca del lado del FILE-SERVER, pone true: el
// firmware da vuelta todo y los numeros siguen contando desde la TERMINAL.
const bool STRIP_REVERSED = false;

// Tope del buffer: el rollo entero (5 m x 60 LED/m). El largo real (numLeds) y el
// inicio de cada tramo/nodo se calculan solos en setup() a partir de BRANCH_COUNTS.
#define MAX_LEDS 300

// Maximo de rangos simultaneos de PIX/ADD (los de mas se ignoran).
#define MAX_PIX_ZONES 8

// --- Estados de animacion ---------------------------------------------------
// (los tipos van antes de cualquier funcion: el IDE de Arduino genera los
// prototipos arriba de la primera funcion y tienen que conocer Zone)
// Las TRANSITORIAS (A_PROCESS en adelante) animan un rato y vuelven a z.next.
enum Anim { A_OFF = 0, A_IDLE, A_DISCOVER, A_FOCUS, A_EXPLOIT, A_TRANSFER,
            A_PROCESS, A_PING, A_SCAN, A_BLIP, A_ERROR };

// Una zona es un rango de LEDs que se anima como una unidad.
struct Zone {
  int      start;  // primer LED (contando desde la TERMINAL)
  int      len;
  uint8_t  anim;
  uint8_t  next;   // a que anim pasa cuando termina PROCESS
  uint32_t t0;
};

CRGB leds[MAX_LEDS];
int  numLeds = 0;                 // tramos + nodos (tope MAX_LEDS)
Zone branches[NUM_BRANCHES];      // los tramos fijos (SEG/ALL/IDLE/OFF)
Zone nodes[NUM_NODES];            // 1 LED por switch/router, despues de cada tramo
Zone pixZones[MAX_PIX_ZONES];     // rangos libres (PIX/ADD), van encima
int  pixCount = 0;

// Colores base
const CRGB C_GREEN = CRGB(40, 255, 40);
const CRGB C_DIMG  = CRGB(6, 40, 8);
const CRGB C_AMBER = CRGB(255, 150, 0);
const CRGB C_CYAN  = CRGB(40, 220, 220);
const CRGB C_WHITE = CRGB(255, 255, 255);
const CRGB C_RED   = CRGB(255, 20, 10);
const CRGB C_REDHOT = CRGB(255, 70, 30);

String rx;  // buffer de linea

void setAnim(Zone& z, uint8_t a) {
  z.anim = a;
  z.t0 = millis();
}

// Las animaciones transitorias se ejecutan un rato y despues vuelven a z.next.
bool isTransient(uint8_t a) {
  return a == A_PROCESS || a == A_PING || a == A_SCAN || a == A_BLIP || a == A_ERROR;
}

// Arranca una anim transitoria recordando a donde volver (el estado previo, salvo
// que ya fuera transitorio). Al terminar, renderZone hace setAnim(z, z.next).
void startTransient(Zone& z, uint8_t a) {
  if (!isTransient(z.anim)) z.next = z.anim;
  setAnim(z, a);
}

void startProcess(Zone& z) { startTransient(z, A_PROCESS); }

void setAllZones(uint8_t a) {
  pixCount = 0;  // volver al modo tramos
  for (int b = 0; b < NUM_BRANCHES; b++) setAnim(branches[b], a);
  for (int k = 0; k < NUM_NODES; k++) setAnim(nodes[k], a);
}

// Anima el tramo b. Si termina en un nodo, el nodo "procesa" (titila) y despues
// queda como el tramo. Con OFF/IDLE el nodo copia el estado sin titilar.
void animBranch(int b, uint8_t a) {
  if (isTransient(a)) startTransient(branches[b], a);
  else setAnim(branches[b], a);
  if (b >= NUM_NODES) return;
  Zone& n = nodes[b];
  if (a == A_OFF || a == A_IDLE) { setAnim(n, a); return; }
  // Con una anim transitoria el nodo la acompana y vuelve a lo previo; con una
  // sostenida titila ("procesando") y queda como el tramo.
  if (isTransient(a)) { startTransient(n, a); return; }
  n.next = (a == A_DISCOVER) ? A_FOCUS : a;
  setAnim(n, A_PROCESS);
}

// Reserva los proximos n LEDs de la cadena para la zona z (sin pasarse del buffer).
void reserve(Zone& z, int n) {
  if (n < 0) n = 0;
  if (numLeds + n > MAX_LEDS) n = MAX_LEDS - numLeds;
  z.start = numLeds;
  z.len = n;
  z.next = A_OFF;
  numLeds += n;
}

void setup() {
  Serial.begin(115200);
  for (int b = 0; b < NUM_BRANCHES; b++) {
    reserve(branches[b], BRANCH_COUNTS[b]);
    if (b < NUM_NODES) reserve(nodes[b], 1);
  }
  FastLED.addLeds<WS2812B, DATA_PIN, GRB>(leds, numLeds);
  // Limite de consumo: la fuente es 5V/10A (50W). Con 68 LEDs el blanco pleno
  // rondaria 4,1A; igual FastLED autoescala el brillo en cada show() para no
  // pasar de 9000 mA (90%) si alargas tramos. Evita brownout/reset del micro. Es
  // independiente de setBrightness(): ese es el techo, esto es el limite de corriente.
  FastLED.setMaxPowerInVoltsAndMilliamps(5, 9000);
  FastLED.setBrightness(140);
  setAllZones(A_IDLE);
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
      // Espera con vida: respiracion verde muy tenue + un cometa que recorre TODO
      // el tablero (usa la posicion absoluta z.start+i y un reloj global, asi los
      // tramos y nodos se encadenan en un unico barrido continuo que se repite).
      uint32_t now = millis();
      uint8_t br = quadwave8((now / 16) & 0xFF);          // respiracion lenta
      CRGB base = blend(CRGB::Black, C_DIMG, br);
      int span = (numLeds > 0) ? numLeds : 1;
      int head = (now / 55) % span;                        // cabeza del cometa 0..span
      for (int i = 0; i < n; i++) {
        int d = head - (z.start + i);
        if (d < 0) d += span;                              // distancia por detras de la cabeza
        px[i] = (d < 10) ? blend(base, C_GREEN, (uint8_t)(255 - d * 26)) : base;
      }
      break;
    }

    case A_DISCOVER: {
      // Barrido de descubrimiento REPETIDO: la cabeza verde recorre el tramo
      // varias pasadas (dejando una estela tenue) y recien despues queda en FOCUS.
      const uint32_t PASS = 520;    // ms por pasada
      const int PASSES = 3;         // cuantas veces se repite el barrido
      if (el >= PASS * PASSES) { setAnim(z, A_FOCUS); break; }
      int head = (int)(((el % PASS) * n) / PASS);
      for (int i = 0; i < n; i++) {
        int d = head - i;
        if (d == 0 || d == 1) px[i] = C_GREEN;             // cabeza brillante
        else if (d > 0)       px[i] = CRGB(12, 70, 18);    // estela ya recorrida
        else                  px[i] = CRGB::Black;         // todavia sin tocar
      }
      break;
    }

    case A_FOCUS:
      fill_solid(px, n, CRGB(20, 120, 30));
      break;

    case A_EXPLOIT: {
      // Ataque: ROJO agresivo. Strobe rapido de fondo + un punto caliente que
      // corre por el tramo (sensacion de intrusion).
      uint8_t w = triwave8((el / 3) & 0xFF);
      fill_solid(px, n, blend(CRGB(30, 0, 0), C_RED, w));
      int head = (el / 22) % (n > 0 ? n : 1);
      for (int k = 0; k < 3; k++) {
        int j = head - k;
        if (j >= 0 && j < n) px[j] = C_REDHOT;
      }
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

    case A_PROCESS:
      // titila blanco ("procesando") y despues pasa a z.next
      if (el >= NODE_PROCESS_MS) { setAnim(z, z.next); break; }
      fill_solid(px, n, ((el / NODE_BLINK_MS) & 1) ? CRGB::Black : C_WHITE);
      break;

    case A_PING: {
      // Eco: un punto cyan va de la terminal al final del tramo y vuelve, una vez.
      const uint32_t D = 900;
      if (el >= D) { setAnim(z, z.next); break; }
      uint32_t half = D / 2;
      int head = (el < half) ? (int)((el * (n - 1)) / half)
                             : (int)(((D - el) * (n - 1)) / half);   // ida y vuelta
      for (int i = 0; i < n; i++) {
        int d = head - i; if (d < 0) d = -d;
        px[i] = (d == 0) ? C_CYAN : (d == 1) ? CRGB(0, 60, 60) : CRGB::Black;
      }
      break;
    }

    case A_SCAN: {
      // Escaneo de puertos: flicker ambar/verde por toda la zona y vuelve a z.next.
      const uint32_t D = 1100;
      if (el >= D) { setAnim(z, z.next); break; }
      for (int i = 0; i < n; i++) {
        uint8_t r = random8();
        px[i] = (r > 180) ? C_AMBER : (r > 110 ? CRGB(50, 35, 0) : CRGB::Black);
      }
      break;
    }

    case A_BLIP: {
      // Ack breve: un destello verde que sube y baja. Reacciona a cualquier comando.
      const uint32_t D = 260;
      if (el >= D) { setAnim(z, z.next); break; }
      uint8_t w = quadwave8((uint8_t)((el * 255) / D));
      fill_solid(px, n, blend(CRGB::Black, C_GREEN, w));
      break;
    }

    case A_ERROR: {
      // Error: parpadeo rojo un par de veces y vuelve a z.next.
      const uint32_t D = 700;
      if (el >= D) { setAnim(z, z.next); break; }
      fill_solid(px, n, ((el / 120) & 1) ? CRGB::Black : C_RED);
      break;
    }
  }
}

uint8_t animFromToken(const String& t) {
  if (t == "DISCOVER") return A_DISCOVER;
  if (t == "FOCUS")    return A_FOCUS;
  if (t == "EXPLOIT")  return A_EXPLOIT;
  if (t == "TRANSFER") return A_TRANSFER;
  if (t == "PROCESS")  return A_PROCESS;
  if (t == "PING")     return A_PING;
  if (t == "SCAN")     return A_SCAN;
  if (t == "BLIP")     return A_BLIP;
  if (t == "ERROR")    return A_ERROR;
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
    z.next = A_OFF;  // PIX/ADD con PROCESS: titila y se apaga
    setAnim(z, a);
  }
}

void handleLine(String line) {
  line.trim();
  if (line.length() == 0) return;

  if (line == "IDLE") { setAllZones(A_IDLE); return; }
  if (line == "OFF")  { setAllZones(A_OFF);  return; }

  if (line.startsWith("ALL:")) {
    uint8_t a = animFromToken(line.substring(4));
    pixCount = 0;  // volver al modo tramos
    for (int b = 0; b < NUM_BRANCHES; b++) animBranch(b, a);
    return;
  }
  if (line.startsWith("SEG:") || line.startsWith("NODE:")) {
    bool isNode = line.startsWith("NODE:");
    int c1 = line.indexOf(':');
    int c2 = line.indexOf(':', c1 + 1);
    if (c2 < 0) return;
    int id = line.substring(c1 + 1, c2).toInt();
    uint8_t a = animFromToken(line.substring(c2 + 1));
    if (isNode) {
      if (id < 0 || id >= NUM_NODES) return;
      pixCount = 0;
      if (isTransient(a)) startTransient(nodes[id], a);
      else setAnim(nodes[id], a);
    } else {
      if (id < 0 || id >= NUM_BRANCHES) return;
      pixCount = 0;
      animBranch(id, a);
    }
    return;
  }
  if (line.startsWith("PIX:") || line.startsWith("ADD:")) {
    int c2 = line.lastIndexOf(':');
    if (c2 <= 4) return;
    uint8_t a = animFromToken(line.substring(c2 + 1));
    if (line.startsWith("PIX:")) {
      // reemplaza: apaga toda la tira y deja solo estos rangos
      setAllZones(A_OFF);
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
  // 2) refrescar animaciones ~60fps: tramos, nodos y encima los rangos PIX/ADD
  static uint32_t last = 0;
  if (millis() - last >= 16) {
    last = millis();
    for (int b = 0; b < NUM_BRANCHES; b++) renderZone(branches[b]);
    for (int k = 0; k < NUM_NODES; k++) renderZone(nodes[k]);
    for (int i = 0; i < pixCount; i++) renderZone(pixZones[i]);
    // LEDs danados: siempre apagados, haga lo que haga la animacion
    for (int d = 0; d < NUM_DEAD; d++) {
      if (DEAD_LEDS[d] >= 0 && DEAD_LEDS[d] < numLeds) leds[DEAD_LEDS[d]] = CRGB::Black;
    }
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
