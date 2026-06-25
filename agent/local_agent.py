from dataclasses import dataclass

from .agent_interface import AgentBaseClass, AGENT_SYSTEM_PROMPT, AgentDeps
from pydantic_ai import Agent, AgentRunResult, RunContext
from .models import gemma_model
import sqlite3


@dataclass
class LocalAgentDeps:
    db_conn: sqlite3.Connection


class LocalAgent(AgentBaseClass):

    def __init__(self, db_connection: sqlite3.Connection = None):
        super().__init__(gemma_model, db_connection)


    def _register_tools(self):
        @self._agent.tool
        def make_appointment(ctx: RunContext[AgentDeps], patient_name: str, day: str, time: str) -> str:
            """Makes the appointment in the system"""
            self.make_appointment(ctx, patient_name, day, time)

        @self._agent.tool_plain
        def check_availability(number: int) -> bool:
            """Checks if appointment is available"""
            print(f'check_availability: checking slot {number}')
            return True

    


if __name__ == "__main__":
    test_agent = LocalAgent()
    print(test_agent.run_agent('Hi! I need to make an appointment for my dog Coco at 5pm today. Can you schedule me in?'))
