"""Vista del modo RETO (escape room): acertijos con pistas en el tablero.

El tablero de LEDs y los componentes fisicos (router, switches, cable/canaleta) son
el ORACULO que da las pistas; el visitante responde eligiendo una opcion o tipeando.
Vista "tonta": muestra lo que el RetoController le pide y avisa respuestas/pistas
por on_answer() / on_hint() / on_restart().
"""
from __future__ import annotations

import customtkinter as ctk

from app.ui import theme


class RetoView(ctk.CTkFrame):
    def __init__(self, parent, mono_font, on_answer=None, on_hint=None, on_restart=None):
        super().__init__(parent, fg_color=theme.BG)
        self.mono = mono_font
        self.on_answer = on_answer
        self.on_hint = on_hint
        self.on_restart = on_restart
        self._entry = None

        wrap = ctk.CTkFrame(self, fg_color=theme.BG)
        wrap.place(relx=0.5, rely=0.5, anchor="center")
        wrap.grid_columnconfigure(0, weight=1, minsize=700)
        r = [0]

        def add(w, pady=(0, 6)):
            w.grid(row=r[0], column=0, sticky="ew", padx=30, pady=pady)
            r[0] += 1

        add(ctk.CTkLabel(wrap, text="RETO  //  ESCAPE DE LA RED", text_color=theme.DIM,
                         font=(mono_font, 15)), pady=(0, 6))
        self.counter = ctk.CTkLabel(wrap, text="", text_color=theme.CYAN,
                                    font=(mono_font, 14, "bold"))
        add(self.counter, pady=(0, 14))
        self.question = ctk.CTkLabel(wrap, text="", text_color=theme.FG, font=(mono_font, 21),
                                     wraplength=700, justify="center")
        add(self.question, pady=(0, 10))
        self.clue = ctk.CTkLabel(wrap, text="", text_color=theme.CYAN, font=(mono_font, 15),
                                 wraplength=700, justify="center")
        add(self.clue, pady=(0, 18))

        self.answers = ctk.CTkFrame(wrap, fg_color=theme.BG)
        self.answers.grid(row=r[0], column=0, sticky="ew", padx=20, pady=(0, 14))
        self.answers.grid_columnconfigure((0, 1), weight=1)
        r[0] += 1

        self.result = ctk.CTkLabel(wrap, text="", text_color=theme.WHITE, font=(mono_font, 17),
                                   wraplength=700, justify="center")
        add(self.result, pady=(0, 12))

        self.hint_btn = ctk.CTkButton(wrap, text="PISTA", command=self._hint,
                                      fg_color=theme.BG_PANEL, hover_color="#222",
                                      text_color=theme.AMBER, border_color=theme.AMBER,
                                      border_width=1, font=(mono_font, 14), height=38, width=160)
        self.hint_btn.grid(row=r[0], column=0, pady=(0, 10))

    # ------------------------------------------------------------------
    def _hint(self):
        if self.on_hint:
            self.on_hint()

    def _choose(self, opt):
        if self.on_answer:
            self.on_answer(opt)

    def _submit_text(self):
        if self._entry is not None and self.on_answer:
            v = self._entry.get().strip()
            if v:
                self.on_answer(v)

    def _clear_answers(self):
        for w in self.answers.winfo_children():
            w.destroy()
        self._entry = None

    def render_puzzle(self, idx, total, question, clue, ptype, options=None):
        self.counter.configure(text="ACERTIJO %d DE %d" % (idx, total))
        self.question.configure(text=question, text_color=theme.FG)
        self.clue.configure(text=clue)
        self.result.configure(text="")
        self.hint_btn.configure(state="normal")
        self._clear_answers()
        if ptype == "choice":
            for i, o in enumerate(options or []):
                b = ctk.CTkButton(self.answers, text=o, command=lambda o=o: self._choose(o),
                                  fg_color=theme.BG_PANEL, hover_color="#163b16",
                                  border_color=theme.GREEN, border_width=2, text_color=theme.FG,
                                  font=(self.mono, 17, "bold"), height=58)
                b.grid(row=i // 2, column=i % 2, padx=8, pady=8, sticky="ew")
        else:
            self._entry = ctk.CTkEntry(self.answers, font=(self.mono, 22), height=54,
                                       justify="center")
            self._entry.grid(row=0, column=0, padx=8, pady=8, sticky="ew")
            self._entry.bind("<Return>", lambda e: self._submit_text())
            ctk.CTkButton(self.answers, text="RESPONDER", command=self._submit_text,
                          fg_color=theme.GREEN, text_color="#04140a",
                          font=(self.mono, 17, "bold"), height=54, width=160
                          ).grid(row=0, column=1, padx=8, pady=8)
            self._entry.focus_set()

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
                      ).grid(row=0, column=0, columnspan=2, padx=8, pady=8, sticky="ew")
