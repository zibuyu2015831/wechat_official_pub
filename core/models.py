# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/11/21
contact: 【公众号】思维兵工厂
description: 数据库连接
--------------------------------------------
"""

import os
from typing import Tuple
from datetime import date, timedelta, datetime

from .constant import drive_info
from .config import pro_logger, project_dir, config

from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from sqlalchemy import create_engine, Column, Integer, String, text, inspect, Date, Time, TEXT, DateTime, func

BaseModel = declarative_base()


class WechatUser(BaseModel):
    """
    用户表
    """

    __tablename__ = 'wechat_user'

    id = Column(Integer, primary_key=True)

    official_user_id = Column(String(100), unique=True, comment='公众号用户ID', default=None)
    unique_user_id = Column(String(100), unique=True, comment='唯一用户ID，用于将多个平台的用户整合到一起', default=None)

    corp_user_id = Column(String(100), comment='该用户在企业微信里的ID', default=None)
    corp_id = Column(String(100), comment='企业微信ID，唯一表示企业微信', default=None)

    user_from = Column(String(100), comment='标记用户来源：企业微信|公众号|网页', default=None)

    username = Column(String(100), unique=True, comment='用户昵称', default=None)
    password = Column(String(500), comment='用户密码', default=None)
    is_web_active = Column(Integer, comment='是否已经注册网页端，0：未激活，1：已激活', default=0)

    email = Column(String(50), unique=True, comment='用户邮箱', default=None)
    phone = Column(String(20), unique=True, comment='用户手机', default=None)

    credit = Column(Integer, comment='用户积分', default=50)
    has_cancel_subscribed = Column(Integer, comment='是否取消过关注，0：取消过，1：未取消过', default=0)

    is_master = Column(Integer, comment='是否是管理员，0：不是，1：是', default=0)
    is_vip = Column(Integer, comment='是否是会员，0：不是，1：是', default=0)
    vip_expired_time = Column(Integer, comment='会员过期时间，-1表示永久', default=0)

    is_delete = Column(Integer, comment='是否删除，0：未删除，1：已删除', default=0)
    has_encrypt = Column(Integer, comment='是否已经加密过，0：未加密，1：已加密', default=0)

    note_url = Column(String(200), comment='用户笔记上传URL', default=None)
    note_token = Column(String(100), comment='用户笔记上传token', default=None)
    note_path = Column(String(100), comment='用户笔记上传路径', default=None)

    def to_dict(self):
        return {
            "id": self.id,
            "unique_user_id": self.unique_user_id,
            "official_user_id": self.official_user_id,
            "corp_user_id": self.corp_user_id,
            "corp_id": self.corp_id,
            "user_from": self.user_from,
            "username": self.username,
            "password": self.password,
            "is_web_active": self.is_web_active,
            "email": self.email,
            "phone": self.phone,
            "credit": self.credit,
            "has_cancel_subscribed": self.has_cancel_subscribed,
            "is_master": self.is_master,
            "is_vip": self.is_vip,
            "vip_expired_time": self.vip_expired_time,
            "is_delete": self.is_delete,
            "has_encrypt": self.has_encrypt,
            "note_url": self.note_url,
            "note_token": self.note_token,
        }


class UserCredit(BaseModel):
    """用户积分消耗表"""
    __tablename__ = 'wechat_credit'

    id = Column(Integer, primary_key=True, autoincrement=True)

    official_user_id = Column(String(100), comment='公众号用户ID', default=None)
    unique_user_id = Column(String(100), comment='唯一用户ID，用于将多个平台的用户整合到一起', default=None)

    is_add = Column(Integer, comment='是否是加积分，0：减积分，1：加积分', default=1)
    this_credit = Column(Integer, comment='本次积分变化数', default=0)
    total_credit = Column(Integer, comment='当前总积分', default=0)
    reason = Column(String(100), comment='积分消耗原因', nullable=True)

    change_date = Column(Date, default=date.today, nullable=False, comment='添加日期：年月日')
    change_time = Column(Time, default=lambda: datetime.now().time(), nullable=False, comment='添加时间：时分秒')

    @classmethod
    def update_user_credit(
            cls,
            session: scoped_session,
            credit_num: int,
            reason: str,
            is_add: bool = True,
            wechat_user: "WechatUser" = None,
            official_user_id: str = None,
            unique_user_id: str = None,
    ) -> Tuple[bool, int, str]:
        """
        更新用户积分
        :param session: 数据库会话
        :param credit_num: 积分变化数
        :param reason: 积分消耗原因
        :param is_add: 是否是加积分，0：减积分，1：加积分
        :param wechat_user: 用户对象
        :param official_user_id: 公众号用户ID
        :param unique_user_id: 唯一用户ID，用于将多个平台的用户整合到一起
        :return: 是否更新成功、当前总积分、提示信息
        """

        if not wechat_user:
            if official_user_id:
                wechat_user = session.query(WechatUser).filter(WechatUser.official_user_id == official_user_id).first()
            else:
                wechat_user = session.query(WechatUser).filter(WechatUser.unique_user_id == unique_user_id).first()

        msg = '积分更新失败'
        if not wechat_user:
            msg = '积分更新失败，未找到用户'
            pro_logger.error(f"{msg}；official_user_id:【{official_user_id}】, unique_user_id:【{unique_user_id}】")
            return False, 0, msg

        try:
            is_add = 1 if is_add else 0
            credit_obj = cls(
                unique_user_id=wechat_user.unique_user_id,
                official_user_id=wechat_user.official_user_id,
                is_add=is_add,
                reason=reason,
                this_credit=credit_num,
                total_credit=wechat_user.credit + credit_num,
            )

            session.add(credit_obj)
            wechat_user.credit += credit_num
            session.commit()

            msg = f"""成功更新用户【{wechat_user.username or official_user_id or unique_user_id}】的积分，
