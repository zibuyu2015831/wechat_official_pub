# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: mind_workshop
author: 子不语
date: 2024/4/25
contact: 【公众号】思维兵工厂
description: 【关键词回复功能】 文字转语音功能
--------------------------------------------
"""

import time
import requests
import threading
from typing import Dict, TYPE_CHECKING

from .base import WeChatKeyword, register_function
from ..config import config, pro_logger
from ..types import WechatReplyData
from ..models import KeyWord

if TYPE_CHECKING:
    from ..handle_post import BasePostHandler

FUNCTION_DICT = dict()
FIRST_FUNCTION_DICT = dict()


class KeywordFunction(WeChatKeyword):
    model_name = "text_to_voice"

    ms_voice_dict = {
        '晓晓': {'key': 'zh-CN-XiaoxiaoNeural', 'intro': '女声，普通话', 'language': 'cn'},
        '小伊': {'key': 'zh-CN-XiaoyiNeural', 'intro': '女声，普通话', 'language': 'cn'},
        '云健': {'key': 'zh-CN-YunjianNeural', 'intro': '男声，普通话', 'language': 'cn'},
        '小希': {'key': 'zh-CN-YunxiNeural', 'intro': '男声，普通话', 'language': 'cn'},
        '云夏': {'key': 'zh-CN-YunxiaNeural', 'intro': '女声，普通话', 'language': 'cn'},
        '云阳': {'key': 'zh-CN-YunyangNeural', 'intro': '男声，普通话', 'language': 'cn'},
        '小贝': {'key': 'zh-CN-liaoning-XiaobeiNeural', 'intro': '女声，普通话', 'language': 'cn'},
        '小妮': {'key': 'zh-CN-shaanxi-XiaoniNeural', 'intro': '女声，普通话', 'language': 'cn'},
        '惠艾': {'key': 'zh-HK-HiuGaaiNeural', 'intro': '女声，粤语', 'language': 'cn'},
        '惠安': {'key': 'zh-HK-HiuMaanNeural', 'intro': '女声，粤语', 'language': 'cn'},
        '王伦': {'key': 'zh-HK-WanLungNeural', 'intro': '男声，粤语', 'language': 'cn'},
        '云晨': {'key': 'zh-TW-HsiaoChenNeural', 'intro': '女声，普通话', 'language': 'cn'},
        '云余': {'key': 'zh-TW-HsiaoYuNeural', 'intro': '女声，普通话', 'language': 'cn'},
        '云和': {'key': 'zh-TW-YunJheNeural', 'intro': '男声，普通话', 'language': 'cn'},

        'Mitchell': {'key': 'en-NZ-MitchellNeural', 'intro': '男声，英语', 'language': 'en'},
        'Molly': {'key': 'en-NZ-MollyNeural', 'intro': '女声，英语', 'language': 'en'},
        'Libby': {'key': 'en-GB-LibbyNeural', 'intro': '女声，英语', 'language': 'en'},
        'Maisie': {'key': 'en-GB-MaisieNeural', 'intro': '女声，英语', 'language': 'en'},
        'Ryan': {'key': 'en-GB-RyanNeural', 'intro': '男声，英语', 'language': 'en'},
        'Sonia': {'key': 'en-GB-SoniaNeural', 'intro': '女声，英语', 'language': 'en'},
        'Thomas': {'key': 'en-GB-ThomasNeural', 'intro': '男声，英语', 'language': 'en'},
        'Ana': {'key': 'en-US-AnaNeural', 'intro': '女声，英语', 'language': 'en'},
        'Aria': {'key': 'en-US-AriaNeural', 'intro': '女声，英语', 'language': 'en'},
        'Christopher': {'key': 'en-US-ChristopherNeural', 'intro': '男声，英语', 'language': 'en'},
        'Eric': {'key': 'en-US-EricNeural', 'intro': '男声，英语', 'language': 'en'},
        'Guy': {'key': 'en-US-GuyNeural', 'intro': '男声，英语', 'language': 'en'},
        'Jenny': {'key': 'en-US-JennyNeural', 'intro': '女声，英语', 'language': 'en'},
        'Michelle': {'key': 'en-US-MichelleNeural', 'intro': '女声，英语', 'language': 'en'},
        'Roger': {'key': 'en-US-RogerNeural', 'intro': '男声，英语', 'language': 'en'},
        'Steffan': {'key': 'en-US-SteffanNeural', 'intro': '男声，英语', 'language': 'en'},
        'Natasha': {'key': 'en-AU-NatashaNeural', 'intro': '女声，英语', 'language': 'en'},
        'William': {'key': 'en-AU-WilliamNeural', 'intro': '男声，英语', 'language': 'en'},
        'Sam': {'key': 'en-HK-SamNeural', 'intro': '男声，英语', 'language': 'en'},
        'Yan': {'key': 'en-HK-YanNeural', 'intro': '女声，英语', 'language': 'en'},
        'Clara': {'key': 'en-CA-ClaraNeural', 'intro': '女声，英语', 'language': 'en'},
        'Liam': {'key': 'en-CA-LiamNeural', 'intro': '男声，英语', 'language': 'en'}
    }

    @staticmethod
    def submit_tts_task(data: Dict) -> bool:

        try:
            if not config.yun_func_tts_config.func_url:
                config.is_debug and pro_logger.error(f"[文本转语音] 未配置云函数URL，调用失败")
                return False

            result = requests.post(config.yun_func_tts_config.func_url, json=data)

            config.is_debug and pro_logger.info(f"[文本转语音] 云函数调用结果：{result.text}")
            config.is_debug and pro_logger.info(f"[文本转语音] 云函数调用成功")
        except:
            config.is_debug and pro_logger.error(f"[文本转语音] 云函数调用失败", exc_info=True)
            return True

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['文本转语音', '文字转语音', '配音'], is_first=False,
                       function_intro='将输入文本转化为音频，可下载')
    def text_to_voice(self, content: str, *args, **kwargs):
        """文本转语音---文本内容：返回语音任务id，可根据id获取音频链接"""

        post_handler:BasePostHandler = kwargs.get('post_handler')
        file_name = self.ramdom_code()  # 随机生成文件名

        if not content:
            return WechatReplyData(msg_type="text", content="请输入文本内容")

        # 1. 根据文本的语种确定音色
        key = kwargs.get('key')
        if self.is_en_text(content):
            voice_choice = config.yun_func_tts_config.default_en_voice or "en-GB-SoniaNeural"
            if key and self.ms_voice_dict.get(key).get('key'):
                voice_choice = self.ms_voice_dict.get(key).get('key')
        elif self.is_zh_text(content) or self.is_zh_and_en_text(content):
            voice_choice = config.yun_func_tts_config.default_zh_voice or "zh-CN-XiaoxiaoNeural"
            if key and self.ms_voice_dict.get(key).get('key'):
                voice_choice = self.ms_voice_dict.get(key).get('key')
        else:
            return WechatReplyData(msg_type="text", content="请检查文本，配音功能目前仅支持中文与英文~")

        # 2. 向数据库写入关键词回复
        current_timestamp = int(time.time())
        expires = current_timestamp + config.yun_func_tts_config.expires

        keyword_obj = KeyWord(
            official_user_id=post_handler.request_data.to_user_id,
            keyword=file_name,
            reply_content=f"配音任务正在进行，请稍等...",
            reply_type="text",
            expire_time=expires,
        )

        post_handler.database.session.add(keyword_obj)
        post_handler.database.session.commit()

        # 3. 提交配音任务——云函数
        data = {
            'official_user_id': post_handler.request_data.to_user_id,
            "voice_choice": voice_choice,
            "text": content,
            "file_name": file_name,
            'token': config.yun_func_tts_config.func_token,
        }

        thread1 = threading.Thread(target=self.submit_tts_task, args=(data,))
        thread1.start()

        # 4. 小等一会，让线程执行，但不必等待任务完成
        time.sleep(0.3)

        return WechatReplyData(
            msg_type="text",
            content=f"已提交【文本转语音】任务\n\n请稍等一会后，回复【{file_name}】获取音频链接"
        )

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['文本转语音', '文字转语音', '配音'], is_first=True)
    def correct_text_to_voice(self, content: str, *args, **kwargs):
        """当用户输入“配音、文本转语音、文字转语音”等短指令而没有携带参数时，给出示例提示"""

        msg = f"""👉指令名称：{content}；
👉参数要求：需携带参数；
👉使用注意：以三个减号（---）分隔参数。

f"🌱示例🌱
输入【{content}---需要配音的文本】"""

        return WechatReplyData(msg_type="text", content=self.command_intro_title.format(msg))


def add_keyword_function(*args, **kwargs):
    obj = KeywordFunction(*args, **kwargs)
    return {obj: FUNCTION_DICT}


def add_first_keyword_function(*args, **kwargs):
    obj = KeywordFunction(*args, **kwargs)
    return {obj: FIRST_FUNCTION_DICT}
