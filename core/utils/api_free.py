# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: mind_workshop
author: 子不语
date: 2024/1/22
contact: 【公众号】思维兵工厂
description: 封装一些免费API接口；需要重新检测URL有效性，废弃未用

--------------------------------------------

API测试链接与文档url

【文档地址】文本转语音API：https://xiaoapi.cn/?action=doc&id=31
【接口测试】https://xiaoapi.cn/API/zs_tts.php?type=xunfei&msg=你好，这是测试的内容&id=19

【文档地址】音乐搜索：https://xiaoapi.cn/?action=doc&id=53
【接口测试】https://xiaoapi.cn/API/yy_sq.php?msg=稻香&type=json&n=1

【文档地址】短链接：https://xiaoapi.cn/?action=doc&id=19
【接口测试】https://xiaoapi.cn/API/dwz.php?url=http://xiaoapi.cn

【文档地址】网易云音乐热门评论：https://api.uomg.com/doc-comments.163.html
【接口测试】https://api.uomg.com/api/comments.163

【文档地址】网易云音乐随机歌曲：https://api.uomg.com/doc-rand.music.html
【接口测试】https://api.uomg.com/api/rand.music?sort=热歌榜&format=json

【接口文档】蓝奏云直链解析：https://api.oick.cn/doc/lanzou
【接口测试】https://api.oick.cn/api/lanzou?url=https://wwa.lanzoui.com/iaxxjsd

