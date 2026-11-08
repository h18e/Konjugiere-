"""Kompakter Auszug aus dem gefilterten englischen Wiktionary.

Die Datei raw/enwiktionary/verbs.jsonl ist rund 1 GB gross. Dieser Schritt
zieht nur das Nötige heraus (Grundform, Formen mit Tags, Hilfsverb) und
schreibt es nach raw/extract/. Alle weiteren Schritte lesen nur den Auszug.

Aufruf (aus data/):  python3 -m pipeline.extract
"""

from __future__ import annotations

import json
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "raw"
SOURCE = RAW / "enwiktionary" / "verbs.jsonl"
OUT = RAW / "extract"


def is_lemma(entry: dict) -> bool:
    """Grundform, wenn mindestens eine Bedeutung kein Verweis auf eine andere Form ist."""
    return any(not (s.get("form_of") or "form-of" in (s.get("tags") or [])) for s in entry.get("senses", []))


def compact(entry: dict) -> dict:
    return {
        "word": entry["word"],
        "forms": [[f.get("form", ""), f.get("tags") or [], f.get("source", "")] for f in entry.get("forms", [])],
        "head": [h.get("name") for h in entry.get("head_templates", [])],
        "senses": [(s.get("glosses") or [""])[0] for s in entry.get("senses", [])][:3],
        "sense_tags": [s.get("tags") or [] for s in entry.get("senses", [])],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = {lang: (OUT / f"{lang}.jsonl").open("w", encoding="utf-8") for lang in ("it", "en")}
    fr_reflexive = set()
    counts = {"it": 0, "en": 0}
    with SOURCE.open(encoding="utf-8") as fh:
        for line in fh:
            entry = json.loads(line)
            lang = entry["lang_code"]
            if not is_lemma(entry):
                continue
            word = entry["word"].replace("’", "'")
            if lang == "fr":
                if (word.startswith("se ") or word.startswith("s'")) and " " not in word.split(" ", 1)[-1] \
                        and " " not in word[2:].strip():
                    fr_reflexive.add(word)
                continue
            if lang == "it" and not any(f.get("form") == "it-conj" for f in entry.get("forms", [])):
                continue
            heads = [h.get("name") for h in entry.get("head_templates", [])]
            # «say» und einige andere nutzen statt en-verb die allgemeine Vorlage «head»
            if lang == "en" and "en-verb" not in heads and not ("head" in heads and any(
                    "past" in (f.get("tags") or []) for f in entry.get("forms", []))):
                continue
            files[lang].write(json.dumps(compact(entry), ensure_ascii=False) + "\n")
            counts[lang] += 1
    for f in files.values():
        f.close()
    (OUT / "fr_reflexive.txt").write_text("\n".join(sorted(fr_reflexive)) + "\n", encoding="utf-8")
    print(f"extract: it {counts['it']}, en {counts['en']}, fr reflexiv {len(fr_reflexive)}")


if __name__ == "__main__":
    main()
