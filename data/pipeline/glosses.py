"""Deutsche Bedeutungen aus dem deutschen Wiktionary (Wiktextract) aufbereiten.

Zwei Wege werden kombiniert:
1. direkt: Bedeutungsangaben und Übersetzungen beim fremdsprachigen Eintrag
   («suivre» → «folgen»). Oft sind das aber Umschreibungen statt Übersetzungen.
2. rückwärts: Übersetzungstabellen der deutschen Verben («gehen» → aller).

Jede deutsche Übersetzung bekommt Punkte; die besten drei werden angezeigt,
alle dienen der Suche.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

DE_VERBS = Path(__file__).resolve().parent.parent / "raw" / "dewiktionary" / "verbs.jsonl"

MAX_WORDS = 3  # längere Ausdrücke sind Erklärungen, keine Übersetzungen
LANGS = ("fr", "it", "en")


LABELS = {"auch", "etwas", "sich", "transitiv", "intransitiv", "reflexiv", "umgangssprachlich", "übertragen",
          "figurativ", "veraltet", "selten"}


def split_outside_parentheses(text: str, separators: str) -> list[str]:
    parts, depth, current = [], 0, []
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if ch in separators and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    parts.append("".join(current))
    return parts


def clean_gloss(text: str) -> list[str]:
    """Eine Bedeutungsangabe in kurze Übersetzungen zerlegen.

    Eine Angabe besteht aus Abschnitten (getrennt durch ; oder :), diese aus
    Teilen (getrennt durch Kommas). Ein Abschnitt zählt nur als Übersetzungsliste,
    wenn alle Teile kurz sind; sonst ist er eine Erklärung und fällt ganz weg.
    """
    text = re.sub(r"^\s*\[[^\]]*\]\s*", "", text)   # «[1] …»
    text = re.sub(r"\s+", " ", text.replace("…", "").replace("\u00a0", " "))
    terms = []
    for segment in split_outside_parentheses(text, ";:"):
        parts = [p.strip(" .") for p in split_outside_parentheses(segment, ",")]
        parts = [p for p in parts if p and p not in LABELS]
        if not parts or any(len(re.sub(r"\([^)]*\)", "", p).split()) > MAX_WORDS for p in parts):
            continue
        for part in parts:
            words = re.sub(r"\([^)]*\)", "", part).split()
            # deutsche Verben werden klein geschrieben; Grossgeschriebenes ist Erklärung
            if words and words[-1][0].islower():
                terms.append(part)
    return terms


def dedupe_key(term: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", term).strip()


def entry_glosses(entry: dict) -> list[list[str]]:
    """Pro Bedeutung die Liste der kurzen Übersetzungen."""
    if "form-of" in (entry.get("tags") or []):
        return []
    result = []
    for sense in entry.get("senses", []):
        if "form-of" in (sense.get("tags") or []):
            continue
        terms = [t for g in sense.get("glosses", []) for t in clean_gloss(g)]
        if terms:
            result.append(terms)
    return result


def first_sense(index: str | None) -> bool:
    return bool(index) and re.match(r"^1(\D|$)", index) is not None


@dataclass
class Candidates:
    scores: dict[str, float] = field(default_factory=lambda: defaultdict(float))

    def add(self, term: str, points: float) -> None:
        self.scores[term] += points

    def ranked(self, de_rank: dict[str, int] | None = None) -> list[str]:
        de_rank = de_rank or {}
        order = {t: i for i, t in enumerate(self.scores)}   # Reihenfolge im Wiktionary
        return sorted(self.scores, key=lambda t: (-self.scores[t], order[t]))


class GlossIndex:
    def __init__(self) -> None:
        self.candidates: dict[tuple[str, str], Candidates] = defaultdict(Candidates)
        self.de_rank: dict[str, int] = {}

    # --- Aufbau -------------------------------------------------------------

    def add_entry(self, entry: dict) -> None:
        lang = entry.get("lang_code")
        if "form-of" in (entry.get("tags") or []):
            return
        if lang == "de":
            self._add_reverse(entry)
        elif lang in LANGS:
            self._add_direct(entry)

    def _add_direct(self, entry: dict) -> None:
        key = (entry["lang_code"], entry["word"].replace("’", "'"))
        for i, terms in enumerate(entry_glosses(entry)):
            for t in terms:
                self.candidates[key].add(t, 4 if i == 0 else 2)
        for tr in entry.get("translations") or []:
            if tr.get("lang_code") == "de" and tr.get("word"):
                for term in clean_gloss(tr["word"]):
                    self.candidates[key].add(term, 4 if first_sense(tr.get("sense_index")) else 2)

    def _add_reverse(self, entry: dict) -> None:
        german = entry["word"]
        seen: set[tuple[str, str, str]] = set()
        for tr in entry.get("translations") or []:
            lang, word = tr.get("lang_code"), (tr.get("word") or "").replace("’", "'")
            if lang not in LANGS or not word:
                continue
            index = tr.get("sense_index") or ""
            if (lang, word, index) in seen:
                continue
            seen.add((lang, word, index))
            # jede Bedeutung des deutschen Verbs zählt einmal, Bedeutung 1 doppelt
            self.candidates[(lang, word)].add(german, 2 if first_sense(index) else 1)

    # --- Abfrage ------------------------------------------------------------

    def terms(self, lang: str, word: str) -> list[str]:
        c = self.candidates.get((lang, word))
        return c.ranked(self.de_rank) if c else []

    def short(self, lang: str, word: str, limit: int = 3) -> str:
        c = self.candidates.get((lang, word))
        if not c:
            return ""
        best, seen = [], set()
        for t in c.ranked(self.de_rank):
            if c.scores[t] >= 2 and dedupe_key(t) not in seen:
                seen.add(dedupe_key(t))
                best.append(t)
        return ", ".join(best[:limit])


def load(path: Path = DE_VERBS, de_counts: dict[str, int] | None = None) -> GlossIndex:
    index = GlossIndex()
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            index.add_entry(json.loads(line))
    if de_counts:
        ordered = sorted(de_counts, key=lambda w: -de_counts[w])
        index.de_rank = {w: i for i, w in enumerate(ordered)}
    return index
