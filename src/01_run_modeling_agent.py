import os
from ria.agents.modeling_agent import ParametricModelingAgent
import pathlib

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
    label = 'mp_ass'

    output_dir = os.path.join(OUTPUT_FOLDER, f"{id}_{label}")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    images = []
    for img_file in os.listdir(IMAGE_FOLDER):
        suffix = pathlib.Path(img_file).suffix.lower()
        if suffix in ['.png', '.gif', '.webp', '.jpeg']:
            images.append(os.path.join(IMAGE_FOLDER, img_file))

    print (images)    
    # USER PROMPT: This is where you define the task for the modeling agent.
    task = "Generate a chicken garaage."
    
    # improvement = "Introduce a measured twist: rotate each 4-floor stack by 2\u20133\u00b0 around a slightly off-center core, accumulating 12\u201315\u00b0 at the crown; keep floor plates orthogonal to remain buildable.\n- Carve a bold void: subtract a vertical slot 20\u201330% of the plan that shifts into a diagonal sky-bridge cut between levels ~18\u201326; glaze and light the void to reveal depth and program.\n- Stage controlled offsets: create 2\u20133 setbacks/cantilevers at ~1/3 and ~2/3 height, offsetting 8\u201312% of tower width to form sky-terraces; articulate thicker edge beams to signal structure."

    # OPTIONAL: Add reference_images=IMAGE_FOLDER if any.
    modeling_agent = ParametricModelingAgent()

    modeling_agent.generate_code(user_task=task, output_dir=output_dir, reference_images=images)