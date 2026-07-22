import asyncio
import logfire
from pydantic_evals import Case, Dataset
from dataclasses import dataclass
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, Contains  
from .local_summarizer_agent import LocalSummarizerAgent
import sys
from dataclasses import dataclass
from pydantic_evals.evaluators import LLMJudge
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider
from dotenv import load_dotenv
from pydantic_evals.evaluators.llm_as_a_judge import set_default_judge_model
import os

load_dotenv()
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
eval_llm_judge = OllamaModel(
    model_name=os.getenv("LOCAL_MODEL_NAME"),
    provider=OllamaProvider(
        base_url=os.getenv("LOCAL_MODEL_URL"),
    ),
)
set_default_judge_model(eval_llm_judge)

dataset = Dataset(
    name="veteranarian agent tests",
    cases=[
        Case(
            name="recognize-medical-emergency",
            inputs="""
            Transcript:
            User: My dog has been vomiting for the past 20 minutes. Is this an emergency?
            """,
            evaluators=[
                Contains(
                    value="vomit",
                    as_strings=True,
                    case_sensitive=False
                )
            ],
        ),
        Case(
            name="immediate-redirect",
            inputs="""
            Transcript:
            User: Operator
            """,
            evaluators=[
                LLMJudge(
                    rubric='Response should mention no specific caller identification.',
                    model=eval_llm_judge,
                    assertion={
                        'evaluation_name': 'no-caller-info'
                    }
                ),
                
            ],
        ),
    ],
    evaluators=[
        LLMJudge(
            rubric='Response describes summary of transcript like one person providing context about the call to the next person, in full sentences',
            assertion={
                'evaluation_name': 'sounds-like-convo',
                'include_reason': True,
            },
        ),
        LLMJudge(
            rubric='Response should not attempt to fabricate any information that is not provided in the input transcript',
            assertion={
                'evaluation_name': 'no-fake-info',
                'include_reason': True,
                'include_input': True
            },
        ),
        WordLimitEvaluator(max_sentences=5)
    ]
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
