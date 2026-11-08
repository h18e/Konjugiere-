import Foundation

/// Eindeutige Kennung einer Lernkarte: Verb × Zeitform × Person × Geschlecht (Q18).
nonisolated struct CardKey: Hashable, Codable {
    let lang: Language
    let verbKey: String
    let tense: String
    let person: String
    /// «m», «f» oder leer
    let gender: String

    var string: String { [lang.rawValue, verbKey, tense, person, gender].joined(separator: "|") }
}

/// Eine einzelne Aufgabe in einer Übungsrunde.
nonisolated struct ExerciseItem: Identifiable {
    let id = UUID()
    let key: CardKey
    let verb: VerbSummary
    let tense: Tense
    /// So angezeigt, wie es eingetippt werden soll («elle», «que je», «I»), leer beim Imperativ
    let pronoun: String
    /// ♀ / ♂, nur wenn sich die Form dadurch ändert und das Pronomen es nicht zeigt (Q23)
    let genderSymbol: String?
    /// Bezeichnung der Person, wenn es kein Pronomen gibt (Imperativ, Stammformen)
    let personLabel: String?
    /// Musterlösung inkl. Pronomen
    let solution: String
    /// Alle zulässigen Antworten inkl. Pronomen
    let accepted: [String]
    /// Form ohne Pronomen (Multiple Choice, Tabelle)
    let bareForm: String
    let bareAccepted: [String]
    /// Antwortmöglichkeiten für Multiple Choice (Formen ohne Pronomen), inkl. der richtigen
    var choices: [String] = []
}

nonisolated enum ExerciseFactory {
    static let genderedPersons: Set<String> = ["1s", "2s", "1p", "2p"]

    /// Erzeugt die Aufgabe zu einer Karte. Gibt nil zurück, wenn die Form fehlt.
    static func item<R: RandomNumberGenerator>(key: CardKey, verb: VerbSummary, tense: Tense,
                                               table: ConjugationTable, rng: inout R) -> ExerciseItem? {
        let rows = table.rows(for: tense.code)
        guard let row = rows.first(where: { $0.person == key.person && ($0.gender ?? "") == key.gender }) else {
            return nil
        }
        let pronoun = choosePronoun(row.pronoun, rng: &rng)
        let forms = [row.form] + row.alternatives
        var accepted = forms.map { TextNormalizer.fullAnswer(pronoun: pronoun, form: $0) }
        // «que je sois» darf auch ohne «que» eingetippt werden
        for conj in key.lang.subjunctiveConjunctions where pronoun.hasPrefix(conj) {
            let rest = String(pronoun.dropFirst(conj.count))
            accepted += forms.map { TextNormalizer.fullAnswer(pronoun: rest, form: $0) }
        }
        let symbol: String? = {
            guard let g = row.gender, genderedPersons.contains(key.person) else { return nil }
            return g == "f" ? "♀" : "♂"
        }()
        var item = ExerciseItem(
            key: key, verb: verb, tense: tense, pronoun: pronoun, genderSymbol: symbol,
            personLabel: pronoun.isEmpty ? personLabel(key.person, lang: key.lang) : nil,
            solution: accepted[0], accepted: accepted, bareForm: row.form, bareAccepted: forms)
        item.choices = choices(for: row, tense: tense, table: table, rng: &rng)
        return item
    }

    /// «il/elle» → «il» oder «elle» ; «qu'il/qu'elle» entsprechend ; «he/she/it» → eines davon.
    static func choosePronoun<R: RandomNumberGenerator>(_ pronoun: String, rng: inout R) -> String {
        let parts = pronoun.split(separator: "/").map(String.init)
        return parts.count > 1 ? parts.randomElement(using: &rng)! : pronoun
    }

    static func personLabel(_ person: String, lang: Language) -> String? {
        switch person {
        case "past": "Simple past"
        case "pp": "Past participle"
        case "base": "Infinitive"
        case "2s": lang == .en ? "you (Singular)" : "Imperativ, 2. Person Singular"
        case "1p": lang == .en ? "let's" : "Imperativ, 1. Person Plural"
        case "2p": lang == .en ? "you (Plural)" : "Imperativ, 2. Person Plural"
        default: nil
        }
    }

    /// Drei falsche Formen aus derselben Tabelle: erst andere Personen derselben Zeit, dann andere Zeiten.
    static func choices<R: RandomNumberGenerator>(for row: FormRow, tense: Tense, table: ConjugationTable,
                                                  rng: inout R) -> [String] {
        let correct = row.form
        var pool: [String] = []
        func add(_ form: String) {
            if form != correct && !row.alternatives.contains(form) && !pool.contains(form) { pool.append(form) }
        }
        table.rows(for: tense.code).shuffled(using: &rng).forEach { add($0.form) }
        if pool.count < 3 {
            for (code, rows) in table.rows.sorted(by: { $0.key < $1.key }) where code != tense.code {
                rows.filter { $0.person == row.person }.forEach { add($0.form) }
            }
        }
        var options = Array(pool.shuffled(using: &rng).prefix(3)) + [correct]
        options.shuffle(using: &rng)
        return options
    }
}

/// Welche Karten in eine Runde kommen.
nonisolated enum RoundBuilder {
    struct CardState {
        let box: Int
        let due: Date
    }

    /// Reihenfolge: zuerst fällige Karten (älteste zuerst), dann neue, dann noch nicht fällige aus tiefen Fächern.
    static func select<R: RandomNumberGenerator>(candidates: [CardKey], states: [String: CardState], now: Date,
                                                 count: Int, rng: inout R) -> [CardKey] {
        var due: [(CardKey, CardState)] = []
        var fresh: [CardKey] = []
        var later: [(CardKey, CardState)] = []
        for key in candidates {
            if let s = states[key.string] {
                if Leitner.isDue(s.due, now: now) { due.append((key, s)) } else { later.append((key, s)) }
            } else {
                fresh.append(key)
            }
        }
        due.sort { ($0.1.due, $0.1.box) < ($1.1.due, $1.1.box) }
        later.sort { ($0.1.box, $0.1.due) < ($1.1.box, $1.1.due) }
        fresh.shuffle(using: &rng)
        let ordered = due.map(\.0) + fresh + later.map(\.0)
        return Array(ordered.prefix(count))
    }

    /// Alle Karten, die zu den Verben und Zeitformen gehören.
    static func candidates(verbs: [VerbSummary], tenses: [Tense], table: (VerbSummary) -> ConjugationTable) -> [CardKey] {
        var result: [CardKey] = []
        for verb in verbs {
            let t = table(verb)
            for tense in tenses where tense.practicable {
                for row in t.rows(for: tense.code) {
                    guard let person = row.person, person != "base" else { continue }
                    result.append(CardKey(lang: verb.lang, verbKey: verb.key, tense: tense.code,
                                          person: person, gender: row.gender ?? ""))
                }
            }
        }
        return result
    }
}
