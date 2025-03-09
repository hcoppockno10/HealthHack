import json
import logging
from typing import Any, List, Union

import pandas as pd
from rapidfuzz import process
from inspect_ai.tool import tool, ToolError, Tool

from .tool_models import Interaction, InteractionList, DrugProfile

# If you prefer to read these from environment variables or a config file, you can do so.
DATA_ROOT = ".data"
DRUG_PROFILE_LOC = DATA_ROOT + "/bnf-drug-data/data/drug_profile_slugs.tsv"
DRUG_SPECIFIC_LOC = DATA_ROOT + r"/bnf-drug-data/data/drugs/{drug_name}.json"

DRUG_INTERACTION_PROFILE_LOC = DATA_ROOT + r"/bnf-drug-data/data/drug_interaction_slugs.tsv"
DRUG_INTERACTION_SPECIFIC_LOC = DATA_ROOT + r"/bnf-drug-data/data/drug_interactions/{drug_name}.json"
BRAND_DRUG_LOC = DATA_ROOT + r"/bnf-drug-data/data/synonyms.tsv"

DEFAULT_THRESHOLD = 90  # Fuzzy matching threshold


def map_ingredients(drug_name: str, synonyms: dict, threshold: int = DEFAULT_THRESHOLD):
    """Resolve a drug name to a list of ingredients."""
    drug_name = drug_name.lower().strip()

    if drug_name in synonyms:
        # Direct match
        return synonyms[drug_name].split(", ")
    else:
        # Fuzzy match among synonyms
        best_match = process.extractOne(drug_name, synonyms.keys())
        if best_match and best_match[1] > threshold:
            return synonyms[best_match[0]].split(", ")
        else:
            # Return the original name if no good match found
            return drug_name


def ingredient_to_bnf_profile(ingredient: str, bnf_profiles: dict, threshold: int = DEFAULT_THRESHOLD):
    """Resolve a single ingredient to a BNF profile slug."""
    ingredient = ingredient.lower().strip()

    if ingredient in bnf_profiles:
        return bnf_profiles[ingredient]
    else:
        best_match = process.extractOne(ingredient, bnf_profiles.keys())
        if best_match and best_match[1] > threshold:
            return bnf_profiles[best_match[0]]
        else:
            raise ToolError(f"Could not find BNF profile slug match for ingredient: {ingredient}")


def ingredients_to_bnf_profiles(ingredients: List[str], bnf_profiles: dict, threshold: int = DEFAULT_THRESHOLD):
    """Resolve multiple ingredients to a single BNF profile slug if needed."""
    slug_components = []
    for i in ingredients:
        if i in bnf_profiles:
            slug_components.append(bnf_profiles[i])
        else:
            best_match = process.extractOne(i, bnf_profiles.keys())
            if best_match and best_match[1] > threshold:
                slug_components.append(bnf_profiles[best_match[0]])
            else:
                # If no match, just append the string as-is
                slug_components.append(i)

    # We often see BNF slugs use " with " to combine multi-ingredient drugs
    combined_search = " with ".join(slug_components)
    best_match = process.extractOne(combined_search, bnf_profiles.keys())
    if best_match:
        return bnf_profiles[best_match[0]]
    else:
        raise ToolError(f"Could not find combined BNF profile slug for: {combined_search}")


def resolve_drug_profile(drug_name: str, synonyms: dict, bnf_profiles: dict, threshold: int = DEFAULT_THRESHOLD):
    """Resolve a drug name to a BNF profile slug using direct or fuzzy matching and synonyms."""
    drug_name = drug_name.lower().strip()

    # Attempt direct match
    if drug_name in bnf_profiles:
        return bnf_profiles[drug_name]

    # Attempt synonyms -> ingredients -> slug
    drug_ingredients = map_ingredients(drug_name, synonyms, threshold)
    if isinstance(drug_ingredients, str):
        # Single fallback
        return ingredient_to_bnf_profile(drug_ingredients, bnf_profiles, threshold)
    elif isinstance(drug_ingredients, list):
        if len(drug_ingredients) == 1:
            return ingredient_to_bnf_profile(drug_ingredients[0], bnf_profiles, threshold)
        else:
            return ingredients_to_bnf_profiles(drug_ingredients, bnf_profiles, threshold)

    # If all else fails:
    raise ToolError(f"Could not find a BNF profile slug match for {drug_name}")


def ingredient_to_bnf_interactions(ingredient: str, bnf_interactions: dict, threshold: int = DEFAULT_THRESHOLD):
    """Resolve a single ingredient to a BNF interaction slug."""
    ingredient = ingredient.lower().strip()

    if ingredient in bnf_interactions:
        return bnf_interactions[ingredient]
    else:
        best_match = process.extractOne(ingredient, bnf_interactions.keys())
        if best_match and best_match[1] > threshold:
            return bnf_interactions[best_match[0]]
        else:
            raise ToolError(f"Could not find a BNF interaction slug match for {ingredient}")


def ingredients_to_bnf_interactions(ingredients: list, bnf_interactions: dict, threshold: int = DEFAULT_THRESHOLD):
    """Resolve multiple ingredients to BNF interaction slugs."""
    slugs = []
    for i in ingredients:
        try:
            s = ingredient_to_bnf_interactions(i, bnf_interactions, threshold)
            slugs.append(s)
        except ToolError:
            # If we cannot find an interaction slug for a single ingredient, skip
            continue
    return slugs


