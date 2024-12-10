# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/11/20
contact: 【公众号】思维兵工厂
description: 
--------------------------------------------
"""

import re
import datetime
import logging.handlers
from datetime import datetime


class DailyRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """
    扩展 TimedRotatingFileHandler 类，
    实现以当天日期命名日志文件
    """

    def __init__(
            self, filename, when='h',
            interval=1, backupCount=0,
            encoding=None, delay=False,
            utc=False, atTime=None
    ):
        super().__init__(
            filename=filename,
            when=when,
            interval=interval,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
            utc=utc,
            atTime=atTime
        )

    @staticmethod
    def replace_date(*args, **kwargs):
        """定义替换函数"""
        current_date = datetime.now().strftime("%Y%m%d")
        return f"log_{current_date}.log"

    def rotation_filename(self, default_name):
        """
        重写父类方法，实现以当天日期命名日志文件
        :param default_name: 默认文件名
        :return: 新文件名
        """

        # 定义正则表达式
        pattern = r'log_(\d{8})\.log'

        current_date = datetime.now().strftime("%Y%m%d")

        if '.' in default_name:
            return re.sub(pattern, self.replace_date, default_name)
        else:
            return f"{default_name}_{current_date}.log"
