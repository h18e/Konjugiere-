import Foundation
import Testing
@testable import Konjugiere

/// Prüft die mitgelieferte Datenbank (data/build/konjugiere.sqlite).
@MainActor
struct DatabaseTests {
    let db: VerbDatabase

    init() throws { db = try VerbDatabase.bundled() }

    @Test func searchFindsConjugatedForm() {
        let names = db.search(.fr, query: "suis").map(\.infinitive)
        #expect(names.contains("être"))
        #expect(names.contains("suivre"))
    }

    @Test func searchFindsGermanMeaning() {
        #expect(db.search(.fr, query: "folgen").map(\.infinitive).contains("suivre"))
    }

    @Test func searchIgnoresAccentsAndPronouns() {
        #expect(db.search(.fr, query: "etre").first?.infinitive == "être")
        #expect(db.search(.fr, query: "j'ai").map(\.infinitive).contains("avoir"))
    }

    @Test func frenchTableHasCompoundTenses() throws {
        let aller = try #require(db.verbs(.fr, infinitive: "aller").first)
        #expect(aller.auxiliary == "être")
        let table = db.table(for: aller)
        #expect(table.rows(for: "present").contains { $0.form == "vais" })
        #expect(table.rows(for: "passe_compose").contains { $0.form == "suis allée" })
    }

    @Test func italianAndEnglish() throws {
        let essere = try #require(db.verbs(.it, infinitive: "essere").first)
        #expect(db.table(for: essere).rows(for: "presente").contains { $0.form == "sono" })
        let go = try #require(db.verb(.en, key: "go"))
        #expect(db.table(for: go).rows(for: Language.principalParts).map(\.form).contains("went"))
        #expect(db.verbs(.en, infinitive: "lie").count == 2)
    }

    @Test func englishPracticesOnlyPrincipalParts() {
        let practicable = db.tenses(.en).filter(\.practicable).map(\.code)
        #expect(practicable == [Language.principalParts])
    }

    @Test func packagesHaveVerbs() {
        for lang in Language.allCases {
            let packages = db.packages(lang)
            #expect(!packages.isEmpty)
            for p in packages { #expect(!db.verbs(in: p).isEmpty, "\(p.title)") }
        }
    }
}
