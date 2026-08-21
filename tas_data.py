"""
Erzeugt ein Truck-Appointment-Scheduling-Szenario: LKW-Anmeldungen mit
bevorzugter Ankunftszeit und Bearbeitungsdauer, für eine gegebene Anzahl
paralleler Tore innerhalb eines Betriebszeitraums.
"""

import numpy as np


def generate_appointments(n_trucks, n_docks, seed, operating_minutes=720.0,
                           service_time_range=(20.0, 90.0), n_peaks=2, peak_concentration=0.5):
    """Erzeugt n_trucks bevorzugte Ankunftszeiten (Minuten ab Betriebsbeginn)
    und Bearbeitungsdauern (Minuten).

    peak_concentration: 0.0 = Wunschzeiten gleichverteilt über den gesamten
    Betriebszeitraum, höhere Werte (bis 1.0) = ein wachsender Anteil der
    LKW bevorzugt eine von n_peaks Stoßzeiten (z. B. Schichtwechsel) statt
    gleichmäßig über den Tag verteilt anzukommen.

    Gibt (preferred_times, service_times, peak_times) zurück.
    """
    rng = np.random.default_rng(seed)

    peak_times = rng.uniform(0, operating_minutes, size=max(1, n_peaks))
    is_peak = rng.random(n_trucks) < peak_concentration
    peak_choice = rng.integers(0, len(peak_times), size=n_trucks)
    peak_spread = operating_minutes * 0.06

    uniform_times = rng.uniform(0, operating_minutes, size=n_trucks)
    peak_sampled_times = rng.normal(peak_times[peak_choice], peak_spread)
    preferred_times = np.where(is_peak, peak_sampled_times, uniform_times)
    preferred_times = np.clip(preferred_times, 0, operating_minutes).round(0)

    lo, hi = service_time_range
    service_times = rng.uniform(lo, hi, size=n_trucks).round(0)

    return preferred_times, service_times, peak_times
