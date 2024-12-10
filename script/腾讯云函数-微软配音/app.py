# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/11/25
contact: 【公众号】思维兵工厂
description: 本脚本用于部署腾讯云的web云函数，实现文本转语音功能；

要求python版本 >= 3.9；其中 main_handler 也可单独用于部署事件云函数；

处理流程：

    1. 利用微软接口，将文本转为语音；
    2. 将该音频上传至七牛云的对象存储或符合S3协议的对象存储，同时获取音频下载链接；
    3. 将音传入的文件名称与上一步得到的音频下载链接，写入数据库；作为公众号的关键词自动回复；
    4. 返回音频下载链接；

部署时需要为该函数设置以下环境变量，同时将部署之后得到的url写入主程序配置文件中：

    - token：鉴权token[可选]，如果传入，则只有token输入正确的请求才会处理；
    - storage_type[可选]：值为“qiniu”或“s3”，默认s3
    - text_tip：回复文本的额外提示[可选]；

    - qiniu_access_key[可选]：七牛云的access_key
    - qiniu_secret_key[可选]：七牛云的secret_key
    - bucket_domain[可选]：对象存储bucket的域名

    - bucket_name：对象存储bucket的名称

    - s3_endpoint[可选]：s3对象存储的域名；
    - s3_region[可选]：s3对象存储的区域；
    - s3_access_key[可选]：s3对象存储的密钥；
    - s3_secret_key[可选]：s3对象存储的密钥；

    - db_ip：数据库 ip
    - db_port：数据库 port
    - db_name：数据库 name
    - db_user：数据库 user
    - db_password：数据库 password

部署事件云函数时，需要自行安装三个依赖包（psycopg2容易出现依赖问题）：

    - qiniu
    - edge_tts
    - psycopg2-binary

该接口只接收POST请求，需要在请求体中传入如下参数：

    - token：用于鉴权；
    - official_user_id：该用户的公众号id
    - voice_choice：字符串类型；音色选择；
    - text：字符串类型；待配音的文本；
    - file_name：字符串类型；音频文件名，也作为用户获取音频的关键字；默认为随机字符串；
    - expires：整数类型；音频链接有效期[可选]，单位秒，默认3600；
    - has_change_db：布尔类型；是否根据关键词和用户的公众号ID，修改数据库中对应数据，默认为True

返回数据格式：

