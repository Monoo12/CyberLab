"""Todo el texto visible de la mision (espanol), ASCII art y pistas.

La dificultad (facil | medio | dificil) cambia CUANTO te guia la terminal:
  - facil:  te dice el comando y la IP; pistas detalladas; help completo.
  - medio:  te nombra el comando pero NO la IP (la descubris con scan); help sin IPs.
  - dificil: no te da comandos; help minimo; pistas vagas.
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
            "Escribi  help  para ver los comandos (vas a tener que descubrir las IP vos).",
        ]
    else:  # dificil
        base += [
            "Sin asistencia. Usa tus conocimientos de redes para llegar al secreto.",
            "Herramientas reales disponibles. 'pista' da una idea vaga si te trabas.",
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
    "  exploit [metodo]         atacar el login  (leak | sqli | hydra)",
    "  ls [ruta]                listar archivos del servidor (tras exploit)",
    "  read <ruta>              leer un archivo del servidor (tras exploit)",
] + _HELP_COMMON_TAIL

HELP_MEDIO = [
    "Comandos (las IP las descubris con scan):",
    "  scan                     descubrir dispositivos en la red",
    "  inspect <ip>             puertos abiertos de un host",
    "  connect <ip:puerto>      abrir el servicio web",
    "  exploit [metodo]         atacar el login",
    "  ls / read / cd           explorar el servidor (tras acceso)",
    "  ping / pwd / whoami / clear / menu / hint",
]

HELP_DIFICIL = [
    "Modo DIFICIL: sin lista de comandos.",
    "Podes usar herramientas de red reales (nmap, hydra, curl...) o comandos simples.",
    "Escribi 'pista' si estas muy trabado, o 'menu' para bajar la dificultad.",
]


def help_for(difficulty: str) -> list[str]:
    return {"facil": HELP_FACIL, "medio": HELP_MEDIO}.get(difficulty, HELP_DIFICIL)


# ------------------------- PISTAS por dificultad -----------------------
# state -> texto. facil menciona comando + contexto; medio solo el comando;
# dificil una idea conceptual sin nombrar el comando.
_HINTS_FACIL = {
    "briefing": "Pista: empeza con  scan  para ver que dispositivos hay en la red.",
    "scanned": "Pista: el objetivo es el FILE-SERVER. Usa  inspect <ip>  sobre su IP.",
    "inspected": "Pista: el puerto 80 es web. Proba  connect <ip:80>  para abrir el servicio.",
    "connected": "Pista: en la pagina, proba 'Inspeccionar' para buscar datos ocultos, o usa  exploit.",
    "exploited": "Pista: ya tenes acceso. Usa  ls  para mirar las carpetas y  cd  para entrar.",
    "listed": "Pista: el archivo esta en /restricted. Proba  read /restricted/secret.txt",
}
_HINTS_MEDIO = {
    "briefing": "Pista: hay que descubrir la red primero (scan).",
    "scanned": "Pista: identifica los puertos del servidor objetivo (inspect).",
    "inspected": "Pista: conecta al servicio web que encontraste (connect).",
    "connected": "Pista: el login tiene mas de una debilidad. Inspecciona el HTML o usa exploit.",
    "exploited": "Pista: explora el sistema de archivos (ls, cd).",
    "listed": "Pista: busca en la carpeta restringida y leela (read).",
}
_HINTS_DIFICIL = {
    "briefing": "Pista: no sabes que hay en la red. Averigualo.",
    "scanned": "Pista: cada host expone servicios en ciertos puertos.",
    "inspected": "Pista: un servicio web se accede desde un navegador.",
    "connected": "Pista: los desarrolladores dejan pistas y errores. Mira bien el login.",
    "exploited": "Pista: ahora sos otro usuario. Mira que archivos podes ver.",
    "listed": "Pista: lo importante suele estar 'restringido'.",
}


def hint_for(difficulty: str, state: str) -> str | None:
    table = {"facil": _HINTS_FACIL, "medio": _HINTS_MEDIO}.get(difficulty, _HINTS_DIFICIL)
    return table.get(state)


# ------------------- NUDGES tras cada comando (gated) ------------------
# Devuelve el texto de guia post-comando segun dificultad, o None si no corresponde.
def nudge(difficulty: str, key: str, ip: str = "") -> str | None:
    if difficulty == "dificil":
        return None
    if key == "inspect_to_connect":
        if difficulty == "facil":
            return "[+] El puerto 80 (http) sirve una web. Proba: connect " + ip + ":80"
        return "[+] Hay un servicio web. Conectate a el."
    if key == "scan_done":
        if difficulty == "facil":
            return "[+] Objetivo probable: FILE-SERVER (" + ip + ")."
        return "[+] Uno de estos es el objetivo. Inspecciona sus puertos."
    if key == "connect_tip":
        if difficulty == "facil":
            return "    Tip: proba 'Inspeccionar' (click derecho) para ver datos ocultos, o usa 'exploit'."
        return "    Tip: mira bien la pagina y su codigo fuente."
    if key == "exploited":
        if difficulty == "facil":
            return "[+] Ya estas dentro. Usa 'ls' para explorar y 'cd' para entrar a las carpetas."
        return "[+] Acceso conseguido. Explora el servidor."
    if key == "found_restricted":
        if difficulty == "facil":
            return "[+] Hay una carpeta 'restricted'. Proba: read /restricted/secret.txt"
        return "[+] Algo parece restringido..."
    return None


RUN_SCAN = "[*] Escaneando la red en busca de dispositivos activos..."
RUN_INSPECT = "[*] Escaneando puertos de {ip}..."
RUN_CONNECT = "[*] Abriendo {url} en el navegador..."
RUN_EXPLOIT = "[*] Lanzando exploit ({method}) contra el FILE-SERVER..."
