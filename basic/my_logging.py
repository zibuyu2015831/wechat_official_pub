# -*- coding: utf-8 -*-

"""
该脚本用于更规范地输出日志
使用时，在程序的类中继承这里的 MyLogging 类，就可以使用 self.logger 输出日志
默认终端输出+文本输出
文本输出存储于【log.files】文件夹中（没有时自动创建）

MyLogging 还提供了一个 类方法 print_logger
某些情况下，不想使用日志功能时，可以用它替换 self.logger，实现简单的打印
"""

from builtins import ModuleNotFoundError
from datetime import datetime
from pathlib import Path
import logging.handlers
import logging.config
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
module_path = Path.cwd() / 'module'
sys.path.append(str(module_path.absolute()))  # 在这里添加项目的module路径，方便main文件导入aligo模块


class DailyRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """
    扩展 TimedRotatingFileHandler 类，
    实现以当天日期命名日志文件
    """

    def __init__(self, filename, when='h', interval=1, backupCount=0,
                 encoding=None, delay=False, utc=False, atTime=None,
                 formatter=None):
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc, atTime, formatter)

    def rotation_filename(self, default_name):
        pre_file_name = default_name.rsplit('.', maxsplit=1)[0]

        current_date = datetime.now().strftime("%Y%m%d")
        return pre_file_name + '-' + current_date + ".log"


class MyLogging(object):
    def __init__(self, config: dict = None):

        log_file_path = Path.cwd() / 'log_files'
        self.fmt = "%(asctime)s.%(msecs)04d | %(levelname)8s | %(module)s | %(message)s "

        if not log_file_path.exists():
            log_file_path.mkdir()

        if config:
            self.config = config
        else:
            self.config = self._get_config()

    @property
    def logger(self):
        logger_config = self.config['logger_config']
        logging.config.dictConfig(logger_config)
        logger = logging.getLogger('main_logger')

        try:
            import coloredlogs

            level_color_mapping = {
                'DEBUG': {'color': 'blue'},
                'INFO': {'color': 'green'},
                'WARNING': {'color': 'yellow', 'bold': True},
                'ERROR': {'color': 'red'},
                'CRITICAL': {'color': 'red', 'bold': True}
            }
            # 自定义日志的字段颜色
            field_color_mapping = dict(
                asctime=dict(color='green'),
                hostname=dict(color='magenta'),
                levelname=dict(color='white', bold=True),
                name=dict(color='blue'),
                programname=dict(color='cyan'),
                username=dict(color='yellow'),
            )

            coloredlogs.install(
                level=logging.DEBUG,
                logger=logger,
                milliseconds=True,
                datefmt='%X',
                fmt=self.fmt,
                level_styles=level_color_mapping,
                field_styles=field_color_mapping
            )
        except ModuleNotFoundError as e:
            logger.info("温馨提示：安装 coloredlogs 模块，可使得终端日志输出更好看~")

        return logger

    @classmethod
    def print_logger(cls):

        class PrintLogger(object):
            @staticmethod
            def debug(msg): print(msg)

            @staticmethod
            def info(msg): print(msg)

            @staticmethod
            def warn(msg): print(msg)

            @staticmethod
            def warning(msg): print(msg)

            @staticmethod
            def error(msg): print(msg)

            @staticmethod
            def critical(msg): print(msg)

        return PrintLogger()

    @staticmethod
    def _get_config():
        config_dict = {
            "logger_config": {
                "version": 1,
                "disable_existing_loggers": True,
                "formatters": {
                    "verbose": {
                        "format": "%(asctime)s.%(msecs)04d | %(levelname)8s | %(module)s | %(message)s",
                        # "format": "%(asctime)s.%(msecs)04d | %(levelname)8s | %(message)s | %(module)s | %(process:d)s | %(thread:d)s",
                        "style": "%"
                    },
                    "simple": {
                        "format": "%(asctime)s.%(msecs)04d | %(levelname)8s | %(message)s",
                        "style": "%"
                    }
                },
                "handlers": {
                    "console": {
                        "level": "INFO",
                        "class": "logging.StreamHandler",
                        "formatter": "simple"
                    },
                    "file": {
                        "level": "DEBUG",
                        "class": "my_logging.DailyRotatingFileHandler",
                        # "class": "logging.handlers.TimedRotatingFileHandler",
                        "filename": "log_files/log.log",
                        "when": "D",
                        "interval": 1,
                        "backupCount": 10,
                        # "suffix": "%Y%m%d.log",
                        "formatter": "verbose",
                        "encoding": "utf-8",
                    }
                },
                "loggers": {
                    "main_logger": {
                        "handlers": [
                            "console",
                            "file"
                        ],
                        "propagate": True,
                        "level": 'DEBUG'
                    }
                }
            }
        }

        return config_dict
