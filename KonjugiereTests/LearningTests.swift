import Foundation
import Testing
@testable import Konjugiere

struct AnswerCheckerTests {
    @Test func toleratesCaseSpacesAndApostrophes() {
        #expect(AnswerChecker.check("  J’ aime ", accepted: ["j'aime"]) == .correct)
        #expect(AnswerChecker.check("Elle  est allée", accepted: ["elle est allée"]) == .correct)
    }

    @Test func accentsAreStrict() {
        #expect(AnswerChecker.check("elle est allee", accepted: ["elle est allée"]) == .accentOnly)
        #expect(AnswerChecker.check("il a ete", accepted: ["il a été"]) == .accentOnly)
        #expect(!AnswerResult.accentOnly.countsAsCorrect)
    }

    @Test func wrongAndEmpty() {
        #expect(AnswerChecker.check("je vais", accepted: ["je suis"]) == .wrong)
        #expect(AnswerChecker.check("   ", accepted: ["je suis"]) == .wrong)
    }

    @Test func alternativesAccepted() {
        #expect(AnswerChecker.check("je paie", accepted: ["je paye", "je paie"]) == .correct)
    }

    @Test func diffMarksMissingCharacters() {
        let segments = AnswerChecker.diff(input: "elle est alle", expected: "elle est allée")
        #expect(segments.map(\.text).joined() == "elle est allée")
        #expect(segments.filter { !$0.matches }.map(\.text) == ["é"])
    }
}

struct LeitnerTests {
    let calendar = Calendar(identifier: .gregorian)
    let now = Date(timeIntervalSince1970: 1_800_000_000)

    @Test func correctMovesUp() {
        let r = Leitner.next(box: 1, correct: true, now: now, calendar: calendar)
        #expect(r.box == 2)
        #expect(r.due == calendar.date(byAdding: .day, value: 2, to: calendar.startOfDay(for: now)))
    }

    @Test func capsAtFive() {
        #expect(Leitner.next(box: 5, correct: true, now: now, calendar: calendar).box == 5)
    }

    @Test func wrongResetsToOne() {
        let r = Leitner.next(box: 4, correct: false, now: now, calendar: calendar)
        #expect(r.box == 1)
        #expect(r.due == calendar.date(byAdding: .day, value: 1, to: calendar.startOfDay(for: now)))
    }
}

struct FormDisplayTests {
    @Test func combinesGender() {
        #expect(FormDisplay.combineGender("allé", "allée") == "allé(e)")
        #expect(FormDisplay.combineGender("allés", "allées") == "allé(e)s")
        #expect(FormDisplay.combineGender("andato", "andata") == "andato/a")
        #expect(FormDisplay.combineGender("suis", "suis") == "suis")
    }

    @Test func mergesMaleAndFemaleRows() {
        let rows = [
            FormRow(person: "1s", gender: "m", pronoun: "je", form: "suis allé"),
            FormRow(person: "1s", gender: "f", pronoun: "je", form: "suis allée"),
            FormRow(person: "3s", gender: "m", pronoun: "il", form: "est allé"),
            FormRow(person: "3s", gender: "f", pronoun: "elle", form: "est allée"),
        ]
        let lines = FormDisplay.lines(rows)
        #expect(lines.count == 2)
        #expect(lines[0].pronoun == "je")
        #expect(lines[0].form == "suis allé(e)")
        #expect(lines[1].pronoun == "il/elle")
    }
}

struct ExerciseFactoryTests {
    let verb = VerbSummary(id: 1, lang: .fr, key: "aller", infinitive: "aller", group: "3", auxiliary: "être",
                           model: nil, reflexiveOf: nil, rank: 1, gloss: "gehen", note: nil, hasIrregular: true)
    let present = Tense(lang: .fr, code: "present", mood: "Indicatif", nameNative: "Présent", nameDE: "Präsens",
                        sort: 1, level: 1, rare: false, personal: true)
    let subj = Tense(lang: .fr, code: "subjonctif_present", mood: "Subjonctif", nameNative: "Subjonctif présent",
                     nameDE: "Konjunktiv", sort: 2, level: 2, rare: false, personal: true)
    let pc = Tense(lang: .fr, code: "passe_compose", mood: "Indicatif", nameNative: "Passé composé",
                   nameDE: "Perfekt", sort: 3, level: 1, rare: false, personal: true)

