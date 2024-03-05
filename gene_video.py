import os
import argparse
import shutil
import time
import hashlib
from multiprocessing import cpu_count
from pathlib import Path
from typing import List

import cv2
import pandas as pd

from mutagen.id3 import USLT, Encoding, ID3, TIT2, TALB, TCOM

from gtts import gTTS
from mutagen.mp3 import MP3
from pydub import AudioSegment
from tqdm import tqdm
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, AudioFileClip


def _clean_content(content: str, clean_symbol=()):
    if content is None:
        return ''

    if pd.isnull(content):
        return ''

    if type(content) != str:
        content = str(content)

    content = content.strip()

    if len(clean_symbol) > 0:
        for symbol in clean_symbol:
            content = content.replace(symbol, '')

    return content


def is_null(obj):
    """
    判断一个对象是否为空，不同的对象有不同的判定方法
    """
    if obj is None:
        return True

    if hasattr(obj, '__len__'):
        return len(obj) <= 0

    raise RuntimeError("不支持的obj类型：" + str(type(obj)))


def sum_list_total_len(obj_list: list):
    """
    统计list每个元素的总长度之和
    """
    total_len = 0
    for item in obj_list:
        total_len += len(item)

    return total_len


def has_chinese(content: str):
    for char in content:
        if '\u4e00' <= char <= '\u9fff':
            return True

    return False


def md5(content: str):
    md = hashlib.md5()
    md.update(content.encode('utf-8'))
    return md.hexdigest()


