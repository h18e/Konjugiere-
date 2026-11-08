"""Englisch: Stammformen aus dem englischen Wiktionary, Zeiten nach Regeln.

Englische Verben haben nur wenige Formen (go, goes, went, gone, going).
Alle Zeiten werden daraus mit Hilfsverben zusammengesetzt. Geübt werden
vor allem die Stammformen der unregelmässigen Verben.
"""

from __future__ import annotations

import json
from pathlib import Path

from .model import Form, TenseDef, Verb

EXTRACT = Path(__file__).resolve().parent.parent / "raw" / "extract" / "en.jsonl"

PERSONS = ["1s", "2s", "3s", "1p", "2p", "3p"]
SUBJECT = {"1s": "I", "2s": "you", "3s": "he/she/it", "1p": "we", "2p": "you", "3p": "they"}

TENSES = [
    TenseDef("principal_parts", "Stammformen", "Principal parts", "Stammformen", 1, personal=False),
    TenseDef("simple_present", "Present", "Simple present", "Präsens", 1),
    TenseDef("present_progressive", "Present", "Present progressive", "Verlaufsform Präsens", 1),
    TenseDef("present_perfect", "Present", "Present perfect", "Perfekt", 2),
    TenseDef("present_perfect_progressive", "Present", "Present perfect progressive", "Verlaufsform Perfekt", 3),
    TenseDef("simple_past", "Past", "Simple past", "Präteritum", 1),
    TenseDef("past_progressive", "Past", "Past progressive", "Verlaufsform Präteritum", 2),
    TenseDef("past_perfect", "Past", "Past perfect", "Plusquamperfekt", 3),
    TenseDef("past_perfect_progressive", "Past", "Past perfect progressive", "Verlaufsform Plusquamperfekt", 3,
             rare=True),
    TenseDef("will_future", "Future", "Will-future", "Futur I", 1),
    TenseDef("going_to_future", "Future", "Going-to future", "nahe Zukunft", 1),
    TenseDef("future_progressive", "Future", "Future progressive", "Verlaufsform Futur", 3, rare=True),
    TenseDef("future_perfect", "Future", "Future perfect", "Futur II", 3),
    TenseDef("conditional", "Conditional", "Conditional I", "Konditional I", 2),
    TenseDef("conditional_perfect", "Conditional", "Conditional II", "Konditional II", 3),
    TenseDef("imperative", "Imperative", "Imperative", "Imperativ", 2),
]

VARIANT_TAGS = {"UK", "US"}   # gleichwertige Varianten; alles andere (archaisch, Dialekt …) fällt weg

BE_PRESENT = ["am", "are", "is", "are", "are", "are"]
BE_PAST = ["was", "were", "was", "were", "were", "were"]
BE_ENTRY = {"word": "be", "senses": ["To exist."], "forms": [
    ["is", ["present", "singular", "third-person"], ""], ["being", ["participle", "present"], ""],
    ["was", ["past"], ""], ["were", ["past"], ""], ["been", ["participle", "past"], ""]]}


def principal_forms(entry: dict) -> dict[str, list[str]] | None:
    """{'3s': [...], 'past': [...], 'pp': [...], 'ing': [...]} aus den Kopf-Formen."""
    slots: dict[str, list[str]] = {"3s": [], "past": [], "pp": [], "ing": []}
    for form, tags, source in entry["forms"]:
        if source or not form or form == "-":
            continue
        tagset = set(tags)
        extra = tagset - {"present", "singular", "third-person", "participle", "past"}
        if extra - VARIANT_TAGS:
            continue
        if {"present", "singular", "third-person"} <= tagset:
            key = "3s"
        elif "participle" in tagset and "present" in tagset:
            key = "ing"
        elif "participle" in tagset and "past" in tagset:
            key = "pp"
        elif "past" in tagset:
            key = "past"
        else:
            continue
        if form not in slots[key]:
            slots[key].append(form)
    # fehlende Formen aus der Konjugationstabelle ergänzen («spoken» steht nur dort)
    table_tags = {"pp": {"participle", "past"}, "ing": {"participle", "present"},
                  "3s": {"present", "singular", "third-person"}}
    for key, wanted in table_tags.items():
        if not slots[key]:
            slots[key] = [form for form, tags, source in entry["forms"]
                          if source == "conjugation" and set(tags) == wanted][:1]
    if not all(slots.values()):
        return None
    if slots["3s"][0] == entry["word"]:
        return None  # Modalverb (he can) – keine vollständige Konjugation
    return slots


