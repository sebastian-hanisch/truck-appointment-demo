# Truck-Appointment-Scheduling – Streamlit-Demo

Interaktive Demo zur Terminvergabe für LKW-Anlieferungen an einer Umschlaghalle. Fünfte Demo im
Portfolio für die Website "Sebastian Hanisch – Operations Research und Machine Learning", nach
Tourenplanung (VRP), 3D-Packungsoptimierung, Liniennetz-Design (ÖPNV) und Tor-Zuordnung (Dock
Door Assignment) - im Kernfeld Fracht-/Logistik, aber mit einer neuen Problemklasse.

## Das Problem: Parallel-Maschinen-Scheduling mit Freigabeterminen

Jedem LKW muss ein (Tor, Startzeit)-Paar zugewiesen werden - keine Überlappung mit anderen LKW
am selben Tor, kein Start vor der bevorzugten Ankunftszeit (dem "Freigabetermin"), mit dem Ziel,
die Gesamtwartezeit zu minimieren. Formal ein **Parallel-Maschinen-Scheduling-Problem mit
Freigabeterminen** (jedes Tor ist eine "Maschine", jeder LKW ein "Auftrag" mit Bearbeitungsdauer
und frühestem Starttermin) - eine gut untersuchte Problemklasse der Scheduling-Theorie,
praxisrelevant unter dem Namen Truck Appointment Scheduling seit Häfen und Distributionszentren
begonnen haben, feste Zeitfenster statt freier Anfahrt zu vergeben.

## Einordnung: warum ein neues Projekt statt einer Erweiterung

