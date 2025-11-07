import os
from ria.agents.modeling_agent import ParametricModelingAgent

OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")
IMAGE_FOLDER = os.path.join(OUTPUT_FOLDER, '00_reference_images')

def get_output_padding(dir):
    pad = 0
    for folder in os.listdir(dir):
        if os.path.isdir(os.path.join(dir, folder)):
            pad += 1
    return str(pad).zfill(2)

if __name__ == "__main__":
    id = get_output_padding(OUTPUT_FOLDER)
    label = 'demo'

    output_dir = os.path.join(OUTPUT_FOLDER, f"{id}_{label}")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    task = "Generate a cubicle structure with openings, based on the reference image provided"

    modeling_agent = ParametricModelingAgent()
    modeling_agent.generate_code(user_task=task, output_dir=output_dir, reference_images=IMAGE_FOLDER)