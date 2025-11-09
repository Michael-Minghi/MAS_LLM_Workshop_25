import base64
import json
from dotenv import load_dotenv
from ria.instructions import load_instruction
from ria.utils import load_images, json_load, json_dump, load_text
import os
from enum import Enum
import questionary

# import from pydantic ai
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
import logfire

# import from pydantic
from pydantic import BaseModel, Field, ValidationError

load_dotenv(override=True)

# 01 -- DEFINE THE LLM MODEL AND OTHER CONSTANTS.
#__________________________________________________________________________________________

MODEL_NAME_DEFAULT = "gpt-5"

# INPUT_IMAGE_COUNT = 5

# def check_scores(scores: list[int] | None):
#     if scores:
#         if len(scores) != INPUT_IMAGE_COUNT:
#             raise ValidationError(f"Scores must be a list of {INPUT_IMAGE_COUNT} integers.")
#         for v in scores:
#             if v < 1 or v > 5:
#                 raise ValueError("Score must be between 1 and 5")
#     return scores

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

        self.agent = Agent(model=model, deps_type=str)

        @self.agent.instructions
        def concept_instructions(ctx: RunContext[str]) -> str:
            prompt = load_instruction(ctx.deps, ext="md")
            return prompt

# 05 -- DEFINE HOW TO RUN THE EVALUATIONS AND WHAT DATA TO LOOK AT IN EACH STEP.  
#__________________________________________________________________________________________

    def evaluate_design(self, path: str) -> None:
        print (f"validating files integrity in {path}...")

        # load design driver
        file = os.path.join(path, "design_driver.json")
        if not os.path.exists(file):
            raise FileNotFoundError(f"design_driver.json not found")
        design_driver = json_load(file)

        # load user task
        design_concept = design_driver.get("task")

         # load reference images
        ref_img_data = load_images(design_driver.get("reference_images"))

        # load render images
        render_data = load_images([os.path.join(path, f) for f in os.listdir(path) if f.endswith(('.png', '.jpeg', '.gif', '.webp'))])

        # load generated script 
        file = os.path.join(path, "gh_function.py")
        if not os.path.exists(file):
            raise FileNotFoundError(f"gh_function.py not found")
        gh_pyhon_script = load_text(file)
        
        print ("files validated. running evaluation...")

        concept_score = self.agent.run_sync(
            user_prompt=[
                f"Evaluate the overall strength of the concept {design_concept}, using also the only if provided.",
                *ref_img_data
            ],
            deps='evaluation_metrics_system',
            output_type=ConceptStrength
        ).output

        modeling_score = self.agent.run_sync(
            user_prompt=[
                f"Evaluate the alignment of the gh python script {gh_pyhon_script} that generates the model with the given concept {design_concept} and the rendered object. ", 
                *render_data,
            ],
            deps='evaluation_metrics_system',
            output_type=ModelingStrategy
        ).output

        geometric_score = self.agent.run_sync(
            user_prompt=[
                f"Evaluate the alignment of the geometry rendered in the image with the given design concept {design_concept}.",
                f"code: {gh_pyhon_script}", 
                *render_data,
            ],
            deps='evaluation_metrics_system',
            output_type=GeometricAlignment
        ).output

        # Extract scores as floats
        scores = [
            float(concept_score.scores) if concept_score.scores else None,
            float(modeling_score.scores) if modeling_score.scores else None,
            float(geometric_score.scores) if geometric_score.scores else None,
        ]
        # Filter out None values
        valid_scores = [s for s in scores if s]
        average_score = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else None

        # Generate improvement proposal
        improvement = self.agent.run_sync(
            user_prompt=[
                "Based on the previous evaluations and scores, provide an improvement proposal focusing on the weakest aspect of these three:",
                f"Design Concept: {concept_score}",
                f"Modeling Strategy: {modeling_score}",
                f"Geometric Alignment: {geometric_score}",
            ],
            deps='evaluation_improvement_system',
            output_type=ImprovementProposal
        ).output

        # Return all scores and improvement proposal as a dictionary
        json_dump(
            dict(
                concept_strength=concept_score.model_dump(),
                modeling_strategy=modeling_score.model_dump(),
                geometric_alignment=geometric_score.model_dump(),
                average_score=average_score,
                improvement_proposal=improvement.model_dump()
            ),
            os.path.join(path, "evaluation_report.json")
        )

        print ("Evaluation completed. Report saved to evaluation_report.json")