import hashlib
import os

from PIL import Image


def md5(text) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def remove_file(file):
    if os.path.exists(file):
        os.remove(file)


def resize_image(image_path: str, width: int, height: int, output_path: str):
    with Image.open(image_path) as img:
        resized_img = img.resize((width, height))

        # Convert RGBA to RGB if necessary
        if resized_img.mode == "RGBA":
            resized_img = resized_img.convert("RGB")

        resized_img.save(output_path, format="JPEG")  # Explicitly set format


def exec_cmd(cmd, output_file=None, error_msg=None):
    os.system(cmd)
    if output_file is None:
        return

    if error_msg is None:
        error_msg = f"Fail to generate file: {str(output_file)}"
    assert os.path.exists(output_file), error_msg
