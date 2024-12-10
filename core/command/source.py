# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: mind_workshop
author: 子不语
date: 2024/4/25
contact: 【公众号】思维兵工厂
description:  【关键词回复功能】处理网盘资源链接相关功能
--------------------------------------------
"""

import datetime
from typing import TYPE_CHECKING
from sqlalchemy import func, or_

from ..models import Source
from ..types import WechatReplyData, SourceFile, SinglePageData
from .base import WeChatKeyword, register_function

if TYPE_CHECKING:
    from ..handle_post import BasePostHandler

FUNCTION_DICT = dict()
FIRST_FUNCTION_DICT = dict()


class KeywordFunction(WeChatKeyword):
    model_name = "source"

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['资源数量', '资源总数', '当前资源数', '当前资源总数'], is_first=True,
                       function_intro='输出实时的资源总数')
    def source_count(self, *args, **kwargs):
        """返回数据表wechat_source的总数：当前资源总数"""

        post_handler: BasePostHandler = kwargs.get('post_handler')

        update_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        header = f"- -👉{update_time}👈- -\n\n"
        total_count = post_handler.database.session.query(func.count(Source.id)).scalar()
        return WechatReplyData(msg_type="text", content=header + f'当前资源总数为：{total_count}')

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['资源搜索', '搜索资源', '资源', '查找', '查询', '搜索'], is_first=False,
                       function_intro='根据提供的关键词，查询公开分享的各类网盘资源')
    def search_source(self, content: str, *args, **kwargs):
        """从数据库中搜索资源"""

        post_handler: BasePostHandler = kwargs.get('post_handler')

        results = post_handler.database.session.query(Source).filter(
            or_(
                Source.title.like(f'%{content}%'),
                Source.check_title.like(f'%{content}%'),
                Source.description.like(f'%{content}%')
            )
        ).all()

        if not results:
            return WechatReplyData(msg_type="text", content=f"---【{content}】搜索无结果---")

        results_list = [SourceFile(
            title=result.title,
            check_title=result.check_title,
            share_key=result.share_key,
            share_pwd=result.share_pwd,
            share_url=result.share_url,
            description=result.description,
            drive_name=result.drive_name
        ) for result in results]

        first_page_content = self.paginate(content, self.source_single_page, results_list, post_handler)

        return WechatReplyData(msg_type="text", content=first_page_content)

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['source_single_page', ], is_show=False, )
    def source_single_page(self, single_page: SinglePageData, *args, **kwargs):
        """内部方法：资源搜索结果的单页处理方法：逐一拼接网盘链接前缀"""

        post_handler: BasePostHandler = kwargs.get('post_handler')

        header, middle, footer = self.make_pagination(
            current_page_num=single_page.current_page,
            pages_num=single_page.total_page,
            search_keyword=single_page.title
        )

        file_obj_list = single_page.data

        all_line = []
        for file_obj in file_obj_list:
            line = f"【{file_obj.drive_name}】<a href='{file_obj.share_url}'>{file_obj.title}</a>\n"
            all_line.append(line)

        result = '\n'.join(all_line)
        content = header + result + middle + footer
        return content.strip()

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['资源搜索', '搜索资源', '资源', '查找', '查询', '搜索'], is_first=True)
    def correct_search_source(self, content: str, *args, **kwargs):
        """当用户输入“搜索、资源、查找、查询”等短指令而没有携带参数时，给出示例提示"""

        msg = f"""👉指令名称：{content}；
👉参数要求：需携带参数；
👉使用注意：以三个减号（---）分隔参数。

🌱示例🌱
输入【{content}---三国演义】，即可搜索与“三国演义”有关的资源"""

        return WechatReplyData(msg_type="text", content=self.command_intro_title.format(msg))


def add_keyword_function(*args, **kwargs):
    obj = KeywordFunction(*args, **kwargs)
    return {obj: FUNCTION_DICT}


def add_first_keyword_function(*args, **kwargs):
    obj = KeywordFunction(*args, **kwargs)
    return {obj: FIRST_FUNCTION_DICT}
