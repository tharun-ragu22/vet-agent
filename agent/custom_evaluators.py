from dataclasses import dataclass
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext  

import json

@dataclass
class GetDatetimeFromPhrase_CheckKeyWords(Evaluator):
    expected_keywords: list[str]
    def evaluate(self, ctx: EvaluatorContext) -> EvaluationReason:
        calls = ctx.span_tree.find(
            {
                "and_": [
                    {"name_equals": "running tool"},
                    {"has_attributes": {"gen_ai.tool.name": "get_datetime_from_phrase"}},
                ]
            }
        )
        if not calls:
            return EvaluationReason(value = False, reason='did not try to get datetime')
        print('all get datetime calls:', calls)
        call = calls[0]
        print(call.attributes)

        phrase = json.loads(call.attributes.get('tool_arguments')).get('phrase')
        if not phrase:
            return EvaluationReason(value = False, reason='phrase not passed in')

        missing_keywords = []
        for kw in self.expected_keywords:
            if kw not in phrase:
                missing_keywords.append(kw)
                break
        
        return EvaluationReason(value= len(missing_keywords) == 0, reason=f"{phrase} missing {len(missing_keywords)} keyword{'s' if len(missing_keywords) != 1 else ''}: {missing_keywords}")
