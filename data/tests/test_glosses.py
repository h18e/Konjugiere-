from pipeline.glosses import GlossIndex, clean_gloss, entry_glosses


def test_explanation_and_translation_are_separated():
    assert clean_gloss("um sich von einem Ort zu entfernen: abfahren, abreisen") == ["abfahren", "abreisen"]
    assert clean_gloss("sich zum Sprecher oder zu der Person bewegen; kommen, herkommen") == ["kommen", "herkommen"]


def test_simple_gloss():
    assert clean_gloss("folgen") == ["folgen"]


def test_long_explanations_and_nouns_are_dropped():
    assert clean_gloss("eine Handlung mehrmals hintereinander ausführen") == []
    assert clean_gloss("Präteritum des Verbs") == []
    assert clean_gloss("regnen, auch") == ["regnen"]


def test_brackets():
    assert clean_gloss("[1] heben; aufheben, erheben") == ["heben", "aufheben", "erheben"]


def test_form_of_entries_are_ignored():
    entry = {"tags": ["form-of"], "senses": [{"glosses": ["Präteritum (simple past) des Verbs go"]}]}
    assert entry_glosses(entry) == []


def test_reverse_translations_rank_by_points():
    idx = GlossIndex()
    idx.add_entry({"lang_code": "de", "word": "gehen", "translations": [
        {"lang_code": "fr", "word": "aller", "sense_index": "1"},
        {"lang_code": "fr", "word": "aller", "sense_index": "4"}]})
    idx.add_entry({"lang_code": "de", "word": "sieben", "translations": [
        {"lang_code": "fr", "word": "passer", "sense_index": "1"}]})
    idx.add_entry({"lang_code": "de", "word": "fahren", "translations": [
        {"lang_code": "fr", "word": "aller", "sense_index": "3"}]})
    assert idx.terms("fr", "aller") == ["gehen", "fahren"]
    assert idx.short("fr", "aller") == "gehen"          # fahren hat nur 1 Punkt
    assert "fahren" in idx.terms("fr", "aller")         # … zählt aber für die Suche


def test_direct_and_reverse_combine():
    idx = GlossIndex()
    idx.add_entry({"lang_code": "fr", "word": "suivre", "senses": [{"glosses": ["folgen"]}]})
    idx.add_entry({"lang_code": "de", "word": "folgen", "translations": [
        {"lang_code": "fr", "word": "suivre", "sense_index": "1"}]})
    idx.add_entry({"lang_code": "de", "word": "verfolgen", "translations": [
        {"lang_code": "fr", "word": "suivre", "sense_index": "1"}]})
    assert idx.short("fr", "suivre") == "folgen, verfolgen"


def test_explanation_segment_with_long_parts_is_dropped_completely():
    assert clean_gloss("sich in einem Zustand, einer Charakteristik befinden, an einem Ort sein") == []


def test_grammar_labels_are_dropped():
    assert clean_gloss("denken, transitiv") == ["denken"]


def test_commas_inside_parentheses_do_not_split():
    assert clean_gloss("denken (bedenken, überlegen)") == ["denken (bedenken, überlegen)"]


def test_short_gloss_ignores_parenthetical_duplicates_and_spacing():
    idx = GlossIndex()
    idx.add_entry({"lang_code": "fr", "word": "savoir", "senses": [
        {"glosses": ["wissen, können"]}, {"glosses": ["können (fähig sein)"]}]})
    idx.add_entry({"lang_code": "fr", "word": "attendre", "senses": [
        {"glosses": ["warten (auf etwas)"]}, {"glosses": ["warten\u00a0(auf etwas)"]}]})
    assert idx.short("fr", "savoir") == "wissen, können"
    assert idx.short("fr", "attendre") == "warten (auf etwas)"


def test_translation_fields_are_cleaned_too():
    idx = GlossIndex()
    idx.add_entry({"lang_code": "en", "word": "wait", "senses": [], "translations": [
        {"lang_code": "de", "word": "warten (auf etwas), abwarten", "sense_index": "1"}]})
    assert idx.short("en", "wait") == "warten (auf etwas), abwarten"
