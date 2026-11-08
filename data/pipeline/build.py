"""Alle Quellen zusammenführen und die App-Datenbank konjugiere.sqlite erzeugen.

Aufruf (aus data/):  python3 -m pipeline.build
Ergebnis:            data/build/konjugiere.sqlite und docs/DATENQUALITAET.md
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import zlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from . import english, french, frequency, glosses, italian
from .model import Form, TenseDef, Verb, normalize
from .packages import PACKAGES

DATA = Path(__file__).resolve().parent.parent
BUILD = DATA / "build"
DB_PATH = BUILD / "konjugiere.sqlite"
CORRECTIONS = DATA / "corrections" / "corrections.tsv"
GLOSS_CORRECTIONS = DATA / "corrections" / "glosses.tsv"
SCHEMA_VERSION = 2

LANGUAGES = {
    "fr": ("Französisch", "Verbiste 0.1.49 (Pierre Sarrazin); Bedeutungen: deutsches Wiktionary",
           "GPL v2+ (Konjugationen), CC BY-SA 4.0 (Bedeutungen)",
           "Konjugationen: Verbiste, © Pierre Sarrazin, GPL. Bedeutungen: Wiktionary-Autoren, CC BY-SA, "
           "aufbereitet mit Wiktextract (kaikki.org). Häufigkeit: FrequencyWords (Hermit Dave), CC BY-SA 4.0."),
    "it": ("Italienisch", "englisches Wiktionary; Bedeutungen: deutsches Wiktionary", "CC BY-SA 4.0",
           "Wiktionary-Autoren, CC BY-SA, aufbereitet mit Wiktextract (kaikki.org). "
           "Häufigkeit: FrequencyWords (Hermit Dave), CC BY-SA 4.0."),
    "en": ("Englisch", "englisches Wiktionary; Bedeutungen: deutsches Wiktionary", "CC BY-SA 4.0",
           "Wiktionary-Autoren, CC BY-SA, aufbereitet mit Wiktextract (kaikki.org). "
           "Häufigkeit: FrequencyWords (Hermit Dave), CC BY-SA 4.0."),
}

TENSES: dict[str, list[TenseDef]] = {"fr": french.TENSES, "it": italian.TENSES, "en": english.TENSES}

# Formen, die für den Häufigkeitsrang zählen. Formen, die oft gleich wie Nomen
# oder Pronomen geschrieben werden (il monde, tu, lui), bleiben draussen.
FREQ_TENSES = {
    "fr": {"imparfait", "futur_simple", "conditionnel_present"},
    "it": {"imperfetto", "futuro_semplice", "condizionale_presente"},
    "en": {"principal_parts", "simple_present", "present_progressive"},
}
FREQ_PERSONS_PRESENT = {"1p", "2p"}

REFLEXIVE_TOKENS = {"me", "te", "se", "nous", "vous", "m'", "t'", "s'", "mi", "ti", "si", "ci", "vi",
                    "me ne", "te ne", "se ne", "ce ne", "ve ne"}


@dataclass
class Entry:
    verb: Verb
    rank: int | None = None
    gloss: str = ""
    gloss_terms: list[str] | None = None


# --- Sammeln ------------------------------------------------------------------

def french_verbs(gl: glosses.GlossIndex) -> list[Verb]:
    conj = french.Conjugator.from_verbiste()
    names = set(conj.verbs)
    candidates = set()
    path = DATA / "raw" / "extract" / "fr_reflexive.txt"
    if path.exists():
        candidates |= {l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()}
    candidates |= {w for (lang, w) in gl.candidates if lang == "fr"}
    candidates |= {w for p in PACKAGES["fr"] for w in split_verbs(p[3])}
    for c in candidates:
        if c.startswith("se ") and " " not in c[3:] and c[3:] in names:
            if not french.starts_with_vowel(c[3:], conj.verbs[c[3:]][1]):
                names.add(c)
        elif c.startswith("s'") and " " not in c[2:] and c[2:] in names:
            names.add(c)
    return [conj.verb(n) for n in sorted(names)]


def italian_verbs(gl: glosses.GlossIndex) -> list[Verb]:
    conj = italian.Conjugator.from_extract()
    names = set(conj.entries)
    extra = {w for (lang, w) in gl.candidates if lang == "it" and w.endswith("rsi") and " " not in w}
    extra |= {w for p in PACKAGES["it"] for w in split_verbs(p[3]) if w.endswith("rsi")}
    names |= {w for w in extra if conj.has(w)}
    result = []
    for n in sorted(names):
        try:
            result.append(conj.verb(n))
        except KeyError:
            pass
    return result


def load_manual_glosses(path: Path = GLOSS_CORRECTIONS) -> dict[tuple[str, str], str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        rows = csv.DictReader((l for l in fh if not l.startswith("#")), delimiter="\t")
        return {(r["lang"], r["infinitive"]): r["gloss"] for r in rows}


def italian_archaic() -> set[str]:
    """Italienische Verben, deren Bedeutungen alle als veraltet o. Ä. markiert sind."""
    result = set()
    with (DATA / "raw" / "extract" / "it.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            e = json.loads(line)
            tags = e.get("sense_tags") or []
            if tags and all(set(t) & ARCHAIC_TAGS for t in tags):
                result.add(e["word"])
    return result


def english_verbs(gl: glosses.GlossIndex, counts: dict[str, int]) -> list[Verb]:
    conj = english.Conjugator.from_extract()
    # Wiktionary führt auch scherzhafte Verben («to you», «to and»). Aufgenommen wird nur,
    # was das deutsche Wiktionary als englisches Verb kennt.
    keep = {w for w in conj.words() if w.isalpha() and w.islower() and ("en", w) in gl.candidates
            and w not in ENGLISH_MODALS}
    result = []
    for w in sorted(keep):
        result.extend(conj.verbs(w))
    return result


def split_verbs(text: str) -> list[str]:
    """«se lever s'habiller parler» → ['se lever', "s'habiller", 'parler']"""
    words, out = text.split(), []
    i = 0
    while i < len(words):
        if words[i] == "se" and i + 1 < len(words):
            out.append(f"se {words[i + 1]}")
            i += 2
        else:
            out.append(words[i])
            i += 1
    return out


