# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/12/4
contact: 【公众号】思维兵工厂
description: 【关键词回复功能】 笔记转存功能
--------------------------------------------
"""

import time
import requests
import threading
from typing import TYPE_CHECKING

from ..config import config, pro_logger
from ..types import WechatReplyData
from .base import WeChatKeyword, register_function

if TYPE_CHECKING:
    from ..handle_post import BasePostHandler

FUNCTION_DICT = dict()
FIRST_FUNCTION_DICT = dict()


def send_save_note_request(note_url: str, yun_func_token: str, yun_func_url: str, note_path: str):
    """发送转存笔记请求"""

    config.is_debug and pro_logger.debug(f'开始发送转存笔记的请求：【{note_url}】')

    data = {
        "token": yun_func_token or "",
        "note_url": note_url,
        "save_note_path": note_path,
    }

    yun_func_url = yun_func_url.strip()
    if not yun_func_url.endswith('/upload_note'):
        yun_func_url = yun_func_url + '/upload_note'

    requests.post(yun_func_url, json=data)


class KeywordFunction(WeChatKeyword):
    model_name = "save_to_note"

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['笔记', '收藏', '收藏笔记', '转存笔记'], is_first=False,
                       function_intro='根据链接获取HTML内容，转存为笔记')
    def save_to_note(self, content: str, *args, **kwargs):
        """根据链接获取HTML内容，转存为笔记"""

        post_handler: BasePostHandler = kwargs.get('post_handler')

        note_path = kwargs.get('key') or post_handler.wechat_user.note_path

        if not post_handler.wechat_user.note_url:
            return WechatReplyData(
                msg_type='text',
                content='请先设置笔记保存地址，再进行笔记保存操作！'
            )

        if not content:
            return WechatReplyData(
                msg_type='text',
                content='请输入需要转存笔记的网址链接！'
            )

        if not self.is_valid_url(content):
            return WechatReplyData(
                msg_type='text',
                content='输入内容并非网址链接，请检查！'
            )

        t1 = threading.Thread(target=send_save_note_request, kwargs={
            'note_url': content,
            'yun_func_token': post_handler.wechat_user.note_token or '',
            'yun_func_url': post_handler.wechat_user.note_url,
            'note_path': note_path or ''
        })

        t1.start()
        time.sleep(0.1)  # 给线程1毫秒执行

        return WechatReplyData(
            msg_type='text',
            content='笔记保存中，请稍等...'
        )

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['设置笔记路径', '设置笔记保存路径', '笔记路径', '设置笔记上传路径'], is_first=False,
                       function_intro='设置笔记上传路径，默认将笔记保存到【000_cloud_note】文件夹下')
    def set_note_path(self, content: str, *args, **kwargs) -> WechatReplyData:
        """设置笔记上传路径：即笔记保存到obsidian哪个文件夹下"""

        post_handler: BasePostHandler = kwargs.get('post_handler')
        obj = WechatReplyData(msg_type="text", content=f"---笔记路径设置失败---")

        try:

            post_handler.wechat_user.note_path = content
            post_handler.database.session.commit()
            obj.content = f"---笔记路径设置成功---"

            config.is_debug and self.logger.info(
                f'已将用户【{post_handler.request_data.to_user_id}】的笔记路径设置为【{content}】'
            )

        except:
            obj.content = f"---笔记路径设置失败：未知错误---"
            self.logger.error('set_note_path方法出现错误', exc_info=True)
        finally:
            return obj

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['设置笔记token', '设置笔记密钥', '笔记密钥', '笔记token'], is_first=False,
                       function_intro='设置您个人的笔记token')
    def set_note_token(self, content: str, *args, **kwargs) -> WechatReplyData:
        """设置独属于用户个人的笔记token"""

        post_handler: BasePostHandler = kwargs.get('post_handler')
        obj = WechatReplyData(msg_type="text", content=f"---笔记密钥设置失败---")

        try:

            post_handler.wechat_user.note_token = content
            post_handler.database.session.commit()
            obj.content = f"---笔记密钥设置成功---"

            config.is_debug and self.logger.info(
                f'已将用户【{post_handler.request_data.to_user_id}】的笔记密钥设置为【{content}】'
            )

        except:
            obj.content = f"---笔记密钥设置失败：未知错误---"
            self.logger.error('set_note_token方法出现错误', exc_info=True)
        finally:
            return obj

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['设置笔记地址', '笔记地址', '绑定笔记地址'], is_first=False,
                       function_intro='设置您个人的笔记地址')
    def set_note_home(self, content: str, *args, **kwargs) -> WechatReplyData:
        """设置独属于用户个人的笔记地址"""

        post_handler: BasePostHandler = kwargs.get('post_handler')
        obj = WechatReplyData(msg_type="text", content=f"---笔记地址设置失败---")

        if not self.is_valid_url(content):
            obj.content = obj.content + "\n\n" + "输入的网址链接有误，请检查！"
            return obj

        try:

            post_handler.wechat_user.note_url = content
            post_handler.database.session.commit()
            obj.content = f"---笔记地址设置成功---\n\n如果你设置了请求token，也需要设置笔记密钥哦~"

            config.is_debug and self.logger.info(
                f'已将用户【{post_handler.request_data.to_user_id}】的笔记地址设置为【{content}】'
            )

        except Exception:
            obj.content = f"---笔记地址设置失败：未知错误---"
            self.logger.error('set_note_home方法出现错误', exc_info=True)
        finally:
            return obj

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['查看笔记token', '我的笔记token', '查看笔记密钥', '我的笔记密钥'], is_first=True)
    def get_note_token(self, content: str, *args, **kwargs) -> WechatReplyData:
        post_handler: BasePostHandler = kwargs.get('post_handler')
        obj = WechatReplyData(msg_type="text", content="")

        if not post_handler.wechat_user.note_token:
            obj.content = '您还没有设置笔记地址，请先设置笔记地址！'
        else:
            obj.content = f'您当前的笔记地址为：\n\n{post_handler.wechat_user.note_token}'

        return obj

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['查看笔记地址', '我的笔记地址', ], is_first=True)
    def get_note_url(self, content: str, *args, **kwargs) -> WechatReplyData:
        post_handler: BasePostHandler = kwargs.get('post_handler')
        obj = WechatReplyData(msg_type="text", content="")

        if not post_handler.wechat_user.note_url:
            obj.content = '您还没有设置笔记地址，请先设置笔记地址！'
        else:
            obj.content = f'您当前的笔记地址为：\n\n{post_handler.wechat_user.note_url}'

        return obj

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['笔记', '收藏', '收藏笔记', '转存笔记'], is_first=True)
    def correct_save_to_note(self, content: str, *args, **kwargs) -> WechatReplyData:

        msg = f"""👉指令名称：{content}；
