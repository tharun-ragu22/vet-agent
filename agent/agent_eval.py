import logfire
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import HasMatchingSpan
from agent.local_agent import LocalAgent

# 1. Initialize local-only logfire
logfire.configure(send_to_logfire=False)

# 2. Tell PydanticAI to send its spans to this local tracker
logfire.instrument_pydantic_ai()

test_agent = LocalAgent()
dataset = Dataset(
    name="veteranarian agent tests",
    cases=[
        Case(
            name="simple-appointment",
            inputs="""
            Hi, my name is Hughie Campbell, I'm a current patient with you guys. 
            My dog Cosette needs an appointment for 5 o'clock today. Is this possible?
            """,
            evaluators=[
                HasMatchingSpan(
                    query={
                        'has_attributes': {'gen_ai.tool.name': 'check_availability'}
                    }
                )
            ],
        ),
    ],
)

def run_agent_task(inputs: str) -> str:
    return test_agent.run_agent(inputs)

report = dataset.evaluate_sync(run_agent_task)

report.print()