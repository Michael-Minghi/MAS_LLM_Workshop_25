import json
import os
import re
import socket
from datetime import datetime
from typing import List

import logfire
from dotenv import load_dotenv
from dataclasses import dataclass
from rich import print as rprint

from ria.instruction import load_prompt
from ria.utils import render_objs, RenderStyle
load_dotenv(override=True)

import logfire

# import from pydantic ai
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

MODEL_NAME_DEFAULT = "gpt-4o"

def clean_code_string(code_string):
    # Remove ```python or other language specifier and the closing ```
    return re.sub(r"```[a-zA-Z]*\n|```", "", code_string).strip()

def concat_calls_code(example_calls: List[str]):
    # Loop through the code_calls and dynamically add code for each call and path assignment
    content = ""
    content += "import ghpythonlib.treehelpers as th\n"
    content += "    from Grasshopper.Kernel.Data import GH_Path\n"
    content += "    geometry_states = []\n"
    for i, call in enumerate(example_calls):
        content += f"    # Generate sample geometry {i+1}/{len(example_calls)}\n"
        content += f"    {call}\n"
        content += f"    geometry = list(geometry) if not isinstance(geometry, list) else geometry\n"
        content += "    geometry_states.append(geometry)\n\n"
    content += "    # Convert the list of geometries to a Grasshopper DataTree\n"
    content += "    geometry_states = th.list_to_tree(geometry_states)\n"
    return content

def _prepare_code_for_gh(function_code: str, example_calls: List[str]):
    # Dynamically generate the code that defines 'function_calls' as a list
    # function_calls_list = ",\n".join(f'"{call}"' for call in code.code_calls)
    # code_function = code.code_function.replace('"""', '\\"""')
    calls_code = concat_calls_code(example_calls)
    function_code = function_code.replace('"""', '\\"""')
    code_to_send = "#! python 3\n"
    code_to_send += f'function_code = """{function_code}"""\n'
    code_to_send += f"""
try:
    exec(function_code)
    {calls_code}
    print("success")
except Exception as e:
    print("Error: ", e)
"""
    return code_to_send


def _send_code_to_grasshopper(message):
    # Define the server address and port
    server_address = ("localhost", 12346)
    # Define the server address and port
    receive_server_address = ("localhost", 12347)

    # Create a UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # Send the message
        udp_socket.sendto(message.encode(), server_address)
        print(f"Sent: {message}")
        udp_socket.close()
        print("Message sent. Waiting for response...")
        # Enter a loop to listen for the response
        # Create a UDP socket
        new_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set the socket option to reuse the address
        new_udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind the socket to the server address
        new_udp_socket.bind(receive_server_address)
        while True:

            # Receive the response from the receiver
            data, addr = new_udp_socket.recvfrom(4096)

            # Print the received response
            print(f"Received response from {addr}.")
            return data.decode()

            # Break the loop after receiving the first response
            # break
    finally:
        udp_socket.close()
        new_udp_socket.close()
        print("Closed socket")


def save_script_to_file(path, gh_code, idea_file, summary, loop):
    # Extract the function name from the 'code_func' by splitting at 'def' and '('
    # func_name = gh_code.split("def ")[1].split("(")[0]

    # # Create the .py file named after the function
    # filename = f"{func_name}.py"
    filename = f"{str(loop).zfill(2)}_gh_function.py"
    filename = os.path.join(path, filename)

    # content = concat_code(gh_code, summary, idea_file)
    summary_string = f'""" Summary:\n{summary}"""\n\n'
    with open(filename, "w") as f:
        f.write(f"# Created for {idea_file}\n\n")
        f.write(summary_string)
        f.write(gh_code)
        print(f"Python script saved as {filename}")
    return gh_code


def remove_dict_key_recursive(d, keys_to_remove=[]):
    # print(type(d))
    if isinstance(d, dict):

        for key in keys_to_remove:
            d.pop(key, None)
        # d.pop('title', None)  # Remove the 'title' key if it exists
        for key in list(d.keys()):
            remove_dict_key_recursive(
                d[key], keys_to_remove=keys_to_remove
            )  # Recursively call to remove from sub-dictionaries
    elif isinstance(d, list):
        for item in d:
            remove_dict_key_recursive(
                item, keys_to_remove=keys_to_remove
            )  # Recursively call to remove from each item in the list


