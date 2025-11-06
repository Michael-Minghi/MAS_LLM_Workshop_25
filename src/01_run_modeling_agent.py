
import os, faulthandler
import random
from rich import print as rprint

from ria.agents.modeling_agent import get_design_folder_name
from ria.utils import load_metaphors_data, load_skill_libs

faulthandler.enable(all_threads=True)

RUN_SINGLE_DESIGN = True
FOLDER_EXPERIMENT = "experiment_01-test"
FOLDER_DESIGN_TASKS = "02_design_tasks"
FOLDER_PARAMETRIC_MODELS = "03_designs"
FOLDER_HISTORY_CONTEXT = "ctx02-task" # context folder for history and evaluation
MODEL = "gpt-4o"
# (use, do not use) the following coding frameworks:
CODING_FRAMEWORK = ("RhinoCommon", "rhinoscriptsyntax")
use_framework = "RhinoCommon"
do_not_use_framework = "rhinoscriptsyntax"
DESIGNS_PER_TASK = 1  # typically 5, but for testing we use 1
VALIDATE_PER_DESIGN = 3 # 2 for at least one validation, 1 for no validation

# CONTEXT flags (initial settings)
task_on = True  # include design task?
history_on = False  # include previous designs?
evaluation_on = False  # include evaluations of previous designs?
validation_on = True


# --- dependencies ----------------------------------------
if evaluation_on:  # evals → history → task
    history_on = True
    task_on = True
elif history_on:  # history → task
    task_on = True

# --- context prefix --------------------------------------
if evaluation_on:
    context_mode = "ctx04-eval"
elif history_on:
    context_mode = "ctx03-hist"
elif task_on:
    context_mode = "ctx02-task"
else:
    context_mode = "ctx01-drvr"

output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), FOLDER_EXPERIMENT)
FOLDER_DESIGN_TASKS = os.path.join(output_dir, FOLDER_DESIGN_TASKS)
FOLDER_PARAMETRIC_MODELS = os.path.join(output_dir, FOLDER_PARAMETRIC_MODELS)
FOLDER_OUTPUT = FOLDER_PARAMETRIC_MODELS


KEYS_TO_REMOVE = [
    # "implications_form",
    #"implications_space",
    #"design_components",
    "design_concept",
    "image_path",
]

def cleanup_interpretation_data(interpretation_data, keys_to_remove=None):
    if keys_to_remove is None:
        return interpretation_data
    for key in keys_to_remove:
        if key in interpretation_data:
            del interpretation_data[key]
    return interpretation_data


if __name__ == "__main__":
    rprint("Ignoring the following keys in the interpretations data:", KEYS_TO_REMOVE)

    # designer = ParametricModelingAgent(model_name=MODEL, use_framework=use_framework, do_not_use_framework=do_not_use_framework, logfire_debug=True)

    validator = ReflectionAgent(model_name=MODEL, logfire_debug=True)

    full_interpretations = load_metaphors_data(FOLDER_DESIGN_TASKS)
    interpretations_to_model = full_interpretations.copy()

    if history_on or evaluation_on:
        full_skill_libs = load_skill_libs(os.path.join(FOLDER_PARAMETRIC_MODELS, FOLDER_HISTORY_CONTEXT))
        skills_to_model = full_skill_libs.copy()
        rprint("Loaded skills to model:", len(skills_to_model))
        # rprint(skills_to_model.keys())

    if context_mode == "ctx01-drvr":
        _remove = []
        for key in interpretations_to_model.keys():
            if key.split("_")[1] != "01":
                _remove.append(key)
        for key in _remove:
            del interpretations_to_model[key]

    if RUN_SINGLE_DESIGN:
        # Get a random idea in the list and remove it
        random_key = random.choice(list(full_interpretations.keys()))
        random_key = "01_metal_3_t04.json" 
        print("selected design task:", random_key)
        interpretation_filename, interpretation_data = (
            random_key,
            full_interpretations.pop(random_key),
        )
        interpretations_to_model = {interpretation_filename: interpretation_data}

    total_count_generations = len(interpretations_to_model) * DESIGNS_PER_TASK
    counter = 0
    for (
        interpretation_filename,
        interpretation_data,
    ) in interpretations_to_model.items():

        # pass
        print("will create geometry for this design task:")
        interpretation_data = cleanup_interpretation_data(
            interpretation_data, keys_to_remove=KEYS_TO_REMOVE
        )
        rprint(interpretation_data)
        print("will inject the following parametric models")
        # rprint(skills_to_model[interpretation_filename])
        interpretations_keys_in_input = sorted(list(interpretation_data.keys()))
        interpretations_keys_in_input = "-".join(interpretations_keys_in_input)

        # tp = "metaphor" if metaphor_only else "all"

        actual_folder = os.path.join(FOLDER_OUTPUT, f"{context_mode}")

        for i in range(DESIGNS_PER_TASK):
            counter += 1
            print(
                f"Generating Parametric Model for {interpretation_filename} ({i+1}/{DESIGNS_PER_TASK})"
            )
            previous_generated_gh_skills = None
            if evaluation_on:
                previous_generated_gh_skills = skills_to_model[interpretation_filename]

            elif history_on:
                previous_generated_gh_skills = skills_to_model[interpretation_filename]
                for key in previous_generated_gh_skills:
                    if "evaluation" in previous_generated_gh_skills[key]:
                        del previous_generated_gh_skills[key]["evaluation"]

            # get output directory for the design
            output_dir = get_design_folder_name(actual_folder, interpretation_filename)

            validator.reflect_design(
                modeling_context=ModeilingContext(
                    interpretation_data=interpretation_data,
                    interpretation_filename=interpretation_filename,
                    skill_libs=previous_generated_gh_skills,
                    output_dir=output_dir,
                    number_of_attempts=5,
                    number_of_example_usages=5,
                )
            )

            print(
                f"Generated Parametric Model - progress: {counter}/{total_count_generations}"
            )
    print("Done.")
