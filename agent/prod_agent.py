from agent.agent_interface import IAgent, AGENT_SYSTEM_PROMPT
from pydantic_ai import Agent, AgentRunResult
from .models import google_model
import sqlite3

class ProdAgent(IAgent):
    

    _agent = Agent(
        model=google_model,
        system_prompt=AGENT_SYSTEM_PROMPT
    )

    @staticmethod
    def make_appointment_impl(patient_name: str, day: str, time: str, db_connection: sqlite3.Connection = None):
        cursor = db_connection.cursor()
        cursor.execute(
            "INSERT INTO appointments (patient_name, day, time) VALUES (?, ?, ?)",
            (patient_name, day, time)
        )
        db_connection.commit()
    
    @_agent.tool_plain
    def make_appointment(patient_name: str, day: str, time: str) -> str:
        """Makes the appointment in the system"""
        print(f'make_appointment: making appointment for {patient_name} at {day} {time}')
        ProdAgent.make_appointment_impl(patient_name, day, time)


    @_agent.tool_plain
    def check_availability(number: int) -> bool:
        """Checks if appointment is available"""
        print(f'check_availability: appointment for {number}')
        return True

    # 4. The run_agent execution wrapper
    async def run_agent(self, prompt: str) -> AgentRunResult[str]:
        res = await self._agent.run(prompt)
        return res


if __name__ == "__main__":
    test_agent = ProdAgent()
    print(test_agent.run_agent('Hi! I need to make an appointment for my dog Coco at 5pm today. Can you schedule me in?'))