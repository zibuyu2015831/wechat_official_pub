# -*- coding: utf-8 -*-
import re
import uuid
import datetime
import requests
import threading
from pathlib import Path
from utils.baidu_ocr import OCR
from basic.my_config import config
from basic.my_logging import MyLogging


class ImageHandler(MyLogging):

    def __init__(self):
        super().__init__()
        self.config_dict = config

    @property
    def function_mapping(self):
        """
        调用名与函数的对应关系
        :return:
        """
        mapping_dict = {
            'ocr': 'ocr_one_pic',
            '图片转文本': 'ocr_one_pic',
            '图片转文字': 'ocr_one_pic',
            '上传图片': 'store_img_to_aliyun',
            '保存图片': 'store_img_to_aliyun',
        }
        return mapping_dict

    def _store_ocr_result(self, reply_obj, text_list):
        """存储用户OCR的结果"""

        title = text_list[0][0:10]  # 获取首行的、最多前10个字作为标题
        title = self.remove_invalid_chars(title)
        today_str = datetime.date.today().strftime('%Y%m%d')
        content = '\n\n'.join(text_list)

        # 生成文件标题：【20231103-子不语-ocr测试.txt】
        user_nickname_dict = self.config_dict.get('wechat', {}).get('user_nickname', {})
        if reply_obj.to_user_id in user_nickname_dict:
            nickname = user_nickname_dict.get(reply_obj.to_user_id)
            file_name = f"{today_str}-{nickname}-{title}.txt"
        else:
            file_name = f"{today_str}-{reply_obj.to_user_id}-{title}.txt"

        # 存储ocr结果的文件夹，已在MyConfig类中判断并创建
        dir_file_path = Path.cwd() / 'data' / 'ocr_files'

        file_path = dir_file_path / file_name
        self.logger.info(f"新建文件【{str(file_path.name)}】，保存OCR结果")
        with open(file_path, mode='w', encoding='utf8') as f:
            f.write(content)

        ocr_result_dir = self.config_dict.get('aliyun', '').get('ocr_result_dir')
        reply_obj.upload_ali_file(file_path, parent_file_id=ocr_result_dir, msg="上传ocr处理结果文件！")

    def store_ocr_result(self, reply_obj, text_list):
        """ 新开一个线程：创建文件，保存ocr结果 """
        save_content_thread = threading.Thread(target=self._store_ocr_result,
                                               kwargs={'reply_obj': reply_obj, "text_list": text_list})
        save_content_thread.start()

    @staticmethod
    def generate_short_uuid():
        return str(uuid.uuid4())[:5]

    @staticmethod
    def remove_invalid_chars(s):
        '''阿里云盘命名要求：不得包含以下字符:/*?:<>\"|"'''
        return re.sub(r'[/*?:<>\\"|]', '', s)

    def upload_image(self, reply_obj, file_path):
        image_dir = self.config_dict.get('aliyun', '').get('image_dir')
        self.logger.info("上传用户图片到阿里云盘......")
        reply_obj.upload_ali_file(file_path, parent_file_id=image_dir, msg="图片上传成功！")

    def _store_image(self, reply_obj):
        """存储用户发送的图片"""
        image_url = reply_obj.pic_url
        short_uuid = self.generate_short_uuid()  # 获取随机5位数的字符串
        image_title = f"{reply_obj.to_user_id}-{datetime.datetime.today().strftime('%Y%m%d')}-{short_uuid}.jpg"

        # 存储图片的文件夹，已在MyConfig类中判断并创建
        image_dir = Path.cwd() / 'data' / "image"

        image_path = image_dir / image_title

        try:
            self.logger.info("下载并保存用户传输的图片...")
            response = requests.get(image_url)
            with open(image_path, mode='wb') as f:
                f.write(response.content)
            self.logger.info("用户图片保存成功！")

            self.upload_image(reply_obj, image_path)
        except Exception as e:
            self.logger.error("保存用户图片失败了...", exc_info=True)

    def store_image(self, reply_obj) -> threading.Thread:
        """新开一个线程：创建文件，保存ocr结果"""

        save_content_thread = threading.Thread(target=self._store_image, kwargs={'reply_obj': reply_obj})
        save_content_thread.start()
        return save_content_thread

    @staticmethod
    def make_ocr_info(paragraphs):
        length = len(paragraphs)

        page_list = []
        for i in range(length):
            page_list.append(f"【获取ocr结果第{i + 1}页】")
        all_page = "\n".join(page_list)
        info = f'{paragraphs[0]} - - - - - - - - - - - - - - - - \n\n该文本较长，仅显示第一页\n\n可输入以下命令，获取后续：\n' + all_page

        return info

    def ocr_one_pic(self, reply_obj):
        """
        OCR一张图片，该图片由微信参数中的PicUrl获取
        :param reply_obj:
        :return:
        """
        image_url = reply_obj.pic_url
        media_id = reply_obj.media_id

        for i in range(3):
            try:
                self.logger.info(f"开始ocr图片，该图片链接为：【{image_url}】")
                self.logger.info(f"该图片的media_id为：【{media_id}】")

                ocr_obj = OCR(self.config_dict, logger=self.logger)
                text_dict = ocr_obj.accurate_basic_by_url(image_url)  # 如果ocr成功，返回的是包含文本的字典；失败则返回原json

                text_list = text_dict.get('text')

                if not text_list:
                    return reply_obj.make_reply_text(
                        "ocr过程出现错误，请检查图片。\n\n图片要求：\n1. 图片最短边至少15px，最长边最大8192px；\n2. 仅支持jpg/jpeg/png/bmp格式")

                self.logger.info("成功完成图片OCR")

                # 保存OCR结果
                self.store_ocr_result(reply_obj, text_list)

                # 由于微信限制，文本回复不得超过600字，所以将内容进行分段。
                paragraphs = ocr_obj.split_text(text_list)
                reply_obj.ocr_text_list = paragraphs
                if len(paragraphs) == 1:
                    reply = paragraphs[0]
                else:
                    reply = self.make_ocr_info(paragraphs)
                return reply_obj.make_reply_text(reply)
            except Exception as e:
                self.logger.error(f"ocr图片过程中可能出现网络错误，即将重试...", exc_info=True)

        # 没有成功完成ocr，也需要返回内容
        return reply_obj.make_reply_text('ocr过程出现错误，请联系管理员')
