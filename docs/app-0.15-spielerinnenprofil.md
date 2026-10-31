# App 0.15: Suche und Spielerinnenprofil (Finn 31.10.2026, im Web live)

Vorbild ist die Webversion https://wosoinsider.de/ticker/ (Quelltext per curl laden, Abschnitt "Suche und Spielerinnenprofil" im Skript und die CSS-Klassen pf-*). Design und Logik genau so übernehmen. Freigegebener Entwurf: https://claude.ai/artifact/CobBBdajXdaRdBsEz6QSy4 (Version 9).

## Daten
spielerinnen.json im Repo fbl-daten (GitHub Pages, wie news.json). Erst laden, wenn Suche oder Profil geöffnet wird; danach im Speicher halten.
- "vereine": {Kürzel: {"name", "spiele", "kommend": [{"datum", "wb" (Liga|Pokal|CL|Europapokal), "md"?, "gegner", "gk"?, "ha" (H|A), "rang"?}]}}
- "spielerinnen": [{"id", "n", "k", "verein", "nr", "pos" (Kickbase-Position TW|ABW|MF|ST), "nation",
   "spiele": [{"md", "datum", "gegner", "gk", "ha", "erg", "art" (S Startelf|E eingewechselt|B Bank|X nicht im Kader), "min", "aus"?, "ein"?, "tore"? [Minuten als Text], "vorl"? Zahl, "gelb"? Minute oder true, "rot"? Minute oder true}],
   "orte"? [[x, y, Anzahl]] (x 0 links bis 1 rechts, y 0 eigenes Tor bis 1 gegnerisches Tor; erster Eintrag = Hauptplatz),
   "ersatz"? [{"n", "s" (Startelf für sie), "w" (für sie eingewechselt)}], "status"? {"s" raus|gesperrt|fraglich, "grund", "rueckkehr", "stand"},
   "verlauf"? [Statuszeilen], "einschaetzung"? {"satz", "phasen" [{"d", "t", "prog"?}], "vergleich"?}, "prognose"? {"md", "st", "wert"?, "grund"?, "warum"},
   "standards"? {"elfmeter"|"freistoesse"|"ecken": Rang}, "pokal"? [{"datum", "wb", "gegner", "erg", "art", "aus"?, "ein"?, "tore", "vorl"}]}]
Alle optionalen Felder optional decodieren.

## Einstieg
- Lupe oben rechts in der Kopfleiste (alle drei Tabs) öffnet die Suche.
- Name unter dem Foto im Meldungsartikel (gestrichelt unterstrichen) öffnet das Profil.
- Profilkarte im Artikel direkt nach "Für Kickbase": Foto 44, Name fett, darunter "Köln · Sturm · Sicher für den 9. Spieltag", rechts "Profil ›".
- Chips der offiziellen Aufstellung im Spielplan und in "Aufstellung im Spiel" sind antippbar (Verein + Nachname eindeutig im Verein, sonst nichts tun).
- Zurück führt dorthin, woher man kam (Artikel, Spiel, Suche, Tab); aus einem Profil ins nächste Profil (Ersatz-Namen später) stapelt.

## Suche
Suchfeld "Spielerin oder Verein suchen", Treffer ohne Akzente (buhl findet Bühl, desic findet Dešić). Leer: "Zuletzt angesehen" (bis 4, lokal gespeichert), "Gerade im Gespräch" (meiste Meldungen der letzten 7 Tage, bis 6), Tipp-Zeile. Mit Text: Spielerinnen (Nachname-Anfang zuerst, bis 30) und Vereine. Zeile: Foto 52, Name, "Verein · Position · Nr.", Statuspunkt (grün fit, rot raus, lila gesperrt, orange fraglich). Verein öffnet Kaderliste nach Tor, Abwehr, Mittelfeld, Sturm.

## Profil (eine Seite, Reihenfolge)
1. Kopf: Foto 132x165 mit Wasserzeichen 1,3-fach groß, Name in zwei Zeilen (Barlow 34, Großbuchstaben), "Verein · Nr.", Tags: nur VERLETZT/GESPERRT/FRAGLICH, dann Kickbase-Position als Wort (STURM). Oben rechts auf Höhe des Namens Mini-Spielfeld 46x69 mit allen Linien und weißem Punkt am Hauptplatz.
2. Drei Kacheln gleich hoch, mittig: STATUS (Fit/Verletzt in Farbe, klein "nichts gemeldet" oder "zurück November" bzw. "seit X Tagen"), NÄCHSTER SPIELTAG (Stufe in Farbe, klein "Einsatzwert 87 %" mit geschütztem Leerzeichen), LETZTE 3 EINSÄTZE (Ø-Zeichen klein und dünn, Minutenschnitt, klein "4 Tore · 1 Vorlage"). Die kleinen Zeilen stehen auf einer Linie.
3. Für Kickbase (blau umrandet): Satz "4 der letzten 5 Spiele in der Startelf, davon 1x vorzeitig ausgewechselt." (bei Ausfall "Fällt aus (verletzt). Vorher …"), kein Balken. Standards nur wenn vorhanden (Chips, ab Rang 2 "2. Wahl"). Nächste Spiele: 3 Einträge aus vereine.kommend; eine Lücke von 14 Tagen oder mehr wird als eigener Eintrag "PAUSE Länderspielpause, N Tage ohne Spiel" eingefügt und zählt mit. Bei 3 oder mehr Spielen in 8 Tagen orange "3 Spiele in 8 Tagen" neben der Überschrift. Keine Ampel.
4. Ihre Position: links Spielfeld 84x126 mit ihren Startplätzen (ein Platz: weißer Punkt ohne Zahl; mehrere: Punkte mit Anzahl, seltenere kleiner und blasser, nebeneinander statt übereinander). Rechts Platzname (z. B. OFFENSIVE LINKS), Rolle (STAMMPLATZ ab 75 % Startelf in Kaderspielen grün, ROTATION ab 40 % orange, sonst HERAUSFORDERIN grau), "7 von 8 Spielen in der Startelf (3x nicht im Kader)", "Ø 85' wenn sie beginnt", "auch: Abwehr rechts 1x". Darunter "Wer sie ersetzt" (bis 2 Namen) oder "Bisher keine, sie hat immer selbst gespielt."
5. Saison Bundesliga: 5 Zahlen (Startelf x/y, Minuten, Tore, Vorlagen, Karten), Säulen je Spiel inklusive Pokal (orange, "P") und Champions League (lila, "CL") nach Datum, Höhe = Minuten (max 120), Minuten weiß in der Säule, darüber Bälle und V. Antippen zeigt Details. Legende einzeilig: Startelf, Joker, Bank, fehlte, Pokal, UWCL.
6. Status-Verlauf nur wenn vorhanden: Kasten UNSERE EINSCHÄTZUNG (satz, Phasen, Einschätzungen blau mit "(Einschätzung)", Vergleich klein), dann Zeitleiste.
7. News zu NAME: 3 Meldungen einzeilig, "Alle N Meldungen zu NAME".
8. Fußzeile Bildnachweis und "Daten: Sportschau, Vereine, eigene Auswertung". Teilen-Knopf oben rechts (Link wosoinsider.de/ticker/#spielerin/ID).
