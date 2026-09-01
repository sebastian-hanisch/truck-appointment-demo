"""
Gantt-Chart-Visualisierung (Plotly): LKW als horizontale Balken je Tor, von
Startzeit bis Fertigstellung, eingefärbt nach Wartezeit (grün = pünktlich,
rot = lange Wartezeit). Bevorzugte Ankunftszeit je LKW als kleiner Strich
markiert, Stoßzeiten als vertikale gepunktete Linien.
"""

import numpy as np
import plotly.graph_objects as go

REFERENCE_START_HOUR = 6.0  # Betriebsbeginn als Uhrzeit - rein kosmetisch fuer die Achsenbeschriftung

WAIT_COLOR_LOW = (22, 163, 74)   # #16a34a, kein/kaum Warten
WAIT_COLOR_HIGH = (220, 38, 38)  # #dc2626, lange Wartezeit


def format_clock(minutes):
    total_minutes = int(round(minutes)) + int(REFERENCE_START_HOUR * 60)
    h, m = divmod(total_minutes % (24 * 60), 60)
    return f"{h:02d}:{m:02d}"


def _wait_color(wait, max_wait):
    t = 0.0 if max_wait <= 0 else max(0.0, min(1.0, wait / max_wait))
    rgb = tuple(int(round(a + (b - a) * t)) for a, b in zip(WAIT_COLOR_LOW, WAIT_COLOR_HIGH))
    return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"


def build_gantt_figure(preferred_times, service_times, dock_of_truck, start_of_truck, n_docks,
                        operating_minutes, peak_times=None):
    fig = go.Figure()
    n = len(preferred_times)
    dock_labels = [f"Tor {d + 1}" for d in range(n_docks)]

    waiting = [float(start_of_truck[i] - preferred_times[i]) for i in range(n)]
    max_wait = max(waiting) if waiting else 0.0

    for i in range(n):
        d = int(dock_of_truck[i])
        w = waiting[i]
        fig.add_trace(
            go.Bar(
                base=[float(start_of_truck[i])], x=[float(service_times[i])], y=[dock_labels[d]],
                orientation="h", width=0.6,
                marker=dict(color=_wait_color(w, max_wait), line=dict(width=1, color="white")),
                hovertext=(
                    f"LKW {i + 1}<br>Wunsch {format_clock(preferred_times[i])}<br>"
                    f"Start {format_clock(start_of_truck[i])}<br>Wartezeit {w:.0f} min"
                ),
                hoverinfo="text", showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[float(preferred_times[i])], y=[dock_labels[d]], mode="markers",
                marker=dict(symbol="line-ns", size=16, line=dict(width=2, color="#111827")),
                hoverinfo="skip", showlegend=False,
            )
        )

    if peak_times is not None:
        for pt in peak_times:
            fig.add_vline(x=float(pt), line=dict(color="#9ca3af", width=1, dash="dot"))

    tick_step = max(60.0, operating_minutes / 8)
    tick_vals = list(np.arange(0, operating_minutes + tick_step, tick_step))
    tick_text = [format_clock(v) for v in tick_vals]

    fig.update_layout(
        xaxis=dict(
            title="Uhrzeit", range=[-5, operating_minutes + 5],
            tickvals=tick_vals, ticktext=tick_text, zeroline=False,
        ),
        yaxis=dict(
            title="Tor", categoryorder="array",
            categoryarray=list(reversed(dock_labels)) if dock_labels else [],
        ),
        height=max(260, 70 * n_docks + 120), margin=dict(l=10, r=10, t=30, b=10),
        barmode="overlay",
    )
    # fixedrange auf beiden Achsen: verhindert Pinch-Zoom/Drag-Pan im Chart,
    # damit auf Touch-Geräten stattdessen die Seite normal gescrollt wird
    # (Hover-Tooltips bleiben davon unberührt).
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig
