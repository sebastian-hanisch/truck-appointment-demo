"""
Erzeugt einen Terminplan als downloadbares PDF (in-memory) - Kennzahlen +
LKW-für-LKW-Zeitplan.
"""

import time

from tas_evaluation import evaluate_schedule
from tas_visualization import format_clock


def generate_schedule_plan_pdf(label, preferred_times, service_times, dock_of_truck, start_of_truck):
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    stats = evaluate_schedule(preferred_times, service_times, dock_of_truck, start_of_truck)
    n = len(preferred_times)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Terminplan - {label}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Erstellt: {time.strftime('%d.%m.%Y %H:%M')} Uhr", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Kennzahlen", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Gesamtwartezeit: {stats['total_waiting_min']:.0f} min", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Durchschnittliche Wartezeit: {stats['avg_waiting_min']:.1f} min", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Pünktlich (ohne Wartezeit): {stats['on_time_share']:.1f}%", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Anzahl LKW: {n}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Zeitplan", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    for i in range(n):
        wait = start_of_truck[i] - preferred_times[i]
        pdf.cell(
            0, 6,
            f"LKW {i + 1}: Tor {int(dock_of_truck[i]) + 1}, "
            f"Wunsch {format_clock(preferred_times[i])}, Start {format_clock(start_of_truck[i])}, "
            f"Wartezeit {wait:.0f} min",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )

    return bytes(pdf.output())
