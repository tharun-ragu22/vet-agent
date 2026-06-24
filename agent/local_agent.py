from dataclasses import dataclass

from .agent_interface import IAgent
from pydantic_ai import Agent, AgentRunResult, RunContext
from .models import gemma_model
import sqlite3

@dataclass
class LocalAgentDeps:
    db_conn : sqlite3.Connection
class LocalAgent(IAgent):

    def __init__(self, db_connection: sqlite3.Connection = None):
        if db_connection is None:
            db_connection = sqlite3.connect(":memory:")
        self.db_conn = db_connection
        self.deps = LocalAgentDeps(db_connection)
    
    _agent = Agent(
        model=gemma_model,
        system_prompt="""
        You are a receptionist agent for a veteranarian office. You will use local tools whenever you can.
         
        You must check if an appointment is available before making it. If the appointment is available, you should make the appointment.
        This is all you need to do to when someone asks to make you an appointment, don't ask for any more information.
        """
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
    def make_appointment(ctx: RunContext[LocalAgentDeps], patient_name: str, day: str, time: str) -> str:
        """Makes the appointment in the system"""
        print(f'make_appointment: making appointment for {patient_name} at {day} {time}')
        LocalAgent.make_appointment_impl(patient_name, day, time, ctx.deps.db_conn)

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
    test_agent = LocalAgent()
    print(test_agent.run_agent('Hi! I need to make an appointment for my dog Coco at 5pm today. Can you schedule me in?'))