import Foundation
import SQLite3

/// Schreibgeschützter Zugriff auf die Verbdaten (konjugiere.sqlite, mit der App ausgeliefert).
final class VerbDatabase {
    enum DatabaseError: LocalizedError {
        case missing
        case open(String)
        case query(String)

        var errorDescription: String? {
            switch self {
            case .missing: "Die Verbdatenbank fehlt im App-Paket (konjugiere.sqlite)."
            case .open(let msg): "Die Verbdatenbank lässt sich nicht öffnen: \(msg)"
            case .query(let msg): "Datenbankfehler: \(msg)"
            }
        }
    }

    nonisolated(unsafe) private var db: OpaquePointer?
    private var tenseCache: [Language: [Tense]] = [:]
    private var tableCache: [Int: ConjugationTable] = [:]

    init(url: URL) throws {
        var handle: OpaquePointer?
        let status = sqlite3_open_v2(url.path, &handle, SQLITE_OPEN_READONLY | SQLITE_OPEN_NOMUTEX, nil)
        guard status == SQLITE_OK, let handle else {
            let msg = handle.map { String(cString: sqlite3_errmsg($0)) } ?? "Code \(status)"
            sqlite3_close(handle)
            throw DatabaseError.open(msg)
        }
        db = handle
    }

    static func bundled() throws -> VerbDatabase {
        guard let url = Bundle.main.url(forResource: "konjugiere", withExtension: "sqlite") else {
            throw DatabaseError.missing
        }
        return try VerbDatabase(url: url)
    }

    deinit {
        sqlite3_close(db)
    }

    // MARK: - Abfragen

    func tenses(_ lang: Language) -> [Tense] {
        if let cached = tenseCache[lang] { return cached }
        let result = rows("""
            SELECT code, mood, name_native, name_de, sort, level, rare, personal
            FROM tense WHERE lang = ? ORDER BY sort
            """, [lang.rawValue]) { r in
            Tense(lang: lang, code: r.text(0), mood: r.text(1), nameNative: r.text(2), nameDE: r.text(3),
                  sort: r.int(4), level: r.int(5), rare: r.int(6) != 0, personal: r.int(7) != 0)
        }
        tenseCache[lang] = result
        return result
    }

    func tense(_ lang: Language, code: String) -> Tense? {
        tenses(lang).first { $0.code == code }
    }

    /// Suche nach Infinitiv, konjugierter Form oder deutscher Bedeutung (Präfixsuche).
    func search(_ lang: Language, query: String, limit: Int = 60) -> [VerbSummary] {
        let tokens = TextNormalizer.search(query)
            .replacingOccurrences(of: "'", with: "' ")          // «j'aime» → «j'», «aime»
            .split(separator: " ").map(String.init)
            .filter { !Self.ignoredTokens.contains($0) }
        guard let term = tokens.max(by: { $0.count < $1.count }), !term.isEmpty else {
            return topVerbs(lang, limit: limit)
        }
        return rows("""
            SELECT \(Self.verbColumns),
                   MIN(CASE WHEN s.term = ?1 THEN 0 ELSE 1 END) AS exact, MIN(s.kind) AS kind
            FROM search s JOIN verb v ON v.id = s.verb_id
            WHERE s.lang = ?2 AND s.term >= ?1 AND s.term < ?3
            GROUP BY v.id
            ORDER BY exact, kind, v.freq_rank IS NULL, v.freq_rank, v.reflexive_of IS NOT NULL, v.infinitive
            LIMIT ?4
            """, [term, lang.rawValue, term + "\u{FFFF}", limit], map: Self.summary)
    }

    /// Wörter, die beim Suchen nicht weiterhelfen («je suis» → «suis»).
    private static let ignoredTokens: Set<String> = [
        "je", "j'", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles", "que", "qu'",
        "io", "lui", "lei", "noi", "voi", "loro", "che",
        "i", "you", "he", "she", "it", "we", "they", "to",
    ]

    func topVerbs(_ lang: Language, limit: Int = 200) -> [VerbSummary] {
        rows("""
            SELECT \(Self.verbColumns) FROM verb v
            WHERE v.lang = ? AND v.freq_rank IS NOT NULL ORDER BY v.freq_rank LIMIT ?
            """, [lang.rawValue, limit], map: Self.summary)
    }

    func verb(_ lang: Language, key: String) -> VerbSummary? {
        rows("SELECT \(Self.verbColumns) FROM verb v WHERE v.lang = ? AND v.verb_key = ?",
             [lang.rawValue, key], map: Self.summary).first
    }

    func verbs(_ lang: Language, infinitive: String) -> [VerbSummary] {
        rows("SELECT \(Self.verbColumns) FROM verb v WHERE v.lang = ? AND v.infinitive = ? ORDER BY v.id",
             [lang.rawValue, infinitive], map: Self.summary)
    }

    /// Verben, die nach demselben Muster konjugiert werden.
    func verbs(_ lang: Language, model: String, limit: Int = 40) -> [VerbSummary] {
        rows("""
            SELECT \(Self.verbColumns) FROM verb v
            WHERE v.lang = ? AND v.model = ? AND v.reflexive_of IS NULL
            ORDER BY v.freq_rank IS NULL, v.freq_rank, v.infinitive LIMIT ?
            """, [lang.rawValue, model, limit], map: Self.summary)
    }

