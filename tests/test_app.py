"""
Automatisierte Tests für die Truck-Appointment-Scheduling-Demo.

Zwei Ebenen, wie bei den anderen Demos:
1. UI-Tests über streamlit.testing.v1.AppTest.
2. Unit-Tests der reinen Logik-Funktionen (normale Imports, da die Logik in
   eigenen Modulen ohne Streamlit-UI-Code liegt).

Ausführen mit: pytest tests/ -v
"""

import os
import sys

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

APP_DIR = os.path.join(os.path.dirname(__file__), "..")
APP_PATH = os.path.join(APP_DIR, "app.py")
TIMEOUT = 90

sys.path.insert(0, os.path.abspath(APP_DIR))


def fresh_app():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=TIMEOUT)
    return at


def assert_ok(at):
    assert not at.exception, f"Unerwartete Exception(s): {[e.message for e in at.exception]}"


# ==========================================================================
# 1. UI-Tests (AppTest)
# ==========================================================================

def test_default_load():
    at = fresh_app()
    assert_ok(at)


def test_primary_view_shows_three_metrics():
    at = fresh_app()
    assert_ok(at)
    labels = [m.label for m in at.metric[:3]]
    assert labels == ["Ø Wartezeit", "Gesamtwartezeit", "Pünktlich"]


def test_primary_view_no_algorithm_name_in_headline():
    at = fresh_app()
    assert_ok(at)
    headlines = [str(m.value) for m in at.markdown if "Ihr optimierter Terminplan" in str(m.value)]
    assert headlines
    for name in ["FCFS", "ERD", "SPT"]:
        assert name not in headlines[0]


def test_primary_view_method_attribution_in_caption():
    at = fresh_app()
    assert_ok(at)
    captions = [str(c.value) for c in at.caption]
    assert any("drei eigenen Methoden" in c for c in captions)


@pytest.mark.parametrize("label", ["Ruhiger Tag", "Schichtwechsel-Stoßzeit", "Volle Auslastung"])
def test_presets_apply_without_crash(label):
    at = fresh_app()
    btn = [b for b in at.button if label in b.label][0]
    btn.click().run(timeout=TIMEOUT)
    assert_ok(at)


def test_regenerate_button():
    at = fresh_app()
    seed_before = at.sidebar.number_input(key="seed_input").value
    at.sidebar.button[0].click().run(timeout=TIMEOUT)
    assert_ok(at)
    seed_after = at.sidebar.number_input(key="seed_input").value
    assert seed_after != seed_before, "Seed hat sich durch den Klick nicht geändert"


@pytest.mark.parametrize("slider_idx,value", [(0, 80), (0, 8), (1, 10), (1, 1)])
def test_slider_extremes(slider_idx, value):
    at = fresh_app()
    at.sidebar.slider[slider_idx].set_value(value).run(timeout=TIMEOUT)
    assert_ok(at)


def test_worst_case_settings_no_crash():
    at = fresh_app()
    at.sidebar.slider[0].set_value(80).run(timeout=TIMEOUT)
    at.sidebar.slider[1].set_value(1).run(timeout=TIMEOUT)
    at.sidebar.slider[3].set_value(1.0).run(timeout=TIMEOUT)
    at.sidebar.slider[4].set_value(4).run(timeout=TIMEOUT)
    assert_ok(at)


def test_pdf_download_buttons_present():
    at = fresh_app()
    assert_ok(at)
    labels = [d.label for d in at.download_button]
    assert len(labels) == 4  # Primäransicht + FCFS + ERD + SPT
    assert all("PDF" in l for l in labels)


def test_feedback_buttons_work():
    at = fresh_app()
    up = [b for b in at.button if b.key == "feedback_up_btn"][0]
    up.click().run(timeout=TIMEOUT)
    assert_ok(at)
    assert any("Danke" in str(s.value) for s in at.success)


def test_comparison_tab_has_all_three_methods():
    at = fresh_app()
    assert_ok(at)
    comparison_dfs = [d for d in at.dataframe if "Methode" in d.value.columns]
    assert comparison_dfs
    methods = comparison_dfs[0].value["Methode"].tolist()
    assert "FCFS" in methods
    assert "ERD" in methods
    assert "SPT" in methods


