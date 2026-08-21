"""
Wiederverwendbares Streamlit-UI-Panel für ein einzelnes Zeitplan-Verfahren:
Kennzahlen, Gantt-Chart, PDF-Export.
"""

import streamlit as st

from tas_evaluation import evaluate_schedule
from tas_pdf_export import generate_schedule_plan_pdf
from tas_visualization import build_gantt_figure


def render_schedule_panel(prefix, label, preferred_times, service_times, dock_of_truck, start_of_truck,
                           n_docks, operating_minutes, peak_times):
    stats = evaluate_schedule(preferred_times, service_times, dock_of_truck, start_of_truck)

    m1, m2, m3 = st.columns(3)
    m1.metric("Ø Wartezeit", f"{stats['avg_waiting_min']:.1f} min")
    m2.metric("Gesamtwartezeit", f"{stats['total_waiting_min']:.0f} min")
    m3.metric("Pünktlich", f"{stats['on_time_share']:.0f}%")

    fig = build_gantt_figure(
        preferred_times, service_times, dock_of_truck, start_of_truck, n_docks, operating_minutes, peak_times,
    )
    st.plotly_chart(fig, width="stretch", key=f"{prefix}_plot")
    st.caption(
        "Balkenfarbe nach Wartezeit (grün = pünktlich, rot = lange Wartezeit). Der senkrechte Strich "
        "markiert die bevorzugte Ankunftszeit, gepunktete Linien markieren Stoßzeiten."
    )

    pdf_bytes = generate_schedule_plan_pdf(label, preferred_times, service_times, dock_of_truck, start_of_truck)
    st.download_button(
        "📄 Terminplan als PDF herunterladen", data=pdf_bytes,
        file_name=f"terminplan_{prefix}.pdf", mime="application/pdf", key=f"{prefix}_pdf_download",
    )

    return {
        "label": label, "dock_of_truck": dock_of_truck, "start_of_truck": start_of_truck, **stats,
    }
