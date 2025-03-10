import os

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.scorer import includes
from inspect_ai.solver import generate, use_tools
from inspect_ai.tool import web_browser, ToolFunction

from inspect_ai.dataset import Sample, json_dataset, Dataset

from src.patient_loader import load_jsonl, V1Handler
from src.models import Patient
from src.solvers import process_prescription_information
from src.drug_tools import bnf_drug_interactions_tool, bnf_drug_profiles_tool

from src.contribution import medication_review_critique



def record_to_sample(record: Patient) -> Sample:


    return Sample(
        input='None', # we will unpack with solvers on the fly
        target='None', # we will be comparing consistency, no ground truth
        id=record.patient_id,
        metadata={'patient_data': record},
    )


dataset = list(load_jsonl(
    os.environ.get("PATIENTS_FILE"),
    V1Handler()
    )
    )

#convert to inspect samples
inspect_dataset: Dataset = [record_to_sample(record) for record in dataset]

@task
def medication_review():
    return Task(
        dataset=inspect_dataset,
        solver=[
            process_prescription_information(),
            use_tools([
                *web_browser(),
                bnf_drug_profiles_tool(),
                bnf_drug_interactions_tool()
            ],
            ),
            generate(),
            medication_review_critique(),
        ],
        scorer=None,
        sandbox="docker",
    )
