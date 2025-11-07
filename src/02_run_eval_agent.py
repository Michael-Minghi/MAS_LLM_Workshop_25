import os
from ria.agents.evaluation import EvaluationAgent
import questionary

OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")

if __name__ == "__main__":
    # Prompt user for the path to the design folder
    outputs =  [d for d in os.listdir(OUTPUT_FOLDER) if os.path.isdir(os.path.join(OUTPUT_FOLDER, d))]

    if outputs:   
        design_path = questionary.select(
            "Select the design folder to evaluate:",
            choices=outputs
        ).ask()

        if os.path.exists(os.path.join(os.path.join(OUTPUT_FOLDER, design_path), 'evaluation_report.json')):
            overwrite = questionary.confirm(
                "An evaluation report already exists. Do you want to overwrite it?").ask()
            if not overwrite:
                print("Exiting without overwriting the evaluation report.")
                exit(0)

        eval_agent = EvaluationAgent()
        eval_agent.evaluate_design(os.path.join(OUTPUT_FOLDER, design_path))
    else:
        print("No design folders found in outputs directory.")