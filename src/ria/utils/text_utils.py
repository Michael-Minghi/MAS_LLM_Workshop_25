import re
import os

def to_snake_case(sentence):
    # Remove punctuation using regex
    sentence = re.sub(r'[^\w\s]', '', sentence)
    # Replace spaces with underscores
    sentence = sentence.replace(" ", "_")
    # Convert to lowercase
    sentence = sentence.lower()
    return sentence

class RuntimeLog(object):
    def __init__(self, file_path: str):
        self.file_path = file_path
        # Create the log file if it doesn't exist
        with open(self.file_path, 'w') as f:
            f.write('')

    def log(self, message: str, state: bool):
        with open(self.file_path, 'a') as f:
            f.write(f"{state}|{message}\n")