"""Sprachunabhängiges Datenmodell der Verbdaten."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TenseDef:
    code: str
    mood: str            # z. B. «Indicatif»
    name_native: str     # z. B. «Passé composé»
    name_de: str         # z. B. «Perfekt»
    level: int           # 1 Einsteiger, 2 Mittel, 3 Fortgeschritten
    rare: bool = False   # in der Tabelle anfangs zugeklappt
    personal: bool = True


@dataclass
class Form:
    person: str | None          # 1s 2s 3s 1p 2p 3p · bei Partizipien sg/pl · sonst None
    gender: str | None          # m / f / None (= gilt für beide)
    pronoun: str                # «je», «j'», «il/elle», «que je», «» (Imperativ)
    form: str                   # «suis allée», «me lève»
    alternatives: list[str] = field(default_factory=list)
    irregular: bool = False


@dataclass
class Verb:
    lang: str
    infinitive: str
    group: str | None = None
    auxiliary: str | None = None     # avoir / être / both · avere / essere / both
    model: str | None = None         # «wird konjugiert wie …»
    reflexive_of: str | None = None  # bei «se lever»: «lever»
    source: str = ""
    tenses: dict[str, list[Form]] = field(default_factory=dict)


def full_answer(f: Form, pronoun: str | None = None) -> str:
    """Pronomen und Form so zusammensetzen, wie sie eingetippt werden."""
    p = f.pronoun if pronoun is None else pronoun
    if not p:
        return f.form
    if p.endswith("'"):
        return p + f.form
    return f"{p} {f.form}"


def normalize(text: str) -> str:
    """Für die Suche: klein, ohne Akzente, typografischer Apostroph vereinheitlicht."""
    text = text.replace("’", "'").lower().strip()
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
