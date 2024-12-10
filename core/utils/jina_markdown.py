# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/12/3
contact: 【公众号】思维兵工厂
description: 基于Jina Reader，将html内容转为markdown格式

官网：https://jina.ai/reader/
--------------------------------------------
"""

import requests
from dataclasses import dataclass


@dataclass
class Markdown:

    is_success: bool = False  # 请求是否成功
    title: str = ''
    source: str = ''
    content: str = ''


def convert_url_to_md(url: str):
    """
    请求url获取html内容，转为markdown格式
    :param url:
    :return:
    """

    url = f'https://r.jina.ai/{url}'

    # 在官网中，demo代码需要添加 Authorization 参数；但目前不添加也可以
    # headers = {'Authorization': 'Bearer jina_72481aeb67be4a8da44eec0c6f39f3c6ogXjDzSd3ZhtCRs0yEJ_oC79sslE'}

    content_obj = Markdown()

    try:
        response = requests.get(url)

        lines = response.text.split('\n')

        title = ''
        source = ''
        for line in lines:

            if line.startswith('Title:'):
                title = line.replace('Title:', '').strip()

            if line.startswith('URL Source:'):
                source = line.replace('URL Source:', '').strip()

            if title and source:
                break

        content_start_line = lines.index('Markdown Content:') + 1
        content = '\n'.join(lines[content_start_line:])

        content_obj.title = title
        content_obj.source = source
        content_obj.content = content
        content_obj.is_success = True

    except:
        content_obj.is_success = False
    finally:
        return content_obj


if __name__ == '__main__':
    result = convert_url_to_md('https://hub.baai.ac.cn/view/39924')
    print(result)
