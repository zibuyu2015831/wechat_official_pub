# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: mind_workshop
author: 子不语
date: 2024/4/25
contact: 【公众号】思维兵工厂
description: 【关键词回复功能】 签到功能
--------------------------------------------
"""

import pytz
from datetime import datetime
from typing import TYPE_CHECKING

from .base import WeChatKeyword, register_function
from ..types import WechatReplyData
from ..models import UserSignIn
from ..config import config

if TYPE_CHECKING:
    from ..handle_post import BasePostHandler

FUNCTION_DICT = dict()
FIRST_FUNCTION_DICT = dict()


class KeywordFunction(WeChatKeyword):
    model_name = "signin"

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['签到', '我要签到'], is_first=True,
                       function_intro='签到以获取积分')
    def sign_in(self, content: str, *args, **kwargs):
        """处理签到，获取积分"""

        # 检查签到口令
        if content != config.sign_in_word:
            return WechatReplyData(
                msg_type='text',
                content='签到口令错误，请检查！'
            )

        post_handler: BasePostHandler = kwargs.get('post_handler')

        # 获取当前时区
        local_tz = pytz.timezone('Asia/Shanghai')

        # 获取当前时间并转换为本地时区
        now = datetime.now(pytz.utc).astimezone(local_tz)

        # 获取当前日期
        today = now.date()

        existing_sign_in = post_handler.database.session.query(UserSignIn).filter(
            UserSignIn.official_user_id == post_handler.request_data.to_user_id,
            UserSignIn.sign_in_date == today
        ).first()

        if existing_sign_in:
            return WechatReplyData(
                msg_type='text',
                content="您今天已经签到过了，请明天再来吧！"
            )
        else:
            new_sign_in, credit_num = UserSignIn.update_consecutive_days(
                session=post_handler.database.session,
                official_user_id=post_handler.request_data.to_user_id,
                wechat_user=post_handler.wechat_user
            )

            if credit_num == 0:
                return WechatReplyData(
                    msg_type='text',
                    content=f"签到操作失败；当前总积分{post_handler.wechat_user.credit}，如果积分未增加，请重试！"
                )

            msg = f"---签到成功！---\n\n本次签到获取{credit_num}积分，当前总积分{post_handler.wechat_user.credit}\n\n---连续签到{new_sign_in.consecutive_days}天---"
            return WechatReplyData(
                msg_type='text',
                content=msg
            )


def add_keyword_function(*args, **kwargs):
    obj = KeywordFunction(*args, **kwargs)
    return {obj: FUNCTION_DICT}


def add_first_keyword_function(*args, **kwargs):
    obj = KeywordFunction(*args, **kwargs)
    return {obj: FIRST_FUNCTION_DICT}
