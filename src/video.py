import os
from pathlib import Path

import audioread

from src.audio import AudioGenerator
from src.frame import FrameGenerator
from src.model import Video, Chunk
from src.util import md5, remove_file


class VideoGenerator:

    def __init__(self, video: Video, output_file, cache_dir="./cache/chunk/"):
        self.video = video
        self.output_file = output_file
        self.cache_dir = Path(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)

    def generate_one(self, chunk: Chunk):
        frame_generator = FrameGenerator(chunk.frame, self.video.width, self.video.height)
        image_file, image_filename = frame_generator.generate()

        audio_generator = AudioGenerator(chunk.audio)
        audio_file, audio_filename = audio_generator.generate()

        with audioread.audio_open(audio_file) as f:
            duration = round(f.duration + 0.01 + self.video.interval / 1000, 3)

        filename = md5(image_filename + audio_filename) + ".mp4"
        file = str(self.cache_dir / filename)

        if os.path.exists(file):
            return file, filename

        temp_mp4_file = str(self.cache_dir / (audio_filename + ".mp4"))
        remove_file(temp_mp4_file)
        cmd = f'ffmpeg -loop 1 -i {image_file} -c:v libx264 -t {duration} -vf "scale={self.video.width}:{self.video.height}" -pix_fmt yuv420p {temp_mp4_file}'
        os.system(cmd)

        assert os.path.exists(temp_mp4_file), "Fail to convert image to video."

        remove_file(file)
        cmd = f"ffmpeg -i {temp_mp4_file} -i {audio_file} -c:v copy -c:a aac -b:a 192k {file}"
        os.system(cmd)

        assert os.path.exists(file), "Fail to merge audio and video."

        return file, filename

    def generate(self):
        files = []
        filenames = []
        for chunk in self.video.chunks:
            file, filename = self.generate_one(chunk)

            files.append(file)
            filenames.append(filename)

        # Merge videos.
        tmp_list_file = str(self.cache_dir / "tmp_file_list.txt")
        with open(tmp_list_file, "w") as f:
            for filename in filenames:
                f.write(f"file '{filename}'\n")

        remove_file(self.output_file)
        cmd = f'ffmpeg -f concat -safe 0 -i {tmp_list_file} -c copy {self.output_file}'
        os.system(cmd)

        return self.output_file



