# -*- coding: utf-8 -*-
import os
import json
import time
import logging
import threading
import requests
import xmltodict
from .spark_gpt import SparkGPT
from .text_handler import TextHandler
from module.aligo import Aligo, set_config_folder  # 自己修改后的Aligo


# from aligo import Aligo, set_config_folder


class ReplyHandler(object):

    def __init__(self, xml_dict, config_dict, logger: logging.Logger = None):
        # 设置日志记录对象
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger()

        # 获取项目目录
        self.project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # 用户post请求中的数据
        self.xml_dict = xml_dict

        # 细化配置信息
        self.my_name = xml_dict.get('ToUserName')  # 获取消息的接收者，为本次回复的发送者
        self.to_user_name = xml_dict.get('FromUserName')  # 获取消息的发送者，为本次回复的接收者
        self.logger.info(f"用户id：【{self.to_user_name}】")

        self.msg_id = xml_dict.get('MsgId')  # 消息id，64位整型
        self.logger.info(f"本次消息的MsgId：【{self.msg_id}】")

        self.msg_type = xml_dict.get('MsgType')  # 获取本次消息的MsgType
        self.pic_url = xml_dict.get('PicUrl')  # 如果MsgType是图片，则会有一个图片临时链接，该链接保存3天
        self.media_id = xml_dict.get('MediaId')  # 图片、音频、视频等消息会有一个MediaId,可以调用获取临时素材接口拉取数据。
        self.msg_data_id = xml_dict.get('MsgDataId')  # 消息的数据ID（消息如果来自文章时才有）
        self.idx = xml_dict.get('Idx')  # 多图文时第几篇文章，从1开始（消息如果来自文章时才有）
        self.format = xml_dict.get('Format')  # 语音消息的语音格式，如amr，speex等

        self.create_time = xml_dict.get('CreateTime')  # 获取本次消息的消息创建时间 （整型）（时间戳）
        self.logger.info(f"本次消息的create_time：【{self.create_time}】")

        # 配置信息
        self.config_dict = config_dict

        # 从配置文件中获取ai通话时记住的历史会话数量
        history_item_num = self.config_dict.get('wechat', {}).get('history_item_num')
        if isinstance(history_item_num, int):
            self.history_item_num = history_item_num
        else:
            self.history_item_num = 5

        # 从配置文件中获取ai通话时历史会话的时间限制
        history_time_limit = self.config_dict.get('wechat', {}).get('history_time_limit')
        if isinstance(history_time_limit, int):
            self.history_time_limit = history_time_limit
        else:
            self.history_time_limit = 1800

        # 从配置文件中获取短指令的时间限制
        short_cmd_time_limit = self.config_dict.get('wechat', {}).get('short_cmd_limit_time')
        if isinstance(short_cmd_time_limit, int):
            self.short_cmd_time_limit = short_cmd_time_limit
        else:
            self.short_cmd_time_limit = 600

        self.reply_content_full = ''  # 本次回应的完整信息xml格式
        self.reply_content_text = ''  # 本次回应的文本信息，字符串
        self.ali_history_file_id = ''  # 阿里云盘中存储历史会话信息的文件id
        self.ai_talk_text = dict()  # 本次通讯的ai会话记录
        self.short_cmd = ''  # 本次接收的短指令
        self.history_file_name = f"{self.to_user_name}.json"  # 历史会话信息的文件名称

        # Aligo相关配置
        aligo_config_path = os.path.join(self.project_path)
        set_config_folder(aligo_config_path)
        self.ali_obj = Aligo(logger=self.logger)

        # 从阿里云盘获取历史消息
        self.history_data = self.get_history_data() or {}

    def delete_ali_file(self):
        for i in range(2):
            try:
                # self.logger.info("删除旧的会话数据文件！")
                self.ali_obj.move_file_to_trash(self.ali_history_file_id)
                return
            except Exception as e:
                self.logger.error("旧的会话数据文件删除失败！", exc_info=True)

    def upload_ali_file(self, file_path):
        for i in range(2):
            try:
                self.logger.info("上传新的会话数据文件！")
                self.ali_obj.upload_file(file_path, self.config_dict.get('aliyun', '').get('store_dir_id'))
                return
            except Exception as e:
                self.logger.error("新的会话数据文件上传失败！", exc_info=True)

    def _save_history_data(self):

        # 保存文件前，先删除原有文件
        self.logger.info("删除旧的会话数据文件！")
        self.delete_ali_file()

        new_history_data = []
        new_short_command = []
        if self.history_data:
            # 1. 检查ai_history_talk，保留未过期的AI对话
            ai_history_talk = self.history_data.get('ai_history_talk')
            now_timestamp = int(time.time())

            for item in ai_history_talk[-self.history_item_num:]:
                msg_time = item['msg_time']

                if msg_time + self.history_time_limit > now_timestamp:
                    new_history_data.append(item)

            # 2. 检查短指令是否过期
            old_short_command = self.history_data.get('short_command')
            if old_short_command:
                if old_short_command[0] + self.short_cmd_time_limit > now_timestamp:
                    new_short_command = old_short_command

        # 增加本次对话
        if self.ai_talk_text:
            new_history_data.append(self.ai_talk_text)

        if self.short_cmd:
            new_short_command = [int(time.time()), self.short_cmd]

        # 检查短指令是否过期，过期则去除

        content = {
            'user_id': self.to_user_name,
            'lastest_msg_id': self.msg_id,
            'lastest_msg_reply': self.reply_content_full,
            "short_command": new_short_command,
            'ai_history_talk': new_history_data
        }

        file_dir_path = os.path.join(self.project_path, 'user_data')

        if not os.path.exists(file_dir_path):
            os.makedirs(file_dir_path)
        file_path = os.path.join(file_dir_path, f"{self.to_user_name}.json")

        with open(file_path, mode="w", encoding='utf8') as f:
            f.write(json.dumps(content))
        self.upload_ali_file(file_path)

    def save_history_data(self):
        """
        新开一个线程去保存历史会话信息
        :return:
        """
        save_content_thread = threading.Thread(target=self._save_history_data)
        save_content_thread.start()

    def download_history_data(self, url):
        for i in range(3):
            try:
                response = requests.get(url, headers={
                    'Referer': 'https://www.aliyundrive.com/',
                })
                self.logger.info("历史信息下载完成")
                return response.content
            except Exception as e:
                self.logger.error(f"下载出现错误，重试", exc_info=True)

    def get_ali_file_info(self):
        # 从配置信息中获取阿里云盘存放文件夹的id
        dir_id = self.config_dict.get('aliyun', {}).get('store_dir_id')
        if not dir_id:
            return {}

        # 获取阿里云盘中的文件信息可能由于网络原因导致失败，重试三次
        for i in range(3):
            try:
                self.logger.info(f"获取阿里云盘文件信息")
                files = self.ali_obj.get_file_list(dir_id)

                file_dict = {}
                for file in files:
                    file_dict[file.name] = {'file_id': file.file_id, "download_url": file.download_url}

                return file_dict
            except Exception as e:
                self.logger.error(f"获取阿里云盘文件文件信息失败，即将重试！", exc_info=True)

        return {}

    def get_history_data(self):
        ali_file_info = self.get_ali_file_info()

        if self.history_file_name in ali_file_info:
            self.logger.info(f"该用户拥有历史信息，开始下载历史信息")
            # 获取文件下载链接
            download_url = ali_file_info[self.history_file_name]['download_url']
            # 获取文件id
            self.ali_history_file_id = ali_file_info[self.history_file_name]['file_id']

            # 下载文件
            data = self.download_history_data(download_url)

            if data:
                self.logger.info(f"成功载入历史信息...")
                return json.loads(data)

    def add_history(self, ai):
        """
        为ai通讯添加历史会话信息
        :param ai:
        :return:
        """

        history_talk = self.history_data.get('ai_history_talk')
        if history_talk:
            now_timestamp = int(time.time())
            for talk in history_talk[-self.history_item_num:]:
                msg_time = talk['msg_time']

                if msg_time + self.history_time_limit > now_timestamp:
                    text = talk['msg_list']
                    ai.text.extend(text)

    def make_reply_text(self, content):
        time_stamp = int(time.time())

        resp_dict = {
            'xml': {
                'ToUserName': self.to_user_name,
                'FromUserName': self.my_name,
                'CreateTime': time_stamp,
                'MsgType': 'text',
                'Content': content,
            }
        }
        resp_xml = xmltodict.unparse(resp_dict)
        return resp_xml

    def make_reply_picture(self, media_id):
        time_stamp = int(time.time())

        resp_dict = {
            'xml': {
                'ToUserName': self.to_user_name,
                'FromUserName': self.my_name,
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

    def text(self):
        sep_char = self.config_dict.get('wechat').get('sep_char')
        raw_content = self.xml_dict.get('Content')  # 获取用户发送的文本内容
        # print(self.history_data, self.msg_id)

        # 通过信息的msg_id判断该信息是否已经处理过了
        lastest_msg_id = self.history_data.get('lastest_msg_id')
        if lastest_msg_id == self.msg_id:
            lastest_reply = self.history_data.get('lastest_msg_reply')
            return lastest_reply

        # 文本处理者
        handler = TextHandler(self.config_dict)

        try:
            # 判断是否为处理文本本身的短指令，以是否包含用户输入的分隔符来确定
            if sep_char in raw_content:
                func_name, content = raw_content.split(sep_char, maxsplit=1)

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

            # 判断是否为处理其他格式的短指令
            elif raw_content in self.config_dict.get('wechat', {}).get('short_commend'):
                handle_function = getattr(handler, handler.function_mapping[raw_content])
                self.reply_content_full = handle_function(self, raw_content)

            else:  # 如果没有分隔符号，则是一般的AI对话

                # 实例化ai
                ai = SparkGPT(self.config_dict.get('spark_info'), logger_obj=self.logger)

                # 添加历史会话
                self.add_history(ai)

                # 获取ai回答
                reply_content_text = ai.ask(raw_content)

                # 记录ai回答，元组类型，元素有两个：时间戳+回答
                self.ai_talk_text['msg_time'] = int(time.time())
                self.ai_talk_text['msg_list'] = self.make_ai_one_talk(raw_content, reply_content_text)

                # 生成符合微信服务器要求的回复信息
                self.reply_content_full = self.make_reply_text(reply_content_text)
                # 保存新生成的会话信息
                self.save_history_data()

            return self.reply_content_full
        except Exception as e:
            self.logger.error("本次回复出现错误", exc_info=True)
            return self.make_reply_text("Something wrong had happened!")

    def event(self):
        return self.make_reply_text("Please wait for event development")

    def image(self):



        self.reply_content_full = self.make_reply_picture(self.media_id)
        return self.reply_content_full
        # return self.make_reply_text("Please wait for image development")

    def voice(self):
        return self.make_reply_text("Please wait for voice development")

    def video(self):
        return self.make_reply_text("Please wait for video development")

    def shortvideo(self):
        return self.make_reply_text("Please wait for shortvideo development")

    def location(self):
        return self.make_reply_text("Please wait for location development")

    def link(self):
        return self.make_reply_text("Please wait for link development")


if __name__ == '__main__':
    t = TextHandler()
    print(t.config_dict)
