"""
Bewertet einen Zeitplan (Tor- und Startzeit-Zuordnung je LKW): berechnet
Gesamt- und Durchschnittswartezeit sowie den Makespan (späteste
Fertigstellung über alle Tore) - die für einen Betrieb tatsächlich
relevanten Kennzahlen. Bewusst keine künstliche €-Umrechnung: die
tatsächliche Kostenwirkung von Wartezeit hängt stark vom Vertragsmodell mit
den Spediteuren ab (Standgeld-Sätze variieren stark).
"""

import numpy as np

from tas_constants import EPS


def evaluate_schedule(preferred_times, service_times, dock_of_truck, start_of_truck):
    """Gibt ein Dict zurück: total_waiting_min, avg_waiting_min,
    max_waiting_min (jeweils Minuten), on_time_share (Anteil LKW ohne
    Wartezeit, in %) und makespan_min (späteste Fertigstellung, Minuten ab
    Betriebsbeginn)."""
    n = len(preferred_times)
    if n == 0:
        return {
            "total_waiting_min": 0.0, "avg_waiting_min": 0.0, "max_waiting_min": 0.0,
            "on_time_share": 0.0, "makespan_min": 0.0,
        }

    waiting = np.asarray(start_of_truck, dtype=float) - np.asarray(preferred_times, dtype=float)
    completion = np.asarray(start_of_truck, dtype=float) + np.asarray(service_times, dtype=float)

    return {
        "total_waiting_min": float(waiting.sum()),
        "avg_waiting_min": float(waiting.mean()),
        "max_waiting_min": float(waiting.max()),
        "on_time_share": float((waiting <= EPS).sum()) / n * 100.0,
        "makespan_min": float(completion.max()),
    }
