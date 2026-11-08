"""Italienisch: einfache Zeiten aus dem englischen Wiktionary, Rest nach Regeln.

Das englische Wiktionary (Vorlage it-conj) liefert die einfachen Zeiten und
das Hilfsverb. Die Formen tragen Betonungszeichen («vàdo»), die nicht zur
normalen Rechtschreibung gehören; `orthography` entfernt sie.
Zusammengesetzte Zeiten, Angleichung und Unregelmässigkeit erzeugt dieses Modul.
"""

from __future__ import annotations

import json
from pathlib import Path

from .model import Form, TenseDef, Verb

EXTRACT = Path(__file__).resolve().parent.parent / "raw" / "extract" / "it.jsonl"

PERSONS = ["1s", "2s", "3s", "1p", "2p", "3p"]
IMPERATIVE_PERSONS = ["2s", "1p", "2p"]
PLURAL = {"1p", "2p", "3p"}

TENSES = [
    TenseDef("presente", "Indicativo", "Presente", "Präsens", 1),
    TenseDef("passato_prossimo", "Indicativo", "Passato prossimo", "Perfekt", 1),
    TenseDef("futuro_semplice", "Indicativo", "Futuro semplice", "Futur I", 1),
    TenseDef("imperfetto", "Indicativo", "Imperfetto", "Imperfekt", 2),
    TenseDef("trapassato_prossimo", "Indicativo", "Trapassato prossimo", "Plusquamperfekt", 3),
    TenseDef("passato_remoto", "Indicativo", "Passato remoto", "historisches Perfekt", 3),
    TenseDef("futuro_anteriore", "Indicativo", "Futuro anteriore", "Futur II", 3),
    TenseDef("trapassato_remoto", "Indicativo", "Trapassato remoto", "Vorvergangenheit (literarisch)", 3, rare=True),
    TenseDef("condizionale_presente", "Condizionale", "Condizionale presente", "Konditional I", 2),
    TenseDef("condizionale_passato", "Condizionale", "Condizionale passato", "Konditional II", 3),
    TenseDef("congiuntivo_presente", "Congiuntivo", "Congiuntivo presente", "Subjunktiv Präsens", 2),
    TenseDef("congiuntivo_passato", "Congiuntivo", "Congiuntivo passato", "Subjunktiv Perfekt", 3),
    TenseDef("congiuntivo_imperfetto", "Congiuntivo", "Congiuntivo imperfetto", "Subjunktiv Imperfekt", 3),
    TenseDef("congiuntivo_trapassato", "Congiuntivo", "Congiuntivo trapassato", "Subjunktiv Plusquamperfekt", 3,
             rare=True),
    TenseDef("imperativo", "Imperativo", "Imperativo", "Imperativ", 2),
    TenseDef("gerundio", "Forme nominali", "Gerundio", "Gerundium", 3, personal=False),
    TenseDef("participio_presente", "Forme nominali", "Participio presente", "Partizip Präsens", 3,
             rare=True, personal=False),
    TenseDef("participio_passato", "Forme nominali", "Participio passato", "Partizip Perfekt", 3, personal=False),
]

COMPOUND = {
    "passato_prossimo": "presente",
    "trapassato_prossimo": "imperfetto",
    "trapassato_remoto": "passato_remoto",
    "futuro_anteriore": "futuro_semplice",
    "condizionale_passato": "condizionale_presente",
    "congiuntivo_passato": "congiuntivo_presente",
    "congiuntivo_trapassato": "congiuntivo_imperfetto",
}
SUBJUNCTIVE = {"congiuntivo_presente", "congiuntivo_passato", "congiuntivo_imperfetto", "congiuntivo_trapassato"}

