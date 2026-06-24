from agent.agent_interface import IAgent, AGENT_SYSTEM_PROMPT
from pydantic_ai import Agent, AgentRunResult, RunContext
from .models import google_model
import sqlite3
from dataclasses import dataclass

@dataclass
class ProdAgentDeps:
    db_conn : sqlite3.Connection

class ProdAgent(IAgent):

    def __init__(self, db_connection: sqlite3.Connection = None):
        if db_connection is None:
            db_connection = sqlite3.connect(":memory:")
        self.db_conn = db_connection
        self.deps = ProdAgentDeps(db_connection)
        self._init_db()
    
    def _init_db(self):
        cursor = self.deps.db_conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS appointments (patient_name TEXT PRIMARY KEY, day TEXT, time TEXT)")
        self.deps.db_conn.commit()

    _agent = Agent(
        model=google_model,
        system_prompt=AGENT_SYSTEM_PROMPT
    )

    @staticmethod
    def make_appointment_impl(patient_name: str, day: str, time: str, db_connection: sqlite3.Connection):
        cursor = db_connection.cursor()
        cursor.execute(
            "INSERT INTO appointments (patient_name, day, time) VALUES (?, ?, ?)",
            (patient_name, day, time)
        )
        db_connection.commit()
    
    @_agent.tool
    def make_appointment(ctx: RunContext[ProdAgentDeps], patient_name: str, day: str, time: str) -> str:
        """Makes the appointment in the system"""
        print(f'make_appointment: making appointment for {patient_name} at {day} {time}')
        ProdAgent.make_appointment_impl(patient_name, day, time, ctx.deps.db_conn)


    @_agent.tool_plain
    def check_availability(number: int) -> bool:
        """Checks if appointment is available"""
        print(f'check_availability: appointment for {number}')
        return True

    # 4. The run_agent execution wrapper
    async def run_agent(self, prompt: str) -> AgentRunResult[str]:
        res = await self._agent.run(prompt, deps = self.deps)
        return res


if __name__ == "__main__":
    test_agent = ProdAgent()
    print(test_agent.run_agent('Hi! I need to make an appointment for my dog Coco at 5pm today. Can you schedule me in?'))