import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import cv2
from PIL import Image

_ffmpeg_executable: str = None

def set_ffmpeg(ffmpeg_executable):
    global _ffmpeg_executable
    _ffmpeg_executable = ffmpeg_executable

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

    if str(file).endswith("wav"):
        return is_wav_valid(file)

    if str(file).endswith("jpg"):
        return is_jpg_valid(file)

    return True

def makedirs(filepath):
    parent_dir = os.path.dirname(filepath)
    os.makedirs(parent_dir, exist_ok=True)

def move_file(src, dst):
    shutil.copy2(src, dst)
    os.remove(src)

def copy_file(src, dst):
    shutil.copy2(src, dst)


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

def is_wav_valid(file_path):
    try:
        with open(file_path, 'rb') as f:
            # Check for RIFF header and WAVE format
            header = f.read(12)
            if header[:4] == b'RIFF' and header[8:12] == b'WAVE':
                return True
        return False
    except Exception as e:
        print(f"Error checking WAV: {e}")
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


def get_mp3_duration(file_path):
    cmd = [
        'ffprobe',
        '-i', file_path,
        '-show_entries', 'format=duration',
        '-v', 'quiet',
        '-of', 'csv=p=0'
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return float(result.stdout)


def get_wav_duration(file_path):
    cmd = [
        'ffprobe',
        '-i', file_path,
        '-show_entries', 'format=duration',
        '-v', 'quiet',
        '-of', 'csv=p=0'
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return float(result.stdout)


def get_mp4_duration(filepath):
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'json',
        filepath
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    metadata = json.loads(result.stdout)
    return float(metadata['format']['duration'])


def get_duration(filepath):
    filepath = str(filepath)

    if filepath.endswith(".mp3"):
        return get_mp3_duration(filepath)

    if filepath.endswith(".wav"):
        return get_wav_duration(filepath)

    if filepath.endswith(".mp4"):
        return get_mp4_duration(filepath)

    raise ValueError("Unsupported file format.")


def convert_mp3_to_wav(mp3_file: str, output_file: str):
    # Convert mp3 to wav
    convert_cmd = f'ffmpeg -i {mp3_file} -acodec pcm_s16le -ar 48000 {output_file}'
    exec_cmd(convert_cmd, output_file, "Fail to convert mp3 to wav.", timeout=10)


def convert_wav_to_wav(wav_file: str, output_file: str):
    # Convert wav to wav. The main goal is to make the wav's sample rate 48000
    convert_cmd = f'ffmpeg -i {wav_file} -acodec pcm_s16le -ar 48000 {output_file}'
    exec_cmd(convert_cmd, output_file, "Fail to convert wav to wav.", timeout=10)


def exec_cmd(cmd: str, output_file=None, error_msg=None, stdout=False, timeout=None):
    if _ffmpeg_executable is not None and cmd.startswith("ffmpeg"):
        cmd = _ffmpeg_executable + cmd[6:]

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
