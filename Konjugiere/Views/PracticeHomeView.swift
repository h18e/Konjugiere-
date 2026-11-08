import SwiftData
import SwiftUI

/// Tab «Üben»: Heute fällig, Meine Verben, Lernpakete, freie Auswahl (Q19).
struct PracticeHomeView: View {
    @Environment(AppModel.self) private var model
    @Query private var cards: [Card]
    @Query(sort: \MyVerb.added) private var myVerbs: [MyVerb]
    @AppStorage(ExerciseMode.storageKey) private var mode: ExerciseMode = .typing
    @State private var session: PracticeSession?

    private var lang: Language { model.language }
    private var profileID: UUID? { model.profile?.id }

    private var myCards: [Card] { cards.filter { $0.profileID == profileID && $0.lang == lang.rawValue } }
    private var dueCount: Int { myCards.filter { Leitner.isDue($0.due, now: Date()) }.count }
    private var mine: [MyVerb] { myVerbs.filter { $0.profileID == profileID && $0.lang == lang.rawValue } }
    private var packages: [LearningPackage] { model.database?.packages(lang) ?? [] }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Picker("Übungsart", selection: $mode) {
                        ForEach(ExerciseMode.allCases) { Text($0.name).tag($0) }
                    }
                    .pickerStyle(.segmented)
                    .listRowBackground(Color.clear)
                }

                Section {
                    Button {
                        session = PracticeSession(title: "Heute fällig", lang: lang, verbs: [], dueOnly: true, mode: mode)
                    } label: {
                        StartRow(title: "Heute fällig", systemImage: "calendar.badge.clock",
                                 detail: dueCount == 0 ? "Nichts fällig" : "\(dueCount) Karten")
                    }
                    .disabled(dueCount == 0)

                    Button {
                        session = PracticeSession(title: "Meine Verben", lang: lang, verbs: myVerbSummaries(), mode: mode)
                    } label: {
                        StartRow(title: "Meine Verben", systemImage: "star",
                                 detail: mine.isEmpty ? "Noch keine – im Nachschlagen mit ☆ hinzufügen" : "\(mine.count) Verben")
                    }
                    .disabled(mine.isEmpty)

                    NavigationLink {
                        FreeSelectionView(mode: mode)
                    } label: {
                        Label("Freie Auswahl", systemImage: "slider.horizontal.3")
                    }
                }

                Section("Lernpakete") {
                    ForEach(packages) { package in
                        Button { start(package) } label: { PackageRow(package: package, level: model.profile?.level ?? 1) }
                    }
                }

                Section("Fortschritt") {
                    BoxStatsView(cards: myCards)
                }
            }
            .navigationTitle("Üben")
            .toolbar { ToolbarItem(placement: .principal) { LanguagePicker() } }
            .fullScreenCover(item: $session) { ExerciseSessionView(session: $0) }
        }
    }

    private func myVerbSummaries() -> [VerbSummary] {
        guard let db = model.database else { return [] }
        return mine.compactMap { db.verb(lang, key: $0.verbKey) }
    }

    private func start(_ package: LearningPackage) {
        guard let db = model.database else { return }
        session = PracticeSession(title: package.title, lang: lang, verbs: db.verbs(in: package),
                                  tenseCodes: package.tenses, mode: mode)
    }
}

private struct StartRow: View {
    let title: String
    let systemImage: String
    let detail: String

    var body: some View {
        HStack {
            Label(title, systemImage: systemImage)
            Spacer()
            Text(detail).font(.subheadline).foregroundStyle(.secondary).multilineTextAlignment(.trailing)
        }
    }
}

private struct PackageRow: View {
    let package: LearningPackage
    let level: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            HStack {
                Text(package.title).foregroundStyle(.primary)
                if package.level == level {
                    Text("empfohlen").font(.caption2.bold()).padding(.horizontal, 6).padding(.vertical, 2)
                        .background(.tint.opacity(0.15), in: Capsule())
                }
            }
            Text(package.description).font(.caption).foregroundStyle(.secondary)
            Text(Profile.levelNames[package.level] ?? "").font(.caption2).foregroundStyle(.tertiary)
        }
    }
}