class GenerateVideo(object):

    def __init__(self):
        self.args = self.parse_args()
        self.data_list = self.read_data()

        self.cache_dir = Path(self.args.cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        self.output_dir = Path(self.args.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        os.makedirs(self.cache_dir / 'video', exist_ok=True)
        self.temp_video = self.cache_dir / 'video' / 'temp_video.mp4'

        self.filename = Path(self.args.filename).name.split(".")[0]

        self.lrc_list = [
            "[ar:iioSnail]",  # 作者
            "[al:%s]" % self.filename,  # 专辑（用文件名作为专辑名）
            "[by:iioSnail]",  # 制作人
        ]  # 歌词

    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--filename', type=str, default='./samples/coca20000.xlsx', help='单词文件的路径')
        parser.add_argument('--read-columns', type=str, default='单词,基本释义',
                            help="需要朗读的列，多个列用逗号分隔。例如：单词,基本释义,例句")
        parser.add_argument('--lrc-columns', type=str, default='单词+基本释义',
                            help='需要在音频歌词中展示的列，多个列用逗号分隔，若使用+号。例如：单词+释义,详细释义')
        parser.add_argument('--show-columns', type=str, default='序号+单词+音标,详细释义,例句,例句释义',
                            help="需要在视频中展示的列，多个列以逗号分割，若使用+号，两列将展示到一行。例如：序号+单词+音标,详细释义,例句,例句中文")
        parser.add_argument('--from-line', type=int, default=1, help="从excel哪一行开始（包含该行）")
        parser.add_argument('--until-line', type=int, default=-1, help="到excel哪一行结束（包含该行）。-1表示到文件结尾")
        parser.add_argument('--repeat-times', type=int, default=2, help='重复次数')
        parser.add_argument('--interval', type=int, default=1000, help='两个单词的间隔时间(ms)')
        parser.add_argument('--inner-interval', type=int, default=500, help='单词和释义的间隔时间(ms)')
        parser.add_argument('--max-minutes', type=int, default=30, help='单个音/视频最大时长(分钟)')
        parser.add_argument('--video', action='store_true', default=True, help='生成视频')
        parser.add_argument('--no-video', dest='video', action='store_false', help='不生成视频')
        parser.add_argument('--add-volume', type=int, default=0, help='加减音量（分贝）。例如：10是音量加10分贝，-10是减10分贝')
        parser.add_argument('--background-color', type=str, default='black', help='视频背景色')
        parser.add_argument('--font-color', type=str, default='white', help='文字颜色')
        parser.add_argument('--video-width', type=int, default=1920, help='视频宽')
        parser.add_argument('--video-height', type=int, default=1080, help='视频高')
        parser.add_argument('--max-font-size', type=int, default=120, help='最大字体大小')
        parser.add_argument('--cache-dir', type=str, default='./drive/MyDrive/cache/', help='生成的临时文件存放的目录')
        parser.add_argument('--output-dir', type=str, default='./drive/MyDrive/outputs/', help='输出文件的目录')

        args = parser.parse_known_args()[0]

        return args

    def read_data(self) -> List:
        if not os.path.exists(self.args.filename):
            raise RuntimeError("找不到单词文件: " + self.args.filename)

        if self.args.filename.endswith(".xlsx") or "".endswith(".xls"):
            data = pd.read_excel(self.args.filename, dtype=str)
        elif self.args.filename.endswith(".csv"):
            data = pd.read_csv(self.args.filename, dtype=str)
        else:
            raise RuntimeError("不支持的文件格式：" + self.args.filename)

        read_columns = self.args.read_columns.split(',')
        lrc_columns = self.args.lrc_columns.split(',')
        lrc_columns = [item.split('+') for item in lrc_columns]
        show_columns = self.args.show_columns.split(',')
        show_columns = [item.split('+') for item in show_columns]

        for col in read_columns:
            if col not in data.columns:
                raise RuntimeError("Excel中不存在“%s”列，请检查read-columns参数与Excel文件!" % col)

        for col_list in lrc_columns:
            for col in col_list:
                if col not in data.columns:
                    raise RuntimeError("Excel中不存在“%s”列，请检查lrc-columns参数与Excel文件!" % col)

        for col_list in show_columns:
            for col in col_list:
                if col not in data.columns:
                    raise RuntimeError("Excel中不存在“%s”列，请检查show-columns参数与Excel文件!" % col)

        data_list = []
        for i, row in data.iterrows():
            if i + 1 < self.args.from_line:
                continue

            if self.args.until_line > 0 and i + 1 > self.args.until_line:
                break

            read = []
            for col in read_columns:
                read.append(_clean_content(row[col]))

            lrc = []
            for col_list in lrc_columns:
                items = []
                for col in col_list:
                    items.append(_clean_content(row[col]))
                lrc.append('  '.join(items))

            show = []
            for col_list in show_columns:
                items = []
                for col in col_list:
                    items.append(_clean_content(row[col]))
                show.append('  '.join(items))

            data_list.append((read, lrc, show))

        return data_list

    def generate_audio(self, content, lang=None) -> Path:
        audio_dir = self.cache_dir / 'audio'
        os.makedirs(audio_dir, exist_ok=True)

        old_cache_file = audio_dir / (_clean_content(content, ('\\', '/', ':', '*', '?', '"', '<', '>', '|')) + '.mp3')
        cache_file = audio_dir / (md5(content) + '.mp3')

        if os.path.exists(old_cache_file):
            try:
                return AudioSegment.from_mp3(old_cache_file)
            except:
                print(f"[WARN]“{str(old_cache_file)}”缓存有问题，重新获取!")

        if os.path.exists(cache_file):
            try:
                return AudioSegment.from_mp3(cache_file)
            except:
                print(f"[WARN]“{str(cache_file)}”缓存有问题，重新获取!")

        if lang is None:
            if has_chinese(content):
                lang = 'zh'
            else:
                lang = 'en'

        tts = gTTS(content, lang=lang)
        tts.save(cache_file)

        # 如果报错，请执行：conda install -c conda-forge ffmpeg
        return AudioSegment.from_mp3(cache_file)

    def _auto_font_size(self, text, font_file):
        """
        自适应文字大小
        """
        font_size = self.args.max_font_size

        width, height = self.args.video_width, self.args.video_height
        while font_size >= 20:
            font = ImageFont.truetype(font_file, font_size)

            image = Image.new("RGB", (width, height), self.args.background_color)
            draw = ImageDraw.Draw(image)
            bbox = draw.multiline_textbbox((0, 0, width, height), text, font)
            text_width = bbox[2]

            if text_width <= width:
                break
            else:
                font_size -= 10

        return font_size

    def generate_image(self, lines):
        """
        生成该行的视频图片
        """
        if not self.args.video:
            return None

        text = '\n'.join(lines)

        os.makedirs(self.cache_dir / 'image', exist_ok=True)
        cache_file = self.cache_dir / 'image' / f'{md5(text)}.png'

        if os.path.exists(cache_file):
            return cache_file

        font_file = "./assets/font.TTF"
        font_size = self._auto_font_size(text, font_file)
        font = ImageFont.truetype(font_file, font_size)

        width, height = self.args.video_width, self.args.video_height
        line_spacing = 50
        image = Image.new("RGB", (width, height), self.args.background_color)
        draw = ImageDraw.Draw(image)

        bbox = draw.multiline_textbbox((0, 0, width, height), text, font=font)

        text_y = (height - bbox[3]) // len(lines)

        lines = text.split('\n')
        for line in lines:
            line_bbox = draw.textbbox((0, 0, width, height), line, font)
            line_width, line_height = line_bbox[2], line_bbox[3]
            draw.text(((width - line_width) // 2, text_y), line, font=font, fill=self.args.font_color)
            text_y += line_height + line_spacing  # Move to the next line

        image.save(cache_file)

        return cache_file

    def generate_video(self, video, image, duration: int):
        """
        返回两个值，一个是视频。一个是本次损失的毫秒数。要不然每个视频损失一点，到后面就会对不上。
        """
        if not self.args.video:
            return None, 0

        video_file = self.temp_video

        frame_size = 10
        width = self.args.video_width
        height = self.args.video_height

        if video is None:
            video = cv2.VideoWriter(str(video_file), cv2.VideoWriter_fourcc('m', 'p', '4', 'v'), frame_size,
                                    (width, height))

        # 3532 / 1000 = 3.532 * 10 = 35.32 = 32ms
        #
        frame = int(duration / 1000 * frame_size)
        loss = duration - (1000 / frame_size) * frame

        image = cv2.imread(str(image))
        for _ in range(frame):
            video.write(image)

        return video, loss

    def add_lrc(self, lrc_list: list, timer: int, content):
        """
        增添歌词
        :param timer: 时间节点（毫秒）
        :param content: 歌词内容
        """
        minutes = timer // 60_000
        seconds = timer // 1000 % 60
        sub_seconds = timer % 1000 // 10
        if type(content) == str:
            lrc_list.append("[%02d:%02d.%02d]%s" % (minutes, seconds, sub_seconds, content))

        if type(content) == list:
            for content_item in content:
                lrc_list.append("[%02d:%02d.%02d]%s" % (minutes, seconds, sub_seconds, content_item))

    def merge_audio_video(self, audio_path, video_path, output_path):
        audio = str(audio_path)
        video = str(video_path)

        video = VideoFileClip(video)
        audio = AudioFileClip(audio)
        video = video.set_audio(audio)

        video.write_videofile(str(output_path), fps=10, threads=cpu_count(), logger=None)
        video.close()

    def build_in_lrc(self, filename, lrc_list):
        """
        将歌词嵌入到mp3文件中。但不是所有音乐软件都识别
        todo 搞了好久，搞不出来
        :param filename: 文件名路径
        :param lrc_list: 歌词列表
        """
        audio = MP3(filename, ID3=ID3)

        if not audio.tags:
            audio.add_tags()

        uslt_frame = USLT(encoding=3, lang='eng', text='\n'.join(lrc_list))

        audio.tags["TALB"] = TALB(encoding=3, text=self.filename)  # 专辑
        audio.tags["TCOM"] = TCOM(encoding=3, text='iioSnail')  # 作曲家
        audio.tags['USLT'] = uslt_frame

        audio.save()

    def generate(self):
        start_index = None
        video: cv2.VideoWriter = None
        audio_segments = []
        lrc_list = self.lrc_list.copy()
        loss = 0
        for i, (read_items, lrc_items, show_items) in tqdm(enumerate(self.data_list), total=len(self.data_list)):
            curr_audio_segments = []
            index = i + 1
            if start_index is None:
                start_index = index

            if len(read_items) <= 0:
                continue

            # 生成音频
            for _ in range(self.args.repeat_times):
                for j, read_content in enumerate(read_items):
                    if is_null(read_content):
                        continue

                    audio = self.generate_audio(read_content)
                    audio = audio.fade_in(100).fade_out(100)
                    curr_audio_segments.append(audio)
                    audio_segments.append(audio)
                    if len(audio_segments) <= 0:
                        # 音频一开始先增添一小段静音
                        interval = AudioSegment.silent(duration=self.args.interval,
                                                       frame_rate=audio.frame_rate)
                        audio_segments.append(interval)
                        curr_audio_segments.append(interval)

                    interval = AudioSegment.silent(duration=self.args.inner_interval, frame_rate=audio.frame_rate)
                    curr_audio_segments.append(interval)
                    audio_segments.append(interval)

            # 两个单词之间增加空白
            silent_duration = max(self.args.interval - self.args.inner_interval, 100)
            interval = AudioSegment.silent(duration=silent_duration,
                                           frame_rate=audio_segments[-1].frame_rate)
            curr_audio_segments.append(interval)
            audio_segments.append(interval)

            # 计算本次的音频时长(ms)
            audio_duration = sum_list_total_len(curr_audio_segments)

            # 生成视频
            image = self.generate_image(show_items)  # 生成图片
            video, loss = self.generate_video(video, image, audio_duration + loss)

            total_audio_duration = sum_list_total_len(audio_segments)
            # 生成歌词
            self.add_lrc(lrc_list, total_audio_duration - audio_duration, lrc_items)

            # 输出到文件
            if total_audio_duration >= self.args.max_minutes * 60 * 1000 or i == len(
                    self.data_list) - 1:

                offset = max(self.args.from_line - 1, 0)  # 如果不是从第1行开始的，那么标题名字也跟着往后偏移
                title = f'{start_index + offset}-{index + offset}'
                merged_audio_file = self.output_dir / f'{title}.wav'
                merged_audio = sum(audio_segments)
                merged_audio += self.args.add_volume  # 加减音量
                merged_audio.export(str(merged_audio_file), format("wav"))
                lrc_file = self.output_dir / f'{title}.lrc'
                # 生成歌词
                with open(lrc_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lrc_list))

                print("\n生成音频文件：", str(merged_audio_file))
                print("\n生成歌词文件：", str(lrc_file))

                if self.args.video:
                    video.release()

                    cache_video_file = self.cache_dir / 'video' / f'{title}.mp4'
                    shutil.move(self.temp_video, cache_video_file)
                    video_file = self.output_dir / f'{title}.mp4'

                    # 合并音频视频
                    start_time = time.time()
                    print("\n生成视频中，耗时较长，请耐心等待...")
                    self.merge_audio_video(merged_audio_file, cache_video_file, video_file)

                    print("\n生成视频文件：", str(video_file))
                    print("耗时:", int(time.time() - start_time), '秒')

                audio_segments = []
                start_index = None
                video = None
                lrc_list = self.lrc_list.copy()


if __name__ == '__main__':
    GenerateVideo().generate()
