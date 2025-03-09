from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, computed_field

from inspect_ai.model import ChatMessage



class StructuredPrescriptionInformation(BaseModel):
    min_consumption_frequency: Optional[float] = Field(description="Minimum consumption frequency (per time period)")
    max_consumption_frequency: Optional[float] = Field(description="Maximum consumption frequency (per time period)")
    time_period: Optional[Literal["daily", "weekly", "monthly"]] = Field(
        description="Time period (daily, weekly, or monthly)", default="daily"
    )
    min_administrations_at_each_consumption: Optional[float] = Field(
        description="Minimum number of administrations at each consumption"
    )
    max_administrations_at_each_consumption: Optional[float] = Field(
        description="Maximum number of administrations at each consumption"
    )
    min_dose_quantity: Optional[str] = Field(
        description="Minimum dose quantity, a drug quantity or measurement e.g. '5ml'"
    )
    max_dose_quantity: Optional[str] = Field(
        description="Maximum dose quantity, a drug quantity or measurement e.g. '5ml'"
    )
    administration_unit: Optional[str] = Field(
        description="The form or unit of the medication, e.g., 'tablet', 'puff', 'sachet'"
    )
    as_needed: bool = Field(description="Boolean indicating whether the drug is to be taken 'as needed'", default=False)
    as_directed: bool = Field(
        description="Boolean indicating whether the drug is to be taken 'as directed'", default=False
    )

    @computed_field
    @property
    def default_consumption_frequency(self) -> Optional[float]:
        if self.min_consumption_frequency is not None and self.max_consumption_frequency is not None:
            return (self.min_consumption_frequency + self.max_consumption_frequency) / 2
        elif self.min_consumption_frequency is not None:
            return self.min_consumption_frequency
        elif self.max_consumption_frequency is not None:
            return self.max_consumption_frequency
        else:
            return None

    @computed_field
    @property
    def default_administration_quantity(self) -> Optional[float]:
        if (
            self.min_administrations_at_each_consumption is not None
            and self.max_administrations_at_each_consumption is not None
        ):
            return (self.min_administrations_at_each_consumption + self.max_administrations_at_each_consumption) / 2
        elif self.min_administrations_at_each_consumption is not None:
            return float(self.min_administrations_at_each_consumption)
        elif self.max_administrations_at_each_consumption is not None:
            return float(self.max_administrations_at_each_consumption)
        else:
            return None


class MultiShotStructuredPrescriptionInformation(StructuredPrescriptionInformation):
    explanation: Optional[str] = Field(
        description="The explanation of the structured prescription information", default=None
    )
    instruction: Optional[str] = Field(
        description="The instruction of the structured prescription information", default=None
    )


class DrugEvent(StructuredPrescriptionInformation):
    # From drug object
    instructions_to_patient: Optional[str] = Field(description="The instructions given by the prescriber", default=None)
    quantity: Optional[int] = Field(description="The number of units issued.", default=None)
    start_date: Optional[datetime] = Field(description="The date the prescription was issued", default=None)

    end_date: Optional[datetime] = Field(
        description="Estimate of date the patient will stop taking medication ", default=None
    )
    active: Optional[bool] = Field(
        description="The drug was taken at a specified date, assuming the dosage instructions were followed.",
        default=None,
    )
    duration: Optional[float] = Field(description="How long the drug is taken for (days)", default=None)


class Drug(BaseModel):
    id: int
    name: str
    quantity: int
    event: Optional[DrugEvent] = None
    dosage: Optional[str] = None
    instructions_to_patient: Optional[str] = None
    bnf_code: Optional[str] = None


class PrescriptionEvent(BaseModel):
    id: int
    drugs: List[Drug]
    date: datetime


class BloodPressure(BaseModel):
    blood_pressure_systolic: int = Field(
        title="Systolic Blood Pressure",
        description="The systolic pressure of the blood units mmHg. e.g. 120",
    )
    blood_pressure_diastolic: int = Field(
        title="Diastolic Blood Pressure",
        description="The Diastolic pressure of the blood units mmHg. e.g. 80",
    )


