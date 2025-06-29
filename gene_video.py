import argparse
import json

from src.model import Video
from src.video import VideoGenerator


class GenerateVideo(object):

    def __init__(self):
        self.args = self.parse_args()

    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--file', type=str, required=True, help='The json filepath.')
        parser.add_argument('--output', type=str, default='output.mp4', help='The output filepath.')
        parser.add_argument('--output-mp3', type=str, default=None, help='The output filepath for mp3 file.')
        parser.add_argument('--output-lrc', type=str, default=None, help='The output filepath for lyric file.')
        parser.add_argument('--background', type=str, default="./assets/background.png",
                            help="The background image file path. Default: ./assert/background.png")
        parser.add_argument('--width', type=int, default=1920, help="The width of video. Default: 1920")
        parser.add_argument('--height', type=int, default=1080, help="The height of video. Default: 1080")
        parser.add_argument('--framerate', type=int, default=25, help="The framerate of video. Default: 25")
        parser.add_argument('--cache-dir', type=str, default='./cache/')
        parser.add_argument('--proxy', type=str, help="The proxy for edge-tts. For example: http://127.0.0.1:1080")

        args = parser.parse_args()

        return args

    def generate(self):
        with open(self.args.file, encoding='utf-8') as f:
            data_json = json.load(f)

        video = Video(width=self.args.width, height=self.args.height, framerate=self.args.framerate,
                      background_image=self.args.background, chunks=Video.from_dict(data_json))
        video_generator = VideoGenerator(video, args=self.args, cache_dir=self.args.cache_dir)
        video_generator.generate()
        video_generator.output_audio()
        video_generator.output_lrc()


if __name__ == '__main__':
    GenerateVideo().generate()
