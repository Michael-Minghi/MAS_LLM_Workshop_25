from ria.agents import EvaluationAgent, EvaluationModel
from ria.utils import json_dump, json_load
import os
from PIL import Image
import json
import pandas as pd
from pprint import pprint

FOLDER_EXPERIMENT = "experiment_01-test"
FOLDER_PARAMETRIC_MODELS = "03_designs"

CROP_IMAGES = False
RESIZE_IMAGES = False
OVERRIDE_EVALUATION = True

data_folder = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    FOLDER_EXPERIMENT,
    FOLDER_PARAMETRIC_MODELS,
)
eval_folder = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), FOLDER_EXPERIMENT, "04_evaluation_crops"
)
resized_folder = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), FOLDER_EXPERIMENT, "05_resized_images"
)

def add_averages(df, score_columns):
    # score_columns = [key for key, value in EvaluationModel.model_fields.items() if int in get_args(value.annotation)]
    df[score_columns] = df[score_columns].apply(pd.to_numeric, errors='coerce')
    averages = df[score_columns].mean().round(2)
    average_row = {
        "image_path": "overall",
        **averages.to_dict(),
    }
    df = pd.concat([df, pd.DataFrame([average_row])], ignore_index=True)
    df["average"] = df[score_columns].mean(axis=1).map("{:.2f}".format)
    return df

def build_items_dict(data_folder):
    # Initialize an empty dictionary to store results
    folder_dict = {}

    # Walk through all subfolders in the data_folder
    for root, dirs, files in os.walk(data_folder):
        png_list = []
        json_files = []
        py_files = []

        # Find all .png, .json and .py files in the current subfolder
        for file in files:
            if file.endswith(".png"):
                png_list.append(os.path.join(root, file))
            elif file.endswith(".json") and file != "progress_log.json":
                json_files.append(os.path.join(root, file))
            elif file.endswith(".py"):
                py_files.append(os.path.join(root, file))
        
        # Get only the last json file of the gh python script if multiple are present
        if len(png_list) > 5:
            png_list.sort()
            png_list = png_list[-5:]

        # If we found any of these formats, we add them to the dictionary with the folder as the key
        if png_list:
            folder_dict[root] = {"images_list": png_list, "json_files": json_files, "py_files": py_files}

    # Sort the dictionary by key
    sorted_folder_dict = dict(sorted(folder_dict.items()))
    return sorted_folder_dict


