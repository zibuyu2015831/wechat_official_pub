import time
import json
import requests
import xmltodict
from pathlib import Path
from functools import wraps


# 装饰器，对于requests请求，出错时重试三次
def runtime_decorator(func):
    @wraps(func)
    def inner(*args, **kwargs):

        for i in range(3):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(e)
                print(f"运行{func.__name__}时出错了，第{i + 1}次重试")

        # 若重试之后，仍然获取不到access_token，则报错
        raise Exception(f"{func.__name__}已经重试三次，皆失败")

    return inner


class WechatHandler(object):

    def __init__(self, config_dict: dict = None):
        if config_dict:
            self.config_dict = config_dict
        else:
            config_path = Path.cwd() / 'config' / 'config.json'

            if not config_path.exists():
                raise Exception("缺乏配置文件")

            with open(config_path, mode='r', encoding='utf8') as f:
                self.config_dict = json.load(f)

        self.app_id = config_dict.get('app_id')
        self.app_secret = config_dict.get('app_secret')

        self.params = {
            'grant_type': 'client_credential',
            'appid': self.app_id,
            'secret': self.app_secret
        }

        # 相关请求所需的access_token
        self.access_token = ''
        # access_token的有效期：时间戳，整型
        self.token_expires_in = 0

        # 测试时，使用固定的token
        # self.access_token = '74_KK1J9CRnYb6IgOWcX7uaNu1CXnI8apzHSjGW1Fsm2ZZRMFvR3tREhdke_NCSI1N4x4s1KDo9nLGILoVvlxMSNk5aJmCez02_yJ0F2LJ34RIy7nMb_acoa-xxjv4PWBdAIADKP'
        # self.token_expires_in = int(time.time())

        self.pre_url = 'https://api.weixin.qq.com/cgi-bin/'
        # 临时素材相关接口
        self.token_url = f"{self.pre_url}token"  # 获取token
        self.soft_src_upload_url = f"{self.pre_url}media/upload"  # 上传临时素材
        self.soft_src_download_url = f"{self.pre_url}media/get"  # 下载临时素材
        # 永久素材相关接口
        self.hard_img_upload_url = f"{self.pre_url}media/uploadimg"  # 上传图文消息内的图片获取URL
        self.hard_src_upload_url = f"{self.pre_url}material/add_material"  # 上传其他类型永久素材:图片（image）、语音（voice）、视频（video）和缩略图（thumb）
        self.hard_src_download_url = f"{self.pre_url}material/get_material"  # 下载永久素材
        self.hard_src_delete_url = f"{self.pre_url}material/del_material"  # 删除永久素材
        self.hard_src_count_url = f"{self.pre_url}material/get_materialcount"  # 获取永久素材的各类总数列表
        self.hard_src_list_url = f"{self.pre_url}material/batchget_material"  # 获取永久素材的列表
        # 菜单相关接口
        self.get_menu_url = f"{self.pre_url}get_current_selfmenu_info"  # 查询当前菜单
        self.create_menu_url = f"{self.pre_url}menu/create"  # 创建菜单
        self.delete_menu_url = f"{self.pre_url}menu/delete"  # 删除菜单
        # 草稿相关接口
        self.create_draft_url = f"{self.pre_url}draft/add"  # 新建素材
        self.get_draft_url = f"{self.pre_url}draft/get"  # 获取素材
        self.delete_draft_url = f"{self.pre_url}draft/delete"  # 删除素材
        self.update_draft_url = f"{self.pre_url}draft/update"  # 修改素材
        self.get_draft_count_url = f"{self.pre_url}draft/count"  # 获取素材总数
        self.get_draft_list_url = f"{self.pre_url}draft/batchget"  # 获取素材列表
        # 清除api接口调用的额度限制
        self.clear_quota_url = f"{self.pre_url}clear_quota"  # 清空api的调用quota，每月可以清除10次
        # 发布相关
        self.publish_news_url = f"{self.pre_url}freepublish/submit"  # 发布草稿
        self.publish_status_url = f"{self.pre_url}freepublish/get"  # 查询发布状态
        self.article_list_url = f"{self.pre_url}freepublish/batchget"  # 获取已发布图文列表
        self.get_article_url = f"{self.pre_url}freepublish/getarticle"  # 获取已发布的图文
        # 智能接口
        self.voice_to_text_url = "media/voice/addvoicetorecofortext"

    def clear_quota(self):
        params = {
            'access_token': self.token,
        }

        data = {
            'appid': self.app_id
        }

        response = requests.post(self.clear_quota_url, params=params, json=data)
        result = response.json()

        if result['errcode'] == 0:
            return True
        print(result)
        return False

    # 预留函数，待开发，模拟从存储中获取access_token
    def get_token_local(self):
        """
        检查之前的token是否仍然在有效期内
        :return:
        """

        token = {
            "access_token": None,
            "token_expires_in": 0
        }

        access_token = token.get('access_token')
        token_expires_in = token.get('token_expires_in')

        return access_token, token_expires_in

    @runtime_decorator
    def get_token(self):
        """
        微信的接口鉴权token，有效期为两小时
        可以本地保存token，有效期内不用反复获取
        :return:
        """

        # 获取本地存储的access_token

        if not self.access_token and not self.token_expires_in:
            self.access_token, self.token_expires_in = self.get_token_local()

        # 检验本地存储的access_token，仍然有效则直接返回
        now_timestamp = int(time.time())
        if self.access_token and self.token_expires_in > now_timestamp:
            return self.access_token

        response = requests.get(self.token_url, params=self.params)
        json_data = response.json()

        self.access_token = json_data['access_token']
        self.token_expires_in = now_timestamp + 7000  # 官方设置access_token的有效期为7200秒，这里为确保其有效性，取整处理

        return self.access_token

    @property
    def token(self):
        # 检验本地存储的access_token，仍然有效则直接返回
        now_timestamp = int(time.time())
        if self.access_token and self.token_expires_in > now_timestamp:
            return self.access_token

        return self.get_token()

    @runtime_decorator
    def upload_source(self, file_type: str, file_path, source_type: str = "soft"):
        """
        公共方法：用于上传临时素材或永久素材
        :param file_type:素材类别：image、voice、video等
        :param file_path:所上传文件的路径，用于读取文件
        :param source_type:永久素材hard或临时素材soft；另加一个other（上传图文消息内的图片获取URL，不占用永久素材额度的接口）
        :return:
        """

        if source_type == "soft":
            url = self.soft_src_upload_url
        elif source_type == "hard":
            url = self.hard_src_upload_url
        elif file_type == 'image' and source_type == "other":
            url = self.hard_src_upload_url
        else:
            raise Exception('素材类型传入错误。\n临时素材source_type=soft\n永久素材source_type=hard')

        params = {
            'access_token': self.token,
            'type': file_type,
            'media': ''
        }

        with open(file_path, "rb") as f:
            files = {"media": f}
            response = requests.post(url, files=files, params=params)

        return response.json()

    def upload_soft_source(self, file_type: str, file_path):
        """
        上传临时素材，
        临时素材的有效期是3天
        注意，各类素材的大小有要求：
            图片（image）: 10M，支持PNG\JPEG\JPG\GIF格式
            语音（voice）：2M，播放长度不超过60s，支持AMR\MP3格式
            视频（video）：10MB，支持MP4格式
            缩略图（thumb）：64KB，支持JPG格式
        :param file_type:
        :param file_path:
        :return:
        """
        return self.upload_source(file_type=file_type, file_path=file_path, source_type='soft')

    # 待完善，上传视频素材时，官方有附加要求
    def upload_hard_source(self, file_type: str, file_path) -> dict:
        """
        上传永久素材。
        总数量有上限：图文消息素材、图片素材上限为100000，其他类型为1000。
        注意，各类素材的大小有要求：
            图片（image）: 10M，支持PNG\JPEG\JPG\GIF格式
            语音（voice）：2M，播放长度不超过60s，支持AMR\MP3格式
            视频（video）：10MB，支持MP4格式
            缩略图（thumb）：64KB，支持JPG格式
        :param file_type:
        :param file_path:
        :return:
        """
        return self.upload_source(file_type=file_type, file_path=file_path, source_type='hard')

    def upload_img_get_url(self, file_path):
        """
        上传图文消息内的图片获取URL
        本接口所上传的图片不占用公众号的素材库中图片数量的100000个的限制。
        图片仅支持jpg/png格式，大小必须在1MB以下。
        :param file_path: 上传图片所在路径
        :return:
        """
        return self.upload_source(file_type='image', file_path=file_path, source_type='other')

    @runtime_decorator
    def download_source(self, media_id: str, file_dir, source_type: str = "soft"):
        """
        公共方法，用于下载临时素材或永久素材：
            1. 如果该临时素材是视频，返回结果为json：
                { "video_url":DOWN_URL }
            2. 永久素材比临时素材多了一个类型：图文素材。返回结果为json：
                {
                     "news_item":
                     [
                         {
                         "title":TITLE,  # 图文消息的标题
                         "thumb_media_id":THUMB_MEDIA_ID,  # 图文消息的封面图片素材id（必须是永久mediaID）
                         "show_cover_pic":SHOW_COVER_PIC(0/1),  # 是否显示封面，0为false，即不显示，1为true，即显示
                         "author":AUTHOR,  # 作者
                         "digest":DIGEST,  # 图文消息的摘要，仅有单图文消息才有摘要，多图文此处为空
                         "content":CONTENT,  # 图文消息的具体内容，支持HTML标签，必须少于2万字符，小于1M，且此处会去除JS
                         "url":URL,  # 图文页的URL
                         "content_source_url":CONTENT_SOURCE_URL  # 图文消息的原文地址，即点击“阅读原文”后的URL
                         },
                        # 多图文消息有多篇文章
                      ]
                }
            3. 其他类型的临时素材，返回该素材本身内容，可直接以二进制方式写入文件；
            4. 错误情况下，返回：
                { "errcode":40007,"errmsg":"invalid media_id" }

            5. 该请求的返回头中携带素材类型信息，可通过请求头中的信息判断素材类型、获取文件名称：
                HTTP/1.1 200 OK
                Connection: close
                Content-Type: voice/speex
                Content-disposition: attachment; filename="MEDIA_ID.speex"
                Date: Sun, 06 Jan 2016 10:20:18 GMT
                Cache-Control: no-cache, must-revalidate
                Content-Length: 339721
                curl -G "https://api.weixin.qq.com/cgi-bin/media/get/jssdk?access_token=ACCESS_TOKEN&media_id=MEDIA_ID"
        :param media_id:
        :param file_dir:  素材下载后的存放路径
        :param source_type:
        :return:
        """

        if source_type == "soft":
            url = self.soft_src_download_url
        elif source_type == "hard":
            url = self.hard_src_download_url
        else:
            raise Exception('素材类型传入错误。\n临时素材source_type=soft\n永久素材source_type=hard')

        params = {
            'access_token': self.token,
            'media_id': media_id
        }

        response = requests.get(url, params=params)
        file_name = response.headers.get('filename')
        file_path = file_dir / file_name

        with open(file_path, mode='wb') as wf:
            wf.write(response.content)

    def download_soft_source(self, media_id: str, file_dir):
        """
        下载临时素材
        :param media_id:
        :param file_dir:
        :return:
        """
        return self.download_source(media_id, file_dir)

    def download_hard_source(self, media_id: str, file_dir):
        """
        下载永久素材
        :param media_id:
        :param file_dir:
        :return:
        """
        return self.download_source(media_id, file_dir, source_type='hard')

    @runtime_decorator
    def delete_hard_src(self, media_id):
        """
        删除永久素材：
            成功时返回：{ "media_id":MEDIA_ID }
            失败时放回：{ "errcode":ERRCODE, "errmsg":ERRMSG }
        :param media_id:
        :return:
        """

        params = {
            'access_token': self.token,
            'media_id': media_id
        }

        response = requests.post(self.hard_src_delete_url, params=params)
        return response.json()

    @runtime_decorator
    def get_source_count(self):
        """
        获取永久素材各类型的数量。
        数据格式：
            {'voice_count': 0, 'video_count': 0, 'image_count': 0, 'news_count': 0}
        :return:
        """

        params = {
            'access_token': self.token,
        }

        response = requests.get(self.hard_src_count_url, params=params)
        return response.json()

    @runtime_decorator
    def get_source_list(self, src_type, offset: int = 0, count: int = 20):
        """
        获取永久素材列表
        :param src_type:素材的类型，图片（image）、视频（video）、语音 （voice）、图文（news）
        :param offset:从全部素材的该偏移位置开始返回，0表示从第一个素材 返回
        :param count:返回素材的数量，取值在1到20之间
        :return:
        """

        params = {
            'access_token': self.token,
        }

        data = {
            "type": src_type,
            "offset": offset,
            "count": count
        }

        response = requests.post(self.hard_src_list_url, json=data, params=params)
        return response.json()

    def get_menu(self):
        """
        获取公众号菜单
        :return:
        """
        response = requests.get(self.get_menu_url, params={'access_token': self.token, })
        return response.json()

    def create_menu(self, menu_data: dict):
        """
        公众号创建菜单
        :param menu_data:
        :return:
        """
        json_data = json.dumps(menu_data, ensure_ascii=False).encode('utf8')

        response = requests.post(self.create_menu_url, params={'access_token': self.token, }, data=json_data)
        return response.json()

    def delete_menu(self):
        """
        删除当前菜单
        :return:
        """
        response = requests.get(self.delete_menu_url, params={'access_token': self.token, })
        return response.json()

    def create_draft(self, article_data):
        # 对数据进行json处理，注意编码格式，微信不接受Unicode编码
        json_data = json.dumps(article_data, ensure_ascii=False).encode('utf8')

        response = requests.post(self.create_draft_url, data=json_data, params={'access_token': self.token, })
        return response.json()

    def get_draft(self, media_id):

        data = {
            "media_id": media_id,
        }

        response = requests.post(self.get_draft_url, json=data, params={'access_token': self.token, })
        return response.json()

    def update_draft(self, article_data):

        # 对数据进行json处理，注意编码格式，微信不接受Unicode编码
        json_data = json.dumps(article_data, ensure_ascii=False).encode('utf8')

        response = requests.post(self.update_draft_url, data=json_data, params={'access_token': self.token, })
        return response.json()

    def publish_news(self, media_id):
        """
        开发者需要先将图文素材以草稿的形式保存，
        选择要发布的草稿 media_id 进行发布
        :param media_id:
        :return:
        """
        data = {
            "media_id": media_id,
        }

        response = requests.post(self.publish_news_url, json=data, params={'access_token': self.token, })
        return response.json()

    def publish_status(self, publish_id):
        """
        此接口获知发布情况
        :param publish_id:
        :return:
        """
        data = {
            "publish_id": publish_id,
        }

        response = requests.post(self.publish_status_url, json=data, params={'access_token': self.token, })

        return response.json()

    def get_article_list(self, offset: str = 0, count: int = 20, no_content: int = 0):

        if count > 20:
            count = 20

        data = {
            "offset": offset,
            "count": count,
            "no_content": no_content
        }

        response = requests.post(self.article_list_url, json=data, params={'access_token': self.token, })

        return response.json()

    def get_article(self, article_id):
        data = {
            "article_id": article_id,
        }
        response = requests.post(self.get_article_url, json=data, params={'access_token': self.token, })
        # print(response.content.decode('utf8'))
        return response.json()

    def voice_to_text(self, file_path, voice_format, voice_id, lang: str = "zh_CN "):
        params = {
            "access_token": self.token,
            "format": voice_format,  # 文件格式 （只支持mp3，16k，单声道，最大1M）
            "voice_id": voice_id,
            "lang": lang,
        }

        with open(file_path, "rb") as f:
            files = {"media": f}
            response = requests.post(self.voice_to_text_url, files=files, params=params)

        return response.json()

    def get_voice_result(self):
        pass


