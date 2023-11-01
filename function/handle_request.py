# -*- coding: utf-8 -*-
import os
import time
import json
import hashlib
import logging
import xmltodict
from .post_handler import ReplyHandler


def get_config() -> dict:
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_path, 'config.json')
    if not os.path.exists(config_path):
        raise Exception("配置文件不存在！")
    with open(config_path, mode='r', encoding='utf8') as rf:
        config_dict = json.load(rf)

    return config_dict


def authenticate(query_data, logger: logging.Logger):
    config_dict = get_config()
    # 从配置信息中获取公众号token
    wechat_token = config_dict.get('wechat').get('wechat_token')

    # 获取微信传递的参数
    signature = query_data.get('signature')
    timestamp = query_data.get('timestamp')
    nonce = query_data.get('nonce')

    if not signature or not timestamp or not nonce:
        return ""

    tmp_list = [wechat_token, timestamp, nonce]
    tmp_list.sort()

    tmp_str = "".join(tmp_list)
    hashcode = hashlib.sha1(tmp_str.encode('utf8')).hexdigest()

    if hashcode == signature:
        logger.info('经过验证，为微信服务器信息')
        return True
    else:
        logger.error('经过验证，不是微信服务器信息')
        return False


def handle_get(request, logger: logging.Logger):
    echo_str = request.args.get('echostr')
    if not echo_str:
        logger.info("get请求中没有echostr，并非微信服务器请求")
        return "This get request is not for authenticated."

    if authenticate(request.args, logger):
        return echo_str

    return 'not wechat info!'


def handle_post(request, logger: logging.Logger):
    config_dict = get_config()
    # 先验证是否为微信服务器发送的信息
    if not authenticate(request.args, logger):
        return "not wechat info"

    xml_dict = xmltodict.parse(request.data.decode('utf-8')).get('xml', {})
    print(xml_dict)
    msg_type = xml_dict.get('MsgType')  # 获取本次消息的MsgType
    logger.info(f"用户发送的消息类型是【{msg_type}】")

    handler = ReplyHandler(xml_dict, config_dict, logger)

    if hasattr(ReplyHandler, msg_type):
        handle_method = getattr(handler, msg_type)
        reply = handle_method()
    else:
        reply = ""

    return reply
