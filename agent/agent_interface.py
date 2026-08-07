from abc import ABC
from dataclasses import dataclass
import sqlite3
from typing import Any
from pydantic_ai import Agent, RunContext
import parsedatetime
from datetime import datetime

CHUNK_ALERT = 'chunk_uploaded'

class PatientAggressiveError(Exception):
    """Raised when an appointment is rejected because the patient is marked as aggressive."""

AGENT_SYSTEM_PROMPT = """
    You are a receptionist agent for a veteranarian office. You will use local tools whenever you can.
    YOUR ANSWER MUST BE IN PLAINTEXT, NO ASTERISKS OR ANYTHING.
    YOU MUST OUTPUT "REDIRECT" AND CEASE THE CONVERSATION IN THE FOLLOWING CASES AND ONLY THESE CASES:
    * IF THE USER ASKS YOU SOMETHING THAT YOU CANNOT ANSWER USING THE INFORMATION YOU HAVE 
    * IF THE USER ASKS TO BE TRANSFERRED TO A HUMAN (i.e. human representative, operator) 
    * IF THE USER IS FACING AN EMERGENCY

    These are your responsibilities:
    1. Confirming Appointments
    If someone asks you to confirm an appointment with them, use local tools to look through the database to check if the appointment
    exists. You only need a name to check availability. Filter through the results yourself to see if the availability exists. Don't just say you will do it.

    2. Making Appointments
    If someone asks you to make an appointment with them.You must check if an appointment is available before making it. 
    If the appointment day and time they are requesting is currently recorded in the database, then you must tell them this. Do NOT proceed with making the appointment.
    If they use a relative date, like "today" or "tomorrow", use your available tools to get the actual date and time they are referring to. DO NOT ASK THE CLIENT FOR THE ACTUAL DATE.
    Record the date in the format YYY-MM-DD and the time in the format HH:MM.
    If the appointment is available, you should make the appointment.
    If you have all the information you need, do NOT ask them again to confirm that they want to book that appointment, just book the appointment in the system.
    If the check_availability tool reports that the appointment was rejected because the patient is marked as aggressive, tell the client that this patient requires special handling and cannot be booked over the phone. Do NOT proceed with making the appointment. DO NOT MENTION TO THE CLIENT THAT THE PATIENT WAS MARKED AGGRESSIVE.


    If you need more information to use a tool, make sure to remember the current information you have for a tool's usage, and only ask for what you need
    """
@dataclass
class AgentDeps:
    db_conn: sqlite3.Connection

