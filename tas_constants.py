"""
Zentrale Konstanten für die Truck-Appointment-Scheduling-Demo
(Sebastian Hanisch - Operations Research und Machine Learning).
"""

DOCK_COLORS = ["#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed", "#0891b2", "#db2777", "#65a30d"]
EPS = 1e-9

DEFAULT_N_TRUCKS = 24
DEFAULT_N_DOCKS = 4
DEFAULT_OPERATING_MINUTES = 720.0  # 12 Stunden, z. B. 6:00-18:00 Uhr
DEFAULT_SERVICE_TIME_RANGE = (20.0, 90.0)  # Minuten je LKW

FEEDBACK_FILE = "feedback_log.csv"