原因：【{reason}】
{'增加' if is_add else '减少'} {credit_num} 积分；
当前用户总积分：{wechat_user.credit}"""

            pro_logger.info(msg)
            return True, wechat_user.credit, '更新成功'
        except:
            msg = f"积分更新失败，数据库操作失败"
            pro_logger.error(f"积分更新失败，数据库操作失败", exc_info=True)
            session.rollback()
            return False, wechat_user.credit, msg


class UserSignIn(BaseModel):
    """用户签到表"""
    __tablename__ = 'wechat_sign_in'

    id = Column(Integer, primary_key=True, autoincrement=True)
    official_user_id = Column(String(100), comment='公众号用户ID', default=None)
    unique_user_id = Column(String(100), comment='唯一用户ID，用于将多个平台的用户整合到一起', default=None)

    sign_in_date = Column(Date, default=date.today, nullable=False)
    sign_in_time = Column(Time, default=lambda: datetime.now().time(), nullable=False)
    consecutive_days = Column(Integer, default=1, nullable=False)

    @classmethod
    def update_consecutive_days(
            cls,
            session: scoped_session,
            official_user_id: str,
            wechat_user: "WechatUser"
    ) -> tuple["UserSignIn", int]:
        """
        更新用户连续签到天数，并返回本次签到的积分实例和积分数量
        :param session:
        :param official_user_id:
        :param wechat_user:
        :return:
        """

        today = date.today()

        # 获取该用户昨天的签到记录
        yesterday_sign_in = session.query(UserSignIn).filter(
            UserSignIn.official_user_id == official_user_id
        ).order_by(UserSignIn.sign_in_date.desc()).first()

        if yesterday_sign_in and yesterday_sign_in.sign_in_date == today - timedelta(days=1):
            # 如果昨天有签到记录，则今天的连续签到天数加1
            consecutive_days = yesterday_sign_in.consecutive_days + 1
        else:
            # 否则，连续签到天数重新从1开始计数
            consecutive_days = 1

        # 从配置信息中获取一次签到的最小积分和最大积分
        min_credit = config.min_credit or 2
        max_credit = config.max_credit or 10

        credit_count = int(max_credit / min_credit)

        # 本次签到获得的积分
        credit_num = consecutive_days * min_credit if consecutive_days < credit_count else max_credit

        # 将签到积分添加到用户积分中
        wechat_user.credit += credit_num
        try:
            # 创建新的签到记录并设置连续签到天数
            new_sign_in = UserSignIn(
                official_user_id=official_user_id,
                sign_in_date=today,
                consecutive_days=consecutive_days
            )

            credit_change = UserCredit(
                official_user_id=wechat_user.official_user_id,
                unique_user_id=wechat_user.unique_user_id,
                is_add=1,
                reason="签到",
                this_credit=credit_num,
                total_credit=wechat_user.credit
            )

            session.add(credit_change)
            session.add(new_sign_in)
            session.commit()
            pro_logger.info(f"""【{wechat_user.username or wechat_user.official_user_id}】成功签到;