SUBJECT = {"1s": "io", "2s": "tu", "3s": "lui/lei", "1p": "noi", "2p": "voi", "3p": "loro"}
SUBJECT_GENDER = {("3s", "m"): "lui", ("3s", "f"): "lei"}
REFLEXIVE = {"1s": "mi", "2s": "ti", "3s": "si", "1p": "ci", "2p": "vi", "3p": "si"}
REFLEXIVE_IMPERATIVE = {"2s": "ti", "1p": "ci", "2p": "vi"}

# Tags, die eine Form genauer bestimmen, aber nicht als Variante kennzeichnen
GRAMMAR_TAGS = {"first-person", "second-person", "third-person", "singular", "plural", "indicative",
                "present", "imperfect", "historic", "past", "future", "conditional", "subjunctive",
                "imperative", "gerund", "participle", "infinitive", "auxiliary"}

ACCENTS = {"à": "a", "è": "e", "é": "e", "ì": "i", "í": "i", "ò": "o", "ó": "o", "ù": "u", "ú": "u"}
VOWELS = set("aeiou") | set(ACCENTS)
KEEP_MONOSYLLABLE = {"è", "dà", "dì"}


def orthography(text: str) -> str:
    """Wie `orthography_word`, für jedes Wort einzeln («se ne và» → «se ne va»)."""
    return " ".join(orthography_word(w) for w in text.split(" "))


def orthography_word(word: str) -> str:
    """Betonungszeichen entfernen; nur die von der Rechtschreibung verlangten bleiben.

    Ein Akzent bleibt, wenn er auf dem letzten Buchstaben eines mehrsilbigen
    Worts steht (andò, poté), bei Einsilbern auf Doppelvokal (può, già)
    sowie bei den Ausnahmen è, dà, dì.
    """
    out = []
    for i, c in enumerate(word):
        if c not in ACCENTS:
            out.append(c)
            continue
        last = i == len(word) - 1
        keep = False
        if last:
            groups = 0
            prev_vowel = False
            for ch in word:
                is_v = ch in VOWELS
                if is_v and not prev_vowel:
                    groups += 1
                prev_vowel = is_v
            keep = groups >= 2 or word in KEEP_MONOSYLLABLE or (i > 0 and word[i - 1] in "iu")
        out.append(c if keep else ACCENTS[c])
    return "".join(out)


def person_of(tags: set[str]) -> str | None:
    for p, label in (("1", "first-person"), ("2", "second-person"), ("3", "third-person")):
        if label in tags:
            if "singular" in tags:
                return p + "s"
            if "plural" in tags:
                return p + "p"
    return None


def tense_of(tags: set[str]) -> str | None:
    if "imperative" in tags:
        return None if {"negative", "formal"} & tags else "imperativo"
    if "gerund" in tags:
        return "gerundio"
    if "participle" in tags:
        return "participio_presente" if "present" in tags else "participio_passato" if "past" in tags else None
    if "conditional" in tags:
        return "condizionale_presente"
    if "subjunctive" in tags:
        return "congiuntivo_presente" if "present" in tags else "congiuntivo_imperfetto" if "imperfect" in tags else None
    if "indicative" in tags:
        if "present" in tags:
            return "presente"
        if "imperfect" in tags:
            return "imperfetto"
        if "historic" in tags:
            return "passato_remoto"
        if "future" in tags:
            return "futuro_semplice"
    return None


# --- regelmässige Konjugation (für die Markierung) -----------------------------

