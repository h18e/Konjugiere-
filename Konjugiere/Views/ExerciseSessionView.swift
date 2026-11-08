import SwiftData
import SwiftUI

/// Eine Übungsrunde im Vollbild.
struct ExerciseSessionView: View {
    let session: PracticeSession

    @Environment(AppModel.self) private var model
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    @Query private var cards: [Card]
    @State private var engine: SessionEngine?

    var body: some View {
        NavigationStack {
            Group {
                if let engine {
                    if let step = engine.current {
                        StepView(engine: engine, step: step)
                            .id(step.id)
                    } else if engine.steps.isEmpty {
                        ContentUnavailableView("Nichts zu üben", systemImage: "checkmark.seal",
                                               description: Text(session.dueOnly
                                                   ? "Heute ist keine Karte fällig."
                                                   : "Für diese Auswahl gibt es keine übbaren Formen. Prüfe die Zeitformen in den Einstellungen."))
                    } else {
                        SummaryView(engine: engine) { dismiss() }
                    }
                } else {
                    ProgressView()
                }
            }
            .navigationTitle(session.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Beenden", systemImage: "xmark") { dismiss() }
                }
                if let engine, !engine.finished {
                    ToolbarItem(placement: .principal) {
                        ProgressView(value: engine.progress).frame(width: 140)
                    }
                }
            }
        }
        .onAppear(perform: start)
    }

    private func start() {
        guard engine == nil, let db = model.database, let profile = model.profile else { return }
        engine = SessionEngine(session: session, database: db, profile: profile, cards: cards)
    }
}

private struct StepView: View {
    let engine: SessionEngine
    let step: SessionEngine.Step

    var body: some View {
        switch step {
        case .single(let item):
            if engine.session.mode == .choice {
                ChoiceExerciseView(engine: engine, item: item)
            } else {
                TypingExerciseView(engine: engine, item: item)
            }
        case .table(let items):
            TableExerciseView(engine: engine, items: items)
        }
    }
}

/// Kopf einer Aufgabe: Verb, Bedeutung, Zeitform (Q22).
struct PromptHeader: View {
    let item: ExerciseItem

    var body: some View {
        VStack(spacing: 6) {
            Text(item.verb.infinitive).font(.largeTitle.bold())
            if !item.verb.gloss.isEmpty {
                Text(item.verb.gloss).font(.subheadline).foregroundStyle(.secondary).multilineTextAlignment(.center)
            }
            TenseLabel(tense: item.tense).multilineTextAlignment(.center)
                .padding(.top, 4)
        }
        .frame(maxWidth: .infinity)
    }
}

/// «elle ♀» / «Imperativ, 2. Person Singular»
struct PersonCue: View {
    let item: ExerciseItem

    var body: some View {
        HStack(spacing: 6) {
            if let label = item.personLabel {
                Text(label).font(.title3.weight(.medium))
            } else {
                Text(item.pronoun).font(.title2.weight(.semibold))
            }
            if let symbol = item.genderSymbol {
                Text(symbol).font(.title2).foregroundStyle(symbol == "♀" ? .pink : .blue)
                    .accessibilityLabel(symbol == "♀" ? "weiblich" : "männlich")
            }
        }
    }
}

// MARK: - Eintippen

private struct TypingExerciseView: View {
    let engine: SessionEngine
    let item: ExerciseItem

    @Environment(\.modelContext) private var context
    @State private var input = ""
    @State private var result: AnswerResult?
    @State private var showTable = false
    @FocusState private var focused: Bool

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                PromptHeader(item: item)
                PersonCue(item: item)
                TextField(item.pronoun.isEmpty ? "Form eintippen" : "\(item.pronoun) …", text: $input)
                    .font(.title2)
                    .multilineTextAlignment(.center)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .keyboardType(.alphabet)
                    .submitLabel(result == nil ? .done : .next)
                    .focused($focused)
                    .disabled(result != nil)
                    .padding(12)
                    .background(.fill.tertiary, in: RoundedRectangle(cornerRadius: 12))
                    .onSubmit(submitOrNext)
                    .toolbar {
                        ToolbarItemGroup(placement: .keyboard) {
                            AccentBar(keys: engine.session.lang.accentKeys) { input += $0 }
                        }
                    }
                if let result {
                    FeedbackView(result: result, input: input, solution: item.solution) { showTable = true }
                }
                Button(action: submitOrNext) {
                    Text(result == nil ? "Prüfen" : "Weiter").frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .disabled(result == nil && input.trimmingCharacters(in: .whitespaces).isEmpty)
            }
            .padding()
            .frame(maxWidth: 560)
            .frame(maxWidth: .infinity)
        }
        .onAppear { focused = true }
        .sheet(isPresented: $showTable) { TableSheet(engine: engine, item: item) }
    }

    private func submitOrNext() {
        if result == nil {
            guard !input.trimmingCharacters(in: .whitespaces).isEmpty else { return }
            let r = AnswerChecker.check(input, accepted: item.accepted)
            result = r
            engine.record(item, correct: r.countsAsCorrect, context: context)
            focused = true
        } else {
            engine.advance()
        }
    }
}

