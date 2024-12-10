# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/11/20
contact: 【公众号】思维兵工厂
description: 处理微信端发送的 POST 请求
--------------------------------------------
"""

import os
import uuid
import time
import json
import random
import xmltodict
from typing import Optional, Tuple, Dict, List

from openai import OpenAI, AuthenticationError, PermissionDeniedError
from sqlalchemy import and_, or_, desc
from sqlalchemy.exc import PendingRollbackError

from .utils.weather import WeatherHandler
from .config import config, pro_logger, project_dir
from .types import WechatRequestData, WechatReplyData, WechatReactMessage
from .models import WechatUser, DatabaseHandler, WechatMessage, KeyWord
from .command import FIRST_FUNCTION_DICT, ALL_FUNCTION_DICT, check_keywords


class BasePostHandler(object):
    """处理接收到的POST请求"""

    def __init__(self, xml_dict: dict) -> None:

        self._wechat_user: Optional[WechatUser] = None
        self._database: Optional[DatabaseHandler] = None

        self.function_dict: dict = ALL_FUNCTION_DICT
        self.first_function_dict: dict = FIRST_FUNCTION_DICT

        self.current_command_key: str = '所处指令调用'  # 固定，用作数据库中存储指令的key

        self.current_command: str = ''  # 当前指令名称

        self.message_object: Optional[WechatMessage] = None  # 本次交互的消息对象

        self.request_data: WechatRequestData = WechatRequestData(xml_dict)  # 本次请求的用户消息
        self.reply_obj: WechatReplyData = WechatReplyData()  # 本次请求处理后的回复消息

        self.keywords_dict: Dict = {}  # 本地的关键词回复
        self.initialize_keywords()  # 加载本地关键词回复

    @property
    def database(self) -> DatabaseHandler:

        need_check_database = config.need_check_database if hasattr(config, 'need_check_database') and isinstance(
            config.need_check_database, bool) else True

        if not self._database or not isinstance(self._database, DatabaseHandler):
            self._database = DatabaseHandler(
                db_user=config.db_config.db_user,
                db_password=config.db_config.db_password,
                db_host=config.db_config.db_host,
                db_port=config.db_config.db_port,
                db_name=config.db_config.db_name,
                need_check_database=need_check_database
            )

        return self._database

    @property
    def wechat_user(self) -> WechatUser:

        if self._wechat_user and isinstance(self._wechat_user, WechatUser):
            return self._wechat_user

        user = self.database.session.query(WechatUser).filter(
            WechatUser.official_user_id == self.request_data.to_user_id,
            WechatUser.is_delete == 0
        ).first()

        if user:
            self._wechat_user = user
            return user

        # 创建新用户
        new_user = WechatUser(
            official_user_id=self.request_data.to_user_id,
            user_from=self.user_from,
            unique_user_id=uuid.uuid4().hex,
        )

        self.database.session.add(new_user)
        self.database.session.commit()
        self._wechat_user = new_user
        return self._wechat_user

    @property
    def user_from(self):
        return f'公众号：{config.wechat_config.app_name}'

    @property
    def real_reply_message(self) -> str:
        """
        解析self.reply_obj，生成最后的回复内容
        :return:
        """

        if self.reply_obj.msg_type == 'text':
            return self.make_reply_text(self.reply_obj.content)
        elif self.reply_obj.msg_type == 'image':
            return self.make_reply_picture(self.reply_obj.media_id)
        elif self.reply_obj.msg_type == 'voice':
            return self.make_reply_voice(self.reply_obj.media_id)
        else:
            return self.make_reply_text('该类型的回复逻辑暂未开发')

    @staticmethod
    def parse_history_message(messages: List[WechatReactMessage]) -> List[dict]:
        """
        解析消息列表，生成符合AI通讯要求的对话列表
        :param messages:
        :return:
        """

        msg_list = []

        repeat_msg = []

        for message in messages[::-1]:

            if message.receive_content in repeat_msg:
                continue
            else:
                repeat_msg.append(message.receive_content)

            msg_list.append({
                "role": "user",
                "content": message.receive_content
            })

            msg_list.append({
                "role": "assistant",
                "content": message.reply_content
            })

        return msg_list

    @staticmethod
    def get_ai_answer(question: str, history_message: List[Dict[str, str]] = None) -> Optional[str]:
        """
        调用AI接口，获取AI的回复
        :param question: 最新的提问文本
        :param history_message: 历史会话信息
        :return:
        """

        if not config.ai_config.is_valid():
            config.is_debug and pro_logger.error(f'AI鉴权信息不全，无法获取AI回复！')
            return

        if not history_message:
            history_message = []

        history_message.append({
            "role": "user",
            "content": question
        })

        history_message.insert(0, {
            "role": "system",
            "content": config.ai_config.system_prompt
        }) if config.ai_config.system_prompt else None

        config.is_debug and pro_logger.info(f'本次AI交互上下文是：')
        config.is_debug and pro_logger.info(f'{history_message}')

        # 防止访问错误重试两次
        for _ in range(3):

            api_key = random.choice(config.ai_config.key_list)
            model = config.ai_config.model_name

            try:
                client = OpenAI(api_key=api_key, base_url=config.ai_config.base_url)

                response = client.chat.completions.create(
                    model=model,
                    messages=history_message,
                    response_format={"type": "text"}
                )

                answer: str = response.choices[0].message.content

                if not answer:
                    config.is_debug and pro_logger.error(f'AI回复为空')
                    config.is_debug and pro_logger.info(f'响应信息：{response}')

                return answer
            except AuthenticationError:
                config.is_debug and pro_logger.error(f'AI密钥【{api_key}】已失效！', exc_info=True)
                config.ai_config.key_list.remove(api_key)
            except PermissionDeniedError:
                config.is_debug and pro_logger.error(f'AI密钥【{api_key}】无权限调用【{model}】模型！', exc_info=True)
                config.ai_config.key_list.remove(api_key)
            except:
                config.is_debug and pro_logger.error(f'获取AI回复时出现未知错误', exc_info=True)

            config.is_debug and pro_logger.warning(f'AI接口调用失败，正在尝试使用下一个密钥重试...')

    def initialize_keywords(self) -> None:
        """
        初始化本地关键词字典
        :return:
        """

        try:
            data_dir_path = os.path.join(project_dir, 'data')
            keywords_path = os.path.join(data_dir_path, 'keywords.json')
            if not os.path.exists(keywords_path):
                return

            with open(keywords_path, 'r', encoding='utf-8') as f:
                keywords_dict = json.load(f)

            if not isinstance(keywords_dict, dict):
                config.is_debug and pro_logger.error(f'关键词文件【keywords.json】格式错误，必须是字典格式，请检查！')
                return

            for k, v in keywords_dict.items():
                if not isinstance(k, str) or not isinstance(v, dict):
                    config.is_debug and pro_logger.error(f'关键词文件格式错误，键必须是字符串，值必须是字典，请检查！')
                    return

            for k, v in keywords_dict.items():

                if 'content' not in v:
                    config.is_debug and pro_logger.error(f'关键词【{k}】格式错误，值中必须包含content字段，请检查！')
                    continue

                if 'media_id' not in v:
                    config.is_debug and pro_logger.error(f'关键词【{k}】格式错误，值中必须包含media_id字段，请检查！')
                    continue

                if 'msg_type' not in v:
                    config.is_debug and pro_logger.error(f'关键词【{k}】格式错误，值中必须包含msg_type字段，请检查！')
                    continue

                self.keywords_dict[k.lower()] = v
            config.is_debug and pro_logger.info(f'关键词文件【keywords.json】解析成功，共{len(keywords_dict)}个关键词！')
        except:
            config.is_debug and pro_logger.error(f'关键词文件【keywords.json】解析出现未知错误！', exc_info=True)

    def check_keyword(self) -> bool:
        """
        检查是否为关键词自动回复
        :return: bool
        """

        config.is_debug and pro_logger.info(f'检查是否为关键词自动回复：[{self.request_data.content}]')

        if config.wechat_config.sep_char in self.request_data.content:
            config.is_debug and pro_logger.info(f'文本中包含分隔符，不是关键词自动回复')
            return False

        # 1. 先检查本地
        if self.request_data.content.lower() in self.keywords_dict:
            info_dict: Dict = self.keywords_dict[self.request_data.content.lower()]
            self.reply_obj.content = info_dict['content']
            self.reply_obj.media_id = info_dict['media_id']
            self.reply_obj.msg_type = info_dict['msg_type']
            return True

        # 2. 再检查云端数据库
        current_timestamp = int(time.time())
        keyword = self.database.session.query(KeyWord).filter(

            and_(

                or_(
                    KeyWord.keyword == self.request_data.content,
                    KeyWord.keyword == self.current_command_key,
                ),

                or_(
                    KeyWord.official_user_id == '系统',
                    KeyWord.official_user_id == self.request_data.to_user_id
                ),

                or_(
                    KeyWord.expire_time == 0,
                    current_timestamp <= KeyWord.expire_time
                )
            )
        ).order_by(desc(KeyWord.expire_time)).first()

        if not keyword:
            return False

        # 如果是指令调用，则记录当前指令
        if keyword.keyword == self.current_command_key:
            self.current_command = keyword.reply_content

            self.check_commands(self.current_command)
            return True

        # 如果是关键词回复，则获取回复内容
        self.reply_obj.content = keyword.reply_content
        self.reply_obj.msg_type = keyword.reply_type
        self.reply_obj.media_id = keyword.reply_media_id
        return True

    def close_database(self) -> None:
        """
        关闭数据库连接
        :return:
        """

        try:
            self.database.session.close()  # 关闭会话
        except:
            pro_logger.error(f"Error closing session!", exc_info=True)

    def get_history_message(self, limit: int = 5) -> List[WechatReactMessage]:
        """
        获取该用户最近几条通讯消息
        :param limit: 最大条数
        :return:
        """

        messages = self.database.session.query(WechatMessage).filter(
            WechatMessage.official_user_id == self.request_data.to_user_id,
            WechatMessage.user_from == self.user_from,
            WechatMessage.reply_type == 'text',

            WechatMessage.receive_content != '',
            # WechatMessage.receive_content != f'{config.sign_in_word}', # 暂时不忽略签到信息
            WechatMessage.receive_content.isnot(None),
            # not_(WechatMessage.receive_content.like(f'%{config.wechat_config.sep_char}%')), # 暂时不忽略指令调用信息

            WechatMessage.reply_content != '',
            WechatMessage.reply_content.isnot(None),
        ).order_by(desc(WechatMessage.receive_time)).limit(limit).all()

        message_list: List[WechatReactMessage] = []

        if messages:
            for message in messages:

                if not message.reply_content:
                    continue

                message_list.append(WechatReactMessage(
                    receive_content=message.receive_content,
                    reply_content=message.reply_content
                ))

        return message_list

    def check_message(self) -> Tuple[bool, bool]:
        """
        微信服务器在五秒内收不到响应会断掉连接，并且重新发起请求，总共重试三次。

        这个方法用于检查是否该条消息已经接收过：
            第一次接收：进行处理
            第二次或第三次接收：等待并获取第一次的处理结果
        :return: result and continue_flag
        """

        msg = self.database.session.query(WechatMessage).filter(
            WechatMessage.official_user_id == self.request_data.to_user_id,
            WechatMessage.receive_msg_id == self.request_data.msg_id,
            # WechatMessage.user_from == self.user_from
        ).first()

        if not msg:
            config.is_debug and pro_logger.info('该条消息从未处理过')
            self.save_message(has_handled=False)
            return False, True

        self.message_object = msg

        config.is_debug and pro_logger.info(f'该条消息已有记录，检查是否处理完成。reply_type: [{msg.reply_type}]')
        if msg.reply_type:
            self.reply_obj.msg_type = msg.reply_type
            self.reply_obj.content = msg.reply_content
            self.reply_obj.media_id = msg.reply_media_id

            config.is_debug and pro_logger.info('该条消息已处理过，直接返回')
            return True, True

        waiting_time = 0
        retry_time = config.retry_time or 1
        if not isinstance(retry_time, int):
            retry_time = 1

        while waiting_time < 5:
            config.is_debug and pro_logger.info('该条消息正在处理中，等待前一次处理完成')
            time.sleep(retry_time)
            waiting_time += retry_time

            msg = self.database.session.query(WechatMessage).filter(
                WechatMessage.official_user_id == self.request_data.to_user_id,
                WechatMessage.receive_msg_id == self.request_data.msg_id,
                # WechatMessage.user_from == self.user_from
            ).first()

            if msg.reply_type:
                self.reply_obj.msg_type = msg.reply_type
                self.reply_obj.content = msg.reply_content
                self.reply_obj.media_id = msg.reply_media_id
                return True, True

        # 超过5秒，微信将重新发送请求
        return False, False

    def save_message(self, has_handled: bool = True):

        try:
            if not has_handled:
                msg = WechatMessage(
                    official_user_id=self.request_data.to_user_id,
                    receive_content=self.request_data.content,
                    receive_media_id=self.request_data.media_id,
                    receive_msg_id=self.request_data.msg_id,
                    receive_time=self.request_data.create_time,
                    user_from=self.user_from
                )

                self.message_object = msg
                self.database.session.add(msg)
                logger_msg = '本次请求已记录'
            else:
                self.message_object.reply_content = self.reply_obj.content
                self.message_object.reply_media_id = self.reply_obj.media_id
                self.message_object.reply_type = self.reply_obj.msg_type
                logger_msg = f'本次交互信息已存入数据库'

            self.database.session.commit()
            config.is_debug and pro_logger.info(logger_msg)
        except PendingRollbackError:
            # 发生错误时回滚事务
            self.database.session.rollback()
            # 重试操作，或者重新启动事务
            self.database.session.commit()
        except Exception:
            pro_logger.info(self.reply_obj)
            pro_logger.error(f'将交互信息写入数据库时出现错误', exc_info=True)

    def text(self) -> None:
        """处理接收到的文本信息"""
        self.reply_obj.content = self.request_data.content

    def event(self) -> None:
        """处理接收到的事件信息"""

        self.reply_obj.content = "Please wait for event development"
        if self.request_data.event_type == 'subscribe':
            self.reply_obj.content = config.wechat_config.subscribe_greeting or "欢迎关注，这是一个有趣的公众号哦~"

    def image(self) -> None:
        """
        处理接收到的图片信息，在微信的文本信息中：
            PicUrl	图片链接（由系统生成）
            MediaId	图片消息媒体id，可以调用获取临时素材接口拉取数据。
        :return:
        """
        self.reply_obj.msg_type = 'image'
        self.reply_obj.media_id = self.request_data.media_id

    def file(self):
        """处理文件信息"""
        self.reply_obj.content = "Please wait for file development"

    def voice(self) -> None:
        """处理语音信息"""
        self.reply_obj.msg_type = 'voice'
        self.reply_obj.media_id = self.request_data.media_id

    def video(self) -> None:
        """处理视频信息"""
        self.reply_obj.content = "Please wait for video development"

    def shortvideo(self) -> None:
        """处理短视频信息"""
        self.reply_obj.content = "Please wait for shortvideo development"

    def location(self) -> None:
        """处理位置信息"""
        msg = f"----您当前位置----\n\n经度：{self.request_data.location_y};\n纬度：{self.request_data.location_x}"
        self.reply_obj.content = msg

    def link(self) -> None:
        """处理链接信息"""
        self.reply_obj.content = "Please wait for link development"

    def unknown(self) -> None:
        """处理未知信息"""
        self.reply_obj.content = "未知请求，请联系管理员"

    def make_reply_text(self, content: str) -> str:
        """
        接收文本，生成符合微信服务器要求的文本信息
        :param content:
        :return:
        """

        time_stamp = int(time.time())

        resp_dict = {
            'xml': {
                'ToUserName': self.request_data.to_user_id,
                'FromUserName': self.request_data.my_user_id,
                'CreateTime': time_stamp,
                'MsgType': 'text',
                'Content': content[0:600],  # 注意：微信的文本回复有长度限制，最多600字，此处做兜底处理。
            }
        }
        resp_xml = xmltodict.unparse(resp_dict)
        return resp_xml

    def make_reply_picture(self, media_id: str) -> str:
        """
        接收图片的media_id（该值在图片上传到腾讯服务器后获取）
        生成符合微信服务器要求的图片回复信息
        :param media_id:
        :return:
        """

        time_stamp = int(time.time())

        resp_dict = {
            'xml': {
                'ToUserName': self.request_data.to_user_id,
                'FromUserName': self.request_data.my_user_id,
                'CreateTime': time_stamp,
                'MsgType': 'image',
                'Image': {
                    'MediaId': media_id
                },
            }
        }
        resp_xml = xmltodict.unparse(resp_dict)
        return resp_xml

    def make_reply_voice(self, media_id: str) -> str:
        """
        接收图片的media_id（该值在图片上传到腾讯服务器后获取）
        生成符合微信服务器要求的图片回复信息
        :param media_id:
        :return:
        """

        time_stamp = int(time.time())

        resp_dict = {
            'xml': {
                'ToUserName': self.request_data.to_user_id,
                'FromUserName': self.request_data.my_user_id,
                'CreateTime': time_stamp,
                'MsgType': 'voice',
                'Voice': {
                    'MediaId': media_id
                },
            }
        }
        resp_xml = xmltodict.unparse(resp_dict)
        return resp_xml

    def check_commands(self, command: str = None, *args, **kwargs) -> bool:

        if not command:
            command = self.request_data.content

        result: WechatReplyData = check_keywords(
            first_function_dict=self.first_function_dict,
            function_dict=self.function_dict,
            keyword=command,
            user=self.wechat_user,
            user_from=self.user_from,
            post_handler=self,
            *args, **kwargs
        )

        if result:
            self.reply_obj = result
            return True
        return False


class PostHandler(BasePostHandler):

    def text(self) -> None:
        """处理接收到的文本信息"""

        # 1. 检查是否是指令调用
        if self.check_commands():
            return

        # 2. 尝试获取AI回复
        config.is_debug and pro_logger.info(f"未匹配到关键词回复，尝试获取AI回复...")

        msg_limit = config.history_message_limit
        message = self.parse_history_message(self.get_history_message(msg_limit))
        ai_answer = self.get_ai_answer(self.request_data.content, message)

        if ai_answer:
            config.is_debug and pro_logger.info(f"AI回复：{ai_answer}")
            self.reply_obj.content = ai_answer
            return

        self.reply_obj.content = self.request_data.content

    def image(self) -> None:
        """
        处理接收到的图片信息，在微信的文本信息中：
            PicUrl	图片链接（由系统生成）
            MediaId	图片消息媒体id，可以调用获取临时素材接口拉取数据。
        :return:
        """

        if self.current_command and self.check_commands(self.current_command):
            return

        self.reply_obj.msg_type = 'text'
        self.reply_obj.content = self.request_data.pic_url

    def location(self) -> None:
        """处理位置信息"""

        if not config.caiyun_token:
            self.reply_obj.content = "请先配置彩云天气token，否则无法获取天气信息"
            return

        weather_tip = WeatherHandler.caiyun_weather(
            longitude=self.request_data.location_y,
            latitude=self.request_data.location_x,
            token=config.caiyun_token,
            hour_num=config.weather_show_hours,
            logger=pro_logger
        )

        self.reply_obj.content = weather_tip
