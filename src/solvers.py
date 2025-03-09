from datetime import datetime, timedelta
from typing import List
import logging

from inspect_ai.solver import solver, Generate, TaskState, Solver
from inspect_ai.model import ChatMessageSystem, ChatMessageUser

from src.models import PrescriptionEvent, Patient, Consultation
from src.prompts import SYSTEM_MESSAGE, FORMAT_RESPONSE_PROMPT, MEDICAL_DATA_PROMPT, USE_BROWSER_PROMPT, USE_BNF_TOOL_PROMPT

logger = logging.getLogger(__name__)

def active_at_date(
    prescription_profile: List[PrescriptionEvent], date: datetime = None
) -> List[PrescriptionEvent]:
    """
    only includes prescription events that occurred at most six months before `date`.

    Args:
        prescription_profile (List[PrescriptionEvent])
        date (datetime, optional): If None, defaults to the latest prescription event date.

    Returns:
        List[PrescriptionEvent]: Filtered list of events within six months of the date,
        with `active` flags set on each drug's event.
    """

    # If no date is provided, default to the max date found in the prescription_profile
    if date is None:
        date = max((obj.date for obj in prescription_profile), default=None)
        if date is None:
            # No prescription events at all
            return []

    # Calculate the cutoff for six months prior (approx 180 days)
    six_months_ago = date - timedelta(days=180)

    # Filter events to only those within six months of `date`
    filtered_profile = [
        event for event in prescription_profile
        if event.date >= six_months_ago
    ]

    return filtered_profile

def format_prescription_profile(patient: Patient, consultation: Consultation) -> str:
    profile_prompt = r"""
    Patient Profile:
    - Patient Identifier: {patient_id}
    - Patient Age: {patient_age}
    - Patient Gender: {patient_gender}

    Prescription Profile:
    """

    prompt = profile_prompt.format(
        patient_id=patient.patient_id,
        patient_age=patient.age,
        patient_gender=patient.gender,
    )

    for event in consultation.prescription_profile:

        prompt += f"""
----------------------------
Prescription Event:
    - Prescription Date: {event.date}
Drugs:
    """

        for drug in event.drugs:
            prompt += f"""
--------------------------------
- Drug Name: {drug.name}
- Drug Quantity: {drug.quantity}
"""

    return prompt

def format_medical_data(patient: Patient) -> str:
    if not patient.medical_data:
        raise ValueError("No medical data provided for the patient")

    medical_data: str = ""
    for event in patient.medical_data:
        medical_data += f"""
Consultation Event: {event.date_of_consultation}
- GP Notes: {event.gp_notes}
- Blood Pressure: {event.blood_pressure.blood_pressure_systolic}/{event.blood_pressure.blood_pressure_diastolic}
- Unplanned Hospital Admissions: {event.unplanned_hospital_admissions}
- Deprivation Index (0 most deprived 10 least deprived): {event.deprivation_index}
- Serum Sodium: {event.serum_sodium}
- Haemoglobin: {event.haemoglobin}
- Oxygen Saturation: {event.oxygen_saturation}
- Heart Rate: {event.heart_rate}
"""
    return medical_data

@solver
def process_prescription_information(
    system_message: str = SYSTEM_MESSAGE,
    format_response_prompt: str = FORMAT_RESPONSE_PROMPT,
    medical_data_prompt: str = MEDICAL_DATA_PROMPT,

) -> Solver:
    """
    Process prescription information to extract relevant information
    """
    async def solve(state: TaskState, generate: Generate):

        patient: Patient = state.metadata['patient_data']

        consultation = Consultation(
            date_performed=datetime.now(),
            indicators=None,
            prescription_profile= active_at_date(patient.prescription_profile),
        )

        patient_info: str = format_prescription_profile(patient, consultation)
        consultation_info: str = format_medical_data(patient)

        state.messages.append(
            ChatMessageSystem(content=system_message)
        )
        state.messages.append(
            ChatMessageUser(content=patient_info + consultation_info + medical_data_prompt + format_response_prompt + USE_BROWSER_PROMPT + USE_BNF_TOOL_PROMPT)
        )

        return state
    return solve