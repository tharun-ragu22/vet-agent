from .summarizer_base import SummarizerAgentBaseClass
from agent.models import google_model

class ProdSummarizerAgent(SummarizerAgentBaseClass):

    def __init__(self):
        super().__init__(google_model)