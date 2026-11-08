import Foundation

nonisolated enum AnswerResult: Equatable {
    case correct
    /// Nur Akzente falsch oder fehlend – zählt als falsch (strenge Prüfung, Q16).
    case accentOnly
    case wrong

    var countsAsCorrect: Bool { self == .correct }
}

/// Prüft eingetippte Antworten. Reine Funktionen, ohne Oberfläche testbar.
nonisolated enum AnswerChecker {
    /// - Parameter accepted: alle zulässigen Antworten, die erste ist die Musterlösung.
    static func check(_ input: String, accepted: [String]) -> AnswerResult {
        let given = TextNormalizer.answer(input)
        guard !given.isEmpty else { return .wrong }
        let normalized = accepted.map(TextNormalizer.answer)
        if normalized.contains(given) { return .correct }
        let folded = TextNormalizer.foldDiacritics(given)
        if normalized.contains(where: { TextNormalizer.foldDiacritics($0) == folded }) { return .accentOnly }
        return .wrong
    }

    /// Markiert in der Musterlösung die Zeichen, die in der Eingabe fehlen oder abweichen.
    /// Grundlage ist die längste gemeinsame Teilfolge (LCS) der Zeichen.
    static func diff(input: String, expected: String) -> [DiffSegment] {
        let a = Array(TextNormalizer.answer(input))
        let b = Array(expected)
        let bNorm = Array(TextNormalizer.answer(expected))
        guard bNorm.count == b.count else {
            // Musterlösung enthält Zeichen, die das Normalisieren verändert: ganze Lösung markieren
            return [DiffSegment(text: expected, matches: false)]
        }
        let n = a.count, m = b.count
        var lcs = Array(repeating: Array(repeating: 0, count: m + 1), count: n + 1)
        if n > 0 && m > 0 {
            for i in stride(from: n - 1, through: 0, by: -1) {
                for j in stride(from: m - 1, through: 0, by: -1) {
                    lcs[i][j] = a[i] == bNorm[j] ? lcs[i + 1][j + 1] + 1 : max(lcs[i + 1][j], lcs[i][j + 1])
                }
            }
        }
        var matched = Array(repeating: false, count: m)
        var i = 0, j = 0
        while i < n && j < m {
            if a[i] == bNorm[j] {
                matched[j] = true
                i += 1; j += 1
            } else if lcs[i + 1][j] >= lcs[i][j + 1] {
                i += 1
            } else {
                j += 1
            }
        }
        var segments: [DiffSegment] = []
        for (index, char) in b.enumerated() {
            let ok = matched[index]
            if let last = segments.last, last.matches == ok {
                segments[segments.count - 1].text.append(char)
            } else {
                segments.append(DiffSegment(text: String(char), matches: ok))
            }
        }
        return segments
    }
}

nonisolated struct DiffSegment: Equatable {
    var text: String
    var matches: Bool
}
