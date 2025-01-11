import cv2
import numpy as np
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import os
from pydub.utils import mediainfo
from typing import List
import subprocess
import shutil
import configparser
import sys

class GenerateSubtitle:
    def __init__(
            self,
            font_path: str,
            font_size: int,
            band_size: List,
            background_color: List,
            text_color: List,
        ):
        self.font_path = font_path
        self.font_size = font_size
        self.band_size = band_size
        self.background_color = background_color
        self.text_color = text_color
        self.temp_dir = os.path.abspath('temp')
        if not os.path.exists(self.temp_dir):
            os.mkdir(self.temp_dir)
        else:
            print(f'{self.temp_dir} already exists')

    @staticmethod
    def get_audio_duration(audio_file):
        info = mediainfo(audio_file)
        return float(info["duration"])

    def create_text_video(self, text, output_file):
        # text
        font = ImageFont.truetype(self.font_path, self.font_size)
        width, height = self.band_size
        img = Image.new('RGB', (width, height), self.background_color)
        draw = ImageDraw.Draw(img)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
        text_x = (width - text_width) // 2
        text_y = (height - text_height) // 2
        draw.text((text_x, text_y), text, fill=self.text_color, font=font)
        # sound
        tts = gTTS(text=text, lang='ja', slow=False)
        audio_file = f"{self.temp_dir}/temp_audio.mp3"
        tts.save(audio_file)
        duration = self.get_audio_duration(audio_file)
        # movie
        fps = 30
        frame_count = int(fps * duration)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video = cv2.VideoWriter(output_file, fourcc, fps, (width, height))
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        for _ in range(frame_count):
            video.write(frame)
        video.release()
        # movie + sound
        temp_video = f"{self.temp_dir}/temp_video.mp4"
        os.rename(output_file, temp_video)
        os.system(f"ffmpeg -i {temp_video} -i {audio_file} -c:v copy -c:a aac -strict experimental {output_file}")
        # remove temp files
        os.remove(temp_video)
        os.remove(audio_file)

    def concatenate_text_video(self, output_file):
        files = sorted([f for f in os.listdir(self.temp_dir) if f.endswith('.mp4')])
        list_file_path = os.path.join(self.temp_dir, "file_list.txt")
        with open(list_file_path, "w") as list_file:
            for file in files:
                full_path = os.path.join(self.temp_dir, file)
                list_file.write(f"file '{full_path}'\n")
        try:
            subprocess.run(
                ["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_file_path, "-c", "copy", output_file],
            )
            print(f"Output file created: {output_file}")
        except subprocess.CalledProcessError as e:
            print(f"Error during concatenation: {e}")
        finally:
            if os.path.exists(list_file_path):
                os.remove(list_file_path)

    def main(self, text, output_file):
        # splited movie
        text_list = text.splitlines()
        for i, splited_text in enumerate(text_list):
            self.create_text_video(splited_text, f'{self.temp_dir}/{i}.mp4')
        self.concatenate_text_video(output_file)

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if __name__ == '__main__':
    config_ini = configparser.ConfigParser()
    config_ini.read(resource_path('config/config.ini'), encoding='utf-8')
    subtitle = config_ini['Subtitle']
    font_path = subtitle.get('font_path')
    font_size = int(subtitle.get('font_size'))
    band_size = eval(subtitle.get('band_size'))
    text_color = eval(subtitle.get('text_color'))
    background_color = eval(subtitle.get('background_color'))
    gen = GenerateSubtitle(
        font_path, font_size, band_size, background_color, text_color,
    )
    with open(resource_path("script.txt")) as f:
        all_text = f.read()
    paragraphs = [paragraph.strip() for paragraph in all_text.strip().split("\n\n")]
    for i, text in enumerate(paragraphs):
        gen.main(text, f"output/page_{i+1}.mp4")
    shutil.rmtree(gen.temp_dir)
    