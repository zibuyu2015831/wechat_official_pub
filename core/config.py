# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/11/20
contact: 【公众号】思维兵工厂
description: 加载项目配置信息
--------------------------------------------
"""

from .error import NotConfigError, ConfigError
from .types import ConfigData, AiConfig, DBConfig, WechatConfig, QiNiuConfig, YunFuncTTSConfig, BaiDuConfig

from builtins import ModuleNotFoundError
from dataclasses import asdict
from typing import Optional
import logging.handlers
import logging.config
import datetime
import logging
import json
import sys
import os

# 将package包路径添加到系统路径中，方便使用云函数部署时导入依赖
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
package_dir = os.path.join(project_dir, 'package')

if os.path.exists(package_dir):
    sys.path.insert(0, package_dir)


class ProjectConfig(object):
    """
    项目配置信息类
    """

    def __init__(self, logger: logging.Logger = None, log_dir_name: str = 'logs'):

        # 程序根目录
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self._config_dict: Optional[dict] = None  # 配置原字典
        self._config_obj: Optional[ConfigData] = None  # 配置对象
        self._logger: Optional[logging.Logger] = None  # 日志对象

        if logger and isinstance(logger, logging.Logger):
            self._logger = logger

        self.log_dir_name = log_dir_name

        self.check_config()

    def check_config(self):
        """检查配置文件所在目录是否存在"""

        config_dir_path = os.path.join(self.base_path, 'config')
        if not os.path.exists(config_dir_path):
            raise NotConfigError("配置文件夹【config】不存在，程序终止。")

        self.check_config_file()
        self.update_config_from_env()
        self.parse_config()

    @staticmethod
    def check_word(key):
        """检查给定值是否为bool、None等类型"""

        if key == 'True':
            return True

        if key == 'true':
            return True

        if key == 'False':
            return False

        if key == 'false':
            return False

        if key == 'null':
            return None

        if key == 'None':
            return None
        return key

    def update_config_from_env(self):
        """从环境变量中读取配置信息，更新config.json里的配置"""

        for k, v in self._config_dict.items():

            if isinstance(v, list) or isinstance(v, tuple) or isinstance(v, set):
                continue

            if not isinstance(v, dict):
                self._config_dict[k] = self.check_word(os.environ.get(k)) or v
                continue

            for kk, vv in v.items():
                if isinstance(vv, list) or isinstance(vv, dict) or isinstance(v, tuple) or isinstance(v, set):
                    continue

                self._config_dict[k][kk] = self.check_word(os.environ.get(f'{k}__{kk}')) or vv

        key_list_str = os.environ.get('key_list')
        if not key_list_str:
            return

        try:
            key_list = json.loads(key_list_str)

            for key in key_list:
                if not isinstance(key, str):
                    return

            self._config_obj.ai_config.key_list = key_list
        except:
            self._config_dict.get("is_debug") and self.logger.error("环境变量【key_list】配置不正确，无法解析，请检查。")

    def check_config_file(self):
        """检查配置文件是否存在"""

        config_dir_path = os.path.join(self.base_path, 'config')
        config_file_path = os.path.join(config_dir_path, "config.json")
        if not os.path.exists(config_file_path):
            demo_config = ConfigData()
            with open(config_file_path, mode='w', encoding='utf8') as wf:
                json.dump(asdict(demo_config), wf, ensure_ascii=False, indent=4)

            raise NotConfigError("配置文件【config.json】不存在，程序终止。")

        with open(config_file_path, mode='r', encoding='utf8') as read_f:
            self._config_dict = json.load(read_f)

    def parse_qiniu_config(self):
        """解析七牛云配置信息"""
        self._config_obj.qiniu_config = QiNiuConfig()
        qiniu_config = self._config_dict.get('qiniu_config', {})

        if len(qiniu_config) != 4:
            self._config_obj.is_debug and self.logger.error("配置文件【config.json】中，qiniu_config配置不正确，请检查。")
            return

        if not all(k in qiniu_config for k in ['access_key', 'secret_key', 'bucket_name', 'bucket_domain']):
            self._config_obj.is_debug and self.logger.error("配置文件【config.json】中qiniu_config配置不正确，请检查。")
            return

        self._config_obj.qiniu_config = QiNiuConfig(**qiniu_config)

    def parse_wechat_config(self):
        """解析微信配置信息"""

        self._config_obj.wechat_config = WechatConfig()
        wechat_config = self._config_dict.get('wechat_config', {})

        if not wechat_config:
            self._config_obj.is_debug and self.logger.info("配置文件【config.json】中，未配置wechat_config信息!")
            raise ConfigError()

        if len(wechat_config) != 7:
            self._config_obj.is_debug and self.logger.error("配置文件【config.json】中，wechat_config缺少必须项，请检查。")
            raise ConfigError()

        if not all(k in wechat_config for k in ['app_id', 'app_secret', 'app_name', 'wechat_token', 'sep_char']):
            self._config_obj.is_debug and self.logger.error("配置文件【config.json】中，wechat_config配置不正确，请检查。")
            raise ConfigError()

        self._config_obj.wechat_config = WechatConfig(**wechat_config)

        if not self._config_obj.wechat_config.is_valid():
            raise ConfigError()

    def parse_db_config(self):
        """解析数据库配置信息"""

        self._config_obj.db_config = DBConfig()
        db_config = self._config_dict.get('db_config', {})

        if not db_config:
            self._config_obj.is_debug and self.logger.info(
                "配置文件【config.json】中，未配置db_config信息，使用sqlite数据库!")
            return

        if len(db_config) != 6:
            self._config_obj.is_debug and self.logger.error("配置文件【config.json】中，db_config配置不正确，请检查。")
            return

        if not all(k in db_config for k in ['db_type', 'db_host', 'db_port', 'db_name', 'db_user', 'db_password']):
            self._config_obj.is_debug and self.logger.error("配置文件【config.json】中，db_config配置不正确，请检查。")
            return

        self._config_obj.db_config = DBConfig(**db_config)

    def parse_ai_config(self):
        """解析AI配置信息"""

        self._config_obj.ai_config = AiConfig()
        ai_config = self._config_dict.get('ai_config', {})

        if not ai_config:
            self._config_obj.is_debug and self.logger.info(
                "配置文件【config.json】中，未配置ai_config信息，AI通讯功能无法使用!")
            return

        if len(ai_config) != 4:
            self._config_obj.is_debug and self.logger.error("配置文件【config.json】中，ai_config配置不正确，请检查。")
            return

        if not all(k in ai_config for k in ['key_list', 'base_url', 'model_name']):
            self._config_obj.is_debug and self.logger.error("配置文件【config.json】中，ai_config配置不正确，请检查。")
            return

        self._config_obj.ai_config = AiConfig(**ai_config)

    def parse_yun_tts_config(self):
        """解析云函数关于文字转语音的配置信息"""

        self._config_obj.yun_func_tts_config = YunFuncTTSConfig()

        yun_func_tts_config = self._config_dict.get('yun_func_tts_config', {})

        if len(yun_func_tts_config) != 5:
            self._config_obj.is_debug and self.logger.error(
                "配置文件【config.json】中，yun_func_tts_config配置不正确，请检查。")
            return

        if not all(k in yun_func_tts_config for k in ['func_token', 'func_url']):
            self._config_obj.is_debug and self.logger.error(
                "配置文件【config.json】中，yun_func_tts_config配置不正确，请检查。")
            return

        self._config_obj.yun_func_tts_config = YunFuncTTSConfig(**yun_func_tts_config)

    def parse_baidu_config(self):
        """解析百度云配置信息"""
        self._config_obj.baidu_config = BaiDuConfig()

        baidu_config = self._config_dict.get('baidu_config', {})

        if len(baidu_config) != 2:
            self._config_obj.is_debug and self.logger.error("配置文件【config.json】中，baidu_config配置不正确，请检查。")
            return

        if not all(k in baidu_config for k in ['api_key', 'secret_key']):
            self._config_obj.is_debug and self.logger.error(
                "配置文件【config.json】中，baidu_config配置不正确，请检查。")
            return

        self._config_obj.baidu_config = BaiDuConfig(**baidu_config)

    def parse_config(self):
        """解析配置文件AiConfig"""

        self._config_obj = ConfigData(**self._config_dict)

        self.parse_wechat_config()  # 加载微信配置信息
        self.parse_ai_config()  # 加载AI配置信息
        self.parse_db_config()  # 加载数据库配置信息
        self.parse_qiniu_config()  # 加载七牛云对象存储配置信息
        self.parse_yun_tts_config()  # 加载云函数关于文字转语音的配置信息
        self.parse_baidu_config()  # 加载百度配置信息（OCR功能）

    @property
    def config(self) -> ConfigData:
        return self._config_obj

    @property
    def logger(self) -> logging.Logger:

        if not self._logger:
            self._logger = self.make_logger()

        return self._logger

    def make_logger(self, logger_name: str = 'main_logger') -> logging.Logger:

        # 从配置信息中，获取关于日志的配置
        logger_config = self.config.logger_config

        # 如果找不到关于日志的配置，使用默认配置
        if not logger_config:
            logger_config = self.default_logger_config

        # 设置日志存放目录
        log_file_path = os.path.join(self.base_path, self.log_dir_name)
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
        except ModuleNotFoundError:
            logger.info("温馨提示：安装 coloredlogs 模块，可使得终端日志输出更好看~")

        return logger

    @property
    def default_logger_config(self) -> dict:

        current_data = datetime.datetime.now().strftime('%Y%m%d')

        config_dict = {
            "version": 1,
            "disable_existing_loggers": True,
            "formatters": {
                "verbose": {
                    "format": "%(asctime)s.%(msecs)04d | %(levelname)8s | %(module)s | %(message)s",
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
                    "class": "core.utils.logger_handler.DailyRotatingFileHandler",
                    # "class": "logging.handlers.TimedRotatingFileHandler",
                    "filename": f"{self.base_path}/{self.log_dir_name}/log_{current_data}.log",
                    "when": "D",
                    "interval": 1,
                    "backupCount": 10,
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

        # 如果是使用云函数部署，则关闭日志文件，只输出到控制台
        if self._config_obj.is_yun_function:
            config_dict['loggers']['main_logger']['handlers'].remove('file')
            config_dict['handlers'].pop('file')

        return config_dict


config_obj = ProjectConfig()

config = config_obj.config
pro_logger = config_obj.logger
