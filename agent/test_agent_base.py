import sqlite3
import sys
from pathlib import Path

import pytest

# 1. Force Python to see the root directory before doing ANY imports
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# 2. Force Python to recognize 'agent' as a top-level package for relative resolutions
import agent
sys.modules['agent'] = agent

# 3. NOW import your production code safely
from agent.agent_interface import AgentBaseClass, PatientAggressiveError


def test_make_appointment():
    # Given the user wants to make appointment
    # And the appointment is available
    patient_name = 'beef'
    day = '2026-01-01'
    time = '10:30'
    with sqlite3.connect(":memory:") as conn:
        cursor = conn.cursor()
        AgentBaseClass.create_schema(conn)

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

        # When they check if they have that appointment
        result = AgentBaseClass.check_appointment_impl(patient_name, day, time, conn)

        # Then the system tells them they have not appointment
        assert len(result) == 0

def test_check_appointment_appointment_made_should_say_yes():
    # Given the user wants does have an appointment
    patient_name = 'beef'
    day = '2026-01-01'
    time = '10:30'
    with sqlite3.connect(":memory:") as conn:
        cursor = conn.cursor()
        AgentBaseClass.create_schema(conn)
        AgentBaseClass.make_appointment_impl(patient_name, day, time, conn)

        # When they check if they have that appointment
        result = AgentBaseClass.check_appointment_impl(patient_name, day, time, conn)

        # Then the system confirms that they do4
        assert len(result) == 1

def test_mark_patient_aggressive_then_is_patient_aggressive_returns_true():
    # Given a patient is marked as aggressive
    patient_name = 'rex'
    with sqlite3.connect(":memory:") as conn:
        AgentBaseClass.create_schema(conn)
        AgentBaseClass.mark_patient_aggressive_impl(patient_name, conn)

        # When the system checks whether the patient is aggressive
        result = AgentBaseClass.is_patient_aggressive_impl(patient_name, conn)

        # Then it reports the patient as aggressive
        assert result is True

def test_is_patient_aggressive_returns_false_for_unknown_patient():
    # Given a patient that has never been recorded
    patient_name = 'beef'
    with sqlite3.connect(":memory:") as conn:
        AgentBaseClass.create_schema(conn)

        # When the system checks whether the patient is aggressive
        result = AgentBaseClass.is_patient_aggressive_impl(patient_name, conn)

        # Then it reports the patient as not aggressive
        assert result is False

def test_make_appointment_rejected_if_patient_marked_aggressive():
    # Given a patient is marked as aggressive
    patient_name = 'rex'
    day = '2026-01-01'
    time = '10:30'
    with sqlite3.connect(":memory:") as conn:
        AgentBaseClass.create_schema(conn)
        AgentBaseClass.mark_patient_aggressive_impl(patient_name, conn)

        # When the agent tries to make the appointment
        # Then the system rejects the appointment
        with pytest.raises(PatientAggressiveError):
            AgentBaseClass.make_appointment_impl(patient_name, day, time, conn)

        # And no appointment is recorded
        result = AgentBaseClass.check_appointment_impl(patient_name, day, time, conn)
        assert len(result) == 0

def test_make_appointment_allowed_if_patient_not_marked_aggressive():
    # Given a patient is not marked as aggressive
    patient_name = 'beef'
    day = '2026-01-01'
    time = '10:30'
    with sqlite3.connect(":memory:") as conn:
        AgentBaseClass.create_schema(conn)

        # When the agent tries to make the appointment
        AgentBaseClass.make_appointment_impl(patient_name, day, time, conn)

        # Then the appointment is recorded
        result = AgentBaseClass.check_appointment_impl(patient_name, day, time, conn)
        assert len(result) == 1

def test_make_appointment_tool_returns_rejection_message_when_patient_aggressive():
    # Given a patient is marked as aggressive
    patient_name = 'rex'
    day = '2026-01-01'
    time = '10:30'
    with sqlite3.connect(":memory:") as conn:
        AgentBaseClass.create_schema(conn)
        AgentBaseClass.mark_patient_aggressive_impl(patient_name, conn)

        agent_instance = AgentBaseClass.__new__(AgentBaseClass)
        ctx = _FakeContext(conn)

        # When the make_appointment tool is invoked
        result = agent_instance.make_appointment(ctx, patient_name, day, time)

        # Then it returns a rejection message and does not book the appointment
        assert 'aggressive' in result.lower()
        assert len(AgentBaseClass.check_appointment_impl(patient_name, day, time, conn)) == 0


class _FakeDeps:
    def __init__(self, db_conn):
        self.db_conn = db_conn


class _FakeContext:
    def __init__(self, db_conn):
        self.deps = _FakeDeps(db_conn)
