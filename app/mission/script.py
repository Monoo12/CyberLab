"""Todo el texto visible de la mision (espanol), ASCII art y pistas.

La dificultad cambia CUANTO y COMO te guia la terminal:
  - facil:   comando simple + la IP concreta; pistas muy detalladas.
  - medio:   te orienta por concepto, sin comandos obvios ni IPs.
  - dificil: te da pistas de los comandos REALES (nmap, hydra, curl) SIN las IPs.
  - pro:     no te da comandos ni pistas concretas; solo una idea conceptual.
El parser acepta las dos sintaxis (guiada y real) en TODAS las dificultades.
"""
from __future__ import annotations

BANNER = r"""
  ____      _               _          _
 / ___|   _| |__   ___ _ __| |    __ _| |__
| |  | | | | '_ \ / _ \ '__| |   / _` | '_ \
| |__| |_| | |_) |  __/ |  | |__| (_| | |_) |
 \____\__, |_.__/ \___|_|  |_____\__,_|_.__/
      |___/        ACCESO A SISTEMAS  v1.0
"""


def briefing(difficulty: str) -> list[str]:
    base = [
        "[ SISTEMA DE MONITOREO ]  Actividad sospechosa detectada en la red.",
        "",
        "Tu mision, agente: infiltrarte en el FILE-SERVER y recuperar el archivo",
        "secreto que se guarda en la carpeta restringida.",
        "",
        "Tenes 5 minutos. El reloj corre desde ahora.",
        "",
    ]
    if difficulty == "facil":
        base += [
            "Escribi  help  para ver los comandos disponibles.",
            "Primer paso sugerido:  scan   (descubrir que hay en la red).",
        ]
    elif difficulty == "medio":
        base += [
            "Escribi  help  para ver los comandos. Las IP y el camino los descubris vos.",
        ]
    elif difficulty == "dificil":
        base += [
            "Herramientas reales disponibles (nmap, hydra, curl...).",
            "Escribi  help  para la sintaxis; las IP concretas las sacas del reconocimiento.",
        ]
    else:  # pro
        base += [
            "Sin asistencia. Usa tus conocimientos para llegar al secreto del FILE-SERVER.",
            "'pista' apenas te da una idea si te trabas de verdad.",
        ]
    base.append("")
    return base


MISSION_COMPLETE = [
    "",
    "================  MISSION COMPLETE  ================",
    "",
    "Recuperaste el archivo secreto. Repasemos lo que hiciste:",
    "  1. scan     -> descubriste los dispositivos de la red (sus IPs).",
    "  2. inspect  -> encontraste que puertos/servicios tenia el objetivo.",
    "  3. connect  -> abriste el servicio web real del servidor.",
    "  4. exploit  -> venciste el login por una de sus 3 debilidades.",
    "  5. ls/read  -> navegaste el servidor y leiste el archivo restringido.",
    "",
    "Eso es, en esencia, lo que hace un atacante -- y por que cada puerto",
    "abierto, cada clave debil y cada dato expuesto importan.",
    "",
    "  [ Enter ] jugar de nuevo     [ M ] volver al menu (cambiar dificultad)",
    "===================================================",
]

# ------------------------- HELP por dificultad -------------------------
_HELP_COMMON_TAIL = [
    "  cd <carpeta>             cambiar de directorio (tras acceso)",
    "  pwd                      mostrar el directorio actual",
    "  ping <ip>                probar si un host responde",
    "  whoami / clear           quien sos / limpiar pantalla",
    "  menu                     volver al menu de configuracion",
    "  hint / help              pedir una pista / esta ayuda",
]

HELP_FACIL = [
    "Comandos disponibles:",
    "  scan                     descubrir dispositivos en la red",
    "  inspect <ip>             ver puertos abiertos de un dispositivo",
    "  connect <ip:puerto>      abrir el servicio en el navegador real",
    "  exploit <ip> [metodo]    atacar el login de un host (leak | sqli | hydra)",
    "  ls [ruta]                listar archivos del servidor (tras exploit)",
    "  read <ruta>              leer un archivo del servidor (tras exploit)",
] + _HELP_COMMON_TAIL

HELP_MEDIO = [
    "Comandos (las IP y el camino los descubris vos):",
    "  scan                     descubrir dispositivos en la red",
    "  inspect <ip>             puertos abiertos de un host",
    "  connect <ip:puerto>      abrir un servicio web",
    "  exploit <ip> [metodo]    atacar el login de un host",
    "  ls / read / cd           explorar el servidor (tras acceso)",
    "  ping / pwd / whoami / clear / menu / hint",
]

HELP_DIFICIL = [
    "Modo DIFICIL -- sintaxis de herramientas reales (sin IPs concretas):",
    "  nmap -sn <rango>                       descubrir hosts activos",
    "  nmap -p 22,80,5000 <ip>                escanear puertos",
    "  connect <ip:puerto>                    abrir el servicio web",
    "  curl -d \"user=' OR '1'='1' -- \" http://<ip>/login    (SQL injection)",
    "  hydra -l admin -P wordlist.txt <ip> http-post-form ...  (fuerza bruta)",
    "  Metodo 'leak': abri el servicio y usa 'Inspeccionar' en el navegador.",
    "  ls / cd / read  para explorar tras obtener acceso.",
]

HELP_PRO = [
    "Modo PRO: sin lista de comandos.",
    "Podes usar herramientas de red reales o comandos simples.",
    "Escribi 'pista' si estas muy trabado, o 'menu' para bajar la dificultad.",
]


def help_for(difficulty: str) -> list[str]:
    return {
        "facil": HELP_FACIL,
        "medio": HELP_MEDIO,
        "dificil": HELP_DIFICIL,
    }.get(difficulty, HELP_PRO)


