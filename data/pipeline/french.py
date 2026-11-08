"""Französisch: einfache Zeiten aus Verbiste, zusammengesetzte Zeiten nach Regeln.

Verbiste liefert pro Verb eine Konjugationsvorlage (z. B. «aim:er») mit den
Endungen der einfachen Zeiten. Daraus erzeugt dieses Modul:
- Pronomen inkl. Elision (j', m', qu'il) und aspiriertem h (je hais)
- zusammengesetzte Zeiten mit avoir/être, inkl. Angleichung des Partizips
- Futur proche (aller + Infinitiv)
- reflexive Varianten (se lever)
- Markierung unregelmässiger Formen
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from .model import Form, TenseDef, Verb

VERBISTE_DIR = Path(__file__).resolve().parent.parent / "raw" / "verbiste" / "verbiste-0.1.49" / "data"

PERSONS = ["1s", "2s", "3s", "1p", "2p", "3p"]
IMPERATIVE_PERSONS = ["2s", "1p", "2p"]
PLURAL = {"1p", "2p", "3p"}

TENSES = [
    TenseDef("present", "Indicatif", "Présent", "Präsens", 1),
    TenseDef("passe_compose", "Indicatif", "Passé composé", "Perfekt", 1),
    TenseDef("futur_proche", "Indicatif", "Futur proche", "nahe Zukunft", 1),
    TenseDef("futur_simple", "Indicatif", "Futur simple", "Futur I", 1),
    TenseDef("imparfait", "Indicatif", "Imparfait", "Imperfekt", 2),
    TenseDef("plus_que_parfait", "Indicatif", "Plus-que-parfait", "Plusquamperfekt", 3),
    TenseDef("futur_anterieur", "Indicatif", "Futur antérieur", "Futur II", 3),
    TenseDef("passe_simple", "Indicatif", "Passé simple", "historisches Perfekt", 3, rare=True),
    TenseDef("passe_anterieur", "Indicatif", "Passé antérieur", "Vorvergangenheit (literarisch)", 3, rare=True),
    TenseDef("conditionnel_present", "Conditionnel", "Conditionnel présent", "Konditional I", 2),
    TenseDef("conditionnel_passe", "Conditionnel", "Conditionnel passé", "Konditional II", 3),
    TenseDef("subjonctif_present", "Subjonctif", "Subjonctif présent", "Subjunktiv Präsens", 2),
    TenseDef("subjonctif_passe", "Subjonctif", "Subjonctif passé", "Subjunktiv Perfekt", 3),
    TenseDef("subjonctif_imparfait", "Subjonctif", "Subjonctif imparfait", "Subjunktiv Imperfekt", 3, rare=True),
    TenseDef("subjonctif_plus_que_parfait", "Subjonctif", "Subjonctif plus-que-parfait",
             "Subjunktiv Plusquamperfekt", 3, rare=True),
    TenseDef("imperatif", "Impératif", "Impératif", "Imperativ", 2),
    TenseDef("participe_present", "Formes nominales", "Participe présent", "Partizip Präsens", 3, personal=False),
    TenseDef("participe_passe", "Formes nominales", "Participe passé", "Partizip Perfekt", 3, personal=False),
]

# Pfad in der Verbiste-XML-Vorlage → unser Zeitform-Code
SIMPLE = {
    ("indicative", "present"): "present",
    ("indicative", "imperfect"): "imparfait",
    ("indicative", "future"): "futur_simple",
    ("indicative", "simple-past"): "passe_simple",
    ("conditional", "present"): "conditionnel_present",
    ("subjunctive", "present"): "subjonctif_present",
    ("subjunctive", "imperfect"): "subjonctif_imparfait",
    ("imperative", "imperative-present"): "imperatif",
    ("participle", "present-participle"): "participe_present",
    ("participle", "past-participle"): "participe_passe",
}

# zusammengesetzte Zeit → Zeit des Hilfsverbs
COMPOUND = {
    "passe_compose": "present",
    "plus_que_parfait": "imparfait",
    "passe_anterieur": "passe_simple",
    "futur_anterieur": "futur_simple",
    "conditionnel_passe": "conditionnel_present",
    "subjonctif_passe": "subjonctif_present",
    "subjonctif_plus_que_parfait": "subjonctif_imparfait",
}

SUBJUNCTIVE = {"subjonctif_present", "subjonctif_passe", "subjonctif_imparfait", "subjonctif_plus_que_parfait"}

# Verben, die die zusammengesetzten Zeiten mit être bilden (geschlossene Liste).
ETRE = {
    "aller", "arriver", "advenir", "apparaître", "décéder", "devenir", "échoir", "intervenir",
    "mourir", "naître", "partir", "parvenir", "provenir", "redevenir", "renaître", "repartir",
    "rester", "retomber", "revenir", "survenir", "tomber", "venir",
}
# Verben, die intransitiv être und transitiv avoir verlangen.
BOTH = {
    "descendre", "entrer", "monter", "passer", "redescendre", "remonter", "rentrer",
    "ressortir", "retourner", "sortir",
}

SUBJECT = {"1s": "je", "2s": "tu", "3s": "il/elle", "1p": "nous", "2p": "vous", "3p": "ils/elles"}
SUBJECT_GENDER = {("3s", "m"): "il", ("3s", "f"): "elle", ("3p", "m"): "ils", ("3p", "f"): "elles"}
REFLEXIVE = {"1s": "me", "2s": "te", "3s": "se", "1p": "nous", "2p": "vous", "3p": "se"}
REFLEXIVE_IMPERATIVE = {"2s": "toi", "1p": "nous", "2p": "vous"}

VOWELS = set("aàâäeéèêëiîïoôöuùûüœæ")


@dataclass
class Template:
    name: str
    suffix: str
    # Zeitform → Liste pro Person → Liste der Endungsvarianten (leer = Form existiert nicht)
    endings: dict[str, list[list[str]]]


def parse_templates(path: Path) -> dict[str, Template]:
    root = ET.parse(path).getroot()
    templates = {}
    for t in root.findall("template"):
        name = t.get("name")
        endings = {}
        for (mood, tense), code in SIMPLE.items():
            node = t.find(f"{mood}/{tense}")
            if node is None:
                continue
            endings[code] = [[(i.text or "") for i in p.findall("i")] for p in node.findall("p")]
        templates[name] = Template(name, name.split(":", 1)[1], endings)
    return templates


def parse_verbs(path: Path) -> dict[str, tuple[str, bool]]:
    """Infinitiv → (Vorlage, aspiriertes h)."""
    root = ET.parse(path).getroot()
    return {v.findtext("i"): (v.findtext("t"), v.find("aspirate-h") is not None)
            for v in root.findall("v")}


def starts_with_vowel(word: str, aspirate_h: bool) -> bool:
    if not word:
        return False
    c = word[0].lower()
    return c in VOWELS or (c == "h" and not aspirate_h)


def elide(pronoun: str, following: str, aspirate_h: bool) -> str:
    """«je» + «aime» → «j'» ; gibt das Pronomen mit Leerzeichen oder Apostroph zurück."""
    if pronoun in ("je", "me", "te", "se", "que") and starts_with_vowel(following, aspirate_h):
        return pronoun[:-1] + "'"
    return pronoun + " "


