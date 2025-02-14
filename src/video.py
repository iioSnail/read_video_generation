import os
from pathlib import Path

import audioread
from tqdm import tqdm

from src.audio import AudioGenerator
from src.frame import FrameGenerator
from src.model import Video, Chunk
from src.util import md5, remove_file, resize_image, exec_cmd, file_exists


class VideoGenerator:

    def __init__(self, video: Video, args, cache_dir="./cache"):
        self.video = video
        self.args = args
        self.output_file = self.args.output
        self.cache_dir = Path(cache_dir) / "chunk"

        os.makedirs(self.cache_dir, exist_ok=True)

    def generate_one(self, chunk: Chunk):
        frame_generator = FrameGenerator(chunk.frame, self.video.width, self.video.height, cache_dir=self.args.cache_dir)
        image_file, image_filename = frame_generator.generate()

        audio_generator = AudioGenerator(chunk.audio, self.args, cache_dir=self.args.cache_dir)
        audio_file, audio_filename = audio_generator.generate()

        filename = md5(image_filename + audio_filename) + ".mp4"
        file = str(self.cache_dir / filename)

        if file_exists(file):
            return file, filename

        with audioread.audio_open(audio_file) as f:
            duration = round(f.duration + 0.01 + self.video.interval / 1000, 3)

        temp_mp4_file = str(self.cache_dir / (audio_filename + ".mp4"))
        remove_file(temp_mp4_file)
        cmd = f'ffmpeg -loop 1 -i {image_file} -c:v libx264 -t {duration} -vf "scale={self.video.width}:{self.video.height}" -pix_fmt yuv420p {temp_mp4_file}'
        exec_cmd(cmd, temp_mp4_file, "Fail to convert image to video.")

        remove_file(file)
        cmd = f"ffmpeg -i {temp_mp4_file} -i {audio_file} -c:v copy -c:a aac -b:a 192k {file}"
        exec_cmd(cmd, file, "Fail to merge audio and video.")

        return file, filename

    def generate(self):
        files = []
        filenames = []
        for chunk in tqdm(self.video.chunks, desc="Generating"):
            file, filename = self.generate_one(chunk)

            files.append(file)
            filenames.append(filename)

        print("Start merge every pieces...")
        # Merge videos.
        tmp_list_file = str(self.cache_dir / "tmp_file_list.txt")
        with open(tmp_list_file, "w") as f:
            for filename in filenames:
                f.write(f"file '{filename}'\n")

        file = self.cache_dir / "temp_output.mp4"
        remove_file(file)
        cmd = f'ffmpeg -f concat -safe 0 -i {tmp_list_file} -c copy {file}'
        exec_cmd(cmd, file, "Fail to merge videos.", stdout=True)

        print("Add background to the video...")
        # Add background
        bg_file = str(self.cache_dir / 'background.jpg')
        resize_image(self.video.background_image, self.video.width, self.video.height, bg_file)
        remove_file(self.output_file)
        cmd = f'ffmpeg -i {file} -i {bg_file} -filter_complex "[0:v]colorkey=0x000000:0.1:0.2[ckout];[1:v][ckout]overlay[out]" -map "[out]" -map 0:a {self.output_file}'
        exec_cmd(cmd, self.output_file, "Fail to add background to final video.", stdout=True)

        print("Success to generate video. The file is located at ", self.output_file)

        return self.output_file



