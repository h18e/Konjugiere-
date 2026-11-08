import SwiftData
import SwiftUI

/// Konjugationstabelle eines Verbs mit Zusatzinfos (Q25, Q26).
struct VerbDetailView: View {
    let verb: VerbSummary

    @Environment(AppModel.self) private var model
    @Environment(\.modelContext) private var context
    @Query private var myVerbs: [MyVerb]

    @State private var table = ConjugationTable(rows: [:])
    @State private var expanded: Set<String> = []
    @State private var related: [VerbSummary] = []
    @State private var samePattern: [VerbSummary] = []
    @State private var modelVerb: VerbSummary?
    @State private var reportTarget: ReportTarget?
    @State private var session: PracticeSession?

    private var tenses: [Tense] { model.database?.tenses(verb.lang) ?? [] }

    private var isMine: Bool {
        myVerbs.contains { $0.profileID == model.profile?.id && $0.lang == verb.lang.rawValue && $0.verbKey == verb.key }
    }

    var body: some View {
        List {
            header
            ForEach(moods, id: \.self) { mood in
                Section(mood) {
                    ForEach(tenses.filter { $0.mood == mood && !table.rows(for: $0.code).isEmpty }) { tense in
                        DisclosureGroup(isExpanded: binding(for: tense)) {
                            ForEach(FormDisplay.lines(table.rows(for: tense.code))) { line in
                                FormLineView(line: line, lang: verb.lang)
                                    .contextMenu {
                                        Button("Als fehlerhaft melden", systemImage: "exclamationmark.bubble") {
                                            reportTarget = ReportTarget(tense: tense, line: line)
                                        }
                                    }
                            }
                        } label: {
                            TenseLabel(tense: tense)
                        }
                    }
                }
            }
            if !related.isEmpty {
                Section(verb.reflexiveOf == nil ? "Reflexive Variante" : "Grundverb") {
                    ForEach(related) { v in NavigationLink(value: v) { VerbListRow(verb: v) } }
                }
            }
            if !samePattern.isEmpty {
                Section("Verben mit demselben Muster") {
                    ForEach(samePattern) { v in NavigationLink(value: v) { VerbListRow(verb: v) } }
                }
            }
        }
        .navigationTitle(verb.infinitive)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .primaryAction) {
                Button(isMine ? "Aus Meine Verben entfernen" : "Zu Meine Verben hinzufügen",
                       systemImage: isMine ? "star.fill" : "star", action: toggleMine)
                Button("Üben", systemImage: "play.fill") {
                    session = PracticeSession(title: verb.infinitive, lang: verb.lang, verbs: [verb])
                }
            }
        }
        .sheet(item: $reportTarget) { target in
            ReportErrorSheet(verb: verb, target: target)
        }
        .fullScreenCover(item: $session) { s in ExerciseSessionView(session: s) }
        .task(id: verb.id) { load() }
    }

    private var header: some View {
        Section {
            VStack(alignment: .leading, spacing: 8) {
                Text(verb.infinitive).font(.largeTitle.bold())
                if !verb.gloss.isEmpty {
                    Text(verb.gloss).font(.title3).foregroundStyle(.secondary)
                }
                if let note = verb.note {
                    Text(note).font(.footnote).foregroundStyle(.secondary)
                }
                FlowChips(items: chips)
                if let modelVerb {
                    NavigationLink(value: modelVerb) {
                        Label("wird konjugiert wie **\(modelVerb.infinitive)**", systemImage: "arrow.triangle.branch")
                    }
                    .font(.subheadline)
                }
            }
            .padding(.vertical, 4)
        }
    }

    private var chips: [String] {
        var items: [String] = []
        if let aux = verb.auxiliaryLabel { items.append("Hilfsverb: \(aux)") }
        if let group = verb.groupLabel { items.append(group) }
        if verb.reflexiveOf != nil { items.append("reflexiv") }
        return items
    }

    private var moods: [String] {
        var seen: [String] = []
        for t in tenses where !seen.contains(t.mood) && !table.rows(for: t.code).isEmpty { seen.append(t.mood) }
        return seen
    }

    private func binding(for tense: Tense) -> Binding<Bool> {
        Binding(get: { expanded.contains(tense.code) },
                set: { if $0 { expanded.insert(tense.code) } else { expanded.remove(tense.code) } })
    }

    private func load() {
        guard let db = model.database else { return }
        table = db.table(for: verb)
        expanded = Set(tenses.filter { !$0.rare }.map(\.code))
        if let base = verb.reflexiveOf {
            related = db.verbs(verb.lang, infinitive: base)
        } else {
            related = db.reflexiveVariants(verb.lang, base: verb.infinitive)
        }
        if let m = verb.model {
            samePattern = db.verbs(verb.lang, model: m).filter { $0.id != verb.id && $0.infinitive != verb.reflexiveOf }
            modelVerb = m == verb.infinitive || m == verb.reflexiveOf ? nil : db.verbs(verb.lang, infinitive: m).first
        } else {
            samePattern = []
            modelVerb = nil
        }
    }

    private func toggleMine() {
        guard let profile = model.profile else { return }
        if let existing = myVerbs.first(where: {
            $0.profileID == profile.id && $0.lang == verb.lang.rawValue && $0.verbKey == verb.key }) {
            context.delete(existing)
        } else {
            context.insert(MyVerb(profileID: profile.id, verb: verb))
        }
    }
}

