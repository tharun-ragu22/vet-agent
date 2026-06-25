from agent.agent_interface import AgentBaseClass, AGENT_SYSTEM_PROMPT, AgentDeps
from pydantic_ai import Agent, AgentRunResult, RunContext
from .models import google_model
import sqlite3
from dataclasses import dataclass


@dataclass
class ProdAgentDeps:
    db_conn: sqlite3.Connection


class ProdAgent(AgentBaseClass):    

    def __init__(self, db_connection: sqlite3.Connection = None):
        super().__init__(google_model, db_connection)


    


if __name__ == "__main__":
    test_agent = ProdAgent()
    print(test_agent.run_agent('Hi! I need to make an appointment for my dog Coco at 5pm today. Can you schedule me in?'))
