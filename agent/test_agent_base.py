import sqlite3
import sys
from pathlib import Path

# 1. Force Python to see the root directory before doing ANY imports
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# 2. Force Python to recognize 'agent' as a top-level package for relative resolutions
import agent
sys.modules['agent'] = agent

# 3. NOW import your production code safely
from agent.agent_interface import AgentBaseClass


def test_make_appointment():
    # Given the user wants to make appointment
    # And the appointment is available
    patient_name = 'beef'
    day = '2026-01-01'
    time = '10:30'
    with sqlite3.connect(":memory:") as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE appointments (patient_name TEXT PRIMARY KEY, day TEXT, time TEXT)")
        


        # When the agent asks to make the appointment
        AgentBaseClass.make_appointment_impl(patient_name, day, time, conn)

        # Then the system records the appointment in persistent storage
        result = cursor.execute(f"SELECT * FROM appointments WHERE patient_name = '{patient_name}'").fetchall()

        assert len(result) == 1

def test_check_appointment_no_appointment_made_should_say_no():
    # Given the user wants doesn't have an appointment
    patient_name = 'beef'
    day = '2026-01-01'
    time = '10:30'
    with sqlite3.connect(":memory:") as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE appointments (patient_name TEXT PRIMARY KEY, day TEXT, time TEXT)")

        # When the agent asks to make the appointment
        result = AgentBaseClass.check_appointment_impl(patient_name, day, time, conn)

        # Then the system tells them they have not appointment
        assert len(result) == 0
      