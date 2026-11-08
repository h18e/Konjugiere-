import SwiftData
import SwiftUI

/// Tab «Einstellungen»: Profil, Zeitformen, Profile, Fehlermeldungen, Quellen.
struct SettingsView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.modelContext) private var context
    @Query(sort: \Profile.created) private var profiles: [Profile]
    @Query(sort: \ErrorReport.created) private var reports: [ErrorReport]
    @State private var showNewProfile = false
    @State private var confirmDeleteReports = false

    var body: some View {
        NavigationStack {
            Form {
                if let profile = model.profile {
                    ProfileSection(profile: profile)
                    Section {
                        ForEach(Language.allCases) { lang in
                            NavigationLink {
                                TenseSettingsView(profile: profile, lang: lang)
                            } label: {
                                LabeledContent("\(lang.flag) \(lang.name)",
                                               value: profile.hasCustomTenses(lang) ? "eigene Auswahl" : "nach Stufe")
                            }
                        }
                    } header: {
                        Text("Zeitformen zum Üben")
                    } footer: {
                        Text("Ohne eigene Auswahl gelten alle Zeitformen bis zur Stufe des Profils. Englisch übt die Stammformen (go – went – gone).")
                    }
                }

                Section("Profile") {
                    ForEach(profiles) { p in
                        Button { model.select(p) } label: {
                            HStack {
                                VStack(alignment: .leading) {
                                    Text(p.name.isEmpty ? "Ohne Namen" : p.name).foregroundStyle(.primary)
                                    Text(p.levelName).font(.caption).foregroundStyle(.secondary)
                                }
                                Spacer()
                                if p.id == model.profile?.id { Image(systemName: "checkmark").foregroundStyle(.tint) }
                            }
                        }
                        .deleteDisabled(p.id == model.profile?.id)
                    }
                    .onDelete(perform: deleteProfiles)
                    Button("Profil hinzufügen", systemImage: "person.badge.plus") { showNewProfile = true }
                }

                Section {
                    if reports.isEmpty {
                        Text("Keine Meldungen").foregroundStyle(.secondary)
                    } else {
                        ForEach(reports) { r in
                            VStack(alignment: .leading, spacing: 2) {
                                Text("\(r.infinitive) · \(r.shownForm)")
                                if !r.note.isEmpty { Text(r.note).font(.caption).foregroundStyle(.secondary) }
                            }
                        }
                        .onDelete { offsets in offsets.map { reports[$0] }.forEach(context.delete) }
                        ShareLink(item: ErrorExport.text(reports)) {
                            Label("Als Text teilen", systemImage: "square.and.arrow.up")
                        }
                        Button("Alle löschen", systemImage: "trash", role: .destructive) { confirmDeleteReports = true }
                    }
                } header: {
                    Text("Fehlermeldungen")
                } footer: {
                    Text("Eine Form meldest du im Nachschlagen: lange auf die Form drücken → «Als fehlerhaft melden».")
                }

                Section("Daten und Lizenzen") {
                    ForEach(model.database?.sources() ?? []) { s in
                        VStack(alignment: .leading, spacing: 2) {
                            Text(s.name).font(.subheadline.weight(.medium))
                            Text(s.source).font(.caption)
                            Text(s.license).font(.caption).foregroundStyle(.secondary)
                            if !s.attribution.isEmpty { Text(s.attribution).font(.caption2).foregroundStyle(.secondary) }
                        }
                    }
                    if let built = model.database?.meta("built") {
                        LabeledContent("Datenstand", value: built)
                    }
                    LabeledContent("Version", value: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "–")
                }
            }
            .navigationTitle("Einstellungen")
            .sheet(isPresented: $showNewProfile) { NewProfileSheet() }
            .confirmationDialog("Alle Fehlermeldungen löschen?", isPresented: $confirmDeleteReports,
                                titleVisibility: .visible) {
                Button("Löschen", role: .destructive) { reports.forEach(context.delete) }
            }
        }
    }

    /// Löscht Profile samt Karten und «Meine Verben».
    private func deleteProfiles(_ offsets: IndexSet) {
        for p in offsets.map({ profiles[$0] }) where p.id != model.profile?.id {
            let id = p.id
            try? context.delete(model: Card.self, where: #Predicate { $0.profileID == id })
            try? context.delete(model: MyVerb.self, where: #Predicate { $0.profileID == id })
            context.delete(p)
        }
    }
}

private struct ProfileSection: View {
    @Bindable var profile: Profile

    var body: some View {
        Section("Aktives Profil") {
            TextField("Name", text: $profile.name)
            Picker("Stufe", selection: $profile.level) {
                ForEach(1...3, id: \.self) { Text(Profile.levelNames[$0]!).tag($0) }
            }
            Stepper("Karten pro Runde: \(profile.roundLength)", value: $profile.roundLength, in: 5...50, step: 5)
        }
    }
}

private struct TenseSettingsView: View {
    @Bindable var profile: Profile
    let lang: Language
    @Environment(AppModel.self) private var model

    private var all: [Tense] { model.database?.tenses(lang) ?? [] }

    var body: some View {
        let active = Set(profile.activeTenses(lang, all: all).map(\.code))
        Form {
            Section {
                ForEach(all.filter(\.practicable)) { tense in
                    Toggle(isOn: Binding(get: { active.contains(tense.code) },
                                         set: { profile.setTense(tense, active: $0, all: all) })) {
                        HStack {
                            TenseLabel(tense: tense)
                            Spacer()
                            Text(Profile.levelNames[tense.level] ?? "").font(.caption2).foregroundStyle(.tertiary)
                        }
                    }
                }
            }
            if profile.hasCustomTenses(lang) {
                Section {
                    Button("Auf Stufe «\(profile.levelName)» zurücksetzen") { profile.resetTenses(lang) }
                }
            }
        }
        .navigationTitle("\(lang.flag) Zeitformen")
    }
}

private struct NewProfileSheet: View {
    @Environment(AppModel.self) private var model
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var level = 1

    var body: some View {
        NavigationStack {
            Form {
                TextField("Name", text: $name)
                Picker("Stufe", selection: $level) {
                    ForEach(1...3, id: \.self) { Text(Profile.levelNames[$0]!).tag($0) }
                }
                .pickerStyle(.inline)
            }
            .navigationTitle("Neues Profil")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Abbrechen") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Anlegen") {
                        let p = Profile(name: name.trimmingCharacters(in: .whitespaces), level: level)
                        context.insert(p)
                        model.select(p)
                        dismiss()
                    }
                    .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
        .presentationDetents([.medium])
    }
}