{
    "code": 状态码，0表示成功,
    "message": 提示信息,
    "url": 音频下载地址,
    "keyword": 关键词，根据该关键词在公众号获取音频,
    "expires": 音频链接有效期，单位秒,
    "has_change_db": 是否修改数据库,
}
--------------------------------------------
"""

import os
import json
import time
import random
import asyncio
import traceback
from typing import Dict, Optional

import boto3
import qiniu
import edge_tts
import psycopg2
from flask import Flask, request
from qiniu.services.cdn.manager import create_timestamp_anti_leech_url

IS_YUN_CLOUD = True  # 部署用
# IS_YUN_CLOUD = False  # 测试用

# 部署云函数时，根据环境变量判断是否为云函数部署（一般都会有TZ的环境变量）
TZ = os.getenv('TZ')
if TZ:
    IS_YUN_CLOUD = True

STORAGE_LIST = ['qiniu', 's3']

app = Flask(__name__)


class DBHandler(object):
    def __init__(
            self,
            db_ip: str,
            db_port: str,
            db_name: str,
            db_user: str,
            db_password: str
    ):
        self.db_ip = db_ip
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password

    def execute_single_sql(self, sql: str, params: Dict) -> bool:
        """
        执行SQL语句，返回查询结果
        :param sql: SQL语句
        :param params: 以字典形式传入参数
        :return: 查询结果
        """

        try:
            with psycopg2.connect(host=self.db_ip,
                                  port=self.db_port,
                                  dbname=self.db_name,
                                  user=self.db_user,
                                  password=self.db_password) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                conn.commit()

            return True
        except:
            return False


class S3Handler(object):
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

    def get_file_url(
            self,
            remote_file_path: str,
            bucket_name: str = '',
            expires: int = 3600
    ) -> str:
        return self.client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': bucket_name or self.bucket_name,
                'Key': remote_file_path,
            },
            ExpiresIn=expires
        )


class QiniuHandler(object):

    def __init__(self, access_key: str, secret_key: str):
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.access_key = access_key
        self.secret_key = secret_key
        self.__auth = qiniu.Auth(self.access_key, self.secret_key)

    def list_buckets(self, bucket_name: str) -> list:
        bucket_handler = qiniu.BucketManager(self.__auth)
        ret, eof, info = bucket_handler.list(bucket_name)
        return ret

    def upload_file(
            self,
            bucket_name: str,
            local_file_path: str,
            remote_file_path: str
    ) -> bool:

        if isinstance(local_file_path, str) and os.path.exists(local_file_path) and os.path.isfile(local_file_path):
            with open(local_file_path, 'rb') as f:
                data = f.read()
        else:
            data = local_file_path

        token = self.__auth.upload_token(bucket_name)
        ret, info = qiniu.put_data(token, remote_file_path, data)

        if ret is not None:
            return True
        else:
            return False

    @staticmethod
    def get_file_url(
            bucket_domain: str,
            remote_file_path: str,
            expires: int = 3600
    ) -> str:

        host = f'http:/{bucket_domain}'

        # 配置时间戳时指定的key
        encrypt_key = ''

        # 查询字符串,不需要加?
        query_string = ''

        # 截止日期的时间戳,秒为单位，3600为当前时间一小时之后过期
        deadline = int(time.time()) + expires

        timestamp_url = create_timestamp_anti_leech_url(host, remote_file_path, query_string, encrypt_key, deadline)

        return timestamp_url


class Handler(object):

    def __init__(self):

        self.storage_type = os.getenv('storage_type') or 's3'

        # 七牛云对象存储配置
        self.qiniu_access_key = os.getenv('qiniu_access_key')
        self.qiniu_secret_key = os.getenv('qiniu_secret_key')
        self.bucket_domain = os.getenv('bucket_domain')

        # s3对象存储配置
        self.s3_endpoint = os.getenv('s3_endpoint')
        self.s3_region = os.getenv('s3_region')
        self.s3_access_key = os.getenv('s3_access_key')
        self.s3_secret_key = os.getenv('s3_secret_key')

        self.bucket_name = os.getenv('bucket_name')

        self.token = os.getenv('token')

        # 数据库连接信息
        self.db_ip = os.getenv('db_ip')
        self.db_port = os.getenv('db_port')
        self.db_name = os.getenv('db_name')
        self.db_user = os.getenv('db_user')
        self.db_password = os.getenv('db_password')

        self.text_tip: str = os.getenv('text_tip', '')

        self.event: Optional[Dict] = None  # 云函数请求传入的参数
        self.code: int = -1  # 返回状态码，默认为-1（失败）
        self.message: str = ''  # 请求信息
        self.url: str = ''  # 配音完成后的音频下载链接
        self.official_user_id: str = ''  # 用户在公众号的ID

        # 音频有效期，单位秒，默认3600秒
        try:
            self.expires = int(os.getenv('expires', 3600))
        except:
            self.expires = 3600

        self.file_name: str = ''  # 配音完成后的音频名称
        self.text: str = ''  # 待配音的文本
        self.voice_choice: str = ''  # 配音的音色选择
        self.has_change_db: bool = True  # 是否需要修改数据库中的对应数据

        # 微软语音接口支持的音色列表
        self.ms_voice_list = [
            "af-ZA-AdriNeural",
            "af-ZA-WillemNeural",
            "am-ET-AmehaNeural",
            "am-ET-MekdesNeural",
            "ar-AE-FatimaNeural",
            "ar-AE-HamdanNeural",
            "ar-BH-AliNeural",
            "ar-BH-LailaNeural",
            "ar-DZ-AminaNeural",
            "ar-DZ-IsmaelNeural",
            "ar-EG-SalmaNeural",
            "ar-EG-ShakirNeural",
            "ar-IQ-BasselNeural",
            "ar-IQ-RanaNeural",
            "ar-JO-SanaNeural",
            "ar-JO-TaimNeural",
            "ar-KW-FahedNeural",
            "ar-KW-NouraNeural",
            "ar-LB-LaylaNeural",
            "ar-LB-RamiNeural",
            "ar-LY-ImanNeural",
            "ar-LY-OmarNeural",
            "ar-MA-JamalNeural",
            "ar-MA-MounaNeural",
            "ar-OM-AbdullahNeural",
            "ar-OM-AyshaNeural",
            "ar-QA-AmalNeural",
            "ar-QA-MoazNeural",
            "ar-SA-HamedNeural",
            "ar-SA-ZariyahNeural",
            "ar-SY-AmanyNeural",
            "ar-SY-LaithNeural",
            "ar-TN-HediNeural",
            "ar-TN-ReemNeural",
            "ar-YE-MaryamNeural",
            "ar-YE-SalehNeural",
            "az-AZ-BabekNeural",
            "az-AZ-BanuNeural",
            "bg-BG-BorislavNeural",
            "bg-BG-KalinaNeural",
            "bn-BD-NabanitaNeural",
            "bn-BD-PradeepNeural",
            "bn-IN-BashkarNeural",
            "bn-IN-TanishaaNeural",
            "bs-BA-GoranNeural",
            "bs-BA-VesnaNeural",
            "ca-ES-EnricNeural",
            "ca-ES-JoanaNeural",
            "cs-CZ-AntoninNeural",
            "cs-CZ-VlastaNeural",
            "cy-GB-AledNeural",
            "cy-GB-NiaNeural",
            "da-DK-ChristelNeural",
            "da-DK-JeppeNeural",
            "de-AT-IngridNeural",
            "de-AT-JonasNeural",
            "de-CH-JanNeural",
            "de-CH-LeniNeural",
            "de-DE-AmalaNeural",
            "de-DE-ConradNeural",
            "de-DE-FlorianMultilingualNeural",
            "de-DE-KatjaNeural",
            "de-DE-KillianNeural",
            "de-DE-SeraphinaMultilingualNeural",
            "el-GR-AthinaNeural",
            "el-GR-NestorasNeural",
            "en-AU-NatashaNeural",
            "en-AU-WilliamNeural",
            "en-CA-ClaraNeural",
            "en-CA-LiamNeural",
            "en-GB-LibbyNeural",
            "en-GB-MaisieNeural",
            "en-GB-RyanNeural",
            "en-GB-SoniaNeural",
            "en-GB-ThomasNeural",
            "en-HK-SamNeural",
            "en-HK-YanNeural",
            "en-IE-ConnorNeural",
            "en-IE-EmilyNeural",
            "en-IN-NeerjaExpressiveNeural",
            "en-IN-NeerjaNeural",
            "en-IN-PrabhatNeural",
            "en-KE-AsiliaNeural",
            "en-KE-ChilembaNeural",
            "en-NG-AbeoNeural",
            "en-NG-EzinneNeural",
            "en-NZ-MitchellNeural",
            "en-NZ-MollyNeural",
            "en-PH-JamesNeural",
            "en-PH-RosaNeural",
            "en-SG-LunaNeural",
            "en-SG-WayneNeural",
            "en-TZ-ElimuNeural",
            "en-TZ-ImaniNeural",
            "en-US-AnaNeural",
            "en-US-AndrewMultilingualNeural",
            "en-US-AndrewNeural",
            "en-US-AriaNeural",
            "en-US-AvaMultilingualNeural",
            "en-US-AvaNeural",
            "en-US-BrianMultilingualNeural",
            "en-US-BrianNeural",
            "en-US-ChristopherNeural",
            "en-US-EmmaMultilingualNeural",
            "en-US-EmmaNeural",
            "en-US-EricNeural",
            "en-US-GuyNeural",
            "en-US-JennyNeural",
            "en-US-MichelleNeural",
            "en-US-RogerNeural",
            "en-US-SteffanNeural",
            "en-ZA-LeahNeural",
            "en-ZA-LukeNeural",
            "es-AR-ElenaNeural",
            "es-AR-TomasNeural",
            "es-BO-MarceloNeural",
            "es-BO-SofiaNeural",
            "es-CL-CatalinaNeural",
            "es-CL-LorenzoNeural",
            "es-CO-GonzaloNeural",
            "es-CO-SalomeNeural",
            "es-CR-JuanNeural",
            "es-CR-MariaNeural",
            "es-CU-BelkysNeural",
            "es-CU-ManuelNeural",
            "es-DO-EmilioNeural",
            "es-DO-RamonaNeural",
            "es-EC-AndreaNeural",
            "es-EC-LuisNeural",
            "es-ES-AlvaroNeural",
            "es-ES-ElviraNeural",
            "es-ES-XimenaNeural",
            "es-GQ-JavierNeural",
            "es-GQ-TeresaNeural",
            "es-GT-AndresNeural",
            "es-GT-MartaNeural",
            "es-HN-CarlosNeural",
            "es-HN-KarlaNeural",
            "es-MX-DaliaNeural",
            "es-MX-JorgeNeural",
            "es-NI-FedericoNeural",
            "es-NI-YolandaNeural",
            "es-PA-MargaritaNeural",
            "es-PA-RobertoNeural",
            "es-PE-AlexNeural",
            "es-PE-CamilaNeural",
            "es-PR-KarinaNeural",
            "es-PR-VictorNeural",
            "es-PY-MarioNeural",
            "es-PY-TaniaNeural",
            "es-SV-LorenaNeural",
            "es-SV-RodrigoNeural",
            "es-US-AlonsoNeural",
            "es-US-PalomaNeural",
            "es-UY-MateoNeural",
            "es-UY-ValentinaNeural",
            "es-VE-PaolaNeural",
            "es-VE-SebastianNeural",
            "et-EE-AnuNeural",
            "et-EE-KertNeural",
            "fa-IR-DilaraNeural",
            "fa-IR-FaridNeural",
            "fi-FI-HarriNeural",
            "fi-FI-NooraNeural",
            "fil-PH-AngeloNeural",
            "fil-PH-BlessicaNeural",
            "fr-BE-CharlineNeural",
            "fr-BE-GerardNeural",
            "fr-CA-AntoineNeural",
            "fr-CA-JeanNeural",
            "fr-CA-SylvieNeural",
            "fr-CA-ThierryNeural",
            "fr-CH-ArianeNeural",
            "fr-CH-FabriceNeural",
            "fr-FR-DeniseNeural",
            "fr-FR-EloiseNeural",
            "fr-FR-HenriNeural",
            "fr-FR-RemyMultilingualNeural",
            "fr-FR-VivienneMultilingualNeural",
            "ga-IE-ColmNeural",
            "ga-IE-OrlaNeural",
            "gl-ES-RoiNeural",
            "gl-ES-SabelaNeural",
            "gu-IN-DhwaniNeural",
            "gu-IN-NiranjanNeural",
            "he-IL-AvriNeural",
            "he-IL-HilaNeural",
            "hi-IN-MadhurNeural",
            "hi-IN-SwaraNeural",
            "hr-HR-GabrijelaNeural",
            "hr-HR-SreckoNeural",
            "hu-HU-NoemiNeural",
            "hu-HU-TamasNeural",
            "id-ID-ArdiNeural",
            "id-ID-GadisNeural",
            "is-IS-GudrunNeural",
            "is-IS-GunnarNeural",
            "it-IT-DiegoNeural",
            "it-IT-ElsaNeural",
            "it-IT-GiuseppeMultilingualNeural",
            "it-IT-IsabellaNeural",
            "iu-Cans-CA-SiqiniqNeural",
            "iu-Cans-CA-TaqqiqNeural",
            "iu-Latn-CA-SiqiniqNeural",
            "iu-Latn-CA-TaqqiqNeural",
            "ja-JP-KeitaNeural",
            "ja-JP-NanamiNeural",
            "jv-ID-DimasNeural",
            "jv-ID-SitiNeural",
            "ka-GE-EkaNeural",
            "ka-GE-GiorgiNeural",
            "kk-KZ-AigulNeural",
            "kk-KZ-DauletNeural",
            "km-KH-PisethNeural",
            "km-KH-SreymomNeural",
            "kn-IN-GaganNeural",
            "kn-IN-SapnaNeural",
            "ko-KR-HyunsuMultilingualNeural",
            "ko-KR-InJoonNeural",
            "ko-KR-SunHiNeural",
            "lo-LA-ChanthavongNeural",
            "lo-LA-KeomanyNeural",
            "lt-LT-LeonasNeural",
            "lt-LT-OnaNeural",
            "lv-LV-EveritaNeural",
            "lv-LV-NilsNeural",
            "mk-MK-AleksandarNeural",
            "mk-MK-MarijaNeural",
            "ml-IN-MidhunNeural",
            "ml-IN-SobhanaNeural",
            "mn-MN-BataaNeural",
            "mn-MN-YesuiNeural",
            "mr-IN-AarohiNeural",
            "mr-IN-ManoharNeural",
            "ms-MY-OsmanNeural",
            "ms-MY-YasminNeural",
            "mt-MT-GraceNeural",
            "mt-MT-JosephNeural",
            "my-MM-NilarNeural",
            "my-MM-ThihaNeural",
            "nb-NO-FinnNeural",
            "nb-NO-PernilleNeural",
            "ne-NP-HemkalaNeural",
            "ne-NP-SagarNeural",
            "nl-BE-ArnaudNeural",
            "nl-BE-DenaNeural",
            "nl-NL-ColetteNeural",
            "nl-NL-FennaNeural",
            "nl-NL-MaartenNeural",
            "pl-PL-MarekNeural",
            "pl-PL-ZofiaNeural",
            "ps-AF-GulNawazNeural",
            "ps-AF-LatifaNeural",
            "pt-BR-AntonioNeural",
            "pt-BR-FranciscaNeural",
            "pt-BR-ThalitaMultilingualNeural",
            "pt-PT-DuarteNeural",
            "pt-PT-RaquelNeural",
            "ro-RO-AlinaNeural",
            "ro-RO-EmilNeural",
            "ru-RU-DmitryNeural",
            "ru-RU-SvetlanaNeural",
            "si-LK-SameeraNeural",
            "si-LK-ThiliniNeural",
            "sk-SK-LukasNeural",
            "sk-SK-ViktoriaNeural",
            "sl-SI-PetraNeural",
            "sl-SI-RokNeural",
            "so-SO-MuuseNeural",
            "so-SO-UbaxNeural",
            "sq-AL-AnilaNeural",
            "sq-AL-IlirNeural",
            "sr-RS-NicholasNeural",
            "sr-RS-SophieNeural",
            "su-ID-JajangNeural",
            "su-ID-TutiNeural",
            "sv-SE-MattiasNeural",
            "sv-SE-SofieNeural",
            "sw-KE-RafikiNeural",
            "sw-KE-ZuriNeural",
            "sw-TZ-DaudiNeural",
            "sw-TZ-RehemaNeural",
            "ta-IN-PallaviNeural",
            "ta-IN-ValluvarNeural",
            "ta-LK-KumarNeural",
            "ta-LK-SaranyaNeural",
            "ta-MY-KaniNeural",
            "ta-MY-SuryaNeural",
            "ta-SG-AnbuNeural",
            "ta-SG-VenbaNeural",
            "te-IN-MohanNeural",
            "te-IN-ShrutiNeural",
            "th-TH-NiwatNeural",
            "th-TH-PremwadeeNeural",
            "tr-TR-AhmetNeural",
            "tr-TR-EmelNeural",
            "uk-UA-OstapNeural",
            "uk-UA-PolinaNeural",
            "ur-IN-GulNeural",
            "ur-IN-SalmanNeural",
            "ur-PK-AsadNeural",
            "ur-PK-UzmaNeural",
            "uz-UZ-MadinaNeural",
            "uz-UZ-SardorNeural",
            "vi-VN-HoaiMyNeural",
            "vi-VN-NamMinhNeural",
            "zh-CN-XiaoxiaoNeural",
            "zh-CN-XiaoyiNeural",
            "zh-CN-YunjianNeural",
            "zh-CN-YunxiNeural",
            "zh-CN-YunxiaNeural",
            "zh-CN-YunyangNeural",
            "zh-CN-liaoning-XiaobeiNeural",
            "zh-CN-shaanxi-XiaoniNeural",
            "zh-HK-HiuGaaiNeural",
            "zh-HK-HiuMaanNeural",
            "zh-HK-WanLungNeural",
            "zh-TW-HsiaoChenNeural",
            "zh-TW-HsiaoYuNeural",
            "zh-TW-YunJheNeural",
            "zu-ZA-ThandoNeural",
            "zu-ZA-ThembaNeural"
        ]

    @property
    def result(self) -> str:
        return json.dumps({
            "code": self.code,
            "message": self.message,
            "url": self.url,
            "keyword": self.file_name,
            "expires": self.expires,
            "has_change_db": self.has_change_db,
        })

    @property
    def random_code(self, length: int = 5) -> str:
        """随机生成指定长度的数字字符串"""
        return ''.join(map(str, random.choices(range(10), k=length)))

    def check_db(self):
        if not all([self.db_ip, self.db_port, self.db_name, self.db_user, self.db_password]):
            self.message = '数据库配置错误'
            return False
        return True

    def check_token(self, data: Dict) -> bool:

        if not self.token:
            return True

        query_string = self.event.get('queryString', {})

        token = query_string.get('token') or data.get('token')
        if not token:
            self.message = '参数缺失，没有通过请求参数传入token'
            return False

        if token == self.token:
            return True

        self.message = 'token验证不通过'
        return False

    def check_data(self) -> bool:

        data = json.loads(self.event.get('body', '{}'))

        if not data or not isinstance(data, dict):
            self.message = '参数缺失，没有传入data'
            return False

        request_method = self.event.get('httpMethod')
        if not request_method or request_method.upper() != 'POST':
            self.message = '请求方式错误，只支持POST请求'
            return False

        self.file_name = data.get('file_name')
        if not self.file_name:
            self.message = '参数缺失，没有传入音频文件名'
            return False

        self.has_change_db = data.get('has_change_db', True)

        self.official_user_id = data.get('official_user_id')
        if not self.official_user_id:
            self.message = '请传入公众号用户ID'
            return False

        self.voice_choice = data.get('voice_choice', '')
        if not self.voice_choice:
            self.message = '参数缺失，没有传入配音音色'
            return False

        if self.voice_choice not in self.ms_voice_list:
            self.message = '参数错误，配音音色选择错误'
            return False

        self.text = data.get('text', '')
        if not self.text:
            self.message = '参数缺失，没有传入配音文本'
            return False

        return True

    def check_s3(self) -> bool:
        if not all([self.bucket_name, self.s3_access_key, self.s3_secret_key, self.s3_endpoint, self.s3_region]):
            self.message = 'S3参数缺失'
            return False
        return True

    def check_qiniu(self) -> bool:
        if not all([self.qiniu_access_key, self.qiniu_secret_key, self.bucket_domain, self.bucket_name]):
            self.message = '七牛云参数缺失'
            return False
        return True

    def check_storage(self):

        if self.storage_type == 'qiniu':
            return self.check_qiniu()
        elif self.storage_type == 's3':
            return self.check_s3()
        else:
            self.message = '存储类型错误'
            return False

    def check_request(self) -> bool:
        """检查请求参数、数据库配置、对象存储配置、token是否合法"""

        data = json.loads(self.event.get('body', '{}'))

        return self.check_data() and self.check_db() and self.check_storage() and self.check_token(data)

    @staticmethod
    async def ms_text_to_voice(text: str, file_name: str, voice_choice: str = 'zh-CN-XiaoxiaoNeural') -> str:
        """
        :param text: 待转换的文本
        :param voice_choice: 语音类型
        :param file_name: 文件名
        :return: 文件路径
        """

        try:
            file_name = file_name.replace('.mp3', '')

            if IS_YUN_CLOUD:
                file_path = os.path.join('/tmp', f"{file_name}.mp3")
            else:
                file_path = f"{file_name}.mp3"

            communicate = edge_tts.Communicate(text, voice_choice)
            await communicate.save(file_path)

            return file_path
        except:
            return ''

    def handle_tts(self) -> str:

        # 提交协程任务，生成音频
        return asyncio.run(self.ms_text_to_voice(
            text=self.text,
            voice_choice=self.voice_choice,
            file_name=self.file_name
        ))

    def upload_file(self, local_voice_path: str):

        if not os.path.exists(local_voice_path):
            self.message = '音频文件不存在'
            return ''

        strip_file_name = self.file_name.replace('.mp3', '')
        if self.official_user_id:
            remote_file_path = f"text-to-voice/{self.official_user_id}/{strip_file_name}.mp3"
        else:
            remote_file_path = f"text-to-voice/{strip_file_name}.mp3"

        if self.storage_type == 'qiniu':
            return self.upload_file_to_qiniu(local_voice_path, remote_file_path)
        return self.upload_file_to_s3(local_voice_path, remote_file_path)

    def upload_file_to_s3(self, local_voice_path: str, remote_file_path: str) -> str:
        try:
            s3_handler = S3Handler(
                s3_access_key=self.s3_access_key,
                s3_secret_key=self.s3_secret_key,
                s3_region=self.s3_region,
                s3_endpoint=self.s3_endpoint,
                bucket_name=self.bucket_name,
            )

            s3_handler.upload_file(local_voice_path, remote_file_path)
            return s3_handler.get_file_url(
                remote_file_path=remote_file_path
            )
        except Exception as e:
            self.message = f'上传音频到七牛云发送未知错误，【{e}】'
            return ''

    def upload_file_to_qiniu(self, local_voice_path: str, remote_file_path: str) -> str:
        """
        上传文件到七牛云
        :param local_voice_path: 音频文件路径
        :param remote_file_path:
        :return: 文件访问链接
        """

        try:
            qiniu_handler = QiniuHandler(self.qiniu_access_key, self.qiniu_secret_key)

            qiniu_handler.upload_file(
                bucket_name=self.bucket_name,
                local_file_path=local_voice_path,
                remote_file_path=remote_file_path
            )

            return qiniu_handler.get_file_url(
                bucket_domain=self.bucket_domain,
                remote_file_path=remote_file_path,
                expires=self.expires
            )
        except Exception as e:
            self.message = f'上传音频到七牛云发送未知错误，【{e}】'
            return ''

    def edit_keyword(self, keyword: str, success: bool = True) -> str:

        if not keyword or not self.official_user_id or not self.has_change_db:
            return self.message

        try:
            db_handler = DBHandler(
                db_ip=self.db_ip,
                db_port=self.db_port,
                db_name=self.db_name,
                db_user=self.db_user,
                db_password=self.db_password,
            )

            sql = """
            UPDATE wechat_keywords 
            SET reply_content = %(reply_content)s
            WHERE official_user_id = %(official_user_id)s AND keyword = %(keyword)s;
            """

            content = f'点击即可播放，跳转浏览器即可下载。\n\n<a href="{self.url}">音频链接</a>'

            if self.text_tip:
                content = content + f'\n\n【温馨提示】\n{self.text_tip}'

            if not success:
                content = '配音失败，请重新提交配音任务！'

            params = {
                'official_user_id': self.official_user_id,
                'keyword': keyword,
                'reply_content': content
            }

            db_handler.execute_single_sql(sql=sql, params=params)

            return self.message
        except Exception as e:
            return f'进行数据库操作出现未知错误，错误为：【{e}】'

    def run(self, event: Dict) -> bool:

        try:
            self.event = event

            if not self.check_request():
                return False

            voice_path = self.handle_tts()

            if not voice_path:
                self.message = '语音生成失败'
                return False

            self.url = self.upload_file(voice_path)

            if not self.url:
                return False

            self.code = 0
            self.message = '语音生成成功'
            return True
        except Exception as e:
            print(traceback.format_exc())
            self.message = f'云函数出现未知错误，【{e}】'
            return False


def main_handler(event, context=None) -> str:
    """ 基于代码部署时，使用这个入口 """

    handler = Handler()

    result = handler.run(event)

    # 根据处理情况，修改数据库中对应的关键词回复
    handler.message = handler.edit_keyword(keyword=handler.file_name, success=result)

    return handler.result


@app.route('/tts', methods=['post'])
def run():
    result = main_handler({
        'body': request.data.decode('utf-8'),
        'httpMethod': request.method,
    })

    return result


if __name__ == '__main__':
    TZ = os.getenv('TZ')

    if TZ:
        app.run(host='0.0.0.0', port=9000)
    else:
        app.run(host='127.0.0.1', port=9000)
