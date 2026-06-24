import asyncio
import logfire
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import HasMatchingSpan
from .local_agent import LocalAgent
import sys

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
                ),
                HasMatchingSpan(
                    query={
                        'has_attributes': {'gen_ai.tool.name': 'bork'}
                    }
                )
            ],
        ),
    ],
)

async def run_agent_task(inputs: str) -> str:
    return await test_agent.run_agent(inputs)

async def main():

    report = await dataset.evaluate(run_agent_task)

    report.print()

    if len(report.failures) > 0:
        print(f"\n❌ Evaluation failed with {len(report.failures)} failure(s).")
        sys.exit(1)
    
    print("\n✅ All evaluations passed successfully.")

asyncio.run(main())