def get_simple_schema(pydantic_model, as_dict=False):
    # Copy schema to avoid altering original Pydantic schema.
    schema = {k: v for k, v in pydantic_model.schema().items()}
    # rprint(schema)
    # Remove extraneous fields.
    keys_to_remove = ["title", "additionalProperties", "type", "default"]
    remove_dict_key_recursive(schema, keys_to_remove=keys_to_remove)
    # rprint(schema)
    # Ensure json in context is well-formed with double quotes.
    if as_dict:
        return schema
    schema_str = json.dumps(schema)
    return schema_str


def get_design_folder_name(orig_output_dir, interpretation_filename):
    # strip the idea file from .json
    idea_name = interpretation_filename.split(".")[0]
    output_dir = os.path.join(orig_output_dir, idea_name)

    # Get the next design ID based on the existing folders in the output directory
    existing_folders = (
        [
            name
            for name in os.listdir(output_dir)
            if os.path.isdir(os.path.join(output_dir, name))
        ]
        if os.path.exists(output_dir)
        else []
    )
    existing_ids = [
        int(folder.split("_")[2])
        for folder in existing_folders
        if len(folder.split("_")) > 2 and folder.split("_")[2].isdigit()
    ]
    next_id = max(existing_ids, default=0) + 1

    dir_name = os.path.basename(output_dir).split("_")
    dir_name.insert(2, f"{next_id:04n}")
    dir_name = "_".join(dir_name)

    output_dir = os.path.join(output_dir, dir_name)
    return output_dir

def get_obj_padding(dir):
    pad = 0
    for file in os.listdir(dir):
        if file.endswith(".obj"):
            pad += 1
    return str(pad).zfill(2)

