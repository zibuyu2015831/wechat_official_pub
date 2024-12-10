# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: mind_workshop
author: 子不语
date: 2024/4/24
contact: 【公众号】思维兵工厂
description: 【关键词回复功能】文本的加密解密功能
--------------------------------------------
"""

import base64
from typing import TYPE_CHECKING
from Crypto.Cipher import AES
from ..types import WechatReplyData
from .base import register_function, WeChatKeyword

if TYPE_CHECKING:
    from ..handle_post import BasePostHandler

FUNCTION_DICT = dict()
FIRST_FUNCTION_DICT = dict()


class KeywordFunction(WeChatKeyword):
    model_name = "text_oracle"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.key = self.config.encrypt_key  # 用于文本加密、解密的key

        self.sep_char = self.config.wechat_config.sep_char or '---'

    @staticmethod
    def add_to_16(value) -> bytes:
        """如果字符串位数不是16的倍数，补足为16的倍数"""

        while len(value) % 16 != 0:
            value += '\0'
        return str.encode(value)  # 返回bytes

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['加密文本', '文本加密', '加密'], function_intro='加密一段文本')
    def encrypt_oracle(self, content: str, *args, **kwargs) -> WechatReplyData:
        """加密---待解密文本---key（可选）：加密文本"""

        try:

            # 如果用户没有传入key，则使用用户的id作为key
            post_handler: BasePostHandler = kwargs.get('post_handler')
            key = kwargs.get('key') or post_handler.wechat_user.official_user_id or self.key

            # key = kwargs.get('key') or self.key

            text = base64.b64encode(content.encode('utf-8')).decode('ascii')
            # 初始化加密器
            aes = AES.new(self.add_to_16(key), AES.MODE_ECB)
            # 先进行aes加密
            encrypt_aes = aes.encrypt(self.add_to_16(text))
            # 用base64转成字符串形式
            encrypted_text = str(base64.encodebytes(encrypt_aes), encoding='utf-8').strip()  # 执行加密并转码返回bytes

            return WechatReplyData(msg_type="text", content=encrypted_text, )

        except Exception:
            self.logger.error("加密出现错误。", exc_info=True)
            obj = WechatReplyData(
                msg_type="text",
                content="加密出现错误，请重试！",
            )

            return obj

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['解密文本', '文本解密', '解密'], function_intro='解密由本公众号加密的文本')
    def decrypt_oracle(self, content: str, *args, **kwargs) -> WechatReplyData:
        """解密---待解密文本---key（可选）：解密文本"""

        try:

            # 如果用户没有传入key，则使用用户的id作为key
            post_handler: BasePostHandler = kwargs.get('post_handler')
            key = kwargs.get('key') or post_handler.wechat_user.official_user_id or self.key

            # key = kwargs.get('key') or self.key

            # 初始化加密器
            aes = AES.new(self.add_to_16(key), AES.MODE_ECB)
            # 优先逆向解密base64成bytes
            base64_decrypted = base64.decodebytes(content.encode(encoding='utf-8'))
            # 执行解密密并转码返回str
            decrypted_text = str(aes.decrypt(base64_decrypted), encoding='utf-8')
            decrypted_text = base64.b64decode(decrypted_text.encode('utf-8')).decode('utf-8')

            obj = WechatReplyData(
                msg_type="text",
                content=decrypted_text,
            )

            return obj

        except Exception:
            self.logger.error("解密出现错误。", exc_info=True)

            obj = WechatReplyData(
                msg_type="text",
                content="解密出现错误，请检查key后重试！！",
                media_id=""
            )

            return obj

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['加密文本', '文本加密', '加密'], is_first=True)
    def correct_encrypt_oracle(self, content: str, *args, **kwargs) -> WechatReplyData:
        """当用户输入“加密、加密文本”等短指令而没有携带参数时，给出示例提示"""

        msg = f"""👉指令名称：{content}；
👉参数要求：需携带参数；
👉使用注意：以三个减号（---）分隔参数。

🌱示例🌱
输入【{content}---需要加密的文本】，将返回加密后的文本。

该指令默认以系统密钥对文本进行加密，如果想自定义密钥，可以通过第二参数传递。

🌱示例🌱
【{content}---需要加密的文本---自己的密钥】

🌱注意🌱
密钥必须由字母、数字或特殊字符组成，不能包含中文。指定加密密钥，则解密也需使用该密钥。"""

        return WechatReplyData(msg_type="text", content=self.command_intro_title.format(msg))

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['解密文本', '文本解密', '解密'], is_first=True)
    def correct_decrypt_oracle(self, content: str, *args, **kwargs) -> WechatReplyData:
        """当用户输入“解密、解密文本”等短指令而没有携带参数时，给出示例提示"""

        msg = f"""👉指令名称：{content}；
👉参数要求：需携带参数；
👉使用注意：以三个减号（---）分隔参数。

🌱示例🌱
输入【{content}---需要解密的文本】，将返回解密后的文本。

该指令默认以系统密钥对文本进行解密，如果加密文本是由自定义密钥加密的，需通过第二参数传递密钥。否则将解密失败。

🌱示例🌱
【{content}---需要解密的文本---自己的密钥】

🌱注意🌱
密钥必须由字母、数字或特殊字符组成，不能包含中文。"""

        return WechatReplyData(msg_type="text", content=self.command_intro_title.format(msg))


def add_keyword_function(*args, **kwargs):
    obj = KeywordFunction(*args, **kwargs)
    return {obj: FUNCTION_DICT}


def add_first_keyword_function(*args, **kwargs):
    obj = KeywordFunction(*args, **kwargs)
    return {obj: FIRST_FUNCTION_DICT}
