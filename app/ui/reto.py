"""Vista del modo RETO (escape room) -- version "juego".

Arriba, una barra de CONTROL DE LA RED que se llena a medida que capturas nodos.
Abajo, el acertijo actual, que puede ser de varios tipos:
  - choice   : tocar una opcion
  - text     : escribir una respuesta corta
  - keypad   : cargar un numero en un teclado en pantalla
  - sequence : repetir un patron tocando los nodos (estilo Simon), guiado por el tablero

Vista "tonta": muestra lo que el RetoController le pide y avisa por
on_answer(value) / on_hint() / on_restart(). Para secuencias, cada toque de nodo
manda on_answer(clave_del_nodo).
"""
from __future__ import annotations

import customtkinter as ctk

from app.ui import responsive, theme

# Nodos que se tocan en los acertijos de secuencia (clave -> etiqueta).
NODE_BUTTONS = [("izq", "SW-IZQ"), ("router", "ROUTER"), ("der", "SW-DER")]


class RetoView(ctk.CTkFrame):
    def __init__(self, parent, mono_font, on_answer=None, on_hint=None, on_restart=None):
        super().__init__(parent, fg_color=theme.BG)
        self.mono = mono_font
        self.on_answer = on_answer
        self.on_hint = on_hint
        self.on_restart = on_restart
        self._entry = None
        self._keypad_value = ""
        self._keypad_lbl = None

        wrap = ctk.CTkFrame(self, fg_color=theme.BG)
        wrap.place(relx=0.5, rely=0.5, anchor="center")
        wrap.grid_columnconfigure(0, weight=1)
        responsive.bind_minsize(wrap, 0, 720)
        r = [0]

        def add(w, pady=(0, 6)):
            w.grid(row=r[0], column=0, sticky="ew", padx=30, pady=pady)
            r[0] += 1

        add(ctk.CTkLabel(wrap, text="RETO  //  TOMA EL CONTROL DE LA RED",
                         text_color=theme.DIM, font=(mono_font, 15)), pady=(0, 8))

        # --- barra de control de la red (progreso) ---
        self.ctrl_lbl = ctk.CTkLabel(wrap, text="CONTROL DE LA RED  0%", text_color=theme.CYAN,
                                     font=(mono_font, 14, "bold"))
        add(self.ctrl_lbl, pady=(0, 2))
        self.ctrl_bar = ctk.CTkProgressBar(wrap, height=16, corner_radius=8,
                                           progress_color=theme.GREEN, fg_color="#10220f")
        self.ctrl_bar.set(0.0)
        add(self.ctrl_bar, pady=(0, 16))

        self.counter = ctk.CTkLabel(wrap, text="", text_color=theme.CYAN, font=(mono_font, 13, "bold"))
        add(self.counter, pady=(0, 6))
        self.question = ctk.CTkLabel(wrap, text="", text_color=theme.FG, font=(mono_font, 21),
                                     wraplength=720, justify="center")
        add(self.question, pady=(0, 8))
        self.clue = ctk.CTkLabel(wrap, text="", text_color=theme.CYAN, font=(mono_font, 15),
                                 wraplength=720, justify="center")
        add(self.clue, pady=(0, 16))

        self.answers = ctk.CTkFrame(wrap, fg_color=theme.BG)
        self.answers.grid(row=r[0], column=0, sticky="ew", padx=20, pady=(0, 12))
        self.answers.grid_columnconfigure((0, 1, 2), weight=1)
        r[0] += 1

        self.result = ctk.CTkLabel(wrap, text="", text_color=theme.WHITE, font=(mono_font, 16),
                                   wraplength=720, justify="center")
        add(self.result, pady=(0, 10))

        self.hint_btn = ctk.CTkButton(wrap, text="PISTA", command=self._hint,
                                      fg_color=theme.BG_PANEL, hover_color="#222",
                                      text_color=theme.AMBER, border_color=theme.AMBER,
                                      border_width=1, font=(mono_font, 14), height=36, width=150)
        self.hint_btn.grid(row=r[0], column=0, pady=(0, 10))

    # ------------------------------------------------------------------
    def _hint(self):
        if self.on_hint:
            self.on_hint()

    def _answer(self, value):
        if self.on_answer:
            self.on_answer(value)

    def set_progress(self, pct):
        self.ctrl_bar.set(max(0.0, min(1.0, pct)))
        self.ctrl_lbl.configure(text="CONTROL DE LA RED  %d%%" % int(pct * 100))

    def _clear_answers(self):
        for w in self.answers.winfo_children():
            w.destroy()
        self._entry = None
        self._keypad_value = ""
        self._keypad_lbl = None

    def lock_answers(self, locked):
        for w in self.answers.winfo_children():
            try:
                w.configure(state="disabled" if locked else "normal")
            except Exception:
                pass

    # ------------------------------------------------------------------
    def render_puzzle(self, idx, total, question, clue, ptype, options=None):
        self.counter.configure(text="ACERTIJO %d DE %d" % (idx, total))
        self.question.configure(text=question, text_color=theme.FG)
        self.clue.configure(text=clue)
        self.result.configure(text="")
        self.hint_btn.configure(state="normal")
        self._clear_answers()
        if ptype == "choice":
            self._build_choice(options or [])
        elif ptype == "text":
            self._build_text()
        elif ptype == "keypad":
            self._build_keypad()
        elif ptype == "sequence":
            self._build_sequence()

    def _build_choice(self, options):
        self.answers.grid_columnconfigure((0, 1, 2), weight=1)
        for i, o in enumerate(options):
            b = ctk.CTkButton(self.answers, text=o, command=lambda o=o: self._answer(o),
                              fg_color=theme.BG_PANEL, hover_color="#163b16",
                              border_color=theme.GREEN, border_width=2, text_color=theme.FG,
                              font=(self.mono, 17, "bold"), height=58)
            b.grid(row=i // 2, column=(i % 2) * 2, columnspan=2 if len(options) <= 2 else 1,
                   padx=8, pady=8, sticky="ew")

    def _build_text(self):
        self._entry = ctk.CTkEntry(self.answers, font=(self.mono, 22), height=54, justify="center")
        self._entry.grid(row=0, column=0, columnspan=2, padx=8, pady=8, sticky="ew")
        self._entry.bind("<Return>", lambda e: self._submit_text())
        ctk.CTkButton(self.answers, text="OK", command=self._submit_text, fg_color=theme.GREEN,
                      text_color="#04140a", font=(self.mono, 17, "bold"), height=54
                      ).grid(row=0, column=2, padx=8, pady=8, sticky="ew")
        self._entry.focus_set()

    def _submit_text(self):
        if self._entry is not None:
            v = self._entry.get().strip()
            if v:
                self._answer(v)

    def _build_keypad(self):
        self._keypad_value = ""
        self._keypad_lbl = ctk.CTkLabel(self.answers, text="_", text_color=theme.GREEN,
                                        font=(self.mono, 30, "bold"))
        self._keypad_lbl.grid(row=0, column=0, columnspan=3, pady=(0, 8), sticky="ew")
        keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "C", "0", "OK"]
        for i, k in enumerate(keys):
            col = i % 3
            row = 1 + i // 3
            if k == "OK":
                fg, tc, cmd = theme.GREEN, "#04140a", self._keypad_ok
            elif k == "C":
                fg, tc, cmd = theme.BG_PANEL, theme.AMBER, self._keypad_clear
            else:
                fg, tc, cmd = theme.BG_PANEL, theme.FG, (lambda d=k: self._keypad_press(d))
            ctk.CTkButton(self.answers, text=k, command=cmd, fg_color=fg, text_color=tc,
                          border_color=theme.DIM, border_width=1, font=(self.mono, 20, "bold"),
                          height=52).grid(row=row, column=col, padx=6, pady=6, sticky="ew")

    def _keypad_press(self, d):
        if len(self._keypad_value) < 6:
            self._keypad_value += d
            self._keypad_lbl.configure(text=self._keypad_value)

    def _keypad_clear(self):
        self._keypad_value = ""
        self._keypad_lbl.configure(text="_")

    def _keypad_ok(self):
        if self._keypad_value:
            self._answer(self._keypad_value)

    def _build_sequence(self):
        self.answers.grid_columnconfigure((0, 1, 2), weight=1)
        for i, (key, label) in enumerate(NODE_BUTTONS):
            ctk.CTkButton(self.answers, text=label, command=lambda k=key: self._answer(k),
                          fg_color=theme.BG_PANEL, hover_color="#163b16", border_color=theme.CYAN,
                          border_width=2, text_color=theme.FG, font=(self.mono, 18, "bold"),
                          height=72).grid(row=0, column=i, padx=8, pady=8, sticky="ew")

    def show_result(self, text, color=None):
        self.result.configure(text=text, text_color=color or theme.WHITE)

    def render_done(self, title, subtitle, win=True):
        self.counter.configure(text="")
        self.question.configure(text=title, text_color=theme.GREEN if win else theme.RED)
        self.clue.configure(text="")
        self.result.configure(text=subtitle, text_color=theme.WHITE)
        self.hint_btn.configure(state="disabled")
        self._clear_answers()
        ctk.CTkButton(self.answers, text="JUGAR DE NUEVO",
                      command=(self.on_restart or (lambda: None)), fg_color=theme.CYAN,
                      text_color="#04140a", font=(self.mono, 17, "bold"), height=58
                      ).grid(row=0, column=0, columnspan=3, padx=8, pady=8, sticky="ew")
