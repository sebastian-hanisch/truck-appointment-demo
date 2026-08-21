"""
Truck-Appointment-Scheduling für die Umschlaghalle – interaktive Demo
Sebastian Hanisch - Operations Research und Machine Learning

Fünfte Demo im Portfolio, nach Tourenplanung (VRP), 3D-Packungsoptimierung,
Liniennetz-Design (ÖPNV) und Tor-Zuordnung (Dock Door Assignment). Anders
als die Tor-Zuordnung (rein räumlich, keine Zeitdimension) und die
Seefracht-Konsolidierung (Bin-Packing + Facility-Wahl) ist das hier ein
echtes Scheduling-Problem: jedem LKW muss ein (Tor, Startzeit)-Paar
zugewiesen werden, ohne Überlappungen am selben Tor und mit Start nicht vor
der bevorzugten Ankunftszeit, mit dem Ziel, die Gesamtwartezeit zu
minimieren - ein Parallel-Maschinen-Scheduling-Problem mit Freigabeterminen.

Selbe Methodik wie bei den anderen vier Demos: Konstruktionsheuristik +
Bewertung + Vergleich, Ergebnis zuerst ("Ihr optimierter Terminplan"),
Methodenvergleich sekundär im Expander. Anders als bei der Tor-Zuordnung
sind es hier drei Konstruktionsheuristiken (klassische Scheduling-
Prioritätsregeln) statt Konstruktion + lokaler Verbesserung - eine
nachträgliche Verbesserungssuche wurde geprüft und wieder verworfen, siehe
README und den Docstring von tas_heuristics.py.

Lauffähig mit: streamlit run app.py
"""

import pandas as pd
import streamlit as st

from tas_data import generate_appointments
from tas_evaluation import evaluate_schedule
from tas_feedback import log_feedback
from tas_heuristics import erd_schedule, fcfs_schedule, spt_schedule
from tas_pdf_export import generate_schedule_plan_pdf
from tas_presets import apply_preset, bounds, init_session_state_defaults, load_permalink_settings, randomize_seed, sync_query_params
from tas_ui_panel import render_schedule_panel
from tas_visualization import build_gantt_figure, format_clock

st.set_page_config(page_title="Truck-Appointment-Scheduling – Sebastian Hanisch", layout="wide")

st.title("🚚 Truck-Appointment-Scheduling")
st.markdown(
    """
Interaktive Demo zur Terminvergabe für LKW-Anlieferungen an einer Umschlaghalle. Drei selbst
implementierte Scheduling-Prioritätsregeln – **FCFS** (First-Come-First-Served, LKW in
Anmeldereihenfolge ohne Priorisierung), **ERD** (Earliest-Release-Date-first, nach Wunschzeit
sortiert) und **SPT** (Shortest-Processing-Time-first unter den jeweils verfügbaren LKW,
ereignisgesteuert) – werden direkt verglichen. Zielgröße ist die Gesamtwartezeit: jeder LKW darf
frühestens zu seiner Wunschzeit starten, ohne Überlappung mit anderen LKW am selben Tor. Ein
Parallel-Maschinen-Scheduling-Problem mit Freigabeterminen – anders als die räumliche
Tor-Zuordnung der Schwester-Demo kommt hier zum ersten Mal eine echte Zeitdimension dazu.
"""
)

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
preset_col1, preset_col2, preset_col3 = st.columns(3)
with preset_col1:
    st.button(
        "😌 Ruhiger Tag", width="stretch",
        on_click=apply_preset, args=(16, 4, 720.0, 0.2, 1, 5),
        help="Wenige LKW, Wunschzeiten eher gleichmäßig über den Tag verteilt.",
    )
with preset_col2:
    st.button(
        "⏰ Schichtwechsel-Stoßzeit", width="stretch",
        on_click=apply_preset, args=(30, 4, 720.0, 0.85, 1, 11),
        help="Die meisten LKW wollen zur selben Stoßzeit ankommen (z. B. Schichtwechsel).",
    )
