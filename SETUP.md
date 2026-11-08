# Setup

## Voraussetzungen
- Mac mit Xcode (getestet mit Xcode 27.1)
- Python 3 (getestet mit 3.14 von python.org)
- Der Projektordner liegt **ausserhalb von iCloud Drive**, nämlich in `~/Developer/Konjugiere!`.

## Daten aufbereiten

Das musst du nur machen, wenn du die Datenbank neu erzeugen willst. Auf deinem Mac ist sie bereits erzeugt.

Öffne das Terminal (⌘-Leertaste, «Terminal» tippen, Return) und führe die Befehle nacheinander aus.

**1. In den Datenordner wechseln.** `cd` heisst «change directory». Die Anführungszeichen braucht es wegen des Ausrufezeichens im Ordnernamen.

```bash
cd ~/Developer/"Konjugiere!"/data
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
| `zsh: event not found: "` | Das Ausrufezeichen im Ordnernamen wurde nicht in Anführungszeichen gesetzt. Befehl genau so kopieren wie oben. |
| `No module named pytest` | Schritt 2 fehlt, oder du hast `python3` statt `.venv/bin/python` verwendet. |
| `CERTIFICATE_VERIFY_FAILED` | Tritt mit dem aktuellen Skript nicht mehr auf, weil das Herunterladen über `curl` läuft. Falls doch: Meldung an Claude schicken. |
| `FileNotFoundError: … raw/extract/…` | Schritt 4 fehlt. |

## iOS-App
Folgt im nächsten Schritt.