# --- Korrekturen ----------------------------------------------------------------

def apply_corrections(verbs: dict[tuple[str, str], list[Verb]], path: Path = CORRECTIONS) -> int:
    if not path.exists():
        return 0
    n = 0
    with path.open(encoding="utf-8") as fh:
        for rec in csv.DictReader((l for l in fh if not l.startswith("#")), delimiter="\t"):
            for verb in verbs.get((rec["lang"], rec["infinitive"]), []):
                rows = verb.tenses.setdefault(rec["tense"], [])
                person = rec["person"] or None
                gender = rec["gender"] or None
                match = [r for r in rows if r.person == person and r.gender == gender]
                if rec["form"] == "-":
                    for r in match:
                        rows.remove(r)
                elif match:
                    match[0].form = rec["form"]
                    match[0].alternatives = [a for a in rec.get("alternatives", "").split("|") if a]
                else:
                    rows.append(Form(person, gender, rec.get("pronoun", ""), rec["form"],
                                     [a for a in rec.get("alternatives", "").split("|") if a]))
                n += 1
    return n


# --- Datenbank ------------------------------------------------------------------

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE language (code TEXT PRIMARY KEY, name TEXT NOT NULL, source TEXT NOT NULL,
                       license TEXT NOT NULL, attribution TEXT NOT NULL);
CREATE TABLE tense (lang TEXT NOT NULL, code TEXT NOT NULL, mood TEXT NOT NULL, name_native TEXT NOT NULL,
                    name_de TEXT NOT NULL, sort INTEGER NOT NULL, level INTEGER NOT NULL,
                    rare INTEGER NOT NULL, personal INTEGER NOT NULL, PRIMARY KEY (lang, code));
-- verb_key: bleibt über Neuaufbauten gleich (Lernfortschritt hängt daran). Meist der Infinitiv,
-- bei gleich geschriebenen englischen Verben mit Stammformen: «lie~lay~lain», «lie~lied~lied».
CREATE TABLE verb (id INTEGER PRIMARY KEY, lang TEXT NOT NULL, verb_key TEXT NOT NULL, infinitive TEXT NOT NULL,
                   infinitive_norm TEXT NOT NULL, verb_group TEXT, auxiliary TEXT, model TEXT,
                   reflexive_of TEXT, freq_rank INTEGER, gloss_de TEXT NOT NULL, note TEXT,
                   has_irregular INTEGER NOT NULL, source TEXT NOT NULL);
