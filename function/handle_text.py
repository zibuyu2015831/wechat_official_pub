# -*- coding: utf-8 -*-
import os
import re
import json
import logging
import base64
from Crypto.Cipher import AES
from basic.my_config import config
from basic.my_logging import MyLogging


class TextHandler(MyLogging):

    def __init__(self):
        super().__init__()
        self.config_dict = config
        self.key = self.config_dict.get('wechat', {}).get('password_key')
        self.sep_char = self.config_dict.get('wechat', {}).get('sep_char')

    @property
    def function_mapping(self):
        """
        调用名与函数的对应关系
        :return:
        """
        mapping_dict = {
            '加密': 'encrypt_oracle',
            '解密': 'decrypt_oracle',

            'ocr': 'picture_ocr',
            '图片转文本': 'picture_ocr',
            '图片转文字': 'picture_ocr',

            '语音转文件': 'voice_to_file',

            '退出': 'cancel_short_cmd',
            '取消': 'cancel_short_cmd',
        }
        return mapping_dict

    # str不是16的倍数那就补足为16的倍数
    @staticmethod
    def add_to_16(value):
        while len(value) % 16 != 0:
            value += '\0'
        return str.encode(value)  # 返回bytes

    # 加密方法
    def encrypt_oracle(self, reply_obj, unencrypted_content: str, key: str = None, *args, **kwargs):

        try:
            if not key:
                key = self.key

            text = base64.b64encode(unencrypted_content.encode('utf-8')).decode('ascii')
            # 初始化加密器
            aes = AES.new(self.add_to_16(key), AES.MODE_ECB)
            # 先进行aes加密
            encrypt_aes = aes.encrypt(self.add_to_16(text))
            # 用base64转成字符串形式
            encrypted_text = str(base64.encodebytes(encrypt_aes), encoding='utf-8')  # 执行加密并转码返回bytes

            return reply_obj.make_reply_text(encrypted_text)
        except Exception as e:
            return "加密出现错误，请重试！"

    # 解密方法
    def decrypt_oracle(self, reply_obj, encrypted_content: str, key: str = None, *args, **kwargs):

        try:
            if not key:
                key = self.key

            # 初始化加密器
            aes = AES.new(self.add_to_16(key), AES.MODE_ECB)
            # 优先逆向解密base64成bytes
            base64_decrypted = base64.decodebytes(encrypted_content.encode(encoding='utf-8'))
            # 执行解密密并转码返回str
            decrypted_text = str(aes.decrypt(base64_decrypted), encoding='utf-8')
            decrypted_text = base64.b64decode(decrypted_text.encode('utf-8')).decode('utf-8')

            return reply_obj.make_reply_text(decrypted_text)
        except Exception as e:
            return "解密出现错误，请检查key后重试！！"

    # 保存阿里云盘链接中的文件
    def store_ali_file(self, reply_obj, content: str, key: str = None, *args, **kwargs):
        """
        自动转存阿里云盘链接中的文件到自己网盘
        :param reply_obj:
        :param content:
        :param key:
        :param args:
        :param kwargs:
        :return:
        """
        ali_obj = kwargs.get('ali_obj')
        re_pattern = re.compile(self.config_dict.get('aliyun', {}).get('pattern'))
        # re_pattern = re.compile(r'https://www\.aliyundrive\.com/s/[a-zA-Z0-9]{9,13}')

        results = re_pattern.findall(content)
        for item in results:
            print(item)

    @staticmethod
    def short_cmd_reply(reply_obj, content: str, ):
        # 保存用户输入的短指令名称
        reply_obj.short_cmd = content
        # 保存新生成的会话信息
        reply_obj.save_user_data()

    # 图片OCR
    def picture_ocr(self, reply_obj, content: str, *args, **kwargs):
        self.short_cmd_reply(reply_obj, content)
        return reply_obj.make_reply_text(f"好的，我已经做好了{content}的准备，请您发送图片...")

    def voice_to_file(self, reply_obj, content: str, *args, **kwargs):
        self.short_cmd_reply(reply_obj, content)
        return reply_obj.make_reply_text(f"好的，我已经做好了{content}的准备，请您发送语音...")

    def cancel_short_cmd(self, reply_obj, content: str, *args, **kwargs):
        reply_obj.short_cmd = '无'
        # 保存新生成的会话信息
        reply_obj.save_user_data()
        return reply_obj.make_reply_text(f"已退出短指令模式...")


if __name__ == '__main__':
    h = TextHandler({
        "aliyun": {
            "pattern": "https://www.aliyundrive.com/s/[a-zA-Z0-9]{9,13}"
        }
    })
    text = """
        「G 古墓丽影 (系列3部) 4K HDR  DV...音轨 内封特效 FRDS 蓝光版」https://www.aliyundrive.com/s/Wwgu7WstPDy
        「G 哥斯拉系列.2160p.HDR.国英音轨.内封特效【系列合集」https://www.aliyundrive.com/s/LMQMfFh27Fc
        「G 攻壳机动队(2017) 4K原盘 国英音轨 特效字幕 」https://www.aliyundrive.com/s/KGzmzJFVqwW
        「W 危情十日 (1990) 4K HDR 国英双...轨 默认英语 中字外挂 内嵌字幕」https://www.aliyundrive.com/s/LG3bzPJbgXz
        「Z 芝加哥七君子审判(2020)4K NF 内封中字」https://www.aliyundrive.com/s/QYd4DdzpNbB
        「T 天兆(2002) 1080P REMUX 外挂中字 」https://www.aliyundrive.com/s/o4DBUfBHK36
            """