with preset_col3:
    st.button(
        "🔥 Volle Auslastung", width="stretch",
        on_click=apply_preset, args=(40, 3, 720.0, 0.6, 2, 9),
        help="Viele LKW auf wenige Tore - die Tore sind nahe an ihrer Kapazitätsgrenze.",
    )

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    n_trucks = st.slider(
        "Anzahl LKW", *bounds("n_trucks_slider"), key="n_trucks_slider",
        help="Gesamtzahl der Anlieferungen, die heute terminiert werden müssen.",
    )
    n_docks = st.slider(
        "Anzahl Tore", *bounds("n_docks_slider"), key="n_docks_slider",
        help="Parallele Andockstellen - jedes Tor kann zu jedem Zeitpunkt genau einen LKW "
        "bedienen. Mehr Tore bei gleicher LKW-Zahl bedeuten in der Regel kürzere Wartezeiten.",
    )
    operating_minutes = st.slider(
        "Betriebszeitraum (Minuten)", *bounds("operating_minutes_slider"), step=30.0, key="operating_minutes_slider",
        help="Länge des Betriebstags in Minuten (Standard 720 = 12 Stunden). Bestimmt, über "
        "welchen Zeitraum sich die Wunschzeiten verteilen können.",
    )

    st.markdown("**Ankunftsmuster**")
    peak_concentration = st.slider(
        "Konzentration auf Stoßzeiten", *bounds("peak_concentration_slider"), step=0.05, key="peak_concentration_slider",
        help="0 = Wunschzeiten gleichmäßig über den Tag verteilt, 1 = die meisten LKW wollen zu "
        "einer von wenigen Stoßzeiten ankommen (z. B. Schichtwechsel). Je höher der Wert, desto "
        "größer ist in der Regel der Vorteil von ERD/SPT gegenüber FCFS.",
    )
    n_peaks = st.slider(
        "Anzahl Stoßzeiten", *bounds("n_peaks_slider"), key="n_peaks_slider",
        help="Wie viele unterschiedliche Stoßzeiten es gibt, auf die sich Wunschzeiten "
        "konzentrieren können.",
    )
    seed = st.number_input(
        "Zufalls-Seed", step=1, key="seed_input",
        help="Steuert die Zufallsgenerierung von Wunschzeiten und Bearbeitungsdauern. Gleicher "
        "Seed + gleiche Einstellungen ergeben immer exakt dasselbe Szenario - reproduzierbar "
        "und über die Adresszeile teilbar.",
    )

    st.button(
        "🎲 Neues Szenario generieren", width="stretch", on_click=randomize_seed,
        help="Würfelt einen neuen Zufalls-Seed und erzeugt damit ein komplett neues Szenario - "
        "praktisch, ohne selbst eine neue Seed-Zahl eintippen zu müssen.",
    )

sync_query_params(n_trucks, n_docks, operating_minutes, peak_concentration, n_peaks, seed)

if "force_regen" not in st.session_state:
    st.session_state.force_regen = False

gen_key = (n_trucks, n_docks, operating_minutes, peak_concentration, n_peaks, int(seed))
needs_init = (
    "gen_key_cache" not in st.session_state or st.session_state.force_regen
    or st.session_state.get("gen_key_cache") != gen_key
)
if needs_init:
    preferred_times, service_times, peak_times = generate_appointments(
        n_trucks, n_docks, int(seed), operating_minutes=operating_minutes,
        peak_concentration=peak_concentration, n_peaks=n_peaks,
    )
    dock_fcfs, start_fcfs = fcfs_schedule(preferred_times, service_times, n_docks)
    dock_erd, start_erd = erd_schedule(preferred_times, service_times, n_docks)
    dock_spt, start_spt = spt_schedule(preferred_times, service_times, n_docks)
    st.session_state.preferred_times = preferred_times
    st.session_state.service_times = service_times
    st.session_state.peak_times = peak_times
    # Zeitpläne mitcachen statt bei jedem Rerun (z. B. Expander auf-/zuklappen) neu zu
    # berechnen - analog zur Tor-Zuordnungs-Demo.
    st.session_state.dock_fcfs = dock_fcfs
    st.session_state.start_fcfs = start_fcfs
    st.session_state.dock_erd = dock_erd
    st.session_state.start_erd = start_erd
    st.session_state.dock_spt = dock_spt
    st.session_state.start_spt = start_spt
    st.session_state.gen_key_cache = gen_key
    st.session_state.force_regen = False

