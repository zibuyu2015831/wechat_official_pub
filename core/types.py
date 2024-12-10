# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_dev
author: 子不语
date: 2024/11/20
contact: 【公众号】思维兵工厂
description: 数据容器类
--------------------------------------------
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional, Callable, Literal, List, Union


@dataclass
class YunFuncTTSConfig:
    """文本转语音，云函数配置"""

    func_token: str = ''  # 云函数鉴权token（云函数部署时有环境变量传入）
    func_url: str = ''  # 云函数url
    default_en_voice: str = "zh-CN-XiaoxiaoNeural"  # 默认中文配音音色
    default_zh_voice: str = "en-GB-SoniaNeural"  # 默认英文配音音色
    expires: Union[int, str] = 3600  # 音频链接有效期（七牛云）

    def is_valid(self) -> bool:
        return all([self.func_token, self.func_url])

    def __post_init__(self):
        try:
            self.expires = int(self.expires)
        except (ValueError, TypeError):
            self.expires = 3600


@dataclass
class QiNiuConfig:
    access_key: str = ''  # 七牛云access_key
    secret_key: str = ''  # 七牛云secret_key
    bucket_name: str = ''  # 七牛云对象存储空间名称
    bucket_domain: str = ''  # 七牛云空间域名

    def is_valid(self) -> bool:
        return all([self.access_key, self.secret_key, self.bucket_name, self.bucket_domain])


@dataclass
class AiConfig:
    """
    Ai配置，用于请求地址、模型名称、API_key等
    """

    model_name: str = ''
    key_list: Optional[List[str]] = None
    base_url: str = 'https://api.siliconflow.cn/v1'
    system_prompt: str = "You are a useful assistant. But if you don't know, you can just say that you don't know."

    def is_valid(self) -> bool:
        return all([self.key_list, self.base_url, self.model_name])


@dataclass
class DBConfig:
    db_type: str = 'postgresql'  # 数据库类型，默认postgresql
    db_host: str = ''  # 数据库连接ID
    db_port: int = 5433  # 数据库端口
    db_user: str = ''  # 数据库用户
    db_password: str = ''  # 数据库密码
    db_name: str = ''  # 数据库数据库名称

    def is_valid(self) -> bool:
        return all([self.db_host, self.db_port, self.db_user, self.db_password, self.db_name])


@dataclass
class WechatConfig:
    """微信公众号配置"""

    manager: str = ''  # 管理员的账号昵称
    app_id: str = ''  # 公众号appID
    app_name: str = ''  # 公众号名称
    app_secret: str = ''  # 公众号appSecret
    wechat_token: str = ''  # 公众号Token
    sep_char: str = "---"  # 短指令的分隔符号
    subscribe_greeting: str = "欢迎你的到来，这是一个有趣的公众号哦~"  # 用户关注公众号时，回复的文本

    def is_valid(self) -> bool:
        return all([self.app_id, self.app_secret, self.wechat_token, self.app_name])


@dataclass
class BaiDuConfig:
    """百度OCR鉴权配置"""
    api_key: str = ''
    secret_key: str = ''

    def is_valid(self) -> bool:
        return all([self.api_key, self.secret_key])


@dataclass
class ConfigData:
    """配置信息类"""

    baidu_config: BaiDuConfig = BaiDuConfig()
    yun_func_tts_config: YunFuncTTSConfig = YunFuncTTSConfig()
    qiniu_config: QiNiuConfig = QiNiuConfig()
    ai_config: AiConfig = AiConfig()
    db_config: DBConfig = DBConfig()
    wechat_config: WechatConfig = WechatConfig()

    sign_in_word: str = "签到"  # 签到口令
    request_token: str = ""  # 接口请求令牌，有些接口操作比较重要，需要进行鉴权，请求时由query参数或请求体参数传入
    min_credit: int = 2  # 一次签到获得最少积分
    max_credit: int = 10  # 一次签到获得最多积分；连续签到有奖励，但总分数不超过这个值
    encrypt_key: bytes = ''  # 用于文本加密解密的默认key，计划废除，改为使用微信用户ID作为加密密钥
    caiyun_token: str = ''  # 彩云天气密钥
    note_card_wechat_token: str = ''  # 笔记卡片的token，用于发送微信消息
    weather_show_hours: int = 6  # 发送天气预报的小时数
    history_message_limit: int = 5  # 历史消息显示条数
    command_expire_time: int = 60 * 30  # 指令过期时间，单位为秒；默认30分钟；

    per_page_count: int = 5  # 每页显示的条数
    need_check_database: bool = True  # 是否检查数据库中所有的表是否已经创建；确保数据库的表已全部创建后可以关闭，减少一次查询，提升速度
    is_yun_function: bool = False  # 是否使用云函数部署项目，如果是，则关闭日志的文件记录
    is_debug: bool = True  # 是否开启debug模式
    logger_config: dict = None  # 日志配置
    command_another_count: int = 2  # 指令别名显示数
    retry_time: int = 1  # 当消息已经在处理时，获取处理结果的时间间隔，单位为秒


@dataclass
class WechatReplyData:
    """微信回复数据类"""
    msg_type: Literal["text", "image", "voice", "video", "shortvideo", "location", "link", "event", "news"] = 'text'
    content: str = ""
    media_id: str = ""


