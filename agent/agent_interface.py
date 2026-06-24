from abc import ABC, abstractmethod

AGENT_SYSTEM_PROMPT = """
    You are a receptionist agent for a veteranarian office. You will use local tools whenever you can.
        
    You must check if an appointment is available before making it. If the appointment is available, you should make the appointment.
    This is all you need to do to when someone asks to make you an appointment, don't ask for any more information.
    """

class IAgent(ABC):
    @abstractmethod
    def run_agent(input: str):
        pass
    
    @abstractmethod
    def make_appointment(input: str) -> str:
        pass

    @abstractmethod
    def check_availability(input: str) -> str:
        pass