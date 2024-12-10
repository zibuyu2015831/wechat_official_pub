# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/11/28
contact: 【公众号】思维兵工厂
description: 部署腾讯云函数，上传markdown笔记到对象存储中

部署时需要为该函数设置以下环境变量，同时将部署之后得到的url写入主程序配置文件中：
    - storage_type[可选]：值为“qiniu”或“s3”或“webdav”，默认qiniu
    - token：鉴权token[可选]，如果传入，则只有token输入正确的请求才会处理；
    - save_note_path[可选]：笔记保存路径；
    - note_source[可选]：标记笔记来源；

    - qiniu_access_key[可选]：七牛云的access_key
    - qiniu_secret_key[可选]：七牛云的secret_key

    - bucket_name：对象存储bucket的名称；七牛云和s3都需要传入

    - s3_endpoint[可选]：s3对象存储的域名；
    - s3_region[可选]：s3对象存储的区域；
    - s3_access_key[可选]：s3对象存储的密钥；
    - s3_secret_key[可选]：s3对象存储的密钥；

    - webdav_url[可选]：WebDav对象存储的域名；
    - webdav_user[可选]：WebDav对象存储的用户名；
    - webdav_psw[可选]：WebDav对象存储的密钥；

该接口只接收POST请求，需要在请求体中传入如下参数：

    - token：用于鉴权；
    - note_title：字符串类型；默认为随机字符串；
    - note_content：字符串类型；笔记内容；
    - note_url[可选]：网址链接，若传入该值，则会忽略 note_title和note_content，改为获取网页内容；

    - save_note_path[可选]：笔记保存路径；默认在根目录下创建【000_cloud_note】文件夹
    - note_source[可选]：笔记来源，用于标记笔记属性；默认为：公众号【思维兵工厂】

    - storage_type[可选]：值为“qiniu”或“s3”或“webdav”，默认qiniu

    - qiniu_access_key[可选]：七牛云的access_key
    - qiniu_secret_key[可选]：七牛云的secret_key

    - bucket_name[可选]：对象存储bucket的名称；七牛云和s3都需要传入

    - s3_endpoint[可选]：s3对象存储的域名；
    - s3_region[可选]：s3对象存储的区域；
    - s3_access_key[可选]：s3对象存储的密钥；
    - s3_secret_key[可选]：s3对象存储的密钥；

    - webdav_url[可选]：WebDav对象存储的域名；
    - webdav_user[可选]：WebDav对象存储的用户名；
    - webdav_psw[可选]：WebDav对象存储的密钥；

