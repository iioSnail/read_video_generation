import hashlib
import os


def md5(text) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def remove_file(file):
    if os.path.exists(file):
        os.remove(file)