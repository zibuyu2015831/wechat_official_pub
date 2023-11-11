# -*- coding: utf-8 -*-
import os
import re
import json
import time
import datetime
import threading
import requests
import xmltodict
from pathlib import Path
from utils.spark_gpt import SparkGPT
from basic.my_config import config
from basic.my_logging import MyLogging
from aligo import Aligo, set_config_folder  # 自己修改后的Aligo
from concurrent.futures import ThreadPoolExecutor


class ReplyHandler(MyLogging):

    def __init__(self, xml_dict: dict) -> None:
        super().__init__()

        # 用户post请求中的数据
        self.xml_dict = xml_dict

        # 逐一获取微信POST请求中携带的参数
        self.my_user_id = xml_dict.get('ToUserName')  # 获取消息的接收者，为本次回复的发送者
        self.to_user_id = xml_dict.get('FromUserName')  # 获取消息的发送者，为本次回复的接收者
        self.create_time = xml_dict.get('CreateTime')  # 获取本次消息的消息创建时间 （整型）（时间戳）
        self.msg_id = xml_dict.get('MsgId')  # 消息id，64位整型
        self.msg_type = xml_dict.get('MsgType')  # 获取本次消息的MsgType
        self.msg_data_id = xml_dict.get('MsgDataId')  # 消息的数据ID（消息如果来自文章时才有）
        self.idx = xml_dict.get('Idx')  # 多图文时第几篇文章，从1开始（消息如果来自文章时才有）
        # 以上七个为基础字段，任何一种类型的消息都会携带
        # 以下为特殊字段，特定的消息类型才会携带
        self.content = xml_dict.get('Content')  # MsgType为text时包含此字段：本次消息的文本内容
        self.pic_url = xml_dict.get('PicUrl')  # MsgType为image时包含此字段：图片链接（由系统生成），该链接保存3天
        self.format = xml_dict.get('Format')  # MsgType为voice时包含此字段：语音消息的语音格式，如amr，speex等
        self.media_id = xml_dict.get('MediaId')  # MsgType为image、voice、video、shortvideo时包含此字段：可以调用获取临时素材接口拉取数据。
        self.thumb_media_id = xml_dict.get('ThumbMediaId')  # MsgType为video、shortvideo时包含此字段：视频消息缩略图的媒体id，可以调用下载接口拉取数据。
        # 以下为链接消息特有字段
        self.title = xml_dict.get('Title')  # MsgType为link时包含此字段：消息标题
        self.description = xml_dict.get('Description')  # MsgType为link时包含此字段：消息描述
        self.url = xml_dict.get('Url')  # MsgType为link时包含此字段：消息链接
        # 以下为地理位置信息（location）特有字段
        self.location_x = xml_dict.get('Location_X')  # MsgType为location时包含此字段：地理位置纬度
        self.location_y = xml_dict.get('Location_Y')  # MsgType为location时包含此字段：地理位置经度
        self.scale = xml_dict.get('Scale')  # MsgType为location时包含此字段：地图缩放大小
        self.label = xml_dict.get('Label')  # MsgType为location时包含此字段：地理位置信息
        # 获取事件类型
        self.event_type = xml_dict.get('Event')  # 关注：subscribe；取消关注：unsubscribe等
        self.event_key = xml_dict.get('EventKey')  # 事件的EventKey

        self.logger.info(f"用户id：【{self.to_user_id}】")
        self.logger.info(f"本次消息的MsgId：【{self.msg_id}】")
        self.logger.info(f"本次消息的create_time：【{self.create_time}】")

        # 配置信息
        self.config_dict = config

        # 从配置文件中获取ai通话时记住的历史会话数量
        user_talk_num = self.config_dict.get('wechat', {}).get('user_talk_num')
        if isinstance(user_talk_num, int):  # 如果配置文件中没有设置，默认记住5条AI会话记录
            self.user_talk_num = user_talk_num
        else:
            self.user_talk_num = 3

        # 从配置文件中获取ai通话时历史会话的时间限制
        user_time_limit = self.config_dict.get('wechat', {}).get('user_time_limit')
        if isinstance(user_time_limit, int):  # 如果配置文件中没有设置，默认记住30分钟内的AI会话记录
            self.user_time_limit = user_time_limit
        else:
            self.user_time_limit = 1800

        # 从配置文件中获取短指令的时间限制
        short_cmd_time_limit = self.config_dict.get('wechat', {}).get('short_cmd_limit_time')
        if isinstance(short_cmd_time_limit, int):  # 如果配置文件中没有设置，默认短指令有效时间为10分钟
            self.short_cmd_time_limit = short_cmd_time_limit
        else:
            self.short_cmd_time_limit = 600

        self.ali_user_file_id = ''  # 阿里云盘中存储用户历史会话信息的文件id
        self.ali_user_file_download_url = ''  # 阿里云盘中存储用户历史会话信息的文件下载直链

        self.reply_content_full = ''  # 本次回应的完整信息xml格式
        self.reply_content_text = ''  # 本次回应的文本信息，字符串
        self.ai_talk_text = dict()  # 本次通讯的ai会话记录，如果有的话
        self.short_cmd = ''  # 本次接收的短指令，如果有的话
        self.ocr_text_list = []  # 本次通讯的ocr结果，如果有的话
        self.voice2text_keyword = {}  # 本次通讯的ocr结果，如果有的话
        self.user_file_name = f"{self.to_user_id}.json"  # 历史会话信息的文件名称

        # Aligo相关配置：后续考虑优化：将配置统一为整个config.json文件
        aligo_config_path = Path.cwd() / 'config'
        set_config_folder(str(aligo_config_path.absolute()))
        self.ali_obj = Aligo(logger=self.logger)

        # 从阿里云盘获取历史消息
        self.user_data = self.get_user_data_from_alipan() or {}

    # 处理文本信息
    def text(self) -> str:
        """处理接收到的文本信息"""

        # 获取短指令分隔符号
        sep_char = self.config_dict.get('wechat').get('sep_char')

        from .handle_text import TextHandler
        # 文本处理者
        handler = TextHandler()

        try:
            # 判断是否为【短指令】调用：短指令处理文本本身，以是否包含用户输入的分隔符来确定
            if sep_char in self.content:
                func_name, content = self.content.split(sep_char, maxsplit=1)

                # 判断是否携带参数
                if sep_char in content:
                    final_content, second_key = content.split(sep_char, maxsplit=1)
                else:
                    final_content = content
                    second_key = ""

                if func_name in handler.function_mapping:
                    handle_function = getattr(handler, handler.function_mapping[func_name])
                    self.reply_content_full = handle_function(self, final_content, second_key)
                else:
                    self.reply_content_full = self.make_reply_text("暂无此功能")

            # 判断是否【指令】调用：指令模式处理其他格式的信息
            elif self.content in self.config_dict.get('wechat', {}).get('short_commend'):
                handle_function = getattr(handler, handler.function_mapping[self.content])
                self.reply_content_full = handle_function(self, self.content)

            else:  # AI对话

                # 实例化ai
                ai = SparkGPT(self.config_dict.get('spark_info'), logger_obj=self.logger)

                # 添加历史会话
                self.add_user_history(ai)

                # 获取ai回答
                reply_content_text = ai.ask(self.content)

                # 记录ai回答，元组类型，元素有两个：时间戳+回答
                self.ai_talk_text['msg_time'] = int(time.time())
                self.ai_talk_text['msg_list'] = self.make_ai_one_talk(self.content, reply_content_text)

                # 生成符合微信服务器要求的回复信息
                self.reply_content_full = self.make_reply_text(reply_content_text)
                # 保存新生成的会话信息
                self._save_user_data()

            return self.reply_content_full
        except Exception as e:
            self.logger.error(f"本次通讯出现错误，用户输入的文本是：【{self.content}】", exc_info=True)
            return self.make_reply_text("Something wrong had happened!")

    # 处理事件信息
    def event(self) -> str:
        if self.event_type == 'subscribe':
            default_greeting = "欢迎关注，这是一个有趣的公众号哦~"
            subscribe_greeting = self.config_dict.get('wechat', {}).get('subscribe_greeting', default_greeting)
            return self.make_reply_text(subscribe_greeting)
        return self.make_reply_text("Please wait for event development")

    # 处理图片信息
    def image(self) -> str:
        """
        处理接收到的图片信息，在微信的文本信息中：
            PicUrl	图片链接（由系统生成）
            MediaId	图片消息媒体id，可以调用获取临时素材接口拉取数据。
        :return:
        """
        from .handle_image import ImageHandler
        # 图片处理者
        handler = ImageHandler()
        store_thread = handler.store_image(self)

        # 获取当前时间
        now_timestamp = int(time.time())
        # 获取用户历史数据文件中存储的指令与时间
        short_cmd_time, user_short_cmd = self.user_data.get("short_command", [0, None])
        # 判断用户的指令时间是否过期
        if short_cmd_time + self.short_cmd_time_limit < now_timestamp:
            user_short_cmd = None

        # 获取user_data中的short_command：当前短指令
        # if self.user_data.get("short_command"):
        #     # 注意user_data中的short_command，是列表格式，第一个元素是时间戳，第二个元素是指令
        #     short_cmd_time, user_short_cmd = self.user_data.get("short_command")
        # else:
        #     user_short_cmd = ''

        if user_short_cmd:
            if user_short_cmd in handler.function_mapping:
                handle_function = getattr(handler, handler.function_mapping[user_short_cmd])
                self.reply_content_full = handle_function(self)
            else:
                type_error_msg = f"当前为指令模式：【{user_short_cmd}】\n无法处理{self.msg_type}格式信息！\n\n请先输入【退出】，以退出指令模式。"
                self.reply_content_full = self.make_reply_text(type_error_msg)
        else:
            self.reply_content_full = self.make_reply_text(f"该图片的临时链接为：\n\n{self.pic_url}")

        self._save_user_data()
        # store_thread.join()  # 等待保存图片的进程完成再返回回复
        return self.reply_content_full
        # return self.make_reply_text("Please wait for image development")

    def file(self):
        """处理文件信息"""
        return self.make_reply_text("Please wait for file development")

    # 处理语音信息
    def voice(self) -> str:
        # media_id = 'x6lBIVCeGMg_tlN-qAPFWmyoRYMfgDrZcAEXIyu7ReM1cbdvXzrEqqsrAV-95c_X'
        # return self.make_reply_voice(media_id)
        return self.make_reply_text("Please wait for voice development")

    def video(self) -> str:
        """处理视频信息"""
        return self.make_reply_text("Please wait for video development")

    def shortvideo(self) -> str:
        """处理短视频信息"""
        return self.make_reply_text("Please wait for shortvideo development")

    def location(self) -> str:
        """处理位置信息"""
        weather_tip = self.weather_request(self.location_y, self.location_x)
        self.reply_content_full = self.make_reply_text(weather_tip)
        return self.reply_content_full
        # return self.make_reply_text("Please wait for location development")

    def link(self) -> str:
        """处理链接信息"""
        return self.make_reply_text("Please wait for link development")

    def delete_ali_file(self) -> None:
        for i in range(2):
            try:
                self.ali_obj.move_file_to_trash(self.ali_user_file_id)
                self.logger.info("删除旧的会话数据文件！")
                return
            except Exception as e:
                self.logger.error("旧的会话数据文件删除失败！", exc_info=True)

    def upload_ali_file(self, file_path, parent_file_id: str = 'root', msg: str = "向阿里云盘上传文件"):
        for i in range(2):
            try:
                self.ali_obj.upload_file(file_path, parent_file_id)
                self.logger.info(msg)
                return
            except Exception as e:
                self.logger.error("文件上传失败！", exc_info=True)

    def _save_user_data(self):
        """
        当一次通讯结束之后，删除用户原来的数据文件，重新生成新的数据文件，并上传阿里云盘；
        执行流程：
            1. 先删除原有文件；
            2. 如果用户有历史数据信息，检测并存储其中为过期的信息到新的历史数据文件中；
            3. 在新的历史数据文件中，增加本次请求的信息；
        :return:
        """

        # 1. 保存文件前，先删除原有文件
        self.delete_ali_file()

        new_user_ai_talk = []
        new_short_command = [0, None]

        # 如果用户有历史数据，检测、保留历史数据中未过期的数据
        if self.user_data:
            # 1. 检查user_ai_talk，保留未过期的AI对话
            user_ai_talk = self.user_data.get('user_ai_talk')
            now_timestamp = int(time.time())

            for item in user_ai_talk[-self.user_talk_num:]:
                msg_time = item['msg_time']

                if msg_time + self.user_time_limit > now_timestamp:
                    new_user_ai_talk.append(item)

            # 2. 检查短指令是否过期
            old_short_command = self.user_data.get('short_command')
            if old_short_command:
                if old_short_command[0] + self.short_cmd_time_limit > now_timestamp:
                    new_short_command = old_short_command

        # 如果本次通讯是AI会话，记住AI会话
        if self.ai_talk_text:
            new_user_ai_talk.append(self.ai_talk_text)

        # 如果本次通讯用户是输入了短指令，记住短指令
        if self.short_cmd == "无":
            new_short_command = [int(time.time()), '']
        elif self.short_cmd:
            new_short_command = [int(time.time()), self.short_cmd]

        # 获取原历史数据中的关键字回复
        keyword_reply = self.user_data.get('keyword_reply', {})
        # 如果有图片ocr结果，存储新的关于ocr结果的关键词回复
        if self.ocr_text_list:
            for index, paragraph in enumerate(self.ocr_text_list):
                keyword_reply[f"获取ocr结果第{index + 1}页"] = paragraph

        # 添加上文本转语音的关键字回复
        keyword_reply.update(self.voice2text_keyword)

        content = {
            'user_id': self.to_user_id,
            'last_msg_id': self.msg_id,
            'last_msg_reply': self.reply_content_full,
            "short_command": new_short_command,
            'user_ai_talk': new_user_ai_talk,
            "keyword_reply": keyword_reply,
        }

        file_dir_path = Path.cwd() / 'data' / 'user_data'
        file_path = file_dir_path / f"{self.to_user_id}.json"

        with open(file_path, mode="w", encoding='utf8') as f:
            f.write(json.dumps(content))
        user_data_dir = self.config_dict.get('aliyun', "").get('user_data_dir')

        self.logger.info("上传新的用户数据文件......")
        self.upload_ali_file(file_path, parent_file_id=user_data_dir, msg="用户数据文件上传成功！")

    def save_user_data(self) -> threading.Thread:
        """
        新开一个线程去保存历史会话信息
        :return:
        """
        save_content_thread = threading.Thread(target=self._save_user_data)
        save_content_thread.start()
        return save_content_thread

    def download_user_data(self, url):
        for i in range(3):
            try:
                response = requests.get(url, headers={
                    'Referer': 'https://www.aliyundrive.com/',
                })
                self.logger.info("用户历史数据文件下载完成")
                return response.content
            except Exception as e:
                self.logger.error(f"用户历史数据下载出现错误，重试中", exc_info=True)

    def get_ali_file_info(self) -> dict:
        """
        发送Aligo请求，获取阿里云盘中，所有用户历史数据文件的文件标题与url信息
        构建成字典并返回
        :return:
        """
        # 从配置信息中获取阿里云盘存放用户数据的文件夹id
        dir_id = self.config_dict.get('aliyun', {}).get('user_data_dir')
        # 如果用户不配置历史数据存放文件夹，则跳过
        if not dir_id:
            return {}

        # 获取阿里云盘中的文件信息可能由于网络原因导致失败，重试三次
        for i in range(3):
            try:
                self.logger.info(f"获取阿里云盘中所有用户的历史数据文件")
                files = self.ali_obj.get_file_list(dir_id)

                file_dict = {}
                for file in files:
                    file_dict[file.name] = {'file_id': file.file_id, "download_url": file.download_url}

                return file_dict
            except Exception as e:
                self.logger.error(f"所有用户的历史数据文件时出现错误，即将重试！", exc_info=True)

        return {}

    def get_user_data_from_alipan(self) -> dict:
        """
        1. 从阿里云盘中获取所有用户历史数据文件的标题与url信息；
        2. 判断用户是否有历史数据文件（历史数据文件在阿里云盘中，以【用户微信id.json】的文件名保存）；
        3. 如果数据拥有历史数据文件，返回该数据的json格式；
        4. 没有则返回空
        :return:
        """
        ali_file_info = self.get_ali_file_info()

        if self.user_file_name in ali_file_info:
            self.logger.info(f"该用户拥有历史数据，开始下载历史数据")
            # 获取文件下载链接
            self.ali_user_file_download_url = ali_file_info[self.user_file_name]['download_url']
            # 获取文件id
            self.ali_user_file_id = ali_file_info[self.user_file_name]['file_id']

            # 下载文件
            data = self.download_user_data(self.ali_user_file_download_url)

            if data:
                self.logger.info(f"成功载入历史信息...")
                return json.loads(data)

        return {}

    def save_ali_share_file(self, share_url: str, drive_id: str, inbox_dir) -> str:

        share_id = share_url.split('/s/', maxsplit=1)[-1].strip()

        try:
            file_info = self.ali_obj.get_share_info(share_id)

            self.logger.info(f"判断分享链接{share_id}是否已经失效")

            if not bool(file_info):
                self.logger.warning(f"链接{share_id}已经失效，跳过不转存")
                return f'【{share_id}】链接已失效，跳过...'

            share_token = self.ali_obj.get_share_token(share_id)

            if file_info.file_count == 1:
                self.ali_obj.share_file_save_all_to_drive(share_token, to_parent_file_id=inbox_dir,
                                                          to_drive_id=drive_id)
            else:
                dir_name = file_info.share_name
                store_dir = self.ali_obj.create_folder(name=dir_name, drive_id=drive_id, parent_file_id=inbox_dir)
                self.ali_obj.share_file_save_all_to_drive(share_token,
                                                          to_parent_file_id=store_dir.file_id,
                                                          to_drive_id=drive_id)
            return f"{file_info.share_name}"
        except Exception as e:
            self.logger.error(f'保存阿里云盘链接时出错了！【{share_url}】')
            return f'【{share_id}】保存失败'

    def save_ali_share_files(self, ali_share_link_list: list = None) -> str:
        """转存阿里云盘链接"""
        thread_num = self.config_dict.get('aliyun', {}).get('thread_num', 2)
        drive_id = self.config_dict.get('aliyun', {}).get('source_drive_id')
        inbox_dir = self.config_dict.get('aliyun', {}).get('inbox_dir')  # 阿里云盘文件夹id

        # 创建线程池
        pool = ThreadPoolExecutor(thread_num)
        future_list = []

        for ali_share_link in ali_share_link_list:
            future = pool.submit(self.save_ali_share_file, ali_share_link, drive_id, inbox_dir)
            future_list.append(future)

        pool.shutdown(True)
        result_msg = "\n".join([f"【{fu.result()}】保存成功" for fu in future_list])

        return '检测到阿里云盘链接，启动转存\n - - - - - - - - - - - - - - - \n\n' + result_msg

    # 预先判断该请求是否已经处理过了
    def pre_judge(self) -> str:

        # 1. 先通过信息的msg_id判断该信息是否已经处理过了
        last_msg_id = self.user_data.get('last_msg_id')
        if last_msg_id == self.msg_id:
            last_reply = self.user_data.get('last_msg_reply')
            return last_reply

        # 如果不是文本信息，直接返回
        if not self.content:
            return ''

        # 2. 判断是否是关键字回复：回复文本
        keyword_reply_dict = self.user_data.get("keyword_reply", {})  # 程序自生成的【关键字回复】
        keyword_reply_dict.update(self.config_dict.get('wechat', {}).get('keyword_reply', {}))  # 添加上配置文件中的【关键字回复】

        if self.content and self.content.strip().replace(' ', '') in keyword_reply_dict:
            return self.make_reply_text(keyword_reply_dict.get(self.content.strip().replace(' ', '')))

        # 3. 判断是否是试听语音：回复语音
        voice_dict = self.config_dict.get('wechat', {}).get('voice_mp3', {})
        if self.content and self.content.strip().replace(' ', '') in voice_dict:
            return self.make_reply_voice(voice_dict.get(self.content.strip().replace(' ', '')))

        # 4. 判断文本中是否包含阿里云盘分享链接，如果有，转存后直接返回文本
        ali_share_link_pattern = self.config_dict.get('aliyun', {}).get('pattern')
        if not ali_share_link_pattern:
            return ''

        # 获取匹配阿里云盘分享链接的正则
        pattern = re.compile(ali_share_link_pattern)
        results = pattern.findall(self.content)

        # 如果用户输入的文本里没有阿里云盘分享链接，直接跳过
        if not results:
            return ''

        result_msg = self.save_ali_share_files(results)

        return self.make_reply_text(result_msg)

    def add_user_history(self, ai: SparkGPT) -> None:
        """
        为ai通讯添加历史会话信息
        :param ai:
        :return:
        """

        user_talk = self.user_data.get('user_ai_talk')
        if user_talk:
            now_timestamp = int(time.time())
            for talk in user_talk[-self.user_talk_num:]:
                msg_time = talk['msg_time']

                if msg_time + self.user_time_limit > now_timestamp:
                    text = talk['msg_list']
                    ai.text.extend(text)

    def make_reply_text(self, content: str) -> str:
        """
        接收文本，生成符合微信服务器要求的文本信息
        :param content:
        :return:
        """
        time_stamp = int(time.time())

        resp_dict = {
            'xml': {
                'ToUserName': self.to_user_id,
                'FromUserName': self.my_user_id,
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
                'ToUserName': self.to_user_id,
                'FromUserName': self.my_user_id,
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
                'ToUserName': self.to_user_id,
                'FromUserName': self.my_user_id,
                'CreateTime': time_stamp,
                'MsgType': 'voice',
                'Voice': {
                    'MediaId': media_id
                },
            }
        }
        resp_xml = xmltodict.unparse(resp_dict)
        return resp_xml

    @staticmethod
    def make_ai_one_talk(question, answer) -> list[dict]:
        talk_list = [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ]

        return talk_list

    def weather_request(self, longitude, latitude) -> str:
        try:
            # 获取彩云天气的token与小时数设置
            token = self.config_dict.get('caiyunAPI_info', {}).get("caiyun_token")
            hour_num = self.config_dict.get('caiyunAPI_info', {}).get("hour_num")

            if not isinstance(hour_num, int) or not hour_num:
                hour_num = 3

            if not token:
                self.logger.error(f"获取不到彩云天气API的token，天气信息获取失败。")
                return f"🌚 呀，管理员忘记配置天气查询了..."

            url = f"https://api.caiyunapp.com/v2.6/{token}/{longitude},{latitude}/hourly?hourlysteps={hour_num}"
            weather_data = requests.get(url).json()

            # 整体天气提醒
            forecast_keypoint = weather_data['result']['forecast_keypoint']

            skycon = weather_data['result']['hourly']['skycon']  # 天气现象
            temperature = weather_data['result']['hourly']['temperature']  # 温度
            apparent_temperature = weather_data['result']['hourly']['apparent_temperature']  # 体感温度
            precipitation = weather_data['result']['hourly']['precipitation']  # 降水概率

            hour_data = zip(skycon, temperature, apparent_temperature, precipitation)

            hour_tips = []
            for item in hour_data:
                datetime_tip = datetime.datetime.fromisoformat(item[0]['datetime']).strftime("%Y-%m-%d_%H:00")
                skycon = item[0]['value']

                weather_icon = self.config_dict.get('weather_info')[skycon][1]
                weather_info = self.config_dict.get('weather_info')[skycon][0]
                skycon_tip = f"{weather_icon} {weather_info}"
                temperature_tip = item[1]['value']
                apparent_temperature_tip = item[2]['value']
                precipitation_tip = item[3]['value']

                hour_tip = f"#{datetime_tip}\n天气情况：{skycon_tip}\n此时温度：{temperature_tip}\n体感温度：{apparent_temperature_tip}\n降水概率：{round(precipitation_tip * 100, 2)}%"

                hour_tips.append(hour_tip)
            hour_tips_str = "\n\n".join(hour_tips)

            weather_tip = f" - - - - - 【天气预测】 - - - - - \n\n{forecast_keypoint.center(25, ' ')}\n\n - - - - 【每小时预测】 - - - - \n\n{hour_tips_str}"

        except Exception as e:
            self.logger.error(f"调用彩云API获取天气失败。【错误信息】---str{e}", exc_info=True)
            weather_tip = f"🌚 呀，天气信息获取失败..."

        return weather_tip


if __name__ == '__main__':
    pass
