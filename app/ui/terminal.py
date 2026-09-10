"""Panel tipo terminal: transcripto con efecto de tipeo + linea de input.

Usa tkinter nativo (tk.Text/tk.Entry) para tener control fino de tags de color y
del efecto typewriter. Se integra dentro de la ventana customtkinter sin problema.
"""
from __future__ import annotations

import tkinter as tk

from app.ui import theme


class TerminalPanel(tk.Frame):
    def __init__(self, parent, mono_font, cps: int = 160, on_submit=None):
        super().__init__(parent, bg=theme.BG, highlightthickness=0)
        self.cps = cps
        self.on_submit = on_submit
        self._typing = False
        self._pending_after = None

        self.text = tk.Text(
            self,
            bg=theme.BG,
            fg=theme.FG,
            insertbackground=theme.GREEN,
            font=(mono_font, 13),
            bd=0,
            highlightthickness=0,
            padx=14,
            pady=10,
            wrap="word",
            state="disabled",
            spacing1=1,
            spacing3=1,
        )
        self.text.pack(fill="both", expand=True)

        # Fila de prompt
        prow = tk.Frame(self, bg=theme.BG)
        prow.pack(fill="x", side="bottom")
        self.prompt = tk.Label(prow, text=" visitante@cyberlab:~$ ", bg=theme.BG,
                               fg=theme.GREEN, font=(mono_font, 13, "bold"))
        self.prompt.pack(side="left")
        self.entry = tk.Entry(prow, bg=theme.BG, fg=theme.WHITE, insertbackground=theme.GREEN,
                              font=(mono_font, 13), bd=0, highlightthickness=0)
        self.entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.entry.bind("<Return>", self._submit)

        # Tags de color
        self.text.tag_config("fg", foreground=theme.FG)
        self.text.tag_config("green", foreground=theme.GREEN)
        self.text.tag_config("dim", foreground=theme.DIM)
        self.text.tag_config("amber", foreground=theme.AMBER)
        self.text.tag_config("red", foreground=theme.RED)
        self.text.tag_config("cyan", foreground=theme.CYAN)
        self.text.tag_config("white", foreground=theme.WHITE)
        self.text.tag_config("banner", foreground=theme.GREEN)

        self._blink_prompt()

    # ------------------------------------------------------------------
    @property
    def is_typing(self) -> bool:
        return self._typing

    def _insert(self, s: str, tag: str = "fg") -> None:
        self.text.config(state="normal")
        self.text.insert("end", s, tag)
        self.text.see("end")
        self.text.config(state="disabled")

    def writeln(self, text: str = "", tag: str = "fg") -> None:
        self._insert(text + "\n", tag)

    def write_lines(self, lines, tag: str = "fg") -> None:
        for ln in lines:
            self.writeln(ln, tag)

    def echo_command(self, cmd: str) -> None:
        self._insert(" visitante@cyberlab:~$ ", "green")
        self._insert(cmd + "\n", "white")

    def type_lines(self, lines, on_done=None, tag: str = "fg", cps: int | None = None) -> None:
        cps = cps or self.cps
        text = "\n".join(lines) + "\n"
        self._typing = True
        self.set_input_enabled(False)
        step = max(1, cps // 50)
        idx = {"i": 0}

        def tick():
            i = idx["i"]
            if i >= len(text):
                self._typing = False
                self.set_input_enabled(True)
                self.focus_input()
                if on_done:
                    on_done()
                return
            self._insert(text[i:i + step], tag)
            idx["i"] += step
            self._pending_after = self.after(20, tick)

        tick()

    def clear(self) -> None:
        if self._pending_after:
            try:
                self.after_cancel(self._pending_after)
            except Exception:
                pass
        self._typing = False
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.config(state="disabled")

    def set_input_enabled(self, enabled: bool) -> None:
        self.entry.config(state="normal" if enabled else "disabled")

    def focus_input(self) -> None:
        try:
            self.entry.focus_set()
        except Exception:
            pass

    def _submit(self, _evt=None):
        if self._typing:
            return "break"
        line = self.entry.get()
        self.entry.delete(0, "end")
        if self.on_submit:
            self.on_submit(line)
        return "break"

    def _blink_prompt(self):
        cur = self.prompt.cget("fg")
        self.prompt.config(fg=theme.BG if cur == theme.GREEN else theme.GREEN)
        self.after(600, self._blink_prompt)
