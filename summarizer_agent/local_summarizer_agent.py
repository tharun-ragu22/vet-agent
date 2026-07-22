from .summarizer_base import SummarizerAgentBaseClass
from agent.models import gemma_model

class LocalSummarizerAgent(SummarizerAgentBaseClass):

    def __init__(self):
        super().__init__(gemma_model)
