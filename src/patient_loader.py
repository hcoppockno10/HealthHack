from abc import ABC, abstractmethod
import json

from .models import Patient

class PatientSchemaHandler(ABC):
    @abstractmethod
    def load_patient(self, data_dict: dict) -> Patient:
        pass


class V1Handler(PatientSchemaHandler):
    def load_patient(self, data_dict: dict) -> Patient:
        prescription_profile = data_dict.get("prescription_profile")
        if not prescription_profile:
            raise ValueError("Data dictionary does not contain a prescription profile or medical history")

        return Patient(
            patient_id=data_dict["patient_id"],
            age=data_dict["age"],
            gender=data_dict["gender"],
            prescription_profile=prescription_profile,
            consultations=data_dict.get("consultations", []),
            medical_data=data_dict.get("medical_data"),
        )
    
def load_jsonl(file_path: str, handler: PatientSchemaHandler):
    with open(file_path, "r") as file:
        for line in file:
            data_dict = json.loads(line)
            yield handler.load_patient(data_dict)