【接口文档】历史上的今天：https://api.oick.cn/doc/lishi
【接口测试】https://api.oick.cn/api/lishi
--------------------------------------------
"""

import random
from datetime import datetime
import asyncio
import time

import aiohttp
import requests
from typing import Optional, List
from dataclasses import dataclass


# from .types import MusicInfo


# 代码完成后，删除这个类，该从types导入
@dataclass
class MusicInfo:
    """歌曲详细信息"""

    name: str = ''  # 歌曲名称
    title = ''  # 冗余字段，歌曲名称
    singer: str = ''  # 歌手
    quality: str = ''  # 音质
    url: str = ''  # 下载链接
    cover: str = ''  # 封面图
    code: str = ''
    tips: str = ''  # 提示

    from_uid: str = ''  # 一次性搜索的id
    search_keyword: str = ''  # 搜索关键词
    order: int = None  # 在搜索结果中的排序

    def __post_init__(self):
        self.title = self.name


@dataclass
class FreeApiTextResult:
    """数据类：文本数据"""

    is_success: bool = False  # 标识请求成功
    title: str = ''  # 标题
    result: str = ''  # 主要回复文本
    content: str = ''  # 其他（评论）
    strip_text: str = ''  # 需要剔除的文本

    def __post_init__(self):
        # 如果url有值，则进行strip操作

        if self.is_success:
            return

        if self.result and self.strip_text:
            self.result = self.result.replace(self.strip_text, '').replace('[]', '').replace('生成失败，', '')
        else:
            self.result = self.result.replace('[]', '').replace('生成失败，', '')

        self.result = f"合成失败，原因：【{self.result}】"


class FreeApi(object):

    def __init__(self):
        # 文本转语音API，文档：https://xiaoapi.cn/?action=doc&id=31
        self.tts_url = 'https://xiaoapi.cn/API/zs_tts.php'

        # 音乐信息API，文档：https://xiaoapi.cn/API/yy.php
        self.music_url = 'https://xiaoapi.cn/API/yy_sq.php'

        # 缩短链接API，文档：https://xiaoapi.cn/?action=doc&id=19
        self.short_url = "https://xiaoapi.cn/API/dwz.php"

        # 星座运势接口（图片版）
        self.xingzhuo_url = 'https://xiaoapi.cn/API/xzys_pic.php'

        # 网易云随机音乐
        self.random_music_url = 'https://api.uomg.com/api/rand.music?format=json'

        # 网易云随机音乐【附带热评】
        self.random_music_with_comment_url = 'https://api.uomg.com/api/comments.163'

        self.history_today_url = 'https://api.oick.cn/api/lishi'

        # 请求头
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

        # 文本转语音的音色选择
        self.voice_choice_dict = {
            1: {'id': '1', 'type': 'xunfei', 'info': '讯飞-七哥（男声）'},
            2: {'id': '2', 'type': 'xunfei', 'info': '讯飞-子晴（女声）'},
            3: {'id': '3', 'type': 'xunfei', 'info': '讯飞-一菲（女声）'},
            4: {'id': '4', 'type': 'xunfei', 'info': '讯飞-小露（女声）'},
            5: {'id': '5', 'type': 'xunfei', 'info': '讯飞-小鹏（男声）'},
            6: {'id': '6', 'type': 'xunfei', 'info': '讯飞-萌小新（男声）'},
            7: {'id': '7', 'type': 'xunfei', 'info': '讯飞-小雪（女声）'},
            8: {'id': '8', 'type': 'xunfei', 'info': '讯飞-超哥（男声）'},
            9: {'id': '9', 'type': 'xunfei', 'info': '讯飞-小媛（女声）'},
            10: {'id': '10', 'type': 'xunfei', 'info': '讯飞-叶子（女声）'},
            11: {'id': '11', 'type': 'xunfei', 'info': '讯飞-千雪（女声）'},
            12: {'id': '12', 'type': 'xunfei', 'info': '讯飞-小忠（男声）'},
            13: {'id': '13', 'type': 'xunfei', 'info': '讯飞-万叔（男声）'},
            14: {'id': '14', 'type': 'xunfei', 'info': '讯飞-虫虫（女声）'},
            15: {'id': '15', 'type': 'xunfei', 'info': '讯飞-楠楠（儿童-男）'},
            16: {'id': '16', 'type': 'xunfei', 'info': '讯飞-晓璇（女声）'},
            17: {'id': '17', 'type': 'xunfei', 'info': '讯飞-芳芳（儿童-女）'},
            18: {'id': '18', 'type': 'xunfei', 'info': '讯飞-嘉嘉（女声）'},
            19: {'id': '19', 'type': 'xunfei', 'info': '讯飞-小倩（女声）'},
            20: {'id': '20', 'type': 'xunfei', 'info': '讯飞-Catherine（女声-英文专用）'},
            21: {'id': '1', 'type': 'baidu', 'info': '度逍遥-磁性男声'},
            22: {'id': '2', 'type': 'baidu', 'info': '度博文-情感男声'},
            23: {'id': '3', 'type': 'baidu', 'info': '度小贤-情感男声'},
            24: {'id': '4', 'type': 'baidu', 'info': '度小鹿-甜美女声'},
            25: {'id': '5', 'type': 'baidu', 'info': '度灵儿-清澈女声'},
            26: {'id': '6', 'type': 'baidu', 'info': '度小乔-情感女声'},
            27: {'id': '7', 'type': 'baidu', 'info': '度小雯-成熟女声'},
            28: {'id': '8', 'type': 'baidu', 'info': '度米朵-可爱女童'}
        }

        self._loop = None  # 异步调用的事件循环
        # 根据关键词获取地点，获取天气信息
        # 未实现url ： https://xiaoapi.cn/API/tq.php?msg=搜索关键词&n=1

    @property
    def loop(self):
        if not self._loop:
            self._loop = asyncio.get_event_loop()
        return self._loop

    def text_to_voice(self, text: str, voice_choice: int = 1) -> Optional[FreeApiTextResult]:
        """
        文本转语音接口
        文档地址：https://xiaoapi.cn/?action=doc&id=31
        接口测试：https://xiaoapi.cn/API/zs_tts.php?type=xunfei&msg=你好，这是测试的内容&id=19
        :param text:
        :param voice_choice:
        :return:
        """

        if voice_choice not in self.voice_choice_dict:
            return

        data = self.voice_choice_dict[voice_choice]
        data.update({'msg': text})
        response = requests.get(self.tts_url, params=data, headers=self.header)

        data = response.json()

        code = data.get('code')
        msg = data.get('msg')
        if code != 200:
            return FreeApiTextResult(is_success=False, result=msg)

        tts = data.get('tts')
        if not tts:
            return FreeApiTextResult(is_success=False, result=msg)

        file_name = tts.rsplit('/', maxsplit=1)[-1].split('.', maxsplit=1)[0]
        if file_name == '00000000':
            return FreeApiTextResult(is_success=False, result=msg)

        return FreeApiTextResult(is_success=True, result=tts)

    # ################## 音乐相关接口 ##################

    def music_request(self, data: dict) -> Optional[dict]:
        """
        音乐信息接口：根据请求体的不同，可获取音乐搜索或单曲详细信息
        文档地址：https://xiaoapi.cn/?action=doc&id=53
        接口测试：https://xiaoapi.cn/API/yy_sq.php?msg=稻香&type=json&n=1
        :param data:
        :return:
        """

        try:
            response = requests.get(self.music_url, params=data, headers=self.header)
            response_data = response.json()
            code = response_data.get('code')

            if code != 200:
                return
            return response_data
        except Exception:
            pass

    def get_music_info(self, msg: str, n: [int, str]) -> Optional[MusicInfo]:
        """同步请求：获取单曲详细信息（包含下载链接）"""

        data = {'msg': msg, 'n': str(n)}
        response_data = self.music_request(data)

        if not response_data:
            return

        return MusicInfo(**response_data)

    def get_music_list(self, msg: str) -> Optional[List[MusicInfo]]:
        """同步请求：根据搜索关键词查询歌曲，返回列表"""

        data = {'msg': msg}
        response_data = self.music_request(data)

        if not response_data:
            return []

        info_list = response_data.get('list')
        if not info_list:
            return

        music_list = [MusicInfo(**i, order=idx + 1, search_keyword=msg) for idx, i in enumerate(info_list)]
        return music_list

    async def async_music_request(self, data: dict) -> Optional[dict]:
        """异步请求公共方法"""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.music_url, params=data, headers=self.header) as response:
                    response_data = await response.json()
                    code = response_data.get('code')
                    if code != 200:
                        return
                    return response_data
        except Exception:
            pass

    async def async_get_music_info_task(self, msg: str, n: [int, str]) -> Optional[MusicInfo]:
        """异步请求：查询单曲详细信息"""

        data = {'msg': msg, 'n': str(n)}
        response_data = await self.async_music_request(data)

        if not response_data:
            return

        return MusicInfo(**response_data)

    async def _async_get_musics_info(self, info_list: List[MusicInfo]) -> Optional[List[MusicInfo]]:
        """异步请求：根据搜索关键词查询歌曲，返回列表"""

        result_list = []
        tasks = []
        for info in info_list:
            task = self.loop.create_task(self.async_get_music_info_task(info.search_keyword, info.order))
            task.add_done_callback(lambda t: result_list.append(t.result()))
            tasks.append(task)

        while True:
            if all([task.done() for task in tasks]):
                return result_list
            else:
                await asyncio.sleep(0.5)

    def async_get_musics_info(self, info_list: List[MusicInfo]) -> Optional[List[MusicInfo]]:
        return asyncio.run(self._async_get_musics_info(info_list))

    def get_short_url(self, url: str) -> Optional[str]:
        """
        短链接接口：该接口直接返回文本
        文档地址：https://xiaoapi.cn/?action=doc&id=19
        接口测试：https://xiaoapi.cn/API/dwz.php?url=https://api.uomg.com/
        :param url:
        :return:
        """

        try:
            host = f"{self.short_url}?url={url}"
            response = requests.get(host, headers=self.header)
            return response.text
        except Exception:
            pass

    def _get(self, host, data: dict = None):
        try:
            response = requests.get(host, headers=self.header, data=data)
            data = response.json()
            return data
        except Exception:
            return

    def random_music(self) -> FreeApiTextResult:
        """
        网易云随机音乐：该接口随机返回网易云一首歌
        文档地址：https://api.uomg.com/doc-rand.music.html
        接口测试：https://api.uomg.com/api/rand.music?sort=热歌榜&format=json
        :return: FreeApiTextResult
        """

        data = self._get(self.random_music_url)
        if not data:
            return FreeApiTextResult(is_success=False, result='【随机音乐】接口异常')

        return FreeApiTextResult(
            is_success=True,
            result=data.get('data', {}).get('url'),
            title=data.get('data', {}).get('name')
        )

    def random_music_with_comment(self) -> FreeApiTextResult:
        """
        网易云热门评论：该接口随机返回网易云的热评，同时携带歌曲
        文档地址：https://api.uomg.com/doc-comments.163.html
        接口测试：https://api.uomg.com/api/comments.163
        :return: FreeApiTextResult
        """

        data = self._get(self.random_music_with_comment_url)
        if not data:
            return FreeApiTextResult(is_success=False, result='【随机音乐（热评版）】接口异常')

        return FreeApiTextResult(
            is_success=True,
            result=data.get('data', {}).get('url'),
            title=data.get('data', {}).get('name'),
            content=data.get('data', {}).get('content')
        )

    def history_today(self) -> FreeApiTextResult:
        """
        历史上的今天：该接口返回【历史上的今天】数据
        文档地址：https://api.oick.cn/doc/lishi
        接口测试：https://api.oick.cn/api/lishi
        :return: FreeApiTextResult
        """

        data = self._get(self.history_today_url)
        if not data:
            return FreeApiTextResult(is_success=False, result='【历史上的今天】接口异常')

        today_year = int(datetime.now().year)

        result = data.get('result', )
        day = data.get('day', )
        if not result:
            return FreeApiTextResult(is_success=False, result='【历史上的今天】信息获取失败')

        tips = []

        while len(result) > 8:
            random_index = random.randint(0, len(result) - 1)
            result.pop(random_index)

        icon_list = ["📚", "👉", "📝", '✍🏻']
        icon = random.choice(icon_list)
        for item in result:
            date = item.get('date', '')
            title = item.get('title', '')

            if not date or not title:
                continue

            try:
                year = int(date.split('年', maxsplit=1)[0])
                year_gap = today_year - year
                tip = icon + f"{year_gap}年前的今天\n【{date}】\n{title}\n\n"
            except Exception:
                year = date.split('年', maxsplit=1)[0]
                tip = icon + f"{year}年的今天\n{title}\n\n"

            tips.append(tip)

        message = ''.join(tips).strip()

        return FreeApiTextResult(is_success=True, result=message, title=day)


if __name__ == '__main__':
    handler = FreeApi()
    a = handler.get_music_info('一生中最爱', 1)
    print(a)
