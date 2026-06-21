from abc import ABC, abstractmethod

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