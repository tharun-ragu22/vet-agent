from .agent_interface import AgentBaseClass
from pydantic_ai import AgentRunResult
import asyncio

class MockOutput():
    def __init__(self, output: str):
        self.output = output


class MockAgent(AgentBaseClass):

    _agent = None

    def make_appointment(number: int) -> str:
        """Makes the appointment in the system"""
        print( f'make_appointment: making appointment: {number}')

    def check_availability(number: int) -> bool:
        """Checks if appointment is available"""
        print(f'check_availability: appointment for {number}')
        return True

    # 4. The run_agent execution wrapper
    async def run_agent(self, prompt: str) -> str:
        await asyncio.sleep(0.5)
        return MockOutput(prompt)
