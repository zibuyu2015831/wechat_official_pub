# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/12/9
contact: 【公众号】思维兵工厂
description: 此脚本用于部署腾讯云函数的定期任务：过期数据清除+数据库备份到对象存储

部署时需要设定以下环境变量：
    - request_token：请求token；
    - wechat_token[可选]：【笔记卡片】的消息发送token，用于发送结果；
    - database_backup_url：
    - database_cleanup_url：
--------------------------------------------
"""

import os
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


def database_cleanup(request_token: str) -> str:
    try:
        database_cleanup_url = os.getenv('database_cleanup_url')
        response = requests.get(database_cleanup_url, params={'request_token': request_token})
        return response.text
    except:
        return ''


def database_backup(request_token: str) -> str:
    try:
        database_backup_url = os.getenv('database_backup_url')
        response = requests.get(database_backup_url, params={'request_token': request_token})
        return response.text
    except:
        return ''


def main_handler(event, context):
    request_token = os.getenv('request_token')
    wechat_token = os.getenv('wechat_token')
    database_cleanup_url = os.getenv('database_cleanup_url')
    database_backup_url = os.getenv('database_backup_url')

    if wechat_token:

        msg = '【思维兵工厂】定期任务：\n\n'

        if database_cleanup_url:
            msg += f'1. 过期数据清除\n'
        if database_backup_url:
            msg += f'2. 数据库备份\n'

        if not request_token:
            msg = '【思维兵工厂】定期任务：\n\n无请求token，无法执行'

        send_wechat_msg(wechat_token, msg=msg.strip())

    cleanup_result = database_cleanup(request_token) or '过期数据清理失败'
    backup_result = database_backup(request_token) or '数据库备份失败'

    msg = f"---微信公众号项目---\n\n1. {cleanup_result}\n2. {backup_result}"
    if wechat_token:
        send_wechat_msg(wechat_token, msg=msg)
    return msg
