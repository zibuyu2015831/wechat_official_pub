# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/11/20
contact: 【公众号】思维兵工厂
description: 全局错误汇集
--------------------------------------------
"""


class NotConfigError(Exception):
    """没有配置文件"""
    msg = "配置文件：config.json不存在，请先配置！"


class ConfigError(Exception):
    """配置文件异常"""
    msg = "配置文件：config.json缺失必须配置项，请检查！"


class WechatReplyTypeError(Exception):
    """关键词回复异常"""
    msg = "回复类型错误，所有函数的返回结果必须是WechatReplyData类型"
