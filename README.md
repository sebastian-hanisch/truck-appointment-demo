# 🚛 Truck-Appointment-Scheduling

Interaktive Demo zur Terminvergabe für anliefernde LKW an einer Umschlaghalle.

**[→ Demo live ausprobieren](https://sebastianhanisch-truckappointment-demo.streamlit.app/)**

## Worum geht's?

Jedem LKW muss ein (Tor, Startzeit)-Paar zugewiesen werden, ohne Überlappungen am selben Tor und mit Start nicht vor der bevorzugten Ankunftszeit — mit dem Ziel, die Gesamtwartezeit zu minimieren. Anders als die räumliche Tor-Zuordnung ist das ein echtes Scheduling-Problem mit Zeitdimension: ein Parallel-Maschinen-Scheduling-Problem mit Freigabeterminen.

## Methodik

- Drei klassische Scheduling-Prioritätsregeln im Vergleich: **First-Come-First-Served (FCFS)**, **Earliest-Release-Date (ERD)** und **Shortest-Processing-Time (SPT)**
- Terminplan als Gantt-Chart, eingefärbt nach Wartezeit
- PDF-Export, Permalink für eigene Beispielszenarien

## Lokal ausführen

```bash
pip install -r requirements-dev.txt
streamlit run app.py
```

Tests: `pytest tests/ -v`

---

Teil des [Operations-Research-Demo-Portfolios](https://sebastianhanisch.net/demos.html) von [Sebastian Hanisch](https://sebastianhanisch.net) — Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html).
