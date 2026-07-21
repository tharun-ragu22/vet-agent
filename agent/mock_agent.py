from .agent_interface import AgentBaseClass
import asyncio

class MockOutput():
    def __init__(self, output: str):
        self.output = output
        self.all_messages = lambda : [{'role': 'user', 'content': 'this is a sample message'}]


class MockAgent(AgentBaseClass):

    _agent = None

    def make_appointment(number: int) -> str:
        """Makes the appointment in the system"""
        print( f'make_appointment: making appointment: {number}')

    def check_availability(number: int) -> bool:
        """Checks if appointment is available"""
        print(f'check_availability: appointment for {number}')
        return True

    async def run_agent(self, prompt: str, message_history = None) -> str:
        return MockOutput(prompt)
