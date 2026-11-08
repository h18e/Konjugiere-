# Release (TestFlight / App Store)

Checkliste der Punkte, die nur du erledigen kannst. Stand: 8. November 2026.

| Punkt | Status |
|---|---|
| Team-ID in `Config/Local.xcconfig` | ✅ |
| App-Icon 1024 × 1024 px, ohne Alphakanal | ✅ |
| Exportkonformität (Verschlüsselung) | ✅ im Projekt hinterlegt (`ITSAppUsesNonExemptEncryption = NO`) |
| Erster Build in App Store Connect | ✅ Build 1 hochgeladen |
| TestFlight: interne Tester (Familie) einladen | ⏳ |
| Datenschutzerklärung (PRIVACY.md) und Support-URL | ⏳ erst für den App Store nötig |
| App-Store-Texte und Screenshots | ⏳ erst für den App Store nötig |

## Neuen Build hochladen
1. `git pull` (falls Claude etwas geändert hat).
2. In Xcode oben als Ziel **Any iOS Device (arm64)** wählen.
3. **Product → Archive**.
4. Im Fenster «Organizer» den neuen Eintrag wählen → **Distribute App** → **App Store Connect** → **Upload** → durchklicken.
5. Nach 5–30 Minuten erscheint der Build in App Store Connect unter **TestFlight**.

**Wichtig:** Jeder Upload braucht eine höhere Build-Nummer (Xcode: Target **Konjugiere** → **General** → **Build**). Claude erhöht sie bei Änderungen mit. Fehlermeldung bei doppelter Nummer: «The bundle version must be higher than the previously uploaded version».

## Exportkonformität
Die App verschlüsselt nichts selbst und baut keine Netzwerkverbindungen auf. Die richtige Antwort in App Store Connect ist deshalb **«None of the algorithms mentioned above»**. Ab Build 2 steht das im Projekt, und App Store Connect fragt nicht mehr.