    /// Reflexive Varianten eines Verbs (lever → se lever).
    func reflexiveVariants(_ lang: Language, base: String) -> [VerbSummary] {
        rows("SELECT \(Self.verbColumns) FROM verb v WHERE v.lang = ? AND v.reflexive_of = ? ORDER BY v.infinitive",
             [lang.rawValue, base], map: Self.summary)
    }

    func table(for verb: VerbSummary) -> ConjugationTable {
        if let cached = tableCache[verb.id] { return cached }
        let blobs = rows("SELECT data FROM verb_table WHERE verb_id = ?", [verb.id]) { $0.blob(0) }
        var table = ConjugationTable(rows: [:])
        if let blob = blobs.first,
           let json = try? (blob as NSData).decompressed(using: .zlib) as Data,
           let decoded = try? JSONDecoder().decode([String: [FormRow]].self, from: json) {
            table = ConjugationTable(rows: decoded)
        }
        if tableCache.count > 200 { tableCache.removeAll() }
        tableCache[verb.id] = table
        return table
    }

    func packages(_ lang: Language) -> [LearningPackage] {
        rows("SELECT id, title, description, level, tenses FROM package WHERE lang = ? ORDER BY sort",
             [lang.rawValue]) { r in
            let tenses = r.textOrNil(4).flatMap { try? JSONDecoder().decode([String].self, from: Data($0.utf8)) }
            return LearningPackage(id: r.int(0), lang: lang, title: r.text(1), description: r.text(2),
                                   level: r.int(3), tenses: tenses)
        }
    }

    func verbs(in package: LearningPackage) -> [VerbSummary] {
        rows("""
            SELECT \(Self.verbColumns) FROM package_verb p JOIN verb v ON v.id = p.verb_id
            WHERE p.package_id = ? ORDER BY p.sort
            """, [package.id], map: Self.summary)
    }

    func sources() -> [SourceInfo] {
        rows("SELECT code, name, source, license, attribution FROM language ORDER BY rowid", []) { r in
            SourceInfo(lang: r.text(0), name: r.text(1), source: r.text(2), license: r.text(3), attribution: r.text(4))
        }
    }

    func meta(_ key: String) -> String? {
        rows("SELECT value FROM meta WHERE key = ?", [key]) { $0.text(0) }.first
    }

    // MARK: - Hilfsfunktionen

    private static let verbColumns = """
        v.id, v.lang, v.verb_key, v.infinitive, v.verb_group, v.auxiliary, v.model, v.reflexive_of, \
        v.freq_rank, v.gloss_de, v.note, v.has_irregular
        """

    private static func summary(_ r: Row) -> VerbSummary {
        VerbSummary(id: r.int(0), lang: Language(rawValue: r.text(1)) ?? .fr, key: r.text(2), infinitive: r.text(3),
                    group: r.textOrNil(4), auxiliary: r.textOrNil(5), model: r.textOrNil(6),
                    reflexiveOf: r.textOrNil(7), rank: r.intOrNil(8), gloss: r.text(9), note: r.textOrNil(10),
                    hasIrregular: r.int(11) != 0)
    }

    struct Row {
        let stmt: OpaquePointer

        func int(_ i: Int32) -> Int { Int(sqlite3_column_int64(stmt, i)) }
        func intOrNil(_ i: Int32) -> Int? { sqlite3_column_type(stmt, i) == SQLITE_NULL ? nil : int(i) }
        func text(_ i: Int32) -> String { textOrNil(i) ?? "" }
        func textOrNil(_ i: Int32) -> String? {
            guard let c = sqlite3_column_text(stmt, i) else { return nil }
            return String(cString: c)
        }
        func blob(_ i: Int32) -> Data {
            guard let bytes = sqlite3_column_blob(stmt, i) else { return Data() }
            return Data(bytes: bytes, count: Int(sqlite3_column_bytes(stmt, i)))
        }
    }

    private func rows<T>(_ sql: String, _ args: [Any], map: (Row) -> T) -> [T] {
        var stmt: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK, let stmt else {
            assertionFailure("SQL-Fehler: \(String(cString: sqlite3_errmsg(db)))")
            return []
        }
        defer { sqlite3_finalize(stmt) }
        // SQLITE_TRANSIENT: SQLite kopiert den Text sofort
        let transient = unsafeBitCast(-1, to: sqlite3_destructor_type.self)
        for (index, value) in args.enumerated() {
            let i = Int32(index + 1)
            switch value {
            case let v as Int: sqlite3_bind_int64(stmt, i, Int64(v))
            case let v as String: sqlite3_bind_text(stmt, i, v, -1, transient)
            default: sqlite3_bind_null(stmt, i)
            }
        }
        var result: [T] = []
        while sqlite3_step(stmt) == SQLITE_ROW {
            result.append(map(Row(stmt: stmt)))
        }
        return result
    }
}