class ParametricModelingAgent:
    def __init__(
        self,
        model_name=MODEL_NAME_DEFAULT,
        # output_dir="",
        use_framework="RhinoCommon",
        do_not_use_framework="rhinoscriptsyntax",
        logfire_debug=True,
    ):
        # Initialize logfire for logging
        if logfire_debug:
            logfire.configure(token=os.getenv("LOGFIRE_TOKEN"))
            logfire.instrument_openai()
        # Initialize the OpenAI model with the specified model name
        model = OpenAIChatModel(
            model_name=model_name,
            provider=OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"))
        )

        # Load the system prompt template for the agent
        sys_prompt_template = load_prompt("modeling_agent_system", ext="md")
        sys_prompt_template.format(
            use_framework=use_framework, do_not_use_framework=do_not_use_framework
        )

        # initialize the agent with the model and specify the output type
        self.agent = Agent(
            model=model,
            instructions=sys_prompt_template,
            output_type=str,  # The agent will return a string of code
        )

        self.prompt_template = "Create a function for Grasshopper Python that can create an architectural Facade System adhereing to the provided design task below. The function must take relevant parameters as input to parametrically create the geometry of the Facade System along with any needed helper geometry objects. The function returns a list of 3D geometries only (breps, surfaces, or meshes). Include a docstring that describes the function's purpose, what it does, inputs, and outputs. Any needed imports must be done in the function body. Return ONLY THE CODE OF THE FUNCTION:\n\n{design_task}."

        self.skill_history_prompt = "Below are previously generated functions for the same metaphor. Try to apply a different approach this time while adhereing to the provided material strategy and design task.\n\nPreviously generated functions:\n\n"

        # Error fixing chain
        self.error_prompt_template = "Please fix the error in the function below in response to the error message. Return ONLY THE CODE OF THE FIXED FUNCTION:\n\n{code}\n\nError Message:\n{error}"

        # Validation chain
        self.validation_prompt_template = "Please adjust the function below based on the following suggestion. Return ONLY THE CODE OF THE FIXED FUNCTION:\n\ncode:\n\n{code}\n\nSuggestion:\n{suggestion}"
        self.validation_gh_code = None

        # define the summarizer chain
        mini_model = OpenAIChatModel(
            model_name="gpt-4o-mini",
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
        mini_model = OpenAIChatModel(
            model_name="gpt-4o-mini",
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
        modeling_context,
        number_of_attempts=8,
        number_of_example_usages=3,
        suggestion=None,
        loop : int = 0
    )-> tuple[str, bool, list[str]| None]: 
        # Initial setup for the first attempt
        message = "this is the first step, no code yet"
        error_message = None
        generated_gh_code = None
        progress_log = []
        interpretation_data = modeling_context.design_task
        interpretation_filename = modeling_context.name
        output_dir = os.path.join(modeling_context.output_dir, modeling_context.name)

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
                if suggestion:
                    result = self.agent.run_sync(
                        user_prompt=self.validation_prompt_template.format(
                            code=self.validation_gh_code, suggestion=suggestion
                        )
                    )
                else:
                    result = self.agent.run_sync(
                        user_prompt=self.prompt_template.format(
                            design_task=interpretation_data
                        )
                    )

            generated_gh_code = result.output
            generated_gh_code = clean_code_string(generated_gh_code)
            print(f"Generated GH code:\n{generated_gh_code}")
            # all_messages.append(generated_gh_code.message)
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

            # save generated code for validation
            self.validation_gh_code = generated_gh_code

            # Check if response indicates success
            data = json.loads(response)
            script_log = data["script_log"]

            os.makedirs(output_dir, exist_ok=True)

            # Check if the progress log file exists, if do add to it
            if os.path.exists(os.path.join(output_dir, "progress_log.json")):
                with open(os.path.join(output_dir, "progress_log.json"), "r") as f:
                    progress_log = json.load(f)

            progress_log.append(
                {"run": loop, "attempt": attempt, "log": script_log, "code": code_for_gh}
            )

            with open(os.path.join(output_dir, "progress_log.json"), "w") as f:
                json.dump(progress_log, f, indent=2)

            if script_log.strip().endswith("success"):
                print("Success! Code executed successfully.")

                # copy the obj file to the output directory
                obj_file_paths = data["obj_file_paths"]
                output_paths = []
                for i, obj_file_path in enumerate(obj_file_paths):
                    padded_index = get_obj_padding(output_dir)

                    obj_file_output_path = os.path.join(
                        output_dir, f"{padded_index}_3d_model.obj"
                    )

                    print(obj_file_path)
                    if os.name == "posix":
                        os.system(f"mv {obj_file_path} {obj_file_output_path}")
                    else:
                        os.system(f"move {obj_file_path} {obj_file_output_path}")
                    print(
                        f"Obj file {i+1}/{len(obj_file_paths)} saved as {obj_file_output_path}"
                    )
                    output_paths.append(obj_file_output_path)

                code_summary = self.summary_agent.run_sync(
                    user_prompt="",
                    deps={
                        "design_task": interpretation_data,
                        "code": code_for_gh,
                    },
                ).output

                save_script_to_file(
                    output_dir,
                    code_for_gh,
                    interpretation_filename,
                    code_summary,
                    loop=loop
                )

                # save the suggestion summary
                mask = 'a' if os.path.exists(os.path.join(output_dir, "suggestion.md")) else 'w'
                if suggestion:
                    with open(os.path.join(output_dir, "suggestion.md"), mask) as f:
                        f.write("\n\n"+suggestion)

                # # save the idea file for reference
                # with open(
                #     os.path.join(output_dir, interpretation_filename), "w"
                # ) as f:
                #     f.write(json.dumps(interpretation_data))
                # # Return the generated code and success flag
                # print("Success! GH code generated and saved.")

                return generated_gh_code, True, output_paths

            # Update the error message for the next attempt
            error_message = script_log

        # If all attempts fail, save the last generated code
        print("All attempts failed.")
        # save_script_to_file(design_output_dir, code_for_gh, idea_file, '')

        return generated_gh_code, False, None