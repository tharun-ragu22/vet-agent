import asyncio
import logfire
from pydantic_evals import Case, Dataset
from dataclasses import dataclass
from pydantic_evals.evaluators import EvaluationReason, HasMatchingSpan, Evaluator, EvaluatorContext, LLMJudge
from pydantic_evals.evaluators.llm_as_a_judge import set_default_judge_model
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider
from .local_agent import LocalAgent
from .agent_interface import AgentBaseClass
from dotenv import load_dotenv
import sys
import sqlite3
import os
from .custom_evaluators import GetDatetimeFromPhrase_CheckKeyWords

load_dotenv()

eval_llm_judge = OllamaModel(
    model_name=os.getenv("LOCAL_MODEL_NAME"),
    provider=OllamaProvider(
        base_url=os.getenv("LOCAL_MODEL_URL"),
    ),
)
set_default_judge_model(eval_llm_judge)

connection = sqlite3.connect(":memory:", check_same_thread=False)
cursor = connection.cursor()
AgentBaseClass.create_schema(connection)

AGGRESSIVE_PATIENT_NAME = "Rex"
CALM_PATIENT_NAME = "Cosette"

AgentBaseClass.mark_patient_aggressive_impl(AGGRESSIVE_PATIENT_NAME, connection)


def reset_appointments():
    cursor.executescript("DROP TABLE IF EXISTS appointments;")
    AgentBaseClass.create_schema(connection)


@dataclass
class AppointmentNotRecordedInDB(Evaluator):
    """Check that no appointment was recorded for the given patient"""
    patient_name: str

    def evaluate(self, ctx: EvaluatorContext) -> bool:
        result = AgentBaseClass.check_appointment_impl(self.patient_name, None, None, connection)
        return len(result) == 0


@dataclass
class AppointmentRecordedInDB(Evaluator):
    """Check that an appointment was recorded for the given patient"""
    patient_name: str

    def evaluate(self, ctx: EvaluatorContext) -> bool:
        result = AgentBaseClass.check_appointment_impl(self.patient_name, None, None, connection)
        return len(result) == 1


@dataclass
class OutputDoesNotLeakAggressiveLabel(Evaluator):
    """Check that the caller-facing response never uses the word "aggressive" itself"""
    def evaluate(self, ctx: EvaluatorContext) -> bool:
        return "aggressive" not in str(ctx.output).lower()


@dataclass
class CheckAvailability_ResponseRejectsAggressivePatient(Evaluator):
    """Check that the check_availability tool reported an aggressive-patient rejection"""
    def evaluate(self, ctx: EvaluatorContext) -> EvaluationReason:
        calls = ctx.span_tree.find(
            {
                "and_": [
                    {"name_equals": "running tool"},
                    {"has_attributes": {"gen_ai.tool.name": "check_availability"}},
                ]
            }
        )
        if not calls:
            return EvaluationReason(value=False, reason="no check_availability calls found")

        tool_response = calls[0].attributes.get("tool_response")
        print("check_availability response:", tool_response)

        return EvaluationReason(
            value=tool_response is not None and "aggressive" in str(tool_response).lower(),
            reason="tool response should mention the aggressive-patient rejection"
        )


@dataclass
class MakeAppointmentNotCalled(Evaluator):
    """Check that the make_appointment tool was never invoked"""
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
    name="aggressive patient appointment rejection",
    cases=[
        Case(
            name="aggressive-patient-appointment-rejected",
            inputs=f"""
            Hi, my name is Hughie Campbell, I'm a current patient with you guys.
            My dog {AGGRESSIVE_PATIENT_NAME} needs an appointment for 5 o'clock today. Is this possible?
            """,
            evaluators=[
                HasMatchingSpan(
                    query={"has_attributes": {"gen_ai.tool.name": "check_availability"}}
                ),
                CheckAvailability_ResponseRejectsAggressivePatient(),
                MakeAppointmentNotCalled(),
                AppointmentNotRecordedInDB(patient_name=AGGRESSIVE_PATIENT_NAME),
                OutputDoesNotLeakAggressiveLabel(),
                LLMJudge(
                    rubric='Response should tell the caller that the appointment requires special handling',
                    assertion={'evaluation_name': 'mentions-special-handling'}
                ),
                LLMJudge(
                    rubric='Response should tell the caller that the appointment cannot be booked over the phone',
                    assertion={'evaluation_name': 'cannot-book-over-phone'}
                ),
            ],
        ),
        Case(
            name="non-aggressive-patient-appointment-allowed",
            inputs=f"""
            Hi, my name is Hughie Campbell, I'm a current patient with you guys.
            My dog {CALM_PATIENT_NAME} needs an appointment for 5 pm today. Is this possible?
            """,
            evaluators=[
                HasMatchingSpan(
                    query={"has_attributes": {"gen_ai.tool.name": "make_appointment"}}
                ),
                AppointmentRecordedInDB(patient_name=CALM_PATIENT_NAME),
                GetDatetimeFromPhrase_CheckKeyWords(expected_keywords=['today', '5 pm'])
            ],
        ),
    ],
)

async def run_agent_task(inputs: str) -> str:
    reset_appointments()
    return await test_agent.run_agent(inputs)

async def main():

    report = await dataset.evaluate(run_agent_task, max_concurrency=1)

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
