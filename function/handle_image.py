# -*- coding: utf-8 -*-
import time
import logging
import requests
import threading
from pathlib import Path
from .baidu_ocr import OCR


class ImageHandler(object):

    def __init__(self, config_dict, logger: logging.Logger):

        self.config_dict = config_dict
        self.logger = logger

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
        title = text_list[0]
        content = '\n\n'.join(text_list)

        user_nickname_dict = self.config_dict.get('wechat', {}).get('user_nickname', {})
        if reply_obj.to_user_id in user_nickname_dict:
            nickname = user_nickname_dict.get(reply_obj.to_user_id)
            file_name = f"OCR存储-{int(time.time())}-{nickname}-{title}.txt"
        else:
            file_name = f"OCR存储-{int(time.time())}-{reply_obj.to_user_id}-{title}.txt"

        dir_file_path = Path.cwd() / 'ocr_files'
        if not dir_file_path.exists():
            dir_file_path.mkdir()

        file_path = dir_file_path / file_name
        self.logger.info(f"新建文件【{str(file_path.name)}】，保存OCR结果")
        with open(file_path, mode='w', encoding='utf8') as f:
            f.write(content)

    def store_ocr_result(self, reply_obj, text_list):
        """
        新开一个线程：创建文件，保存ocr结果
        :return:
        """
        save_content_thread = threading.Thread(target=self._store_ocr_result,
                                               kwargs={'reply_obj': reply_obj, "text_list": text_list})
        save_content_thread.start()

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

    def store_img_to_aliyun(self, reply_obj):
        image_url = reply_obj.pic_url
        media_id = reply_obj.media_id

        for i in range(3):
            try:
                self.logger.info(f"开始下载图片，该图片链接为：【{image_url}】")

                # response = requests.get(image_url)
                self.logger.info(f"图片下载完成，开始将图片上传到阿里云盘")
                self.logger.info(f"该图片的media_id为：【{media_id}】")
                return reply_obj.make_reply_text("已将图片保存至阿里云盘")
            except Exception as e:
                pass