class AgentBaseClass(ABC):
    def __init__(self, model, db_connection):
        self.model = model
        if db_connection is None:
            db_connection = sqlite3.connect(":memory:", check_same_thread = False)
        self.db_conn = db_connection
        self.deps = AgentDeps(db_connection)
        self._init_db()
    
        self._agent = Agent(
            model=model,
            system_prompt=AGENT_SYSTEM_PROMPT
        )
        self._register_tools()
    
    def _init_db(self):
        AgentBaseClass.create_schema(self.deps.db_conn)

    @staticmethod
    def create_schema(db_connection: sqlite3.Connection):
        cursor = db_connection.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS appointments (patient_name TEXT PRIMARY KEY, day TEXT, time TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS patients (patient_name TEXT PRIMARY KEY, is_aggressive INTEGER NOT NULL DEFAULT 0)")
        cursor.execute("CREATE TABLE IF NOT EXISTS staff_availability (staff_id INTEGER NOT NULL, available_from TEXT NOT NULL, available_until TEXT NOT NULL)")
        db_connection.commit()
    
    def _register_tools(self):
        @self._agent.tool_plain
        def get_datetime_from_phrase(phrase: str) -> datetime:
            """
            Converts natural language description of date AND time into datetime object
            
            Examples (if today is August 6, 2026):
            'today at 11:15 A.M.' -> 2026-08-06 11:15:00
            '11:15 A.M. today' -> 2026-08-06 11:15:00
            'tomorrow at 3:00 P.M.' -> 2026-08-07 15:00:00
            'Wednesday at 4:15 P.M.' -> 2026-08-12 16:15:00
            """
            return self.get_datetime_from_phrase_impl(phrase)

        @self._agent.tool
        def make_appointment(ctx: RunContext[AgentDeps], patient_name: str, day: str, time: str) -> str:
            """Makes the appointment in the system"""
            return self.make_appointment(ctx, patient_name, day, time)

        @self._agent.tool
        def check_availability(ctx: RunContext[AgentDeps], patient_name: str, day: str, time: str) -> Any:
            """Checks if appointment is available"""
            return self.check_availability(ctx, patient_name, day, time)

    @staticmethod
    def get_datetime_from_phrase_impl(phrase: str) -> datetime:
        print('getting dt from phrase:', phrase)
        cal = parsedatetime.Calendar(version=parsedatetime.VERSION_CONTEXT_STYLE)       
        dt, _ = cal.parseDT(phrase)
        print('got dt:', dt)
        return dt

    @staticmethod
    def make_appointment_impl(patient_name: str, day: str, time: str, db_connection: sqlite3.Connection):
        cursor = db_connection.cursor()

        cursor.execute(
            "INSERT INTO appointments (patient_name, day, time) VALUES (?, ?, ?)",
            (patient_name, day, time)
        )
        db_connection.commit()

    @staticmethod
    def check_availability_impl(patient_name: str, day: str | None, time: str | None, db_connection: sqlite3.Connection):
        if AgentBaseClass.is_patient_aggressive_impl(patient_name, db_connection):
            raise PatientAggressiveError(
                f"Appointment for {patient_name} was rejected because the patient is marked as aggressive."
            )
        return AgentBaseClass.check_appointment_impl(patient_name, day, time, db_connection)

    @staticmethod
    def is_patient_aggressive_impl(patient_name: str, db_connection: sqlite3.Connection) -> bool:
        cursor = db_connection.cursor()
        result = cursor.execute(
            "SELECT is_aggressive FROM patients WHERE lower(patient_name) = lower(?)",
            (patient_name,)
        ).fetchone()
        return bool(result[0]) if result else False

    @staticmethod
    def mark_patient_aggressive_impl(patient_name: str, db_connection: sqlite3.Connection, is_aggressive: bool = True) -> None:
        cursor = db_connection.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_name, is_aggressive) VALUES (?, ?)
            ON CONFLICT(patient_name) DO UPDATE SET is_aggressive = excluded.is_aggressive
            """,
            (patient_name, int(is_aggressive))
        )
        db_connection.commit()

    @staticmethod
    def check_appointment_impl(patient_name: str, day: str | None, time: str | None, db_connection: sqlite3.Connection):
        cursor = db_connection.cursor()
        query = f"""
        SELECT * FROM appointments 
        WHERE lower(patient_name) = lower(?1)
        AND (?2 IS NULL OR lower(day) = lower(?2))
        AND (?3 IS NULL OR lower(time) = lower(?3))
        """

        return cursor.execute(query, {'1': patient_name, '2': day, '3': time}).fetchall()       
    
    def make_appointment(self, ctx: RunContext[AgentDeps], patient_name: str, day: str, time: str) -> str:
        """Makes the appointment in the system"""
        print(f'make_appointment: making appointment for {patient_name} at {day} {time}')
        AgentBaseClass.make_appointment_impl(patient_name, day, time, ctx.deps.db_conn)
        return f'Appointment made for {patient_name} on {day} at {time}.'

    def check_availability(self, ctx: RunContext[AgentDeps], patient_name: str, day: str, time: str):
        """Checks if appointment is available"""
        print(f'check_appointment: checking appointment for {patient_name} at {day} {time}')
        try:
            return AgentBaseClass.check_availability_impl(patient_name, day, time, ctx.deps.db_conn)
        except PatientAggressiveError as e:
            return str(e)

    async def run_agent(self, input: str, message_history = None):
        result = await self._agent.run(input, deps=self.deps, message_history=message_history)
        return result