preferred_times = st.session_state.preferred_times
service_times = st.session_state.service_times
peak_times = st.session_state.peak_times
truck_ids = list(range(1, n_trucks + 1))

with st.expander("📦 LKW-Anmeldungen (nicht editierbar – an die Generierung gekoppelt)"):
    appointments_df = pd.DataFrame({
        "LKW": truck_ids,
        "Wunschzeit": [format_clock(t) for t in preferred_times],
        "Bearbeitungsdauer (min)": service_times.round(0),
    })
    st.dataframe(appointments_df, width="stretch", hide_index=True)

dock_fcfs = st.session_state.dock_fcfs
start_fcfs = st.session_state.start_fcfs
dock_erd = st.session_state.dock_erd
start_erd = st.session_state.start_erd
dock_spt = st.session_state.dock_spt
start_spt = st.session_state.start_spt

stats_fcfs = evaluate_schedule(preferred_times, service_times, dock_fcfs, start_fcfs)
stats_erd = evaluate_schedule(preferred_times, service_times, dock_erd, start_erd)
stats_spt = evaluate_schedule(preferred_times, service_times, dock_spt, start_spt)

# Beste der drei Methoden fuer die Primaeransicht: geringere durchschnittliche
# Wartezeit gewinnt. Baseline fuer den Vergleich ist immer FCFS (nicht "die
# jeweils andere Methode") - eindeutig definiert, auch mit drei Kandidaten.
candidates = [
    {"key": "fcfs", "label": "FCFS", "dock": dock_fcfs, "start": start_fcfs, **stats_fcfs},
    {"key": "erd", "label": "ERD", "dock": dock_erd, "start": start_erd, **stats_erd},
    {"key": "spt", "label": "SPT", "dock": dock_spt, "start": start_spt, **stats_spt},
]
best = min(candidates, key=lambda c: c["avg_waiting_min"])
baseline = next(c for c in candidates if c["key"] == "fcfs")

st.markdown("## 🎯 Ihr optimierter Terminplan")

reduction_pct = 0.0
if baseline["avg_waiting_min"] > 0:
    reduction_pct = (baseline["avg_waiting_min"] - best["avg_waiting_min"]) / baseline["avg_waiting_min"] * 100

m1, m2, m3 = st.columns(3)
m1.metric(
    "Ø Wartezeit", f"{best['avg_waiting_min']:.1f} min",
    delta=f"{-reduction_pct:+.1f}% ggü. FCFS", delta_color="inverse",
)
m2.metric("Gesamtwartezeit", f"{best['total_waiting_min']:.0f} min")
m3.metric("Pünktlich", f"{best['on_time_share']:.0f}%")

if reduction_pct > 1.0:
    st.success(
        f"💡 Mit '{best['label']}' sinkt die durchschnittliche Wartezeit um "
        f"**{reduction_pct:.1f}%** gegenüber '{baseline['label']}' – weniger Standzeit für "
        f"Spediteure und ein gleichmäßiger ausgelasteter Betrieb."
    )

fig_best = build_gantt_figure(
    preferred_times, service_times, best["dock"], best["start"], n_docks, operating_minutes, peak_times,
)
st.plotly_chart(fig_best, width="stretch", key="primary_best_plot")
st.caption(
    "Balkenfarbe nach Wartezeit (grün = pünktlich, rot = lange Wartezeit). Der senkrechte "
    "Strich markiert die bevorzugte Ankunftszeit, gepunktete Linien markieren Stoßzeiten."
)

pdf_bytes_best = generate_schedule_plan_pdf("Optimierter Terminplan", preferred_times, service_times, best["dock"], best["start"])
st.download_button(
    "📄 Terminplan als PDF herunterladen", data=pdf_bytes_best,
    file_name="terminplan_optimiert.pdf", mime="application/pdf", key="primary_pdf_download",
)