def test_permalink_writes_and_restores():
    at = fresh_app()
    assert_ok(at)
    qp = dict(at.query_params)
    for key in ["n_trucks", "n_docks", "op_min", "peak_conc", "n_peaks", "seed"]:
        assert key in qp

    at2 = AppTest.from_file(APP_PATH)
    at2.query_params["n_trucks"] = "40"
    at2.run(timeout=TIMEOUT)
    assert_ok(at2)
    assert at2.sidebar.slider[0].value == 40


@pytest.mark.parametrize("param,value", [
    ("n_trucks", "9999"), ("n_trucks", "-5"), ("n_docks", "9999"),
    ("peak_conc", "nan"), ("peak_conc", "inf"), ("peak_conc", "-inf"),
    ("seed", "-42"), ("n_peaks", "not_a_number"), ("op_min", "9999999"),
])
def test_permalink_handles_bad_values_without_crash(param, value):
    at = AppTest.from_file(APP_PATH)
    at.query_params[param] = value
    at.run(timeout=TIMEOUT)
    assert_ok(at)


def test_slider_bounds_match_setting_specs():
    import tas_presets

    at = fresh_app()
    assert_ok(at)
    by_key = {s.key: s for s in at.sidebar.slider if s.key}
    checked = 0
    for state_key, spec in tas_presets.SETTING_SPECS.items():
        if spec.lo is None or state_key not in by_key:
            continue
        slider = by_key[state_key]
        assert slider.min == pytest.approx(spec.lo)
        assert slider.max == pytest.approx(spec.hi)
        checked += 1
    assert checked == 5, f"Nur {checked} von 5 erwarteten Slidern geprüft - Test greift vermutlich nicht vollständig"


def test_setting_specs_defaults_are_within_bounds():
    import tas_presets

    for state_key, spec in tas_presets.SETTING_SPECS.items():
        if spec.lo is not None:
            assert spec.lo <= spec.default <= spec.hi, f"{state_key}: Default außerhalb [{spec.lo},{spec.hi}]"


def test_permalink_url_params_are_unique():
    import tas_presets

    params = [spec.url_param for spec in tas_presets.SETTING_SPECS.values()]
    assert len(params) == len(set(params))


# ==========================================================================
# 2. Unit-Tests der reinen Funktionen
# ==========================================================================

from tas_data import generate_appointments
from tas_evaluation import evaluate_schedule
from tas_heuristics import _construct, _earliest_start, erd_schedule, fcfs_schedule, spt_schedule


def test_generate_appointments_shapes():
    preferred, service, peaks = generate_appointments(30, 4, seed=1)
    assert preferred.shape == (30,)
    assert service.shape == (30,)
    assert len(peaks) == 2  # Standard n_peaks


def test_generate_appointments_within_operating_window():
    preferred, service, peaks = generate_appointments(50, 4, seed=1, operating_minutes=600.0)
    assert (preferred >= 0).all()
    assert (preferred <= 600.0).all()


def test_generate_appointments_peak_concentration_effect():
    """Höhere peak_concentration sollte die Wunschzeiten stärker um wenige
    Stoßzeiten streuen (geringere Varianz relativ zur Gleichverteilung)."""
    preferred_low, _, _ = generate_appointments(200, 4, seed=1, peak_concentration=0.0, n_peaks=1)
    preferred_high, _, _ = generate_appointments(200, 4, seed=1, peak_concentration=1.0, n_peaks=1)
    assert np.std(preferred_high) < np.std(preferred_low)


def test_generate_appointments_zero_trucks_no_crash():
    preferred, service, peaks = generate_appointments(0, 4, seed=1)
    assert len(preferred) == 0
    assert len(service) == 0


# --- Bewertungslogik: handkonstruierte Fälle ---

def test_evaluate_schedule_hand_constructed():
    preferred = np.array([0.0, 10.0])
    service = np.array([20.0, 5.0])
    dock = np.array([0, 0])
    start = np.array([0.0, 20.0])  # zweiter LKW wartet 10 min (20-10)
    result = evaluate_schedule(preferred, service, dock, start)
    assert result["total_waiting_min"] == pytest.approx(10.0)
    assert result["avg_waiting_min"] == pytest.approx(5.0)
    assert result["max_waiting_min"] == pytest.approx(10.0)
    assert result["on_time_share"] == pytest.approx(50.0)
    assert result["makespan_min"] == pytest.approx(25.0)


def test_evaluate_schedule_empty_no_crash():
    result = evaluate_schedule(np.array([]), np.array([]), np.array([]), np.array([]))
    assert result["total_waiting_min"] == 0.0


