import re
from abc import abstractmethod
from typing import Any, Callable, Dict, List, Literal, Optional, Type, Union

from markdownify import markdownify
from pydantic import AnyUrl, BaseModel, Field

class ToolResponseModel(BaseModel):
    @property
    @abstractmethod
    def prompt(self) -> str:
        "The part of the response to send to the model"
        pass

class Interaction(ToolResponseModel):
    """BNF drug interactions"""

    # TODO these should be constrained to only allow the expected values
    root_drug: str
    drug_name: str
    severity: str
    additiveEffect: bool
    description: str
    url: Optional[Union[AnyUrl, str]] = None  # allow string so it is JSON serializable
    evidence: Optional[Union[str, Type[None]]] = None

    @property
    def prompt(self) -> str:
        tmp_prompt = ""
        tmp_prompt += f"### {self.root_drug} -- {self.drug_name}\n----\n"
        tmp_prompt += f"Severity: {self.severity}\n\r"
        tmp_prompt += f"Additive Effects: {self.additiveEffect}\n\r"
        tmp_prompt += f"Evidence for Interaction: {self.evidence}\n\r"
        tmp_prompt += f"Description: {markdownify(self.description)}\n\r"
        return tmp_prompt


class InteractionList(ToolResponseModel):
    """List of BNF drug interactions"""

    interactions: List[Interaction] = []
    no_match: Optional[List] = []

    @property
    def prompt(self) -> str:
        prompt = "The following interactions were found:\n====\n"
        for interaction in self.interactions:
            prompt += interaction.prompt
        # TODO the below is not formatted correctly so commented out
        if self.no_match:
            prompt += "\n\n Some drugs were not found in the BNF database and therefore could not be checked for interactions:"
            # for item in self.no_match:
            #    tmp_prompt += f"\n{item[0]}"
        return prompt


class DrugProfile(ToolResponseModel):
    """BNF drug profiles"""

    title: str
    slug: str
    primaryClassification: dict
    secondaryClassifications: Optional[Union[Dict, List[Dict]]]
    allergyAndCrossSensitivity: Optional[Dict] = None
    breastFeeding: Optional[Dict] = None
    conceptionAndContraception: Optional[Union[Dict, List[Dict]]] = None
    contraIndications: Optional[Union[Dict, List[Dict]]] = None
    cautions: Optional[Union[Dict, List[Dict]]] = None
    constituentDrugs: Optional[Union[Dict, List[Dict]]] = None
    directionsForAdministration: Optional[Union[Dict, List[Dict]]] = None
    drugAction: Optional[Union[Dict, List[Dict]]] = None
    effectOnLaboratoryTests: Optional[Union[Dict, List[Dict]]] = None
    exceptionsToLegalCategory: Optional[Union[Dict, List[Dict]]] = None
    handlingAndStorage: Optional[Union[Dict, List[Dict]]] = None
    hepaticImpairment: Optional[Union[Dict, List[Dict]]] = None
    importantSafetyInformation: Optional[Union[Dict, List[Dict]]] = None
    indicationsAndDose: Optional[Union[Dict, List[Dict]]] = None
    interactants: Optional[Union[Dict, List[Dict]]] = None
    lessSuitableForPrescribing: Optional[Union[Dict, List[Dict]]] = None
    medicinalForms: Optional[Union[Dict, List[Dict]]] = None
    monitoringRequirements: Optional[Union[Dict, List[Dict]]] = None
    nationalFunding: Optional[Union[Dict, List[Dict]]] = None
    palliativeCare: Optional[Union[Dict, List[Dict]]] = None
    patientAndCarerAdvice: Optional[Union[Dict, List[Dict]]] = None
    preTreatmentScreening: Optional[Union[Dict, List[Dict]]] = None
    pregnancy: Optional[Union[Dict, List[Dict]]] = None
    prescribingAndDispensingInformation: Optional[Union[Dict, List[Dict]]] = None
    professionSpecificInformation: Optional[Union[Dict, List[Dict]]] = None
    renalImpairment: Optional[Union[Dict, List[Dict]]] = None
    sideEffects: Optional[Union[Dict, List[Dict]]] = None
    treatmentCessation: Optional[Union[Dict, List[Dict]]] = None
    relatedTreatmentSummaries: Optional[Union[Dict, List[Dict]]] = None
    relatedNursePrescribersTreatmentSummaries: Optional[Union[Dict, List[Dict]]] = None
    unlicensedUse: Optional[Union[Dict, List[Dict]]] = None
    url: Optional[Union[AnyUrl, str]] = None  # allow string so it is JSON serializable

    def drug_content(self, drug_dict: dict | None) -> str:
        """
        bnf for drug content has fixed structure
        """
        drug_dict = drug_dict["drugContent"]
        if drug_dict is None:
            return ""

        content_for: str = drug_dict.get("contentFor", "")
        content: str = drug_dict.get("content", "")

        return content_for + content

    def drug_class_content(self, drug_dict: Union[Dict, List] | None) -> str:
        """
        bnf for drug class content has fixed structure
        """
        ""
        drug_dict = drug_dict["drugClassContent"]
        if drug_dict is None:
            return ""
        if isinstance(drug_dict, List):
            content = [f"{drug['contentFor']} {drug['content']}" for drug in drug_dict]
            return "\n----\n".join(content)
        elif isinstance(drug_dict, Dict):
            content = f"{drug_dict['contentFor']} {drug_dict['content']}"
            return content

    @property
    def prompt(self) -> str:
        prompt: str = "BNF Drug Profile\n====\n"

        prompt += f"Drug Name: {self.title}\n====\n"

        prompt += "Drug Action: \n====\n"
        if self.drugAction:
            prompt += self.drug_content(self.drugAction)
            prompt += "\n----\n"
            prompt += self.drug_class_content(self.drugAction)

        if self.cautions:
            prompt += "Cautions: \n====\n"
            prompt += markdownify(self.drug_content(self.cautions))
            prompt += "\n----\n"
            prompt += markdownify(self.drug_class_content(self.cautions))

        if self.sideEffects:
            prompt += "Side Effects: \n====\n"
            prompt += markdownify(self.drug_content(self.sideEffects))
            prompt += "\n----\n"
            prompt += markdownify(self.drug_class_content(self.sideEffects))
        return prompt