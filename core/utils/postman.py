# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/12/6
contact: 【公众号】思维兵工厂
description: 消息发送，可发送微信消息或者邮件
--------------------------------------------
"""

import requests


def send_wechat_msg(token: str, msg: str = '', img_url: str = '') -> bool:
    """
    发送微信消息
    :param token: 笔记卡片的token
    :param msg: 文本信息
    :param img_url: 图片地址
    :return: bool 是否发送成功
    """

    host = f'https://nodered.glwsq.cn/weixin2'

    data = {
        "token": token,
        "group": False,
        "type": "text" if msg else "image",
        "content": msg if msg else img_url,
    }

    try:
        response = requests.post(host, json=data)
        json_resp = response.json()

        return json_resp.get('success', False)
    except:
        return False


def send_email(msg: str):
    # TODO: 待实现
    pass


