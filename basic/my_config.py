# -*- coding: utf-8 -*-
import json
from pathlib import Path


class MyConfig(object):

    def __init__(self):

        self.config = {}

        config_dir_path = Path.cwd() / 'config'
        if not config_dir_path.exists():
            raise Exception("配置文件夹不存在")

        config_file_path = config_dir_path / 'config.json'
        if not config_file_path.exists():
            raise Exception("配置文件不存在")

        with open(config_file_path, mode='r', encoding='utf8') as read_f:
            self.config = json.load(read_f)

        self.check_dir()

    @staticmethod
    def check_dir():
        data_dir_path = Path.cwd() / 'data'

        if not data_dir_path.exists():
            data_dir_path.mkdir()

        user_data_dir = data_dir_path / 'user_data'
        if not user_data_dir.exists():
            user_data_dir.mkdir()

        image_dir = data_dir_path / 'image'
        if not image_dir.exists():
            image_dir.mkdir()

        ocr_files_dir = data_dir_path / 'ocr_files'
        if not ocr_files_dir.exists():
            ocr_files_dir.mkdir()


config_obj = MyConfig()
config = config_obj.config
