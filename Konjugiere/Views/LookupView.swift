import SwiftUI

/// Tab «Nachschlagen»: Suche links, Konjugationstabelle rechts (iPad) bzw. darunter (iPhone).
struct LookupView: View {
    @Environment(AppModel.self) private var model
    @State private var query = ""
    @State private var results: [VerbSummary] = []
    @State private var selection: VerbSummary?

    var body: some View {
        NavigationSplitView {
            List(results, selection: $selection) { verb in
                NavigationLink(value: verb) { VerbListRow(verb: verb) }
            }
            .overlay {
                if results.isEmpty && !query.isEmpty {
                    ContentUnavailableView.search(text: query)
                }
            }
            .searchable(text: $query, placement: .navigationBarDrawer(displayMode: .always),
                        prompt: "Verb, Form oder deutsche Bedeutung")
            .autocorrectionDisabled()
            .textInputAutocapitalization(.never)
            .navigationTitle("Nachschlagen")
            .toolbar { ToolbarItem(placement: .principal) { LanguagePicker() } }
            .task(id: "\(model.language.rawValue)|\(query)") { runSearch() }
        } detail: {
            NavigationStack {
                if let selection {
                    VerbDetailView(verb: selection)
                } else {
                    ContentUnavailableView("Verb wählen", systemImage: "text.book.closed",
                                           description: Text("Suche nach einem Infinitiv, einer konjugierten Form wie «suis» oder einer deutschen Bedeutung wie «folgen»."))
                }
            }
            .navigationDestination(for: VerbSummary.self) { VerbDetailView(verb: $0) }
        }
    }

    private func runSearch() {
        guard let db = model.database else { return }
        results = db.search(model.language, query: query)
        if let s = selection, s.lang != model.language { selection = nil }
    }
}

struct VerbListRow: View {
    let verb: VerbSummary

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack(spacing: 6) {
                Text(verb.infinitive).font(.body.weight(.medium))
                if verb.hasIrregular && verb.lang != .fr {
                    Image(systemName: "exclamationmark.circle").font(.caption).foregroundStyle(.orange)
                        .accessibilityLabel("unregelmässig")
                }
            }
            if !verb.gloss.isEmpty {
                Text(verb.gloss).font(.subheadline).foregroundStyle(.secondary).lineLimit(1)
            }
            if let note = verb.note {
                Text(note).font(.caption).foregroundStyle(.tertiary).lineLimit(1)
            }
        }
    }
}
