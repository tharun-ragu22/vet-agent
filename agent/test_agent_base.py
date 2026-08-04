import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta
from freezegun import freeze_time
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


@pytest.fixture
def conn():
    with sqlite3.connect(":memory:") as connection:
        AgentBaseClass.create_schema(connection)
        yield connection

def test_make_appointment(conn):
    # Given the user wants to make appointment
    # And the appointment is available
    patient_name = 'beef'
    day = '2026-01-01'
    time = '10:30'

    # When the agent asks to make the appointment
    AgentBaseClass.make_appointment_impl(patient_name, day, time, conn)

    # Then the system records the appointment in persistent storage
    result = conn.execute(f"SELECT * FROM appointments WHERE patient_name = '{patient_name}'").fetchall()
    assert len(result) == 1

def test_check_appointment_no_appointment_made_should_say_no(conn):
    # Given the user doesn't have an appointment
    patient_name = 'beef'
    day = '2026-01-01'
    time = '10:30'

    # When they check if they have that appointment
    result = AgentBaseClass.check_appointment_impl(patient_name, day, time, conn)

    # Then the system tells them they have no appointment
    assert len(result) == 0

def test_check_appointment_appointment_made_should_say_yes(conn):
    # Given the user does have an appointment
    patient_name = 'beef'
    day = '2026-01-01'
    time = '10:30'
    AgentBaseClass.make_appointment_impl(patient_name, day, time, conn)

    # When they check if they have that appointment
    result = AgentBaseClass.check_appointment_impl(patient_name, day, time, conn)

    # Then the system confirms that they do
    assert len(result) == 1

def test_mark_patient_aggressive_then_is_patient_aggressive_returns_true(conn):
    # Given a patient is marked as aggressive
    patient_name = 'rex'
    AgentBaseClass.mark_patient_aggressive_impl(patient_name, conn)

    # When the system checks whether the patient is aggressive
    result = AgentBaseClass.is_patient_aggressive_impl(patient_name, conn)

    # Then it reports the patient as aggressive
    assert result is True

def test_is_patient_aggressive_returns_false_for_unknown_patient(conn):
    # Given a patient that has never been recorded
    patient_name = 'beef'

    # When the system checks whether the patient is aggressive
    result = AgentBaseClass.is_patient_aggressive_impl(patient_name, conn)

    # Then it reports the patient as not aggressive
    assert result is False

def test_check_availability_rejected_if_patient_marked_aggressive(conn):
    # Given a patient is marked as aggressive
    patient_name = 'rex'
    day = '2026-01-01'
    time = '10:30'
    AgentBaseClass.mark_patient_aggressive_impl(patient_name, conn)

    # When the agent checks availability for that patient
    # Then the system rejects the check
    with pytest.raises(PatientAggressiveError):
        AgentBaseClass.check_availability_impl(patient_name, day, time, conn)

def test_check_availability_allowed_if_patient_not_marked_aggressive(conn):
    # Given a patient is not marked as aggressive
    patient_name = 'beef'
    day = '2026-01-01'
    time = '10:30'

    # When the agent checks availability for that patient
    result = AgentBaseClass.check_availability_impl(patient_name, day, time, conn)

    # Then it returns the normal availability query results
    assert result == []

def test_make_appointment_allowed_if_patient_not_marked_aggressive(conn):
    # Given a patient is not marked as aggressive
    patient_name = 'beef'
    day = '2026-01-01'
    time = '10:30'

    # When the agent tries to make the appointment
    AgentBaseClass.make_appointment_impl(patient_name, day, time, conn)

    # Then the appointment is recorded
    result = AgentBaseClass.check_appointment_impl(patient_name, day, time, conn)
    assert len(result) == 1

