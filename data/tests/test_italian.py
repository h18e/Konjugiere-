"""Tests für Italienisch (englisches Wiktionary + eigene Regeln).

Voraussetzung: `python3 -m pipeline.extract` wurde ausgeführt.
"""

import pytest

from pipeline import italian
from pipeline.model import full_answer


@pytest.fixture(scope="module")
def it():
    return italian.Conjugator.from_extract(only={
        "andare", "essere", "avere", "fare", "parlare", "cercare", "mangiare", "studiare", "finire",
        "dormire", "credere", "pentirsi", "alzarsi", "potere", "dare", "correre", "venire", "dire",
        "prendere", "lavarsi", "alzare", "lavare", "andarsene"})


def row(verb, tense, person=None, gender=None):
    rows = [f for f in verb.tenses[tense] if f.person == person and f.gender == gender]
    assert len(rows) == 1, f"{tense} {person} {gender}: {rows}"
    return rows[0]


def answer(verb, tense, person=None, gender=None):
    return full_answer(row(verb, tense, person, gender))


@pytest.mark.parametrize("raw,clean", [
    ("vàdo", "vado"), ("andàre", "andare"), ("andò", "andò"), ("è", "è"), ("dà", "dà"),
    ("và", "va"), ("fà", "fa"), ("hò", "ho"), ("sèi", "sei"), ("andrèbbe", "andrebbe"),
    ("poté", "poté"), ("può", "può"), ("và'", "va'"), ("andrài", "andrai"), ("siéte", "siete"),
])
def test_stress_marks_are_removed(raw, clean):
    assert italian.orthography(raw) == clean


def test_present(it):
    v = it.verb("andare")
    assert [answer(v, "presente", p) for p in ("1s", "2s", "3s", "1p", "2p", "3p")] == [
        "io vado", "tu vai", "lui/lei va", "noi andiamo", "voi andate", "loro vanno"]


def test_essere_and_avere(it):
    assert answer(it.verb("essere"), "presente", "3s") == "lui/lei è"
    assert answer(it.verb("avere"), "presente", "1s") == "io ho"
    assert answer(it.verb("essere"), "passato_remoto", "3s") == "lui/lei fu"


def test_subjunctive_has_che(it):
    assert answer(it.verb("essere"), "congiuntivo_presente", "1s") == "che io sia"


def test_passato_prossimo_with_avere(it):
    v = it.verb("parlare")
    assert v.auxiliary == "avere"
    assert answer(v, "passato_prossimo", "1s") == "io ho parlato"
    assert answer(v, "passato_prossimo", "3p") == "loro hanno parlato"


def test_passato_prossimo_with_essere_agrees(it):
    v = it.verb("andare")
    assert v.auxiliary == "essere"
    assert answer(v, "passato_prossimo", "1s", "f") == "io sono andata"
    assert answer(v, "passato_prossimo", "3s", "m") == "lui è andato"
    assert answer(v, "passato_prossimo", "3s", "f") == "lei è andata"
    assert answer(v, "passato_prossimo", "3p", "f") == "loro sono andate"
    assert answer(v, "trapassato_prossimo", "1p", "m") == "noi eravamo andati"
    assert answer(it.verb("essere"), "passato_prossimo", "1s", "m") == "io sono stato"


def test_reflexive(it):
    v = it.verb("alzarsi")
    assert v.auxiliary == "essere"
    assert v.reflexive_of == "alzare"
    assert answer(v, "presente", "1s") == "io mi alzo"
    assert answer(v, "passato_prossimo", "1s", "f") == "io mi sono alzata"
    assert answer(v, "passato_prossimo", "3p", "m") == "loro si sono alzati"
    assert [answer(v, "imperativo", p) for p in ("2s", "1p", "2p")] == ["alzati", "alziamoci", "alzatevi"]


def test_imperative(it):
    v = it.verb("andare")
    f = row(v, "imperativo", "2s")
    assert f.form == "vai"
    assert "va'" in f.alternatives
    assert answer(v, "imperativo", "2p") == "andate"


def test_both_auxiliaries(it):
    v = it.verb("correre")
    assert v.auxiliary == "both"


def test_irregular_marking(it):
    assert not row(it.verb("parlare"), "presente", "1s").irregular
    assert not row(it.verb("cercare"), "presente", "2s").irregular      # cerchi
    assert not row(it.verb("mangiare"), "futuro_semplice", "1s").irregular  # mangerò
    assert not row(it.verb("studiare"), "presente", "2s").irregular     # studi
    assert not row(it.verb("finire"), "presente", "1s").irregular       # finisco
    assert not row(it.verb("dormire"), "presente", "1s").irregular
    assert not row(it.verb("credere"), "passato_remoto", "1s").irregular
    assert row(it.verb("andare"), "presente", "1s").irregular           # vado
    assert not row(it.verb("andare"), "presente", "1p").irregular       # andiamo
    assert row(it.verb("fare"), "presente", "1s").irregular
    assert row(it.verb("prendere"), "passato_prossimo", "1s").irregular  # preso


def test_group(it):
    assert it.verb("parlare").group == "-are"
    assert it.verb("credere").group == "-ere"
    assert it.verb("finire").group == "-ire"
    assert it.verb("alzarsi").group == "-are"


def test_participle_and_gerund(it):
    v = it.verb("fare")
    assert row(v, "gerundio").form == "facendo"
    assert row(v, "participio_passato", "sg", "m").form == "fatto"
    assert row(v, "participio_passato", "pl", "f").form == "fatte"


def test_multiword_forms_lose_stress_marks():
    assert italian.orthography("se ne và") == "se ne va"


def test_pronominal_verbs_with_ne(it):
    v = it.verb("andarsene")
    assert v.reflexive_of == "andare"
    assert answer(v, "presente", "3s") == "lui/lei se ne va"
    assert answer(v, "passato_prossimo", "1s", "f") == "io me ne sono andata"
