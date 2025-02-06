from dataclasses import dataclass, fields
from typing import List, Any


@dataclass
class FrameElement:
    x_coord: float  # 0~1
    y_coord: float  # 0~1
    coord_type: str  # top-left or center. Default: center
    font_size: int  # px. default: 18
    font_color: str  # Default: white
    content: str  # text content. For example: Hello world

    def __post_init__(self):
        self.coord_type = 'center' if self.coord_type is None else self.coord_type
        self.font_size = 18 if self.font_size is None else self.font_size
        self.font_color = "white" if self.font_color is None else self.font_color


@dataclass
class Frame:
    elements: List[FrameElement]


@dataclass
class AudioElement:
    text: str  # The text that will be read.
    tts_name: str  # The name of edge-tts. Reference: https://github.com/rany2/edge-tts
    before_silence: int  # Add silence before the audio. Unit: ms
    after_silence: int  # Add silence before the audio. Unit: ms

    def __post_init__(self):
        self.tts_name = 'en-US-AnaNeural' if self.tts_name is None else self.tts_name
        self.before_silence = 0 if self.before_silence is None else self.before_silence
        self.after_silence = 0 if self.after_silence is None else self.after_silence


@dataclass
class Audio:
    elements: List[AudioElement]
    interval: int  # The silence duration between two audio. Unit: ms

    def __post_init__(self):
        self.interval = 0 if self.interval is None else self.interval


@dataclass
class Chunk:
    frame: Frame
    audio: Audio


@dataclass
class Video:
    width: int
    height: int
    framerate: int
    interval: int  # The silence duration between two chunk. Unit: ms

    chunks: List[Chunk]

    def __post_init__(self):
        self.framerate = 24 if self.framerate is None else self.framerate
        self.interval = 0 if self.interval is None else self.interval

    @staticmethod
    def from_dict(data_dict) -> List[Chunk]:
        chunks = []
        for data_item in data_dict:
            frame_elements = [
                FrameElement(
                    x_coord=element.get("x_coord"),
                    y_coord=element.get("y_coord"),
                    coord_type=element.get("coord_type"),
                    font_size=element.get("font_size"),
                    font_color=element.get("font_color"),
                    content=element.get("content")
                )
                for element in data_item['frame']['elements']
            ]

            frame = Frame(elements=frame_elements)

            audio_elements = [
                AudioElement(
                    text=element.get("text"),
                    tts_name=element.get("tts_name"),
                    before_silence=element.get('before_silence'),
                    after_silence=element.get('after_silence'),
                )
                for element in data_item['audio']['elements']
            ]
            audio = Audio(elements=audio_elements, interval=data_item['audio']['interval'])

            chunks.append(Chunk(frame=frame, audio=audio))

        return chunks
