from dataclasses import dataclass

from .agent_interface import AgentBaseClass
from .models import gemma_model
import sqlite3


@dataclass
class LocalAgentDeps:
    db_conn: sqlite3.Connection


class LocalAgent(AgentBaseClass):

    def __init__(self, db_connection: sqlite3.Connection = None):
        super().__init__(gemma_model, db_connection)

    


if __name__ == "__main__":
    test_agent = LocalAgent()
    print(test_agent.run_agent('Hi! I need to make an appointment for my dog Coco at 5pm today. Can you schedule me in?'))