CREATE INDEX verb_lang_inf ON verb (lang, infinitive_norm);
CREATE UNIQUE INDEX verb_lang_key ON verb (lang, verb_key);
CREATE INDEX verb_lang_model ON verb (lang, model);
CREATE INDEX verb_lang_rank ON verb (lang, freq_rank);
-- data: JSON, komprimiert mit DEFLATE (roh, RFC 1951)
-- {"tense_code": [[person, gender, pronoun, form, [alternatives], irregular], ...], ...}
CREATE TABLE verb_table (verb_id INTEGER PRIMARY KEY REFERENCES verb (id), data BLOB NOT NULL);
-- kind: 0 = Infinitiv, 1 = konjugierte Form, 2 = deutsche Bedeutung
CREATE TABLE search (lang TEXT NOT NULL, term TEXT NOT NULL, verb_id INTEGER NOT NULL REFERENCES verb (id),
                     kind INTEGER NOT NULL, PRIMARY KEY (lang, term, verb_id, kind)) WITHOUT ROWID;
CREATE TABLE package (id INTEGER PRIMARY KEY, lang TEXT NOT NULL, title TEXT NOT NULL,
                      description TEXT NOT NULL, level INTEGER NOT NULL, sort INTEGER NOT NULL,
                      tenses TEXT);
CREATE TABLE package_verb (package_id INTEGER NOT NULL REFERENCES package (id),
                           verb_id INTEGER NOT NULL REFERENCES verb (id), sort INTEGER NOT NULL);
