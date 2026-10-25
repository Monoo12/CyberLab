"""MissionController: maquina de estados de la mision (pasos 0-8, seccion 6).

Coordina en SINCRONIA la terminal (texto), el mapa visual y los LEDs, y ejecuta
los comandos del backend en un hilo worker (los resultados vuelven al hilo de Tk
via una queue poleada con after()). La orquestacion visual vive aca, no en el
backend, para que el show sea identico corra el motor Real o el Simulado.

La dificultad (facil/medio/dificil) cambia cuanto guia la terminal (nudges, pistas
y help); el parser acepta las dos sintaxis (guiada y real) en todas las dificultades.
"""
from __future__ import annotations

import posixpath
import queue
import threading

from app.leds import segments as seg
from app.mission import script
from app.mission.commands import (CommandParser, EXTRA_COMMANDS, available_commands,
                                   versions_available)
from app.ui import theme

WAITING = "waiting"
BRIEFING = "briefing"
SCANNED = "scanned"
INSPECTED = "inspected"
CONNECTED = "connected"
EXPLOITED = "exploited"
LISTED = "listed"
DONE = "done"


class MissionController:
    def __init__(self, root, cfg, backend, terminal, netmap, leds,
                 show_waiting, show_mission, on_return_menu=None, on_timer=None,
                 suspense=None):
        self.root = root
        self.cfg = cfg
        self.backend = backend
        self.term = terminal
        self.netmap = netmap
        self.leds = leds
        self.suspense = suspense     # overlay cinematografico (modos accesibles)
        self.show_waiting = show_waiting
        self.show_mission = show_mission
        self.on_return_menu = on_return_menu
        self.on_timer = on_timer

        self.parser = CommandParser(cfg.network.cidr)
        self.difficulty = cfg.modes.difficulty
        self.mode = cfg.modes.mode          # tarjetas | guiado | experto | reto
        self.lesson = cfg.modes.lesson      # rotar | clave | expuesto | login
        self._round = 0                     # para rotar la leccion entre rondas
        self.free = cfg.modes.free_mode
        self.available = available_commands(self.difficulty, self.free)
        self.state = WAITING
        self.hosts = []
        self.cwd = "/"
        self.target = cfg.host_by_role("fileserver")
        self.target_ip = self.target.ip if self.target else None
        self.sessions = set()      # ips a las que ya entraste
        self.session_ip = None     # host en el que tenes shell (para ls/read/cd)
        self.access = False        # compat: True si tenes acceso a algun host
        self.term.completer = self._completions

        self._q = queue.Queue()
        self._timer_job = None
        self._hint_job = None
        self._alive = True
        self._remaining = cfg.timing.mission_seconds
        self.term.on_submit = self.handle_input
        self._pump()

    # ================= ciclo de vida =================
    def enter_waiting(self):
        self.state = WAITING
        self._cancel_timers()
        if self.suspense:
            self.suspense.stop()
        try:
            self.backend.close_browser()
        except Exception:
            pass
        if self.netmap:
            self.netmap.reset()
        self.leds.idle()
        self.term.clear()
        self.show_waiting()

    def start_mission(self):
        self.state = BRIEFING
        self.lesson = self._resolve_lesson()   # rota por ronda si lesson='rotar'
        self.access = False
        self.sessions = set()
        self.session_ip = None
        self.hosts = []
        self.cwd = "/"
        self._remaining = self.cfg.timing.mission_seconds
        if self.netmap:
            self.netmap.reset()
        self.leds.off()
        self.show_mission()
        self.term.clear()
        self.term.write_lines(script.BANNER.splitlines(), tag="banner")
        self.term.writeln("")
        brief = (script.briefing_guiado(self.free) if self.mode == "guiado"
                 else script.briefing(self.difficulty, self.free))
        self.term.type_lines(brief, tag="fg", on_done=self._after_briefing)

    def _after_briefing(self):
        self._start_timer()
        self._arm_hint()
        if self.cfg.modes.engine == "real":
            self._run_preflight()
        self.term.focus_input()
        self._arm_suggestion()   # guiado: deja 'scan' listo para apretar Enter

    # ================= pre-flight (solo modo real) =================
    def _run_preflight(self):
        from app.backend import preflight
        self.term.writeln("[ PREFLIGHT ] verificando el laboratorio (red, nodo, credenciales)...",
                          tag="dim")
        self._async(lambda: preflight.run_checks(self.cfg), self._preflight_done)

    def _preflight_done(self, results):
        for status, text in results:
            if status == "ok":
                self.term.writeln("  [OK] " + text, tag="green")
            else:
                self.term.writeln("  [!]  " + text, tag="amber")
        if any(s == "warn" for s, _ in results):
            self.term.writeln("  (si algo falla en vivo, reinicia en modo Simulado como fallback)",
                              tag="dim")
        self.term.writeln("")

    def on_any_key(self):
        if self.state == WAITING:
            self.start_mission()
        elif self.state == DONE:
            self.enter_waiting()

    def shutdown(self):
        """Detiene el controller (pump/timers) al volver al menu o cerrar."""
        self._alive = False
        self._cancel_timers()
        if self.suspense:
            self.suspense.stop()
        try:
            self.backend.close_browser()
        except Exception:
            pass

    def _to_menu(self):
        self._cancel_timers()
        try:
            self.backend.close_browser()
        except Exception:
            pass
        self.leds.idle()
        if self.on_return_menu:
            self.on_return_menu()

    # ================= entrada de comandos =================
    def handle_input(self, line):
        if self.state in (WAITING, DONE):
            return
        self._arm_hint()
        if not line.strip():
            return
        self.term.echo_command(line)
        pc = self.parser.parse(line)

        if pc.error:
            self.term.writeln("[!] " + pc.error, tag="red")
            if self.difficulty != "dificil":
                self.term.writeln("    escribi 'help' para ver los comandos.", tag="dim")
            self.leds.animate_all(seg.ANIM_ERROR)   # flash rojo: algo salio mal
            return

        # gating por dificultad: los comandos extra no estan en nivel Facil
        if pc.name in EXTRA_COMMANDS and pc.name not in self.available:
            self.term.writeln("[!] '" + pc.name + "' no esta disponible en nivel Facil.", tag="amber")
            self.term.writeln("    subi a Medio/Dificil/Pro o activa Modo Libre.", tag="dim")
            self.leds.animate_all(seg.ANIM_ERROR)
            return

        handlers = {
            "help": self._cmd_help,
            "hint": self._cmd_hint,
            "clear": lambda: self.term.clear(),
            "pwd": lambda: self.term.writeln("  " + self.cwd, tag="cyan"),
            "whoami": self._cmd_whoami,
            "menu": self._to_menu,
            "scan": self._cmd_scan,
            "inspect": lambda: self._cmd_inspect(pc.ip, pc.versions),
            "connect": lambda: self._cmd_connect(pc.ip, pc.port),
            "exploit": lambda: self._cmd_exploit(pc.ip, pc.method),
            "ping": lambda: self._cmd_ping(pc.ip),
            "telnet": lambda: self._cmd_telnet(pc.ip, pc.port),
            "traceroute": lambda: self._cmd_traceroute(pc.ip),
            "arp": self._cmd_arp,
            "netstat": self._cmd_netstat,
            "cd": lambda: self._cmd_cd(pc.path),
            "ls": lambda: self._cmd_ls(pc.path),
            "read": lambda: self._cmd_read(pc.path),
            "empty": lambda: None,
        }
        h = handlers.get(pc.name)
        if h:
            h()
        # Ack minimo en el tablero para los comandos locales (sin red): un blip en
        # el primer nodo, asi CUALQUIER comando mueve algo en los LEDs.
        if pc.name in ("help", "hint", "clear", "pwd", "whoami"):
            self.leds.animate_node(0, seg.ANIM_BLIP)

    # ================= comandos informativos =================
    def _cmd_help(self):
        self.term.write_lines(script.help_for(self.difficulty, self.free), tag="cyan")

    def _cmd_hint(self):
        self._show_hint()

    # ================= autocompletado (TAB) =================
    _IP_CMDS = ("inspect", "connect", "exploit", "ping", "telnet", "traceroute", "nmap")
    _PATH_CMDS = ("cd", "ls", "read", "cat")

    def _completions(self, text):
        ends_space = text.endswith(" ")
        tokens = text.split()
        # 1) completar el nombre del comando (primer token)
        if len(tokens) == 0 or (len(tokens) == 1 and not ends_space):
            pref = tokens[0] if tokens else ""
            return [c + " " for c in sorted(self.available) if c.startswith(pref)]
        cmd = tokens[0]
        last = "" if ends_space else tokens[-1]
        head = text[:len(text) - len(last)]
        # 2) exploit <ip> <metodo>
        if cmd == "exploit" and (len(tokens) > 2 or (len(tokens) == 2 and ends_space)):
            return [head + m for m in ("leak", "sqli", "hydra") if m.startswith(last)]
        # 3) IPs de los hosts descubiertos
        if cmd in self._IP_CMDS:
            ips = [h.ip for h in self.hosts] or [h.ip for h in self.cfg.hosts]
            return [head + ip for ip in ips if ip.startswith(last)]
        # 4) rutas dentro del host donde tenes shell
        if cmd in self._PATH_CMDS and self.session_ip:
            dirpart, partial = (last.rsplit("/", 1) + [""])[:2] if "/" in last else ("", last)
            dirpart = dirpart + "/" if "/" in last else ""
            base_dir = self._resolve(dirpart) if dirpart else self.cwd
            try:
                names = self.backend.fs_names(self.session_ip, base_dir)
            except Exception:
                names = []
            return [head + dirpart + n for n in names if n.startswith(partial)]
        return []

    def _cmd_whoami(self):
        if self.session_ip:
            host = self.cfg.host_by_ip(self.session_ip)
            name = host.name if host else self.session_ip
            user = self.cfg.fileserver.ssh_user if self.session_ip == self.cfg.fileserver.ip else "root"
            self.term.writeln("  " + user + "@" + name, tag="green")
        else:
            self.term.writeln("  visitante@terminal", tag="fg")

    # ================= scan =================
    def _cmd_scan(self):
        self._busy(True)
        self.term.type_lines([script.RUN_SCAN], tag="dim",
                             on_done=lambda: self._async(self.backend.scan, self._scan_done))

    def _scan_done(self, result):
        self.hosts = result.hosts
        self.term.writeln("")
        self.term.writeln("  === NETWORK DISCOVERY ===", tag="green")
        self.term.writeln("  " + "IP".ljust(16) + "NOMBRE".ljust(22) + "TIPO", tag="dim")
        self._reveal_hosts(0)

    def _reveal_hosts(self, i):
        if i >= len(self.hosts):
            self.term.writeln("")
            n = script.nudge(self.difficulty, "scan_done", str(self.target_ip))
            if n:
                self.term.writeln(n, tag="white")
            self.state = SCANNED
            self._busy(False)
            self._narrate("scan")
            self._arm_suggestion()
            return
        h = self.hosts[i]
        mark = "  <- vos" if h.role == "terminal" else ""
        tag = "amber" if (h.role == "fileserver" and self.difficulty == "facil") else "fg"
        self.term.writeln("  " + h.ip.ljust(16) + h.name.ljust(22) + h.role + mark, tag=tag)
        if self.netmap:
            self.netmap.discover_node(h.role)
        self.leds.animate_segments(seg.segments_for_role(h.role), seg.ANIM_DISCOVER)
        self.root.after(420, lambda: self._reveal_hosts(i + 1))

    # ================= inspect =================
    def _cmd_inspect(self, ip, versions=False):
        if not self.free and (self.state == BRIEFING or not self.hosts):
            self.term.writeln("[!] Primero descubri la red (scan).", tag="amber")
            return
        if versions and not versions_available(self.difficulty, self.free):
            self.term.writeln("[!] La deteccion de versiones (-sV) no esta en nivel Facil.", tag="amber")
            versions = False
        host = self.cfg.host_by_ip(ip)
        role = host.role if host else "fileserver"
        if self.netmap:
            self.netmap.focus_role(role)
        self.leds.animate_segments(seg.segments_for_role(role), seg.ANIM_FOCUS)
        self.target_ip = ip
        self._busy(True)
        self.term.type_lines([script.RUN_INSPECT.format(ip=ip)], tag="dim",
                             on_done=lambda: self._async(lambda: self.backend.inspect(ip, versions),
                                                         self._inspect_done))

    def _inspect_done(self, res):
        self.term.writeln("")
        self.term.writeln("  === PUERTOS ABIERTOS EN " + res.ip + " ===", tag="green")
        self.term.writeln("  " + "PUERTO".ljust(10) + "ESTADO".ljust(10) + "SERVICIO", tag="dim")
        for p in res.ports:
            self.term.writeln("  " + str(p.port).ljust(10) + p.state.ljust(10) + p.service, tag="fg")
        self.term.writeln("")
        n = script.nudge(self.difficulty, "inspect_to_connect", res.ip)
        if n:
            self.term.writeln(n, tag="white")
        self.state = INSPECTED
        self._busy(False)
        self._narrate("inspect")
        self._arm_suggestion()

    # ================= connect =================
    def _cmd_connect(self, ip, port):
        url = self.backend.connect(ip, port)
        host = self.cfg.host_by_ip(ip)
        role = host.role if host else "fileserver"
        if self.netmap:
            self.netmap.focus_role(role)
        self.leds.animate_segments(seg.segments_for_role(role), seg.ANIM_FOCUS)
        lines = [script.RUN_CONNECT.format(url=url), "[+] Se abrio el servicio en el navegador."]
        tip = script.nudge(self.difficulty, "connect_tip")
        if tip:
            lines.append(tip)
        self.term.type_lines(lines, tag="fg")
        self.state = CONNECTED
        self._narrate("connect")
        self._arm_suggestion()

    # ================= exploit =================
    def _accessible(self):
        """Modos para quien no sabe: no se puede fallar, con show de suspenso."""
        return self.mode in ("guiado", "tarjetas")

    _ROTATION = ("clave", "expuesto", "login")
    _LESSON_METHOD = {"clave": "hydra", "expuesto": "leak", "login": "sqli"}

    def _resolve_lesson(self):
        """Leccion concreta de esta ronda. 'rotar' cicla clave->expuesto->login."""
        base = self.cfg.modes.lesson
        if base in self._ROTATION:
            return base
        lesson = self._ROTATION[self._round % len(self._ROTATION)]
        self._round += 1
        return lesson

    def _lesson_key(self):
        return self.lesson if self.lesson in self._ROTATION else "clave"

    def _lesson_method(self):
        """Via del backend que ilustra la leccion (clave->hydra, expuesto->leak, login->sqli)."""
        return self._LESSON_METHOD.get(self._lesson_key(), "hydra")

    # ---- modo GUIADO: proximo comando sugerido + narracion en lenguaje simple ----
    def _suggested_command(self):
        ip = self.target_ip or (self.target.ip if self.target else "")
        port = self.cfg.fileserver.http_port
        secret = self.cfg.fileserver.secret_path
        return {
            BRIEFING: "scan",
            SCANNED: "inspect " + ip,
            INSPECTED: "connect " + ip + ":" + str(port),
            CONNECTED: "exploit " + ip,
            EXPLOITED: "ls",
            LISTED: "read " + secret,
        }.get(self.state, "")

    def _arm_suggestion(self):
        if self.mode != "guiado":
            return
        # Guiado-Facil: el comando queda listo (Enter). Guiado-Medio (o mas): aparece en
        # fantasma y hay que escribirlo si o si.
        require_typing = self.difficulty != "facil"
        self.term.suggest(self._suggested_command(), require_typing=require_typing)

    def _narrate(self, step):
        if self.mode != "guiado":
            return
        lines = script.narrate_guiado(step, self._lesson_key())
        if lines:
            self.term.write_lines(lines, tag="cyan")

    def _cmd_exploit(self, ip, method):
        if not self.free and not self.hosts:
            self.term.writeln("[!] Primero descubri la red (scan).", tag="amber")
            return
        if not ip:
            self.term.writeln("[!] uso:  exploit <ip> [leak|sqli|hydra]", tag="amber")
            self.term.writeln("    indica la IP del servidor a atacar.", tag="dim")
            return
        method = method or "hydra"
        host = self.cfg.host_by_ip(ip)
        role = host.role if host else "unknown"
        self.target_ip = ip

        # Modos accesibles: el "golpe 2" es el show de suspenso que termina en exito.
        # La via usada coincide con la leccion de la ronda (clave/expuesto/login).
        if self._accessible() and self.suspense is not None:
            acc_method = self._lesson_method()
            if self.netmap and role != "unknown":
                self.netmap.pulse_role(role, times=10, color=theme.AMBER)
            self._busy(True)
            self.suspense.play(
                role, self.lesson,
                on_done=lambda: self._async(lambda: self.backend.exploit(ip, acc_method),
                                            self._exploit_done))
            return

        if self.netmap and role != "unknown":
            self.netmap.pulse_role(role, times=10, color=theme.AMBER)
        # Exploit mas "vivo": pulso rojo por el camino + caos (glitch) en los nodos
        # (los switches/router "reventados" mientras corre el ataque).
        self.leds.animate_segments(seg.segments_for_role(role), seg.ANIM_EXPLOIT)
        for node_id in seg.NODE_LEDS:
            self.leds.animate_node(node_id, seg.ANIM_GLITCH)
        self._busy(True)
        self.term.type_lines([
            script.RUN_EXPLOIT.format(method=method, ip=ip),
            "  [" + "#" * 28 + "] 100%",
        ], tag="dim", on_done=lambda: self._async(lambda: self.backend.exploit(ip, method),
                                                  self._exploit_done))

    def _exploit_done(self, res):
        self.term.writeln("")
        self.term.write_lines(res.output, tag="green" if res.success else "red")
        if res.success:
            ip = self.target_ip
            self.sessions.add(ip)
            self.session_ip = ip
            self.cwd = "/"
            self.access = True
            self.state = EXPLOITED
            host = self.cfg.host_by_ip(ip)
            role = host.role if host else "fileserver"
            if self.netmap:
                self.netmap.focus_role(role)
            self.leds.animate_segments(seg.segments_for_role(role), seg.ANIM_FOCUS)
            n = script.nudge(self.difficulty, "exploited")
            if n:
                self.term.writeln("")
                self.term.writeln(n, tag="white")
        self._busy(False)
        if res.success:
            self._narrate("exploit")
            self._arm_suggestion()

    # ================= ping =================
    def _cmd_ping(self, ip):
        host = self.cfg.host_by_ip(ip)
        if host and self.netmap:
            self.netmap.focus_role(host.role)
        if host:
            # eco que viaja hasta el host y vuelve por cada tramo del camino
            self.leds.animate_segments(seg.segments_for_role(host.role), seg.ANIM_PING)
        elif ip == "127.0.0.1":
            self.leds.animate_segment(0, seg.ANIM_PING)        # a vos mismo (terminal)
        elif ip == "255.255.255.255" or ip.endswith(".255"):
            self.leds.animate_all(seg.ANIM_PING)               # broadcast: toda la red
        self._busy(True)
        self._async(lambda: self.backend.ping(ip), self._ping_done)

    def _ping_done(self, lines):
        self.term.write_lines(lines, tag="fg")
        self._busy(False)

    # ================= recon extra (telnet/traceroute/arp/netstat) =========
    def _cmd_telnet(self, ip, port):
        host = self.cfg.host_by_ip(ip)
        if host and self.netmap:
            self.netmap.focus_role(host.role)
        if host:
            # "golpear la puerta": escaneo/flicker sobre el camino al host
            self.leds.animate_segments(seg.segments_for_role(host.role), seg.ANIM_SCAN)
        self._busy(True)
        self._async(lambda: self.backend.telnet(ip, port), self._recon_done)

    def _cmd_traceroute(self, ip):
        host = self.cfg.host_by_ip(ip)
        role = host.role if host else None
        self._busy(True)

        def done(lines):
            self.term.write_lines(lines, tag="fg")
            self._busy(False)
            # LED: encender la ruta salto por salto hacia el objetivo
            if role:
                self._light_path_progressive(seg.segments_for_role(role), 0)

        self._async(lambda: self.backend.traceroute(ip), done)

    def _light_path_progressive(self, segs, i):
        if i >= len(segs):
            return
        self.leds.animate_segment(segs[i], seg.ANIM_DISCOVER)
        self.root.after(350, lambda: self._light_path_progressive(segs, i + 1))

    def _cmd_arp(self):
        ips = [h.ip for h in self.hosts] or [h.ip for h in self.cfg.hosts]
        # "quien es quien en la red": titilan los nodos (switches + router)
        for node_id in seg.NODE_LEDS:
            self.leds.animate_node(node_id, seg.ANIM_PROCESS)
        self._busy(True)
        self._async(lambda: self.backend.arp(ips), self._recon_done)

    def _cmd_netstat(self):
        ip = self.session_ip or (self.cfg.host_by_role("terminal").ip
                                 if self.cfg.host_by_role("terminal") else "127.0.0.1")
        # tus propias conexiones: pulso en tu tramo (el de la terminal, seg 0)
        self.leds.animate_segment(0, seg.ANIM_PING)
        self._busy(True)
        self._async(lambda: self.backend.netstat(ip), self._recon_done)

    def _recon_done(self, lines):
        self.term.write_lines(lines, tag="fg")
        self._busy(False)

    # ================= filesystem (cd / ls / read) =================
    def _resolve(self, path):
        if not path:
            return self.cwd
        joined = path if path.startswith("/") else posixpath.join(self.cwd, path)
        norm = posixpath.normpath(joined)
        if not norm.startswith("/"):
            norm = "/" + norm
        return norm

    def _no_access(self):
        self.term.writeln("[!] Todavia no tenes acceso a ningun host. Corre 'exploit <ip>' primero.",
                          tag="amber")

    def _cmd_cd(self, path):
        if not self.session_ip:
            self._no_access()
            return
        target = self._resolve(path)
        self._busy(True)
        self._async(lambda: self.backend.is_dir(self.session_ip, target),
                    lambda ok: self._cd_done(ok, target))

    def _cd_done(self, ok, target):
        if ok:
            self.cwd = target
            self.term.writeln("  -> " + target, tag="dim")
            segs = self._session_segments()
            if segs:
                self.leds.animate_segment(segs[-1], seg.ANIM_BLIP)  # blip al cambiar de carpeta
        else:
            self.term.writeln("[!] No existe el directorio: " + target, tag="amber")
            self.leds.animate_all(seg.ANIM_ERROR)
        self._busy(False)

    def _session_segments(self):
        """Tramos LED hacia el host donde tenes shell (para feedback de ls/cd)."""
        host = self.cfg.host_by_ip(self.session_ip) if self.session_ip else None
        return seg.segments_for_role(host.role) if host else []

    def _cmd_ls(self, path):
        if not self.session_ip:
            self._no_access()
            return
        target = self._resolve(path)
        # leyendo el directorio: shimmer corto sobre el tramo del servidor
        self.leds.animate_segments(self._session_segments(), seg.ANIM_BLIP)
        self._busy(True)
        self._async(lambda: self.backend.ls(self.session_ip, target), self._ls_done)

    def _ls_done(self, res):
        self.term.writeln("  " + res.path, tag="dim")
        for e in res.entries:
            tag = "cyan" if e.is_dir else "fg"
            suffix = "/" if e.is_dir else ""
            self.term.writeln("    " + e.name + suffix, tag=tag)
        if any(e.name == "restricted" for e in res.entries):
            n = script.nudge(self.difficulty, "found_restricted")
            if n:
                self.term.writeln(n, tag="white")
        was_exploited = self.state == EXPLOITED
        if self.state == EXPLOITED:
            self.state = LISTED
        self._busy(False)
        if was_exploited:
            self._narrate("ls")
        self._arm_suggestion()

    def _cmd_read(self, path):
        if not self.session_ip:
            self._no_access()
            return
        if not path:
            self.term.writeln("[!] uso: read <ruta>", tag="amber")
            return
        target = self._resolve(path)
        self._busy(True)
        self._async(lambda: self.backend.read(self.session_ip, target),
                    lambda r: self._read_done(r, target))

    def _read_done(self, res, target):
        self.term.writeln("")
        self.term.write_lines(res.content.splitlines(), tag="green")
        self._busy(False)
        got_flag = "FLAG{" in (res.content or "")
        host = self.cfg.host_by_ip(self.session_ip)
        role = host.role if host else "fileserver"
        if got_flag:
            if self.netmap:
                self.netmap.transfer_role(role)
            self.leds.animate_segments(seg.segments_for_role(role), seg.ANIM_TRANSFER)
        # En la MISION, leer el secreto del FILE-SERVER termina el juego.
        if not self.free and target.rstrip("/").endswith("secret.txt") \
                and self.session_ip == self.cfg.fileserver.ip:
            self.root.after(1200, self._complete)
        elif self.free and got_flag:
            self.term.writeln("")
            self.term.writeln("[+] FLAG capturada. Segui explorando otros hosts o 'menu' para salir.",
                              tag="white")

    # ================= fin =================
    def _complete(self):
        self.state = DONE
        self._cancel_timers()
        self.term.type_lines(script.MISSION_COMPLETE, tag="green", on_done=self._arm_done_reset)
        self.leds.animate_all(seg.ANIM_TRANSFER)

    def _arm_done_reset(self):
        self.term.set_input_enabled(False)
        self.root.focus_set()
        self.root.bind("<Key>", self._done_key)
        self.root.bind("<Button-1>", self._done_key_click)

    def _unbind_done(self):
        self.root.unbind("<Key>")
        self.root.unbind("<Button-1>")

    def _done_key(self, evt=None):
        key = (getattr(evt, "keysym", "") or "").lower()
        self._unbind_done()
        if key == "m":
            self._to_menu()
        else:
            self.enter_waiting()

    def _done_key_click(self, _evt=None):
        self._unbind_done()
        self.enter_waiting()

    # ================= timers / pistas =================
    def _start_timer(self):
        self._cancel_timers()
        if self.free:
            if self.on_timer:
                self.on_timer(None)   # None -> el label muestra tiempo infinito
            return
        self._tick_timer()

    def _tick_timer(self):
        if self.on_timer:
            self.on_timer(self._remaining)
        if self._remaining <= 0:
            self.term.writeln("[!] Tiempo agotado -- pero podes seguir para completar la mision.",
                              tag="amber")
            return
        self._remaining -= 1
        self._timer_job = self.root.after(1000, self._tick_timer)

    def _arm_hint(self):
        if self._hint_job:
            try:
                self.root.after_cancel(self._hint_job)
            except Exception:
                pass
        secs = self.cfg.timing.hint_idle_seconds
        self._hint_job = self.root.after(secs * 1000, self._show_hint)

    def _show_hint(self):
        if self.state in (WAITING, DONE):
            return
        if self.mode == "guiado":
            self.term.writeln("Pista: apreta  ENTER  para el paso que quedo listo aca abajo.",
                              tag="amber")
            self._arm_suggestion()
            self._arm_hint()
            return
        text = script.hint_for(self.difficulty, self.state)
        if text:
            self.term.writeln(text, tag="amber")
        self._arm_hint()

    def _cancel_timers(self):
        for job in (self._timer_job, self._hint_job):
            if job:
                try:
                    self.root.after_cancel(job)
                except Exception:
                    pass
        self._timer_job = None
        self._hint_job = None

    # ================= infraestructura async =================
    def _busy(self, busy):
        self.term.set_input_enabled(not busy)
        if not busy:
            self.term.focus_input()

    def _async(self, fn, on_done):
        def worker():
            try:
                res = fn()
                self._q.put((on_done, res, None))
            except Exception as exc:
                self._q.put((on_done, None, exc))
        threading.Thread(target=worker, daemon=True).start()

    def _pump(self):
        if not self._alive:
            return
        try:
            while True:
                on_done, res, err = self._q.get_nowait()
                if err is not None:
                    self.term.writeln("[!] Error: " + str(err), tag="red")
                    self.term.writeln("    (podes cambiar a modo Simulado como fallback)", tag="dim")
                    self._busy(False)
                else:
                    on_done(res)
        except queue.Empty:
            pass
        self.root.after(50, self._pump)
