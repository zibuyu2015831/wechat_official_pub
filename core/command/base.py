# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/11/21
contact: 【公众号】思维兵工厂
description: 
--------------------------------------------
"""

import re
import time
import random
import logging
from typing import Optional, Union, List, Callable, Sequence, TYPE_CHECKING

from ..models import KeyWord
from ..config import pro_logger, config
from ..error import WechatReplyTypeError
from ..constant import sep_char, cancel_command_list
from ..types import FunctionInfo, ConfigData, WechatReplyData, SinglePageData

if TYPE_CHECKING:
    from ..handle_post import BasePostHandler


def register_function(
        commands: Union[str, Sequence[str]],
        function_dict: dict,
        first_function_dict: dict,
        is_first: bool = False,
        is_master: bool = False,
        is_show: bool = True,
        function_intro: str = None
):
    """
    一个装饰器，用来定义关键词回复。
    当要实现一个文本关键词时，只需要书写对应的方法，再通过此函数进行注册即可；
    注册时，需要传入commands（触发关键词）
    :param commands: 触发功能的关键词，字符串或列表
    :param function_dict: 存储关键词与实现对应功能的字典；非直接功能，即调用时需要传递参数
    :param first_function_dict: 存储关键词与实现对应功能的字典；直接功能，即调用时无需参数
    :param is_first: 是否是直接功能，即无需参数直接调用
    :param is_master: 是否仅管理员可用
    :param is_show: 该功能是否向用户展示
    :param function_intro: 功能介绍
    :return:
    """

    if not isinstance(commands, (list, tuple)):
        function_name_list = [commands, ]
    else:
        function_name_list = commands

    def register(real_func_obj: Callable, func_dict: dict, func_name_list: Union[str, list[str], tuple[str]]):
        for func in func_name_list:

            if func.strip() in func_dict:
                old_func_name = func_dict[func.strip()].function_name
                msg = f"函数重名错误，关键词【{func.strip()}】已与【{old_func_name}】绑定，不可再绑定【{real_func_obj.__name__}】"

                config.is_debug and pro_logger.error(msg)
                continue

            func_dict[func.strip()] = FunctionInfo(
                function=real_func_obj,
                function_name=real_func_obj.__name__,
                is_first=is_first,
                is_master=is_master,
                is_show=is_show,
                function_intro=function_intro,
            )

            config.is_debug and pro_logger.info(f"成功注册功能：【{func}-{real_func_obj.__name__}】")

        config.is_debug and pro_logger.info("-" * 30)

    def inner(func):

        if is_first:
            register(func, first_function_dict, function_name_list)
        else:
            register(func, function_dict, function_name_list)

        return func

    return inner


def check_keywords(
        first_function_dict: dict,
        function_dict: dict,
        keyword: str,
        *args,
        **kwargs
) -> Optional[WechatReplyData]:
    """
    检查关键词是否匹配
    :param first_function_dict: 存储关键词与实现对应功能的字典；直接功能，即调用时无需参数
    :param function_dict: 存储关键词与实现对应功能的字典；非直接功能，即调用时需要传递参数
    :param keyword: 触发关键词（用户发送的原文本内容）
    :return:
    """

    if not keyword:
        return

    if config.wechat_config.sep_char in keyword:

        command, content = keyword.split(config.wechat_config.sep_char, maxsplit=1)

        pro_logger.info(f"用户输入的关键词包含分隔符")
        pro_logger.info(f"将关键词拆分为两部分：命令【{command}】和 内容【{content}】")

        if config.wechat_config.sep_char in content:
            content, key = content.split(config.wechat_config.sep_char, maxsplit=1)
            pro_logger.info(f"将内容拆分为两部分：内容【{content}】和 键（key）【{key}】")
        else:
            key = None
            pro_logger.info(f"内容中不包含分隔符，键（key）为空")

        pro_logger.info(f"逐一判断命令【{command}】是否在注册列表【function_dict】中")
        for handler_obj, command_dict in function_dict.items():

            if command in command_dict:

                pro_logger.info(f"匹配到命令【{command}】对应的处理方法")

                function_info_obj: FunctionInfo = command_dict[command]

                pro_logger.info(f"该方法为：【{handler_obj.model_name}.{function_info_obj.function_name}】；即将调用该方法")

                result = function_info_obj.function(
                    handler_obj, content, key=key,
                    function_dict=function_dict,
                    first_function_dict=first_function_dict,
                    *args, **kwargs
                )

                if not isinstance(result, WechatReplyData):
                    raise WechatReplyTypeError(
                        f'【关键词：{command}】对应的函数【{function_info_obj.function_name}】返回值类型错误'
                    )

                return result

        pro_logger.info(f"未匹配到命令【{command}】对应的处理方法")
    else:
        pro_logger.info(f"用户输入的关键词不包含分隔符")
        pro_logger.info(f"逐一判断命令【{keyword}】是否在注册列表【first_function_dict】中")

        for handler_obj, command_dict in first_function_dict.items():

            if keyword in command_dict:

                pro_logger.info(f"匹配到命令【{keyword}】对应的处理方法")

                if config.wechat_config.sep_char in keyword:
                    keyword, key = keyword.split(config.wechat_config.sep_char, maxsplit=1)
                else:
                    key = None

                function_info_obj: FunctionInfo = command_dict[keyword]

                pro_logger.info(f"该方法为：【{handler_obj.model_name}.{function_info_obj.function_name}】；即将调用该方法")

                result = function_info_obj.function(
                    handler_obj, keyword, key=key,
                    function_dict=function_dict,
                    first_function_dict=first_function_dict,
                    *args, **kwargs

                )

                if not isinstance(result, WechatReplyData):
                    raise WechatReplyTypeError(
                        f'【关键词：{keyword}】对应的函数【{function_info_obj.function_name}】返回值类型错误'
                    )

                return result

        pro_logger.info(f"未匹配到命令【{keyword}】对应的处理方法")


class WeChatKeyword(object):
    """处理微信【关键词回复】的父类"""

    model_name = "base(父类)"

    def __init__(self, *args, **kwargs):

        self.cancel_command_list = cancel_command_list

        self.logger: logging.Logger = pro_logger
        self.config: ConfigData = config
        self.sep_char = config.wechat_config.sep_char or sep_char
        self.command_intro_title = "------ ✍🏻 短指令介绍------\n\n{}"

    @staticmethod
    def save_command_keyword(post_handler: "BasePostHandler", command: str) -> bool:

        try:
            current_timestamp = int(time.time())
            expire_time = current_timestamp + config.command_expire_time

            keyword_obj = KeyWord(
                keyword=post_handler.current_command_key,
                reply_content=command,  # 注意这里存储的key，得是注册函数时 commands 列表中的值
                official_user_id=post_handler.request_data.to_user_id,
                reply_type='text',
                expire_time=expire_time,
            )

            post_handler.database.session.add(keyword_obj)
            post_handler.database.session.commit()

            config.is_debug and pro_logger.info(f"【{command}】指令保存成功")
            return True
        except:
            config.is_debug and pro_logger.error(f"【{command}】指令保存失败", exc_info=True)
            return False

    def paginate(self, content: str, handle_function: Callable, item_list: List, post_handler) -> Optional[str]:
        """
        系统方法：将传入的列表（任何数据类的实例）进行分页、每页数据存入redis缓存
        :param content: 用户输入的关键词；
        :param handle_function: 处理方法，该方法接收元素为Command实例的列表，处理成字符串；
        :param item_list: 所有项目列表，元素为Command实例；
        :param post_handler: post_handler；
        :return:
        """

        try:
            per_page_count = int(config.per_page_count)
        except:
            self.logger.error(f"【系统配置】每页数据量配置错误；本次处理默认每页数据量：5", exc_info=True)
            per_page_count = 5

        # 按照系统配置的每页数量进行分页
        pages = [item_list[i:i + per_page_count] for i in range(0, len(item_list), per_page_count)]

        first_page_content: str = ''
        current_timestamp = int(time.time())
        expire_time = current_timestamp + 60 * 60 * 3

        for index, page in enumerate(pages, start=1):

            page_obj = SinglePageData(
                current_page=index,
                total_page=len(pages),
                data=page,
                title=content
            )

            # 将单页数据存入redis缓存
            reply_content = handle_function(page_obj)
            keyword = f"{content}-{index}"

            keyword_obj = KeyWord(
                keyword=keyword,
                reply_content=reply_content,
                reply_type='text',
                official_user_id=post_handler.request_data.to_user_id,
                expire_time=expire_time,
            )

            post_handler.database.session.add(keyword_obj)

            if index == 1:
                first_page_content = reply_content

        post_handler.database.session.commit()

        return first_page_content

    @staticmethod
    def make_pagination(current_page_num: Union[str, int], pages_num: Union[str, int], search_keyword: str):
        """系统方法：生成每页的内容，包括主内容与分页信息"""

        header = f"---【{search_keyword}】搜索结果---\n\n"

        middle = f"\n\n👉👉当前第{current_page_num}页，共{pages_num}页👈👈\n\n"

        if pages_num == '1':
            footer = ""
            middle = f"\n\n👉👉当前第{current_page_num}页，共{pages_num}页👈👈"
        else:
            page_tips = []
            for i in range(1, int(pages_num) + 1):

                if i == int(current_page_num):
                    continue

                page_tip = f"回复【{search_keyword}-{i}】可查看第{i}页"
                page_tips.append(page_tip)

            if len(page_tips) <= 6:
                footer = "\n".join(page_tips)
            else:
                footer = '\n'.join(page_tips[:2]) + "\n...\n" + '\n'.join(page_tips[-2:])

        return header, middle, footer

    @staticmethod
    def is_en_text(text: str):
        """
        小工具，利用正则判断输入的文本是否为英文文本。

        :param text: (str)需要判断的文本。
        :return: (bool) 如果文本是英文文本则返回 True，否则返回 False。
        """

        # 使用正则表达式匹配英文字符和中英文标点符号
        pattern = re.compile(r'^[a-zA-Z0-9\s.,!?\'"():;@#%&*+=|\\/-，。！？、‘’“”（）《》【】〔〕—]+$')
        return bool(pattern.match(text))

    @staticmethod
    def is_zh_text(text: str):
        """
        小工具，利用正则判断输入的文本是否为中文文本。

        :param text:  (str)需要判断的文本。
        :return: (bool) 如果文本是中文文本则返回 True，否则返回 False。
        """

        # 使用正则表达式匹配中文字符
        pattern = re.compile(r'^[\u4e00-\u9fff\s，。！？、‘’“”（）《》【】〔〕—]+$')
        return bool(pattern.match(text))

    @staticmethod
    def is_zh_and_en_text(text: str):
        """
        小工具，利用正则判断输入的文本是否为中文和英文混合文本。
        :param text:
        :return:
        """

        contains_chinese = False
        allowed_punctuation = set(' ,.!?"\'@#%&*+=|-()[]{};:\n\t')
        for c in text:
            if ('\u4e00' <= c <= '\u9fff' or
                    '\u3400' <= c <= '\u4dbf' or
                    '\uF900' <= c <= '\uFAFF' or
                    '\U00020000' <= c <= '\U0002FFFF' or
                    '\u3000' <= c <= '\u303F' or
                    '\uFF00' <= c <= '\uFFEF'):
                contains_chinese = True
            elif c.isalpha() and c.lower() in 'abcdefghijklmnopqrstuvwxyz':
                continue
            elif c.isdigit():
                continue
            elif c in allowed_punctuation:
                continue
            else:
                return False
        return contains_chinese

    @staticmethod
    def is_valid_url(url):
        """
        检查给定的字符串是否是一个有效的URL。

        :param url: 需要检查的字符串
        :return: 如果是有效的URL返回True，否则返回False
        """
        # 定义正则表达式
        url_pattern = re.compile(
            r'https?://'  # 匹配 http 或 https 协议
            r'(www\.)?'  # 可选的 www. 前缀
            r'[-a-zA-Z0-9@:%._\+~#=]{1,256}'  # 域名部分
            r'\.[a-zA-Z0-9()]{1,6}'  # 顶级域名
            r'\b'  # 单词边界
            r'([-a-zA-Z0-9()@:%_\+.~#?&//=]*)'  # 路径、查询参数和片段标识符
        )

        # 使用正则表达式进行匹配
        match = url_pattern.match(url)

        # 返回匹配结果
        return bool(match)

    @staticmethod
    def ramdom_code(length: int = 5) -> str:
        """
        随机生成指定长度的数字字符串
        :param length: 随机数字字符串长度
        :return:
        """
        return ''.join(map(str, random.choices(range(10), k=length)))

    @staticmethod
    def cancel_command(post_handler: "BasePostHandler") -> WechatReplyData:

        keywords = post_handler.database.session.query(KeyWord).filter(
            KeyWord.keyword == post_handler.current_command_key,
            KeyWord.official_user_id == post_handler.request_data.to_user_id
        ).all()
        if not keywords:
            return WechatReplyData(msg_type="text", content="---已在首页，没有进入指令---")

        for keyword in keywords:
            post_handler.database.session.delete(keyword)
        post_handler.database.session.commit()

        return WechatReplyData(msg_type="text", content="---已退出指令模式---")

    def check_is_cancel_command(self, content: str, post_handler: "BasePostHandler") -> Optional[WechatReplyData]:

        if content in self.cancel_command_list:
            return self.cancel_command(post_handler)
