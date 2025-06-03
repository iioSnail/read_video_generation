import os
import shutil
from pathlib import Path

import audioread
from tqdm import tqdm

from src.audio import AudioGenerator
from src.frame import FrameGenerator
from src.model import Video, Chunk, VideoClip
from src.util import md5, remove_file, resize_image, exec_cmd, file_exists, md5_file


class VideoGenerator:

    def __init__(self, video: Video, args, cache_dir="./cache"):
        self.video = video
        self.args = args
        self.output_file = self.args.output
        self.cache_dir = Path(cache_dir) / "chunk"

        os.makedirs(self.cache_dir, exist_ok=True)

    def generate_one(self, chunk: Chunk):
        if chunk.video_clip is not None:
            return self.generate_video_clip(chunk.video_clip)

        frame_generator = FrameGenerator(chunk.frame, self.video.width, self.video.height,
                                         cache_dir=self.args.cache_dir)
        image_file, image_filename = frame_generator.generate()

        audio_generator = AudioGenerator(chunk.audio, self.args, cache_dir=self.args.cache_dir)
        audio_file, audio_filename = audio_generator.generate()

        filename = md5(image_filename + audio_filename) + ".mp4"
        file = str(self.cache_dir / filename)

        if file_exists(file):
            return filename

        with audioread.audio_open(audio_file) as f:
            duration = round(f.duration + 0.01 + self.video.interval / 1000, 3)

        temp_mp4_file = str(self.cache_dir / (audio_filename + ".mp4"))
        remove_file(temp_mp4_file)
        cmd = (f'ffmpeg -loop 1 -i {image_file} -c:v libx264 -t {duration} -r {self.video.framerate} '
               f'-vf "scale={self.video.width}:{self.video.height}" -pix_fmt yuv420p {temp_mp4_file}')
        exec_cmd(cmd, temp_mp4_file, "Fail to convert image to video.", timeout=20)

        temp_mp4_file2 = str(self.cache_dir / (audio_filename + "_bg.mp4"))
        remove_file(temp_mp4_file2)
        cmd = (f"ffmpeg -i {temp_mp4_file} -i {audio_file} -c:v copy -c:a aac -ar 48000 -b:a 192k -ac 2 "
               f"-r {self.video.framerate} {temp_mp4_file2}")
        exec_cmd(cmd, temp_mp4_file2, "Fail to merge audio and video.")

        # Add background
        bg_file = str(self.cache_dir / 'background.jpg')
        resize_image(self.video.background_image, self.video.width, self.video.height, bg_file)
        cmd = (f'ffmpeg -i {temp_mp4_file2} -i {bg_file} -r {self.video.framerate} '
               f'-filter_complex "[0:v]colorkey=0x000000:0.1:0.2[ckout];[1:v][ckout]overlay[out]" -map "[out]" -map 0:a {file}')
        exec_cmd(cmd, file, "Fail to add background to video.")

        remove_file(temp_mp4_file)
        remove_file(temp_mp4_file2)

        return filename

    def generate_video_clip(self, video_clip: VideoClip):
        file_path = Path(video_clip.file_path)
        assert file_exists(file_path), "File not exists or corrupts:" + str(file_path)

        filename = "%s_%d_%d.mp4" % (md5_file(file_path), video_clip.before_delay, video_clip.after_delay)

        file = str(self.cache_dir / filename)

        if file_exists(file):
            return filename

        input_file = file_path

        temp_files = []
        if video_clip.before_delay > 0:
            delay = video_clip.before_delay
            before_temp_file = self.cache_dir / ("%s_before.mp4" % md5_file(file_path))

            remove_file(before_temp_file)
            cmd = f'ffmpeg -i {input_file} -vf "tpad=start_duration={delay / 1000}:start_mode=clone" -af "adelay={delay}|{delay}" -c:a aac {before_temp_file}'
            exec_cmd(cmd, before_temp_file, "Fail to convert video format.")

            input_file = before_temp_file
            temp_files.append(before_temp_file)

        if video_clip.after_delay > 0:
            delay = video_clip.after_delay
            after_temp_file = self.cache_dir / ("%s_after.mp4" % md5_file(file_path))

            remove_file(after_temp_file)
            cmd = f'ffmpeg -i {input_file} -vf "tpad=stop={delay / 1000}:stop_mode=clone" -af "apad=pad_dur={delay / 1000}" {after_temp_file}'
            exec_cmd(cmd, after_temp_file, "Fail to convert video format.")

            input_file = after_temp_file
            temp_files.append(after_temp_file)

        cmd = (f'ffmpeg -i {input_file} -c:a aac -ar 48000 -b:a 192k -ac 2 -c:v libx264 -pix_fmt yuv420p '
               f'-r {self.video.framerate} -vf "scale={self.video.width}:{self.video.height}:force_original_aspect_ratio=disable,format=yuv420p" '
               f'-vsync cfr {file}')
        exec_cmd(cmd, file, "Fail to convert video format.")

        for temp_file in temp_files:
            remove_file(temp_file)

        return filename

    def generate(self):
        filenames = []
        for chunk in tqdm(self.video.chunks, desc="Generating"):
            filename = self.generate_one(chunk)

            filenames.append(filename)

        print("Start merge every pieces...")
        # Merge videos.
        tmp_list_file = str(self.cache_dir / "tmp_file_list.txt")
        with open(tmp_list_file, "w") as f:
            for filename in filenames:
                f.write(f"file '{filename}'\n")

        remove_file(self.output_file)
        cmd = f'ffmpeg -f concat -safe 0 -i {tmp_list_file} -c:v libx264 -c:a aac {self.output_file}'
        exec_cmd(cmd, self.output_file, "Fail to merge videos.", stdout=True)

        print("Success to generate video. The file is located at ", self.output_file)

        return self.output_file
