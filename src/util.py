import hashlib
import os
import subprocess

import cv2
from PIL import Image


def md5(text) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def md5_file(file_path):
    """Calculate MD5 hash of a file."""
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        # Read and update hash in chunks of 4K
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def remove_file(file):
    if os.path.exists(file):
        os.remove(file)


def file_exists(file):
    if not os.path.exists(file):
        return False

    if os.path.getsize(file) <= 0:
        return False

    if str(file).endswith("mp4"):
        return is_mp4_valid(file)

    if str(file).endswith("mp3"):
        return is_mp3_valid(file)

    if str(file).endswith("jpg"):
        return is_jpg_valid(file)

    return True


def is_mp4_valid(file_path):
    try:
        cap = cv2.VideoCapture(str(file_path))
        if not cap.isOpened():
            return False
        # Check if we can read at least one frame
        ret, frame = cap.read()
        cap.release()
        return ret
    except Exception as e:
        print(f"Error: {e}")
        return False


def is_mp3_valid(file_path):
    try:
        with open(file_path, 'rb') as f:
            # Check for MP3 header (simplistic check)
            data = f.read(3)
            if data == b'ID3':
                return True
            # Check for MPEG frame header
            f.seek(0)
            header = f.read(4)
            if (header[0] == 0xFF) and ((header[1] & 0xE0) == 0xE0):
                return True
        return False
    except Exception as e:
        print(f"Error checking MP3: {e}")
        return False


def is_jpg_valid(file_path):
    try:
        with Image.open(str(file_path)) as img:
            img.verify()  # Verify the file contents
            return True
    except (IOError, SyntaxError) as e:
        print(f"Invalid image: {e}")
        return False


def resize_image(image_path: str, width: int, height: int, output_path: str):
    with Image.open(image_path) as img:
        resized_img = img.resize((width, height))

        # Convert RGBA to RGB if necessary
        if resized_img.mode == "RGBA":
            resized_img = resized_img.convert("RGB")

        resized_img.save(output_path, format="JPEG")  # Explicitly set format


def exec_cmd(cmd, output_file=None, error_msg=None, stdout=False, timeout=None):
    if stdout:
        subprocess.run(cmd, timeout=timeout)
    else:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)

    if output_file is None:
        return

    if error_msg is None:
        error_msg = f"Fail to generate file: {str(output_file)}."

    error_msg += f" Cmd: {cmd}"

    assert file_exists(output_file), error_msg
