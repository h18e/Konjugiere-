# Konjugiere! – Spezifikation

Stand: 8. November 2026 · Ergebnis der Grilling-Runden Q1–Q31 · Freigabe erteilt am 8.11.2026

## Rolle
Claude arbeitet als iOS-Entwickler (SwiftUI, SwiftData) und Datenaufbereiter (Python, SQLite). Raphi testet und entscheidet.

## Zweck
«Konjugiere!» ist ein Nachschlagewerk und eine Lernhilfe für Verbkonjugationen auf Französisch, Italienisch und Englisch. Nachschlagen und Üben sind eng miteinander verbunden.

## Zielgruppe und Verteilung
- Für die Familie, mit gemischten Niveaus von Schulfranzösisch bis fortgeschritten. Installation über Xcode bzw. TestFlight.
- Der App Store bleibt eine Option. Darum sind Quelle und Lizenz pro Sprache festgehalten, und Verbiste (GPL) ist austauschbar.

## Technischer Stack
- Universal-App für iPhone und iPad, SwiftUI, mindestens iOS 18.
- Lerndaten mit SwiftData, ohne iCloud in V1. Das Datenmodell ist so angelegt, dass CloudKit später aktiviert werden kann.
- Verbdaten liegen in einer schreibgeschützten SQLite-Datenbank (`konjugiere.sqlite`), die mit der App ausgeliefert wird. Sie wird von einem Python-Skript im Ordner `data/` erzeugt.
- Die App läuft vollständig offline. Kein Server, keine Audiofunktion in V1.
- Die Oberfläche ist auf Deutsch in Schweizer Schreibweise (ss statt ß).

## Datenquellen
| Sprache | Konjugationen | Deutsche Bedeutung | Lizenz |
|---|---|---|---|
| FR | Verbiste | deutsches Wiktionary (Wiktextract) | GPL v2+ / CC BY-SA |
| IT | englisches Wiktionary (Wiktextract) | deutsches Wiktionary | CC BY-SA |
| EN | englisches Wiktionary (Wiktextract) | deutsches Wiktionary | CC BY-SA |

- Korrekturen stehen in `data/corrections/*.tsv`. Sie werden bei jedem Import angewendet und haben Vorrang vor den Quellen.
- Häufigkeitsränge (für Lernpakete und Sortierung) stammen aus frei lizenzierten Häufigkeitslisten. Welche Liste, wird im Datenskript festgehalten.

## Datenmodell