Ursprünglich als Erweiterung der Tor-Zuordnungs-Demo (`dock-demo`) angedacht ("Cross-Dock-
Routing": Sendungen konsolidieren, dann Toren zuordnen) - beim genaueren Vergleich stellte sich
heraus, dass dieses Modell strukturell fast identisch mit einer bereits existierenden, deutlich
ausgereifteren Demo ist (`freight_demo`, Seefracht-Konsolidierung: Bin-Packing + Facility-Wahl).
Truck-Appointment-Scheduling dagegen bringt eine **echte Zeitdimension** ins Portfolio, die in
keiner der vier bestehenden Demos vorkommt (`dock-demo`: rein räumliche Zuordnung ohne
Zeitachse; `freight_demo`: Bin-Packing + Facility-Wahl, ebenfalls ohne Zeitachse;
`transit-demo`: Netzwerk-Design; `vrp_demo`: Routing) - deshalb ein eigenständiges neues
Projekt statt einer Erweiterung.

## Dateistruktur

Modular wie bei den anderen Demos:

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Hauptablauf (Primäransicht, Sidebar, Detail-Expander) |
| `tas_constants.py` | Konstanten |
| `tas_data.py` | LKW-Anmeldungen (Wunschzeit, Bearbeitungsdauer) erzeugen |
| `tas_heuristics.py` | FCFS-, ERD- und SPT-Konstruktion |
| `tas_evaluation.py` | Bewertung: Wartezeit, Pünktlichkeit, Makespan |
| `tas_visualization.py` | Gantt-Chart (Plotly) |
| `tas_pdf_export.py` | PDF-Terminplan-Erzeugung |
| `tas_feedback.py` | Feedback-Logging |
| `tas_ui_panel.py` | Wiederverwendbares UI-Panel je Heuristik |
| `tas_presets.py` | Beispielszenarien, Permalink-Logik (`SETTING_SPECS`) |

## Funktionsumfang

- **Wunschzeiten statt fixer Zeitfenster:** Jeder LKW hat eine bevorzugte Ankunftszeit
  (Minuten ab Betriebsbeginn) und eine Bearbeitungsdauer, konfigurierbar über eine
  "Konzentration auf Stoßzeiten" (0 = gleichverteilt über den Tag, 1 = die meisten LKW wollen
  zu einer von wenigen Stoßzeiten ankommen - z. B. Schichtwechsel).
- **Drei eigene Scheduling-Prioritätsregeln:**
  - *FCFS* (Baseline): LKW in Anmeldereihenfolge, jeweils frühestmögliches freies Tor -
    repräsentiert eine Terminvergabe ohne gezielte Planung.
  - *ERD* (Earliest Release Date first): LKW nach aufsteigender Wunschzeit sortiert, sonst
    derselbe Platzierungsmechanismus wie FCFS.
  - *SPT* (Shortest Processing Time first, ereignisgesteuert): sobald ein Tor frei wird,
    übernimmt unter den bereits verfügbaren LKW der mit der kürzesten Bearbeitungsdauer - siehe
    Korrektur unten.
- **Wartezeit statt Kosten als Kennzahl:** Bewusst keine künstliche €-Umrechnung, da die
  tatsächliche Kostenwirkung von Standzeiten stark vom Vertragsmodell mit den Spediteuren
  abhängt.
- **Primäransicht "Ihr optimierter Terminplan"** von Anfang an: zeigt die beste der drei
  Methoden direkt, kein Algorithmus-Name in der Überschrift.
- **Drei Ein-Klick-Beispielszenarien:** Ruhiger Tag, Schichtwechsel-Stoßzeit, Volle Auslastung.
- **Gantt-Chart-Visualisierung:** Tore auf der Y-Achse, Uhrzeit auf der X-Achse, Balkenfarbe
  nach Wartezeit, Wunschzeit als Strich markiert, Stoßzeiten als gepunktete Linien - visuell
  komplett anders als die räumlichen Grundrisse der bisherigen Demos.
- **Permalink, Feedback-Mechanismus, PDF-Export:** wie bei den anderen Demos, inklusive
  `SETTING_SPECS`-Muster und NaN/Infinity-Schutz von Anfang an.
- **Mathematische Formulierung als eigener Expander:** formale Definition als $P_m \mid r_i
  \mid \sum C_i$ (Parallel-Maschinen-Scheduling mit Freigabeterminen, disjunktive und
  binäre MILP-Form), NP-Schwere-Beleg über Lenstra/Rinnooy Kan/Brucker (1977), formale
  Herleitung aller drei Konstruktionsregeln sowie ein Monotonie-Beweis dafür, warum lokale
  Verbesserung hier wirkungslos bleibt - mit direktem Bezug auf die entsprechenden Funktionen
  im Code.

## Ein Konstruktionsfehler gefunden: statische SPT-Sortierung ignoriert Freigabetermine

Die erste Version der SPT-Heuristik sortierte alle LKW einmalig global nach Bearbeitungsdauer
und plante sie in dieser Reihenfolge ein - unabhängig davon, wann sie tatsächlich verfügbar
sind. Das kann einen bereits verfügbaren langen Auftrag unnötig hinter einen erst später
verfügbaren kurzen Auftrag zurückstellen.

**Handkonstruierter Beleg:** Ein Tor, ein langer Auftrag L (Dauer 100, sofort verfügbar) und ein
kurzer Auftrag S (Dauer 1, erst ab Minute 50 verfügbar). Die naive Sortierung plant S zuerst ein
(kürzere Dauer, unabhängig von der Verfügbarkeit) - S bekommt Minute 50, L muss danach warten
und startet erst bei Minute 51 (Gesamtwartezeit 51). Die korrigierte, ereignisgesteuerte Version
lässt das Tor sofort mit L loslegen (L ist zu dem Zeitpunkt der einzige verfügbare Auftrag),
S wartet dann bis Minute 100 auf das freie Tor, muss dort aber nur bis Minute 100 statt 101
warten (Gesamtwartezeit 50) - ein Minute besser, und das Prinzip verallgemeinert sich.

**Fix:** `spt_schedule()` in `tas_heuristics.py` simuliert den Betrieb jetzt ereignisgesteuert:
sobald ein Tor frei wird, wird unter den zu diesem Zeitpunkt bereits verfügbaren, noch nicht
eingeplanten LKW der mit der kürzesten Bearbeitungsdauer gewählt. Über 40 Zufallsinstanzen war
diese Version nie schlechter und meist deutlich besser als die naive Sortierung (getestet in
`test_spt_dominates_naive_static_spt_ordering`, das handkonstruierte Beispiel oben in
`test_spt_hand_constructed_case_where_naive_ordering_fails`). Die naive Variante wurde aus der
App entfernt (kein Nutzer sollte eine bekannt unterlegene Methode angeboten bekommen), bleibt
aber über `_construct()` in den Tests referenzierbar, um den Fund reproduzierbar zu halten.

## Eine geplante Erweiterung geprüft und verworfen: lokale Verbesserungssuche bringt nichts

Ursprünglich als drittes Verfahren geplant (analog zu `dock-demo`s 2-opt): eine lokale
Verbesserungssuche auf der SPT-Konstruktion. Zwei Varianten wurden implementiert und
benchmarkt - beide fanden in **0 von 300 Testinstanzen** irgendeine Verbesserung:

1. **Einzel-LKW-Neuplatzierung** (Relocate): jeden LKW einzeln aus seinem Slot entfernen und auf
   den frühestmöglichen freien Slot über alle Tore neu setzen, falls das seine Wartezeit senkt.
2. **Paarweiser Tausch** (Swap): zwei LKW tauschen ihre (Tor, Startzeit)-Zuordnung, falls das
   die Summe ihrer beiden Wartezeiten senkt und an beiden neuen Positionen machbar ist.

**Das ist kein Zufall, sondern beweisbar:** Bei einer ereignisgesteuerten Konstruktion wird
jeder LKW zum Zeitpunkt seiner Einplanung bereits gegen alle zu dem Zeitpunkt bekannten
Alternativen optimal platziert (frühestmöglicher Slot über alle Tore, gegeben die bis dahin
getroffenen Buchungen). Eine nachträgliche Neubetrachtung eines einzelnen LKW gegen die
*vollständige* Endkonfiguration prüft ihn gegen eine Buchungsmenge, die die ursprüngliche
(zum Einplanungszeitpunkt bekannte) Menge als Teilmenge enthält, plus alle später
hinzugekommenen Buchungen - niemals weniger. Mehr mögliche Hindernisse können den
frühestmöglichen Slot nur gleich lassen oder verschlechtern, nie verbessern. Deshalb kann eine
einzelne Neuplatzierung (und, empirisch bestätigt, auch ein einzelner Tausch) nie einen
früheren Slot finden, als die Konstruktion bereits gefunden hat.

**Konsequenz:** Beide Implementierungen wurden nicht in die App übernommen. Die App bleibt bei
drei Konstruktionsheuristiken (FCFS, ERD, SPT) statt "Konstruktion + Verbesserung" wie bei
`dock-demo` - für diese Problemklasse ist das der ehrliche, weil beweisbar vollständige Ansatz.

## Qualität der drei Verfahren

Über mehrere Zufallsinstanzen (24-60 LKW, 2-4 Tore, mittlere bis hohe Stoßzeiten-Konzentration):

| Vergleich | Ergebnis |
|---|---|
| ERD vs. FCFS | ERD im Schnitt ~12 min kürzere Ø-Wartezeit, in 3 von 120 Testinstanzen leicht schlechter |
| SPT vs. ERD | SPT im Schnitt ~15 min kürzere Ø-Wartezeit, in 2 von 120 Testinstanzen leicht schlechter |
| SPT vs. FCFS | SPT im Schnitt ~27 min kürzere Ø-Wartezeit gegenüber der Baseline |

Keine der drei Heuristiken hat eine Optimalitätsgarantie für mehrere parallele Tore mit
unterschiedlichen Freigabeterminen (SPT ist nur für eine einzelne Maschine ohne Freigabetermine
nachweislich optimal, Smith 1956) - in der Primäransicht gewinnt deshalb schlicht die Methode
mit der geringsten Ø-Wartezeit für das jeweilige Szenario, nicht immer dieselbe.

## Bewusst nicht enthalten (Scope-Entscheidung)

- Keine Pufferzeiten zwischen zwei LKW am selben Tor (direkt aneinander anschließende
  Bearbeitung ist erlaubt).
- Keine Torkompatibilität (nicht jedes Tor für jeden Fahrzeugtyp geeignet) als Nebenbedingung.
- Keine Verspätungen gegenüber einer harten Zusage (nur Wartezeit gegenüber dem Wunsch als
  Zielgröße) - eine Erweiterung um harte Deadlines wäre ein eigenständiges Teilproblem
  (Earliest-Due-Date-Familie statt Earliest-Release-Date-Familie).
- Keine mehrtägige Planung (ein einzelner Betriebstag).
- Kein Metaheuristik-Verfahren - nachdem schon die einfache lokale Verbesserungssuche beweisbar
  wirkungslos ist (siehe oben), würde eine Metaheuristik auf derselben Nachbarschaft am selben
  Problem scheitern.

## 1. Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## 2. Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

62 Tests, laufen automatisch bei jedem Push/PR über GitHub Actions.

## 3. Kostenlos online stellen (Streamlit Community Cloud)

1. Diesen Ordner in ein GitHub-Repository hochladen.
2. Auf [share.streamlit.io](https://share.streamlit.io) anmelden.
3. "New app" → Repository und `app.py` als Hauptdatei → Deploy.

## 4. Anpassungsideen für später

- Pufferzeiten zwischen zwei LKW am selben Tor als Nebenbedingung.
- Harte Zusagen/Deadlines statt nur Wunschzeiten (Earliest-Due-Date-Familie zusätzlich zur
  Earliest-Release-Date-Familie).
- Torkompatibilität für bestimmte Fahrzeugtypen.
- Mehrtägige statt eintägige Planung, mit Übertrag nicht bedienter LKW auf den Folgetag.
- Test an einem echten Mobilgerät.