# ------------------------- PISTAS por dificultad -----------------------
# facil: comando simple + IP.  medio: concepto sin comando obvio ni IP.
# dificil: comando REAL sin IP.  pro: idea conceptual, sin comandos.
_HINTS_FACIL = {
    "briefing": "Pista: empeza con  scan  para ver que dispositivos hay en la red.",
    "scanned": "Pista: el objetivo es el FILE-SERVER. Usa  inspect <ip>  sobre su IP.",
    "inspected": "Pista: el puerto 80 es web. Proba  connect <ip:80>  para abrir el servicio.",
    "connected": "Pista: en la pagina, proba 'Inspeccionar' para datos ocultos, o usa  exploit <ip>  (la IP del servidor).",
    "exploited": "Pista: ya tenes acceso. Usa  ls  para mirar las carpetas y  cd  para entrar.",
    "listed": "Pista: el archivo esta en /restricted. Proba  read /restricted/secret.txt",
}
_HINTS_MEDIO = {
    "briefing": "Pista: todavia no sabes que hay en la red. Empeza por mapearla.",
    "scanned": "Pista: no todos los equipos son el objetivo; interesa el que guarda archivos, y que servicios expone.",
    "inspected": "Pista: uno de esos puertos sirve una web. Es tu puerta de entrada.",
    "connected": "Pista: el login no es tan seguro como parece. Hay mas de una forma de entrar.",
    "exploited": "Pista: ahora sos otro usuario. Recorre sus carpetas.",
    "listed": "Pista: lo valioso suele estar donde dice 'restringido'.",
}
_HINTS_DIFICIL = {
    "briefing": "Pista: descubri hosts activos con  nmap -sn <rango>  (o arp-scan).",
    "scanned": "Pista: escanea los puertos del objetivo con  nmap -p 22,80,5000 <ip>.",
    "inspected": "Pista: hay un HTTP abierto. Abrilo (connect <ip:puerto>) e inspecciona el HTML.",
    "connected": "Pista: el login es vulnerable. Proba SQLi (curl con ' OR '1'='1) o fuerza bruta (hydra ... http-post-form).",
    "exploited": "Pista: ya tenes shell. Enumera el filesystem (ls, cd) buscando lo restringido.",
    "listed": "Pista: leé el archivo objetivo con  read /restricted/secret.txt  (o cat).",
}
_HINTS_PRO = {
    "briefing": "Pista: no sabes que hay en la red. Averigualo.",
    "scanned": "Pista: cada host expone servicios en ciertos puertos.",
    "inspected": "Pista: un servicio web se accede desde un navegador.",
    "connected": "Pista: los desarrolladores dejan pistas y errores. Mira bien el login.",
    "exploited": "Pista: ahora sos otro usuario. Mira que archivos podes ver.",
    "listed": "Pista: lo importante suele estar 'restringido'.",
}


def hint_for(difficulty: str, state: str) -> str | None:
    table = {
        "facil": _HINTS_FACIL,
        "medio": _HINTS_MEDIO,
        "dificil": _HINTS_DIFICIL,
    }.get(difficulty, _HINTS_PRO)
    return table.get(state)


# ------------------- NUDGES tras cada comando (gated) ------------------
# Guia automatica post-comando segun dificultad, o None si no corresponde.
def nudge(difficulty: str, key: str, ip: str = "") -> str | None:
    if difficulty == "pro":
        return None

    if key == "scan_done":
        if difficulty == "facil":
            return "[+] Objetivo probable: FILE-SERVER (" + ip + ")."
        if difficulty == "medio":
            return "[+] Uno de estos es el objetivo. Fijate cual expone servicios interesantes."
        return "[+] Elegi el objetivo y escanea sus puertos:  nmap -p 22,80,5000 <ip>"  # dificil

    if key == "inspect_to_connect":
        if difficulty == "facil":
            return "[+] El puerto 80 (http) sirve una web. Proba: connect " + ip + ":80"
        if difficulty == "medio":
            return "[+] Hay un servicio web ahi. Es tu puerta de entrada."
        return "[+] HTTP abierto: abrilo con  connect <ip:80>  e inspecciona el HTML."  # dificil

    if key == "connect_tip":
        if difficulty == "facil":
            return "    Tip: proba 'Inspeccionar' (click derecho) para ver datos ocultos, o usa 'exploit <ip>'."
        if difficulty == "medio":
            return "    Tip: mira bien la pagina; el login tiene mas de una debilidad."
        return "    Tip: SQLi (' OR '1'='1), fuerza bruta (hydra), o creds filtradas en el HTML."  # dificil

    if key == "exploited":
        if difficulty == "facil":
            return "[+] Ya estas dentro. Usa 'ls' para explorar y 'cd' para entrar a las carpetas."
        if difficulty == "medio":
            return "[+] Acceso conseguido. Recorre el servidor."
        return "[+] Shell obtenida. Enumera el filesystem (ls, cd)."  # dificil

    if key == "found_restricted":
        if difficulty == "facil":
            return "[+] Hay una carpeta 'restricted'. Proba: read /restricted/secret.txt"
        if difficulty == "medio":
            return "[+] Algo parece restringido..."
        return "[+] Objetivo probable en /restricted (read/cat)."  # dificil

    return None


RUN_SCAN = "[*] Escaneando la red en busca de dispositivos activos..."
RUN_INSPECT = "[*] Escaneando puertos de {ip}..."
RUN_CONNECT = "[*] Abriendo {url} en el navegador..."
RUN_EXPLOIT = "[*] Lanzando exploit ({method}) contra {ip}..."