# --- Heuristiken: Machbarkeit (keine Überlappungen, kein Start vor Wunschzeit) ---

def _assert_feasible(preferred, service, dock, start, n_docks):
    for d in range(n_docks):
        idxs = sorted((i for i in range(len(dock)) if dock[i] == d), key=lambda i: start[i])
        for a, b in zip(idxs, idxs[1:]):
            assert start[a] + service[a] <= start[b] + 1e-6, "Überlappung am selben Tor gefunden"
    assert all(start[i] >= preferred[i] - 1e-6 for i in range(len(dock))), "LKW vor seiner Wunschzeit gestartet"


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("heuristic", [fcfs_schedule, erd_schedule, spt_schedule])
def test_heuristics_produce_feasible_schedules(heuristic, seed):
    preferred, service, peaks = generate_appointments(30, 4, seed=seed, peak_concentration=0.6, n_peaks=2)
    dock, start = heuristic(preferred, service, 4)
    _assert_feasible(preferred, service, dock, start, 4)
    assert len(dock) == 30 and len(start) == 30
    assert all(0 <= d < 4 for d in dock)


def test_heuristics_handle_zero_trucks():
    preferred, service, peaks = generate_appointments(0, 4, seed=1)
    for heuristic in [fcfs_schedule, erd_schedule, spt_schedule]:
        dock, start = heuristic(preferred, service, 4)
        assert len(dock) == 0 and len(start) == 0


def test_erd_matches_fcfs_when_arrival_order_equals_preferred_order():
    """Wenn die Wunschzeiten bereits aufsteigend nach Index sortiert sind,
    muss ERD (sortiert nach Wunschzeit) dasselbe Ergebnis liefern wie FCFS
    (sortiert nach Index) - beide verarbeiten dann dieselbe Reihenfolge."""
    preferred = np.array([0.0, 10.0, 20.0, 30.0])
    service = np.array([15.0, 5.0, 25.0, 10.0])
    dock_f, start_f = fcfs_schedule(preferred, service, 2)
    dock_e, start_e = erd_schedule(preferred, service, 2)
    assert list(dock_f) == list(dock_e)
    assert list(start_f) == list(start_e)


def test_erd_beats_fcfs_on_average(seed_range=range(1, 11)):
    """Qualitäts-Sanity-Check: ERD soll im Schnitt eine geringere
    durchschnittliche Wartezeit liefern als FCFS - das ist der
    Daseinszweck der Wunschzeit-Priorisierung."""
    deltas = []
    for seed in seed_range:
        preferred, service, peaks = generate_appointments(30, 4, seed=seed, peak_concentration=0.6, n_peaks=2)
        dock_f, start_f = fcfs_schedule(preferred, service, 4)
        dock_e, start_e = erd_schedule(preferred, service, 4)
        wf = evaluate_schedule(preferred, service, dock_f, start_f)["avg_waiting_min"]
        we = evaluate_schedule(preferred, service, dock_e, start_e)["avg_waiting_min"]
        deltas.append(wf - we)
    assert sum(deltas) / len(deltas) > 0.0


def test_spt_beats_erd_on_average(seed_range=range(1, 11)):
    """Qualitäts-Sanity-Check analog zu test_erd_beats_fcfs_on_average: SPT
    (ereignisgesteuert, verfügbarkeitsbewusst) soll im Schnitt nochmal
    besser abschneiden als ERD."""
    deltas = []
    for seed in seed_range:
        preferred, service, peaks = generate_appointments(30, 4, seed=seed, peak_concentration=0.6, n_peaks=2)
        dock_e, start_e = erd_schedule(preferred, service, 4)
        dock_s, start_s = spt_schedule(preferred, service, 4)
        we = evaluate_schedule(preferred, service, dock_e, start_e)["avg_waiting_min"]
        ws = evaluate_schedule(preferred, service, dock_s, start_s)["avg_waiting_min"]
        deltas.append(we - ws)
    assert sum(deltas) / len(deltas) > 0.0


