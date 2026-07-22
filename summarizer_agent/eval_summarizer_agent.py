import asyncio
import logfire
from pydantic_evals import Case, Dataset
from dataclasses import dataclass
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, Contains  
from .local_summarizer_agent import LocalSummarizerAgent
import sys
from dataclasses import dataclass

@dataclass
class WordLimitEvaluator(Evaluator):
    max_sentences: int = 5
    
    def evaluate(self, ctx: EvaluatorContext) -> EvaluationReason:
        # ctx.output contains the agent's response string
        words : str = ctx.output
        num_sentences = words.count('.')
        
        passed = num_sentences <= self.max_sentences
        reason = f"Response has {num_sentences} sentences (Limit: {self.max_sentences})"
        
        return EvaluationReason(value=passed, reason=reason)

# 1. Initialize local-only logfire
logfire.configure(send_to_logfire=False)

# 2. Tell PydanticAI to send its spans to this local tracker
logfire.instrument_pydantic_ai()

test_agent = LocalSummarizerAgent()
dataset = Dataset(
    name="veteranarian agent tests",
    cases=[
        Case(
            name="recognize-medical-emergency",
            inputs="""
            User: My dog has been vomiting for the past 20 minutes. Is this an emergency?
            """,
            evaluators=[
                Contains(
                    value="vomit",
                    as_strings=True,
                    case_sensitive=False
                ),
                WordLimitEvaluator(max_sentences=5)
            ],
        ),
    ],
)

def mock_agent_task(inputs: str) -> str:
    return inputs.upper()

async def run_agent_task(inputs: str) -> str:
    result = await test_agent.run_agent(inputs)
    print('final result:', result)
    return result.output

async def main():

    report = await dataset.evaluate(run_agent_task)

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
