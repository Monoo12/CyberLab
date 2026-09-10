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
from app.mission.commands import CommandParser
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
                 show_waiting, show_mission, on_return_menu=None, on_timer=None):
        self.root = root
        self.cfg = cfg
        self.backend = backend
        self.term = terminal
        self.netmap = netmap
        self.leds = leds
        self.show_waiting = show_waiting
        self.show_mission = show_mission
        self.on_return_menu = on_return_menu
        self.on_timer = on_timer

        self.parser = CommandParser(cfg.network.cidr)
        self.difficulty = cfg.modes.difficulty
        self.state = WAITING
        self.hosts = []
        self.cwd = "/"
        self.target = cfg.host_by_role("fileserver")
        self.target_ip = self.target.ip if self.target else None
        self.access = False

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
        self.access = False
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
        self.term.type_lines(script.briefing(self.difficulty), tag="fg", on_done=self._after_briefing)

    def _after_briefing(self):
        self._start_timer()
        self._arm_hint()
        self.term.focus_input()

    def on_any_key(self):
        if self.state == WAITING:
            self.start_mission()
        elif self.state == DONE:
            self.enter_waiting()

    def shutdown(self):
        """Detiene el controller (pump/timers) al volver al menu o cerrar."""
        self._alive = False
        self._cancel_timers()
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
            return

        handlers = {
            "help": self._cmd_help,
            "hint": self._cmd_hint,
            "clear": lambda: self.term.clear(),
            "pwd": lambda: self.term.writeln("  " + self.cwd, tag="cyan"),
            "whoami": self._cmd_whoami,
            "menu": self._to_menu,
            "scan": self._cmd_scan,
            "inspect": lambda: self._cmd_inspect(pc.ip),
            "connect": lambda: self._cmd_connect(pc.ip, pc.port),
            "exploit": lambda: self._cmd_exploit(pc.ip, pc.method),
            "ping": lambda: self._cmd_ping(pc.ip),
            "cd": lambda: self._cmd_cd(pc.path),
            "ls": lambda: self._cmd_ls(pc.path),
            "read": lambda: self._cmd_read(pc.path),
            "empty": lambda: None,
        }
        h = handlers.get(pc.name)
        if h:
            h()

    # ================= comandos informativos =================
    def _cmd_help(self):
        self.term.write_lines(script.help_for(self.difficulty), tag="cyan")

    def _cmd_hint(self):
        self._show_hint()

    def _cmd_whoami(self):
        if self.access:
            self.term.writeln("  " + self.cfg.fileserver.ssh_user + "@FILE-SERVER", tag="green")
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
    def _cmd_inspect(self, ip):
        if self.state == BRIEFING or not self.hosts:
            self.term.writeln("[!] Primero descubri la red (scan).", tag="amber")
            return
        host = self.cfg.host_by_ip(ip)
        role = host.role if host else "fileserver"
        if self.netmap:
            self.netmap.focus_role(role)
        self.leds.animate_segments(seg.segments_for_role(role), seg.ANIM_FOCUS)
        self.target_ip = ip
        self._busy(True)
        self.term.type_lines([script.RUN_INSPECT.format(ip=ip)], tag="dim",
                             on_done=lambda: self._async(lambda: self.backend.inspect(ip),
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

    # ================= exploit =================
    def _cmd_exploit(self, ip, method):
        if not self.hosts:
            self.term.writeln("[!] Primero descubri la red (scan).", tag="amber")
            return
        if not ip:
            self.term.writeln("[!] uso:  exploit <ip> [leak|sqli|hydra]", tag="amber")
            self.term.writeln("    indica la IP del servidor a atacar.", tag="dim")
            return
        method = method or "hydra"
        host = self.cfg.host_by_ip(ip)
        role = host.role if host else "unknown"
        if self.netmap and role != "unknown":
            self.netmap.pulse_role(role, times=10, color=theme.AMBER)
        self.leds.animate_segments(seg.segments_for_role(role), seg.ANIM_EXPLOIT)
        self.target_ip = ip
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
            self.access = True
            self.state = EXPLOITED
            if self.netmap:
                self.netmap.focus_role("fileserver")
            self.leds.animate_segments(seg.segments_for_role("fileserver"), seg.ANIM_FOCUS)
            n = script.nudge(self.difficulty, "exploited")
            if n:
                self.term.writeln("")
                self.term.writeln(n, tag="white")
        self._busy(False)

    # ================= ping =================
    def _cmd_ping(self, ip):
        host = self.cfg.host_by_ip(ip)
        if host and self.netmap:
            self.netmap.focus_role(host.role)
        if host:
            self.leds.animate_segments(seg.segments_for_role(host.role), seg.ANIM_FOCUS)
        self._busy(True)
        self._async(lambda: self.backend.ping(ip), self._ping_done)

    def _ping_done(self, lines):
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

    def _cmd_cd(self, path):
        if not self.access:
            self.term.writeln("[!] Todavia no tenes acceso. Corre 'exploit' primero.", tag="amber")
            return
        target = self._resolve(path)
        self._busy(True)
        self._async(lambda: self.backend.is_dir(target), lambda ok: self._cd_done(ok, target))

    def _cd_done(self, ok, target):
        if ok:
            self.cwd = target
            self.term.writeln("  -> " + target, tag="dim")
        else:
            self.term.writeln("[!] No existe el directorio: " + target, tag="amber")
        self._busy(False)

    def _cmd_ls(self, path):
        if not self.access:
            self.term.writeln("[!] Todavia no tenes acceso. Corre 'exploit' primero.", tag="amber")
            return
        target = self._resolve(path)
        self._busy(True)
        self._async(lambda: self.backend.ls(target), self._ls_done)

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
        if self.state == EXPLOITED:
            self.state = LISTED
        self._busy(False)

    def _cmd_read(self, path):
        if not self.access:
            self.term.writeln("[!] Todavia no tenes acceso. Corre 'exploit' primero.", tag="amber")
            return
        if not path:
            self.term.writeln("[!] uso: read <ruta>", tag="amber")
            return
        target = self._resolve(path)
        self._busy(True)
        self._async(lambda: self.backend.read(target), lambda r: self._read_done(r, target))

    def _read_done(self, res, target):
        self.term.writeln("")
        self.term.write_lines(res.content.splitlines(), tag="green")
        self._busy(False)
        if target.rstrip("/").endswith("secret.txt"):
            if self.netmap:
                self.netmap.transfer_role("fileserver")
            self.leds.animate_segments(seg.segments_for_role("fileserver"), seg.ANIM_TRANSFER)
            self.root.after(1200, self._complete)

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
