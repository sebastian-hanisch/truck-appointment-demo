"""Unabhaengige Orakel fuer die Terminvergabe: exakter Optimalwert per Brute Force (alle
Reihenfolgen x Torzuordnungen, semi-aktive Startzeiten) auf winzigen Instanzen, Brute-Force-Suche
des fruehesten freien Slots und Neuplatzierungs-Orakel (ein LKW wird entfernt und gegen alle
anderen Buchungen neu eingeplant) fuer die im README behauptete Wirkungslosigkeit lokaler
Verbesserung."""

import itertools
import random

import numpy as np

from tas_data import generate_appointments
from tas_evaluation import evaluate_schedule
from tas_heuristics import _earliest_start, erd_schedule, fcfs_schedule, spt_schedule

HEURISTICS = (fcfs_schedule, erd_schedule, spt_schedule)


def _feasible(pref, svc, dock, start):
    n = len(pref)
    if any(start[i] < pref[i] - 1e-9 for i in range(n)):
        return False
    for i in range(n):
        for j in range(i + 1, n):
            if dock[i] == dock[j] and start[i] < start[j] + svc[j] - 1e-9 and start[j] < start[i] + svc[i] - 1e-9:
                return False
    return True


def _optimum(pref, svc, m):
    n = len(pref)
    best = float("inf")
    for perm in itertools.permutations(range(n)):
        for assign in itertools.product(range(m), repeat=n):
            if assign[0] != 0:
                continue
            free = [0.0] * m
            total = 0.0
            for k, j in enumerate(perm):
                d = assign[k]
                s = max(pref[j], free[d])
                free[d] = s + svc[j]
                total += s - pref[j]
                if total >= best:
                    break
            else:
                best = min(best, total)
    return best


def _earliest_bruteforce(bookings, pref, p):
    for c in sorted({pref} | {e for _s, e in bookings if e >= pref}):
        if all(c + p <= s + 1e-9 or c >= e - 1e-9 for s, e in bookings):
            return c


def test_hand_example_optimum_is_50_and_spt_attains_it():
    pref, svc = np.array([0.0, 50.0]), np.array([100.0, 1.0])  # README: langer LKW L, kurzer LKW S
    assert _optimum(list(pref), list(svc), 1) == 50.0
    _d, s = spt_schedule(pref, svc, 1)
    assert float(np.sum(s - pref)) == 50.0


def test_heuristics_feasible_and_never_below_exact_optimum():
    rng = random.Random(1)
    gaps = {f.__name__: [] for f in HEURISTICS}
    for _ in range(120):
        n, m = rng.randint(2, 5), rng.randint(1, 3)
        pref = [float(rng.randint(0, 30)) for _ in range(n)]
        svc = [float(rng.randint(1, 20)) for _ in range(n)]
        opt = _optimum(pref, svc, m)
        for f in HEURISTICS:
            d, s = f(np.array(pref), np.array(svc), m)
            assert _feasible(pref, svc, d, s)
            ev = evaluate_schedule(np.array(pref), np.array(svc), d, s)
            total = sum(s[i] - pref[i] for i in range(n))
            assert abs(ev["total_waiting_min"] - total) < 1e-9
            assert abs(ev["avg_waiting_min"] - total / n) < 1e-9
            assert abs(ev["makespan_min"] - max(s[i] + svc[i] for i in range(n))) < 1e-9
            assert total >= opt - 1e-9
            gaps[f.__name__].append(total - opt)
    # SPT ist in dieser Stichprobe im Mittel am naechsten am Optimum
    assert np.mean(gaps["spt_schedule"]) <= np.mean(gaps["erd_schedule"]) <= np.mean(gaps["fcfs_schedule"])


def test_earliest_start_matches_bruteforce_search():
    rng = random.Random(2)
    for _ in range(1500):
        t, iv = 0.0, []
        for _k in range(rng.randint(0, 6)):
            t += rng.choice([0, 0, 1, 5, 20])
            d = rng.randint(1, 30)
            iv.append((t, t + d))
            t += d
        pref, p = float(rng.choice([0, 3, 10, 25, 60, 100])), float(rng.randint(1, 40))
        assert abs(_earliest_start(sorted(iv), pref, p) - _earliest_bruteforce(iv, pref, p)) < 1e-9


def test_no_single_truck_relocation_improves_any_schedule():
    """README/Mathematik-Expander: lokale Verbesserung durch Neuplatzierung findet nie etwas."""
    rng = random.Random(3)
    for k in range(25):
        n, m = rng.randint(12, 30), rng.randint(1, 4)
        pref, svc, _pk = generate_appointments(n, m, k, n_peaks=rng.randint(1, 2), peak_concentration=rng.random())
        for f in HEURISTICS:
            dock, start = f(pref, svc, m)
            for i in range(n):
                for d in range(m):
                    bookings = [(start[j], start[j] + svc[j]) for j in range(n) if j != i and dock[j] == d]
                    assert _earliest_bruteforce(bookings, float(pref[i]), float(svc[i])) >= start[i] - 1e-9
