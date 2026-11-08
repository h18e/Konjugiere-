"""Kuratierte Lernpakete.

Jedes Paket: Titel, Beschreibung, Stufe (1–3), Verben und optional fest
vorgegebene Zeitformen (sonst gelten die aktiven Zeitformen des Profils).
"""

PACKAGES = {
    "fr": [
        ("Die 12 wichtigsten Verben", "Ohne diese geht nichts.", 1,
         "être avoir aller faire dire pouvoir vouloir savoir venir prendre voir devoir", None),
        ("Verben auf -er", "Die 1. Gruppe: regelmässig und am häufigsten.", 1,
         "parler aimer donner trouver penser regarder écouter chanter jouer travailler habiter "
         "arriver demander rester porter chercher montrer passer entrer tomber", None),
        ("Verben auf -ir (2. Gruppe)", "Mit -iss- im Plural: nous finissons.", 1,
         "finir choisir réussir grandir remplir réfléchir obéir punir rougir grossir maigrir agir", None),
        ("Unregelmässige Verben", "Die häufigsten Verben der 3. Gruppe.", 2,
         "aller faire dire voir venir prendre mettre partir sortir dormir lire écrire boire croire "
         "connaître recevoir vivre ouvrir courir tenir comprendre apprendre", None),
        ("Modalverben", "können, wollen, müssen, wissen, nötig sein", 1,
         "pouvoir vouloir devoir savoir falloir", None),
        ("Passé composé mit être", "Die Verben der Bewegung und des Zustandswechsels.", 1,
         "aller venir arriver partir entrer sortir monter descendre naître mourir rester tomber "
         "retourner devenir revenir rentrer", ["passe_compose"]),
        ("Reflexive Verben", "se lever, s'habiller … im Passé composé mit être.", 2,
         "se lever se laver s'habiller se coucher se réveiller se promener s'amuser se dépêcher "
         "s'appeler s'asseoir se souvenir se tromper", None),
        ("Verben mit Schreibbesonderheiten", "mangeons, commençons, paie, appelle, achète …", 2,
         "manger commencer payer appeler acheter jeter préférer essayer envoyer nettoyer lever répéter", None),
    ],
    "it": [
        ("Die 12 wichtigsten Verben", "Ohne diese geht nichts.", 1,
         "essere avere andare fare dire potere volere sapere venire dare stare dovere", None),
        ("Verben auf -are", "Regelmässig und am häufigsten.", 1,
         "parlare mangiare lavorare abitare amare cantare giocare guardare ascoltare studiare "
         "comprare pagare cercare arrivare tornare", None),
        ("Verben auf -ere", "Regelmässige Verben der 2. Konjugation.", 1,
         "credere vendere ricevere ripetere temere battere cadere godere", None),
        ("Verben auf -ire", "Mit und ohne -isc-: dormo, finisco.", 1,
         "dormire partire sentire aprire offrire seguire servire finire capire preferire pulire "
         "spedire costruire", None),
        ("Unregelmässige Verben", "Die häufigsten unregelmässigen Verben.", 2,
         "essere avere andare fare dire stare dare venire uscire bere tenere rimanere scegliere "
         "porre tradurre salire", None),
        ("Passato prossimo mit essere", "Verben der Bewegung und des Zustandswechsels.", 1,
         "andare venire arrivare partire uscire entrare tornare restare nascere morire cadere "
         "diventare", ["passato_prossimo"]),
        ("Reflexive Verben", "alzarsi, chiamarsi … im Passato prossimo mit essere.", 2,
         "alzarsi lavarsi chiamarsi vestirsi svegliarsi divertirsi sedersi sentirsi annoiarsi "
         "fermarsi", None),
        ("Modalverben", "können, wollen, müssen, wissen", 1, "potere volere dovere sapere", None),
    ],
    "en": [
        ("Unregelmässige Verben 1", "Die 30 wichtigsten: go – went – gone.", 1,
         "be have do go come get make take see know say give find think tell become leave feel "
         "put bring begin keep write stand hear let meet run pay sit", ["principal_parts"]),
        ("Unregelmässige Verben 2", "Die nächsten 30.", 2,
         "speak read grow lose fall send build understand draw break spend cut drive buy wear "
         "choose eat drink sleep swim sing fly forget hide ride throw wake win teach catch",
         ["principal_parts"]),
        ("Unregelmässige Verben 3", "Für Fortgeschrittene.", 3,
         "bear beat bend bet bind bite bleed blow breed burst cast cling creep deal dig dive feed "
         "fight flee forbid forgive freeze grind hang kneel lay lead lend light mislead ring rise "
         "seek sell set sew shake shine shoot show shrink shut sink slide spin split spread steal "
         "stick sting stink strike swear sweep swing tear weep wind", ["principal_parts"]),
        ("Zeiten mit regelmässigen Verben", "Alle Zeiten an einfachen Verben üben.", 2,
         "work play live love want need help ask call try use like", None),
    ],
}
