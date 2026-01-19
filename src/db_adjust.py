import contextlib
import math
import os
import tempfile
import wave
from pathlib import Path
from typing import List

import numpy as np
import webrtcvad
from pydub import AudioSegment
from tqdm import tqdm

from src.util import exec_cmd, move_file


class SpeechDetection:
    """
    Detect speech segments and loudness from audio or video.
    """

    def __init__(self, aggressiveness: int = 2):
        self.vad = webrtcvad.Vad(aggressiveness)

    def _format_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h:02}:{m:02}:{s:06.3f}"

    def _convert_to_wav(self, input_file: str) -> str:
        audio = AudioSegment.from_file(input_file)
        audio = (
            audio
            .set_channels(1)
            .set_frame_rate(16000)
            .set_sample_width(2)  # 16-bit PCM
        )

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        audio.export(tmp.name, format="wav")
        return tmp.name

    def _read_wave(self, path: str):
        with contextlib.closing(wave.open(path, "rb")) as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 16000

            pcm_data = wf.readframes(wf.getnframes())
            return pcm_data, wf.getframerate()

    def _frame_generator(self, frame_duration_ms: int, audio: bytes, sample_rate: int):
        frame_size = int(sample_rate * frame_duration_ms / 1000) * 2
        offset = 0
        timestamp = 0.0
        duration = frame_duration_ms / 1000.0

        while offset + frame_size <= len(audio):
            yield audio[offset:offset + frame_size], timestamp, duration
            timestamp += duration
            offset += frame_size

    def _pcm16_dbfs(self, pcm_bytes: bytes) -> float:
        """
        Compute average RMS loudness in dBFS from 16-bit PCM audio.
        """
        if not pcm_bytes:
            return float("-inf")

        samples = np.frombuffer(pcm_bytes, dtype=np.int16)
        if samples.size == 0:
            return float("-inf")

        rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
        if rms == 0:
            return float("-inf")

        return 20 * math.log10(rms / 32768.0)

    def detect(self, filename: str) -> List[dict]:
        """
        Detect speech segments in an audio/video file.

        Returns:
        [
            {
                "start_time": "00:00:01.135",
                "end_time": "00:00:04.351",
                "db": -22.84
            },
            ...
        ]
        """
        wav_file = self._convert_to_wav(filename)
        audio, sample_rate = self._read_wave(wav_file)

        frames = list(self._frame_generator(30, audio, sample_rate))

        speech_segments = []
        triggered = False
        start_time = 0.0
        speech_pcm = bytearray()

        for frame, timestamp, duration in frames:
            is_speech = self.vad.is_speech(frame, sample_rate)

            if is_speech and not triggered:
                triggered = True
                start_time = timestamp
                speech_pcm = bytearray()
                speech_pcm.extend(frame)

            elif is_speech and triggered:
                speech_pcm.extend(frame)

            elif not is_speech and triggered:
                end_time = timestamp
                db = self._pcm16_dbfs(bytes(speech_pcm))

                speech_segments.append({
                    "start_time": self._format_time(start_time),
                    "end_time": self._format_time(end_time),
                    "db": round(db, 2)
                })

                triggered = False
                speech_pcm = bytearray()

        # Handle speech continuing until EOF
        if triggered:
            end_time = frames[-1][1] + frames[-1][2]
            db = self._pcm16_dbfs(bytes(speech_pcm))

            speech_segments.append({
                "start_time": self._format_time(start_time),
                "end_time": self._format_time(end_time),
                "db": round(db, 2)
            })

        os.remove(wav_file)
        return speech_segments


class DecibelAdjustor:

    def __init__(self, cache_dir: Path, target_db: float = -20.0, max_gain: float = 15.0):
        self.cache_dir = cache_dir
        self.target_db = target_db
        self.max_gain = max_gain

    def adjust(self, filename: str, output: str, target_db=None):
        if target_db is None:
            target_db = self.target_db

        detector = SpeechDetection()
        segments = detector.detect(filename)

        # Load original audio
        audio = AudioSegment.from_file(filename)
        audio = audio.set_channels(1)

        # IMPORTANT: start EMPTY, not silent
        adjusted_audio = AudioSegment.empty()

        cursor = 0

        for seg in tqdm(segments, total=len(segments), desc="Adjusting decibels"):
            start_ms = self._time_to_ms(seg["start_time"])
            end_ms = self._time_to_ms(seg["end_time"])
            measured_db = seg["db"]

            # Copy non-speech exactly
            if start_ms > cursor:
                adjusted_audio += audio[cursor:start_ms]

            speech_chunk = audio[start_ms:end_ms]

            # Compute gain
            gain = target_db - measured_db
            gain = max(min(gain, self.max_gain), -self.max_gain)

            adjusted_audio += speech_chunk.apply_gain(gain)

            cursor = end_ms

        # Append tail
        if cursor < len(audio):
            adjusted_audio += audio[cursor:]

        # Export temp audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir=self.cache_dir) as tmp:
            adjusted_audio.export(tmp.name, format="wav")
            tmp_audio = tmp.name

        if self._is_video(filename):
            self._mux_audio(filename, tmp_audio, output)
        else:
            move_file(tmp_audio, output)

    def _time_to_ms(self, t: str) -> int:
        h, m, s = t.split(":")
        return int((int(h) * 3600 + int(m) * 60 + float(s)) * 1000)

    def _is_video(self, filename: str) -> bool:
        return os.path.splitext(filename)[1].lower() in {
            ".mp4", ".mkv", ".mov", ".avi"
        }

    def _mux_audio(self, video_path: str, audio_path: str, output_path: str):
        cmd = (
            f'ffmpeg -y -i "{video_path}" -i "{audio_path}" '
            f'-c:v copy -map 0:v:0 -map 1:a:0 '
            f'-shortest "{output_path}"'
        )

        exec_cmd(cmd, output_path, "Fail to adjust decibel.", stdout=True)
