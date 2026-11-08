import SwiftData
import SwiftUI

@main
struct KonjugiereApp: App {
    @State private var model = AppModel()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(model)
        }
        .modelContainer(for: [Profile.self, Card.self, MyVerb.self, ErrorReport.self])
    }
}
