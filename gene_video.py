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
        parser.add_argument('--interval', type=int, default=500,
                            help='The silence duration between two chunk. Unit: ms. Default: 500ms')
        parser.add_argument('--background', type=str, default="./assets/background.png",
                            help="The background image file path. Default: ./assert/background.png")
        parser.add_argument('--width', type=int, default=1920, help="The width of video. Default: 1920")
        parser.add_argument('--height', type=int, default=1080, help="The height of video. Default: 1080")
        parser.add_argument('--framerate', type=int, default=24, help="The framerate of video. Default: 24")
        parser.add_argument('--cache-dir', type=str, default='./cache/')
        parser.add_argument('--proxy', type=str, help="The proxy for edge-tts. For example: http://127.0.0.1:1080")

        args = parser.parse_args()

        return args

    def generate(self):
        with open(self.args.file, encoding='utf-8') as f:
            data_json = json.load(f)

        video = Video(width=self.args.width, height=self.args.height, framerate=self.args.framerate,
                      interval=self.args.interval, background_image=self.args.background,
                      chunks=Video.from_dict(data_json))
        video_generator = VideoGenerator(video, args=self.args, cache_dir=self.args.cache_dir)
        video_generator.generate()


if __name__ == '__main__':
    GenerateVideo().generate()
