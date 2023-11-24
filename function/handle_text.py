# -*- coding: utf-8 -*-
import re
import time
import uuid
import base64
import requests
import threading
from Crypto.Cipher import AES
from .config import MyConfig
from .handle_post import ReplyHandler


class TextHandler(MyConfig):

    def __init__(self):
        super().__init__()

        self.key = self.config.get('wechat', {}).get('password_key')
        self.sep_char = self.config.get('wechat', {}).get('sep_char')

    @property
    def function_mapping(self) -> dict:
        """
        调用名与函数的对应关系
        :return:
        """
        mapping_dict = {
            # 以下为短指令功能
            '加密': 'encrypt_oracle',
            '解密': 'decrypt_oracle',

            '文本转语音': 'text_to_voice',
            '文字转语音': 'text_to_voice',
            '配音': 'text_to_voice',

            # 以下为指令功能
            'ocr': 'picture_ocr',
            '图片转文本': 'picture_ocr',
            '图片转文字': 'picture_ocr',

            # 退出指令功能
            '退出': 'cancel_short_cmd',
            '取消': 'cancel_short_cmd',
        }
        return mapping_dict

    @staticmethod
    def generate_short_uuid(num: int = 5) -> str:
        """
        返回指定位数的随机字符串
        :param num: 将生成的随机字符串的位数
        :return:
        """
        return str(uuid.uuid4())[:num]

    # str不是16的倍数那就补足为16的倍数
    @staticmethod
    def add_to_16(value) -> bytes:
        while len(value) % 16 != 0:
            value += '\0'
        return str.encode(value)  # 返回bytes

    # 加密方法
    def encrypt_oracle(self, reply_obj: ReplyHandler, content: str, key: str = None, *args, **kwargs) -> str:

        try:
            if not key:
                key = self.key

            text = base64.b64encode(content.encode('utf-8')).decode('ascii')
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
    def decrypt_oracle(self, reply_obj: ReplyHandler, content: str, key: str = None, *args, **kwargs) -> str:

        try:
            if not key:
                key = self.key

            # 初始化加密器
            aes = AES.new(self.add_to_16(key), AES.MODE_ECB)
            # 优先逆向解密base64成bytes
            base64_decrypted = base64.decodebytes(content.encode(encoding='utf-8'))
            # 执行解密密并转码返回str
            decrypted_text = str(aes.decrypt(base64_decrypted), encoding='utf-8')
            decrypted_text = base64.b64decode(decrypted_text.encode('utf-8')).decode('utf-8')

            return reply_obj.make_reply_text(decrypted_text)
        except Exception as e:
            return "解密出现错误，请检查key后重试！！"

    def _submit_text_to_voice_mission(self, data, make_voice_url):
        try:
            self.logger.info("提交文本转语音任务")
            response = requests.post(make_voice_url, json=data)

        except Exception as e:
            self.logger.error("文本转语音任务提交失败！", exc_info=True)

    def text_to_voice(self, reply_obj: ReplyHandler, content: str, key: str = None, *args, **kwargs) -> str:
        voice_list = self.config.get('wechat', {}).get('voice_list', {})
        voice_choice = voice_list.get(key)

        if not voice_choice:
            voice_choice = "zh-CN-XiaoxiaoNeural"

        # 随机字符串，该字符串作为获取结果的关键字
        random_str = self.generate_short_uuid(7)

        # 保存的文件名，为了防止重名，也添加上字符串
        file_name = f"{reply_obj.to_user_id}" + '-' + random_str

        make_voice_url = self.config.get('wechat', {}).get('make_voice_url', '')

        if not make_voice_url:
            return '文本转语音功能未配置！'

        data = {
            "lanzou_cookie": self.config.get('lanzou_cookies'),
            'text': content,
            'voice_choice': voice_choice,
            'file_name': file_name,
            'random_str': random_str,
            "user_wechat_id": reply_obj.to_user_id,
            "user_file_id": reply_obj.ali_user_file_id,
            "user_file_download_url": reply_obj.ali_user_file_download_url
        }

        save_content_thread = threading.Thread(target=self._submit_text_to_voice_mission, args=(data, make_voice_url))
        save_content_thread.start()
        time.sleep(0.1)  # 让子线程运行一会，但不必等待结果
        reply_obj.voice2text_keyword[random_str] = "程序执行中，请稍后获取......"

        reply_obj._save_user_data()

        return reply_obj.make_reply_text(f"已提交【文本转语音】任务\n\n请稍等1分钟后，回复【{random_str}】获取结果")

    # 保存阿里云盘链接中的文件
    def store_ali_file(self, reply_obj: ReplyHandler, content: str, key: str = None, *args, **kwargs):
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
        re_pattern = re.compile(self.config.get('aliyun', {}).get('pattern'))
        # re_pattern = re.compile(r'https://www\.aliyundrive\.com/s/[a-zA-Z0-9]{9,13}')

        results = re_pattern.findall(content)
        for item in results:
            print(item)

    @staticmethod
    def short_cmd_reply(reply_obj: ReplyHandler, content: str):
        # 保存用户输入的短指令名称
        reply_obj.short_cmd = content
        # 保存新生成的会话信息
        reply_obj._save_user_data()

    # 图片OCR
    def picture_ocr(self, reply_obj: ReplyHandler, content: str, *args, **kwargs):
        self.short_cmd_reply(reply_obj, content)
        return reply_obj.make_reply_text(f"-----已进入指令模式-----\n\n我已经做好了{content}的准备，请您发送图片...")

    def cancel_short_cmd(self, reply_obj: ReplyHandler, content: str, *args, **kwargs):
        reply_obj.short_cmd = '无'
        # 保存新生成的会话信息
        reply_obj._save_user_data()
        return reply_obj.make_reply_text(f"-----已退出指令模式-----")


if __name__ == '__main__':
    my_text = """
        「G 古墓丽影 (系列3部) 4K HDR  DV...音轨 内封特效 FRDS 蓝光版」https://www.aliyundrive.com/s/Wwgu7WstPDy
        「G 哥斯拉系列.2160p.HDR.国英音轨.内封特效【系列合集」https://www.aliyundrive.com/s/LMQMfFh27Fc
        「G 攻壳机动队(2017) 4K原盘 国英音轨 特效字幕 」https://www.aliyundrive.com/s/KGzmzJFVqwW
        「W 危情十日 (1990) 4K HDR 国英双...轨 默认英语 中字外挂 内嵌字幕」https://www.aliyundrive.com/s/LG3bzPJbgXz
        「Z 芝加哥七君子审判(2020)4K NF 内封中字」https://www.aliyundrive.com/s/QYd4DdzpNbB
        「T 天兆(2002) 1080P REMUX 外挂中字 」https://www.aliyundrive.com/s/o4DBUfBHK36
            """
