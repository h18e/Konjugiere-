import Foundation
import Observation
import SwiftData

enum ExerciseMode: String, CaseIterable, Identifiable {
    case typing, choice, table

    var id: String { rawValue }

    var name: String {
        switch self {
        case .typing: "Eintippen"
        case .choice: "Auswahl"
        case .table: "Tabelle"
        }
    }

    static let storageKey = "exerciseMode"

    static var stored: ExerciseMode {
        ExerciseMode(rawValue: UserDefaults.standard.string(forKey: storageKey) ?? "") ?? .typing
    }
}

/// Was geübt werden soll (Q19): Paket, freie Auswahl, Meine Verben oder «Heute fällig».
struct PracticeSession: Identifiable {
    let id = UUID()
    let title: String
    let lang: Language
    var verbs: [VerbSummary]
    /// Fest vorgegebene Zeitformen; nil = aktive Zeitformen des Profils
    var tenseCodes: [String]?
    /// Nur fällige Karten (die Verben ergeben sich aus den Karten)
    var dueOnly = false
    var mode: ExerciseMode

    init(title: String, lang: Language, verbs: [VerbSummary], tenseCodes: [String]? = nil,
         dueOnly: Bool = false, mode: ExerciseMode = .stored) {
        self.title = title
        self.lang = lang
        self.verbs = verbs
        self.tenseCodes = tenseCodes
        self.dueOnly = dueOnly
        self.mode = mode
    }
}

/// Ablauf einer Übungsrunde (Q27): Falsche Karten kommen am Ende nochmals,
/// ins Leitner-System zählt nur die erste Antwort pro Karte.
@Observable
final class SessionEngine {
    enum Step: Identifiable {
        case single(ExerciseItem)
        case table([ExerciseItem])

        var id: UUID {
            switch self {
            case .single(let item): item.id
            case .table(let items): items[0].id
            }
        }
    }

    let session: PracticeSession
    private(set) var steps: [Step] = []
    private(set) var index = 0
    /// Erste Antwort pro Karte: richtig/falsch
    private(set) var firstResults: [String: Bool] = [:]
    private(set) var repeats = 0

    private let profileID: UUID
    private var cards: [String: Card]
    private var tables: [Int: ConjugationTable] = [:]
    private var rng = SystemRandomNumberGenerator()
    private let database: VerbDatabase

    var current: Step? { index < steps.count ? steps[index] : nil }
    var finished: Bool { current == nil }
    var progress: Double { steps.isEmpty ? 1 : Double(index) / Double(steps.count) }
    var correctFirstTry: Int { firstResults.values.filter { $0 }.count }

    init(session: PracticeSession, database: VerbDatabase, profile: Profile, cards: [Card], now: Date = Date()) {
        self.session = session
        self.database = database
        self.profileID = profile.id
        var byKey: [String: Card] = [:]
        for c in cards where c.profileID == profile.id { byKey[c.keyString] = c }
        self.cards = byKey
        build(profile: profile, now: now)
    }

    private func table(_ verb: VerbSummary) -> ConjugationTable {
        if let t = tables[verb.id] { return t }
        let t = database.table(for: verb)
        tables[verb.id] = t
        return t
    }

    private func build(profile: Profile, now: Date) {
        let lang = session.lang
        let allTenses = database.tenses(lang)
        var verbs = session.verbs
        var candidates: [CardKey]
        if session.dueOnly {
            let due = cards.values.filter { $0.lang == lang.rawValue && Leitner.isDue($0.due, now: now) }
            candidates = due.compactMap(\.key)
            let keys = Set(candidates.map(\.verbKey))
            verbs = keys.compactMap { database.verb(lang, key: $0) }
        } else {
            let tenses: [Tense]
            if let codes = session.tenseCodes {
                tenses = codes.compactMap { code in allTenses.first { $0.code == code } }
            } else {
                tenses = profile.activeTenses(lang, all: allTenses)
            }
            candidates = RoundBuilder.candidates(verbs: verbs, tenses: tenses, table: table)
        }
        let verbByKey = Dictionary(verbs.map { ($0.key, $0) }, uniquingKeysWith: { a, _ in a })
        let states = cards.mapValues { RoundBuilder.CardState(box: $0.box, due: $0.due) }

        switch session.mode {
        case .typing, .choice:
            let keys = RoundBuilder.select(candidates: candidates, states: states, now: now,
                                           count: profile.roundLength, rng: &rng)
            steps = keys.compactMap { key in
                guard let v = verbByKey[key.verbKey] else { return nil }
                return makeItem(key, verb: v).map(Step.single)
            }
        case .table:
            // Reihenfolge der Tabellen nach Dringlichkeit; pro Person ein zufälliges Geschlecht
            let ordered = RoundBuilder.select(candidates: candidates, states: states, now: now,
                                              count: candidates.count, rng: &rng)
            var groups: [String] = []
            for key in ordered where !groups.contains(key.verbKey + "|" + key.tense) {
                groups.append(key.verbKey + "|" + key.tense)
            }
            let tableCount = max(1, profile.roundLength / 5)
            for group in groups.prefix(tableCount) {
                let keys = candidates.filter { $0.verbKey + "|" + $0.tense == group }
                var chosen: [CardKey] = []
                var persons: [String] = []
                for k in keys where !persons.contains(k.person) {
                    persons.append(k.person)
                    let options = keys.filter { $0.person == k.person }
                    chosen.append(options.randomElement(using: &rng)!)
                }
                guard let v = verbByKey[chosen.first?.verbKey ?? ""] else { continue }
                let items = chosen.compactMap { makeItem($0, verb: v) }
                if !items.isEmpty { steps.append(.table(items)) }
            }
        }
    }

    private func makeItem(_ key: CardKey, verb: VerbSummary) -> ExerciseItem? {
        guard let tense = database.tense(session.lang, code: key.tense) else { return nil }
        return ExerciseFactory.item(key: key, verb: verb, tense: tense, table: table(verb), rng: &rng)
    }

    func conjugationTable(for verb: VerbSummary) -> ConjugationTable { table(verb) }

    /// Antwort zu einer Aufgabe verbuchen.
    func record(_ item: ExerciseItem, correct: Bool, context: ModelContext, now: Date = Date()) {
        let key = item.key.string
        if firstResults[key] == nil {
            firstResults[key] = correct
            let card: Card
            if let existing = cards[key] {
                card = existing
            } else {
                card = Card(profileID: profileID, key: item.key)
                context.insert(card)
                cards[key] = card
            }
            card.record(correct: correct, now: now)
        }
        if !correct, let again = makeItem(item.key, verb: item.verb) {
            repeats += 1
            steps.append(.single(again))
        }
    }

    func advance() {
        if index < steps.count { index += 1 }
    }
}
