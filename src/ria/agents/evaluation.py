import base64
import json
from dotenv import load_dotenv
from ria.prompts import load_prompt
from ria.utils import ModelingContext
import os
from typing import Annotated
from enum import Enum

# import from pydantic ai
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
import logfire

# import from pydantic
from pydantic import BaseModel, Field, ValidationError, AfterValidator

load_dotenv(override=True)

#MODEL_NAME_DEFAULT = "gpt-4o"
MODEL_NAME_DEFAULT = "gpt-5"
INPUT_IMAGE_COUNT = 5

def get_simple_schema(pydantic_model):
    schema = {k: v for k, v in pydantic_model.schema().items()}
    keys_to_remove = ["title", "additionalProperties", "type", "default"]
    reduced_schema = remove_dict_key_recursive(schema, keys_to_remove=keys_to_remove)
    schema_str = json.dumps(reduced_schema)
    return schema_str

def remove_dict_key_recursive(d, keys_to_remove=[]):
    if isinstance(d, dict):
        for key in keys_to_remove:
            d.pop(key, None)
        for key in list(d.keys()):
            remove_dict_key_recursive(d[key], keys_to_remove=keys_to_remove)
    elif isinstance(d, list):
        for item in d:
            remove_dict_key_recursive(item, keys_to_remove=keys_to_remove)

def check_scores(scores: list[int] | None):
    if scores:
        if len(scores) != INPUT_IMAGE_COUNT:
            raise ValidationError(f"Scores must be a list of {INPUT_IMAGE_COUNT} integers.")
        for v in scores:
            if v < 1 or v > 5:
                raise ValueError("Score must be between 1 and 5")
    return scores

# Scores = Annotated[list[int], AfterValidator(check_scores)]

class ImprovementTarget(str, Enum):
    DESIGN_DRIVER = "design_driver"
    DESIGN_TASK = "design_task"
    DESIGN_MODELING = "design_modeling"

class ConceptStrength(BaseModel):
    scores: int | None = Field(
        default=None,
        description="What's the overall strength and quality of the design concept, according to the guidelines in the system prompt? Ranging from 1 to 5. Low score=1: The design concept is bland, not evocative and does not represent the chosen material categories. Also, you cannot tell if the strategy was continuity or disruption. High score=5: The design concept is strong, formally and spatially evocative and is clearly specific to the chosen material and material categories. It also shows clearly the continuity or disruption strategy. BE STRICT WITH THE SCORES, THE GOAL IS TO IDENTIFY WEAKNESSES AND IMPROVE THEM.",
    )
    explanation: str | None = Field(
        default=None,
        description="Explain your reasoning for the scores given above. Provide specific observations (referencing the rendered image if necessary) that support your evaluation of the design concept strength.",
    )

class MaterialCoherence(BaseModel):
    scores: int | None = Field(
        default=None,
        description="Are the words chosen for the material categories semantically coherent and lexically diverse? How well do they represent the material's specific processes and evoke a material strategy? Ranging from 1 to 5. Low score=1: The results are unaligned, repetitive and evoke very bland or generic material strategies. High score=5: The alignment is excellent semantically, lexically and architecturally. The words are varied and evoke specific material strategies that uniquely inform the design concept. BE STRICT WITH THE SCORES, THE GOAL IS TO IDENTIFY WEAKNESSES AND IMPROVE THEM.",
    )
    explanation: str | None = Field(
        default=None,
        description="Explain your reasoning for the scores given above. Provide specific observations that support your evaluation of the material chart coherence.",
    )

class DesignTaskQuality(BaseModel):
    scores: int | None = Field(
        default=None,
        description="What's the overall quality of the design task, according to the guidelines in the system prompt? Can the step-by-step instructions be perceived in the way the .py function is written? Ranging from 1 to 5. Low score=1: The design task is bland, ambiguous and lacks specificity to become a clear step-by-step instruction on how to model the facade. High score=5: The design task expands the design concept and material categories with relevant dimensions, formal and spatial implications, facade system and building components, clearly translating them into specific and concise modeling steps. BE STRICT WITH THE SCORES, THE GOAL IS TO IDENTIFY WEAKNESSES AND IMPROVE THEM.",
    )
    explanation: str | None = Field(
        default=None,
        description="Explain your reasoning for the scores given above. Provide specific observations (referencing the .py function if necessary) that support your evaluation of the design task quality.",
    )
    
class FacadePotential(BaseModel):
    scores: int | None = Field(
        default=None,
        description="Does the image represent a potential facade? How well do the image and .py function align with the design task, material categories and design concept? Ranging from 1 to 5. Low score=1: The .py function and rendered image could be any geometry and do not represent at all the concept, material or categories in the design task. High score=5: By observing the image, one can easily identify a facade that follows the design concept, material categories, proportions, implications, components, operations and modelling steps suggested in the design task. BE STRICT WITH THE SCORES, THE GOAL IS TO IDENTIFY WEAKNESSES AND IMPROVE THEM.",
    )
    explanation: str | None = Field(
        default=None,
        description="Explain your reasoning for the scores given above. Provide specific observations from the image and/or the .py function that support your evaluation of the facade potential and alignment with the task, material and concept.",
    )

