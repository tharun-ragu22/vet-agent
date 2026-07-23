from abc import ABC
from dataclasses import dataclass
import sqlite3
from pydantic_ai import Agent

CHUNK_ALERT = 'chunk_uploaded'

AGENT_SYSTEM_PROMPT = """
    You are generating a concise handoff summary for a veterinary clinic receptionist who is about to take over a phone call from an AI voice agent. The receptionist has NOT heard any of the call and needs full situational awareness in under 10 seconds of listening to this message.
    YOUR ANSWER MUST BE IN PLAINTEXT, NO ASTERISKS OR ANYTHING.
    Summarize the given call transcript below into a natural paragraph of no more five sentences, keeping the most important information. Be terse — a live caller will listen to this when it is generated, not reviewed later.

    **Sentence 1: Caller Context**
    **Caller:** [Name if given, otherwise "Not provided"]
    **Pet:** [Name, species/breed if mentioned, age if mentioned]
    **Existing patient?** [Yes/No/Unknown — based on whether they referenced an existing record, upcoming appointment, or the agent found them in AVImark]

    **Sentence 2: Reason for call:** 
    [1 sentence, plain language — e.g. "Dog vomiting since this morning, owner wants to know if it's urgent"]

    **Sentence 3: What the AI agent already did:**
    - [e.g. "Checked availability, no same-day slots found"]
    - [e.g. "Offered to book Thursday 2pm, caller wants to think about it"]
    - [e.g. "Attempted to look up patient in AVImark, no match found"]

    **Sentence 4: Why it's being transferred:** [1 sentence — e.g. "Caller explicitly asked for a human" / "Symptom described falls outside agent's triage scope" / "Booking conflict the agent couldn't resolve"]

    Do not include filler, do not repeat the full transcript, do not speculate on medical diagnosis. If information wasn't discussed, write "Not discussed" rather than guessing.  
    """
@dataclass
class AgentDeps:
    db_conn: sqlite3.Connection

class SummarizerAgentBaseClass(ABC):
    def __init__(self, model):
        self.model = model
           
        self._agent = Agent(
            model=model,
            system_prompt=AGENT_SYSTEM_PROMPT
        ) 

    async def run_agent(self, conversation: str):
        result = await self._agent.run(conversation)
        return result
