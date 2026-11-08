"""Häufigkeitsrang von Verben aus Wortformen-Häufigkeiten (FrequencyWords, CC BY-SA 4.0).

Die Listen zählen Wortformen («vais», «allons»), keine Grundformen. Der Rang
eines Verbs ergibt sich aus der Summe seiner Formen. Gehört eine Form zu
mehreren Verben («suis» → être, suivre), wird ihre Häufigkeit aufgeteilt.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

FREQ_DIR = Path(__file__).resolve().parent.parent / "raw" / "frequency"


def load_counts(lang: str, directory: Path = FREQ_DIR) -> dict[str, int]:
    counts: dict[str, int] = {}
    with (directory / f"{lang}_50k.txt").open(encoding="utf-8") as fh:
        for line in fh:
            word, _, n = line.rstrip("\n").rpartition(" ")
            if word and n.isdigit():
                counts[word.replace("’", "'")] = int(n)
    return counts


def rank(verb_words: dict[str, set[str]], counts: dict[str, int]) -> dict[str, int]:
    """Verb → Rang (1 = häufigstes). Verben ohne Treffer bekommen keinen Rang."""
    owners: dict[str, list[str]] = defaultdict(list)
    for verb, words in verb_words.items():
        for w in words:
            owners[w].append(verb)
    score: dict[str, float] = defaultdict(float)
    for word, verbs in owners.items():
        n = counts.get(word)
        if n:
            for v in verbs:
                score[v] += n / len(verbs)
    ordered = sorted(score, key=lambda v: (-score[v], v))
    return {v: i + 1 for i, v in enumerate(ordered)}