### Verbdaten (SQLite, schreibgeschützt)
Das vollständige Schema steht in `data/pipeline/build.py`, hier in Worten (Stand 8.11.2026, ca. 38 MB):
- **meta**: Schemaversion und Build-Datum
- **language**: code (fr/it/en), name, source, license, attribution
- **tense**: lang, code, mood, name_native («Passé composé»), name_de («Perfekt»), sort, level (1–3), rare (anfangs zugeklappt), personal
- **verb**: id, lang, infinitive, infinitive_norm, verb_group, auxiliary (avoir/être/both bzw. avere/essere/both), model («wird konjugiert wie …», nur FR), reflexive_of, freq_rank, gloss_de, note (EN: Unterscheidung gleich geschriebener Verben, z. B. lie/lie), has_irregular, source
- **verb_table**: pro Verb die ganze Konjugation als JSON, komprimiert mit DEFLATE (roh, RFC 1951, in Swift mit `NSData.decompressed(using: .zlib)` lesbar):
  `{"present": [[person, gender, pronoun, form, [alternativen], irregulär], …], …}`
  - person: 1s 2s 3s 1p 2p 3p · bei Partizipien sg/pl · bei den englischen Stammformen base/past/pp · sonst leer
  - gender: m/f/leer. Ist es leer bei 3s/3p, wählt die App «il» oder «elle» zufällig aus `pronoun` («il/elle»).
  - pronoun: so, wie es vor die Form kommt («je», «j'», «que je», «qu'il/qu'elle», «io», «che io», «I»). Endet es auf «'», folgt kein Leerzeichen.
  - Reflexivpronomen sind Teil der Form («me lève», «mi alzo»).
- **search**: lang, term (normalisiert), verb_id, kind (0 Infinitiv, 1 konjugierte Form, 2 deutsche Bedeutung)
- **package / package_verb**: Lernpakete (Titel, Beschreibung, Stufe, optional feste Zeitformen als JSON-Liste)
- Englisch: Die «Zeitform» `principal_parts` enthält die Stammformen. Alle übrigen Zeiten sind zum Nachschlagen gedacht.

### Lerndaten (SwiftData)
- **Profile**: name, level (1–3), defaultLanguage, roundLength (Standard 15), aktive Zeitformen pro Sprache
- **Card**: profile, lang, verbId, tenseCode, person, gender, box (1–5), due, correctCount, wrongCount, lastSeen
- **MyVerb**: profile, lang, verbId, added
- **ErrorReport**: lang, verbId, tenseCode, person, shownForm, note, created

## Funktionale Anforderungen

### Nachschlagen
- Die Sprache wird mit einem Umschalter FR | IT | EN gewählt. Der Standard ist pro Profil gespeichert.
- Die Suche ignoriert Akzente sowie Gross- und Kleinschreibung. Sie findet Infinitive, konjugierte Formen («suis» → être, suivre) und deutsche Bedeutungen («folgen» → suivre). Bei Mehrdeutigkeit erscheinen alle Treffer.
- Die Konjugationstabelle steht auf einer Seite, nach Modus gruppiert. Gängige Zeitformen sind aufgeklappt, seltene zugeklappt. Unregelmässige Formen sind farbig markiert. Bei Formen mit Angleichung werden alle Varianten gezeigt, z. B. «allé(e)(s)».
- Zusatzinfos: Hilfsverb (auch «beides»), Gruppe, «wird konjugiert wie …» mit Link, Verben mit demselben Muster, reflexive Variante, «Zu Meine Verben hinzufügen».
- Jede Form lässt sich als fehlerhaft melden. Die Meldungen lassen sich als Text exportieren.
- Auf dem iPad gibt es eine Seitenleiste: links Liste und Suche, rechts die Tabelle (`NavigationSplitView`).

### Üben
- **Modi**: Eintippen, Multiple Choice, ganze Tabelle (alle Personen einer Zeitform).
- **Vorgabe**: Verb (mit deutscher Bedeutung), Zeitform und ein konkretes Pronomen (il **oder** elle). Bei je/tu/nous/vous erscheint ein Geschlechtssymbol (♀/♂), aber nur wenn sich die Form dadurch ändert.
- **Eingabe** mit Pronomen («j'aime», «elle est allée», «je me suis levée»). Eine Akzentleiste über der Tastatur ist dabei.
- **Prüfung**:
  - Akzente werden streng geprüft. Ein fehlender oder falscher Akzent gilt als falsch, die Rückmeldung sagt aber, dass nur der Akzent falsch ist.
  - Ignoriert werden Gross- und Kleinschreibung, Leerzeichen am Rand, doppelte Leerzeichen und die Apostroph-Varianten (' ’) sowie ein Leerzeichen nach dem Apostroph.
- **Englisch**: Geübt werden die Stammformen der unregelmässigen Verben (go – went – gone).
- **Karte** = Verb × Zeitform × Person (× Geschlecht). Die Statistik fasst zusätzlich pro Verb und Zeitform zusammen («4 von 6 sicher»).
- **Leitner-System** mit 5 Fächern und den Intervallen 1, 2, 4, 8 und 16 Tage. Eine richtige Antwort schiebt die Karte ein Fach weiter, eine falsche zurück in Fach 1.
- **Übungsstoff**: Lernpakete (kuratiert), freie Auswahl, «Meine Verben», «Heute fällig» (mischt alle fälligen Karten).
- **Ablauf einer Runde**: standardmässig 15 Karten, einstellbar. Die Rückmeldung folgt sofort, mit markiertem Unterschied und Link «Tabelle ansehen». Falsche Karten kommen am Ende der Runde nochmals, bis sie einmal richtig gelöst sind. Am Leitner-Fach ändert das nichts.
- Keine Spielelemente. Die Leitner-Fächer bleiben als reine Information sichtbar.

### Profile
- Mehrere Profile sind möglich, standardmässig gibt es eines.
- Beim Erstellen wählt man eine Stufe. Sie legt die aktiven Zeitformen und die vorgeschlagenen Pakete fest, danach lässt sich alles frei anpassen.
  - Einsteiger: Présent, Passé composé, Futur proche, Futur simple (und die Entsprechungen in IT)
  - Mittel: zusätzlich Imparfait, Conditionnel présent, Impératif, Subjonctif présent
  - Fortgeschritten: alle Zeitformen

## Umfang
- **V1**: alles oben Genannte für FR, IT und EN.
- **Später**: iCloud-Synchronisation, Aussprache, macOS, ein Ersatz für Verbiste (App Store), Statistik über die Zeit.

## Umsetzungshinweise
- Die Schichten sind getrennt: `data/` (Python, getestet mit pytest) → `konjugiere.sqlite` → `VerbStore` in der App (nur lesend) → Lernlogik (Leitner und Antwortprüfung, mit Unit-Tests) → Ansichten.
- Die Antwortprüfung und die Leitner-Logik sind reine Swift-Funktionen, die sich ohne Oberfläche testen lassen.
- Rohdaten und die erzeugte Datenbank landen nicht im Git-Repo, wenn sie grösser als einige MB sind. Das Skript lädt sie reproduzierbar herunter. Ob die fertige Datenbank ins Repo kommt, entscheidet die Grösse.
- Lebende Dokumente: README.md, SETUP.md, später RELEASE.md und PRIVACY.md.