def is_regular(form: str) -> bool:
    return form.endswith("ed")


class Conjugator:
    def __init__(self, entries: dict[str, list[dict]]):
        self.entries = entries

    @classmethod
    def from_extract(cls, path: Path = EXTRACT, only: set[str] | None = None) -> "Conjugator":
        entries: dict[str, list[dict]] = {}
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                e = json.loads(line)
                w = e["word"]
                if " " in w or "-" in w or (only is not None and w not in only):
                    continue
                entries.setdefault(w, []).append(e)
        if only is None or "be" in only:
            # «be» nutzt im Wiktionary eine Sondervorlage ohne Kopf-Formen
            entries["be"] = [BE_ENTRY]
        return cls(entries)

    def words(self) -> list[str]:
        return list(self.entries)

    def verbs(self, word: str) -> list[Verb]:
        """Alle Verben mit dieser Grundform; Homographen mit gleichen Formen werden zusammengelegt."""
        result: list[Verb] = []
        seen: list[tuple] = []
        for entry in self.entries.get(word, []):
            parts = principal_forms(entry)
            if parts is None:
                continue
            key = (parts["past"][0], parts["pp"][0])
            if key in seen:
                continue
            seen.append(key)
            verb = self.build(word, parts)
            verb.model = entry["senses"][0][:80] if entry.get("senses") else None
            result.append(verb)
        if len(result) == 1:
            result[0].model = None    # die englische Erklärung braucht es nur zur Unterscheidung
        return result

    def build(self, base: str, parts: dict[str, list[str]]) -> Verb:
        irregular_verb = not (is_regular(parts["past"][0]) and is_regular(parts["pp"][0]))
        verb = Verb(lang="en", infinitive=base, group="irregular" if irregular_verb else "regular",
                    source="enwiktionary")
        past, pp, ing, s3 = parts["past"], parts["pp"], parts["ing"][0], parts["3s"][0]
        past_irr = not is_regular(past[0])
        pp_irr = not is_regular(pp[0])

        verb.tenses["principal_parts"] = [
            Form("base", None, "", base),
            Form("past", None, "", past[0], past[1:], past_irr),
            Form("pp", None, "", pp[0], pp[1:], pp_irr),
        ]

        def rows(make, irregular=False, alts=None) -> list[Form]:
            return [Form(p, None, SUBJECT[p], make(i, p), (alts(i, p) if alts else []), irregular)
                    for i, p in enumerate(PERSONS)]

        if base == "be":
            present = BE_PRESENT
            simple_past = BE_PAST
        else:
            present = [s3 if p == "3s" else base for p in PERSONS]
            simple_past = [past[0]] * 6
        has = ["have", "have", "has", "have", "have", "have"]

        def pp_alts(prefix: str):
            return lambda i, p: [f"{prefix(i)} {x}" for x in pp[1:]]

        t = verb.tenses
        t["simple_present"] = rows(lambda i, p: present[i], base == "be")
        t["present_progressive"] = rows(lambda i, p: f"{BE_PRESENT[i]} {ing}")
        t["present_perfect"] = rows(lambda i, p: f"{has[i]} {pp[0]}", pp_irr, pp_alts(lambda i: has[i]))
        t["present_perfect_progressive"] = rows(lambda i, p: f"{has[i]} been {ing}")
        t["simple_past"] = rows(lambda i, p: simple_past[i], past_irr or base == "be",
                                (lambda i, p: past[1:]) if base != "be" else None)
        t["past_progressive"] = rows(lambda i, p: f"{BE_PAST[i]} {ing}")
        t["past_perfect"] = rows(lambda i, p: f"had {pp[0]}", pp_irr, pp_alts(lambda i: "had"))
        t["past_perfect_progressive"] = rows(lambda i, p: f"had been {ing}")
        t["will_future"] = rows(lambda i, p: f"will {base}")
        t["going_to_future"] = rows(lambda i, p: f"{BE_PRESENT[i]} going to {base}")
        t["future_progressive"] = rows(lambda i, p: f"will be {ing}")
        t["future_perfect"] = rows(lambda i, p: f"will have {pp[0]}", pp_irr, pp_alts(lambda i: "will have"))
        t["conditional"] = rows(lambda i, p: f"would {base}")
        t["conditional_perfect"] = rows(lambda i, p: f"would have {pp[0]}", pp_irr, pp_alts(lambda i: "would have"))
        t["imperative"] = [Form("2s", None, "", base), Form("1p", None, "", f"let's {base}"),
                           Form("2p", None, "", base)]
        return verb
