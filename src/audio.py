import os
import time
from pathlib import Path

from src.model import Audio, AudioElement
from src.util import md5, exec_cmd, file_exists


class AudioGenerator:

    def __init__(self, audio: Audio, args, cache_dir="./cache/"):
        self.args = args
        self.cache_dir = Path(cache_dir) / 'audio'
        os.makedirs(self.cache_dir, exist_ok=True)

        self.audio = audio

    def _tts(self, audio: AudioElement):
        filename = md5(audio.text + "_" + audio.tts_name)
        file = str(self.cache_dir / (filename + ".mp3"))
        if file_exists(file):
            return file, filename

        cmd = f'edge-tts --text "{audio.text}" -v {audio.tts_name} --write-media {file}'
        if self.args.proxy is not None:
            cmd += " --proxy " + self.args.proxy

        exec_cmd(cmd, file, "Fail to generate audio file with edge-tts. Please check you network.")

        time.sleep(0.05)

        return file, filename

    def _generate_one(self, audio: AudioElement):
        file, filename = self._tts(audio)

        if audio.before_silence <= 0 and audio.after_silence <= 0:
            return file, filename

        filename = f"{filename}_{audio.before_silence}_{audio.after_silence}"
        old_file = file
        file = str(self.cache_dir / (filename + ".mp3"))

        if file_exists(file):
            return file, filename

        delay_list = []
        if audio.before_silence > 0:
            delay_list.append(f"adelay={audio.before_silence}|{audio.before_silence}")
        if audio.after_silence > 0:
            delay_list.append(f"apad=pad_dur={round(audio.after_silence / 1000, 3)}")
        delay = ",".join(delay_list)

        cmd = f'ffmpeg -i {old_file} -af "{delay}" -acodec libmp3lame {file}'
        exec_cmd(cmd, file, "Fail to add silence to audio file.")

        return file, filename

    def generate(self):
        # Generate silence audio file.
        silence_file = str(self.cache_dir / f"silence_{self.audio.interval}.mp3")
        if self.audio.interval > 0 and not file_exists(silence_file):
            cmd = f"ffmpeg -f lavfi -t {round(self.audio.interval / 1000, 3)} -i anullsrc=r=44100:cl=stereo {silence_file}"
            exec_cmd(cmd, silence_file, "Fail to generate silent audio file.")

        # Generate audio.
        file_list = []
        filename_list = []
        for i, audio_item in enumerate(self.audio.elements):
            file, filename = self._generate_one(audio_item)

            if self.audio.interval > 0:
                file_list.append(silence_file)

            file_list.append(file)

            filename_list.append(filename)

        filename = md5(f'_{self.audio.interval}_'.join(filename_list))
        file = str(self.cache_dir / (filename + ".mp3"))

        if file_exists(file):
            return file, filename

        merge_txt = str(self.cache_dir / 'merge.txt')
        with open(merge_txt, 'w') as f:
            for file_item in file_list:
                f.write(f"file '{Path(file_item).name}'\n")

        cmd = f'ffmpeg -f concat -safe 0 -i {merge_txt} -c copy {file}'
        exec_cmd(cmd, file, "Fail to merge audio files.")

        return file, filename
