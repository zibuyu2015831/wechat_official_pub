# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/11/20
contact: 【公众号】思维兵工厂
description: 处理微信消息

get方法处理get请求，主要是微信验证接口有效性;
post方法处理post请求;
--------------------------------------------
"""

import hashlib
import xmltodict
from flask import Request
from typing import Optional

from .types import ConfigData
from .config import pro_logger
from .handle_post import PostHandler


class RequestHandler(object):

    def __init__(self) -> None:

        self.config: Optional[ConfigData] = None

    def authenticate(self, query_data: dict) -> bool:
        """根据请求数据，验证是否为微信服务器发送的消息"""

        # 获取微信传递的参数
        signature = query_data.get('signature', '')
        timestamp = query_data.get('timestamp', '')
        nonce = query_data.get('nonce', '')

        if not signature or not timestamp or not nonce:
            return False

        tmp_list = [self.config.wechat_config.wechat_token, timestamp, nonce]
        tmp_list.sort()

        tmp_str = "".join(tmp_list)
        hashcode = hashlib.sha1(tmp_str.encode('utf8')).hexdigest()

        if hashcode == signature:
            self.config.is_debug and pro_logger.info('经过验证，确定为微信服务器信息')
            return True
        else:
            self.config.is_debug and pro_logger.error('经过验证，该请求不是微信服务器信息')
            return False

    def get(self, request: Request) -> str:
        """处理get请求"""

        echo_str = request.args.get('echostr')
        if not echo_str:
            self.config.is_debug and pro_logger.info("get请求中没有echostr参数，并非微信服务器请求")
            return "This get request is not for authenticated."

        if self.authenticate(request.args):
            return echo_str

        return 'authenticate failed!'

    def post(self, request: Request) -> str:
        """处理post请求"""

        # 先验证是否为微信服务器发送的信息
        if not self.authenticate(request.args):
            return "not wechat post request"

        # 获取请求携带的参数
        xml_dict = xmltodict.parse(request.data.decode('utf-8')).get('xml', {})

        msg_type = xml_dict.get('MsgType')  # 获取本次消息的MsgType

        # 测试模式时打印每次请求的信息
        if self.config.is_debug:
            print(xml_dict)
            pro_logger.info(f"用户发送的消息类型是【{msg_type}】")

        handler = PostHandler(xml_dict)

        try:

            if handler.check_keyword():
                return handler.real_reply_message

            result, continue_flag = handler.check_message()

            if result:
                return handler.real_reply_message

            if continue_flag:
                handle_method = getattr(handler, msg_type, 'unknown')
                handle_method()

                # 将本次交互信息写入数据库
                handler.save_message()
                return handler.real_reply_message
        except Exception:
            pro_logger.error("出现未知错误", exc_info=True)
            return handler.make_reply_text("服务器内部错误，请联系管理员！")
        finally:
            handler.close_database()
