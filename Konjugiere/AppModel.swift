import Foundation
import Observation
import SwiftData

/// Gemeinsamer Zustand der App: Verbdatenbank, aktives Profil, gewählte Sprache.
@Observable
final class AppModel {
    let database: VerbDatabase?
    let loadError: String?

    var profile: Profile?
    var language: Language = .fr {
        didSet { profile?.language = language }
    }

    private static let profileKey = "currentProfileID"

    init() {
        do {
            database = try VerbDatabase.bundled()
            loadError = nil
        } catch {
            database = nil
            loadError = error.localizedDescription
        }
    }

    /// Beim Start: gespeichertes Profil wählen oder ein erstes anlegen.
    func bootstrap(context: ModelContext) {
        let profiles = (try? context.fetch(FetchDescriptor<Profile>(sortBy: [SortDescriptor(\.created)]))) ?? []
        let storedID = UserDefaults.standard.string(forKey: Self.profileKey).flatMap(UUID.init)
        if let match = profiles.first(where: { $0.id == storedID }) ?? profiles.first {
            select(match)
        } else {
            let first = Profile(name: "Ich", level: 1)
            context.insert(first)
            select(first)
        }
    }

    func select(_ profile: Profile) {
        self.profile = profile
        UserDefaults.standard.set(profile.id.uuidString, forKey: Self.profileKey)
        language = profile.language
    }
}
