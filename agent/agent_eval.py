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
CREATE_TABLE_COMMAND = "CREATE TABLE IF NOT EXISTS appointments (patient_name TEXT PRIMARY KEY, day TEXT, time TEXT)"

RESET_TABLE_COMMAND = f"""
DROP TABLE IF EXISTS appointments;
{CREATE_TABLE_COMMAND}
"""
cursor.executescript(CREATE_TABLE_COMMAND)

@dataclass
class SimpleAppointment_RecordedInDB(Evaluator):
    """Check if appointment was recorded in the db"""
    def evaluate(self, ctx: EvaluatorContext) -> bool:
        result = cursor.execute(f"SELECT * FROM appointments").fetchall()

        return len(result) == 1

@dataclass
class ParseAppointmentNotMade(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> bool:
        return not ctx.span_tree.any(
            {
                "and_": [
                    {"name_equals": "running tool"},
                    {"has_attributes": {"gen_ai.tool.name": "make_appointment"}},
                ]
            }
        )
    
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
        Case(
            name="check-appointment-not-made",
            inputs="""
            Hi, my name is Hughie Campbell, I'm a current patient with you guys. 
            I wanted to check if I had an appointment for 5 o'clock today with you guys?
            """,
            evaluators=[
                HasMatchingSpan(
                    query={
                        'has_attributes': {'gen_ai.tool.name': 'check_availability'}
                    }
                ),
                ParseAppointmentNotMade(),
            ],
        ),
    ],
)

def mock_agent_task(inputs: str) -> str:
    return inputs.upper()

async def run_agent_task(inputs: str) -> str:
    cursor.executescript(RESET_TABLE_COMMAND)
    return await test_agent.run_agent(inputs)

async def main():

    report = await dataset.evaluate(run_agent_task, max_concurrency=1)

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

        # Dump debug info for each failed case
        failed_case_names = {name for name, _, _ in failed_assertions}
        for case in report.cases:
            if case.name not in failed_case_names:
                continue
            print(f"\n{'='*50}")
            print(f"DEBUG: {case.name}")
            print(f"{'='*50}")
            print(f"INPUT:\n  {case.inputs}")
            print(f"OUTPUT:\n  {case.output}")
            if case.metrics:
                print(f"METRICS: {case.metrics}")
            if case.attributes:
                print(f"ATTRIBUTES: {case.attributes}")

        sys.exit(1)
    
    print("\n✅ All evaluations passed successfully.")

asyncio.run(main())