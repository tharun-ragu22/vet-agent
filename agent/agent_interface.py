from abc import ABC
from dataclasses import dataclass
import sqlite3
from typing import Any
import logfire
from pydantic_ai import Agent, RunContext

CHUNK_ALERT = 'chunk_uploaded'

AGENT_SYSTEM_PROMPT = """
    You are a receptionist agent for a veteranarian office. You will use local tools whenever you can.
    YOUR ANSWER MUST BE IN PLAINTEXT, NO ASTERISKS OR ANYTHING.
    YOU MUST OUTPUT "REDIRECT" AND CEASE THE CONVERSATION IN THE FOLLOWING CASES:
    * IF THE USER ASKS YOU SOMETHING THAT YOU CANNOT ANSWER USING THE INFORMATION YOU HAVE 
    * IF THE USER ASKS TO BE TRANSFERRED TO A HUMAN (i.e. human representative, operator) 

    These are your responsibilities:
    1. Confirming Appointments
    If someone asks you to confirm an appointment with them, use local tools to look through the database to check if the appointment
    exists. You only need a name to check availability. Filter through the results yourself to see if the availability exists. Don't just say you will do it.

    2. Making Appointments
    If someone asks you to make an appointment with them.You must check if an appointment is available before making it. 
    If the appointment day and time they are requesting is currently recorded in the database, then you must tell them this. Do NOT proceed with making the appointment.
    If the appointment is available, you should make the appointment.
    If you have all the information you need, do NOT ask them again to confirm that they want to book that appointment, just do it.
    

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
        cursor = self.deps.db_conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS appointments (patient_name TEXT PRIMARY KEY, day TEXT, time TEXT)")
        self.deps.db_conn.commit()
    
    def _register_tools(self):
        @self._agent.tool
        def make_appointment(ctx: RunContext[AgentDeps], patient_name: str, day: str, time: str) -> str:
            """Makes the appointment in the system"""
            self.make_appointment(ctx, patient_name, day, time)

        @self._agent.tool
        def check_availability(ctx: RunContext[AgentDeps], patient_name: str, day: str, time: str) -> list[Any]:
            """Checks if appointment is available"""
            return self.check_availability(ctx, patient_name, day, time)

    @staticmethod
    def make_appointment_impl(patient_name: str, day: str, time: str, db_connection: sqlite3.Connection):
        cursor = db_connection.cursor()
        
        cursor.execute(
            "INSERT INTO appointments (patient_name, day, time) VALUES (?, ?, ?)",
            (patient_name, day, time)
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
    
    def check_availability(self, ctx: RunContext[AgentDeps], patient_name: str, day: str, time: str) -> str:
        """Makes the appointment in the system"""
        print(f'check_appointment: checking appointment for {patient_name} at {day} {time}')
        return AgentBaseClass.check_appointment_impl(patient_name, day, time, ctx.deps.db_conn)

    async def run_agent(self, input: str, message_history = None):
        result = await self._agent.run(input, deps=self.deps, message_history=message_history)
        return result
