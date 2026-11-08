import Foundation

/// Die drei Sprachen der App.
nonisolated enum Language: String, CaseIterable, Identifiable, Codable {
    case fr, it, en

    var id: String { rawValue }

    var name: String {
        switch self {
        case .fr: "Französisch"
        case .it: "Italienisch"
        case .en: "Englisch"
        }
    }

    var flag: String {
        switch self {
        case .fr: "🇫🇷"
        case .it: "🇮🇹"
        case .en: "🇬🇧"
        }
    }

    var shortName: String { rawValue.uppercased() }

    /// Zeichen für die Akzentleiste über der Tastatur.
    var accentKeys: [String] {
        switch self {
        case .fr: ["é", "è", "ê", "à", "â", "ç", "î", "ï", "ô", "û", "ù", "ë", "œ", "'"]
        case .it: ["à", "è", "é", "ì", "ò", "ù", "'"]
        case .en: ["'"]
        }
    }

    /// Einleitende Konjunktion im Subjunktiv, die beim Eintippen weggelassen werden darf.
    var subjunctiveConjunctions: [String] {
        switch self {
        case .fr: ["que ", "qu'"]
        case .it: ["che "]
        case .en: []
        }
    }

    /// Code der Stammformen-«Zeitform» (nur Englisch).
    static let principalParts = "principal_parts"
}