class MedicalConsulation(BaseModel):
    """
    Medical information from a general practice consultation
    """

    date_of_consultation: datetime = Field(
        title="Date and time of Consultation",
        description="The date and time of the consultation with the general practice doctor.",
    )
    gp_notes: str = Field(
        title="General Practice doctor notes",
        description="The notes that a general practice doctor has made about the patient. This should make no mention of the patient's prescription profile. This should be purely about the patient's health and medical history e.g. conditions they have, symptoms they complain about and general points of health.",
    )
    blood_pressure: BloodPressure = Field(
        title="Blood Pressure",
        description="The blood pressure of the patient.",
    )
    unplanned_hospital_admissions: int = Field(
        title="Number of unplanned hospital admissions since last consultation",
        description="The number of times the patient has been admitted to the hospital without prior planning since the last consulation.",
    )
    deprivation_index: int = Field(
        title="Deprivation Index",
        description="A measure of the deprivation of the area the patient lives in. Where 0 is the most deprived and 10 is the least deprived.",
        ge=0,
        le=10,
    )

    serum_sodium: float = Field(
        title="Serum Sodium",
        description="The concentration of sodium in the patient's blood. X mmol/L e.g. 135mmol/L.",
    )
    haemoglobin: float = Field(
        title="Haeomoglobin",
        description="The concentration of haemoglobin in the patient's blood. X g/dL e.g. 14g/dL.",
    )

    oxygen_saturation: int = Field(
        title="Oxygen Saturation",
        description="The concentration of oxygen in the patient's blood. X% e.g. 98%.",
    )

    heart_rate: int = Field(
        title="Heart Rate",
        description="The rate at which the patient's heart beats. X bpm e.g. 72 bpm.",
    )


class LLMFlagIndicator(BaseModel):
    reasoning: Optional[str] = Field(
        None,
        description="A detailed but concise explanation of why the output was selected. This should be evidence-based and leave little for interpretation.",
    )
    flag: Optional[Literal["Yes", "No"]] = Field(
        None,
        description='Details whether the prescription profile should be reviewed. Only "Serious" and "Severe" cases should be flagged for review.',
    )
    severity: Optional[Literal["No Harm", "Minor", "Moderate", "Serious", "Severe"]] = Field(
        None,
        description="Based on the Harm Associated with Medication Errors Classification (HAMEC) scale.",
    )


class Indicators(BaseModel):
    """
    Indicators of the patient's health
    """

    llm_flag: Optional[LLMFlagIndicator] = Field(
        title="AI Flag",
        description="The output from the LLM model. This should be a summary of the output from the LLM model and should not include any prescription information.",
    )


class Consultation(BaseModel):
    date_performed: Optional[datetime] = None
    message_history: Optional[List[ChatMessage]] = []
    indicators: Optional[Indicators]
    prescription_profile: Optional[List[PrescriptionEvent]] = []


class Patient(BaseModel):
    patient_id: int
    schema_version: int = 1
    age: int
    gender: str
    prescription_profile: List[PrescriptionEvent]
    organisation: Optional[str] = "P2U"
    created_datetime: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    consultations: List[Consultation]
    medical_data: Optional[List[MedicalConsulation]] = Field(
        title="Medical Data",
        description=" This should be a comprehensive list of all the patient's medical history (excluding prescription information).",
    )

    @property
    def latest_consultation(self) -> Consultation:
        return self.consultations[-1]

    @property
    def latest_medical_data(self) -> MedicalConsulation:
        if self.medical_data:
            return self.medical_data[-1]
        else:
            raise ValueError("No medical data for patient")

    def currently_active_drugs(self) -> List[Drug]:
        return self.active_drugs(datetime.now())

    def active_drugs(self, query_date: datetime) -> List[Drug]:
        """Get all drugs that are currently being taken on a given date

        Args:
            query_date (datetime)

        Returns:
            List[Drug]
        """
        active_drugs = []
        for prescription_event in self.prescription_profile:
            for drug in prescription_event.drugs:
                if drug.event and (drug.event.start_date <= query_date <= drug.event.end_date):
                    active_drugs.append(drug)
        return active_drugs