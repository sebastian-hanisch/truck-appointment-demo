"""
Ein-Klick-Beispielszenarien und Permalink-Logik - dasselbe SETTING_SPECS-
Muster wie bei den anderen Demos: eine Wahrheitsquelle für Wertebereiche,
aus der sowohl die Slider als auch die Permalink-Begrenzung lesen, inklusive
NaN/Infinity-Schutz.
"""

import math
import random
from dataclasses import dataclass
from typing import Callable, Optional

import streamlit as st

from tas_constants import DEFAULT_N_DOCKS, DEFAULT_N_TRUCKS, DEFAULT_OPERATING_MINUTES


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: Callable
    default: object
    lo: Optional[float] = None
    hi: Optional[float] = None


SETTING_SPECS = {
    "n_trucks_slider": SettingSpec("n_trucks", int, DEFAULT_N_TRUCKS, 8, 80),
    "n_docks_slider": SettingSpec("n_docks", int, DEFAULT_N_DOCKS, 1, 10),
    "operating_minutes_slider": SettingSpec("op_min", float, DEFAULT_OPERATING_MINUTES, 240.0, 1440.0),
    "peak_concentration_slider": SettingSpec("peak_conc", float, 0.5, 0.0, 1.0),
    "n_peaks_slider": SettingSpec("n_peaks", int, 2, 1, 4),
    "seed_input": SettingSpec("seed", int, 7, 0, 2_000_000_000),
}


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def apply_preset(n_trucks_val, n_docks_val, op_min_val, peak_conc_val, n_peaks_val, seed_val):
    st.session_state["n_trucks_slider"] = n_trucks_val
    st.session_state["n_docks_slider"] = n_docks_val
    st.session_state["operating_minutes_slider"] = op_min_val
    st.session_state["peak_concentration_slider"] = peak_conc_val
    st.session_state["n_peaks_slider"] = n_peaks_val
    st.session_state["seed_input"] = seed_val
    st.session_state["force_regen"] = True


def randomize_seed():
    st.session_state["seed_input"] = random.randint(0, 2_000_000_000)
    st.session_state["force_regen"] = True


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    applied_any = False
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                value = spec.caster(qp[spec.url_param])
                if isinstance(value, float) and not math.isfinite(value):
                    continue
                if spec.lo is not None:
                    value = max(spec.lo, value)
                if spec.hi is not None:
                    value = min(spec.hi, value)
                st.session_state[state_key] = value
                applied_any = True
            except (ValueError, TypeError):
                pass
    if applied_any:
        st.session_state["force_regen"] = True
    st.session_state["permalink_loaded"] = True


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def sync_query_params(n_trucks, n_docks, operating_minutes, peak_concentration, n_peaks, seed):
    try:
        st.query_params["n_trucks"] = str(n_trucks)
        st.query_params["n_docks"] = str(n_docks)
        st.query_params["op_min"] = str(operating_minutes)
        st.query_params["peak_conc"] = str(peak_concentration)
        st.query_params["n_peaks"] = str(n_peaks)
        st.query_params["seed"] = str(int(seed))
    except Exception:
        pass
