from datetime import datetime, timedelta
from typing import List
import logging

from inspect_ai.solver import solver, Generate, TaskState, Solver
from inspect_ai.model import ChatMessageSystem, ChatMessageUser, ChatMessageAssistant, Model, get_model
from inspect_ai._util.dict import omit
from inspect_ai.util import resource

@solver
def medication_review_critique(
    critique_template: str | None = None,
    completion_template: str | None = None,
    model: str | Model | None = None,
) -> Solver:
    """
    Solver which uses a model to critique a structured medication review answer.

    The `critique_template` is used to generate a critique
    and the `completion_template` is used to play that critique
    back to the model for an improved structured medication review response. 
    Note that you can specify an alternate `model` for critique 
    (you don't need to use the model being evaluated).

    Args:
      critique_template (str): String or path to file containing the critique template. 
          The template uses the variables: 'question' and 'completion'. 
          Variables from sample `metadata` are also available.
      completion_template (str): String or path to file containing the completion template. 
          The template uses 'question', 'completion', and 'critique'.
      model (str | Model): Alternate model to be used for critique 
          (by default, the model being evaluated is used).
    """
    # Resolve the templates
    critique_templ = resource(critique_template or DEFAULT_CRITIQUE_TEMPLATE)
    completion_templ = resource(
        completion_template or DEFAULT_CRITIQUE_COMPLETION_TEMPLATE
    )

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        nonlocal model
        model = model if isinstance(model, Model) else get_model(model)

        model_reasoning: str = '\n\n'.join([message.content for message in state.messages])

        # 1) Generate a critique of the existing medication review answer
        critique = await model.generate(
            critique_templ.format(
                smr=model_reasoning,
                completion=state.output.completion,
            )
        )

        # 2) Feed the question, original answer, and the critique back in for an improved answer
        state.messages.append(
            ChatMessageUser(
                content=completion_templ.format(
                    critique=critique.completion,
                ),
            )
        )

        # 3) Regenerate answer using the critique
        return await generate(state)

    return solve


DEFAULT_CRITIQUE_TEMPLATE = r"""
You are an expert in structured medication reviews. PPLEASE REVIEW THIS PRESCRIPTION PROFILE AND DECIDE IF ITS CORRECT
Consider whether it addresses:
- Indications
- Efficacy (or Effectiveness)
- Safety (including adverse effects and interactions)
- Adherence
- Cost or feasibility
- Any other relevant patient factors

If the answer is fully correct and comprehensive, respond with exactly: "The original answer is fully correct".

[BEGIN DATA]
***
SMR trace: {smr}
***
[END DATA]

Critique:
"""

DEFAULT_CRITIQUE_COMPLETION_TEMPLATE = r"""
You are an expert in structured medication reviews. The user asked for a medication review. 
Below is the original answer and a critique of that answer. 
Using the critique, produce an improved structured medication review that addresses: 
- Indications
- Efficacy (or Effectiveness)
- Safety (including adverse effects and interactions)
- Adherence
- Cost or feasibility
- Other relevant patient factors

If the original answer is fully correct, repeat it verbatim.

[BEGIN DATA]
***
[Critique]: {critique}
***
[END DATA]

Provide your final revised answer (or the same one, if fully correct), in the following format:

**Reasoning:** <reasoning>
**Flag:** <flag>
**Severity:** <severity>

"""