连续签到天数：{consecutive_days}；本次签到积分：{credit_num}；当前用户总积分：{wechat_user.credit}""")
            return new_sign_in, credit_num
        except:
            session.rollback()
            pro_logger.error(f"签到失败，数据库操作失败", exc_info=True)
            return cls(), 0

    def to_dict(self):
        return {
            "id": self.id,
            "official_user_id": self.official_user_id,
            "sign_in_date": self.sign_in_date,
            "sign_in_time": self.sign_in_time,
            "consecutive_days": self.consecutive_days
        }

    def __repr__(self):
        return f"<UserSignIn(user_id={self.user_id}, sign_in_date={self.sign_in_date}, consecutive_days={self.consecutive_days})>"


class WechatMessage(BaseModel):
    """
    消息表
    """

    __tablename__ = 'wechat_message'

    id = Column(Integer, primary_key=True)

    official_user_id = Column(String(100), comment='公众号用户ID', default=None)
    unique_user_id = Column(String(100), comment='唯一用户ID，用于将多个平台的用户整合到一起', default=None)

    user_from = Column(String(100), comment='标记用户来源：企业微信|公众号|网页', nullable=True)

    receive_msg_id = Column(String(100), comment='接收消息的ID', default=None)
    receive_content = Column(String(1000), comment='接收的消息', default=None)
    receive_media_id = Column(String(100), comment='接收消息的媒体ID', default=None)
    receive_time = Column(Integer, comment='接收消息的时间', default=None)

    reply_type = Column(String(100), comment='回复的类型，text|image|voice|video|music|news', default=None)
    reply_content = Column(String(1000), comment='回复的内容', default=None)
    reply_media_id = Column(String(100), comment='回复的媒体ID', default=None)

    has_encrypt = Column(Integer, comment='是否已经加密过，0：未加密，1：已加密', default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "unique_user_id": self.unique_user_id,
            "official_user_id": self.official_user_id,
            "user_from": self.user_from,
            "receive_msg_id": self.receive_msg_id,
            "receive_content": self.receive_content,
            "receive_media_id": self.receive_media_id,
            "receive_time": self.receive_time,
            "reply_type": self.reply_type,
            "reply_content": self.reply_content,
            "reply_media_id": self.reply_media_id,
            "has_encrypt": self.has_encrypt
        }


class KeyWord(BaseModel):
    """
    自动回复关键词表
    """

    __tablename__ = 'wechat_keywords'

    id = Column(Integer, primary_key=True)

    keyword = Column(String(100), comment='关键词', default=None)

    reply_type = Column(String(10), comment='回复的类型，text|image|voice|video|music|news', default=None)
    reply_content = Column(TEXT, comment='回复的文本内容', default=None)
    reply_media_id = Column(String(100), comment='回复的媒体ID', default=None)

    official_user_id = Column(String(100), comment='公众号用户ID；“系统”表示对所有用户有效', default='系统')
    expire_time = Column(Integer, comment='回复的有效期，单位：秒；0表示永久有效', default=0)
    is_encrypt = Column(Integer, comment='回复的内容是否已经加密过，0：未加密，1：已加密', default=0)
    is_delete = Column(Integer, comment='是否删除，0：未删除，1：已删除', default=0)

    other_info = Column(String(300), comment='其他信息', default=None)

    def to_dict(self):
        return {
            "id": self.id,
            "keyword": self.keyword,
            "reply_type": self.reply_type,
            "reply_content": self.reply_content,
            "reply_media_id": self.reply_media_id,
            "official_user_id": self.official_user_id,
            "expire_time": self.expire_time,
            "is_encrypt": self.is_encrypt,
            "is_delete": self.is_delete,
        }


class AuthenticatedCode(BaseModel):
    """
    一次性鉴权码表，用于各种用户操作
    """

    __tablename__ = 'wechat_authenticated_code'

    id = Column(Integer, primary_key=True)
    official_user_id = Column(String(100), comment='公众号用户ID', nullable=False)
    code = Column(String(100), unique=True, comment='一次性鉴权码', nullable=False)

    create_time = Column(Integer, comment='过期时间，单位：秒', default=None)
    expire_time = Column(Integer, comment='过期时间，单位：秒', default=None)
    is_used = Column(Integer, comment='是否已使用，0：未使用，1：已使用', default=0)


class Source(BaseModel):
    __tablename__ = 'wechat_source'

    id = Column(Integer, primary_key=True)

    title = Column(String(800), comment='资源名称', default=None)
    check_title = Column(String(800), comment='资源名称，URL文件夹名称', default=None)

    description = Column(TEXT, comment='资源描述', default=None)

    share_key = Column(String(50), comment='资源ID，根据平台的不同，拼接不同的前缀得到分享链接', default=None)
    share_pwd = Column(String(50), comment='提取码', default=None)

    user = Column(String(100), comment='资源分享者', default=None)
    catalog = Column(String(50), comment='分类', default=None)

    vote_count = Column(Integer, comment='点赞数', default=0)
    check_count = Column(Integer, comment='检测数', default=0)

    created_at = Column(DateTime, comment='创建时间', default=func.now())

    drive_type = Column(
        Integer,
        comment='网盘类型，如阿里云盘1、百度网盘2、夸克网盘3、蓝奏云4、迅雷网盘5、种子链接6、其他网盘7',
        default=1
    )

    @property
    def drive_name(self):
        """获取网盘名称"""

        return drive_info.get(self.drive_type, {}).get('drive_name', '未知')

    @property
    def share_url(self):
        """获取分享链接"""
        prefix = drive_info.get(self.drive_type, {}).get('prefix', '')
        if not prefix:
            return ''

        if not self.share_pwd:
            return f'{prefix}{self.share_key}'
        return f'{prefix}{self.share_key}?pwd={self.share_pwd}'

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "share_key": self.share_key,
            "share_pwd": self.share_pwd,
            "user": self.user,
            "catalog": self.catalog,
            "vote_count": self.vote_count,
            "check_count": self.check_count,
            "created_at": self.created_at,
            "drive_type": self.drive_type,
        }


class DatabaseHandler(object):

    def __init__(
            self,
            sqlite_db_path: str = 'database.db',
            db_type: str = 'postgresql',
            db_user: str = '',
            db_password: str = '',
            db_host: str = '',
            db_port: int = 5432,
            db_name: str = '',
            need_check_database: bool = True
    ):
        """
        数据库连接类，支持sqlite数据库和postgresql数据库。
        默认使用sqlite数据库，如果使用postgresql数据库，请传入对应的参数。

        :param sqlite_db_path: sqlite数据库文件路径
        :param db_type: 数据库类型，默认postgresql
        :param db_user: 数据库用户名
        :param db_password: 数据库密码
        :param db_host: 数据库地址
        :param db_port: 数据库端口，默认为5432
        :param db_name: 数据库名称
        :param need_check_database: 是否需要检查数据库中的表是否已创建，如果为False，则不会检查，直接连接数据库。
        """

        self.database_path = sqlite_db_path

        if self.database_path == 'database.db':
            self.database_path = os.path.join(project_dir, 'database.db')

        if not all([db_user, db_password, db_host, db_port, db_name, db_type]):
            self.engine = create_engine("sqlite:///" + sqlite_db_path)
            config.is_debug and pro_logger.info(f"使用sqlite数据库，数据库文件路径：【{self.database_path}】")
        else:
            if db_type.lower() == 'postgresql':
                conn_str = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            elif db_type.lower() == 'mysql':
                conn_str = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            else:
                raise ValueError('不支持的数据库类型')

            config.is_debug and pro_logger.info(f"使用{db_type}数据库，数据库地址：【{db_host}:{db_port}/{db_name}】")
            self.engine = create_engine(conn_str)

        if need_check_database:
            self.create_db()

        self.session = self.get_session()

    def create_db(self):
        """ 创建数据表。如果表已经存在，则跳过 """

        config.is_debug and pro_logger.info(f"检查数据库中，所有的表是否已经创建成功")

        # 先创建所有表
        BaseModel.metadata.create_all(self.engine)

        db_type = self.engine.url.get_backend_name()
        if not db_type == 'postgresql' or not not db_type == 'mysql':
            return

        # 检查表是否创建成功
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()

        # 添加触发器，用于自动补充 user_from 和 unique_user_id 字段
        if 'wechat_message' in tables and 'wechat_user' in tables:
            trigger_sql = """