def test_make_appointment_impl_ignores_aggressive_flag(conn):
    # Given a patient is marked as aggressive
    # (the rejection now happens at check_availability time, not here)
    patient_name = 'rex'
    day = '2026-01-01'
    time = '10:30'
    AgentBaseClass.mark_patient_aggressive_impl(patient_name, conn)

    # When the agent makes the appointment directly
    AgentBaseClass.make_appointment_impl(patient_name, day, time, conn)

    # Then the appointment is recorded
    result = AgentBaseClass.check_appointment_impl(patient_name, day, time, conn)
    assert len(result) == 1

def test_check_availability_impl_returns_rejection_message_when_patient_aggressive(conn):
    # Given a patient is marked as aggressive
    patient_name = 'rex'
    day = '2026-01-01'
    time = '10:30'
    AgentBaseClass.mark_patient_aggressive_impl(patient_name, conn)

    # When the check_availability tool is invoked
    try:
        AgentBaseClass.check_availability_impl(patient_name, day, time, conn)
    except Exception as e:
        # Then it returns a rejection message
        assert 'aggressive' in str(e)
    else:
        pytest.fail()

def test_get_datetime_from_phrase_returns_todays_date():
    # Given the agent has parsed out today as the day to make the appointment
    TODAY_STR = 'today'
    # When the agent uses the tool on this string
    acc_datetime = AgentBaseClass.get_datetime_from_phrase_impl(TODAY_STR)
    # Then the tool returns today's date
    expected_date = datetime.now().date()
    assert acc_datetime.date() == expected_date

def test_get_datetime_from_phrase_today_at_five_pm():
    # Given the agent has parsed out 'today at 5 P.M.' as the day to make the appointment
    TODAY_STR = 'today at 5 P.M.'
    # When the agent uses the tool on this string
    acc_datetime = AgentBaseClass.get_datetime_from_phrase_impl(TODAY_STR)
    # Then the tool returns the correct datetime
    expected_date = datetime.now().replace(hour=17, minute=0, second = 0, microsecond=0)
    assert acc_datetime == expected_date

@freeze_time("2026-08-03 12:00:00")
def test_get_datetime_from_phrase_today_is_monday_get_thursday_at_11_am():
    # Given today is Monday
    # And the agent has parsed out 'thursday at 11 A.M.' as the day to make the appointment
    DATE_PHRASE = 'thursday at 11 A.M.'
    # When the agent uses the tool on this string
    acc_datetime = AgentBaseClass.get_datetime_from_phrase_impl(DATE_PHRASE)
    # Then the tool returns the correct datetime
    expected_date = (datetime.now()+timedelta(days=3)).replace(hour=11, minute=0, second = 0, microsecond=0)
    assert acc_datetime == expected_date

@freeze_time("2026-08-07 12:00:00")
def test_get_datetime_from_phrase_today_is_friday_get_thursday_at_11_am():
    # Given today is Friday
    # Given the agent has parsed out 'thursday at 11 A.M.' as the day to make the appointment
    DATE_PHRASE = 'thursday at 11 A.M.'
    # When the agent uses the tool on this string
    acc_datetime = AgentBaseClass.get_datetime_from_phrase_impl(DATE_PHRASE)
    # Then the tool returns the correct datetime
    expected_date = (datetime.now()+timedelta(days=6)).replace(hour=11, minute=0, second = 0, microsecond=0)
    assert acc_datetime == expected_date

@freeze_time("2026-08-06 12:00:00")
def test_get_datetime_from_phrase_today_is_thursday_get_thursday_at_11_am():
    # Given today is Thursday
    # Given the agent has parsed out 'thursday at 11 A.M.' as the day to make the appointment
    DATE_PHRASE = 'thursday at 11 A.M.'
    # When the agent uses the tool on this string
    acc_datetime = AgentBaseClass.get_datetime_from_phrase_impl(DATE_PHRASE)
    # Then the tool returns the correct datetime
    expected_date = (datetime.now()+timedelta(days=7)).replace(hour=11, minute=0, second = 0, microsecond=0)
    assert acc_datetime == expected_date