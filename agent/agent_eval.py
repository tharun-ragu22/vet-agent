import asyncio
import logfire
from pydantic_evals import Case, Dataset
from dataclasses import dataclass
from pydantic_evals.evaluators import HasMatchingSpan, Evaluator, EvaluatorContext
from .local_agent import LocalAgent
import sys
import sqlite3


connection = sqlite3.connect(":memory:", check_same_thread=False)
cursor = connection.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS appointments (patient_name TEXT PRIMARY KEY, day TEXT, time TEXT)")

@dataclass
class SimpleAppointment_RecordedInDB(Evaluator):
    """Check if appointment was recorded in the db"""
    def evaluate(self, ctx: EvaluatorContext) -> bool:
        result = cursor.execute(f"SELECT * FROM appointments").fetchall()

        return len(result) == 1
    
# 1. Initialize local-only logfire
logfire.configure(send_to_logfire=False)

# 2. Tell PydanticAI to send its spans to this local tracker
logfire.instrument_pydantic_ai()

test_agent = LocalAgent(connection)
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
                        'has_attributes': {'gen_ai.tool.name': 'make_appointment'}
                    }
                ),
                SimpleAppointment_RecordedInDB()
            ],
        ),
    ],
)

def mock_agent_task(inputs: str) -> str:
    return inputs.upper()

async def run_agent_task(inputs: str) -> str:
    return await test_agent.run_agent(inputs)

async def main():

    report = await dataset.evaluate(run_agent_task)

    report.print()

    if report.failures:
        print(f"\n💥 {len(report.failures)} task(s) crashed:")
        for f in report.failures:
            print(f"  - {f.name}: {f.exception_message}")
        sys.exit(1)

    failed_assertions = [
        (case.name, name, result)
        for case in report.cases
        for name, result in case.assertions.items()
        if result.value is False
    ]

    if failed_assertions:
        print(f"\n❌ {len(failed_assertions)} assertion(s) failed:")
        for case_name, assertion_name, result in failed_assertions:
            print(f"  - [{case_name}] {assertion_name}: {result.source}")
        sys.exit(1)
    
    print("\n✅ All evaluations passed successfully.")

asyncio.run(main())