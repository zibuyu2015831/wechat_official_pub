# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/11/21
contact: 【公众号】思维兵工厂
description: 指令功能
--------------------------------------------
"""

from .base import check_keywords


def get_all_first_function_dict():
    """
    获取所有关键词功能
    :return:
    """

    all_first_function_dict = dict()

    # 1. 添加签到功能
    try:
        from . import signin
        all_first_function_dict.update(signin.add_first_keyword_function())
    except:
        pass

    # 2. 添加文本加密解密功能
    try:
        from . import text_oracle
        all_first_function_dict.update(text_oracle.add_first_keyword_function())
    except:
        pass

    # 3. 添加个人信息查询功能
    try:
        from . import search_personal_info
        all_first_function_dict.update(search_personal_info.add_first_keyword_function())
    except:
        pass

    # 4. 添加天气查询功能
    try:
        from . import weather
        all_first_function_dict.update(weather.add_first_keyword_function())
    except:
        pass

    # 6. 添加网盘资源搜索功能
    try:
        from . import source
        all_first_function_dict.update(source.add_first_keyword_function())
    except:
        pass

    # 7. 添加账户相关功能
    try:
        from . import account
        all_first_function_dict.update(account.add_first_keyword_function())
    except:
        pass

    # 8. 添加文本转语音功能
    try:
        from . import text_to_voice
        all_first_function_dict.update(text_to_voice.add_first_keyword_function())
    except:
        pass

    # 9. 添加图片转文本功能
    try:
        from . import ocr
        all_first_function_dict.update(ocr.add_first_keyword_function())
    except:
        pass

    # 10. 添加笔记转存功能
    try:
        from . import note
        all_first_function_dict.update(note.add_first_keyword_function())
    except:
        pass

    return all_first_function_dict


def get_all_function_dict():
    """
    获取所有关键词功能
    :return:
    """

    all_get_function_dict = dict()

    # 1. 添加文本加密解密功能
    try:
        from . import text_oracle
        all_get_function_dict.update(text_oracle.add_keyword_function())
    except:
        pass

    # 2. 添加个人信息查询功能
    try:
        from . import search_personal_info
        all_get_function_dict.update(search_personal_info.add_keyword_function())
    except:
        pass

    # 3. 添加天气查询功能
    try:
        from . import weather
        all_get_function_dict.update(weather.add_keyword_function())
    except:
        pass

    # 5. 添加网盘资源搜索功能
    try:
        from . import source
        all_get_function_dict.update(source.add_keyword_function())
    except:
        pass

    # 6. 添加账户相关功能
    try:
        from . import account
        all_get_function_dict.update(account.add_keyword_function())
    except:
        pass

    # 7. 添加文本转语音相关功能
    try:
        from . import text_to_voice
        all_get_function_dict.update(text_to_voice.add_keyword_function())
    except:
        pass

    # 8. 添加图片转文本功能
    try:
        from . import ocr
        all_get_function_dict.update(ocr.add_keyword_function())
    except:
        pass

    # 10. 添加笔记转存功能
    try:
        from . import note
        all_get_function_dict.update(note.add_keyword_function())
    except:
        pass

    return all_get_function_dict


FIRST_FUNCTION_DICT = get_all_first_function_dict()
ALL_FUNCTION_DICT = get_all_function_dict()

__all__ = [
    'check_keywords',
    'get_all_first_function_dict',
    'get_all_function_dict',
    'FIRST_FUNCTION_DICT',
    'ALL_FUNCTION_DICT'
]