--------------------------------------------
"""

import os
import json
import random
import requests
import datetime
from dataclasses import dataclass
from typing import Dict, Optional

import boto3
import qiniu
from webdav4.client import Client
from flask import Flask, request

IS_YUN_CLOUD = True  # 部署用
# IS_YUN_CLOUD = False  # 测试用

# 部署云函数时，根据环境变量判断是否为云函数部署（一般都会有TZ的环境变量）
TZ = os.getenv('TZ')
if TZ:
    IS_YUN_CLOUD = True


@dataclass
class Markdown:
    is_success: bool = False  # 请求是否成功

    title: str = ''
    source: str = ''
    content: str = ''


class WebDav(object):
    def __init__(
            self,
            webdav_url: str,
            webdav_username: str,
            webdav_password: str,
    ):
        """
        初始化WebDav操作对象
        :param webdav_url:
        :param webdav_username:
        :param webdav_password:
        """
        self.webdav_url = webdav_url
        self.webdav_username = webdav_username
        self.webdav_password = webdav_password

        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        if not self._client:
            self._client = Client(
                self.webdav_url,
                auth=(
                    self.webdav_username,
                    self.webdav_password
                )
            )
        return self._client

    def upload_file(
            self,
            local_file_path: str,
            remote_file_path: str,
    ) -> None:
        """
        上传文件
        :param local_file_path: 本地文件路径
        :param remote_file_path: 远程文件路径
        :return:
        """

        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f'file_path: 【{local_file_path}】 not found')

        return self.client.upload_file(
            from_path=local_file_path,
            to_path=remote_file_path
        )


class S3(object):
    def __init__(
            self,
            s3_endpoint: str,
            s3_region: str,
            s3_access_key: str,
            s3_secret_key: str,
            bucket_name: str,
    ):
        self.s3_endpoint: str = s3_endpoint
        self.s3_region: str = s3_region
        self.s3_access_key: str = s3_access_key
        self.s3_secret_key: str = s3_secret_key

        self.bucket_name: str = bucket_name

        self._client: Optional[boto3.client] = None

    @property
    def client(self):
        if not self._client:
            self._client = boto3.client(
                's3',
                aws_access_key_id=self.s3_access_key,
                aws_secret_access_key=self.s3_secret_key,
                endpoint_url=self.s3_endpoint,
                region_name=self.s3_region
            )
        return self._client

    def upload_file(
            self,
            local_file_path: str,
            remote_file_path: str,
            bucket_name: str = ''
    ):

        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f'file_path: 【{local_file_path}】 not found')

        return self.client.upload_file(
            local_file_path,
            bucket_name or self.bucket_name,
            remote_file_path,
        )


class Qiniu(object):

    def __init__(
            self,
            access_key: str,
            secret_key: str,
            bucket_name: str,
    ):

        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name

        self.__auth = qiniu.Auth(self.access_key, self.secret_key)

    def list_buckets(self, bucket_name: str) -> list:
        bucket_handler = qiniu.BucketManager(self.__auth)
        ret, eof, info = bucket_handler.list(bucket_name)
        return ret

    def upload_file(
            self,
            local_file_path: str,
            remote_file_path: str,
            bucket_name: str = '',
    ) -> bool:

        if isinstance(local_file_path, str) and os.path.exists(local_file_path) and os.path.isfile(local_file_path):
            with open(local_file_path, 'rb') as f:
                data = f.read()
        else:
            data = local_file_path

        token = self.__auth.upload_token(bucket_name or self.bucket_name)
        ret, info = qiniu.put_data(token, remote_file_path, data)

        if ret is not None:
            return True
        else:
            return False


class Handler(object):

    def __init__(self):

        # 存储类型
        self.storage_type = os.getenv('storage_type') or 'qiniu'
        self.yun_token = os.getenv('token')  # 云函数设置时设定的token，用于鉴权；

        # 请求数据
        self.data: Dict = json.loads(request.data.decode('utf-8'))

        self.note_url: str = ''  # 笔记URL，若该值不为空，则忽略 note_title 和 note_content
        self.note_title: str = ''  # 笔记标题；
        self.note_content: str = ''  # 笔记内容；
        self.save_note_path: str = os.getenv('save_note_path') or '000_cloud_note'  # 笔记保存路径；默认在根目录下创建
        self.note_source: str = os.getenv('note_source') or '公众号【思维兵工厂】'  # 笔记来源，用于标记笔记属性

        self._qiniu_handler: Optional[Qiniu] = None
        self._s3_handler: Optional[S3] = None
        self._webdav_handler: Optional[WebDav] = None

        self.message = ''

    @property
    def random_code(self, length: int = 5) -> str:
        """随机生成指定长度的数字字符串"""

        return ''.join(map(str, random.choices(range(10), k=length)))

    def is_token_valid(self) -> bool:
        if not self.yun_token:
            return True

        return self.yun_token == self.data.get('token')

    def get_note_from_url(self) -> bool:

        note_obj = self.convert_url_to_md(self.note_url)

        if not note_obj.is_success:
            return False

        self.note_title = f'{note_obj.title}.md'
        self.note_content = note_obj.content
        self.note_source = note_obj.source
        return True

    def is_note_valid(self) -> bool:

        self.note_url = self.data.get('note_url')  # 笔记链接
        self.storage_type = self.data.get('storage_type') or self.storage_type

        # 笔记保存路径；默认在根目录下创建
        self.save_note_path = self.data.get('save_note_path') or self.save_note_path

        if self.note_url:
            return self.get_note_from_url()

        self.note_title = self.data.get('note_title')  # 笔记标题

        if not self.note_title.endswith('.md'):
            self.note_title = f"{self.note_title}.md" if self.note_title else f"{self.random_code}.md"

        self.note_content = self.data.get('note_content')  # 字符串类型；笔记内容；
        self.note_source = self.data.get('note_source') or self.note_source  # 笔记来源，用于标记笔记属性

        return all([self.note_content, self.note_title])

    @staticmethod
    def convert_url_to_md(url: str) -> Markdown:
        """
        请求url获取html内容，转为markdown格式
        :param url:
        :return:
        """

        url = f'https://r.jina.ai/{url}'

        content_obj = Markdown()

        try:
            response = requests.get(url)

            lines = response.text.split('\n')

            title = ''
            source = ''
            for line in lines:

                if line.startswith('Title:'):
                    title = line.replace('Title:', '').strip()

                if line.startswith('URL Source:'):
                    source = line.replace('URL Source:', '').strip()

                if title and source:
                    break

            content_start_line = lines.index('Markdown Content:') + 1
            content = '\n'.join(lines[content_start_line:])

            content_obj.title = title
            content_obj.source = source
            content_obj.content = content
            content_obj.is_success = True
        except:
            content_obj.is_success = False
        finally:
            return content_obj

    @staticmethod
    def get_old_qiniu() -> Optional[Qiniu]:
        """获取旧的七牛云配置：从云函数的环境变量中获取配置"""

        # 七牛云配置，通过环境变量获取
        qiniu_access_key = os.getenv('qiniu_access_key')
        qiniu_secret_key = os.getenv('qiniu_secret_key')
        bucket_name = os.getenv('bucket_name')

        if all([qiniu_access_key, qiniu_secret_key, bucket_name]):
            return Qiniu(
                access_key=qiniu_access_key,
                secret_key=qiniu_secret_key,
                bucket_name=bucket_name,
            )

    @staticmethod
    def get_old_s3() -> Optional[S3]:
        """获取旧的s3配置：从云函数的环境变量中获取配置"""

        s3_endpoint = os.getenv('s3_endpoint')
        s3_region = os.getenv('s3_region')
        s3_access_key = os.getenv('s3_access_key')
        s3_secret_key = os.getenv('s3_secret_key')
        bucket_name = os.getenv('bucket_name')

        if not all([s3_endpoint, s3_region, s3_access_key, s3_secret_key, bucket_name]):
            return None

        return S3(
            s3_endpoint=s3_endpoint,
            s3_region=s3_region,
            s3_access_key=s3_access_key,
            s3_secret_key=s3_secret_key,
            bucket_name=bucket_name
        )

    @staticmethod
    def get_old_webdav() -> Optional[WebDav]:

        webdav_url = os.getenv('webdav_url')
        webdav_user = os.getenv('webdav_user')
        webdav_psw = os.getenv('webdav_psw')

        if not all([webdav_url, webdav_user, webdav_psw]):
            return None

        return WebDav(webdav_url, webdav_user, webdav_psw)

    def get_new_qiniu(self) -> Optional[Qiniu]:
        """获取新的七牛云配置：从请求数据中获取配置"""

        new_qiniu_access_key = self.data.get('qiniu_access_key')
        new_qiniu_secret_key = self.data.get('qiniu_secret_key')
        new_bucket_name = self.data.get('bucket_name')

        if all([new_qiniu_access_key, new_qiniu_secret_key, new_bucket_name]):
            return Qiniu(
                access_key=new_qiniu_access_key,
                secret_key=new_qiniu_secret_key,
                bucket_name=new_bucket_name,
            )

    def get_new_s3(self) -> Optional[S3]:
        """获取新的s3配置：从请求数据中获取配置"""

        new_s3_endpoint = self.data.get('s3_endpoint')
        new_s3_region = self.data.get('s3_region')
        new_s3_access_key = self.data.get('s3_access_key')
        new_s3_secret_key = self.data.get('s3_secret_key')
        new_bucket_name = self.data.get('bucket_name')

        if not all([new_s3_endpoint, new_s3_region, new_s3_access_key, new_s3_secret_key, new_bucket_name]):
            return None

        return S3(
            s3_endpoint=new_s3_endpoint,
            s3_region=new_s3_region,
            s3_access_key=new_s3_access_key,
            s3_secret_key=new_s3_secret_key,
            bucket_name=new_bucket_name
        )

    def get_new_webdav(self) -> Optional[WebDav]:
        """获取新的webdav配置：从请求数据中获取配置"""

        new_webdav_url = self.data.get('webdav_url')
        new_webdav_user = self.data.get('webdav_user')
        new_webdav_psw = self.data.get('webdav_psw')
        if not all([new_webdav_url, new_webdav_user, new_webdav_psw]):
            return None

        return WebDav(new_webdav_url, new_webdav_user, new_webdav_psw)

    @property
    def s3_handler(self) -> S3:
        if not self._s3_handler:
            self._s3_handler = self.get_new_s3() or self.get_old_s3()

        if not self._s3_handler:
            self.message = 'S3存储配置初始化失败'
            raise Exception('S3存储配置初始化失败；本地无配置信息，请求信息中也无配置信息')

        return self._s3_handler

    @property
    def qiniu_handler(self) -> Qiniu:

        if not self._qiniu_handler:
            self._qiniu_handler = self.get_new_qiniu() or self.get_old_qiniu()

        if not self._qiniu_handler:
            self.message = '七牛云存储配置初始化失败'
            raise Exception('七牛云存储配置初始化失败；本地无配置信息，请求信息中也无配置信息')

        return self._qiniu_handler

    @property
    def webdav_handler(self) -> WebDav:
        if not self._webdav_handler:
            self._webdav_handler = self.get_new_webdav() or self.get_old_webdav()

        if not self._webdav_handler:
            self.message = 'WebDAV存储配置初始化失败'
            raise Exception('WebDAV存储配置初始化失败；本地无配置信息，请求信息中也无配置信息')

        return self._webdav_handler

    @property
    def current_data_str(self) -> str:

        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def save_note_file(self) -> str:
        """
        保存笔记文件
        :return: 成功时返回笔记的路径
        """

        note_content = f'[原文链接]({self.note_url})\n{self.note_content}' if self.note_url else self.note_content

        note_content = f"""---