def test_spt_dominates_naive_static_spt_ordering():
    """Regressionstest für den beim Bauen gefundenen Fehler: eine naive
    Konstruktion, die LKW einmalig global nach Bearbeitungsdauer sortiert
    (ohne die Wunschzeit beim Sortieren zu berücksichtigen), kann einen
    bereits verfügbaren langen Auftrag unnötig hinter einen erst später
    verfügbaren kurzen Auftrag zurückstellen. Über 40 Zufallsinstanzen war
    die ereignisgesteuerte spt_schedule() nie schlechter und meist deutlich
    besser als diese naive Variante."""
    def naive_static_spt(preferred, service, n_docks):
        order = sorted(range(len(preferred)), key=lambda i: service[i])
        return _construct(order, preferred, service, n_docks)

    worse_count = 0
    deltas = []
    for seed in range(1, 41):
        preferred, service, peaks = generate_appointments(24, 4, seed=seed, peak_concentration=0.6, n_peaks=2)
        dock_naive, start_naive = naive_static_spt(preferred, service, 4)
        dock_dyn, start_dyn = spt_schedule(preferred, service, 4)
        w_naive = evaluate_schedule(preferred, service, dock_naive, start_naive)["avg_waiting_min"]
        w_dyn = evaluate_schedule(preferred, service, dock_dyn, start_dyn)["avg_waiting_min"]
        if w_dyn > w_naive + 1e-6:
            worse_count += 1
        deltas.append(w_naive - w_dyn)
    assert worse_count == 0
    assert sum(deltas) / len(deltas) > 0.0


def test_spt_hand_constructed_case_where_naive_ordering_fails():
    """Handkonstruierter Fall mit bekanntem, eindeutig besserem Ergebnis:
    ein langer, sofort verfügbarer Auftrag und ein kurzer, erst später
    verfügbarer Auftrag an einem einzelnen Tor. Naives statisches SPT
    plant den kurzen Auftrag zuerst ein (kürzere Dauer), obwohl er noch
    gar nicht verfügbar ist, und blockiert dadurch den langen Auftrag
    unnötig."""
    preferred = np.array([0.0, 50.0])
    service = np.array([100.0, 1.0])

    def naive_static_spt(preferred, service, n_docks):
        order = sorted(range(len(preferred)), key=lambda i: service[i])
        return _construct(order, preferred, service, n_docks)

    dock_naive, start_naive = naive_static_spt(preferred, service, 1)
    dock_dyn, start_dyn = spt_schedule(preferred, service, 1)

    w_naive = evaluate_schedule(preferred, service, dock_naive, start_naive)["total_waiting_min"]
    w_dyn = evaluate_schedule(preferred, service, dock_dyn, start_dyn)["total_waiting_min"]

    assert w_naive == pytest.approx(51.0)
    assert w_dyn == pytest.approx(50.0)
    assert w_dyn < w_naive


def test_earliest_start_finds_gap_between_bookings():
    intervals = [(0.0, 10.0), (30.0, 40.0)]
    assert _earliest_start(intervals, preferred_time=5.0, service_time=15.0) == pytest.approx(10.0)
    assert _earliest_start(intervals, preferred_time=15.0, service_time=10.0) == pytest.approx(15.0)


def test_earliest_start_empty_intervals_returns_preferred_time():
    assert _earliest_start([], preferred_time=42.0, service_time=10.0) == pytest.approx(42.0)


# --- PDF-Export ---

def test_generate_schedule_plan_pdf_produces_valid_pdf():
    from tas_pdf_export import generate_schedule_plan_pdf

    preferred, service, peaks = generate_appointments(12, 3, seed=2)
    dock, start = spt_schedule(preferred, service, 3)
    pdf_bytes = generate_schedule_plan_pdf("Test", preferred, service, dock, start)
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 500


# --- Feedback ---

def test_feedback_log_and_count_roundtrip(tmp_path):
    from tas_feedback import get_feedback_counts, log_feedback

    log_file = str(tmp_path / "feedback_test.csv")
    assert get_feedback_counts(log_file) == (0, 0)
    assert log_feedback("up", log_file) is True
    assert log_feedback("down", log_file) is True
    assert log_feedback("up", log_file) is True
    assert get_feedback_counts(log_file) == (2, 1)


# --- Visualisierung ---

def test_format_clock_wraps_correctly():
    from tas_visualization import format_clock

    assert format_clock(0) == "06:00"
    assert format_clock(60) == "07:00"
    assert format_clock(18 * 60) == "00:00"  # ueber Mitternacht


def test_build_gantt_figure_handles_zero_trucks():
    from tas_visualization import build_gantt_figure

    fig = build_gantt_figure(np.array([]), np.array([]), np.array([]), np.array([]), 3, 720.0, peak_times=[])
    assert fig is not None
