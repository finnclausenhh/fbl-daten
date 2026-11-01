# App 0.20: Kopfzeile und Aufstellungen wie im Web (Stand 01.11.2026)

Vorbild ist der Web-Ticker (wosoinsider.de/ticker, Artifact index.html, Funktionen `feld`, `aufBlock`, `offiziell`, `prognose`, `bankNamen`, `aenderungen`, `wxZeile`). Entwurf mit Begründungen: https://claude.ai/artifact/JkCcspsmjWDHdx1fZPx8kS

Die Darstellung entsteht in der App aus den vorhandenen Daten. Damit gilt sie automatisch auch rückwirkend für alle Aufstellungen ab heute, ohne Datenänderung.

## 1. Kopfzeile (Variante A)
- Logo links, gestapelt wie bisher (WOSO über INSIDER, zentriert zueinander).
- Rechts Tabelle, Statistik und Suche als freie Symbole ohne Kacheln, Farbe gedämpft; aktiv = Akzentblau.
- Kein Mittelkreis, keine Linie, **kein Vereinsfilter** mehr (Knopf und Zeile „Nur ... · ändern“ entfernen; gespeicherte Auswahl ignorieren). Die Vereinsauswahl kommt später in die Einstellungen der Push-Mitteilungen.

## 2. Aufstellung als Spielfeld
- Hochkant, Sturm oben, Torhüterin unten. Reihen nach Linie `p`: ST, OM, MF, DM, ABW, TW (leere Reihen weglassen), Spielerinnen gleichmäßig verteilt. Formation klein unten links.
- Fotos 54 pt (ab 6 Reihen 48), Ausschnitt mit Schulter und Trikot (nicht nur Gesicht), Kreis mit blassem Hintergrund (Weiß 5 %, Rand Weiß 7 %). Ohne Foto Initialen in Vereinsfarbe. Foto-Zuordnung: `voll` in fotos.json, sonst Verein plus Nachname (Ø/Ö, á/a gleich behandeln).
- **Offiziell:** keine Stufen-Symbole. NEU als grünes Schild oben rechts am Foto (Feld `f: "neu"`, im Spielplan: nicht in der Startelf des letzten Liga-Spiels mit offizieller Aufstellung). Tore, Karten, Auswechselminute klein am Foto, wenn vorhanden.
- **Prognose:** Stufen-Symbol unten mittig am Foto (Sicher, Erwartet, Unsicher). Antippen zeigt die Begründung. Ganz unten Legende und der Satz „Prognose von WOSOINSIDER, die offizielle Aufstellung kommt ca. 60 Minuten vor Anpfiff und ersetzt sie hier.“ Kein Umschalter Offiziell/Prognose: es gibt immer nur eine der beiden.

## 3. Unter dem Feld (Reihenfolge)
1. **Bank** als Namen, Zeilen TW, ABW, MF, ST (DM und OM zählen als MF), Namen mit Punkt getrennt. RAUS rot hinter dem Namen, wenn sie im letzten Ligaspiel in der Startelf stand (`f: "raus"`).
2. **Änderungen zum letzten Ligaspiel** (nur offiziell): Paare „Foto Name NEU · für · Name RAUS Foto“. RAUS kommt aus Bank `f: "raus"`, aus `fehlt` mit `f: "raus"` und `war != "Bank"` und aus `nicht_startelf`. Paarung nach Positionsgruppe, Rest der Reihe nach.
3. **Alternativen** (nur Prognose): gleiche Paare „Name ALTERNATIVE · für · Name UNSICHER“ aus `alternativ` (`fuer` für `statt`).
4. **Nicht im Kader:** nur Spielerinnen mit `f: "raus"` oder mit bekanntem Grund `i`. Zusatz in Grau: `(i)` oder, ohne Grund, „(zuletzt Startelf/Bank, Grund unbekannt)“ aus `war`.

## 4. Neue Felder in news.json (Action „Aufstellungen live“)
- `quelle_live: true` an allen von der Action gebauten Meldungen.
- Aufstellung: `bank_offen` (Bank noch nicht veröffentlicht), `nicht_startelf` [{n,p,pid}], in `fehlt` zusätzlich `war` ("Startelf"/"Bank") und `i`.
- Platzhalter „Aufstellung X gegen Y folgt“: `platzhalter: true`, `anstoss`, bei Ligaspielen `partie_id`. Im Artikel Knopf „Unsere Prognose ansehen ›“, der zum Spielplan wechselt und die Partie öffnet.
- Meldungen „X nicht im Kader gegen Y“ (id `fehlt-...`): Tags AUFSTELLUNG (+ POKAL), `status: "fraglich"`. Normale Meldungskarte.

## 5. Lichtkegel auch hinter Vereinslogos
- Karten, die nur ein Vereinslogo zeigen (Aufstellungen, Vereinsthemen), bekommen denselben Hintergrund wie die Portraits: radialer Verlauf, Mitte bei 50 % / 45 %, #3A4F78 nach #2A3B5E bei 70 %. Damit wirken alle Karten einheitlich.

## 6. Fehler aus der aktuellen App
- RAUS-Kästchen in Chips wird abgeschnitten („RA…“), z. B. bei Bühl und Ihme. Mit der neuen Darstellung entfallen diese Chips; falls Chips bleiben, das Schild nie kürzen, lieber den Namen.

## Nach dem Build
Patchnotes 0.20 in Alltagssprache (Muster 0.18): neue Kopfzeile, Aufstellung als Spielfeld mit Fotos, Bank und Änderungen auf einen Blick, Hinweis „Aufstellung folgt“.
