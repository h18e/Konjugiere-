import Foundation

nonisolated enum TextNormalizer {
    /// Für die Suche: klein, ohne Akzente, ein einheitlicher Apostroph.
    /// Muss zu `normalize` im Datenskript passen (data/pipeline/model.py).
    static func search(_ text: String) -> String {
        foldDiacritics(unifyApostrophes(text).lowercased())
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Für den Antwortvergleich: Akzente bleiben, alles andere wird toleriert
    /// (Gross-/Kleinschreibung, Leerzeichen, Apostroph-Varianten, Leerzeichen nach dem Apostroph).
    static func answer(_ text: String) -> String {
        var s = unifyApostrophes(text).lowercased()
        s = s.split(whereSeparator: { $0.isWhitespace }).joined(separator: " ")
        s = s.replacingOccurrences(of: "' ", with: "'")
        s = s.replacingOccurrences(of: " '", with: "'")
        return s
    }

    static func foldDiacritics(_ text: String) -> String {
        text.folding(options: .diacriticInsensitive, locale: nil)
    }

    static func unifyApostrophes(_ text: String) -> String {
        text.replacingOccurrences(of: "’", with: "'")
            .replacingOccurrences(of: "‘", with: "'")
            .replacingOccurrences(of: "`", with: "'")
            .replacingOccurrences(of: "´", with: "'")
    }

    /// Pronomen und Form zusammensetzen: «j'» + «aime» → «j'aime», «je» + «suis» → «je suis».
    static func fullAnswer(pronoun: String, form: String) -> String {
        if pronoun.isEmpty { return form }
        if pronoun.hasSuffix("'") { return pronoun + form }
        return pronoun + " " + form
    }
}