st.caption("Ermittelt mit der besten von drei eigenen Methoden für dieses Szenario. Details unten.")

st.markdown("---")

with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich", expanded=False):
    tabs = st.tabs(["🔢 FCFS", "📅 ERD", "📈 SPT", "📊 Vergleich"])

    with tabs[0]:
        st.caption("LKW in Anmeldereihenfolge, jeweils frühestmögliches freies Tor - repräsentiert eine ungeplante Terminvergabe ohne Priorisierung.")
        summary_fcfs = render_schedule_panel("fcfs", "FCFS", preferred_times, service_times, dock_fcfs, start_fcfs, n_docks, operating_minutes, peak_times)

    with tabs[1]:
        st.caption("LKW nach aufsteigender Wunschzeit sortiert (Earliest Release Date first), sonst derselbe Platzierungsmechanismus wie FCFS.")
        summary_erd = render_schedule_panel("erd", "ERD", preferred_times, service_times, dock_erd, start_erd, n_docks, operating_minutes, peak_times)

    with tabs[2]:
        st.caption(
            "Ereignisgesteuert: sobald ein Tor frei wird, übernimmt der LKW mit der kürzesten "
            "Bearbeitungsdauer unter den zu diesem Zeitpunkt bereits verfügbaren (siehe README "
            "für die Details, inklusive einer beim Benchmarking gefundenen und korrigierten "
            "Schwäche einer ersten, einfacheren Version)."
        )
        summary_spt = render_schedule_panel("spt", "SPT", preferred_times, service_times, dock_spt, start_spt, n_docks, operating_minutes, peak_times)

    with tabs[3]:
        st.markdown("### Methodenvergleich")

        comp_rows = []
        for c in [summary_fcfs, summary_erd, summary_spt]:
            comp_rows.append({
                "Methode": c["label"],
                "Ø Wartezeit": f"{c['avg_waiting_min']:.1f} min",
                "Gesamtwartezeit": f"{c['total_waiting_min']:.0f} min",
                "Pünktlich": f"{c['on_time_share']:.0f}%",
                "Makespan": f"{format_clock(c['makespan_min'])}",
            })
        st.dataframe(pd.DataFrame(comp_rows), width="stretch", hide_index=True)
        st.caption(
            "Alle drei Methoden werden mit derselben Bewertungsfunktion gegen dasselbe Szenario "
            "verglichen - fair vergleichbar, auch wenn die Konstruktionsstrategien sehr unterschiedlich sind."
        )

        vis_col1, vis_col2, vis_col3 = st.columns(3)
        for col, summary, key in [
            (vis_col1, summary_fcfs, "compare_fcfs_plot"),
            (vis_col2, summary_erd, "compare_erd_plot"),
            (vis_col3, summary_spt, "compare_spt_plot"),
        ]:
            with col:
                st.markdown(f"**{summary['label']}**")
                fig_compare = build_gantt_figure(
                    preferred_times, service_times, summary["dock_of_truck"], summary["start_of_truck"],
                    n_docks, operating_minutes, peak_times,
                )
                st.plotly_chart(fig_compare, width="stretch", key=key)
        st.caption("Gleiche LKW-Anmeldungen in allen drei Zeitplänen - nur die Zuordnung zu Tor und Startzeit unterscheidet sich.")

