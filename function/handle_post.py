# -*- coding: utf-8 -*-
import json
import time
import threading
import requests
import xmltodict
from pathlib import Path
from utils.spark_gpt import SparkGPT
from .handle_text import TextHandler
from .handle_image import ImageHandler
from basic.my_config import config
from basic.my_logging import MyLogging
from module.aligo import Aligo, set_config_folder  # 自己修改后的Aligo


class ReplyHandler(MyLogging):

    def __init__(self, xml_dict: dict):
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
            self.user_talk_num = 5

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

        self.reply_content_full = ''  # 本次回应的完整信息xml格式
        self.reply_content_text = ''  # 本次回应的文本信息，字符串
        self.ai_talk_text = dict()  # 本次通讯的ai会话记录，如果有的话
        self.short_cmd = ''  # 本次接收的短指令，如果有的话
        self.ocr_text_list = []  # 本次通讯的ocr结果，如果有的话
        self.user_file_name = f"{self.to_user_id}.json"  # 历史会话信息的文件名称

        # Aligo相关配置：后续需要优化，将配置统一为整个config.json文件
        aligo_config_path = Path.cwd() / 'config'
        set_config_folder(str(aligo_config_path.absolute()))
        self.ali_obj = Aligo(logger=self.logger)

        # 从阿里云盘获取历史消息
        self.user_data = self.get_user_data_from_alipan() or {}

    def delete_ali_file(self):
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

        # 保存文件前，先删除原有文件
        self.delete_ali_file()

        new_user_ai_talk = []
        new_short_command = []

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

        # 如果有图片ocr结果
        keyword_reply = {}

        if self.ocr_text_list:
            for index, paragraph in enumerate(self.ocr_text_list):
                keyword_reply[f"获取ocr结果第{index + 1}页"] = paragraph

        content = {
            'user_id': self.to_user_id,
            'last_msg_id': self.msg_id,
            'last_msg_reply': self.reply_content_full,
            "short_command": new_short_command,
            'user_ai_talk': new_user_ai_talk,
            "keyword_reply": keyword_reply
        }

        file_dir_path = Path.cwd() / 'data' / 'user_data'
        file_path = file_dir_path / f"{self.to_user_id}.json"

        with open(file_path, mode="w", encoding='utf8') as f:
            f.write(json.dumps(content))
        user_data_dir = self.config_dict.get('aliyun', '').get('user_data_dir')

        self.logger.info("上传新的用户数据文件......")
        self.upload_ali_file(file_path, parent_file_id=user_data_dir, msg="用户数据文件上传成功！")

    def save_user_data(self):
        """
        新开一个线程去保存历史会话信息
        :return:
        """
        save_content_thread = threading.Thread(target=self._save_user_data)
        save_content_thread.start()

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

    def get_ali_file_info(self):
        # 从配置信息中获取阿里云盘存放用户数据的文件夹id
        dir_id = self.config_dict.get('aliyun', {}).get('user_data_dir')
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

    def get_user_data_from_alipan(self):
        """
        从阿里云盘中获取用户历史数据
        :return:
        """
        ali_file_info = self.get_ali_file_info()

        if self.user_file_name in ali_file_info:
            self.logger.info(f"该用户拥有历史数据，开始下载历史数据")
            # 获取文件下载链接
            download_url = ali_file_info[self.user_file_name]['download_url']
            # 获取文件id
            self.ali_user_file_id = ali_file_info[self.user_file_name]['file_id']

            # 下载文件
            data = self.download_user_data(download_url)

            if data:
                self.logger.info(f"成功载入历史信息...")
                return json.loads(data)

    # 预先判断该请求是否已经处理过了
    def pre_judge(self):

        # 判断是否是关键字回复
        keyword_reply_dict = self.user_data.get("keyword_reply", {})  # 程序自生成的【关键字回复】
        keyword_reply_dict.update(self.config_dict.get('wechat', {}).get('keyword_reply', {}))  # 添加上配置文件中的【关键字回复】

        if self.content and self.content.strip().replace(' ', '') in keyword_reply_dict:
            return self.make_reply_text(keyword_reply_dict.get(self.content))

        # 通过信息的msg_id判断该信息是否已经处理过了
        last_msg_id = self.user_data.get('last_msg_id')
        if last_msg_id == self.msg_id:
            last_reply = self.user_data.get('last_msg_reply')
            return last_reply

    def add_user_history(self, ai):
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

    def make_reply_text(self, content: str):
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

    def make_reply_picture(self, media_id: str):
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

    @staticmethod
    def make_ai_one_talk(question, answer):
        talk_list = [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ]

        return talk_list

    def weather_request(self, longitude, latitude):
        try:

            token = self.config_dict.get('caiyunAPI_info', {}).get("caiyun_token")
            if not token:
                self.logger.warning(f"获取不到彩云天气API的token，天气信息获取失败。")
                return

            url = f"https://api.caiyunapp.com/v2.6/{token}/{longitude},{latitude}/daily?dailysteps=1"
            res = requests.get(url).json()

            temperature_info = res['result']['daily']['temperature'][0]
            weather_code = res['result']['daily']['skycon'][0]['value']

            weather_icon = self.config_dict.get('weather_info')[weather_code][1]
            weather = self.config_dict.get('weather_info')[weather_code][0]

            # 处理温度的数据格式，只要整数：34~27℃
            temperature_max = str(temperature_info['max']).split('.', 1)[0]
            temperature_min = str(temperature_info['min']).split('.', 1)[0]

            # print(temperature_dict, weather_code)
            weather_tip = f"{weather_icon} {weather} {temperature_min}~{temperature_max}℃"
        except Exception as e:
            self.logger.warning(f"调用彩云API获取天气失败。【错误信息】---str{e}", exc_info=True)
            weather_tip = f"🌚 呀，今天的天气信息获取失败..."

        return weather_tip

    def text(self):
        """
        处理接收到的文本信息，在微信的文本信息中：
            Content	文本消息内容
        :return:
        """
        # 获取短指令分隔符号
        sep_char = self.config_dict.get('wechat').get('sep_char')

        # 文本处理者
        handler = TextHandler()

        try:
            # 判断是否为处理文本本身的短指令，以是否包含用户输入的分隔符来确定
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

            # 判断是否为处理其他信息格式的短指令
            elif self.content in self.config_dict.get('wechat', {}).get('short_commend'):
                handle_function = getattr(handler, handler.function_mapping[self.content])
                self.reply_content_full = handle_function(self, self.content)

            else:  # 如果没有分隔符号，且不是短指令，则是AI对话

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
                self.save_user_data()

            return self.reply_content_full
        except Exception as e:
            self.logger.error(f"本次通讯出现错误，用户输入的文本是：【{self.content}】", exc_info=True)
            return self.make_reply_text("Something wrong had happened!")

    def event(self):
        return self.make_reply_text("Please wait for event development")

    def image(self):
        """
        处理接收到的图片信息，在微信的文本信息中：
            PicUrl	图片链接（由系统生成）
            MediaId	图片消息媒体id，可以调用获取临时素材接口拉取数据。
        :return:
        """
        # 图片处理者
        handler = ImageHandler()
        handler.store_image(self)

        # 获取user_data中的short_command：当前短指令
        if self.user_data.get("short_command"):
            # 注意user_data中的short_command，是列表格式，第一个元素是时间戳，第二个元素是指令
            user_short_cmd = self.user_data.get("short_command")[1]
        else:
            user_short_cmd = ''

        if user_short_cmd:
            if user_short_cmd in handler.function_mapping:
                handle_function = getattr(handler, handler.function_mapping[user_short_cmd])
                self.reply_content_full = handle_function(self)
            else:
                type_error_msg = f"当前为指令模式：【{user_short_cmd}】\n无法处理{self.msg_type}格式信息！\n\n请先输入【退出】，以退出指令模式。"
                self.reply_content_full = self.make_reply_text(type_error_msg)
        else:
            self.reply_content_full = self.make_reply_text(f"该图片的临时链接为：\n\n{self.pic_url}")

        self.save_user_data()
        return self.reply_content_full
        # return self.make_reply_text("Please wait for image development")

    def voice(self):
        return self.make_reply_text("Please wait for voice development")

    def video(self):
        return self.make_reply_text("Please wait for video development")

    def shortvideo(self):
        return self.make_reply_text("Please wait for shortvideo development")

    def location(self):
        weather_tip = self.weather_request(self.location_y, self.location_x)
        self.reply_content_full = self.make_reply_text(weather_tip)
        return self.reply_content_full
        # return self.make_reply_text("Please wait for location development")

    def link(self):
        return self.make_reply_text("Please wait for link development")


if __name__ == '__main__':
    pass
