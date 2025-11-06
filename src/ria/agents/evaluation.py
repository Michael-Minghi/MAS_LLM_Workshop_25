import base64
import json
from dotenv import load_dotenv
from ria.instructions import load_prompt
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

# 01 -- DEFINE THE LLM MODEL AND OTHER CONSTANTS.
#__________________________________________________________________________________________

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

# 02 -- STATE ONE CLASS PER EACH METRIC YOU WANT TO EVALUATE. HERE IS A SAMPLE:
#__________________________________________________________________________________________

class ImprovementTarget(str, Enum):
    DESIGN_CONCEPT = "design_concept"
    DESIGN_MODELING = "design_modeling"
    DESIGN_GEOMETRY = "design_geometry"

class ConceptStrength(BaseModel):
    scores: int | None = Field(
        default=None,
        description="What's the overall strength and quality of the design concept? Ranging from 1 to 5. Low score=1: The design concept is not evocative and does not provide clear instructions to model the geometry. High score=5: The design concept is strong, formally evocative and suggests specific modeling strategies.",
    )
    explanation: str | None = Field(
        default=None,
        description="Explain your reasoning for the scores given above, in 2-3 concise sentences. Provide specific observations that support your evaluation.",
    )
class ModelingStrategy(BaseModel):
    scores: int | None = Field(
        default=None,
        description="How clear is the relationship between the .py function used to model the geometry, the design concept and the object rendered in the image? Ranging from 1 to 5. Low score=1: The .py function steps are not easily relatable with the attributes suggested in the design concept nor with the generated object. High score=5: The modeling steps in the .py function clearly reflect the attributes of the design concept and allow a successful modeling of the object.",
    )
    explanation: str | None = Field(
        default=None,
        description="Explain your reasoning for the scores given above, in 2-3 concise sentences. Provide specific observations that support your evaluation.",
    )
class GeometricAlignment(BaseModel):
    scores: int | None = Field(
        default=None,
        description="How well does the rendered geometry represent the attributes of the design concept? Ranging from 1 to 5. Low score=1: The rendered image could be any geometry and does not align at all with the design concept. High score=5: By observing the image, one can easily identify the key formal, spatial and geometrical attributes expressed in the design concept",
    )
    explanation: str | None = Field(
        default=None,
        description="Explain your reasoning for the scores given above, in 2-3 concise sentences. Provide specific observations that support your evaluation.",
    )

# 03 -- OPTIONAL. DEFINE A CLASS TO SUGGEST IMPROVEMENTS BASED ON THE EVALUATIONS.
#__________________________________________________________________________________________
class ImprovementProposal(BaseModel):
    improvement_target: ImprovementTarget | None = Field(
        default=None,
        description="Based on your evaluations, which of the following 3 aspects would you prioritize for improvement? Choose only one: design concept, modeling function or overall geometry.",
    )
    improvement_proposal: str | None = Field(
        default=None,
        description="State a brief improvement proposal for the selected target, with concise language and 3 specific bulletpoints or actions to take.",
    )

# 04 -- BUILD THE EVALUATION AGENT.
#__________________________________________________________________________________________
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
            instructions=load_prompt("evaluation_metrics_system", ext="md"),
            output_type=ConceptStrength,  # The agent will return a string of code
        )
        self.eval_modeling = Agent(
            model=model,
            instructions=load_prompt("evaluation_metrics_system", ext="md"),
            output_type=ModelingStrategy,  # The agent will return a string of code
        )
        self.eval_geometry = Agent(
            model=model,
            instructions=load_prompt("evaluation_metrics_system", ext="md"),
            output_type=GeometricAlignment,  # The agent will return a string of code
        )
        self.eval_suggestion = Agent(
            model=model,
            instructions=load_prompt("evaluation_improvement_system", ext="md"),
            output_type=ImprovementProposal,  # The agent will return a string of code
        )

# 05 -- DEFINE HOW TO RUN THE EVALUATIONS AND WHAT DATA TO LOOK AT IN EACH STEP.  
#__________________________________________________________________________________________

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
                    "Evaluate the overall strength of the concept.",
                    *ref_img_data
                ]
            ).output

            modeling_score = self.eval_modeling.run_sync(
                user_prompt=[
                    f"Evaluate the alignment of the gh python script {modeling_context.gh_pyhon_script} that generates the model with the given concept {modeling_context.design_concept} and the rendered object. ", 
                    *render_data,
                ]
            ).output
    
            geometric_score = self.eval_geometry.run_sync(
                user_prompt=[
                    f"Evaluate the alignment of the geometry rendered in the image with the given design concept {modeling_context.design_concept}.",
                    f"code: {modeling_context.gh_pyhon_script}", 
                    *render_data,
                ]
            ).output

            # Extract scores as floats
            scores = [
                float(concept_score.scores) if concept_score.scores is not None else None,
                float(modeling_score.scores) if modeling_score.scores is not None else None,
                float(geometric_score.scores) if geometric_score.scores is not None else None,
            ]
            # Filter out None values
            valid_scores = [s for s in scores if s is not None]
            average_score = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else None

            # Generate improvement proposal
            improvement = self.eval_suggestion.run_sync(
                user_prompt=[
                    "Based on the previous evaluations and scores, provide an improvement proposal focusing on the weakest aspect of these three:",
                    f"Design Concept: {concept_score}",
                    f"Modeling Strategy: {modeling_score}",
                    f"Geometric Alignment: {geometric_score}",
                ]
            ).output

            # Return all scores and improvement proposal as a dictionary
            return dict(
                concept_strength=concept_score.model_dump(),
                modeling_strategy=modeling_score.model_dump(),
                geometric_alignment=geometric_score.model_dump(),
                average_score=average_score,
                improvement_proposal=improvement.model_dump()
            )

        # except Exception as e:
        #     print(f"Error: {e}")
        #     return None