with st.expander("Wie funktioniert diese Demo?"):
    st.markdown(
        """
**Die Problemstellung:** Jedem LKW muss ein (Tor, Startzeit)-Paar zugewiesen werden - keine
Überlappung mit anderen LKW am selben Tor, kein Start vor der bevorzugten Ankunftszeit, mit dem
Ziel, die Gesamtwartezeit (Start − Wunschzeit, aufsummiert über alle LKW) zu minimieren. Formal
ein **Parallel-Maschinen-Scheduling-Problem mit Freigabeterminen** (jedes Tor ist eine
"Maschine", jeder LKW ein "Auftrag" mit Bearbeitungsdauer und frühestem Starttermin) - eine gut
untersuchte Problemklasse der Scheduling-Theorie, praxisrelevant unter dem Namen Truck
Appointment Scheduling seit Häfen und Distributionszentren begonnen haben, feste Zeitfenster
statt freier Anfahrt zu vergeben (u. a. um Staus und Standzeiten an der Rampe zu vermeiden).

**FCFS (Baseline):** LKW in Anmeldereihenfolge, jeweils an das Tor, an dem er am frühesten
starten kann - repräsentiert eine Terminvergabe ohne gezielte Planung, wie sie ohne Software
oft entsteht.

**ERD (Earliest Release Date first):** Bearbeitet LKW nach aufsteigender Wunschzeit statt
Anmeldereihenfolge - eine naheliegende Priorisierung ("wer zuerst kommen will, wird zuerst
eingeplant"), sonst identischer Platzierungsmechanismus wie FCFS.

**SPT (Shortest Processing Time first, unter den verfügbaren LKW):** Ereignisgesteuerte
Simulation statt statischer Liste - immer wenn ein Tor frei wird, übernimmt unter den zu diesem
Zeitpunkt bereits verfügbaren (Wunschzeit erreicht), noch nicht eingeplanten LKW der mit der
kürzesten Bearbeitungsdauer. Kurze Aufgaben zuerst einplanen räumt schnell Kapazität frei, statt
sie durch einen langen Auftrag früh zu blockieren - eine klassische Grundidee der
Scheduling-Theorie (Smith 1956 für eine einzelne Maschine ohne Freigabetermine bewiesen optimal).

**Keine Optimalitätsgarantie:** Alle drei sind Konstruktionsheuristiken ohne Beweis für das
global beste Ergebnis bei mehreren parallelen Toren mit unterschiedlichen Freigabeterminen - in
Benchmarks liegt SPT meist deutlich vorn, aber nicht in jeder Einzelinstanz zwingend vor ERD
(siehe README). Eine nachträgliche lokale Verbesserungssuche auf der SPT-Konstruktion wurde
geprüft und wieder verworfen: sie fand in keiner von 300 Testinstanzen irgendeine Verbesserung -
ein beweisbares, nicht nur empirisches Ergebnis (siehe README und Docstring von
`tas_heuristics.py`).

**In echten Projekten** kämen meist weitere Nebenbedingungen dazu (Pufferzeiten zwischen zwei
LKW am selben Tor, Torkompatibilität für bestimmte Fahrzeugtypen, Verspätungen gegenüber der
Zusage statt nur Wartezeit gegenüber dem Wunsch, mehrtägige statt eintägige Planung) - das
Grundprinzip aus Konstruktion und Bewertung bleibt aber dasselbe.
"""
    )

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
Formal ist das Terminvergabeproblem ein **Parallel-Maschinen-Scheduling-Problem mit
Freigabeterminen**, in der Drei-Feld-Notation von Graham et al. als $P_m \mid r_i \mid \sum C_i$
bezeichnet. Gegeben:

- eine Menge von $n$ **LKW** (Aufträge) $J = \{1, \ldots, n\}$
- eine Menge von $m$ **Toren** (Maschinen) $D = \{1, \ldots, m\}$
- eine **Wunschzeit** (Freigabetermin) $r_i \geq 0$ je LKW $i$ (`preferred_times` in
  `tas_data.py`)
- eine **Bearbeitungsdauer** $p_i \geq 0$ je LKW $i$ (`service_times`)

Gesucht ist eine Tor-Zuordnung $\delta: J \to D$ und Startzeiten $s_i \geq r_i$, sodass sich
zwei LKW am selben Tor nie überlappen, und die Gesamtwartezeit minimal ist:
"""
    )
    st.latex(r"\min \; \sum_{i=1}^{n} (s_i - r_i) \quad \text{u. d. N.} \quad s_i \geq r_i \;\; \forall i")
    st.latex(
        r"s_i + p_i \leq s_j \;\; \lor \;\; s_j + p_j \leq s_i \qquad \forall i \neq j "
        r"\text{ mit } \delta(i) = \delta(j)"
    )
    st.markdown(
        r"""
