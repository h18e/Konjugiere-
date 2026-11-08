import Foundation

/// Eine Zeile, wie sie in der Konjugationstabelle angezeigt wird.
/// Männliche und weibliche Formen werden zusammengefasst: «je suis allé(e)», «io sono andato/a».
nonisolated struct DisplayLine: Identifiable, Hashable {
    let id: String
    let pronoun: String
    let form: String
    let alternatives: [String]
    let irregular: Bool
    /// Die zugrunde liegenden Zeilen (für «Fehler melden»)
    let rows: [FormRow]
}

nonisolated enum FormDisplay {
    static func lines(_ rows: [FormRow]) -> [DisplayLine] {
        var order: [String] = []
        var groups: [String: [FormRow]] = [:]
        for row in rows {
            let key = row.person ?? "-"
            if groups[key] == nil { order.append(key) }
            groups[key, default: []].append(row)
        }
        return order.map { key in
            let group = groups[key]!
            let m = group.first { $0.gender == "m" }
            let f = group.first { $0.gender == "f" }
            if let m, let f, group.count == 2 {
                return DisplayLine(
                    id: key, pronoun: combinePronouns(m.pronoun, f.pronoun), form: combineGender(m.form, f.form),
                    alternatives: unique(m.alternatives + f.alternatives), irregular: m.irregular || f.irregular,
                    rows: group)
            }
            let r = group[0]
            return DisplayLine(id: key + (r.gender ?? ""), pronoun: r.pronoun, form: r.form,
                               alternatives: r.alternatives, irregular: r.irregular, rows: group)
        }
    }

    /// «allé» + «allée» → «allé(e)» ; «allés» + «allées» → «allé(e)s» ; «andato» + «andata» → «andato/a»
    static func combineGender(_ m: String, _ f: String) -> String {
        if m == f { return m }
        let prefix = String(m.commonPrefix(with: f))
        let sm = String(m.dropFirst(prefix.count))
        let sf = String(f.dropFirst(prefix.count))
        if sm.isEmpty { return "\(prefix)(\(sf))" }
        if sf.hasSuffix(sm) { return "\(prefix)(\(sf.dropLast(sm.count)))\(sm)" }
        if !sm.contains(" ") && !sf.contains(" ") { return "\(m)/\(sf)" }
        return "\(m) / \(f)"
    }

    /// «il» + «elle» → «il/elle» ; gleiche Pronomen bleiben einfach.
    static func combinePronouns(_ m: String, _ f: String) -> String {
        m == f ? m : "\(m)/\(f)"
    }

    private static func unique(_ items: [String]) -> [String] {
        var seen: [String] = []
        for i in items where !seen.contains(i) { seen.append(i) }
        return seen
    }
}