class ImprovementProposal(BaseModel):
    reflection: str | None = Field(
        default=None,
        description="Your task is to reflect on the results of the previous categories and assess what DOES work correctly now, and what NEEDS TO BE IMPROVED. State this reflection in a brief 1-3 sentences per category (design concept/material chart/design task/3DModel)",
    )
    improvement_target: ImprovementTarget | None = Field(
        default=None,
        description="Based on your reflection, which of the following 3 aspects would you prioritize for improvement? Choose only one: design_driver, design_task, design_modeling.",
    )
    improvement_proposal: str | None = Field(
        default=None,
        description="What changes would you suggest to the selected improvement_target to make the design more alligned with the intent, task and materiality? State your improvement proposal briefly with concise language and 3 specific bulletpoints or actions to take.",
    )

class EvaluationAgent:
    def __init__(self, model_name=MODEL_NAME_DEFAULT, logfire_debug=True):
        # Initialize logfire for logging
        if logfire_debug:
            logfire.configure(token=os.getenv("LOGFIRE_TOKEN"))
            logfire.instrument_openai()
            
        # Initialize the OpenAI model with the specified model name
        model = OpenAIChatModel(
            model_name=model_name,
            provider=OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"))
            )

        # initialize the agent with the model and specify the output type
        self.eval_concept = Agent(
            model=model,
            instructions=load_prompt("evaluation_driver_system", ext="md"),
            output_type=ConceptStrength,  # The agent will return a string of code
        )
        self.eval_material = Agent(
            model=model,
            instructions=load_prompt("evaluation_material_system", ext="md"),
            output_type=MaterialCoherence,  # The agent will return a string of code
        )
        self.eval_task = Agent(
            model=model,
            instructions=load_prompt("evaluation_task_system", ext="md"),
            output_type=DesignTaskQuality,  # The agent will return a string of code
        )
        self.eval_modeling = Agent(
            model=model,
            instructions=load_prompt("evaluation_modeling_system", ext="md"),
            output_type=FacadePotential,  # The agent will return a string of code
        )
        self.eval_suggestion = Agent(
            model=model,
            instructions=load_prompt("evaluation_improvement_system", ext="md"),
            output_type=ImprovementProposal,  # The agent will return a string of code
        )

  
    def evaluate_design(self, modeling_context: ModelingContext) -> dict | None:
        # try:
            # Encode reference images
            ref_img_data = []
            with open(modeling_context.image_path, "rb") as image_file:
                image_data = image_file.read()
                ref_img_data.append(
                    BinaryContent(
                        data=image_data,
                        media_type="image/png"
                    )
                )
            
            # Encode render images
            render_data = []
            for file in modeling_context.render_images:
                with open(file, "rb") as image_file:
                    image_data = image_file.read()
                    render_data.append(
                        BinaryContent(
                            data=image_data,
                            media_type="image/png"
                        )
                    )

            concept_score = self.eval_concept.run_sync(
                user_prompt=[
                    "Evaluate the alignment of the images with the design concept, and the overall strength of the concept.",
                    *ref_img_data
                ]
            ).output

            material_score = self.eval_material.run_sync(
                user_prompt=[
                    f"Evaluate the coherence of the material strategies {modeling_context.material_driver} internally, with the given key traits {modeling_context.design_driver} and with the design strategy {modeling_context.design_strategy}. "
                ]
            ).output

            task_score = self.eval_task.run_sync(
                user_prompt=[
                    f"Evaluate the quality of the design task {modeling_context.design_task} with the given design concept {modeling_context.material_driver} and its translation to the {modeling_context.gh_pyhon_script}. "
                ]
            ).output

            modeling_score = self.eval_modeling.run_sync(
                user_prompt=[
                    f"Evaluate the alignment of the generated images and the gh python script that generates the model with the design task {modeling_context.design_task} , the given concept {modeling_context.material_driver} and the design strategy {modeling_context.design_strategy}. ",
                    f"code: {modeling_context.gh_pyhon_script}", 
                    *render_data,
                ]
            ).output

            # Extract scores as floats
            scores = [
                float(concept_score.scores) if concept_score.scores is not None else None,
                float(material_score.scores) if material_score.scores is not None else None,
                float(task_score.scores) if task_score.scores is not None else None,
                float(modeling_score.scores) if modeling_score.scores is not None else None,
            ]
            # Filter out None values
            valid_scores = [s for s in scores if s is not None]
            average_score = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else None

            improvement = self.eval_suggestion.run_sync(
                user_prompt=[
                    "Based on the previous evaluations and scores, choose the weakest segment in the pipeline OR the segment whose improvement would have the most significant impact, and provide a reflection and improvement proposal",
                    f"Design Concept Evaluation: {concept_score}",
                    f"Material Strategy Evaluation: {material_score}",
                    f"Design Task Evaluation: {task_score}",
                    f"Modeling Evaluation: {modeling_score}"
                ]
            ).output

            return dict(
                design_concept_strength=concept_score.model_dump(),
                material_strategy_coherence=material_score.model_dump(),
                design_task_quality=task_score.model_dump(),
                facade_potential=modeling_score.model_dump(),
                average_score=average_score,
                improvement_proposal=improvement.model_dump()
            )

        # except Exception as e:
        #     print(f"Error: {e}")
        #     return None

