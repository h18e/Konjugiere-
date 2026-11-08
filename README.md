# Konjugiere!

Nachschlagewerk und Lernhilfe für Verbkonjugationen auf Französisch, Italienisch und Englisch, als iOS-App für iPhone und iPad.

Was die App können soll, steht in [SPEC.md](SPEC.md). Wie gut die Daten sind, zeigt [docs/DATENQUALITAET.md](docs/DATENQUALITAET.md). Diese Datei wird bei jedem Build neu erzeugt.

## Stand
- ✅ Datenaufbereitung: Französisch, Italienisch und Englisch, mit deutschen Bedeutungen, Häufigkeiten und Lernpaketen
- ⏳ iOS-App: noch nicht begonnen

## Aufbau

```
Konjugiere!/
├── SPEC.md                  Spezifikation (Ergebnis der Planungsrunden)
├── SETUP.md                 Ersteinrichtung Schritt für Schritt
├── docs/
│   ├── DATENQUALITAET.md    automatisch erzeugter Qualitätsbericht
│   └── HANDOFF.md           Übergabe aus dem ersten Chat
└── data/                    Datenaufbereitung (Python)
    ├── pipeline/
    │   ├── fetch.py         Rohdaten herunterladen (Wiktionary wird beim Herunterladen gefiltert)
    │   ├── extract.py       kompakter Auszug aus dem englischen Wiktionary
    │   ├── french.py        Französisch: Verbiste + Regeln (zusammengesetzte Zeiten, Elision, Angleichung)
    │   ├── italian.py       Italienisch: Wiktionary + Regeln (Betonungszeichen, zusammengesetzte Zeiten)
    │   ├── english.py       Englisch: Stammformen + Zeiten mit Hilfsverben
    │   ├── glosses.py       deutsche Bedeutungen aus dem deutschen Wiktionary
    │   ├── frequency.py     Häufigkeitsrang
    │   ├── packages.py      kuratierte Lernpakete
    │   ├── build.py         alles zusammenführen → konjugiere.sqlite
    │   └── report.py        Qualitätsbericht
    ├── corrections/
    │   ├── corrections.tsv  Korrekturen an einzelnen Formen
    │   └── glosses.tsv      deutsche Bedeutungen von Hand
    ├── tests/               pytest-Tests (Parser, Regeln, Filter)
    ├── raw/                 Rohdaten (nicht in Git, rund 1,2 GB)
    └── build/               erzeugte Datenbank (nicht in Git, rund 38 MB)
```

## Datenfluss
1. `fetch` lädt Verbiste, FrequencyWords sowie das englische und das deutsche Wiktionary herunter.
2. `extract` zieht die italienischen und englischen Verben aus dem englischen Wiktionary.
3. `build` konjugiert alle Verben, ergänzt deutsche Bedeutungen, Häufigkeit und Lernpakete, wendet die Korrekturen an und schreibt `data/build/konjugiere.sqlite` sowie den Qualitätsbericht.
4. Die App liest die Datenbank nur. Lernfortschritt und Profile speichert sie separat mit SwiftData.

## Quellen und Lizenzen
| Quelle | Verwendung | Lizenz |
|---|---|---|
| [Verbiste](http://sarrazip.com/dev/verbiste.html) 0.1.49, © Pierre Sarrazin | französische Konjugationen | GPL v2+ |
| Wiktionary (englisch und deutsch), über [Wiktextract/kaikki.org](https://kaikki.org) | IT/EN-Konjugationen, deutsche Bedeutungen | CC BY-SA 4.0 |
| [FrequencyWords](https://github.com/hermitdave/FrequencyWords), Hermit Dave | Häufigkeitsrang | CC BY-SA 4.0 |

Die GPL von Verbiste ist für die Nutzung in der Familie kein Problem. Vor einer Veröffentlichung im App Store muss Französisch auf eine andere Quelle umgestellt werden, siehe SPEC.md.

## Daten neu erzeugen
Siehe [SETUP.md](SETUP.md), Abschnitt «Daten aufbereiten».