if __name__ == '__main__':
    config = {
        "app_id": "wx3b2fd309f9f0710d",
        "app_secret": "fcc9c14c2c38c33554fac1eabe1eb577",
    }
    # cqalN82FuQva2a7feFRzuRlFsLEz17XOKVyrYrzwb7wcjAYFXW9o4HRcrceHISTP   临时素材media_id，一张图片

    # 一张永久素材（图片）
    # http://mmbiz.qpic.cn/sz_mmbiz_jpg/KSl3Ku9NC8HQjeicFsB5EPrGgeS4gzGU7qpma4ac1I5wYiaH2MryDjT54icP3Jb3IibiaWyicphNXMeDuQNFhrSicVauw/0

    # 菜单测试数据
    my_menu_data = {
        "button": [
            {
                "name": "扫码",
                "sub_button": [
                    {
                        "type": "scancode_waitmsg",
                        "name": "扫码带提示",
                        "key": "rselfmenu_0_0",
                        "sub_button": []
                    },
                    {
                        "type": "scancode_push",
                        "name": "扫码推事件",
                        "key": "rselfmenu_0_1",
                        "sub_button": []
                    }
                ]
            },
            {
                "name": "发图",
                "sub_button": [
                    {
                        "type": "pic_sysphoto",
                        "name": "系统拍照发图",
                        "key": "rselfmenu_1_0",
                        "sub_button": []
                    },
                    {
                        "type": "pic_photo_or_album",
                        "name": "拍照或者相册发图",
                        "key": "rselfmenu_1_1",
                        "sub_button": []
                    },
                    {
                        "type": "pic_weixin",
                        "name": "微信相册发图",
                        "key": "rselfmenu_1_2",
                        "sub_button": []
                    }
                ]
            },
            {
                "name": "发送位置",
                "type": "location_select",
                "key": "rselfmenu_2_0"
            },
            # {
            #    "type": "media_id",
            #    "name": "图片",
            #    "media_id": "MEDIA_ID1"
            # },
            # {
            #    "type": "view_limited",
            #    "name": "图文消息",
            #    "media_id": "MEDIA_ID2"
            # },
            # {
            #     "type": "article_id",
            #     "name": "发布后的图文消息",
            #     "article_id": "ARTICLE_ID1"
            # },
            # {
            #     "type": "article_view_limited",
            #     "name": "发布后的图文消息",
            #     "article_id": "ARTICLE_ID2"
            # }
        ]
    }

    # 永久素材：图片
    my_hard_image = {'media_id': 'x6lBIVCeGMg_tlN-qAPFWlTre1Ewq4xvZ3JDpdmXyliePP7_h6NG6lx74OY-31ct',
                     'url': 'http://mmbiz.qpic.cn/sz_mmbiz_jpg/KSl3Ku9NC8H0ubUaLXg2rqtyT1dbtbodNmrLbc2tpp89Kib9volNheDKibzpIdiacJOToZH3sr8Zn8HVEV08licibww/0?wx_fmt=jpeg',
                     'item': []}

    # 草稿测试数据
    my_draft = {
        "articles": [
            {
                "title": "一篇测试图文",
                "author": "子不语",
                "digest": '这是一篇来自python程序的测试图文',
                "content": 'this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!',
                "content_source_url": '',
                "thumb_media_id": 'x6lBIVCeGMg_tlN-qAPFWlTre1Ewq4xvZ3JDpdmXyliePP7_h6NG6lx74OY-31ct',
                "need_open_comment": 0,
                "only_fans_can_comment": 0
            }
        ]
    }

    handler = WechatHandler(config)
    # print(handler.token)
    # res = handler.create_menu(my_menu_data)  # 创建菜单
    # print(res)

    # 上传永久素材：图片
    # res = handler.upload_hard_source('image', 'D:\\zibuyu_project\\wechat_dev\\image\\5.jpg')
    # print(res)

    # 清除api调用限额
    # res = handler.clear_quota()

    # 获取永久素材中图片类型的列表
    # res = handler.get_source_list('image')

    # 创建一个草稿
    # res = handler.create_draft(my_draft)
    # {'media_id': 'x6lBIVCeGMg_tlN-qAPFWmoXgrKQiR8vmFJpIeXZ4PHvGtbvOMYYZh9ue4USGUP1', 'item': []}

    # 获取指定草稿
    # res = handler.get_draft('x6lBIVCeGMg_tlN-qAPFWmoXgrKQiR8vmFJpIeXZ4PHvGtbvOMYYZh9ue4USGUP1')

    # 修改草稿
    update_article = {
        "media_id": 'x6lBIVCeGMg_tlN-qAPFWmoXgrKQiR8vmFJpIeXZ4PHvGtbvOMYYZh9ue4USGUP1',
        "index": 0,
        "articles":
            {
                "title": "一篇测试图文",
                "author": "子不语",
                "digest": '这是一篇来自python程序的测试图文',
                "content": 'this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!',
                "content_source_url": '',
                "thumb_media_id": 'x6lBIVCeGMg_tlN-qAPFWlTre1Ewq4xvZ3JDpdmXyliePP7_h6NG6lx74OY-31ct',
                "need_open_comment": 0,
                "only_fans_can_comment": 0
            }

    }
    # res = handler.update_draft(update_article)

    # 发布一个草稿
    # res = handler.publish_news("x6lBIVCeGMg_tlN-qAPFWmoXgrKQiR8vmFJpIeXZ4PHvGtbvOMYYZh9ue4USGUP1")
    # {'errcode': 0, 'errmsg': 'ok', 'publish_id': 2247483651, 'msg_data_id': 2247483651}

    # 查询发布状态
    # res = handler.publish_status('2247483651')
    # {'publish_id': 2247483651, 'publish_status': 0, 'article_id': 'lcl7QHZYV7f-btPXGE2ieW_AKN8TfmSoMBBGMFaLG6oXqviK2jh1BgXylmTBqmLr', 'article_detail': {'count': 1, 'item': [{'idx': 1, 'article_url': 'http://mp.weixin.qq.com/s?__biz=MzkyOTQ5Mjg3OA==&mid=2247483651&idx=1&sn=85a065a12f189227d38ae37687dfeb9b&chksm=c209fbe2f57e72f47264b4dd5fdf6940d8c9a5f5d6ff96510285e4630df053e944f2ccd3ee92#rd'}]}, 'fail_idx': []}

    # 获取已发布的图文列表
    # res = handler.get_article_list()
    # 获取的结果
    article_list = {'item': [{'article_id': 'lcl7QHZYV7f-btPXGE2ieW_AKN8TfmSoMBBGMFaLG6oXqviK2jh1BgXylmTBqmLr',
                              'content': {'news_item': [{'title': 'ä¸\x80ç¯\x87æµ\x8bè¯\x95å\x9b¾æ\x96\x87',
                                                         'author': 'å\xad\x90ä¸\x8dè¯\xad',
                                                         'digest': 'è¿\x99æ\x98¯ä¸\x80ç¯\x87æ\x9d¥è\x87ªpythonç¨\x8båº\x8fç\x9a\x84æµ\x8bè¯\x95å\x9b¾æ\x96\x87',
                                                         'content': 'this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!',
                                                         'content_source_url': '',
                                                         'thumb_media_id': 'x6lBIVCeGMg_tlN-qAPFWlTre1Ewq4xvZ3JDpdmXyliePP7_h6NG6lx74OY-31ct',
                                                         'show_cover_pic': 0,
                                                         'url': 'http://mp.weixin.qq.com/s?__biz=MzkyOTQ5Mjg3OA==&mid=2247483651&idx=1&sn=85a065a12f189227d38ae37687dfeb9b&chksm=c209fbe2f57e72f47264b4dd5fdf6940d8c9a5f5d6ff96510285e4630df053e944f2ccd3ee92#rd',
                                                         'thumb_url': 'http://mmbiz.qpic.cn/sz_mmbiz_jpg/KSl3Ku9NC8H0ubUaLXg2rqtyT1dbtbodNmrLbc2tpp89Kib9volNheDKibzpIdiacJOToZH3sr8Zn8HVEV08licibww/0?wx_fmt=jpeg',
                                                         'need_open_comment': 0, 'only_fans_can_comment': 0,
                                                         'is_deleted': False}], 'create_time': 1699154821,
                                          'update_time': 1699154848}, 'update_time': 1699154848}], 'total_count': 1,
                    'item_count': 1}

    # res = handler.get_article('lcl7QHZYV7f-btPXGE2ieW_AKN8TfmSoMBBGMFaLG6oXqviK2jh1BgXylmTBqmLr')
    article = {"news_item": [{"title": "一篇测试图文", "author": "子不语", "digest": "这是一篇来自python程序的测试图文",
                              "content": "this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!this is a test news!",
                              "content_source_url": "",
                              "thumb_media_id": "x6lBIVCeGMg_tlN-qAPFWlTre1Ewq4xvZ3JDpdmXyliePP7_h6NG6lx74OY-31ct",
                              "show_cover_pic": 0,
                              "url": "http:\/\/mp.weixin.qq.com\/s?__biz=MzkyOTQ5Mjg3OA==&mid=2247483651&idx=1&sn=85a065a12f189227d38ae37687dfeb9b&chksm=c209fbe2f57e72f47264b4dd5fdf6940d8c9a5f5d6ff96510285e4630df053e944f2ccd3ee92#rd",
                              "thumb_url": "http:\/\/mmbiz.qpic.cn\/sz_mmbiz_jpg\/KSl3Ku9NC8H0ubUaLXg2rqtyT1dbtbodNmrLbc2tpp89Kib9volNheDKibzpIdiacJOToZH3sr8Zn8HVEV08licibww\/0?wx_fmt=jpeg",
                              "need_open_comment": 0, "only_fans_can_comment": 0, "is_deleted": False}],
               "create_time": 1699154821, "update_time": 1699154848}

    # 获取永久素材总数
    # res = handler.get_source_count()
    # print(res)
