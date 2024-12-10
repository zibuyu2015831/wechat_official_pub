# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: mind_workshop
author: 子不语
date: 2024/1/24
contact: 【公众号】思维兵工厂
description: 一个信息查询接口，支持qq查手机号，手机号查询qq，微博查询手机号
--------------------------------------------
"""

from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class PersonInfo(object):
    id: str = ''
    qq: str = ''
    phone: str = ''
    phonediqu: str = ''


class PrivacyHandler(object):

    def __init__(self):
        self._search_qq_url = "https://zy.xywlapi.cc/qqapi"
        self._search_phone_url = "https://zy.xywlapi.cc/qqphone"
        self._search_weibo_url = "https://zy.xywlapi.cc/wbapi"

    @staticmethod
    def _get(url: str, params: dict) -> dict:

        try:
            data = requests.get(url, params=params)
            return data.json()
        except Exception as e:
            print(e)

    @staticmethod
    def handle_result(res: dict) -> Optional[PersonInfo]:
        try:
            if not res:
                return
            if res.get('status') == 200:
                qq = res.get('qq', '')
                phone = res.get('phone', '')
                phone_diqu = res.get('phonediqu', '')
                weibo_id = res.get('id', '')

                return PersonInfo(weibo_id, qq, phone, phone_diqu)
        except Exception:
            pass

    def search_qq(self, qq: str) -> Optional[PersonInfo]:

        res = self._get(url=self._search_qq_url, params={"qq": qq})

        return self.handle_result(res)

    def search_phone(self, phone: str) -> Optional[PersonInfo]:
        res = self._get(url=self._search_phone_url, params={"phone": phone})

        return self.handle_result(res)

    def search_weibo(self, wb: str) -> Optional[PersonInfo]:
        res = self._get(url=self._search_weibo_url, params={"wb": wb})
        return self.handle_result(res)