REGULAR = {
    "are": {
        "presente": ["o", "i", "a", "iamo", "ate", "ano"],
        "imperfetto": ["avo", "avi", "ava", "avamo", "avate", "avano"],
        "passato_remoto": ["ai", "asti", "ò", "ammo", "aste", "arono"],
        "futuro_semplice": ["erò", "erai", "erà", "eremo", "erete", "eranno"],
        "condizionale_presente": ["erei", "eresti", "erebbe", "eremmo", "ereste", "erebbero"],
        "congiuntivo_presente": ["i", "i", "i", "iamo", "iate", "ino"],
        "congiuntivo_imperfetto": ["assi", "assi", "asse", "assimo", "aste", "assero"],
        "imperativo": ["a", "iamo", "ate"],
        "gerundio": ["ando"], "participio_presente": ["ante"], "participio_passato": ["ato"],
    },
    "ere": {
        "presente": ["o", "i", "e", "iamo", "ete", "ono"],
        "imperfetto": ["evo", "evi", "eva", "evamo", "evate", "evano"],
        "passato_remoto": ["ei|etti", "esti", "é|ette", "emmo", "este", "erono|ettero"],
        "futuro_semplice": ["erò", "erai", "erà", "eremo", "erete", "eranno"],
        "condizionale_presente": ["erei", "eresti", "erebbe", "eremmo", "ereste", "erebbero"],
        "congiuntivo_presente": ["a", "a", "a", "iamo", "iate", "ano"],
        "congiuntivo_imperfetto": ["essi", "essi", "esse", "essimo", "este", "essero"],
        "imperativo": ["i", "iamo", "ete"],
        "gerundio": ["endo"], "participio_presente": ["ente"], "participio_passato": ["uto"],
    },
    "ire": {
        "presente": ["o|isco", "i|isci", "e|isce", "iamo", "ite", "ono|iscono"],
        "imperfetto": ["ivo", "ivi", "iva", "ivamo", "ivate", "ivano"],
        "passato_remoto": ["ii", "isti", "ì", "immo", "iste", "irono"],
        "futuro_semplice": ["irò", "irai", "irà", "iremo", "irete", "iranno"],
        "condizionale_presente": ["irei", "iresti", "irebbe", "iremmo", "ireste", "irebbero"],
        "congiuntivo_presente": ["a|isca", "a|isca", "a|isca", "iamo", "iate", "ano|iscano"],
        "congiuntivo_imperfetto": ["issi", "issi", "isse", "issimo", "iste", "issero"],
        "imperativo": ["i|isci", "iamo", "ite"],
        "gerundio": ["endo"], "participio_presente": ["ente|iente"], "participio_passato": ["ito"],
    },
}


def regular_forms(infinitive: str, tense: str, index: int) -> set[str]:
    kind = infinitive[-3:]
    if kind not in REGULAR or tense not in REGULAR[kind]:
        return set()
    stem = infinitive[:-3]
    result = set()
    for ending in REGULAR[kind][tense][index].split("|"):
        s = stem
        if kind == "are":
            if s.endswith(("c", "g")) and ending[0] in "ei":
                s += "h"                                    # cerchi, pagherò
            elif s.endswith(("ci", "gi")) and ending[0] in "ei":
                s = s[:-1]                                  # mangi, mangerò
            elif s.endswith("i") and ending[0] == "i":
                result.add(s + ending)                      # invii (betontes i)
                s = s[:-1]                                  # studi
        result.add(s + ending)
    return result


def enclitic(form: str, clitic: str) -> str:
    """«alza» + «ti» → «alzati» ; «va'» + «ti» → «vatti»."""
    if form.endswith("'"):
        return form[:-1] + clitic[0] + clitic
    return form + clitic


def reflexive_table(table: dict[str, dict], auxiliaries: list[str]) -> tuple[dict[str, dict], list[str]]:
    """Tabelle eines Grundverbs in die reflexive Variante umformen."""
    result: dict[str, dict] = {}
    for tense, per_person in table.items():
        new: dict = {}
        for person, forms in per_person.items():
            if tense == "imperativo":
                new[person] = [enclitic(f, REFLEXIVE_IMPERATIVE[person]) for f in forms]
            elif tense == "gerundio":
                new[person] = [f + "si" for f in forms]
            elif person is None:
                new[person] = list(forms)
            else:
                new[person] = [f"{REFLEXIVE[person]} {f}" for f in forms]
        result[tense] = new
    return result, ["essere"]


CLITIC_SUFFIXES = ("sene", "sela", "si")