CREATE OR REPLACE FUNCTION fill_wechatmessage_fields()
RETURNS TRIGGER AS $$ 
BEGIN
    IF NEW.unique_user_id IS NULL OR NEW.user_from IS NULL THEN
        SELECT unique_user_id, user_from
        INTO NEW.unique_user_id, NEW.user_from
        FROM wechat_user  
        WHERE official_user_id = NEW.official_user_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER before_wechatmessage_insert
BEFORE INSERT ON wechat_message  
FOR EACH ROW
EXECUTE FUNCTION fill_wechatmessage_fields();
"""
            # 检查触发器是否存在
            with self.engine.connect() as connection:
                result = connection.execute(
                    text("SELECT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'before_wechatmessage_insert')"))
                trigger_exists = result.fetchone()[0]
                if not trigger_exists:
                    with self.engine.begin() as connection:
                        connection.execute(text(trigger_sql))
                        config.is_debug and pro_logger.info(f"数据库中，添加触发器【before_wechatmessage_insert】")

        # 添加触发器，用于处理 wechat_keywords 表的唯一性检查
        # if 'wechat_keywords' in tables:

    #             keyword_trigger_sql = """
    # CREATE OR REPLACE FUNCTION handle_keyword_insert()
    # RETURNS TRIGGER AS $$
    # BEGIN
    #     -- 使用一个条件来避免递归插入
    #     -- 判断当前操作是否是 "DELETE"（删除），如果是，则跳过插入
    #     IF TG_OP = 'DELETE' THEN
    #         -- 删除已存在的记录
    #         DELETE FROM wechat_keywords WHERE keyword = OLD.keyword;
    #         RETURN OLD;
    #     END IF;
    #
    #     -- 检查是否已存在相同的 keyword
    #     IF EXISTS (SELECT 1 FROM wechat_keywords WHERE keyword = NEW.keyword) THEN
    #         -- 如果存在，则删除原有的记录
    #         DELETE FROM wechat_keywords WHERE keyword = NEW.keyword;
    #     END IF;
    #
    #     -- 插入新的记录
    #     INSERT INTO wechat_keywords (keyword, reply_type, reply_content, reply_media_id, official_user_id, expire_time, is_encrypt, is_delete)
    #     VALUES (NEW.keyword, NEW.reply_type, NEW.reply_content, NEW.reply_media_id, NEW.official_user_id, NEW.expire_time, NEW.is_encrypt, NEW.is_delete);
    #
    #     -- 返回 NEW 以继续执行插入操作
    #     RETURN NEW;
    # END;
    # $$ LANGUAGE plpgsql;
    #
    # -- 创建触发器
    # CREATE TRIGGER before_keyword_insert
    # BEFORE INSERT ON wechat_keywords
    # FOR EACH ROW
    # EXECUTE FUNCTION handle_keyword_insert();
    # """
    # 检查触发器是否存在
    # with self.engine.connect() as connection:
    #     result = connection.execute(
    #         text("SELECT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'before_keyword_insert')"))
    #     trigger_exists = result.fetchone()[0]
    #
    #     if not trigger_exists:
    #         with self.engine.begin() as connection:
    #             connection.execute(text(keyword_trigger_sql))

    def drop_db(self):
        """ 删除所有表，谨慎操作 """

        confirm = input("确定删除所有表？(确定请输入y) >>>")

        if confirm == "y":
            BaseModel.metadata.drop_all(self.engine)
        else:
            print("操作取消")
            return

    def get_session(self):
        """ 创建一个session，用于操作数据库 """

        session_class = scoped_session(sessionmaker(bind=self.engine))
        session = session_class()

        return session