def resolve_drug_interactions(
    drug_name: str, synonyms: dict, bnf_interactions: dict, threshold: int = DEFAULT_THRESHOLD
) -> List[str]:
    """Resolve a drug name to a list of BNF interaction slugs."""
    drug_name = drug_name.lower().strip()

    # First try a direct match
    if drug_name in bnf_interactions:
        return [bnf_interactions[drug_name]]

    # If not, map drug name to ingredients, then find slugs
    drug_ingredients = map_ingredients(drug_name, synonyms, threshold)
    if isinstance(drug_ingredients, str):
        drug_ingredients = drug_ingredients.split(", ")

    all_slugs = []
    for ingredient in drug_ingredients:
        try:
            slug = ingredient_to_bnf_interactions(ingredient, bnf_interactions, threshold)
            if isinstance(slug, list):
                all_slugs.extend(slug)
            else:
                all_slugs.append(slug)
        except ToolError:
            pass

    return list(set(all_slugs))  # deduplicate if we want


def format_interactions(profile: dict) -> dict:
    """Format the raw JSON structure into a Python dict for each interactant."""
    interactions = {}
    if "result" not in profile or "data" not in profile["result"]:
        return interactions

    data = profile["result"]["data"]
    if "bnfInteractant" not in data or "interactions" not in data["bnfInteractant"]:
        return interactions

    for interaction in data["bnfInteractant"]["interactions"]:
        target_drug = interaction["interactant"]["title"]
        message = interaction["messages"][0]
        interactions[target_drug] = {
            "severity": message["severity"],
            "additiveEffect": message["additiveEffect"],
            "evidence": message["evidence"],
            "description": message["message"],
        }

    return interactions



@tool
def bnf_drug_profiles_tool() -> Tool:

    async def execute(drug_name: str) -> str:
        """
        Return the BNF drug profile for a given drug name.
        
        Args:
            drug_name (str): The name of the drug to look up (brand name or chemical name).

        Returns:
            DrugProfile: A pydantic model of the drug profile (which has a .prompt() method).
        """
        synonyms = pd.read_csv(BRAND_DRUG_LOC, index_col=0, sep="\t")["bnf_name"].to_dict()
        bnf_profiles = pd.read_csv(DRUG_PROFILE_LOC, index_col=0, sep="\t")["slug"].to_dict()

        # Resolve slug
        slug = resolve_drug_profile(drug_name, synonyms, bnf_profiles)

        # Load JSON data
        try:
            with open(DRUG_SPECIFIC_LOC.format(drug_name=slug), "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError as e:
            raise ToolError(f"No local JSON file found for slug '{slug}'") from e

        # Convert to pydantic model
        try:
            raw_profile = data["result"]["data"]["bnfDrug"]
            profile = DrugProfile.model_validate(raw_profile)
        except Exception as e:
            raise ToolError(f"Could not parse BNF drug profile JSON for slug '{slug}'") from e

        return profile.prompt

    return execute


@tool
def bnf_drug_interactions_tool() -> Tool:

    async def execute(drug_list: List[str]) -> str:
        """
        Look up BNF drug interactions among the specified list of drugs.

        Args:
            drug_list:  List of drug names, e.g. ["aspirin", "warfarin", "paracetamol"].

        Returns:
            InteractionList: A pydantic model containing interactions, with a .prompt() method.
        """
        synonyms = pd.read_csv(BRAND_DRUG_LOC, index_col=0, sep="\t")["bnf_name"].to_dict()
        bnf_interactions = pd.read_csv(
            DRUG_INTERACTION_PROFILE_LOC, index_col=0, sep="\t"
        )["slug"].to_dict()

        # For each drug, find its relevant BNF interaction slugs
        slug_map = {}
        for drug in drug_list:
            slugs = resolve_drug_interactions(drug, synonyms, bnf_interactions)
            slug_map[drug] = slugs

        # We'll gather all interactions in an InteractionList
        all_interactions = []

        # For each slug, open the JSON and parse interactions
        for drug_name, slugs in slug_map.items():
            for slug in slugs:
                try:
                    with open(
                        DRUG_INTERACTION_SPECIFIC_LOC.format(drug_name=slug),
                        "r",
                        encoding="utf-8",
                    ) as f:
                        profile = json.load(f)
                except FileNotFoundError:
                    logging.debug(f"File not found for slug={slug}. Skipping.")
                    continue

                formatted = format_interactions(profile)
                # `formatted` is a dict:  {"warfarin": { "severity":..., ... }, ... }
                for target_drug, details in formatted.items():
                    # If the target drug is in the user-specified list, let's record the interaction.
                    if target_drug.lower() in [d.lower() for d in drug_list]:
                        # Build the pydantic Interaction object
                        inter_obj = Interaction(
                            root_drug=drug_name,
                            drug_name=target_drug,
                            severity=details.get("severity"),
                            additiveEffect=details.get("additiveEffect"),
                            evidence=details.get("evidence"),
                            description=details.get("description"),
                            url=None,  # You could attach a BNF URL if you like
                        )
                        all_interactions.append(inter_obj)


        interaction_list = InteractionList(interactions=all_interactions)
        return interaction_list.prompt

    return execute