def reflexive_base(word: str, lemmas: set[str]) -> str | None:
    suffix = next((x for x in CLITIC_SUFFIXES if word.endswith("r" + x)), None)
    if suffix is None:
        return None
    stem = word[: -len(suffix)]                     # «alzar», «por»
    for candidate in (stem + "e", stem[:-1] + "rre"):
        if candidate in lemmas:
            return candidate
    return stem + "e"


class Conjugator:
    def __init__(self, entries: dict[str, dict]):
        self.entries = entries
        self.lemmas = set(entries)
        self._cache: dict[tuple[str, bool], Verb] = {}

    @classmethod
    def from_extract(cls, path: Path = EXTRACT, only: set[str] | None = None) -> "Conjugator":
        entries: dict[str, dict] = {}
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                e = json.loads(line)
                if (only is None or e["word"] in only) and e["word"] not in entries:
                    entries[e["word"]] = e
        return cls(entries)

    def parse(self, entry: dict) -> tuple[dict[str, dict], list[str]]:
        """Zeitform → {Person: [Formen]} und Liste der Hilfsverben (in Reihenfolge)."""
        table: dict[str, dict] = {}
        auxiliaries: list[str] = []
        for form, tags, source in entry["forms"]:
            if source != "conjugation" or not form or form == "-":
                continue
            tagset = set(tags)
            if "auxiliary" in tagset:
                a = orthography(form)
                if a not in auxiliaries:
                    auxiliaries.append(a)
                continue
            if tagset - GRAMMAR_TAGS - {"negative", "formal", "second-person-semantically"}:
                continue                                   # archaisch, literarisch, regional …
            tense = tense_of(tagset)
            if tense is None:
                continue
            person = person_of(tagset) if tense not in ("gerundio", "participio_presente",
                                                        "participio_passato") else None
            slot = table.setdefault(tense, {}).setdefault(person, [])
            clean = orthography(form)
            if clean not in slot:
                slot.append(clean)
        return table, auxiliaries

    def verb(self, word: str, compound: bool = True) -> Verb:
        key = (word, compound)
        if key not in self._cache:
            self._cache[key] = self._build(word, compound)
        return self._cache[key]

    def has(self, word: str) -> bool:
        return word in self.entries or reflexive_base(word, self.lemmas) in self.lemmas

    def _build(self, word: str, compound: bool) -> Verb:
        if word in self.entries:
            table, auxiliaries = self.parse(self.entries[word])
        else:
            # reflexive Variante ohne eigene Tabelle: aus dem Grundverb ableiten
            base_word = reflexive_base(word, self.lemmas)
            if base_word not in self.entries:
                raise KeyError(word)
            table, auxiliaries = reflexive_table(*self.parse(self.entries[base_word]))
        first = table.get("presente", {}).get("1s", [""])[0]
        reflexive = word.endswith(CLITIC_SUFFIXES) and first.startswith(("mi ", "me "))
        base = (reflexive_base(word, self.lemmas) or word) if reflexive else word
        if reflexive:
            aux = "essere"
        elif "avere" in auxiliaries and "essere" in auxiliaries:
            aux = "both"
        elif auxiliaries:
            aux = auxiliaries[0]
        else:
            aux = "avere"
        verb = Verb(lang="it", infinitive=word, group="-" + base[-3:] if base[-3:] in REGULAR else None,
                    auxiliary=aux, reflexive_of=base if reflexive else None, source="enwiktionary")

        def bare(form: str) -> str:
            """Reflexivpronomen für den Regelvergleich abtrennen («mi alzo» → «alzo»)."""
            return form.split(" ", 1)[1] if reflexive and " " in form else form

        def irregular(tense: str, index: int, form: str) -> bool:
            ref = regular_forms(base, tense, index)
            return bool(ref) and bare(form) not in ref if verb.group else True

        def subject(person: str, gender: str | None, tense: str) -> str:
            p = SUBJECT_GENDER.get((person, gender), SUBJECT[person])
            if tense in SUBJUNCTIVE:
                p = "/".join("che " + part for part in p.split("/"))
            return p

        for tense, per_person in table.items():
            rows: list[Form] = []
            if tense == "imperativo":
                for idx, person in enumerate(IMPERATIVE_PERSONS):
                    forms = per_person.get(person)
                    if forms:
                        rows.append(Form(person, None, "", forms[0], forms[1:], irregular(tense, idx, forms[0])))
            elif tense == "participio_passato":
                pp = per_person.get(None, [])
                if pp:
                    main = pp[0]
                    for suffix in CLITIC_SUFFIXES:
                        if reflexive and main.endswith(suffix):
                            main = main[: -len(suffix)]
                            break
                    for num, gen, end in (("sg", "m", "o"), ("sg", "f", "a"), ("pl", "m", "i"), ("pl", "f", "e")):
                        form = main[:-1] + end if main.endswith("o") else main
                        rows.append(Form(num, gen, "", form, [], irregular(tense, 0, main)))
            elif tense in ("gerundio", "participio_presente"):
                forms = per_person.get(None, [])
                if forms:
                    rows.append(Form(None, None, "", forms[0], forms[1:], irregular(tense, 0, bare(forms[0]))))
            else:
                for idx, person in enumerate(PERSONS):
                    forms = per_person.get(person)
                    if forms:
                        rows.append(Form(person, None, subject(person, None, tense), forms[0], forms[1:],
                                         irregular(tense, idx, forms[0])))
            verb.tenses[tense] = rows

        if compound:
            self._compound(verb, reflexive)
        return verb

    def _compound(self, verb: Verb, reflexive: bool) -> None:
        pp_rows = verb.tenses.get("participio_passato")
        if not pp_rows:
            return
        pp = {(f.person, f.gender): f.form for f in pp_rows}
        pp_irregular = pp_rows[0].irregular
        existing = [f.person for f in verb.tenses.get("presente", [])]
        # Klitika vor dem Hilfsverb («mi», «me ne») aus dem Präsens übernehmen
        clitics = {}
        if reflexive:
            for f in verb.tenses.get("presente", []):
                head, _, _ = f.form.rpartition(" ")
                clitics[f.person] = head + " " if head else ""

        def aux_form(name: str, tense: str, person: str) -> str | None:
            if name not in self.entries:
                return None
            for r in self.verb(name, compound=False).tenses.get(tense, []):
                if r.person == person:
                    return r.form
            return None

        primary = "essere" if verb.auxiliary == "essere" else "avere"
        for tense, aux_tense in COMPOUND.items():
            rows: list[Form] = []
            for person in existing:
                refl = clitics.get(person, "")
                number = "pl" if person in PLURAL else "sg"
                if primary == "avere":
                    a = aux_form("avere", aux_tense, person)
                    if a is None:
                        continue
                    alts = []
                    if verb.auxiliary == "both":
                        e = aux_form("essere", aux_tense, person)
                        if e:
                            alts = [f"{e} {pp[(number, g)]}" for g in ("m", "f")]
                    rows.append(Form(person, None, self._subject(person, None, tense),
                                     f"{a} {pp[('sg', 'm')]}", alts, pp_irregular))
                    continue
                e = aux_form("essere", aux_tense, person)
                if e is None:
                    continue
                for gender in ("m", "f"):
                    rows.append(Form(person, gender, self._subject(person, gender, tense),
                                     f"{refl}{e} {pp[(number, gender)]}", [], pp_irregular))
            verb.tenses[tense] = rows

    @staticmethod
    def _subject(person: str, gender: str | None, tense: str) -> str:
        p = SUBJECT_GENDER.get((person, gender), SUBJECT[person])
        if tense in SUBJUNCTIVE:
            p = "/".join("che " + part for part in p.split("/"))
        return p
