import Foundation

/// Leitner-System mit 5 Fächern (Q19).
/// Richtig → ein Fach weiter, falsch → zurück in Fach 1.
/// Fällig nach 1, 2, 4, 8 bzw. 16 Tagen, je nach Fach.
nonisolated enum Leitner {
    static let boxCount = 5
    static let intervals = [1, 2, 4, 8, 16]

    static func next(box: Int, correct: Bool, now: Date, calendar: Calendar = .current) -> (box: Int, due: Date) {
        let newBox = correct ? min(max(box, 1) + 1, boxCount) : 1
        let days = intervals[newBox - 1]
        let start = calendar.startOfDay(for: now)
        let due = calendar.date(byAdding: .day, value: days, to: start) ?? now
        return (newBox, due)
    }

    static func isDue(_ due: Date, now: Date) -> Bool { due <= now }
}
