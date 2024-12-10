# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/11/28
contact: 【公众号】思维兵工厂
description: 存储操作：七牛云、S3、webdav

(目前未使用)
--------------------------------------------
"""

import os
import time
from typing import Optional

import boto3
import qiniu
from webdav4.client import Client
from qiniu.services.cdn.manager import create_timestamp_anti_leech_url


class S3(object):
    def __init__(
            self,
            s3_endpoint: str,
            s3_region: str,
            s3_access_key: str,
            s3_secret_key: str,
            bucket_name: str,
    ):
        """
        初始化S3操作对象
        :param s3_endpoint:
        :param s3_region:
        :param s3_access_key:
        :param s3_secret_key:
        :param bucket_name:
        """

        self.s3_region: str = s3_region
        self.s3_endpoint: str = s3_endpoint
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
        """
        上传文件
        :param local_file_path: 本地文件路径
        :param remote_file_path: 远程文件路径
        :param bucket_name: 存储桶名称，可选，若为空则使用默认存储桶
        :return:
        """

        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f'file_path: 【{local_file_path}】 not found')

        return self.client.upload_file(
            local_file_path,
            bucket_name or self.bucket_name,
            remote_file_path,
        )

    def get_file_url(
            self,
            remote_file_path: str,
            bucket_name: str = '',
            expires: int = 3600
    ) -> str:
        """
        获取文件下载链接
        :param remote_file_path: 远程文件路径
        :param bucket_name: 存储桶名称，可选，若为空则使用默认存储桶
        :param expires: 链接有效期，单位秒，可选，默认3600
        :return:
        """

        return self.client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': bucket_name or self.bucket_name,
                'Key': remote_file_path,
            },
            ExpiresIn=expires
        )


class Qiniu(object):

    def __init__(
            self,
            access_key: str,
            secret_key: str,
            bucket_name: str,
    ):
        """
        初始化七牛云操作对象
        :param access_key:
        :param secret_key:
        :param bucket_name:
        """

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
            bucket_name: str = ''
    ) -> bool:
        """
        上传文件
        :param local_file_path: 本地文件路径
        :param remote_file_path: 远程文件路径
        :param bucket_name: 存储桶名称，可选，若为空则使用默认存储桶
        :return:
        """

        if isinstance(local_file_path, str) and os.path.exists(local_file_path) and os.path.isfile(local_file_path):
            with open(local_file_path, 'rb') as f:
                data = f.read()
        else:
            raise FileNotFoundError(f'file_path: 【{local_file_path}】 not found')

        try:
            token = self.__auth.upload_token(bucket_name or self.bucket_name)
            ret, info = qiniu.put_data(token, remote_file_path, data)

            if ret is not None:
                return True
            return False
        except:
            return False

    def get_file_info(self, key: str) -> dict:
        """
        获取文件信息
        :param key: 文件key
        :return: 文件信息字典
        """
        bucket_handler = qiniu.BucketManager(self.__auth)
        ret, info = bucket_handler.stat(self.bucket_name, key)
        if ret is not None:
            # ret：类似这样的数据结构
            # {
            #     'fsize': 2040316,
            #     'hash': 'FuDR3NoT4GXflba-RCWe6Wj2wZl-',
            #     'md5': 'c6af6e83c9d7acb66b89f0ca242461bb',
            #     'mimeType': 'application/zip',
            #     'putTime': 17337226624680971,
            #     'type': 0
            # }
            return ret
        else:
            return {}

    @staticmethod
    def get_file_url(
            bucket_domain: str,
            remote_file_path: str,
            expires: int = 3600
    ) -> str:
        """
        获取文件下载链接
        :param bucket_domain: 存储桶域名
        :param remote_file_path: 远程文件路径
        :param expires: 链接有效期，单位秒，可选，默认3600
        :return:
        """

        host = f'http:/{bucket_domain}'

        # 配置时间戳时指定的key
        encrypt_key = ''

        # 查询字符串,不需要加?
        query_string = ''

        # 截止日期的时间戳,秒为单位，3600为当前时间一小时之后过期
        deadline = int(time.time()) + expires

        timestamp_url = create_timestamp_anti_leech_url(host, remote_file_path, query_string, encrypt_key, deadline)

        return timestamp_url


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

    def download_file(
            self,
            remote_file_path: str,
            local_file_path: str,
    ) -> None:
        """
        下载文件
        :param remote_file_path: 远程文件路径
        :param local_file_path: 本地文件路径
        :return:
        """
        return self.client.download_file(
            from_path=remote_file_path,
            to_path=local_file_path
        )
