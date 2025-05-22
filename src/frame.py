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

    def generate(self):
        image = Image.new("RGB", (self.width, self.height), self.background)
        draw = ImageDraw.Draw(image)

        filename = md5(json.dumps(asdict(self.frame))) + ".jpg"
        file = str(self.cache_dir / filename)
        if file_exists(file):
            return file, filename

        for element in self.frame.elements:
            # Calculate the actual position based on the relative coordinates
            x = int(element.x_coord * self.width)
            y = int(element.y_coord * self.height)

            # Load a font with the specified size
            font = ImageFont.truetype(self.font_file, element.font_size)  # You can specify a font file

            # Adjust position if coord_type is "center"
            if element.coord_type == "center":
                try:
                    text_width, text_height = draw.textsize(element.content, font=font)
                except Exception as e:
                    left, top, right, bottom = draw.textbbox((0, 0), element.content, font=font)
                    text_width, text_height = right - left, bottom - top

                x -= text_width // 2
                y -= text_height // 2

            # Draw the text on the image
            draw.text((x, y), element.content, font=font, fill=element.font_color)

        image.save(file)

        return file, filename
