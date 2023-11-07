# -*- coding: utf-8 -*-
import os
import json
import base64
import urllib
import logging
import requests
from pathlib import Path


class OCR(object):

    def __init__(self, config_dict: dict = None, logger: logging.Logger = None):

        if config_dict:  # 如果用户传入了config_dict，则使用用户提供的config
            self.config_dict = config_dict.get('baidu_ocr')
        else:  # 如果用户没有传入config_dict，则使用配置文件
            config_path = Path.cwd() / 'config.json'

            if not config_path.exists():
                raise Exception("配置文件不存在")

            with open(config_path, mode='r', encoding='utf8') as read_f:
                config_dict = json.load(read_f)
            self.config_dict = config_dict
        self.text_limit = self.config_dict.get('wechat', {}).get('text_limit', 520)
        # self.api_key = config_dict.get('api_key')
        self.api_key = self.config_dict.get('api_key')
        self.secret_key = self.config_dict.get('secret_key')

        if not self.api_key or not self.secret_key:
            raise Exception("配置文件中缺失api_key或secret_key配置")

        if logger:
            self.logger = logger
        else:
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.DEBUG)

            fmt = f'%(asctime)s.%(msecs)04d | %(levelname)8s | %(message)s'
            formatter = logging.Formatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S", )

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)

            logger.addHandler(console_handler)
            self.logger = logger

        self.ocr_host = {
            # 标准版
            'general_basic': "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token=",
            # 标准版（含位置）
            'general': "https://aip.baidubce.com/rest/2.0/ocr/v1/general?access_token=",
            # 高精度版
            'accurate_basic': "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic?access_token=",
            # 高精度版（含位置）
            'accurate': "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token=",
        }

    def get_access_token(self):
        """
        使用 AK，SK 生成鉴权签名（Access Token）
        :return: access_token，或是None(如果错误)
        """
        token_url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }

        try:
            response = requests.post(token_url, params=params)
            access_token = response.json().get("access_token")
            return access_token
        except Exception as e:
            self.logger.error("获取Access Token失败了！请检查api_key与secret_key。")

    @staticmethod
    def get_file_content_as_base64(img_path, urlencoded=False):
        """
        获取文件base64编码
        :param img_path: 文件路径
        :param urlencoded: 是否对结果进行urlencoded
        :return: base64编码信息
        """
        with open(img_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf8")
            if urlencoded:
                content = urllib.parse.quote_plus(content)

        return content

    @staticmethod
    def handler_text(response_json: dict):

        paragraphs_result = response_json.get('paragraphs_result')

        if not paragraphs_result:
            return response_json

        words_result = response_json.get('words_result')

        paragraphs = []

        for item in paragraphs_result:
            sentence = ''
            words_result_idx = item.get('words_result_idx')
            for idx in words_result_idx:
                word = words_result[idx].get('words')
                sentence += word
            paragraphs.append(sentence)

        return {'text': paragraphs}

    def base_ocr(self, ocr_type: str, data: dict) -> dict:
        # 获取鉴权token
        access_token = self.get_access_token()

        if not access_token:
            raise Exception("获取access_token失败，请检查api_key和secret_key")

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        if ocr_type not in self.ocr_host:
            return {}

        # OCR过程若出现错误，重试两次
        for i in range(3):
            try:
                ocr_host = self.ocr_host[ocr_type] + access_token
                encoded_data = urllib.parse.urlencode(data)
                response = requests.request("POST", ocr_host, headers=headers, data=encoded_data)

                return self.handler_text(response.json())
            except Exception as e:
                self.logger.error("orc过程出现错误", exc_info=True)

    def _by_image(self, ocr_type: str, img_path: str):
        if ocr_type not in self.ocr_host:
            return {}

        # 官方文档要求，图片需要先进行base64编码，之后对数据进行urlencoded处理
        img_data = self.get_file_content_as_base64(img_path, False)

        data = {
            # 以下参数四选一
            'image': img_data,  # 编码后的图片数据
            # 'url': '',  # 图片的url地址
            # 'ofd_file': '',  # OFD文件，base64编码后进行urlencode
            # 'pdf_file': '',  # PDF文件，base64编码后进行urlencode
            # 'pdf_file_num': '',  # 需要识别的PDF文件的对应页码
            'language_type': 'CHN_ENG',  # CHN_ENG：中英文混合；auto_detect，自动检测
            'detect_direction': 'false',  # 是否检测图像朝向，默认不检测
            'vertexes_location': 'false',  # 是否检测图像朝向，默认不检测
            'paragraph': 'true',  # 是否输出段落信息
            'probability': 'true',  # 是否返回识别结果中每一行的置信度
        }

        response = self.base_ocr(ocr_type, data)
        return response

    def _by_url(self, ocr_type: str, image_url: str):
        if ocr_type not in self.ocr_host:
            return {}

        data = {
            # 以下参数四选一
            # 'image': '',  # 编码后的图片数据
            'url': image_url,  # 图片的url地址
            # 'ofd_file': '',  # OFD文件，base64编码后进行urlencode
            # 'pdf_file': '',  # PDF文件，base64编码后进行urlencode
            # 'pdf_file_num': '',  # 需要识别的PDF文件的对应页码
            'language_type': 'CHN_ENG',  # CHN_ENG：中英文混合；auto_detect，自动检测
            'detect_direction': 'false',  # 是否检测图像朝向，默认不检测
            'vertexes_location': 'false',  # 是否检测图像朝向，默认不检测
            'paragraph': 'true',  # 是否输出段落信息
            'probability': 'true',  # 是否返回识别结果中每一行的置信度
        }

        response = self.base_ocr(ocr_type, data)
        return response

    def _by_pdf(self):
        pass

    def _by_ofd(self):
        pass

    def accurate_by_image(self, img_path):

        response = self._by_image('accurate', img_path)
        return response

    def accurate_by_url(self, img_url):
        response = self._by_url('accurate', img_url)
        return response

    def accurate_basic_by_image(self, img_path):
        """
        图像数据，base64编码后进行urlencode，
        要求base64编码和urlencode后大小不超过10M，
        最短边至少15px，最长边最大8192px，支持jpg/jpeg/png/bmp格式
        :param img_path:
        :return:
        """
        response = self._by_image('accurate_basic', img_path)
        return response

    def accurate_basic_by_url(self, img_url):
        """
        图片完整url，url长度不超过1024字节，
        url对应的图片base64编码后大小不超过10M，
        最短边至少15px，最长边最大8192px，
        支持jpg/jpeg/png/bmp格式
        :param img_url:
        :return:
        """
        response = self._by_url('accurate_basic', img_url)
        return response

    def general_basic_by_image(self, img_path):
        response = self._by_image('general_basic', img_path)
        return response

    def general_basic_by_url(self, img_url):
        response = self._by_url('general_basic', img_url)
        return response

    def general_by_image(self, img_path):
        response = self._by_image('general', img_path)
        return response

    def general_by_url(self, img_url):
        response = self._by_url('general', img_url)
        return response

    def split_text(self, text_list: list):
        merged_string = '\n\n'.join(text_list)  # 合并字符串
        if len(merged_string) <= self.text_limit:
            return [merged_string]  # 返回合并后的字符串作为单个元素的列表

        paragraph = ''
        paragraphs = []
        for index, sentence in enumerate(text_list):
            if len(paragraph + sentence) < self.text_limit:
                paragraph += f"{sentence}\n\n"
            else:
                paragraphs.append(paragraph)
                paragraph = sentence
        paragraphs.append(paragraph)
        return paragraphs
