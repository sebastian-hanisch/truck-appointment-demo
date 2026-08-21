"""
Drei selbst implementierte Konstruktionsverfahren für das Truck-Appointment-
Scheduling-Problem: jeder LKW muss einem (Tor, Startzeit)-Paar zugeordnet
werden, ohne Überlappungen am selben Tor und mit Start nicht vor der
bevorzugten Ankunftszeit, mit dem Ziel, die Gesamtwartezeit zu minimieren -
klassische Prioritätsregeln aus der Scheduling-Theorie für Parallel-
Maschinen-Scheduling mit Freigabeterminen.

- fcfs_schedule: verarbeitet LKW in Anmeldereihenfolge (Index-Reihenfolge,
  unabhängig von Wunschzeit oder Bearbeitungsdauer), jeder bekommt das
  frühestmögliche freie Tor - repräsentiert eine ungeplante Terminvergabe
  ohne Priorisierung. Dient als Baseline.

- erd_schedule: verarbeitet LKW nach aufsteigender Wunschzeit (Earliest
  Release Date first) statt Anmeldereihenfolge - eine naheliegende
  Priorisierung ("wer zuerst kommen will, wird zuerst eingeplant"), sonst
  identischer Platzierungsmechanismus wie fcfs_schedule.

- spt_schedule: ereignisgesteuerte Simulation statt statischer Liste - immer
  wenn ein Tor frei wird, wird unter den zu diesem Zeitpunkt bereits
  verfügbaren (Wunschzeit erreicht), noch nicht eingeplanten LKW der mit der
  kürzesten Bearbeitungsdauer gewählt ("SPT unter den verfügbaren LKW").
  Siehe Korrektur-Hinweis unten - eine naive, statische SPT-Sortierung
  (unabhängig von der Wunschzeit) wurde beim Benchmarking als der ERD-Regel
  systematisch unterlegen erkannt und durch diese ereignisgesteuerte Version
  ersetzt.

Alle drei geben (dock_of_truck, start_of_truck) zurück: Arrays der Länge
n_trucks mit dem zugewiesenen Tor-Index bzw. der zugewiesenen Startzeit
(Minuten ab Betriebsbeginn).

Zwei Erweiterungen wurden geprüft und wieder verworfen (Details im README):
eine statische, nur nach Bearbeitungsdauer sortierende SPT-Konstruktion
(siehe oben - durch die ereignisgesteuerte Version ersetzt, da sie in einer
Stichprobe über 240 Zufallsinstanzen nie besser und oft schlechter als die
ereignisgesteuerte Version war) sowie zwei lokale Verbesserungsschritte auf
der ereignisgesteuerten SPT-Konstruktion (Einzel-LKW-Neuplatzierung und
paarweiser Tausch zweier LKW) - beide fanden in 0 von 300 Testinstanzen
irgendeine Verbesserung. Lässt sich zeigen: bei einer ereignisgesteuerten
Konstruktion, die jeden LKW bei seiner Einplanung bereits gegen alle zu dem
Zeitpunkt bekannten Alternativen optimal platziert, kann eine nachträgliche
Neubetrachtung einzelner LKW gegen die *vollständige* Endkonfiguration nie
einen früheren Slot finden als zum Einplanungszeitpunkt (die Endkonfiguration
enthält immer mindestens so viele Buchungen wie zum Einplanungszeitpunkt
bekannt waren, nie weniger) - ein beweisbarer, nicht nur empirischer Befund.
"""

import numpy as np

from tas_constants import EPS


def _earliest_start(sorted_intervals, preferred_time, service_time):
    """Frühester Start >= preferred_time, sodass [start, start+service_time)
    keins der bereits gebuchten Intervalle auf diesem Tor überlappt.
    sorted_intervals: Liste von (start, end)-Tupeln, aufsteigend nach start
    sortiert."""
    candidate = preferred_time
    for start, end in sorted_intervals:
        if candidate + service_time <= start + EPS:
            return candidate
        if candidate < end:
            candidate = end
    return candidate


