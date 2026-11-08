import Foundation
import SwiftData

// Lerndaten (SwiftData). Alle Felder haben Standardwerte und es gibt keine
// Pflicht-Beziehungen, damit sich später iCloud (CloudKit) einschalten lässt.

@Model
final class Profile {
    var id: UUID = UUID()
    var name: String = ""
    /// 1 Einsteiger, 2 Mittel, 3 Fortgeschritten (Q31)
    var level: Int = 1
    /// Zuletzt gewählte Sprache, gleichzeitig der Standard beim Öffnen
    var languageCode: String = Language.fr.rawValue
    var roundLength: Int = 15
    /// Eigene Auswahl der Zeitformen, als «fr:present». Fehlt eine Sprache, gilt die Stufe.
    var activeTenseKeys: [String] = []
    var created: Date = Date()

    init(name: String, level: Int) {
        self.name = name
        self.level = level
    }

    var language: Language {
        get { Language(rawValue: languageCode) ?? .fr }
        set { languageCode = newValue.rawValue }
    }

    static let levelNames = [1: "Einsteiger", 2: "Mittel", 3: "Fortgeschritten"]
    var levelName: String { Self.levelNames[level] ?? "?" }

    private func customMarker(_ lang: Language) -> String { "\(lang.rawValue):*" }

    func hasCustomTenses(_ lang: Language) -> Bool { activeTenseKeys.contains(customMarker(lang)) }

    /// Aktive Zeitformen einer Sprache: eigene Auswahl oder alles bis zur Stufe des Profils.
    func activeTenses(_ lang: Language, all: [Tense]) -> [Tense] {
        let practicable = all.filter(\.practicable)
        if hasCustomTenses(lang) {
            let codes = Set(activeTenseKeys.compactMap { key -> String? in
                let parts = key.split(separator: ":", maxSplits: 1)
                return parts.count == 2 && parts[0] == lang.rawValue ? String(parts[1]) : nil
            })
            return practicable.filter { codes.contains($0.code) }
        }
        return practicable.filter { $0.level <= level }
    }

    func setTense(_ tense: Tense, active: Bool, all: [Tense]) {
        let lang = tense.lang
        var codes = Set(activeTenses(lang, all: all).map(\.code))
        if active { codes.insert(tense.code) } else { codes.remove(tense.code) }
        activeTenseKeys.removeAll { $0.hasPrefix("\(lang.rawValue):") }
        activeTenseKeys.append(customMarker(lang))
        activeTenseKeys += codes.sorted().map { "\(lang.rawValue):\($0)" }
    }

    func resetTenses(_ lang: Language) {
        activeTenseKeys.removeAll { $0.hasPrefix("\(lang.rawValue):") }
    }
}

@Model
final class Card {
    var profileID: UUID = UUID()
    /// CardKey.string – zum schnellen Nachschlagen
    var keyString: String = ""
    var lang: String = ""
    var verbKey: String = ""
    var tense: String = ""
    var person: String = ""
    var gender: String = ""
    var box: Int = 1
    var due: Date = Date()
    var correctCount: Int = 0
    var wrongCount: Int = 0
    var lastSeen: Date? = nil

    init(profileID: UUID, key: CardKey) {
        self.profileID = profileID
        self.keyString = key.string
        self.lang = key.lang.rawValue
        self.verbKey = key.verbKey
        self.tense = key.tense
        self.person = key.person
        self.gender = key.gender
    }

    var key: CardKey? {
        guard let l = Language(rawValue: lang) else { return nil }
        return CardKey(lang: l, verbKey: verbKey, tense: tense, person: person, gender: gender)
    }

    func record(correct: Bool, now: Date = Date()) {
        let next = Leitner.next(box: box, correct: correct, now: now)
        box = next.box
        due = next.due
        lastSeen = now
        if correct { correctCount += 1 } else { wrongCount += 1 }
    }
}

@Model
final class MyVerb {
    var profileID: UUID = UUID()
    var lang: String = ""
    var verbKey: String = ""
    var infinitive: String = ""
    var added: Date = Date()

    init(profileID: UUID, verb: VerbSummary) {
        self.profileID = profileID
        self.lang = verb.lang.rawValue
        self.verbKey = verb.key
        self.infinitive = verb.infinitive
    }
}

@Model
final class ErrorReport {
    var lang: String = ""
    var verbKey: String = ""
    var infinitive: String = ""
    var tense: String = ""
    var person: String = ""
    var gender: String = ""
    var shownForm: String = ""
    var note: String = ""
    var created: Date = Date()

    init(verb: VerbSummary, tense: String, row: FormRow, note: String) {
        self.lang = verb.lang.rawValue
        self.verbKey = verb.key
        self.infinitive = verb.infinitive
        self.tense = tense
        self.person = row.person ?? ""
        self.gender = row.gender ?? ""
        self.shownForm = TextNormalizer.fullAnswer(pronoun: row.pronoun, form: row.form)
        self.note = note
    }

    /// Eine Zeile im Format von data/corrections/corrections.tsv, ergänzt um die Notiz.
    var exportLine: String {
        [lang, infinitive, tense, person, gender, shownForm, "", note].joined(separator: "\t")
    }
}

enum ErrorExport {
    static func text(_ reports: [ErrorReport]) -> String {
        let header = "# Fehlermeldungen aus Konjugiere! – bitte an Claude schicken\n"
            + "lang\tinfinitive\ttense\tperson\tgender\tshown_form\tcorrect_form\tnote"
        return ([header] + reports.sorted { $0.created < $1.created }.map(\.exportLine)).joined(separator: "\n")
    }
}