date: {self.current_data_str}
source: {self.note_source}
---

{note_content}
"""

        if IS_YUN_CLOUD:
            file_path = os.path.join('/tmp', self.note_title)
        else:
            file_path = f"{self.note_title}.md"

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(note_content)

            return file_path
        except:
            return ''

    def upload_file_to_s3(self, local_voice_path: str, remote_file_path: str) -> bool:
        """
        上传文件到S3
        :param local_voice_path:
        :param remote_file_path:
        :return:
        """

        try:
            self.s3_handler.upload_file(local_voice_path, remote_file_path)
            return True
        except Exception as e:
            self.message = f'上传笔记到七牛云发送未知错误，【{e}】'
            return False

    def upload_file_to_qiniu(self, local_voice_path: str, remote_file_path: str) -> bool:
        """
        上传文件到七牛云
        :param local_voice_path: 音频文件路径
        :param remote_file_path:
        :return: 文件访问链接
        """

        try:
            self.qiniu_handler.upload_file(
                local_file_path=local_voice_path,
                remote_file_path=remote_file_path
            )
            return True
        except Exception as e:
            self.message = f'上传笔记到七牛云发送未知错误，【{e}】'
            return False

    def upload_file_to_webdav(self, local_voice_path: str, remote_file_path: str) -> bool:
        """
        上传文件到webdav
        :param local_voice_path:
        :param remote_file_path:
        :return:
        """

        try:
            if not self.webdav_handler.client.exists(self.save_note_path):
                self.webdav_handler.client.mkdir(self.save_note_path)

            self.webdav_handler.upload_file(local_voice_path, remote_file_path)
            return True
        except Exception as e:
            self.message = f'上传笔记到WebDAV发送未知错误，【{e}】'
            return False

    def upload_file(self, local_file_path: str, remote_file_path: str) -> bool:

        if not self.storage_type:
            return False

        result = False
        storage_type = self.storage_type.lower()
        if storage_type == 'qiniu':
            result = self.upload_file_to_qiniu(local_file_path, remote_file_path)
        elif storage_type == 's3':
            result = self.upload_file_to_s3(local_file_path, remote_file_path)
        elif storage_type == 'webdav':
            result = self.upload_file_to_webdav(local_file_path, remote_file_path)

        if not result:
            return False

        self.message = f'上传笔记到【{self.storage_type}】成功'
        return True

    def run(self) -> str:

        if not self.is_token_valid():
            return 'token 鉴权失败'

        if not self.is_note_valid():
            return '笔记内容或标题为空'

        local_note_path = self.save_note_file()
        if not local_note_path:
            return '笔记文件保存失败'

        self.upload_file(
            local_file_path=local_note_path,
            remote_file_path=f'{self.save_note_path}/{self.note_title}'
        )

        return self.message


app = Flask(__name__)


@app.route('/upload_note', methods=['post'])
def run():
    if request.method.lower() != 'post':
        return 'request method is not post'

    handler = Handler()

    return handler.run()


if __name__ == '__main__':
    TZ = os.getenv('TZ')

    if TZ:
        app.run(host='0.0.0.0', port=9000)
    else:
        app.run(host='127.0.0.1', port=9000)
