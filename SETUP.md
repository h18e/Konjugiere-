# Setup

## Voraussetzungen
- Mac mit Xcode (getestet mit Xcode 27.1)
- Python 3 (getestet mit 3.14 von python.org)
- Der Projektordner liegt **ausserhalb von iCloud Drive**, nämlich in `~/Developer/Konjugiere!`.

## Code holen
Claude macht alle Commits und Pushes. Du holst den neuesten Stand nur ab. Auf diesem Mac ist das nicht nötig, weil Claude direkt in deinem Projektordner arbeitet. Auf einem anderen Mac:

```bash
cd ~/Developer/'Konjugiere!' && git pull
```

Die Anmeldung bei GitHub läuft über einen Fine-grained Token mit Zugriff auf **Konjugiere-** und der Berechtigung **Contents: Read and write**. macOS speichert ihn im Schlüsselbund.

## Daten aufbereiten

Das musst du nur machen, wenn du die Datenbank neu erzeugen willst. Auf deinem Mac ist sie bereits erzeugt.

Öffne das Terminal (⌘-Leertaste, «Terminal» tippen, Return) und führe die Befehle nacheinander aus.

**1. In den Datenordner wechseln.** `cd` heisst «change directory». Die einfachen Anführungszeichen braucht es wegen des Ausrufezeichens im Ordnernamen. Doppelte Anführungszeichen funktionieren in zsh nicht.

```bash
cd ~/Developer/'Konjugiere!'/data
```

**2. Eine eigene Python-Umgebung anlegen und das Testwerkzeug installieren.** Das ist nur beim ersten Mal nötig.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
```

**3. Rohdaten herunterladen.** Das dauert einige Minuten. Rund 3,4 GB werden heruntergeladen, aber nur etwa 1,2 GB gespeichert, weil das Skript beim Herunterladen filtert.

```bash
.venv/bin/python -m pipeline.fetch verbiste && .venv/bin/python -m pipeline.fetch frequency && .venv/bin/python -m pipeline.fetch dewiktionary && .venv/bin/python -m pipeline.fetch enwiktionary
```

**4. Kompakten Auszug erzeugen.**

```bash
.venv/bin/python -m pipeline.extract
```

**5. Tests laufen lassen.** Am Schluss muss «passed» stehen und kein «failed».

```bash
.venv/bin/python -m pytest -q tests
```

**6. Datenbank und Qualitätsbericht erzeugen.**

```bash
.venv/bin/python -m pipeline.build
```

Das Ergebnis liegt in `data/build/konjugiere.sqlite`, der Bericht in `docs/DATENQUALITAET.md`.

## Häufige Stolpersteine
| Meldung | Ursache / Lösung |
|---|---|
| `zsh: event not found` oder `dquote>` | Das Ausrufezeichen im Ordnernamen steht nicht in *einfachen* Anführungszeichen. Mit Control-C abbrechen und den Befehl genau so kopieren wie oben. |
| `No module named pytest` | Schritt 2 fehlt, oder du hast `python3` statt `.venv/bin/python` verwendet. |
| `CERTIFICATE_VERIFY_FAILED` | Tritt mit dem aktuellen Skript nicht mehr auf, weil das Herunterladen über `curl` läuft. Falls doch: Meldung an Claude schicken. |
| `FileNotFoundError: … raw/extract/…` | Schritt 4 fehlt. |
| `403` / `Permission … denied` beim Push | Der Token hat keinen Zugriff auf das Repo oder nur Lesezugriff. Auf GitHub die Token-Einstellungen prüfen, dann den gespeicherten Schlüssel löschen: `printf "protocol=https\nhost=github.com\n\n" \| git credential-osxkeychain erase`. |

## iOS-App

**Voraussetzung:** Die Datenbank `data/build/konjugiere.sqlite` existiert (Abschnitt «Daten aufbereiten»). Sie ist nicht in Git. Fehlt sie, bricht der Build mit «Build input file cannot be found: …konjugiere.sqlite» ab.

### 1. Signing einrichten (einmalig)
1. Im Terminal:
   ```bash
   cd ~/Developer/'Konjugiere!' && cp Config/Local.xcconfig.example Config/Local.xcconfig && open -e Config/Local.xcconfig
   ```
2. In TextEdit `ABCDE12345` durch deine Team-ID ersetzen und speichern (⌘S). Die Team-ID findest du in Xcode unter **Xcode → Settings… (⌘,) → Accounts**, dann dein Apple-Account und das Team auswählen. Die Team-ID steht auch auf developer.apple.com unter **Account → Membership details**.
3. Ist die Bundle-ID `ch.raphaelhess.konjugiere` schon vergeben, in derselben Datei die Zeile `KONJUGIERE_BUNDLE_ID = …` aktivieren (die `//` entfernen) und einen eigenen Namen eintragen.

`Local.xcconfig` ist nicht in Git, deshalb gibt es bei `git pull` keine Konflikte.

### 2. Starten
1. Öffnen:
   ```bash
   open ~/Developer/'Konjugiere!'/Konjugiere.xcodeproj
   ```
2. Oben in der Mitte das Ziel wählen: einen Simulator (z. B. «iPhone 18 Pro») oder dein iPhone am Kabel.
3. **⌘R** drücken.
4. Beim ersten Start auf einem echten iPhone: **Einstellungen → Allgemein → VPN & Geräteverwaltung →** dein Entwicklerprofil **→ Vertrauen**.

### 3. Tests
In Xcode **⌘U**. Oder im Terminal:
```bash
cd ~/Developer/'Konjugiere!' && xcodebuild -project Konjugiere.xcodeproj -scheme Konjugiere -destination 'platform=iOS Simulator,name=iPhone 18 Pro' test
```

### Stolpersteine iOS
| Meldung | Ursache / Lösung |
|---|---|
| «Signing for "Konjugiere" requires a development team» | Schritt 1 fehlt, oder die Team-ID in `Config/Local.xcconfig` ist falsch. Danach Xcode schliessen und neu öffnen. |
| «Build input file cannot be found: …konjugiere.sqlite» | Die Datenbank fehlt. Abschnitt «Daten aufbereiten» durchführen. |
| «Failed to register bundle identifier» | Die Bundle-ID ist vergeben. In `Local.xcconfig` eine eigene `KONJUGIERE_BUNDLE_ID` setzen. |
| «Unable to find a device matching …» | Den Simulator gibt es auf deinem Mac nicht. Einen anderen Namen aus der Liste oben in Xcode verwenden. |