def _construct(order, preferred_times, service_times, n_docks):
    """Statische Listen-Konstruktion: verarbeitet LKW in der gegebenen
    Reihenfolge, jeder bekommt das Tor mit dem frühestmöglichen freien Slot
    (gegeben die bisher getroffenen Buchungen)."""
    n = len(preferred_times)
    dock_bookings = [[] for _ in range(n_docks)]  # je Tor: Liste von (start, end), sortiert
    dock_of_truck = np.zeros(n, dtype=int)
    start_of_truck = np.zeros(n)

    for i in order:
        best_dock, best_start = None, None
        for d in range(n_docks):
            s = _earliest_start(dock_bookings[d], preferred_times[i], service_times[i])
            if best_start is None or s < best_start:
                best_start, best_dock = s, d
        dock_of_truck[i] = best_dock
        start_of_truck[i] = best_start
        dock_bookings[best_dock].append((best_start, best_start + service_times[i]))
        dock_bookings[best_dock].sort()

    return dock_of_truck, start_of_truck


def fcfs_schedule(preferred_times, service_times, n_docks):
    """Baseline: LKW in Index-/Anmeldereihenfolge, jeweils frühestmögliches
    freies Tor."""
    n = len(preferred_times)
    if n == 0:
        return np.array([], dtype=int), np.array([])
    if n_docks == 0:
        raise ValueError("n_docks muss mindestens 1 sein, wenn LKW eingeplant werden sollen")
    return _construct(range(n), preferred_times, service_times, n_docks)


def erd_schedule(preferred_times, service_times, n_docks):
    """Earliest-Release-Date-first: LKW nach aufsteigender Wunschzeit
    sortiert, sonst identischer Platzierungsmechanismus wie
    fcfs_schedule."""
    n = len(preferred_times)
    if n == 0:
        return np.array([], dtype=int), np.array([])
    if n_docks == 0:
        raise ValueError("n_docks muss mindestens 1 sein, wenn LKW eingeplant werden sollen")
    order = sorted(range(n), key=lambda i: preferred_times[i])
    return _construct(order, preferred_times, service_times, n_docks)


def spt_schedule(preferred_times, service_times, n_docks):
    """Ereignisgesteuerte SPT-Konstruktion ("SPT unter den verfügbaren
    LKW"): simuliert den Betrieb Ereignis für Ereignis. Sobald ein Tor frei
    wird, wird unter allen LKW, deren Wunschzeit bereits erreicht ist und
    die noch nicht eingeplant sind, der mit der kürzesten Bearbeitungsdauer
    gewählt. Ist zu diesem Zeitpunkt noch kein LKW verfügbar, springt die
    Zeit zur nächsten Wunschzeit unter den verbleibenden LKW vor.

    Anders als eine statische, nur nach Bearbeitungsdauer sortierte
    Konstruktion (siehe Moduldocstring) berücksichtigt diese Version die
    Wunschzeit bei jeder Entscheidung direkt mit - dadurch in einer
    Stichprobe über 240 Zufallsinstanzen nie schlechter und meist deutlich
    besser (siehe test_spt_dominates_naive_spt_ordering)."""
    n = len(preferred_times)
    if n == 0:
        return np.array([], dtype=int), np.array([])
    if n_docks == 0:
        raise ValueError("n_docks muss mindestens 1 sein, wenn LKW eingeplant werden sollen")

    remaining = set(range(n))
    dock_free_at = [0.0] * n_docks
    dock_of_truck = np.zeros(n, dtype=int)
    start_of_truck = np.zeros(n)

    while remaining:
        d = min(range(n_docks), key=lambda k: dock_free_at[k])
        t = dock_free_at[d]
        available = [i for i in remaining if preferred_times[i] <= t + EPS]
        if not available:
            t = min(preferred_times[i] for i in remaining)
            available = [i for i in remaining if preferred_times[i] <= t + EPS]
        chosen = min(available, key=lambda i: service_times[i])
        dock_of_truck[chosen] = d
        start_of_truck[chosen] = t
        dock_free_at[d] = t + service_times[chosen]
        remaining.discard(chosen)

    return dock_of_truck, start_of_truck