# Example usage:
if __name__ == "__main__":
    agent = EvaluationAgent()

    sorted_folder_dict = build_items_dict(data_folder)

    # Convert dictionary items to a list to enable indexing
    sorted_folder_list = list(sorted_folder_dict.items())
    # Print or use the sorted_folder_dict as needed
    for folder, content in sorted_folder_list:
        # Check if evaluation.csv is present in the folder
        if "evaluation.csv" not in os.listdir(folder) or OVERRIDE_EVALUATION:
            print(f"Folder: {folder}")
            # print(f"Images List: {content['images_list']}")
            # print(f"JSON Files: {content['json_files']}")
            print("\n")
            if not content.get("json_files"):
                # Save a dummy file evaluations.csv with content "None"
                with open(os.path.join(folder, "evaluation.csv"), "w") as f:
                    f.write("None")
                continue
            metaphor_data = json_load(content["json_files"][0])
            print(f"Metaphor Data: {metaphor_data}")

            # Check if there is a Python model code
            python_model_code = None
            if content.get("py_files"):
                with open(content["py_files"][0], "r") as f:
                    python_model_code = f.read()

            evaluation_images = []
            # Create columns with an additional 'imagepath' in front
            columns = ["image_path"] + [key for key in EvaluationModel.model_json_schema()["properties"].keys() if key != "improvement"]
            evaluation_results = pd.DataFrame(columns=columns)

            for image_file in content["images_list"]:
                print(f"Image: {image_file}")
                # Open the image
                with Image.open(image_file) as img:
                    # Check if the image is placeholder, i.e. only contains pixels with RGB values between 55 and 68
                    pixels = list(img.getdata())
                    min_treshold = 55
                    max_treshold = 68
                    if all(
                        min_treshold <= pixel[0] <= max_treshold
                        and min_treshold <= pixel[1] <= max_treshold
                        and min_treshold <= pixel[2] <= max_treshold
                        for pixel in pixels
                    ):
                        # print(
                        #     f"Skipping image due to RGB range condition: {image_file}"
                        # )
                        # non_eval = EvaluationModel(
                        #     design_concept_alignment=None,
                        #     material_strategy_alignment=None,
                        #     design_task_alignment=None,
                        #     facadeness=None,
                        #     facade_system=None,
                        #     reflection=None,
                        #     improvement_proposal=None,
                        # )
                        # new_data = {
                        #     "image_path": image_file,
                        #     # "metaphor_file_path": content["json_files"][0],
                        #     **non_eval.model_dump(),
                        # }
                        # # Create a DataFrame for the new data
                        # new_row = pd.DataFrame([new_data])
                        # # Concatenate the new row to the existing DataFrame
                        # evaluation_results = pd.concat(
                        #     [evaluation_results, new_row], ignore_index=True
                        # )
                        continue

                    # If CROP_IMAGES is False, skip cropping
                    if CROP_IMAGES:
                        # Crop 384 pixels from left and right, 474 from top and 294 from bottom
                        width, height = img.size
                        left = 384
                        top = 474
                        right = 384 + 512
                        bottom = 474 + 512
                        cropped_img = img.crop((left, top, right, bottom))

                        # Create the new path by replacing data_folder with eval_folder
                        new_image_path = image_file.replace(data_folder, eval_folder)
                        # Ensure the directory exists
                        os.makedirs(os.path.dirname(new_image_path), exist_ok=True)

                        # Save the cropped image to the new path
                        cropped_img.save(new_image_path)
                        print(f"Cropped Image saved: {new_image_path}")
                    else:
                        # If CROP_IMAGES is False, use the original image path
                        new_image_path = image_file

                    evaluation_images.append(new_image_path)

            print("evaluating with agent")
            evaluation = agent.evaluate_design_metaphor(
                evaluation_images, metaphor_data, model_script=python_model_code
            )

            evaluation = evaluation.model_dump()
            pprint(evaluation)
            improvent = evaluation.pop("improvement")
            for i, img_path in enumerate(evaluation_images):
                new_data = {'image_path': img_path}
                for key in evaluation.keys():
                    if evaluation[key]:
                        new_data[key] = evaluation[key][i]
                    else:
                        new_data[key] = None
                new_row = pd.DataFrame([new_data])
                evaluation_results = pd.concat(
                    [evaluation_results, new_row], ignore_index=True
                )
            
            evaluation_results = add_averages(evaluation_results, score_columns=list(evaluation.keys()))
            evaluation_results.to_csv(
                os.path.join(folder, "evaluation.csv"), index=False
            )

            with open(os.path.join(folder, "improvement_proposals.json"), "w") as f:
                json.dump(improvent, f, indent=4)

                    # new_data = {
                    #     "image_path": image_file,
                    #     # "metaphor_file_path": content["json_files"][0],
                    #     **evaluation.model_dump(),
                    # }
                    # # Create a DataFrame for the new data
                    # new_row = pd.DataFrame([new_data])
                    # # Concatenate the new row to the existing DataFrame
                    # evaluation_results = pd.concat(
                    #     [evaluation_results, new_row], ignore_index=True
                    # )
                    # evaluation_images.append(new_image_path)
            # evaluation_results = add_averages(evaluation_results)
            # # add metaphor file path to the evaluation_results
            # evaluation_results["metaphor_file_path"] = content["json_files"][0]
            # evaluation_results.to_csv(
            #     os.path.join(folder, "evaluation.csv"), index=False
            # )
