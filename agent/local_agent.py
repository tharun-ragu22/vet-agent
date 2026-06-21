from agent_interface import IAgent
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai import Agent, AgentRunResult
class LocalAgent(IAgent):
    
    gemma_model = OllamaModel(
        model_name="gemma4:latest",
        provider=OllamaProvider(base_url="http://localhost:11434/v1")
    )

    _agent = Agent(
        model=gemma_model,
        system_prompt="""
        You are a receptionist agent for a veteranarian office. You will use local tools whenever you can.
         
        You must check if an appointment is available before making it. If the appointment is available, you should make the appointment.
        This is all you need to do to when someone asks to make you an appointment, don't ask for any more information.
        """
    )

    
    @_agent.tool_plain
    def make_appointment(number: int) -> str:
        """Makes the appointment in the system"""
        print( f'make_appointment: making appointment: {number}')

    @_agent.tool_plain
    def check_availability(number: int) -> bool:
        """Checks if appointment is available"""
        print(f'check_availability: appointment for {number}')
        return True

    # 4. The run_agent execution wrapper
    def run_agent(self, prompt: str) -> AgentRunResult[str]:
        res = self._agent.run_sync(prompt)
        return res


if __name__ == "__main__":
    test_agent = LocalAgent()
    print(test_agent.run_agent('Hi! I need to make an appointment for my dog Coco at 5pm today. Can you schedule me in?'))