👉参数要求：需携带两个参数；
👉使用注意：以三个减号（---）分隔参数。

🌱示例🌱
输入【{content}---URL链接】，自动转存该网页到设定的笔记地址中；该功能需要先设定笔记地址。"""
        return WechatReplyData(msg_type="text", content=self.command_intro_title.format(msg))

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['设置笔记token', '设置笔记密钥', '笔记密钥', '笔记token'], is_first=True)
    def correct_set_note_token(self, content: str, *args, **kwargs) -> WechatReplyData:
        msg = f"""👉指令名称：{content}；
👉参数要求：需携带两个参数；
👉使用注意：以三个减号（---）分隔参数。

🌱示例🌱
输入【{content}---笔记token】，添加访问笔记地址时所需的token，增加转存笔记的安全性。"""
        return WechatReplyData(msg_type="text", content=self.command_intro_title.format(msg))

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['设置笔记地址', '笔记地址', '绑定笔记地址'], is_first=True)
    def correct_set_note_home(self, content: str, *args, **kwargs) -> WechatReplyData:
        msg = f"""👉指令名称：{content}；
👉参数要求：需携带两个参数；
👉使用注意：以三个减号（---）分隔参数。

🌱示例🌱
输入【{content}---笔记地址URL】，设定独属于您的笔记地址，用于转存笔记。"""
        return WechatReplyData(msg_type="text", content=self.command_intro_title.format(msg))


def add_keyword_function(*args, **kwargs):
    obj = KeywordFunction(*args, **kwargs)
    return {obj: FUNCTION_DICT}


def add_first_keyword_function(*args, **kwargs):
    obj = KeywordFunction(*args, **kwargs)
    return {obj: FIRST_FUNCTION_DICT}