/// Wie viele Karten in welchem Leitner-Fach liegen.
struct BoxStatsView: View {
    let cards: [Card]

    var body: some View {
        let counts = (1...Leitner.boxCount).map { box in cards.filter { $0.box == box }.count }
        let maxCount = max(1, counts.max() ?? 1)
        VStack(alignment: .leading, spacing: 8) {
            if cards.isEmpty {
                Text("Noch nichts geübt.").foregroundStyle(.secondary)
            } else {
                HStack(alignment: .bottom, spacing: 12) {
                    ForEach(0..<counts.count, id: \.self) { i in
                        VStack(spacing: 4) {
                            Text("\(counts[i])").font(.caption.monospacedDigit())
                            RoundedRectangle(cornerRadius: 4)
                                .fill(.tint.opacity(0.3 + 0.14 * Double(i)))
                                .frame(height: max(4, 60 * Double(counts[i]) / Double(maxCount)))
                            Text("Fach \(i + 1)").font(.caption2).foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity)
                    }
                }
                .accessibilityElement(children: .combine)
                Text("\(cards.count) Karten geübt · Fach 5 = sitzt").font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 4)
    }
}

/// Freie Auswahl: Verben suchen und Zeitformen wählen.
struct FreeSelectionView: View {
    let mode: ExerciseMode

    @Environment(AppModel.self) private var model
    @State private var query = ""
    @State private var results: [VerbSummary] = []
    @State private var chosen: [VerbSummary] = []
    @State private var tenseCodes: Set<String> = []
    @State private var session: PracticeSession?

    private var lang: Language { model.language }
    private var tenses: [Tense] { (model.database?.tenses(lang) ?? []).filter(\.practicable) }

    var body: some View {
        List {
            if !chosen.isEmpty {
                Section("Ausgewählt") {
                    ForEach(chosen) { v in
                        Button { toggle(v) } label: {
                            Label(v.infinitive, systemImage: "checkmark.circle.fill")
                        }
                    }
                }
            }
            Section("Zeitformen") {
                ForEach(tenses) { tense in
                    Toggle(isOn: Binding(get: { tenseCodes.contains(tense.code) },
                                         set: { if $0 { tenseCodes.insert(tense.code) } else { tenseCodes.remove(tense.code) } })) {
                        TenseLabel(tense: tense)
                    }
                }
            }
            Section(query.isEmpty ? "Häufige Verben" : "Treffer") {
                ForEach(results) { v in
                    Button { toggle(v) } label: {
                        HStack {
                            VerbListRow(verb: v).foregroundStyle(.primary)
                            Spacer()
                            Image(systemName: chosen.contains(v) ? "checkmark.circle.fill" : "circle")
                                .foregroundStyle(.tint)
                        }
                    }
                }
            }
        }
        .searchable(text: $query, prompt: "Verb suchen")
        .autocorrectionDisabled()
        .textInputAutocapitalization(.never)
        .navigationTitle("Freie Auswahl")
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("Starten") {
                    session = PracticeSession(title: "Freie Auswahl", lang: lang, verbs: chosen,
                                              tenseCodes: tenses.filter { tenseCodes.contains($0.code) }.map(\.code),
                                              mode: mode)
                }
                .disabled(chosen.isEmpty || tenseCodes.isEmpty)
            }
        }
        .task(id: "\(lang.rawValue)|\(query)") { search() }
        .onAppear(perform: resetTenses)
        .onChange(of: lang) { chosen = []; resetTenses() }
        .fullScreenCover(item: $session) { ExerciseSessionView(session: $0) }
    }

    private func resetTenses() {
        guard tenseCodes.isEmpty || !tenses.contains(where: { tenseCodes.contains($0.code) }) else { return }
        let all = model.database?.tenses(lang) ?? []
        tenseCodes = Set((model.profile?.activeTenses(lang, all: all) ?? []).map(\.code))
    }

    private func search() {
        guard let db = model.database else { return }
        results = query.isEmpty ? db.topVerbs(lang, limit: 100) : db.search(lang, query: query)
    }

    private func toggle(_ verb: VerbSummary) {
        if let i = chosen.firstIndex(of: verb) { chosen.remove(at: i) } else { chosen.append(verb) }
    }
}
