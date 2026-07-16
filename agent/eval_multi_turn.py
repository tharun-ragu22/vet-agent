import asyncio
import logfire
from pydantic_ai import ModelMessage
from pydantic_evals import Case, Dataset
from dataclasses import dataclass
from pydantic_evals.evaluators import EvaluationReason, HasMatchingSpan, Evaluator, EvaluatorContext, Contains
from .local_agent import LocalAgent
import sys
import json
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
class ConversationInputs:
    turns: list[str]

@dataclass
class ParseAppointmentNotChecked(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> bool:
        return not ctx.span_tree.any(
            {
                "and_": [
                    {"name_equals": "running tool"},
                    {"has_attributes": {"gen_ai.tool.name": "check_availability"}},
                ]
            }
        )


@dataclass
class CheckAvailability_NoneFoundFirstTime(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> EvaluationReason:
        check_calls = ctx.span_tree.find(
            {
                "and_": [
                    {"name_equals": "running tool"},
                    {"has_attributes": {"gen_ai.tool.name": "check_availability"}},
                ]
            }
        )
        if not check_calls:
            return False
        
        print('check call attrs:', check_calls[0].attributes)
        tool_result = json.loads(check_calls[0].attributes.get('tool_response'))
        
        return EvaluationReason(
            value=len(tool_result) == 0,
            reason="got to end"
        )

@dataclass
class CheckAvailability_AppointmentsFoundOnNthTime(Evaluator):
    nth_time: int
    def evaluate(self, ctx: EvaluatorContext) -> EvaluationReason:
        check_calls = ctx.span_tree.find(
            {
                "and_": [
                    {"name_equals": "running tool"},
                    {"has_attributes": {"gen_ai.tool.name": "check_availability"}},
                ]
            }
        )
        if not check_calls:
            return False
        
        print('check call attrs:', check_calls[self.nth_time].attributes)
        tool_result = json.loads(check_calls[self.nth_time].attributes.get('tool_response'))
        
        return EvaluationReason(
            value=len(tool_result) == 1,
            reason="got to end"
        )
    
# 1. Initialize local-only logfire
logfire.configure(send_to_logfire=False)

# 2. Tell PydanticAI to send its spans to this local tracker
logfire.instrument_pydantic_ai()

test_agent = LocalAgent(connection)
dataset = Dataset(
    name="multi-turn",
    cases=[
        Case(
            name="book_then_confirm",
            inputs=ConversationInputs(turns=[
                "I'd like to book an appointment for my dog Max for today at 3pm",
                "I just booked an appointment for my dog Max for today at 3pm. Can you confirm it is still happening",
            ]),
            evaluators=[
                CheckAvailability_NoneFoundFirstTime(),
                CheckAvailability_AppointmentsFoundOnNthTime(nth_time=1)
            ]
        ),
        Case(
            name="make_appointment_provide_missing_name",
            inputs=ConversationInputs(turns=[
                "Can you make an appointment for my dog today at 2pm?",
                "His name is Jordan",
            ]),
            evaluators=[
                HasMatchingSpan(
                    query={"has_attributes": {"gen_ai.tool.name": "make_appointment"}}
                ),
            ]
        ),
        Case(
            name="make_appointment_provide_missing_time",
            inputs=ConversationInputs(turns=[
                "Can you make an appointment for my dog Jake today?",
                "At 3pm please",
            ]),
            evaluators=[
                HasMatchingSpan(
                    query={"has_attributes": {"gen_ai.tool.name": "make_appointment"}}
                ),
            ]
        ),
        Case(
            name="check_appointment_provide_missing_time",
            inputs=ConversationInputs(turns=[
                "Can you check if my dog Jake has an appointment for today?",
                "At 3pm",
            ]),
            evaluators=[
                HasMatchingSpan(
                    query={"has_attributes": {"gen_ai.tool.name": "check_availability"}}
                ),
            ]
        ),
        Case(
            name="redirect_try_agent_first",
            inputs=ConversationInputs(turns=[
                "Can you check if my dog Jake has an appointment?",
                "Human representative",
            ]),
            evaluators=[
                Contains(
                    value="REDIRECT",
                    as_strings=True
                ),
                ParseAppointmentNotChecked()
            ],
        ),

    ],

)

async def multi_turn_task(inputs: ConversationInputs) -> str:
    cursor.executescript(RESET_TABLE_COMMAND)
    message_history: list[ModelMessage] = []
    last_output = ""

    for user_message in inputs.turns:
        result = await test_agent.run_agent(
            user_message,
            message_history=message_history,
        )
        message_history = result.all_messages()
        last_output = result.output

    
    return last_output

async def main():

    report = await dataset.evaluate(multi_turn_task, max_concurrency=1)

    report.print(include_reasons=True)

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