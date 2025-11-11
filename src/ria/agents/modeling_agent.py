import json
import os
from dotenv import load_dotenv

# ria imports
from ria.instructions import load_instruction
from ria.utils import render_objs, RenderStyle, clean_code_string, _prepare_code_for_gh, _send_code_to_grasshopper, save_script_to_file, get_obj_padding, log_progress, load_images, json_dump
load_dotenv(override=True)

import logfire

# import from pydantic ai
from pydantic_ai import Agent, RunContext, BinaryContent
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

MODEL_NAME_DEFAULT = "gpt-4o"

class ParametricModelingAgent:
    def __init__(
        self,
        model_name=MODEL_NAME_DEFAULT,
        logfire_debug=True,
    ):
        # Initialize logfire for logging
        if logfire_debug:
            logfire.configure(token=os.getenv("LOGFIRE_TOKEN"))
            logfire.instrument_openai()

        # Initialize the OpenAI model with the specified model name
        model = OpenAIResponsesModel(
            model_name=model_name,
            provider=OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"))
        )

        # Load the system prompt template for the agent
        sys_prompt_template = load_instruction("modeling_agent_system", ext="md")

        # initialize the agent with the model and specify the output type
        self.agent = Agent(
            model=model,
            instructions=sys_prompt_template,
            output_type=str,  # The agent will return a string of code
        )

        self.prompt_template = "Create a function for Grasshopper Python that can create geometries adhereing to the provided design task below. The function must take relevant parameters as input to parametrically create the 3D geometry. The function returns a list of 3D geometries only (breps, surfaces, or meshes). Include a docstring that describes the function's purpose, what it does, inputs, and outputs. Any needed imports must be done in the function body. Return ONLY THE CODE OF THE FUNCTION:\n\n{design_task}."

        # Error fixing chain
        self.error_prompt_template = "Please fix the error in the function below in response to the error message. Return ONLY THE CODE OF THE FIXED FUNCTION:\n\n{code}\n\nError Message:\n{error}"

        # define the summarizer chain
        mini_model = OpenAIResponsesModel(
            model_name="gpt-5-mini",
            provider=OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY")),
        )

        self.summary_agent = Agent(
            model=mini_model,
            output_type=str,  # The agent will return a string of code
        )

        @self.summary_agent.instructions
        def summary_instructions(ctx: RunContext[dict] = "") -> str:
            prompt = "Briefly explain in 100 words how the script below generates an architectural facade system in response to the design task provided. \n\nDesign task:\n{design_task}\n\nCode:\n{code}"
            return prompt.format(
                design_task=ctx.deps.get("design_task", ""), code=ctx.deps.get("code", "")
            )

    def _suggest_example_usage(self, code: str, previous_example_usages=None):
        # define the example usage chain
        mini_model = OpenAIResponsesModel(
            model_name="gpt-5-mini",
            provider=OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY")),
        )

        if previous_example_usages:
            previously_generated_string = (
                "Do not repeat the following example usages:\n\n"
            )
            previously_generated_string += "\n".join(previous_example_usages)
        else:
            previously_generated_string = ""

        prompt_template = "Suggest ONE example usage for the function below in given as 'geometry = function_name(parameter1, parameter2, etc.)'. Return ONLY THE CODE.\n\nFunction Code:\n\n{code}\n\n{previously_generated}".format(
            code=code, previously_generated=previously_generated_string
        )

        example_agent = Agent(model=mini_model, output_type=str)
        return example_agent.run_sync(user_prompt=prompt_template).output

    def generate_code(
        self,
        user_task: str,
        output_dir: str,
        reference_images: list[str] = [],
        number_of_attempts: int = 8,
        number_of_example_usages: int = 3,
    )-> None: 
        # Initial setup for the first attempt
        message = "this is the first step, no code yet"
        error_message = None
        generated_gh_code = None

        # read reference images
        images = load_images(reference_images)

        for attempt in range(number_of_attempts):
            if attempt == 0:
                print("Invoking chain for initial code generation.")
            else:
                print(
                    f"Retrying GH code generation (Attempt {attempt+1}/{number_of_attempts})."
                )

            # Generate GH code
            if error_message and generated_gh_code:
                result = self.agent.run_sync(
                    user_prompt=self.error_prompt_template.format(
                        code=generated_gh_code, error=error_message
                    )
                )
            else:
                result = self.agent.run_sync(
                    user_prompt=[
                        self.prompt_template.format(design_task=user_task), 
                        *images
                    ]
                )
            
            # Clean the generated code string
            generated_gh_code = clean_code_string(result.output)
            print(f"Generated GH code:\n{generated_gh_code}")

            # generate example usage
            example_usages = []
            for i in range(number_of_example_usages):
                example_usage = self._suggest_example_usage(
                    generated_gh_code, previous_example_usages=example_usages
                )
                example_usage = clean_code_string(example_usage)
                print(f"Example usage: {example_usage}")
                example_usages.append(example_usage)

            # Prepare and send the code to Grasshopper
            code_for_gh = _prepare_code_for_gh(generated_gh_code, example_usages)
            print(message)
            response = _send_code_to_grasshopper(code_for_gh)
            print(
                f"Response from GH (Attempt {attempt + 1}):\n=====\n{response}\n=====\n"
            )

            # parse the response
            data = json.loads(response)
            script_log = data["script_log"]

            # log progress
            log_progress(attempt=attempt, log=script_log, code=code_for_gh, output_dir=output_dir) 

            # Check if response indicates success
            if script_log.strip().endswith("success"):
                print("Success! Code executed successfully.")
                
                obj_file_paths = data["obj_file_paths"]
                obj_output_paths = []

                # copy the obj file to the output directory
                for i, obj_file_path in enumerate(obj_file_paths):
                    padded_index = get_obj_padding(output_dir)

                    obj_file_output_path = os.path.join(
                        output_dir, f"{padded_index}_3d_model.obj"
                    )

                    obj_output_paths.append(obj_file_output_path)

                    if os.name == "posix":
                        os.system(f"mv {obj_file_path} {obj_file_output_path}")
                    else:
                        os.system(f"move {obj_file_path} {obj_file_output_path}")
                    print(
                        f"Obj file {i+1}/{len(obj_file_paths)} saved as {obj_file_output_path}"
                    )
                
                # Render the generated geometries
                render_objs(
                    paths=obj_output_paths,
                    render_style=RenderStyle.GHOSTED,
                )

                # Generate code summary
                code_summary = self.summary_agent.run_sync(
                    user_prompt="",
                    deps={
                        "design_task": user_task,
                        "code": code_for_gh,
                    },
                ).output

                # Save the successful script
                save_script_to_file(
                    output_dir,
                    code_for_gh,
                    code_summary
                )

                # Save user task and reference images
                json_dump(
                    {'task': user_task, 'reference_images': reference_images},
                    os.path.join(output_dir, "design_driver.json"),
                )

                return # Exit the loop on success

            else:
                # Update the error message for the next attempt
                error_message = script_log
                attempt += 1

        # If all attempts fail, save the last generated code
        print("All attempts failed.")