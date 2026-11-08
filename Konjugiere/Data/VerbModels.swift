import Foundation

/// Eine Zeitform, z. B. «Passé composé» (Perfekt).
nonisolated struct Tense: Identifiable, Hashable {
    let lang: Language
    let code: String
    let mood: String
    let nameNative: String
    let nameDE: String
    let sort: Int
    /// 1 Einsteiger, 2 Mittel, 3 Fortgeschritten
    let level: Int
    /// In der Tabelle anfangs zugeklappt.
    let rare: Bool
    /// Hat Personen (je, tu …). Partizipien und Gerundium nicht.
    let personal: Bool

    var id: String { "\(lang.rawValue):\(code)" }
    var isPrincipalParts: Bool { code == Language.principalParts }
    /// Kann geübt werden. Englisch: nur die Stammformen (Q21), die übrigen Zeiten dienen dem Nachschlagen.
    var practicable: Bool { lang == .en ? isPrincipalParts : personal }
}

/// Kurzinfo zu einem Verb, wie sie in Listen und im Kopf der Tabelle erscheint.
nonisolated struct VerbSummary: Identifiable, Hashable {
    let id: Int
    let lang: Language
    /// Stabil über Neuaufbauten der Datenbank. Lernfortschritt hängt daran.
    let key: String
    let infinitive: String
    let group: String?
    let auxiliary: String?
    /// «wird konjugiert wie …» (nur Französisch)
    let model: String?
    let reflexiveOf: String?
    let rank: Int?
    let gloss: String
    /// Unterscheidung gleich geschriebener englischer Verben (lie / lie)
    let note: String?
    let hasIrregular: Bool

    var groupLabel: String? {
        guard let group else { return nil }
        switch (lang, group) {
        case (.fr, "1"): return "1. Gruppe (-er)"
        case (.fr, "2"): return "2. Gruppe (-ir, -iss-)"
        case (.fr, "3"): return "3. Gruppe"
        case (.en, "irregular"): return "unregelmässig"
        case (.en, "regular"): return "regelmässig"
        default: return "Verben auf \(group)"
        }
    }

    var auxiliaryLabel: String? {
        guard let auxiliary else { return nil }
        switch auxiliary {
        case "both": return lang == .fr ? "être / avoir" : "essere / avere"
        default: return auxiliary
        }
    }
}

/// Eine Zeile der Konjugationstabelle.
nonisolated struct FormRow: Hashable, Decodable {
    /// 1s 2s 3s 1p 2p 3p · bei Partizipien sg/pl · bei englischen Stammformen base/past/pp
    let person: String?
    /// m / f / nil (= gilt für beide)
    let gender: String?
    /// «je», «j'», «il/elle», «que je» … – leer beim Imperativ
    let pronoun: String
    let form: String
    let alternatives: [String]
    let irregular: Bool

    init(person: String?, gender: String?, pronoun: String, form: String,
         alternatives: [String] = [], irregular: Bool = false) {
        self.person = person
        self.gender = gender
        self.pronoun = pronoun
        self.form = form
        self.alternatives = alternatives
        self.irregular = irregular
    }

    /// Die Datenbank speichert jede Zeile als Array: [person, gender, pronoun, form, [alt], irr]
    init(from decoder: Decoder) throws {
        var c = try decoder.unkeyedContainer()
        person = try c.decodeNil() ? nil : c.decode(String.self)
        gender = try c.decodeNil() ? nil : c.decode(String.self)
        pronoun = try c.decode(String.self)
        form = try c.decode(String.self)
        alternatives = try c.decode([String].self)
        irregular = try c.decode(Int.self) != 0
    }
}

/// Die ganze Konjugation eines Verbs.
nonisolated struct ConjugationTable {
    let rows: [String: [FormRow]]

    func rows(for tense: String) -> [FormRow] { rows[tense] ?? [] }
}

/// Ein kuratiertes Lernpaket.
nonisolated struct LearningPackage: Identifiable, Hashable {
    let id: Int
    let lang: Language
    let title: String
    let description: String
    let level: Int
    /// Fest vorgegebene Zeitformen; nil = aktive Zeitformen des Profils
    let tenses: [String]?
}

/// Herkunft und Lizenz der Daten einer Sprache.
nonisolated struct SourceInfo: Identifiable {
    let lang: String
    let name: String
    let source: String
    let license: String
    let attribution: String
    var id: String { lang }
}
