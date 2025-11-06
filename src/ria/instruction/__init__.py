import importlib.resources as resources

from ria.utils import load_text


def load_prompt(prompt, ext="txt"):
    package_path = resources.resource_filename("ria", "")
    return load_text(f"{package_path}/prompts/{prompt}.{ext}")
