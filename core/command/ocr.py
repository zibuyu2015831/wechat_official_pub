# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: mind_workshop
author: 子不语
date: 2024/4/25
contact: 【公众号】思维兵工厂
description: 【关键词回复功能】 图片转文本功能
--------------------------------------------
"""

import time
from typing import TYPE_CHECKING

from ..config import config
from ..models import KeyWord
from ..types import WechatReplyData
from ..utils.api_baidu import BaiduOCR
from .base import WeChatKeyword, register_function

if TYPE_CHECKING:
    from ..handle_post import BasePostHandler

FUNCTION_DICT = dict()
FIRST_FUNCTION_DICT = dict()


class KeywordFunction(WeChatKeyword):
    model_name = "ocr"
    command = '图片转文本'

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['图片转文本', '图片转文字', 'ocr', '图片识别', '图片文字识别'], is_first=True,
                       function_intro='识别输入的图片，转为文本')
    def picture_ocr(self, content: str, *args, **kwargs) -> WechatReplyData:
        """
        记录进入指令模式：图片OCR
        :param content:
        :param args:
        :param kwargs:
        :return:
        """

        if not config.baidu_config.is_valid():
            return WechatReplyData(
                msg_type="text",
                content=f"---尚未完成百度OCR配置---"
            )

        post_handler: BasePostHandler = kwargs.get('post_handler')

        if not post_handler.current_command:
            # 注意这里的command参数，传入的值得是 commands 列表中的值
            result = self.save_command_keyword(post_handler=post_handler, command=self.command)

            if not result:
                return WechatReplyData(
                    msg_type="text",
                    content=f"---进入指令失败---\n\n当前没法处理【{content}】指令，请联系管理员..."
                )

            return WechatReplyData(
                msg_type="text",
                content=f"---已进入指令模式---\n\n我已经做好了【{content}】的准备，请您发送图片..."
            )

        # 处理图片转文本逻辑
        if post_handler.current_command and post_handler.current_command == self.command:
            image_url = post_handler.request_data.pic_url
            media_id = post_handler.request_data.media_id
            content = post_handler.request_data.content

            return self.ocr_one_pic(
                image_url=image_url,
                media_id=media_id,
                content=content,
                post_handler=post_handler,
            )

        return WechatReplyData(
            msg_type="text",
            content=f"---【严重错误】内部指令混乱---"
        )

    def ocr_one_pic(self, image_url: str, media_id: str, content: str,
                    post_handler: "BasePostHandler") -> WechatReplyData:
        """
        OCR一张图片，该图片由微信参数中的PicUrl获取
        :param image_url: 用户发送图片时，图片的url地址
        :param media_id: 用户发送图片时，图片的media_id
        :param content: 用户发送文本时，文本内容
        :param post_handler:
        :return:
        """

        result = self.check_is_cancel_command(content, post_handler)
        if result:
            return result

        if content and self.is_valid_url(content):
            image_url = content

        if not image_url:
            return WechatReplyData(
                msg_type="text",
                content='您当前处于【图片转文本】指令，请发送图片；\n\n返回主页可输入【退出】'
            )

        # TODO  后续考虑保存图片
        # short_uuid = self.ramdom_code(7)  # 获取随机5位数的字符串
        # image_title = f"{datetime.datetime.today().strftime('%Y%m%d')}-{short_uuid}.jpg"

        for i in range(3):
            try:
                config.is_debug and self.logger.info(f"开始ocr图片，该图片链接为：【{image_url}】")
                config.is_debug and self.logger.info(f"该图片的media_id为：【{media_id}】")

                ocr_obj = BaiduOCR(
                    api_key=config.baidu_config.api_key,
                    secret_key=config.baidu_config.secret_key,
                    logger=self.logger
                )

                # 如果ocr成功，返回的是包含文本的字典；失败则返回原json
                text_dict = ocr_obj.accurate_basic_by_url(image_url)

                text_list = text_dict.get('text')

                if not text_list:
                    return WechatReplyData(
                        msg_type="text",
                        content="OCR过程出现错误，请检查图片。\n\n图片要求：\n\n1. 图片最短边至少15px，最长边最大8192px；\n2. 仅支持jpg/jpeg/png/bmp格式"
                    )

                config.is_debug and self.logger.info("成功完成图片OCR")

                # TODO 后续考虑保存OCR结果
                # store_ocr_result.delay(self.user_unique_key, image_title, "\n\n".join(text_list))

                # 由于微信限制，文本回复不得超过600字，所以将内容进行分段。
                paragraphs = ocr_obj.split_text(text_list)

                if len(paragraphs) == 1:
                    reply = paragraphs[0]
                else:
                    reply = self.make_ocr_info(paragraphs, post_handler)

                return WechatReplyData(
                    msg_type="text",
                    content=reply
                )

            except:
                config.is_debug and self.logger.error(f"ocr图片过程中可能出现网络错误，即将重试...", exc_info=True)

        # 没有成功完成ocr，也需要返回内容
        return WechatReplyData(
            msg_type="text",
            content='ocr过程出现错误，请联系管理员'
        )

    @staticmethod
    def make_ocr_info(paragraphs, post_handler: "BasePostHandler"):
        """
        处理生成的OCR结果：分段
        :param paragraphs:
        :param post_handler:
        :return:
        """

        length = len(paragraphs)

        page_list = []

        current_timestamp = int(time.time())
        expire_time = current_timestamp + config.command_expire_time

        for i in range(length):
            page_list.append(f"【获取ocr结果第{i + 1}页】")

            keyword_obj = KeyWord(
                keyword='【获取ocr结果第{i + 1}页】',
                reply_content=paragraphs[i],
                reply_type='text',
                official_user_id=post_handler.request_data.to_user_id,
                expire_time=expire_time
            )

            post_handler.database.session.add(keyword_obj)
        post_handler.database.session.commit()

        all_page = "\n".join(page_list)
        info = f'{paragraphs[0]} - - - - - - - - - - - - - - - - \n\n该文本较长，仅显示第一页\n\n可输入以下命令，获取后续：\n' + all_page

        return info


def add_keyword_function(*args, **kwargs):
    obj = KeywordFunction(*args, **kwargs)
    return {obj: FUNCTION_DICT}


def add_first_keyword_function(*args, **kwargs):
    obj = KeywordFunction(*args, **kwargs)
    return {obj: FIRST_FUNCTION_DICT}
