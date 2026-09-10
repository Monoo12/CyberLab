/* ==========================================================================
 * Cyber Lab - firmware de la tira LED (Arduino / ESP8266 / ESP32)
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
 * micro. Ajusta los pines y los largos (BRANCH_COUNTS) al tablero real.
 *
 * Requiere la libreria FastLED.  El mapeo id->rama es espejo de
 * app/leds/segments.py (rama 0: router<->switch-izq<->terminal, etc.).
 * ========================================================================== */

#include <FastLED.h>

#define NUM_BRANCHES 5

// --- Pines de datos por rama (AJUSTAR al hardware) -------------------------
// En placas tipo Arduino UNO/Nano: 2,3,4,5,6.  En ESP8266 (NodeMCU) usar
// D1,D2,D5,D6,D7 (GPIO5,4,14,12,13).  En ESP32: casi cualquier GPIO de salida.
#define PIN_B0 2
#define PIN_B1 3
#define PIN_B2 4
#define PIN_B3 5
#define PIN_B4 6

// --- Cantidad de LEDs por rama (AJUSTAR al largo real de cada tramo) --------
// Tramos router<->switch suelen ser mas largos; ramas cortas al switch derecho.
const int BRANCH_COUNTS[NUM_BRANCHES] = { 20, 18, 8, 6, 6 };
#define MAX_LEDS 24  // >= al mayor de BRANCH_COUNTS

// --- Estados de animacion ---------------------------------------------------
enum Anim { A_OFF = 0, A_IDLE, A_DISCOVER, A_FOCUS, A_EXPLOIT, A_TRANSFER };

CRGB leds0[MAX_LEDS], leds1[MAX_LEDS], leds2[MAX_LEDS], leds3[MAX_LEDS], leds4[MAX_LEDS];
CRGB* const BRANCH_LEDS[NUM_BRANCHES] = { leds0, leds1, leds2, leds3, leds4 };

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
  FastLED.addLeds<WS2812B, PIN_B4, GRB>(leds4, BRANCH_COUNTS[4]);
  FastLED.setBrightness(140);
  for (int b = 0; b < NUM_BRANCHES; b++) setAnim(b, A_IDLE);
  FastLED.clear(true);
}

// ---- Animaciones (todas calculan el frame en funcion de millis()) ----------
void renderBranch(int b) {
  CRGB* px = BRANCH_LEDS[b];
  int n = BRANCH_COUNTS[b];
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