    var table: ConjugationTable {
        ConjugationTable(rows: [
            "present": [
                FormRow(person: "1s", gender: nil, pronoun: "je", form: "vais"),
                FormRow(person: "2s", gender: nil, pronoun: "tu", form: "vas"),
                FormRow(person: "3s", gender: nil, pronoun: "il/elle", form: "va"),
                FormRow(person: "1p", gender: nil, pronoun: "nous", form: "allons"),
            ],
            "subjonctif_present": [
                FormRow(person: "1s", gender: nil, pronoun: "que j'", form: "aille"),
            ],
            "passe_compose": [
                FormRow(person: "1s", gender: "m", pronoun: "je", form: "suis allé"),
                FormRow(person: "1s", gender: "f", pronoun: "je", form: "suis allée"),
                FormRow(person: "3s", gender: "f", pronoun: "elle", form: "est allée"),
            ],
        ])
    }

    @Test func concretePronounAndChoices() throws {
        var rng = SystemRandomNumberGenerator()
        let key = CardKey(lang: .fr, verbKey: "aller", tense: "present", person: "3s", gender: "")
        let item = try #require(ExerciseFactory.item(key: key, verb: verb, tense: present, table: table, rng: &rng))
        #expect(["il", "elle"].contains(item.pronoun))
        #expect(item.solution == "\(item.pronoun) va")
        #expect(item.genderSymbol == nil)
        #expect(item.choices.count == 4)
        #expect(item.choices.contains("va"))
    }

    @Test func subjunctiveWithoutConjunctionAccepted() throws {
        var rng = SystemRandomNumberGenerator()
        let key = CardKey(lang: .fr, verbKey: "aller", tense: "subjonctif_present", person: "1s", gender: "")
        let item = try #require(ExerciseFactory.item(key: key, verb: verb, tense: subj, table: table, rng: &rng))
        #expect(item.solution == "que j'aille")
        #expect(AnswerChecker.check("j'aille", accepted: item.accepted) == .correct)
    }

    @Test func genderSymbolOnlyWhereFormChanges() throws {
        var rng = SystemRandomNumberGenerator()
        let fem = CardKey(lang: .fr, verbKey: "aller", tense: "passe_compose", person: "1s", gender: "f")
        let item = try #require(ExerciseFactory.item(key: fem, verb: verb, tense: pc, table: table, rng: &rng))
        #expect(item.genderSymbol == "♀")
        let elle = CardKey(lang: .fr, verbKey: "aller", tense: "passe_compose", person: "3s", gender: "f")
        let item3 = try #require(ExerciseFactory.item(key: elle, verb: verb, tense: pc, table: table, rng: &rng))
        #expect(item3.genderSymbol == nil)
        #expect(item3.solution == "elle est allée")
    }

    @Test func roundPrefersDueThenNew() {
        var rng = SystemRandomNumberGenerator()
        let now = Date()
        let keys = ["1s", "2s", "3s", "1p"].map { CardKey(lang: .fr, verbKey: "aller", tense: "present", person: $0, gender: "") }
        let states: [String: RoundBuilder.CardState] = [
            keys[0].string: .init(box: 3, due: now.addingTimeInterval(86_400)),   // noch nicht fällig
            keys[1].string: .init(box: 2, due: now.addingTimeInterval(-3_600)),   // fällig
        ]
        let picked = RoundBuilder.select(candidates: keys, states: states, now: now, count: 3, rng: &rng)
        #expect(picked.count == 3)
        #expect(picked[0] == keys[1])
        #expect(!picked.contains(keys[0]))
    }

    @Test func candidatesSkipInfinitiveRow() {
        let parts = Tense(lang: .en, code: Language.principalParts, mood: "", nameNative: "Principal parts",
                          nameDE: "Stammformen", sort: 0, level: 1, rare: false, personal: false)
        let go = VerbSummary(id: 2, lang: .en, key: "go", infinitive: "go", group: "irregular", auxiliary: nil,
                             model: nil, reflexiveOf: nil, rank: 1, gloss: "gehen", note: nil, hasIrregular: true)
        let t = ConjugationTable(rows: [Language.principalParts: [
            FormRow(person: "base", gender: nil, pronoun: "", form: "go"),
            FormRow(person: "past", gender: nil, pronoun: "", form: "went"),
            FormRow(person: "pp", gender: nil, pronoun: "", form: "gone"),
        ]])
        let keys = RoundBuilder.candidates(verbs: [go], tenses: [parts], table: { _ in t })
        #expect(keys.map(\.person) == ["past", "pp"])
    }
}