**Äquivalenz zur Gesamtdurchlaufzeit:** Mit Fertigstellung $C_i = s_i + p_i$ gilt
$\sum_i (s_i - r_i) = \sum_i C_i - \sum_i p_i - \sum_i r_i$ - die letzten beiden Summen sind
Konstanten (unabhängig von $\delta$ und $s$). Gesamtwartezeit und Gesamtdurchlaufzeit
$\sum C_i$ zu minimieren ist deshalb dasselbe Problem, nur um eine Konstante verschoben -
daher die $\sum C_i$-Notation in der Literatur, obwohl die App die betrieblich
aussagekräftigere Wartezeit zeigt.

Als binäres Programm mit Zuordnungsvariablen $x_{id} \in \{0,1\}$ (= 1, wenn LKW $i$ Tor $d$
zugewiesen wird) und Reihenfolgevariablen $y_{ij} \in \{0,1\}$ (= 1, wenn $i$ vor $j$
bearbeitet wird) - die gebräuchliche Form für Scheduling-MILPs mit Disjunktionen, linearisiert
über eine hinreichend große Konstante $M$ (z. B. der Betriebszeitraum):
"""
    )
    st.latex(r"\min \; \sum_{i=1}^{n} (s_i - r_i)")
    st.latex(
        r"\text{u. d. N.} \quad \sum_{d=1}^{m} x_{id} = 1 \;\; \forall i, "
        r"\qquad s_i \geq r_i \;\; \forall i"
    )
    st.latex(
        r"s_j \geq s_i + p_i - M(1{-}y_{ij}) - M(2{-}x_{id}{-}x_{jd})"
        r"\qquad \forall i \neq j,\; \forall d"
    )
    st.latex(
        r"s_i \geq s_j + p_j - M\,y_{ij} - M(2{-}x_{id}{-}x_{jd})"
        r"\qquad \forall i \neq j,\; \forall d"
    )
    st.markdown(
        r"""
**Warum NP-schwer?** Ohne Freigabetermine löst die SPT-Regel das Ein-Maschinen-Problem
$1 \| \sum C_i$ in Polynomialzeit exakt optimal (Smith 1956) - kürzeste Aufgaben zuerst
minimiert nachweislich die Summe der Fertigstellungszeiten, und dieses Ergebnis lässt sich auf
$m$ identische parallele Maschinen ohne Freigabetermine erweitern. Sobald jeder Auftrag aber
erst ab seinem eigenen $r_i$ verfügbar ist, kann SPT eine bereits verfügbare lange Aufgabe
zugunsten einer erst später verfügbaren kurzen zurückstellen (siehe README, Abschnitt "Ein
Konstruktionsfehler..." für ein handkonstruiertes Beispiel genau dieses Effekts) - Lenstra,
Rinnooy Kan & Brucker (1977) zeigten, dass bereits das Ein-Maschinen-Problem mit
Freigabeterminen $1 \mid r_i \mid \sum C_i$ NP-schwer ist. Da eine einzelne Maschine der
Spezialfall $m=1$ des hier betrachteten Problems ist, ist $P_m \mid r_i \mid \sum C_i$
für $m \geq 1$ ebenfalls NP-schwer.

**FCFS und ERD als gemeinsame Konstruktionsregel:** Beide verarbeiten die LKW in einer festen
Reihenfolge (FCFS: Anmeldereihenfolge, ERD: aufsteigend nach $r_i$) und platzieren jeden LKW
$i$ am Tor mit dem frühestmöglichen freien Slot, gegeben die Menge $B_d$ der auf Tor $d$ bereits
gebuchten Intervalle:
"""
    )
    st.latex(
        r"s_d(i \mid B_d) = \min \{\, t \geq r_i : [t,\, t{+}p_i) "
        r"\text{ überschneidet kein Intervall in } B_d \,\}"
    )
    st.latex(r"(\delta^*(i), s^*(i)) = \arg\min_{d \,\in\, D} \; s_d(i \mid B_d)")
    st.markdown(
        r"""
$s_d(i \mid B_d)$ entspricht `_earliest_start()`, die äußere Minimierung über alle Tore
`_construct()` in `tas_heuristics.py` - `fcfs_schedule()` und `erd_schedule()` unterscheiden
sich einzig in der Reihenfolge, in der die LKW dieser Regel übergeben werden.

**SPT (ereignisgesteuert):** keine statische Liste, sondern eine Simulation. Sei $f_d$ der
Zeitpunkt, zu dem Tor $d$ als Nächstes frei wird, und $R$ die Menge der noch nicht
eingeplanten LKW:
"""
    )
    st.latex(r"t = \min_{d \,\in\, D} f_d, \qquad d^* = \arg\min_{d \,\in\, D} f_d")
    st.latex(
        r"A(t) = \{\, i \in R : r_i \leq t \,\} \quad (\text{falls } A(t) = \emptyset: "
        r"\; t \leftarrow \min_{i \in R} r_i,\; A(t) \text{ neu bilden})"
    )
    st.latex(r"i^* = \arg\min_{i \,\in\, A(t)} p_i")
    st.markdown(
        r"""
Danach $\delta(i^*) \leftarrow d^*$, $s(i^*) \leftarrow t$, $f_{d^*} \leftarrow t + p_{i^*}$,
$R \leftarrow R \setminus \{i^*\}$ - direkt umgesetzt in `spt_schedule()`: `dock_free_at`
entspricht $f_d$, `remaining` entspricht $R$, `available` entspricht $A(t)$, `chosen`
entspricht $i^*$.

**Warum lokale Verbesserung beweisbar nichts bringt:** $s_d(i \mid B_d)$ ist monoton in
$B_d$ - je mehr Intervalle bereits gebucht sind, desto später oder gleich früh kann $i$ starten,
nie früher: $B \subseteq B' \Rightarrow s_d(i \mid B) \leq s_d(i \mid B')$. Jeder LKW wird bei
seiner Einplanung bereits gegen die zu diesem Zeitpunkt vollständige Buchungsmenge optimal
platziert; die Buchungsmenge zum Ende der Konstruktion ist immer eine Obermenge davon. Eine
nachträgliche Neuplatzierung eines einzelnen LKW gegen die fertige Konfiguration prüft ihn
folglich gegen ein $B_d' \supseteq B_d$ - kann nach obiger Monotonie nie einen früheren Slot
finden. Genau das bestätigten die 0 von 300 Testinstanzen im README, hier aber als Beweis statt
Beobachtung.