/// Akzentleiste über der Tastatur (Q16).
struct AccentBar: View {
    let keys: [String]
    let insert: (String) -> Void

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 4) {
                ForEach(keys, id: \.self) { key in
                    Button(key) { insert(key) }
                        .font(.title3)
                        .frame(minWidth: 34, minHeight: 34)
                        .buttonStyle(.bordered)
                }
            }
        }
    }
}

/// Sofortige Rückmeldung mit markierten Abweichungen (Q27).
struct FeedbackView: View {
    let result: AnswerResult
    let input: String
    let solution: String
    let showTable: () -> Void

    var body: some View {
        VStack(spacing: 10) {
            switch result {
            case .correct:
                Label("Richtig", systemImage: "checkmark.circle.fill").foregroundStyle(.green).font(.title3.bold())
            case .accentOnly:
                Label("Fast – nur der Akzent stimmt nicht", systemImage: "exclamationmark.circle.fill")
                    .foregroundStyle(.orange).font(.title3.bold())
            case .wrong:
                Label("Leider falsch", systemImage: "xmark.circle.fill").foregroundStyle(.red).font(.title3.bold())
            }
            if result != .correct {
                VStack(spacing: 4) {
                    Text("Richtig ist").font(.caption).foregroundStyle(.secondary)
                    diffText.font(.title2)
                }
                Button("Tabelle ansehen", systemImage: "tablecells", action: showTable)
                    .font(.subheadline)
            }
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(.fill.quaternary, in: RoundedRectangle(cornerRadius: 12))
    }

    private var diffText: Text {
        AnswerChecker.diff(input: input, expected: solution).reduce(Text("")) { text, segment in
            text + Text(segment.text)
                .foregroundStyle(segment.matches ? Color.primary : Color.red)
                .fontWeight(segment.matches ? .regular : .bold)
                .underline(!segment.matches)
        }
    }
}

/// Die Tabelle der geübten Zeitform zum Nachsehen.
private struct TableSheet: View {
    let engine: SessionEngine
    let item: ExerciseItem
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                Section {
                    ForEach(FormDisplay.lines(engine.conjugationTable(for: item.verb).rows(for: item.tense.code))) {
                        FormLineView(line: $0, lang: item.verb.lang)
                    }
                } header: {
                    TenseLabel(tense: item.tense)
                }
            }
            .navigationTitle(item.verb.infinitive)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Fertig") { dismiss() } } }
        }
        .presentationDetents([.medium, .large])
    }
}

// MARK: - Multiple Choice

private struct ChoiceExerciseView: View {
    let engine: SessionEngine
    let item: ExerciseItem

    @Environment(\.modelContext) private var context
    @State private var picked: String?
    @State private var showTable = false

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                PromptHeader(item: item)
                PersonCue(item: item)
                VStack(spacing: 10) {
                    ForEach(item.choices, id: \.self) { choice in
                        Button { pick(choice) } label: {
                            HStack {
                                Text(choice).font(.title3)
                                Spacer()
                                if let picked { marker(for: choice, picked: picked) }
                            }
                            .padding()
                            .frame(maxWidth: .infinity)
                            .background(background(for: choice), in: RoundedRectangle(cornerRadius: 12))
                        }
                        .buttonStyle(.plain)
                        .disabled(picked != nil)
                    }
                }
                if picked != nil {
                    if !isCorrect(picked!) {
                        Button("Tabelle ansehen", systemImage: "tablecells") { showTable = true }
                    }
                    Button { engine.advance() } label: { Text("Weiter").frame(maxWidth: .infinity) }
                        .buttonStyle(.borderedProminent).controlSize(.large)
                }
            }
            .padding()
            .frame(maxWidth: 560)
            .frame(maxWidth: .infinity)
        }
        .sheet(isPresented: $showTable) { TableSheet(engine: engine, item: item) }
    }

    private func isCorrect(_ choice: String) -> Bool { item.bareAccepted.contains(choice) }

    private func pick(_ choice: String) {
        picked = choice
        engine.record(item, correct: isCorrect(choice), context: context)
    }

    @ViewBuilder
    private func marker(for choice: String, picked: String) -> some View {
        if isCorrect(choice) {
            Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
        } else if choice == picked {
            Image(systemName: "xmark.circle.fill").foregroundStyle(.red)
        }
    }

    private func background(for choice: String) -> AnyShapeStyle {
        guard let picked else { return AnyShapeStyle(.fill.tertiary) }
        if isCorrect(choice) { return AnyShapeStyle(Color.green.opacity(0.2)) }
        if choice == picked { return AnyShapeStyle(Color.red.opacity(0.2)) }
        return AnyShapeStyle(.fill.quaternary)
    }
}

