import SwiftData
import SwiftUI

struct RootView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.modelContext) private var context

    var body: some View {
        Group {
            if let error = model.loadError {
                ContentUnavailableView("Daten fehlen", systemImage: "exclamationmark.triangle",
                                       description: Text(error))
            } else if model.profile != nil {
                TabView {
                    Tab("Nachschlagen", systemImage: "book") { LookupView() }
                    Tab("Üben", systemImage: "pencil.and.list.clipboard") { PracticeHomeView() }
                    Tab("Einstellungen", systemImage: "gearshape") { SettingsView() }
                }
            } else {
                ProgressView()
            }
        }
        .onAppear { if model.profile == nil { model.bootstrap(context: context) } }
    }
}

/// Umschalter FR | IT | EN für die Symbolleiste.
struct LanguagePicker: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        Picker("Sprache", selection: $model.language) {
            ForEach(Language.allCases) { lang in
                Text("\(lang.flag) \(lang.shortName)").tag(lang)
            }
        }
        .pickerStyle(.segmented)
        .fixedSize()
    }
}
