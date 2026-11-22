#!/usr/bin/env python3
"""
deep_decoder.py — local decoder for syllable-insertion ciphers
(Lithuanian P-kalba / K-kalba style) and cross-word "echo" syllables.

Pass 1  cipher:  vowel-cluster + C + same cluster  ->  cluster
                 ("Lapabapas" -> "Labas", "kapaipaip" -> "kaip"),
                 including the spaced camouflage form ("La pa ba pas").
Pass 2  lexicon (opt.): re-split merged words using a word list.
Pass 3  echoes:  suffix ghost  "Kada da"       -> "Kada"
                 prefix ghost  "su supras"     -> "supras"
                 works the same in English:    "I un understand" -> "I understand"

Why ghosts are capped at 3 letters by default
---------------------------------------------
Every real echo is a short particle: un, su, iš, ne, da, si, en. A longer
repeat is usually two genuine words that happen to share a stem --
"the fast fasting man", "lapas lapoja". Removing one of those destroys
meaning, so the ghost window is the guardrail. Widen it with --max-ghost
only if you know the input is fully enciphered.

Usage:
  python deep_decoder.py "La pa ba pas, kai pa ip se pe ka pa si pi?"
  echo "Kada da tu ateisi si?" | python deep_decoder.py
  python deep_decoder.py -c pk --explain "Nie kie ka kas"
  python deep_decoder.py --lang en "I un understand it."
  python deep_decoder.py --lexicon words.txt "Ka pa da pa ei pei si pi?"
  python deep_decoder.py --selftest
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field

VOWELS_LT = "aąeęėiįyouųū"
VOWELS_EN = "aeiou"
VOWEL_SETS = {
    "lt": set(VOWELS_LT + VOWELS_LT.upper()),
    "en": set(VOWELS_EN + VOWELS_EN.upper()),
    "both": set((VOWELS_LT + VOWELS_EN) + (VOWELS_LT + VOWELS_EN).upper()),
}

CHUNK_SPLIT = re.compile(r"([.,!?;:\n]+)")
WORD_OR_SEP = re.compile(r"\w+|\W+")


@dataclass
class Config:
    consonants: str = "p"          # cipher consonants to try (e.g. "pk")
    lang: str = "lt"               # which vowel set the cipher pass uses
    strict: bool = True            # every vowel cluster in a chunk must be echoed
    min_echoes: int = 2            # protects short real words like "lapas"
    suffix_echo: bool = True
    prefix_echo: bool = True
    min_ghost: int = 2             # a 1-letter ghost is too ambiguous to trust
    max_ghost: int = 3             # see module docstring: this is the guardrail
    lexicon: set[str] | None = None

    @property
    def vowels(self) -> set[str]:
        return VOWEL_SETS[self.lang]


@dataclass
class Result:
    text: str
    log: list[tuple[str, str, str]] = field(default_factory=list)  # (rule, before, after)


def _is_inline_space(ch: str) -> bool:
    return ch.isspace() and ch != "\n"


# ---------------------------------------------------------------- pass 1: cipher
def _match_echo(s: str, pos: int, cluster: str, consonant: str, vowels: set[str]):
    """At s[pos:], match [spaces] C ([spaces] copy-letter)*.
    Returns (end, had_space) or None. Case-insensitive."""
    i, had_space = pos, False
    while i < len(s) and _is_inline_space(s[i]):
        i, had_space = i + 1, True
    if i >= len(s) or s[i].lower() != consonant:
        return None
    i += 1
    for letter in cluster:
        while i < len(s) and _is_inline_space(s[i]):
            i, had_space = i + 1, True
        if i >= len(s) or s[i].lower() != letter.lower():
            return None
        i += 1
    # the copy must end the cluster: "apaa" is not an echo of "a"
    if i < len(s) and s[i] in vowels:
        return None
    return i, had_space


def _decode_chunk(chunk: str, consonant: str, vowels: set[str]):
    """Returns (decoded, echoes, unechoed_clusters)."""
    out, i, echoes, unechoed = [], 0, 0, 0
    while i < len(chunk):
        if chunk[i] not in vowels:
            out.append(chunk[i])
            i += 1
            continue
        j = i
        while j < len(chunk) and chunk[j] in vowels:
            j += 1
        cluster = chunk[i:j]
        out.append(cluster)
        m = _match_echo(chunk, j, cluster, consonant, vowels)
        if m:
            end, had_space = m
            echoes += 1
            # camouflage: spaces around the inserted syllable are fake --
            # also drop the one right after it ("se pe ka" -> "seka")
            if had_space and end < len(chunk) and _is_inline_space(chunk[end]):
                end += 1
            i = end
        else:
            unechoed += 1
            i = j
    return "".join(out), echoes, unechoed


def decode_cipher(text: str, cfg: Config, log: list) -> tuple[str, list[bool]]:
    """Chunk by punctuation; decode a chunk only if it passes the consistency gate.
    Returns text and a per-chunk 'was decoded' flag (used by the lexicon pass)."""
    parts = CHUNK_SPLIT.split(text)
    vowels = cfg.vowels
    flags = []
    for idx in range(0, len(parts), 2):          # even indexes = chunks, odd = delimiters
        chunk, best = parts[idx], None
        for c in cfg.consonants.lower():
            dec, n, miss = _decode_chunk(chunk, c, vowels)
            ok = n >= cfg.min_echoes and (miss == 0 if cfg.strict else True)
            if ok and (best is None or n > best[1]):
                best = (dec, n, c)
        if best:
            log.append((f"cipher[{best[2]}]", chunk.strip(), best[0].strip()))
            parts[idx] = best[0]
        flags.append(bool(best))
    return "".join(parts), flags


# ---------------------------------------------------------------- pass 3: echoes
def _both_real_words(a: str, b: str, lex: set[str] | None) -> bool:
    """With a lexicon, two words that both exist are never an echo pair."""
    return bool(lex) and a in lex and b in lex


def dedupe_echoes(text: str, cfg: Config, log: list) -> str:
    lex = cfg.lexicon
    for _ in range(10):                          # until stable
        toks = WORD_OR_SEP.findall(text)
        changed = False
        k = 0
        while k + 2 < len(toks):
            w, sep, x = toks[k], toks[k + 1], toks[k + 2]
            if not (w[0].isalnum() and x[0].isalnum() and sep.strip() == ""):
                k += 1
                continue
            wl, xl = w.lower(), x.lower()
            ghost_ok = lambda g: cfg.min_ghost <= len(g) <= cfg.max_ghost

            # "Kada da": standalone ghost equals the tail of the previous word
            if (cfg.suffix_echo and ghost_ok(x) and len(w) > len(x)
                    and wl.endswith(xl) and not _both_real_words(wl, xl, lex)):
                log.append(("suffix-echo", f"{w}{sep}{x}", w))
                del toks[k + 1:k + 3]
                changed = True
                continue

            # "su supras": standalone ghost equals the head of the next word
            if (cfg.prefix_echo and ghost_ok(w) and len(x) >= len(w) + 2
                    and xl.startswith(wl) and not _both_real_words(wl, xl, lex)):
                if w[0].isupper():                # keep sentence capitalisation
                    toks[k + 2] = x[0].upper() + x[1:]
                log.append(("prefix-echo", f"{w}{sep}{x}", toks[k + 2]))
                del toks[k:k + 2]
                changed = True
                continue
            k += 1
        text = "".join(toks)
        if not changed:
            break
    return text


# ---------------------------------------------------------------- pass 2: lexicon
def _segment(word: str, lex: set[str]) -> str | None:
    """Split word into the fewest lexicon words; None if impossible."""
    low, n = word.lower(), len(word)
    best: list[list[int] | None] = [None] * (n + 1)
    best[0] = []
    for i in range(n):
        if best[i] is None:
            continue
        for j in range(i + 1, n + 1):
            if low[i:j] in lex and (best[j] is None or len(best[i]) + 1 < len(best[j])):
                best[j] = best[i] + [j]
    if best[n] is None or len(best[n]) < 2:
        return None
    cuts, prev, pieces = best[n], 0, []
    for c in cuts:
        pieces.append(word[prev:c])
        prev = c
    return " ".join(pieces)


def resegment(text: str, flags: list[bool], lex: set[str], log: list) -> str:
    parts = CHUNK_SPLIT.split(text)
    for n, idx in enumerate(range(0, len(parts), 2)):
        if not flags[n]:
            continue

        def fix(m):
            w = m.group(0)
            if w.lower() in lex:
                return w
            seg = _segment(w, lex)
            if seg:
                log.append(("lexicon-split", w, seg))
            return seg or w

        parts[idx] = re.sub(r"\w+", fix, parts[idx])
    return "".join(parts)


# ---------------------------------------------------------------- pipeline
def decode(text: str, cfg: Config | None = None) -> Result:
    cfg = cfg or Config()
    log: list = []
    out, flags = decode_cipher(text, cfg, log)   # cipher first: the gate leaves plain text alone
    if cfg.lexicon:
        out = resegment(out, flags, cfg.lexicon, log)
    out = dedupe_echoes(out, cfg, log)
    return Result(out, log)


def load_lexicon(path: str) -> set[str]:
    with open(path, encoding="utf-8") as f:
        return {w.strip().lower() for w in f if w.strip()}


# ---------------------------------------------------------------- self-test
def selftest() -> int:
    lex = {"kada", "eisi", "labas", "kaip", "sekasi"}
    cases = [
        # --- Lithuanian syllable cipher -------------------------------------
        ("Lapabapas, kaipaip sepekapasipi?", "Labas, kaip sekasi?", {}),
        ("La pa ba pas, kai pa ip se pe ka pa si pi?", "Labas, kaip sekasi?", {}),
        ("La pa ba pas", "Labas", {}),
        ("Kapadapa eipeisipi?", "Kada eisi?", {}),
        ("Nie kie ka kas", "Niekas", {"consonants": "pk"}),
        ("Niekiekakas", "Niekas", {"consonants": "k"}),
        # --- echo syllables, Lithuanian --------------------------------------
        ("Kada da tu ateisi si?", "Kada tu ateisi?", {}),
        ("Aš ne nekenčiu, aš su suprantu.", "Aš nekenčiu, aš suprantu.", {}),
        ("Iš išmoks.", "Išmoks.", {}),
        # --- echo syllables, English -----------------------------------------
        ("I un understand it.", "I understand it.", {"lang": "en"}),
        ("When en will you?", "When will you?", {"lang": "en"}),
        # --- lexicon re-split --------------------------------------------------
        ("Ka pa da pa ei pei si pi?", "Kadaeisi?", {}),
        ("Ka pa da pa ei pei si pi?", "Kada eisi?", {"lexicon": lex}),
        # --- must stay untouched ----------------------------------------------
        ("Labas, kaip sekasi?", "Labas, kaip sekasi?", {}),
        ("Namas masto.", "Namas masto.", {}),
        ("Lapas krito.", "Lapas krito.", {}),
        ("Taip taip.", "Taip taip.", {}),
        # the case both foundations got wrong: 4-letter repeat is not a ghost
        ("The fast fasting man.", "The fast fasting man.", {"lang": "en"}),
        ("Mano mandagumas.", "Mano mandagumas.", {}),
    ]
    fails = 0
    for src, want, over in cases:
        got = decode(src, Config(**over)).text
        mark = "ok  " if got == want else "FAIL"
        fails += got != want
        print(f"{mark} {src!r:50} -> {got!r}" + ("" if got == want else f"   (want {want!r})"))
    print(f"\n{len(cases) - fails}/{len(cases)} passed")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Decode syllable-insertion ciphers and echo syllables.")
    ap.add_argument("text", nargs="?", help="text to decode (default: stdin)")
    ap.add_argument("-c", "--consonants", default="p", help="cipher consonants to try, e.g. pk (default p)")
    ap.add_argument("--lang", choices=sorted(VOWEL_SETS), default="lt", help="vowel set for the cipher pass (default lt)")
    ap.add_argument("--loose", action="store_true", help="decode echoes even if a chunk isn't fully encoded")
    ap.add_argument("--min-echoes", type=int, default=2)
    ap.add_argument("--min-ghost", type=int, default=2, help="shortest standalone echo to remove (default 2)")
    ap.add_argument("--max-ghost", type=int, default=3, help="longest standalone echo to remove (default 3)")
    ap.add_argument("--no-suffix-echo", action="store_true")
    ap.add_argument("--no-prefix-echo", action="store_true")
    ap.add_argument("--lexicon", help="word-per-line file: re-splits merged words and blocks false echoes")
    ap.add_argument("--explain", action="store_true", help="print every change to stderr")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    text = a.text if a.text is not None else sys.stdin.read()
    cfg = Config(
        consonants=a.consonants, lang=a.lang, strict=not a.loose, min_echoes=a.min_echoes,
        suffix_echo=not a.no_suffix_echo, prefix_echo=not a.no_prefix_echo,
        min_ghost=a.min_ghost, max_ghost=a.max_ghost,
        lexicon=load_lexicon(a.lexicon) if a.lexicon else None,
    )
    res = decode(text, cfg)
    print(res.text, end="" if text.endswith("\n") else "\n")
    if a.explain:
        for rule, before, after in res.log:
            print(f"  [{rule}] {before!r} -> {after!r}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