struct TenseLabel: View {
    let tense: Tense

    var body: some View {
        VStack(alignment: .leading, spacing: 1) {
            Text(tense.nameNative).font(.headline)
            Text(tense.nameDE).font(.caption).foregroundStyle(.secondary)
        }
    }
}

struct FormLineView: View {
    let line: DisplayLine
    let lang: Language

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            (Text(line.pronoun.isEmpty ? "" : line.pronoun + (line.pronoun.hasSuffix("'") ? "" : " "))
                .foregroundStyle(.secondary)
             + Text(line.form)
                .foregroundStyle(line.irregular ? Color.orange : Color.primary)
                .fontWeight(line.irregular ? .semibold : .regular))
                .font(.body)
            if !line.alternatives.isEmpty {
                Text("auch: " + line.alternatives.joined(separator: ", "))
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
        .textSelection(.enabled)
        .accessibilityElement(children: .combine)
        .accessibilityHint(line.irregular ? "unregelmässig" : "")
    }
}

/// Einfache Reihe von Hinweis-Kärtchen, die bei Platzmangel umbricht.
struct FlowChips: View {
    let items: [String]

    var body: some View {
        ViewThatFits(in: .horizontal) {
            HStack(spacing: 6) { chipViews }
            VStack(alignment: .leading, spacing: 6) { chipViews }
        }
    }

    private var chipViews: some View {
        ForEach(items, id: \.self) { item in
            Text(item)
                .font(.caption.weight(.medium))
                .padding(.horizontal, 8).padding(.vertical, 4)
                .background(.tint.opacity(0.12), in: Capsule())
        }
    }
}

struct ReportTarget: Identifiable {
    let tense: Tense
    let line: DisplayLine
    var id: String { tense.code + line.id }
}

/// «Form als fehlerhaft melden» (Q28)
struct ReportErrorSheet: View {
    let verb: VerbSummary
    let target: ReportTarget

    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    @State private var note = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Gemeldete Form") {
                    LabeledContent("Verb", value: verb.infinitive)
                    LabeledContent("Zeitform", value: target.tense.nameNative)
                    Text(TextNormalizer.fullAnswer(pronoun: target.line.pronoun, form: target.line.form))
                        .font(.headline)
                }
                Section {
                    TextField("Was stimmt nicht? Wie wäre es richtig?", text: $note, axis: .vertical)
                        .lineLimit(3...6)
                } footer: {
                    Text("Meldungen sammeln sich unter Einstellungen → Fehlermeldungen. Von dort kannst du sie als Text an Claude schicken.")
                }
            }
            .navigationTitle("Fehler melden")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Abbrechen") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Melden") {
                        for row in target.line.rows {
                            context.insert(ErrorReport(verb: verb, tense: target.tense.code, row: row, note: note))
                        }
                        dismiss()
                    }
                }
            }
        }
        .presentationDetents([.medium, .large])
    }
}