**Bezug zum Code:** `evaluate_schedule()` in `tas_evaluation.py` berechnet exakt
$\sum_i (s_i - r_i)$ von oben (`total_waiting_min`). Keines der drei Verfahren löst das Problem
exakt: schon die reine Tor-Zuordnung hat $m^n$ Möglichkeiten, ganz ohne die zusätzliche
Reihenfolge je Tor mitzuzählen - bei $n=40$ LKW und $m=3$ Toren (Szenario "Volle Auslastung")
bereits $3^{40} \approx 1.2 \times 10^{19}$, bei den in der Sidebar maximal einstellbaren
$n=80$ LKW und $m=10$ Toren $10^{80}$ - vollständige Enumeration ist von vornherein
ausgeschlossen.
"""
    )

st.markdown("---")

st.markdown("#### War diese Demo hilfreich für Sie?")
if st.session_state.get("feedback_given"):
    vote_text = "👍 positiv" if st.session_state["feedback_given"] == "up" else "👎 negativ"
    st.success(f"Danke für Ihr Feedback ({vote_text})! 🙏")
else:
    fb_col1, fb_col2 = st.columns(2)
    with fb_col1:
        if st.button("👍 Ja", key="feedback_up_btn", width="stretch"):
            log_feedback("up")
            st.session_state["feedback_given"] = "up"
            st.rerun()
    with fb_col2:
        if st.button("👎 Nein", key="feedback_down_btn", width="stretch"):
            log_feedback("down")
            st.session_state["feedback_given"] = "down"
            st.rerun()

st.caption(
    "Diese Demo ist Teil des Portfolios von Sebastian Hanisch – Operations Research "
    "und Machine Learning. Interesse an einer maßgeschneiderten Lösung für Ihr "
    "Unternehmen? [Kontakt aufnehmen](#)"
)
