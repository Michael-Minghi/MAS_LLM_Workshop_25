import importlib.resources as resources

def load_instruction(prompt, ext="txt"):
    from ria.utils import load_text
    package_path = resources.files("ria")
    return load_text(f"{package_path}/instructions/{prompt}.{ext}")