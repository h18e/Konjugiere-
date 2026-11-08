"""Qualitätsbericht docs/DATENQUALITAET.md nach jedem Build."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .build import TENSES
from .model import full_answer

REPORT = Path(__file__).resolve().parent.parent.parent / "docs" / "DATENQUALITAET.md"
NAMES = {"fr": "Französisch", "it": "Italienisch", "en": "Englisch"}
SAMPLES = {"fr": [("être", "present"), ("aller", "passe_compose"), ("se lever", "present")],
           "it": [("essere", "presente"), ("andare", "passato_prossimo"), ("alzarsi", "presente")],
           "en": [("go", "principal_parts"), ("be", "simple_present"), ("go", "present_perfect")]}


def pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.0f} %)" if b else "–"


def complete(verb, lang) -> bool:
    """Hat das Verb alle gängigen (nicht seltenen) Zeitformen mit allen Personen?"""
    for t in TENSES[lang]:
        if t.rare or not t.personal or t.code in ("imperatif", "imperativo", "imperative"):
            continue
        persons = {f.person for f in verb.tenses.get(t.code, [])}
        if len(persons) < 6:
            return False
    return True


def write_report(result: dict, db_path: Path) -> None:
    entries = result["entries"]
    size_mb = db_path.stat().st_size / 1e6
    lines = [
        "# Datenqualität", "",
        f"Automatisch erzeugt von `python3 -m pipeline.build` am {date.today().isoformat()}.", "",
        f"Datenbank: `data/build/konjugiere.sqlite`, **{size_mb:.1f} MB**. "
        f"Angewendete Korrekturen: {result['corrections']}.", "",
        "## Überblick", "",
        "| | Verben | Formen | mit Häufigkeitsrang | mit DE-Bedeutung | DE-Bedeutung Top 100 | DE-Bedeutung Top 500 "
        "| Top 500 vollständig |",
        "|---|---|---|---|---|---|---|---|",
    ]
    details = []
    for lang, items in entries.items():
        n = len(items)
        forms = sum(len(r) for e in items for r in e.verb.tenses.values())
        ranked = sorted((e for e in items if e.rank), key=lambda e: e.rank)
        top100, top500 = ranked[:100], ranked[:500]
        glossed = sum(1 for e in items if e.gloss)
        lines.append(
            f"| {NAMES[lang]} | {n:,} | {forms:,} | {len(ranked):,} | {pct(glossed, n)} "
            f"| {pct(sum(1 for e in top100 if e.gloss), len(top100))} "
            f"| {pct(sum(1 for e in top500 if e.gloss), len(top500))} "
            f"| {pct(sum(1 for e in top500 if complete(e.verb, lang)), len(top500))} |".replace(",", "'"))

        details += [f"## {NAMES[lang]}", "", "### Die 40 häufigsten Verben", "",
                    "| Rang | Verb | Bedeutung | Gruppe | Hilfsverb |", "|---|---|---|---|---|"]
        for e in ranked[:40]:
            v = e.verb
            details.append(f"| {e.rank} | {v.infinitive} | {e.gloss or '–'} | {v.group or '–'} | {v.auxiliary or '–'} |")
        no_gloss = [e.verb.infinitive for e in top500 if not e.gloss]
        details += ["", f"### Top 500 ohne deutsche Bedeutung ({len(no_gloss)})", "",
                    ", ".join(no_gloss) or "keine", ""]
        incomplete = [e.verb.infinitive for e in top500 if not complete(e.verb, lang)]
        details += [f"### Top 500 mit unvollständigen Zeitformen ({len(incomplete)})", "",
                    "Meist unpersönliche Verben (es regnet) oder Verben ohne Partizip.", "",
                    ", ".join(incomplete) or "keine", ""]
        missing = [m[2] for m in result["missing_package_verbs"] if m[0] == lang]
        details += [f"### Verben aus Lernpaketen, die fehlen ({len(missing)})", "", ", ".join(missing) or "keine", ""]
        details += ["### Stichproben", ""]
        by_name = {e.verb.infinitive: e.verb for e in items}
        for name, tense in SAMPLES[lang]:
            v = by_name.get(name)
            if v is None:
                details.append(f"- **{name}** fehlt!")
                continue
            forms = [full_answer(f) + (" ⚠︎" if f.irregular else "") for f in v.tenses.get(tense, [])]
            details.append(f"- **{name}**, {tense}: " + " · ".join(forms))
        details.append("")
    lines += ["", "«vollständig» = alle gängigen Zeitformen (ohne seltene und ohne Imperativ) mit allen sechs Personen.",
              "⚠︎ = als unregelmässig markiert.", ""] + details
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Bericht: {REPORT}")
