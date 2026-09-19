import os

def prepare(files_dir):
    os.makedirs(files_dir, exist_ok=True)
