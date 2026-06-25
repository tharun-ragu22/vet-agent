from abc import ABC, abstractmethod
from dataclasses import dataclass
import sqlite3

from pydantic_ai import Agent, RunContext

AGENT_SYSTEM_PROMPT = """
    You are a receptionist agent for a veteranarian office. You will use local tools whenever you can.
        
    You must check if an appointment is available before making it. If the appointment is available, you should make the appointment.
    This is all you need to do to when someone asks to make you an appointment, don't ask for any more information.
    """
@dataclass
class AgentDeps:
    db_conn: sqlite3.Connection

class AgentBaseClass(ABC):
    def __init__(self, model, db_connection):
        self.model = model
        if db_connection is None:
            db_connection = sqlite3.connect(":memory:")
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
        pass

    @staticmethod
    def make_appointment_impl(patient_name: str, day: str, time: str, db_connection: sqlite3.Connection):
        cursor = db_connection.cursor()
        cursor.execute(
            "INSERT INTO appointments (patient_name, day, time) VALUES (?, ?, ?)",
            (patient_name, day, time)
        )
        db_connection.commit()
    
    def make_appointment(self, ctx: RunContext[AgentDeps], patient_name: str, day: str, time: str) -> str:
        """Makes the appointment in the system"""
        print(f'make_appointment: making appointment for {patient_name} at {day} {time}')
        AgentBaseClass.make_appointment_impl(patient_name, day, time, ctx.deps.db_conn)

    async def run_agent(self, input: str):
        return await self._agent.run(input, deps=self.deps)

    @abstractmethod
    def _register_tools(self):
        pass
