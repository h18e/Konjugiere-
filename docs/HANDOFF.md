# Handoff: Lernapp für Verbkonjugationen

## Ziel
Raphi will eine eigene Lernapp für Verbkonjugationen entwickeln. Primär Französisch, später evtl. Englisch und Italienisch. Er interessiert sich vor allem für die Daten. Die App selbst soll Claude programmieren. Raphi ist technisch interessiert, aber kein Profi-Entwickler: Anleitungen müssen vollständig sein (exakte Menüpfade, kopierbare Terminal-Befehle). Er testet gründlich und meldet exakte Fehlertexte.

## Stand
- Es ist noch kein Code geschrieben.
- Es gibt noch keine Freigabe. **Nicht mit der Umsetzung beginnen, bis Raphi «Freigabe» (oder Ähnliches) sagt.**
- Claude hat die unten stehenden Eckpunkte vorgeschlagen. Raphi hat noch nicht darauf geantwortet.

## Recherchierte Datenquellen
| Quelle | Sprachen | Format | Lizenz | Bemerkung |
|---|---|---|---|---|
| Verbiste | FR (über 7000 Verben), IT (rund 190) | XML, Verb → Konjugationsvorlage | GPL v2+ | Sauberstes modernes Französisch. Die GPL ist heikel für eine Verteilung im App Store. |
| UniMorph | FR, EN, IT (und viele weitere) | TSV: `Grundform  Form  Tags` | vermutlich CC BY-SA (aus Wiktionary), **Lizenz noch verifizieren** | Einheitliches Format. Die französischen Daten enthalten fälschlich alt- und mittelfranzösische Formen, die herausgefiltert werden müssen. |
| Wiktextract / kaikki.org | FR, EN, IT | JSON | CC BY-SA (Wiktionary) | Sehr umfangreich. |
| Flexique | FR | Datensatz | Open Source | Eher für die linguistische Forschung. |
| Morphalou, Lefff | FR | Lexikon | frei | Für NLP aufbereitet. Lizenz und Details nicht geprüft. |
| mlconjug3 | FR, EN, ES, IT, PT, RO | Python-Bibliothek (MIT) | MIT | Für FR mit Verbiste trainiert, für IT nur rund 94 % genau. Eher Werkzeug als Datenquelle. |

## Vorgeschlagene Eckpunkte (warten auf Bestätigung)
1. **Plattform:** iOS mit SwiftUI (Raphi hat bereits die iOS-App «Frostify» gebaut). Alternative: Web-App.
2. **Datenquelle:** Wiktextract bzw. UniMorph, wegen Lizenz und einheitlichem Format. Altfranzösisch herausfiltern.
3. **Datenaufbereitung:** Python-Skript lädt die Rohdaten, bereinigt sie und erzeugt eine kompakte SQLite-Datenbank, die in die App eingebaut wird. Die App läuft offline.
4. **Startumfang:** nur Französisch, die rund 500 häufigsten Verben.
5. **Zeitformen:** alle in der Datenbank. In der App wählbar, welche geübt werden.
6. **Lernmodus:** Verb, Person und Zeitform werden angezeigt, die Form wird eingetippt. Spaced Repetition, Fortschritt lokal gespeichert.
7. **Sprache der App:** Deutsch.

## Offene Fragen an Raphi
- Für wen ist die App: nur für ihn, für seine Kinder oder für den App Store? Das entscheidet, wie streng die Lizenzfrage behandelt werden muss.
- Welcher Übungsmodus: Eintippen, Multiple Choice oder Karteikarten?

## Nächster Schritt nach der Freigabe
Zuerst das Datenskript bauen, damit Raphi die aufbereiteten Daten sieht. Danach die strukturierte Spezifikation (Rolle, Stack, Datenmodell, Anforderungen) bestätigen und die App aufsetzen.

## Hinweise zur Zusammenarbeit
- Claude macht alle Git-Arbeit (Commits, Pushes). Raphi führt nur `git pull` aus.
- Den Projektordner ausserhalb von iCloud Drive anlegen (z. B. `~/Developer/`).
- Ehrlich sagen, wenn Code nicht kompiliert werden konnte. Den Build-Nachweis erbringt Raphi in Xcode (⌘R).
- Bei Codeänderungen immer den vollständigen Code liefern, nicht nur Ausschnitte.
- Lebende Dokumente mitführen: README.md, SETUP.md, später RELEASE.md und PRIVACY.md.

## Empfohlene Skills
- `iosapp-entwicklung`: Arbeitsweise mit Raphi bei eigenen Apps. Zu Beginn laden.
- `grill-me` oder `to-spec`: um die Spezifikation zu schärfen bzw. festzuhalten.
- `tdd`: für das Datenaufbereitungsskript (Parser und Filter testen).
