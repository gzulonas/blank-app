#!/usr/bin/env python3
"""
decoder_gui.py — desktop front end for deep_decoder.py.

Pure standard library: tkinter only, no pip install, works offline.
Run it from the directory that holds deep_decoder.py:

    python3 decoder_gui.py

Note on tkinter: it ships with the official Python installers on Windows
and macOS. On Debian/Ubuntu it is packaged separately:

    sudo apt install python3-tk
"""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import filedialog, ttk

try:
    from deep_decoder import VOWEL_SETS, Config, decode, load_lexicon
except ImportError:
    sys.exit("deep_decoder.py must sit next to this file; run from that directory.")

EXAMPLES = [
    ("P-kalba", "La pa ba pas, kai pa ip se pe ka pa si pi?"),
    ("Merged", "Lapabapas, kaipaip sepekapasipi?"),
    ("K-kalba", "Nie kie ka kas"),
    ("LT echo", "Kada da tu ateisi si?"),
    ("EN echo", "I un understand it. When en will you?"),
    ("Not a cipher", "The fast fasting man."),
]

PAD = {"padx": 6, "pady": 4}


class DecoderGUI(ttk.Frame):
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master, padding=10)
        self.grid(row=0, column=0, sticky="nsew")
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=3)   # input
        self.rowconfigure(5, weight=3)   # output
        self.rowconfigure(7, weight=2)   # log

        self.lexicon: set[str] | None = None
        self.lexicon_path = tk.StringVar(value="none")

        self._build_options()
        self._build_examples()
        self._build_input()
        self._build_output()
        self._build_log()
        self._build_status()

        self.set_input(EXAMPLES[0][1])

    # ------------------------------------------------------------- widgets
    def _build_options(self) -> None:
        box = ttk.LabelFrame(self, text="Rules", padding=8)
        box.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        for c in (1, 3, 5):
            box.columnconfigure(c, weight=0)

        ttk.Label(box, text="Cipher consonants").grid(row=0, column=0, sticky="w", **PAD)
        self.consonants = tk.StringVar(value="p")
        ttk.Entry(box, textvariable=self.consonants, width=10).grid(row=0, column=1, sticky="w", **PAD)

        ttk.Label(box, text="Vowel set").grid(row=0, column=2, sticky="w", **PAD)
        self.lang = tk.StringVar(value="lt")
        ttk.Combobox(box, textvariable=self.lang, values=sorted(VOWEL_SETS),
                     width=7, state="readonly").grid(row=0, column=3, sticky="w", **PAD)

        ttk.Label(box, text="Ghost length").grid(row=0, column=4, sticky="w", **PAD)
        ghost = ttk.Frame(box)
        ghost.grid(row=0, column=5, sticky="w", **PAD)
        self.min_ghost = tk.IntVar(value=2)
        self.max_ghost = tk.IntVar(value=3)
        ttk.Spinbox(ghost, from_=1, to=9, textvariable=self.min_ghost, width=3,
                    command=self.decode_now).pack(side="left")
        ttk.Label(ghost, text="to").pack(side="left", padx=4)
        ttk.Spinbox(ghost, from_=1, to=9, textvariable=self.max_ghost, width=3,
                    command=self.decode_now).pack(side="left")

        self.strict = tk.BooleanVar(value=True)
        self.suffix_echo = tk.BooleanVar(value=True)
        self.prefix_echo = tk.BooleanVar(value=True)
        ttk.Checkbutton(box, text="Strict cipher gate", variable=self.strict,
                        command=self.decode_now).grid(row=1, column=0, columnspan=2, sticky="w", **PAD)
        ttk.Checkbutton(box, text="Suffix echo", variable=self.suffix_echo,
                        command=self.decode_now).grid(row=1, column=2, sticky="w", **PAD)
        ttk.Checkbutton(box, text="Prefix echo", variable=self.prefix_echo,
                        command=self.decode_now).grid(row=1, column=3, sticky="w", **PAD)

        lex = ttk.Frame(box)
        lex.grid(row=2, column=0, columnspan=6, sticky="w", **PAD)
        ttk.Button(lex, text="Load lexicon…", command=self.pick_lexicon).pack(side="left")
        ttk.Button(lex, text="Clear", command=self.clear_lexicon).pack(side="left", padx=(6, 10))
        ttk.Label(lex, textvariable=self.lexicon_path, foreground="#555").pack(side="left")

        for var in (self.consonants, self.lang):
            var.trace_add("write", lambda *_: self.decode_now())

    def _build_examples(self) -> None:
        row = ttk.Frame(self)
        row.grid(row=1, column=0, sticky="w", pady=(0, 4))
        ttk.Label(row, text="Examples:").pack(side="left", padx=(0, 6))
        for label, text in EXAMPLES:
            ttk.Button(row, text=label, width=12,
                       command=lambda t=text: self.set_input(t)).pack(side="left", padx=2)

    def _build_input(self) -> None:
        ttk.Label(self, text="Encoded text").grid(row=2, column=0, sticky="w")
        self.input = tk.Text(self, height=5, wrap="word", undo=True,
                             font=("TkFixedFont", 11))
        self.input.grid(row=3, column=0, sticky="nsew", pady=(2, 8))
        self.input.bind("<<Modified>>", self._on_modified)

    def _build_output(self) -> None:
        head = ttk.Frame(self)
        head.grid(row=4, column=0, sticky="ew")
        ttk.Label(head, text="Decoded").pack(side="left")
        ttk.Button(head, text="Copy", command=self.copy_output).pack(side="right")
        self.output = tk.Text(self, height=5, wrap="word", state="disabled",
                              font=("TkFixedFont", 11), background="#f4f4f6")
        self.output.grid(row=5, column=0, sticky="nsew", pady=(2, 8))

    def _build_log(self) -> None:
        ttk.Label(self, text="What changed").grid(row=6, column=0, sticky="w")
        self.log = tk.Text(self, height=5, wrap="none", state="disabled",
                           font=("TkFixedFont", 10), background="#f4f4f6")
        self.log.grid(row=7, column=0, sticky="nsew", pady=(2, 8))

    def _build_status(self) -> None:
        self.status = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status, foreground="#555").grid(
            row=8, column=0, sticky="w")

    # ------------------------------------------------------------- actions
    def set_input(self, text: str) -> None:
        self.input.delete("1.0", "end")
        self.input.insert("1.0", text)
        self.decode_now()

    def _on_modified(self, _event=None) -> None:
        if self.input.edit_modified():
            self.input.edit_modified(False)
            self.decode_now()

    def pick_lexicon(self) -> None:
        path = filedialog.askopenfilename(
            title="Lexicon: one word per line",
            filetypes=[("Text", "*.txt"), ("All files", "*")])
        if not path:
            return
        try:
            self.lexicon = load_lexicon(path)
        except OSError as exc:
            self.status.set(f"Could not read lexicon: {exc}")
            return
        self.lexicon_path.set(f"{path.split('/')[-1]} ({len(self.lexicon)} words)")
        self.decode_now()

    def clear_lexicon(self) -> None:
        self.lexicon = None
        self.lexicon_path.set("none")
        self.decode_now()

    def copy_output(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.output.get("1.0", "end-1c"))
        self.status.set("Decoded text copied to clipboard.")

    def _config(self) -> Config:
        lo, hi = self.min_ghost.get(), self.max_ghost.get()
        return Config(
            consonants=self.consonants.get() or "p",
            lang=self.lang.get(),
            strict=self.strict.get(),
            suffix_echo=self.suffix_echo.get(),
            prefix_echo=self.prefix_echo.get(),
            min_ghost=min(lo, hi),
            max_ghost=max(lo, hi),
            lexicon=self.lexicon,
        )

    def decode_now(self, *_args) -> None:
        source = self.input.get("1.0", "end-1c")
        try:
            result = decode(source, self._config())
        except Exception as exc:                      # never let the GUI die on bad input
            self.status.set(f"Decode failed: {exc}")
            return

        self._replace(self.output, result.text)
        if result.log:
            lines = [f"[{rule}]  {before!r}  ->  {after!r}" for rule, before, after in result.log]
            self._replace(self.log, "\n".join(lines))
            n = len(result.log)
            self.status.set(f"{n} change{'' if n == 1 else 's'} applied.")
        else:
            self._replace(self.log, "")
            self.status.set("No cipher or echo found — text left as it is."
                            if source.strip() else "")

    @staticmethod
    def _replace(widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")


def main() -> int:
    root = tk.Tk()
    root.title("Deep Decoder")
    root.minsize(760, 620)
    DecoderGUI(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
