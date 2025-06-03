import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from dataclasses import asdict

from src.model import Frame
from src.util import md5, file_exists


class FrameGenerator:

    def __init__(self, frame: Frame, width, height, cache_dir="./cache/"):
        self.frame = frame
        self.width = width
        self.height = height

        self.cache_dir = Path(cache_dir) / 'image'
        os.makedirs(self.cache_dir, exist_ok=True)

        self.background = "black"
        self.font_file = "./assets/font.TTF"

    def __draw_textsize(self, draw: ImageDraw, content, font):
        try:
            text_width, text_height = draw.textsize(content, font=font)
        except Exception as e:
            left, top, right, bottom = draw.textbbox((0, 0), content, font=font)
            text_width, text_height = right - left, bottom - top

        return text_width, text_height

    def generate(self):
        image = Image.new("RGB", (self.width, self.height), self.background)
        draw = ImageDraw.Draw(image)

        filename = md5(json.dumps(asdict(self.frame))) + ".jpg"
        file = str(self.cache_dir / filename)
        if file_exists(file):
            return file, filename

        for element in self.frame.elements:
            # Calculate the base position
            base_x = int(element.x_coord * self.width)
            base_y = int(element.y_coord * self.height)

            # Load the font
            font = ImageFont.truetype(self.font_file, element.font_size)

            # Split content into multiple lines
            lines = element.content.split('\n')

            # Estimate line height (including spacing)
            _, line_height = self.__draw_textsize(draw, "A", font=font)
            spacing = int(line_height * 0.2)  # some spacing between lines
            total_height = len(lines) * line_height + (len(lines) - 1) * spacing

            # Start y-position to vertically center the block of text
            y = base_y
            if element.coord_type == "center":
                y -= total_height // 2

            # Draw each line
            for line in lines:
                text_width, text_height = self.__draw_textsize(draw, line, font)

                x = base_x
                if element.coord_type == "center":
                    x -= text_width // 2

                draw.text((x, y), line, font=font, fill=element.font_color)
                y += text_height + spacing

        image.save(file)

        return file, filename

