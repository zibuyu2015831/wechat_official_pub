# -*- coding: utf-8 -*-
from builtins import ModuleNotFoundError
from datetime import datetime
import logging.handlers
import logging.config
import logging
import json
import os


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


class MyConfig(object):

    def __init__(self):

        # 程序根目录
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # 1. 读取配置
        config_dir_path = os.path.join(self.base_path, 'config')
        if not os.path.exists(config_dir_path):
            raise Exception("配置文件夹【config】不存在，程序终止。")

        config_file_path = os.path.join(config_dir_path, "wechat.json")
        if not os.path.exists(config_file_path):
            raise Exception("配置文件【config.json】不存在，程序终止。")

        with open(config_file_path, mode='r', encoding='utf8') as read_f:
            self._config = json.load(read_f)

        self._logger = None

    @property
    def config(self) -> dict:
        return self._config

    @property
    def logger(self) -> logging.Logger:
        if not self._logger:
            self._logger = self.make_logger()

        return self._logger

    def make_logger(self, logger_name: str = 'main_logger') -> logging.Logger:
        # 从配置信息中，获取关于日志的配置
        logger_config = self.config.get('logger_config')
        # 如果找不到关于日志的配置，使用默认配置
        if not logger_config:
            logger_config = self._get_config().get('logger_config')

        # 设置日志存放目录
        log_file_path = os.path.join(self.base_path, 'log_files')
        if not os.path.exists(log_file_path):
            os.mkdir(log_file_path)

        logging.config.dictConfig(logger_config)
        logger = logging.getLogger(logger_name)

        fmt = "%(asctime)s.%(msecs)04d | %(levelname)8s | %(module)s | %(message)s "

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
                fmt=fmt,
                level_styles=level_color_mapping,
                field_styles=field_color_mapping
            )
        except ModuleNotFoundError as e:
            logger.info("温馨提示：安装 coloredlogs 模块，可使得终端日志输出更好看~")

        return logger

    def _get_config(self) -> dict:

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
                        "class": "function.config.DailyRotatingFileHandler",
                        # "class": "logging.handlers.TimedRotatingFileHandler",
                        "filename": f"{self.base_path}/log_files/log.log",
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
