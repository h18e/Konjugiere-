"""Tests für Englisch. Voraussetzung: `python3 -m pipeline.extract` wurde ausgeführt."""

import pytest

from pipeline import english
from pipeline.model import full_answer


@pytest.fixture(scope="module")
def en():
    return english.Conjugator.from_extract(only={"go", "walk", "be", "have", "learn", "lie", "can", "stop", "pay", "say", "speak", "shut"})


def row(verb, tense, person=None):
    rows = [f for f in verb.tenses[tense] if f.person == person]
    assert len(rows) == 1, f"{tense} {person}: {rows}"
    return rows[0]


def answer(verb, tense, person=None):
    return full_answer(row(verb, tense, person))


def test_principal_parts(en):
    v = en.verbs("go")[0]
    assert [row(v, "principal_parts", p).form for p in ("base", "past", "pp")] == ["go", "went", "gone"]
    assert row(v, "principal_parts", "past").irregular


def test_regular_verb_not_irregular(en):
    v = en.verbs("walk")[0]
    assert not row(v, "principal_parts", "past").irregular
    assert not v.group == "irregular"
    assert en.verbs("go")[0].group == "irregular"


def test_variants_become_alternatives(en):
    v = en.verbs("learn")[0]
    f = row(v, "principal_parts", "past")
    assert f.form == "learned"
    assert "learnt" in f.alternatives


def test_homographs_with_different_forms_are_separate(en):
    lies = en.verbs("lie")
    assert {row(v, "principal_parts", "past").form for v in lies} == {"lay", "lied"}


def test_modal_is_excluded_but_regular_can_stays(en):
    cans = en.verbs("can")
    assert len(cans) == 1
    assert row(cans[0], "principal_parts", "past").form == "canned"


def test_simple_tenses(en):
    v = en.verbs("go")[0]
    assert answer(v, "simple_present", "1s") == "I go"
    assert answer(v, "simple_present", "3s") == "he/she/it goes"
    assert answer(v, "simple_past", "1p") == "we went"


def test_compound_tenses(en):
    v = en.verbs("go")[0]
    assert answer(v, "present_progressive", "1s") == "I am going"
    assert answer(v, "present_progressive", "3s") == "he/she/it is going"
    assert answer(v, "past_progressive", "2s") == "you were going"
    assert answer(v, "present_perfect", "3s") == "he/she/it has gone"
    assert answer(v, "present_perfect", "1p") == "we have gone"
    assert answer(v, "past_perfect", "1s") == "I had gone"
    assert answer(v, "will_future", "1s") == "I will go"
    assert answer(v, "going_to_future", "3p") == "they are going to go"
    assert answer(v, "conditional_perfect", "1s") == "I would have gone"
    assert answer(v, "imperative", "2s") == "go"


def test_be(en):
    v = en.verbs("be")[0]
    assert [answer(v, "simple_present", p) for p in ("1s", "2s", "3s", "1p", "2p", "3p")] == [
        "I am", "you are", "he/she/it is", "we are", "you are", "they are"]
    assert answer(v, "simple_past", "3s") == "he/she/it was"
    assert answer(v, "simple_past", "2s") == "you were"
    assert answer(v, "present_perfect", "1s") == "I have been"


def test_have(en):
    v = en.verbs("have")[0]
    assert answer(v, "simple_present", "3s") == "he/she/it has"
    assert answer(v, "present_perfect", "1s") == "I have had"


@pytest.mark.parametrize("base,past,pp", [("say", "said", "said"), ("speak", "spoke", "spoken"), ("shut", "shut", "shut")])
def test_verbs_with_special_wiktionary_layout(en, base, past, pp):
    v = en.verbs(base)[0]
    assert [row(v, "principal_parts", p).form for p in ("past", "pp")] == [past, pp]