"""


def deflate(data: bytes) -> bytes:
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    return c.compress(data) + c.flush()


def table_json(verb: Verb, order: list[str]) -> bytes:
    data = {code: [[f.person, f.gender, f.pronoun, f.form, f.alternatives, int(f.irregular)]
                   for f in verb.tenses[code]]
            for code in order if verb.tenses.get(code)}
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def search_terms(verb: Verb) -> set[str]:
    """Einzelwörter der einfachen Formen, ohne Pronomen («suis», «vado», «went»)."""
    terms = set()
    compound = set(french.COMPOUND) | set(italian.COMPOUND) | {"futur_proche"}
    for code, rows in verb.tenses.items():
        if code in compound or (verb.lang == "en" and code not in ("principal_parts", "simple_present")):
            continue
        for f in rows:
            for form in [f.form, *f.alternatives]:
                for token in form.replace("-", " ").split(" "):
                    token = token.strip()
                    if "'" in token:
                        token = token.split("'", 1)[1]
                    if token and token not in REFLEXIVE_TOKENS:
                        terms.add(normalize(token))
    return terms


def freq_words(verb: Verb) -> set[str]:
    """Formen, deren Häufigkeit für den Rang zählt.

    Weggelassen werden Formen, die oft gleich geschrieben werden wie häufige
    andere Wörter: Präsens Singular (il monde, la voiture), Partizipien (tu, lui,
    maintenant), Passé simple (plus) – und im Englischen die Grundform (back, right).
    """
    words = set() if verb.lang == "en" else {verb.infinitive}
    for code, rows in verb.tenses.items():
        if code in FREQ_TENSES[verb.lang] or code in ("present", "presente"):
            for f in rows:
                if code in ("present", "presente") and f.person not in FREQ_PERSONS_PRESENT:
                    continue
                if code == "principal_parts" and f.person == "base":
                    continue
                words.update([f.form, *f.alternatives])
    if verb.lang == "en":
        words.discard(verb.infinitive)
    return {w for w in words if " " not in w}


ENGLISH_MODALS = {"can", "could", "may", "might", "must", "shall", "should", "will", "would", "ought"}
ARCHAIC_TAGS = {"archaic", "obsolete", "poetic", "literary", "dialectal", "regional"}
ITALIAN_IDIOM_SUFFIXES = ("ci", "la", "ne", "vi", "cela", "sela", "sene")


def unranked(verb: Verb, archaic: set[str]) -> bool:
    """Verben, die zwar nachschlagbar sind, aber nicht nach vorne sortiert werden sollen."""
    if verb.infinitive in archaic:
        return True
    return verb.lang == "it" and verb.infinitive.endswith(ITALIAN_IDIOM_SUFFIXES) and not verb.infinitive.endswith("rsi")



def build() -> dict:
    BUILD.mkdir(parents=True, exist_ok=True)
    de_counts = frequency.load_counts("de")
    gl = glosses.load(de_counts=de_counts)
    counts = {lang: frequency.load_counts(lang) for lang in ("fr", "it", "en")}

    print("Französisch …", flush=True)
    all_verbs: dict[str, list[Verb]] = {"fr": french_verbs(gl)}
    print("Italienisch …", flush=True)
    all_verbs["it"] = italian_verbs(gl)
    print("Englisch …", flush=True)
    all_verbs["en"] = english_verbs(gl, counts["en"])

    by_key: dict[tuple[str, str], list[Verb]] = {}
    for lang, verbs in all_verbs.items():
        for v in verbs:
            by_key.setdefault((lang, v.infinitive), []).append(v)
    n_corr = apply_corrections(by_key)

    manual = load_manual_glosses()
    archaic = italian_archaic()
    entries: dict[str, list[Entry]] = {}
    for lang, verbs in all_verbs.items():
        ranks = frequency.rank({v.infinitive: freq_words(v) for v in verbs if not unranked(v, archaic)},
                               counts[lang])
        entries[lang] = []
        for v in verbs:
            gloss = manual.get((lang, v.infinitive)) or gl.short(lang, v.infinitive)
            terms = gl.terms(lang, v.infinitive)
            if (lang, v.infinitive) in manual:
                terms = [t.strip() for t in re.split(r"[,;]", gloss) if t.strip()] + terms
            entries[lang].append(Entry(v, ranks.get(v.infinitive), gloss, terms))

    if DB_PATH.exists():
        DB_PATH.unlink()
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA)
    db.executemany("INSERT INTO meta VALUES (?, ?)", [
        ("schema_version", str(SCHEMA_VERSION)), ("built", date.today().isoformat())])
    for code, (name, source, lic, attr) in LANGUAGES.items():
        db.execute("INSERT INTO language VALUES (?, ?, ?, ?, ?)", (code, name, source, lic, attr))
    for lang, tenses in TENSES.items():
        for i, t in enumerate(tenses):
            db.execute("INSERT INTO tense VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (lang, t.code, t.mood, t.name_native, t.name_de, i, t.level, int(t.rare), int(t.personal)))

    ids: dict[tuple[str, str], list[int]] = {}
    next_id = 1
    for lang, items in entries.items():
        order = [t.code for t in TENSES[lang]]
        items.sort(key=lambda e: (e.rank or 10**9, e.verb.infinitive))
        for e in items:
            v = e.verb
            has_irr = any(f.irregular for rows in v.tenses.values() for f in rows)
            key = v.infinitive
            if len(by_key[(lang, v.infinitive)]) > 1:
                parts = {f.person: f.form for f in v.tenses.get("principal_parts", [])}
                key = f"{v.infinitive}~{parts.get('past', next_id)}~{parts.get('pp', '')}"
            db.execute("INSERT INTO verb VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (next_id, lang, key, v.infinitive, normalize(v.infinitive), v.group, v.auxiliary,
                        v.model if lang == "fr" else None, v.reflexive_of, e.rank, e.gloss,
                        v.model if lang == "en" else None, int(has_irr), v.source))
            db.execute("INSERT INTO verb_table VALUES (?, ?)", (next_id, deflate(table_json(v, order))))
            rows = [(lang, normalize(v.infinitive), next_id, 0)]
            rows += [(lang, t, next_id, 1) for t in search_terms(v) if t != normalize(v.infinitive)]
            rows += [(lang, normalize(t), next_id, 2) for t in (e.gloss_terms or [])]
            db.executemany("INSERT OR IGNORE INTO search VALUES (?, ?, ?, ?)", rows)
            ids.setdefault((lang, v.infinitive), []).append(next_id)
            next_id += 1

    missing_package_verbs = []
    pid = 1
    for lang, packages in PACKAGES.items():
        for sort, (title, desc, level, verbs, tenses) in enumerate(packages):
            db.execute("INSERT INTO package VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (pid, lang, title, desc, level, sort, json.dumps(tenses) if tenses else None))
            for i, name in enumerate(split_verbs(verbs)):
                if (lang, name) in ids:
                    db.execute("INSERT INTO package_verb VALUES (?, ?, ?)", (pid, ids[(lang, name)][0], i))
                else:
                    missing_package_verbs.append((lang, title, name))
            pid += 1
    db.commit()
    db.execute("VACUUM")
    db.close()

    return {"entries": entries, "missing_package_verbs": missing_package_verbs, "corrections": n_corr}


if __name__ == "__main__":
    from .report import write_report
    result = build()
    write_report(result, DB_PATH)