def join(pronoun: str, following: str, aspirate_h: bool) -> str:
    return elide(pronoun, following, aspirate_h) + following


def split_pronoun(text: str) -> tuple[str, str]:
    """«j'aime» → («j'», «aime») ; «il/elle va» → («il/elle», «va»)."""
    if "'" in text.split(" ", 1)[0]:
        head, rest = text.split("'", 1)
        return head + "'", rest
    head, _, rest = text.partition(" ")
    return head, rest


def agree(participle: str, slot: int) -> str:
    """Partizip regelmässig angleichen. slot: 0 m sg, 1 m pl, 2 f sg, 3 f pl."""
    plural_m = participle if participle.endswith(("s", "x")) else participle + "s"
    return [participle, plural_m, participle + "e", participle + "es"][slot]


class Conjugator:
    def __init__(self, templates: dict[str, Template], verbs: dict[str, tuple[str, bool]]):
        self.templates = templates
        self.verbs = verbs
        self._cache: dict[str, Verb] = {}

    @classmethod
    def from_verbiste(cls, directory: Path = VERBISTE_DIR) -> "Conjugator":
        return cls(parse_templates(directory / "conjugation-fr.xml"),
                   parse_verbs(directory / "verbs-fr.xml"))

    # --- einfache Formen ------------------------------------------------------

    def simple(self, infinitive: str, template_name: str | None = None) -> dict[str, list[list[str]]]:
        """Zeitform → pro Person Liste der Formvarianten (ohne Pronomen)."""
        if template_name is None:
            template_name = self.verbs[infinitive][0]
        t = self.templates[template_name]
        if not infinitive.endswith(t.suffix):
            raise ValueError(f"{infinitive} passt nicht zur Vorlage {template_name}")
        stem = infinitive[: len(infinitive) - len(t.suffix)]
        return {code: [[stem + e for e in variants] for variants in per_person]
                for code, per_person in t.endings.items()}

    def group(self, infinitive: str) -> str | None:
        template = self.verbs[infinitive][0]
        if template in (":être", ":avoir"):
            return None
        if template in ("fin:ir", "ha:ïr"):
            return "2"
        if infinitive.endswith("er") and infinitive != "aller":
            return "1"
        return "3"

    def is_irregular(self, infinitive: str, code: str, index: int, form: str) -> bool:
        group = self.group(infinitive)
        if group is None:
            return True
        template = self.verbs[infinitive][0]
        if group == "1" or template == "fin:ir":
            ref_template = "aim:er" if group == "1" else "fin:ir"
            ref = self.simple(infinitive, ref_template).get(code)
            return ref is None or index >= len(ref) or form not in ref[index]
        # 3. Gruppe (und haïr): unregelmässig, wenn der Stamm des Infinitivs nicht erhalten bleibt
        for ending in ("oir", "re", "ir", "ïr", "er"):
            if infinitive.endswith(ending):
                return not form.startswith(infinitive[: -len(ending)])
        return True

    def auxiliary(self, infinitive: str) -> str:
        if infinitive in ETRE:
            return "être"
        if infinitive in BOTH:
            return "both"
        return "avoir"

    # --- ganzes Verb ----------------------------------------------------------

    def verb(self, name: str) -> Verb:
        if name not in self._cache:
            self._cache[name] = self._build(name)
        return self._cache[name]

    def _build(self, name: str) -> Verb:
        reflexive = name.startswith("se ") or name.startswith("s'")
        base = name[3:] if name.startswith("se ") else name[2:] if reflexive else name
        if base not in self.verbs:
            raise KeyError(f"Verb nicht in Verbiste: {base}")
        template_name, aspirate = self.verbs[base]
        simple = self.simple(base)
        verb = Verb(
            lang="fr", infinitive=name, group=self.group(base),
            auxiliary="être" if reflexive else self.auxiliary(base),
            model=template_name.replace(":", ""),
            reflexive_of=base if reflexive else None, source="verbiste",
        )

        def irregular(code: str, idx: int, form: str) -> bool:
            return self.is_irregular(base, code, idx, form)

        def verb_part(person: str, words: str) -> str:
            """Reflexivpronomen vor die Verbform setzen (me lève, m'habille)."""
            return join(REFLEXIVE[person], words, aspirate) if reflexive else words

        def subject(person: str, gender: str | None, code: str, following: str) -> str:
            p = SUBJECT_GENDER.get((person, gender), SUBJECT[person])
            first = following.split(" ")[0]
            # aspiriertes h gilt nur, wenn das folgende Wort eine Form des Verbs selbst ist
            asp = aspirate and not reflexive and code not in COMPOUND and code != "futur_proche"
            if p == "je":
                p = elide("je", first, asp).strip()
            if code in SUBJUNCTIVE:
                p = "/".join(join("que", part, False) for part in p.split("/"))
            return p

        def finite(person: str, gender: str | None, code: str, words: list[str], irr: bool) -> Form:
            main, *alts = [verb_part(person, w) for w in words]
            return Form(person, gender, subject(person, gender, code, main), main, alts, irr)

        # einfache Zeiten
        for code, per_person in simple.items():
            rows: list[Form] = []
            if code == "imperatif":
                for person, variants in zip(IMPERATIVE_PERSONS, per_person):
                    if not variants:
                        continue
                    forms = [f"{v}-{REFLEXIVE_IMPERATIVE[person]}" if reflexive else v for v in variants]
                    rows.append(Form(person, None, "", forms[0], forms[1:],
                                     irregular(code, IMPERATIVE_PERSONS.index(person), variants[0])))
            elif code == "participe_present":
                v = per_person[0]
                if v:
                    rows.append(Form(None, None, "", v[0], v[1:], irregular(code, 0, v[0])))
            elif code == "participe_passe":
                for (num, gen), variants in zip([("sg", "m"), ("pl", "m"), ("sg", "f"), ("pl", "f")], per_person):
                    if variants:
                        rows.append(Form(num, gen, "", variants[0], variants[1:], irregular(code, 0, per_person[0][0])))
            else:
                for idx, (person, variants) in enumerate(zip(PERSONS, per_person)):
                    if variants:
                        rows.append(finite(person, None, code, variants, irregular(code, idx, variants[0])))
            verb.tenses[code] = rows

        existing_persons = [f.person for f in verb.tenses["present"]]
        pp = simple["participe_passe"]  # [m sg, m pl, f sg, f pl]

        # zusammengesetzte Zeiten
        if pp and pp[0]:
            pp_irregular = irregular("participe_passe", 0, pp[0][0])
            avoir, etre = self.simple("avoir"), self.simple("être")
            for code, aux_code in COMPOUND.items():
                rows = []
                for person in existing_persons:
                    idx = PERSONS.index(person)
                    if verb.auxiliary == "avoir":
                        words = [f"{avoir[aux_code][idx][0]} {p}" for p in pp[0]]
                        rows.append(finite(person, None, code, words, pp_irregular))
                        continue
                    for gender in ("m", "f"):
                        slot = {("m", False): 0, ("m", True): 1, ("f", False): 2, ("f", True): 3}[
                            (gender, person in PLURAL)]
                        # fehlt bei Verbiste eine Partizipform (fui → fuie), regelmässig angleichen
                        words = [f"{etre[aux_code][idx][0]} {p}" for p in (pp[slot] or [agree(pp[0][0], slot)])]
                        if verb.auxiliary == "both":
                            words += [f"{avoir[aux_code][idx][0]} {p}" for p in pp[0]]
                        rows.append(finite(person, gender, code, words, pp_irregular))
                verb.tenses[code] = rows

        # Futur proche: aller (Präsens) + Infinitiv
        aller = self.simple("aller")["present"]
        verb.tenses["futur_proche"] = []
        for person in existing_persons:
            inf = join(REFLEXIVE[person], base, aspirate) if reflexive else base
            words = f"{aller[PERSONS.index(person)][0]} {inf}"
            verb.tenses["futur_proche"].append(
                Form(person, None, subject(person, None, "futur_proche", words), words, [], False))
        return verb