// MARK: - Ganze Tabelle

private struct TableExerciseView: View {
    let engine: SessionEngine
    let items: [ExerciseItem]

    @Environment(\.modelContext) private var context
    @State private var inputs: [String]
    @State private var results: [AnswerResult]?
    @FocusState private var focus: Int?

    init(engine: SessionEngine, items: [ExerciseItem]) {
        self.engine = engine
        self.items = items
        _inputs = State(initialValue: Array(repeating: "", count: items.count))
    }

    var body: some View {
        Form {
            Section {
                PromptHeader(item: items[0]).listRowBackground(Color.clear)
            }
            Section {
                ForEach(items.indices, id: \.self) { i in
                    row(i)
                }
            } footer: {
                Text("Mit oder ohne Pronomen eintippen.")
            }
            Section {
                Button(results == nil ? "Prüfen" : "Weiter") {
                    if results == nil { check() } else { engine.advance() }
                }
                .frame(maxWidth: .infinity)
                .bold()
            }
        }
        .toolbar {
            ToolbarItemGroup(placement: .keyboard) {
                AccentBar(keys: engine.session.lang.accentKeys) { key in
                    if let f = focus { inputs[f] += key }
                }
            }
        }
        .onAppear { focus = 0 }
    }

    @ViewBuilder
    private func row(_ i: Int) -> some View {
        let item = items[i]
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Group {
                    if let label = item.personLabel { Text(label).font(.caption) } else { Text(item.pronoun) }
                }
                .foregroundStyle(.secondary)
                .frame(minWidth: 70, alignment: .leading)
                if let s = item.genderSymbol { Text(s).foregroundStyle(s == "♀" ? .pink : .blue) }
                TextField("", text: $inputs[i])
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .focused($focus, equals: i)
                    .submitLabel(i == items.count - 1 ? .done : .next)
                    .onSubmit { focus = i + 1 < items.count ? i + 1 : nil }
                    .disabled(results != nil)
                if let r = results?[i] {
                    Image(systemName: r == .correct ? "checkmark.circle.fill"
                          : r == .accentOnly ? "exclamationmark.circle.fill" : "xmark.circle.fill")
                        .foregroundStyle(r == .correct ? .green : r == .accentOnly ? .orange : .red)
                }
            }
            if let r = results?[i], r != .correct {
                Text(item.bareForm).font(.callout.bold()).foregroundStyle(.red)
            }
        }
    }

    private func check() {
        let r = items.indices.map { i in
            AnswerChecker.check(inputs[i], accepted: items[i].accepted + items[i].bareAccepted)
        }
        results = r
        for (i, item) in items.enumerated() {
            engine.record(item, correct: r[i].countsAsCorrect, context: context)
        }
        focus = nil
    }
}

// MARK: - Abschluss

private struct SummaryView: View {
    let engine: SessionEngine
    let done: () -> Void

    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "flag.checkered").font(.system(size: 56)).foregroundStyle(.tint)
            Text("Runde fertig").font(.largeTitle.bold())
            let total = engine.firstResults.count
            Text("\(engine.correctFirstTry) von \(total) beim ersten Versuch richtig")
                .font(.title3)
            if engine.repeats > 0 {
                Text("\(engine.repeats) Wiederholungen am Schluss").foregroundStyle(.secondary)
            }
            Button("Fertig", action: done).buttonStyle(.borderedProminent).controlSize(.large)
        }
        .padding()
    }
}
