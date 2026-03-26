import os
import time
from pathlib import Path

from src.model import Audio, AudioElement
from src.util import md5, exec_cmd, file_exists, remove_file, get_duration, convert_mp3_to_wav, copy_file, \
    convert_wav_to_wav


class AudioGenerator:

    def __init__(self, audio: Audio, args, cache_dir="./cache/"):
        self.args = args
        self.cache_dir = Path(cache_dir) / 'audio'
        os.makedirs(self.cache_dir, exist_ok=True)

        self.audio = audio

        self.lrc_list = []

    def _get_audio(self, audio: AudioElement):
        if not file_exists(audio.file_path):
            raise FileNotFoundError(audio.file_path)

        filename = md5(str(audio.file_path))
        file = str(self.cache_dir / (filename + ".wav"))

        if file_exists(file):
            return file, filename

        if audio.file_path.endswith(".mp3"):
            convert_mp3_to_wav(audio.file_path, file)
        elif audio.file_path.endswith(".wav"):
            convert_wav_to_wav(audio.file_path, file)
        else:
            raise ValueError("Unsupported file format of audio.file_path")

        return file, filename


    def _tts(self, audio: AudioElement):
        filename = md5(audio.text + "_" + audio.tts_name)
        mp3_file = str(self.cache_dir / (filename + ".mp3"))
        file = str(self.cache_dir / (filename + ".wav"))

        if file_exists(file):
            return file, filename

        text = audio.text.replace("\n", " ")
        cmd = f'edge-tts --text "{text}" -v {audio.tts_name} --write-media {mp3_file}'
        if self.args.proxy is not None:
            cmd += " --proxy " + self.args.proxy

        def gene_file(retry: bool):
            try:
                remove_file(mp3_file)
                exec_cmd(cmd, mp3_file, stdout=retry)
                return True
            except Exception as e:
                print("Fail to generate audio file with edge-tts. Retry it after 20s. Command: {}".format(cmd))
                return False

        for i in range(3):
            if gene_file(i > 0):
                break

            time.sleep(20)
        else:
            raise RuntimeError("Fail to generate audio file with edge-tts. Command: {}".format(cmd))

        time.sleep(0.05)

        # Convert mp3 to wav
        remove_file(file)
        convert_mp3_to_wav(mp3_file, file)
        remove_file(mp3_file)

        return file, filename

    def _generate_one(self, audio: AudioElement):
        if audio.file_path is not None:
            file, filename = self._get_audio(audio)
        else:
            file, filename = self._tts(audio)

        if audio.before_silence <= 0 and audio.after_silence <= 0:
            return file, filename

        filename = f"{filename}_{audio.before_silence}_{audio.after_silence}"
        old_file = file
        file = str(self.cache_dir / (filename + ".wav"))

        if file_exists(file):
            return file, filename

        delay_list = []
        if audio.before_silence > 0:
            delay_list.append(f"adelay={audio.before_silence}|{audio.before_silence}")
        if audio.after_silence > 0:
            delay_list.append(f"apad=pad_dur={round(audio.after_silence / 1000, 3)}")
        delay = ",".join(delay_list)

        remove_file(file)
        cmd = f'ffmpeg -i {old_file} -af "{delay}" -acodec pcm_s16le {file}'
        exec_cmd(cmd, file, "Fail to add silence to audio file.", timeout=10)

        return file, filename

    def generate(self):
        # Generate silence audio file.
        silence_file = str(self.cache_dir / f"silence_{self.audio.interval}.wav")
        if self.audio.interval > 0 and not file_exists(silence_file):
            cmd = (f'ffmpeg -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 -t '
                   f'{round(self.audio.interval / 1000, 3)} -c:a pcm_s16le {silence_file}')
            exec_cmd(cmd, silence_file, "Fail to generate silent audio file.", timeout=10)

        # Generate audio.
        file_list = []
        filename_list = []
        for i, audio_item in enumerate(self.audio.elements):
            file, filename = self._generate_one(audio_item)

            if self.audio.interval > 0:
                file_list.append(silence_file)
                # Measure actual silence file duration for accurate timing
                silence_duration = get_duration(silence_file)
                self.lrc_list.append({
                    "file": silence_file,
                    "duration": silence_duration,
                    "text": None
                })

            file_list.append(file)
            filename_list.append(filename)

            self.lrc_list.append({
                "file": file,
                "text": audio_item.text
            })

        filename = md5(f'_{self.audio.interval}_'.join(filename_list))
        file = str(self.cache_dir / (filename + ".wav"))

        if file_exists(file):
            return file, filename

        merge_txt = str(self.cache_dir / 'merge.txt')
        with open(merge_txt, 'w') as f:
            for file_item in file_list:
                f.write(f"file '{Path(file_item).name}'\n")

        remove_file(file)
        cmd = f'ffmpeg -f concat -safe 0 -i {merge_txt} -c copy {file}'
        exec_cmd(cmd, file, "Fail to merge audio files.", timeout=10)

        return file, filename
