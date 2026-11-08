"""Tests für die französische Konjugation (Verbiste + eigene Regeln).

Die Tests laufen gegen die echten Verbiste-Dateien. Fehlen sie, zuerst
`python3 -m pipeline.fetch verbiste` ausführen.
"""

import pytest

from pipeline import french
from pipeline.model import full_answer


@pytest.fixture(scope="module")
def fr():
    return french.Conjugator.from_verbiste()


def row(verb, tense, person=None, gender=None):
    rows = [f for f in verb.tenses[tense] if f.person == person and f.gender == gender]
    assert len(rows) == 1, f"{tense} {person} {gender}: {rows}"
    return rows[0]


def answer(verb, tense, person=None, gender=None):
    return full_answer(row(verb, tense, person, gender))


# --- einfache Zeiten -------------------------------------------------------

def test_present_regular(fr):
    v = fr.verb("parler")
    assert answer(v, "present", "1s") == "je parle"
    assert answer(v, "present", "1p") == "nous parlons"
    assert answer(v, "present", "3p") == "ils/elles parlent"


def test_elision_before_vowel_and_mute_h(fr):
    assert answer(fr.verb("aimer"), "present", "1s") == "j'aime"
    assert answer(fr.verb("habiter"), "present", "1s") == "j'habite"


def test_no_elision_before_aspirate_h(fr):
    assert answer(fr.verb("haïr"), "present", "1s") == "je hais"


def test_irregular_present(fr):
    v = fr.verb("aller")
    assert [answer(v, "present", p) for p in ("1s", "2s", "3s", "1p", "2p", "3p")] == [
        "je vais", "tu vas", "il/elle va", "nous allons", "vous allez", "ils/elles vont"]


def test_spelling_variants_become_alternatives(fr):
    f = row(fr.verb("payer"), "present", "1s")
    assert f.form == "paie"
    assert "paye" in f.alternatives


def test_defective_verb_has_only_existing_persons(fr):
    v = fr.verb("pleuvoir")
    assert {f.person for f in v.tenses["present"]} == {"3s", "3p"}


def test_subjunctive_has_que(fr):
    v = fr.verb("être")
    assert answer(v, "subjonctif_present", "1s") == "que je sois"
    assert answer(v, "subjonctif_present", "3s") == "qu'il/qu'elle soit"
    assert answer(fr.verb("avoir"), "subjonctif_present", "1s") == "que j'aie"


def test_imperative(fr):
    v = fr.verb("finir")
    assert [answer(v, "imperatif", p) for p in ("2s", "1p", "2p")] == ["finis", "finissons", "finissez"]


# --- zusammengesetzte Zeiten ----------------------------------------------

def test_passe_compose_with_avoir_has_no_gender(fr):
    v = fr.verb("manger")
    assert answer(v, "passe_compose", "1s") == "j'ai mangé"
    assert answer(v, "passe_compose", "3p") == "ils/elles ont mangé"
    assert fr.verb("manger").auxiliary == "avoir"


def test_passe_compose_with_etre_agrees(fr):
    v = fr.verb("aller")
    assert v.auxiliary == "être"
    assert answer(v, "passe_compose", "1s", "m") == "je suis allé"
    assert answer(v, "passe_compose", "1s", "f") == "je suis allée"
    assert answer(v, "passe_compose", "3s", "f") == "elle est allée"
    assert answer(v, "passe_compose", "3p", "m") == "ils sont allés"
    assert answer(v, "passe_compose", "3p", "f") == "elles sont allées"
    assert answer(v, "passe_compose", "2p", "f") == "vous êtes allées"


def test_verbs_with_both_auxiliaries_accept_avoir(fr):
    v = fr.verb("monter")
    assert v.auxiliary == "both"
    f = row(v, "passe_compose", "1s", "m")
    assert f.form == "suis monté"
    assert "ai monté" in f.alternatives


def test_other_compound_tenses(fr):
    v = fr.verb("venir")
    assert answer(v, "plus_que_parfait", "3s", "f") == "elle était venue"
    assert answer(v, "futur_anterieur", "1p", "m") == "nous serons venus"
    assert answer(v, "conditionnel_passe", "1s", "m") == "je serais venu"
    assert answer(v, "subjonctif_passe", "1s", "f") == "que je sois venue"
    assert answer(fr.verb("parler"), "plus_que_parfait", "1s") == "j'avais parlé"


def test_futur_proche(fr):
    assert answer(fr.verb("parler"), "futur_proche", "1s") == "je vais parler"
    assert answer(fr.verb("être"), "futur_proche", "3p") == "ils/elles vont être"


# --- reflexive Verben -----------------------------------------------------

def test_reflexive_present(fr):
    v = fr.verb("se lever")
    assert answer(v, "present", "1s") == "je me lève"
    assert answer(v, "present", "1p") == "nous nous levons"
    assert answer(fr.verb("s'habiller"), "present", "1s") == "je m'habille"


def test_reflexive_compound_uses_etre_and_agrees(fr):
    v = fr.verb("se lever")
    assert v.auxiliary == "être"
    assert answer(v, "passe_compose", "1s", "f") == "je me suis levée"
    assert answer(v, "passe_compose", "3p", "m") == "ils se sont levés"
    assert answer(fr.verb("s'habiller"), "passe_compose", "3s", "f") == "elle s'est habillée"


def test_reflexive_imperative_and_futur_proche(fr):
    v = fr.verb("se lever")
    assert [answer(v, "imperatif", p) for p in ("2s", "1p", "2p")] == ["lève-toi", "levons-nous", "levez-vous"]
    assert answer(v, "futur_proche", "1s") == "je vais me lever"
    assert answer(fr.verb("s'habiller"), "futur_proche", "1s") == "je vais m'habiller"


# --- Unregelmässigkeit, Muster ---------------------------------------------

def test_irregular_marking(fr):
    assert not row(fr.verb("parler"), "present", "1p").irregular
    assert not row(fr.verb("finir"), "present", "1p").irregular
    assert row(fr.verb("aller"), "present", "1s").irregular
    assert not row(fr.verb("aller"), "present", "1p").irregular
    assert row(fr.verb("aller"), "futur_simple", "1s").irregular   # irai
    assert row(fr.verb("acheter"), "present", "1s").irregular      # achète
    assert row(fr.verb("prendre"), "present", "1p").irregular      # prenons
    assert not row(fr.verb("vendre"), "present", "1p").irregular


def test_group(fr):
    assert fr.verb("parler").group == "1"
    assert fr.verb("finir").group == "2"
    assert fr.verb("partir").group == "3"
    assert fr.verb("aller").group == "3"


def test_model_verbs(fr):
    assert fr.verb("parler").model == "aimer"
    assert fr.verb("prendre").model == "prendre"


def test_participles(fr):
    v = fr.verb("aller")
    assert row(v, "participe_present").form == "allant"
    assert {(f.person, f.gender, f.form) for f in v.tenses["participe_passe"]} == {
        ("sg", "m", "allé"), ("sg", "f", "allée"), ("pl", "m", "allés"), ("pl", "f", "allées")}


def test_missing_participle_forms_are_derived(fr):
    # Verbiste kennt bei fuir nur «fui»
    assert answer(fr.verb("s'enfuir"), "passe_compose", "3s", "f") == "elle s'est enfuie"
    assert answer(fr.verb("s'enfuir"), "passe_compose", "3p", "f") == "elles se sont enfuies"