@dataclass
class WechatRequestData:
    """微信请求数据类"""

    xml_dict: dict

    # 基础字段
    my_user_id: Optional[str] = field(default=None, init=False)
    """获取消息的接收者，为本次回复的发送者"""
    to_user_id: Optional[str] = field(default=None, init=False)
    """获取消息的发送者，为本次回复的接收者"""
    create_time: Optional[str] = field(default=None, init=False)
    """获取本次消息的消息创建时间 （整型）（时间戳）"""
    msg_id: Optional[str] = field(default=None, init=False)
    """消息id，64位整型"""
    msg_type: Optional[str] = field(default=None, init=False)
    """获取本次消息的MsgType"""
    msg_data_id: Optional[str] = field(default=None, init=False)
    """消息的数据ID（消息如果来自文章时才有）"""
    idx: Optional[str] = field(default=None, init=False)
    """多图文时第几篇文章，从1开始（消息如果来自文章时才有）"""

    # 特殊字段
    content: Optional[str] = field(default=None, init=False)
    """MsgType为text时包含此字段：本次消息的文本内容"""
    pic_url: Optional[str] = field(default=None, init=False)
    """MsgType为image时包含此字段：图片链接（由系统生成），该链接保存3天"""
    format: Optional[str] = field(default=None, init=False)
    """MsgType为voice时包含此字段：语音消息的语音格式，如amr，speex等"""
    media_id: Optional[str] = field(default=None, init=False)
    """MsgType为image、voice、video、shortvideo时包含此字段：可以调用获取临时素材接口拉取数据。"""
    thumb_media_id: Optional[str] = field(default=None, init=False)
    """MsgType为video、shortvideo时包含此字段：视频消息缩略图的媒体id。"""

    # 链接消息特有字段
    title: Optional[str] = field(default=None, init=False)
    """MsgType为link时包含此字段：消息标题"""
    description: Optional[str] = field(default=None, init=False)
    """MsgType为link时包含此字段：消息描述"""
    url: Optional[str] = field(default=None, init=False)
    """MsgType为link时包含此字段：消息链接"""

    # 地理位置信息（location）特有字段
    location_x: Optional[str] = field(default=None, init=False)
    """MsgType为location时包含此字段：地理位置纬度"""
    location_y: Optional[str] = field(default=None, init=False)
    """MsgType为location时包含此字段：地理位置经度"""
    scale: Optional[str] = field(default=None, init=False)
    """MsgType为location时包含此字段：地图缩放大小"""
    label: Optional[str] = field(default=None, init=False)
    """MsgType为location时包含此字段：地理位置信息"""

    # 事件类型
    event_type: Optional[str] = field(default=None, init=False)
    """获取事件类型，如关注：subscribe；取消关注：unsubscribe等"""
    event_key: Optional[str] = field(default=None, init=False)
    """事件的EventKey"""

    def __post_init__(self):
        # 基础字段
        self.my_user_id = self.xml_dict.get('ToUserName')
        self.to_user_id = self.xml_dict.get('FromUserName')
        self.create_time = self.xml_dict.get('CreateTime')
        self.msg_id = self.xml_dict.get('MsgId')
        self.msg_type = self.xml_dict.get('MsgType')
        self.msg_data_id = self.xml_dict.get('MsgDataId')
        self.idx = self.xml_dict.get('Idx')

        # 特殊字段
        self.content = self.xml_dict.get('Content', '').strip()
        self.pic_url = self.xml_dict.get('PicUrl')
        self.format = self.xml_dict.get('Format')
        self.media_id = self.xml_dict.get('MediaId')
        self.thumb_media_id = self.xml_dict.get('ThumbMediaId')

        # 链接消息特有字段
        self.title = self.xml_dict.get('Title')
        self.description = self.xml_dict.get('Description')
        self.url = self.xml_dict.get('Url')

        # 地理位置信息（location）特有字段
        self.location_x = self.xml_dict.get('Location_X')
        self.location_y = self.xml_dict.get('Location_Y')
        self.scale = self.xml_dict.get('Scale')
        self.label = self.xml_dict.get('Label')

        # 事件类型
        self.event_type = self.xml_dict.get('Event')
        self.event_key = self.xml_dict.get('EventKey')


@dataclass
class WechatReactMessage:
    """存储一条微信交互消息"""

    receive_content: str  # 用户发送的消息
    reply_content: str  # 回复用户的消息


@dataclass
class FunctionInfo:
    """用来对某个类的方法的介绍"""

    function: Callable  # 存储该方法
    function_name: str  # 该方法的名称
    order: int = 0  # 该方法的排序（展示时使用）
    is_first: bool = False  # 该方法是否能直接调用；在微信相关里表现为无需参数
    is_master: bool = False  # 该方法是否仅为管理员可调用
    is_show: bool = True  # 该功能是否向用户展示
    function_intro: str = ''  # 该方法的介绍信息
    random_id: str = uuid.uuid4().hex  # 随机ID值，用于唯一标识，无意义


@dataclass
class Command:
    """存储指令信息"""
    order: int = 0
    title: str = ''
    sub_title: str = ''
    intro: str = ''


@dataclass
class SinglePageData:
    """单页数据内容"""

    title: str
    current_page: int
    total_page: int
    data: List


@dataclass
class SourceFile:
    """数据类：资源信息"""

    drive_name: str = ''  # 网盘类型名称
    title: str = ''  # 资源名称
    check_title: str = ''  # 检查过的资源标题

    share_key: str = ''  # 资源key
    share_pwd: str = ''  # 资源提取码
    share_url: str = ''  # 资源链接（包含提取码）

    description: str = ''  # 资源描述
