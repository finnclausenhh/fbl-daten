
## Neu für 0.16: Tabelle, Statistik, kompakte Analyse, Über WOSOINSIDER und Web-Nachzug (Finn 31.10.2026)

Vorlage ist jeweils die Webversion https://wosoinsider.de/ticker/ (Quelltext per curl laden). Design und Logik genau übernehmen, Texte wörtlich.

1. Kopfleiste: Rechts drei Knöpfe nebeneinander (je 34 Punkt, Abstand 6, abgerundet 10 auf Soft-Grund): Tabelle (Raster mit Kopfzeile, SVG `rect 3.5/4/17x16 rx2.5` plus `M3.5 9h17M3.5 14.5h17M9 9v11`), Statistik (steigende Balken auf Grundlinie, `M3 20h18` plus `M6 16v-3M11 16V9M16 16V5`), Lupe. Der aktive Knopf wird Akzentblau. Web: `kopf-btns`, `data-statview`.
2. Tabelle (Web: `statView("tabelle")`, `ligaStand()`): nur Ligaspiele aus spielplan.json (status beendet, ergebnis). Spalten #, Wappen, Verein, SP, S-U-N, TORE, DIFF, PKT. Sortierung Punkte, Tordifferenz, Tore. Bei völligem Gleichstand Platzzahl nur einmal. Zeile antippen öffnet den Vereinskader (`VereinsKaderView`), Zurück führt zur Tabelle. Untertitel "Google Pixel Frauen-Bundesliga, nach dem N. Spieltag" (N = höchster komplett gespielter Spieltag).
3. Statistik (Web: `statView("statistik")`, `ligaWerte()`, `STKAT`): aus spielerinnen.json (spiele mit art S/E) berechnet, nur Liga. Kategorien in dieser Reihenfolge: Tore, Vorlagen, Scorerpunkte, Joker-Tore (Tore nach Einwechslung), Weiße Weste (TW in der Startelf, Team ohne Gegentor), Tore pro 90 Minuten (ab 270 Minuten, zwei Nachkommastellen mit Komma), Dauerbrennerinnen (jedes Ligaspiel des Vereins in der Startelf, nie ausgewechselt, kein Platzverweis; als Chips), Gelbe Karten (ohne Gelb-Rot), Platzverweise (Rot und Gelb-Rot; als Chips). Oben waagerecht scrollbare Sprung-Chips.
   - Karte je Kategorie mit Top 3, "Top 10 ›" klappt auf (kleinere Fotos 30, Wert 17), "Weniger" klappt zu.
   - Zeile: Rang, Foto (Wasserzeichen wie überall), Wappen 18 VOR dem Namen (feste Spalte, Variante B, Finn 31.10.), Name, Balken (Anteil am Spitzenwert, Platz 1 Akzentblau, sonst #6E9BFF), Wert rechts in Barlow Condensed.
   - Rang 1 bis 3 als runde Plakette 22 Punkt mit dunkler Zahl: Gold #F5C518, Silber #C7CFDA, Bronze #C8865A; ab Platz 4 nur "4." gedämpft.
   - Gleichstand: gleicher Rang, Reihenfolge innerhalb nach weniger Minuten. Liegt an der Grenze (Platz 3 bzw. 10) ein Gleichstand, darunter "Ebenfalls 4: Name, Name" (ab 6 Namen: vier Namen "und N weitere").
   - Zeile oder Chip antippen öffnet das Profil, Zurück führt zurück in die Statistik an dieselbe Stelle.
4. Inside, Top-Analyse kompakt (Web: `analyseInhalt`, Klassen ak-*): Neue Felder in inside.json analyse: `kurz` (2 bis 3 Stichpunkte, Überschrift "Kurz erklärt") und `ausblick` (Liste {md, datum, gk, ha, satz, namen, fehlt, kb, kbart}). Darstellung je Ausblick als Karte: links Spieltag groß ("9.") und Wochentag mit Datum, rechts "gegen/in" Wappen Gegner, rechts oben Etikett "Kickbase: <kb>" (kbart warn = orange, gut = grün, sonst blau), darunter satz, Namen als Chips, fehlt als rote Chips. Darunter aufklappbar "Ganze Analyse lesen ›" mit den bisherigen Absätzen (text), "Unsere Einschätzung" und "Für Kickbase". Fehlen kurz und ausblick, bleibt die bisherige Darstellung. Im Analyse-Kopf die Spalte der großen Zahl fest 118 breit (sonst läuft "17 von 20" in den Text).
5. Über WOSOINSIDER: neuer erster Eintrag in der Fußzeile vor Impressum, Inhalt aus legal.json Schlüssel "ueber" (wie die anderen Rechtstexte, Blöcke h2/p/li, **fett** und Links beachten).
6. Web-Nachzug seit 0.15, alles schon im Web live:
   - Vereinsfilter: Spielansetzungen ohne Aufstellung (Vorberichte, Nachholspiele) nur zeigen, wenn ihr Verein oder ein im Text genannter Verein gewählt ist (Web Kommentar "Spielansetzungen ohne Aufstellung"). Vorher erschien z. B. Köln bei Auswahl FC Bayern.
   - Inside "Spiele mit Ansage": bereits gespielte Partien ausblenden.
   - Feed-Karte: Foto hochkant 76x100, Kopf waagerecht mittig über fotos.json "cx" (Anteil 0 bis 1): object-position x = clamp((cx*h - g/2)/(h-g)*100, 0, 100) Prozent mit h = Bildbreite in Anzeigehöhe skaliert, g = Rahmenbreite (Web Zeile mit "Kopfmitte (cx aus fotos.json)"). Listenabstand 8.
   - Feed-Überschrift: `kurz` aus news.json, falls vorhanden, sonst headline (nie dreizeilig).
   - Artikel: Foto der Spielerin antippen öffnet ihr Profil.
   - Aufstellungs-Meldungen (auch Pokal und Europapokal) mit Objekt `aufstellung` (startelf, bank, fehlt; Einträge mit f "neu"/"raus") wie die Liga-Vorschau zeigen, den Fließtext darunter.
   - Vorberichte (pos "Spielansetzung"): oben beide Vereine "A gegen B" und darunter "Vorbericht" statt "Spielansetzung".
   - Quellenblock kompakt: Zeile "QUELLEN a · b" (Links), darunter eine Zeile "Aus den Quellen mit KI erstellt · Foto …", die beim Antippen "So entsteht WOSOINSIDER ›" aufklappt.
   - Neue Tag-Farben: POKAL rgba(224,150,43,.2)/#F7C27A, EUROPAPOKAL rgba(155,107,232,.22)/#C9AEF7, VORBERICHT und NATIONALTEAM #1D2B47/#F4F5F7. Jede Meldung hat mindestens ein Tag.
   - Profil: Spielminuten enden bei Platzverweis mit der Roten Karte, abgesessene Sperren verschwinden (kommt aus den Daten, App muss nichts tun; nur prüfen).
