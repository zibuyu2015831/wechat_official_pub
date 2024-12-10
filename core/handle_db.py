# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/12/5
contact: 【公众号】思维兵工厂
description: 数据库操作：删除过期数据、批量添加系统关键词、批量添加资源链接等；

eg：设置云函数的时候，可以设置一个定期任务，给数据库瘦身；

upload_source 方法接收post请求，传入的数据类型：
[
    {
        "key": "必须",
        "title": "必须",
        "platform": "必须",
        "description": "非必须",
        "user": "非必须",
        "source_title": "非必须",
    },
]

upload_system_keyword 方法接收post请求，传入的数据类型：
[
    {
        "keyword": "必须",
        "content": "必须",
    },
]
--------------------------------------------
"""

import os
import time
import zipfile
from typing import Dict, List

from sqlalchemy.schema import CreateTable
from sqlalchemy.exc import SQLAlchemyError

from core.constant import file_save_dir_path
from core.config import config, pro_logger, project_dir
from .models import DatabaseHandler, BaseModel, Source, KeyWord, AuthenticatedCode, WechatMessage


class DBManager(object):
    def __init__(self):
        self.database = DatabaseHandler(
            db_type=config.db_config.db_type,
            db_user=config.db_config.db_user,
            db_password=config.db_config.db_password,
            db_host=config.db_config.db_host,
            db_port=config.db_config.db_port,
            db_name=config.db_config.db_name,
            need_check_database=True
        )

    def upload_source(self, data: List[Dict]) -> str:
        """
        向数据库上传资源链接
        :param data:
        :return: str：上传操作信息
        """

        if not isinstance(data, list):
            return '数据格式不正确，传入的数据必须是一个列表！'

        for item in data:
            if not isinstance(item, dict):
                return '数据格式不正确，传入的数据元素必须是一个字典！'

            if 'key' not in item or 'title' not in item or 'platform' not in item:
                return '数据格式不正确，传入的元素必须是字典，且字典里必须包含key、title和url字段！'

        try:
            for item in data:
                obj = Source(
                    key=item.get('key'),
                    title=item.get('title'),
                    source_title=item.get('source_title'),
                    description=item.get('description'),
                    platform=item.get('platform'),
                    user=item.get('user')
                )
                self.database.session.add(obj)
            self.database.session.commit()
            return 'success'
        except SQLAlchemyError:
            pro_logger.error(f"添加资源链接操作失败", exc_info=True)
            self.database.session.rollback()
            return '数据库操作出现未知错误，数据已经回滚！'

    def upload_system_keyword(self, data: List[Dict]) -> str:
        """
        向数据库上传系统关键字
        :param data:
        :return: str：上传操作信息
        """

        if not isinstance(data, list):
            return '数据格式不正确，传入的数据必须是一个列表！'

        for item in data:

            if not isinstance(item, dict):
                return '数据格式不正确，传入的数据元素必须是一个字典！'

            if 'keyword' not in item or 'content' not in item:
                return '数据格式不正确，传入的元素必须是字典，且字典里必须包含keyword和content字段！'

        try:
            for item in data:
                obj = KeyWord(
                    keyword=item['keyword'],
                    reply_content=item['content'],
                    reply_type='text',
                    official_user_id='系统',
                    is_delete=0,
                    is_encrypt=0,
                    expire_time=0
                )
                self.database.session.add(obj)

            self.database.session.commit()
            return 'success'
        except SQLAlchemyError:
            pro_logger.error(f"添加关键词操作失败", exc_info=True)
            self.database.session.rollback()
            return '数据库操作出现未知错误，数据已经回滚！'

    def __delete_expired_data(self, data_model: BaseModel, model_name: str, crt_timestamp: int = None) -> bool:
        """
        删除过期数据
        :param data_model: 数据库模型
        :param model_name: 数据库模型名称
        :param crt_timestamp: 当前时间戳，默认为当前时间
        :return: bool：True表示删除成功，False表示删除失败
        """

        if not crt_timestamp:
            crt_timestamp = int(time.time())

        try:
            config.is_debug and pro_logger.info(f"开始删除{model_name}中的过期数据")

            if hasattr(data_model, 'expire_time'):
                expired_keywords = self.database.session.query(data_model).filter(
                    data_model.expire_time != 0,
                    data_model.expire_time < crt_timestamp
                ).all()
            else:
                expired_keywords = self.database.session.query(data_model).filter(
                    data_model.receive_time < crt_timestamp
                ).all()

            for keyword in expired_keywords:
                self.database.session.delete(keyword)

            self.database.session.commit()
            config.is_debug and pro_logger.info(f"{model_name}中的过期数据删除成功，共删除{len(expired_keywords)}条数据")
            return True
        except:
            config.is_debug and pro_logger.error(f"{model_name}中的过期数据删除失败", exc_info=True)
            self.database.session.rollback()
            return False

    def delete_expired_data(self) -> bool:
        """
        删除KeyWord、AuthenticatedCode、WechatMessage表中的过期数据
        :return: str：数据库清理完成
        """

        current_timestamp = int(time.time())
        special_timestamp = current_timestamp - 60 * 60 * 24 * 10

        if all([
            self.__delete_expired_data(
                data_model=KeyWord,
                model_name='数据表【关键词】',
                crt_timestamp=current_timestamp
            ),

            self.__delete_expired_data(
                data_model=AuthenticatedCode,
                model_name='数据表【授权码】',
                crt_timestamp=current_timestamp
            ),

            self.__delete_expired_data(
                data_model=WechatMessage,
                model_name='数据表【微信消息】',
                crt_timestamp=special_timestamp
            )
        ]):
            return True
        else:
            return False

    @staticmethod
    def export_table_to_sql(table_class, session, file_path):
        """
        将数据库中的数据导出到SQL文件
        :param table_class: 数据库表对应的类
        :param session: 数据库连接对象
        :param file_path: 导出SQL文件的路径
        :return: None
        """

        # 创建表的SQL语句
        # 使用inspect来获取创建表的SQL语句
        # inspector = inspect(session.bind)
        create_table_stmt = CreateTable(table_class.__table__).compile(dialect=session.bind.dialect)
        create_table_sql = str(create_table_stmt)

        # 查询表中的数据
        records = session.query(table_class).all()

        # 构建插入数据的SQL语句
        insert_sql = []
        for record in records:
            columns = ', '.join([column.name for column in table_class.__table__.columns])
            values = ', '.join(["'" + str(getattr(record, column.name)).replace("'", "''") + "'" if isinstance(
                getattr(record, column.name), str)
                                else str(getattr(record, column.name))
                                for column in table_class.__table__.columns])
            insert_statement = f"INSERT INTO {table_class.__tablename__} ({columns}) VALUES ({values});"
            insert_sql.append(insert_statement)

            # 将DDL和DML写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(create_table_sql + ';\n')
            for stmt in insert_sql:
                f.write(stmt + ';\n')

    @staticmethod
    def pack_files_to_zip(file_paths: List[str], zip_file_path: str) -> bool:
        """
        将多个文件打包成一个zip文件。

        :param file_paths: 包含文件路径的列表
        :param zip_file_path: 输出zip文件的路径
        """

        try:
            # 确保zip文件路径的目录存在
            os.makedirs(os.path.dirname(zip_file_path), exist_ok=True)

            # 创建ZipFile对象，并设置模式为写入
            with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in file_paths:
                    # 确保文件存在
                    if not os.path.isfile(file_path):
                        config.is_debug and pro_logger.error(f"文件 {file_path} 不存在，跳过。")
                        continue

                    # 将文件添加到zip文件中
                    # arcname参数是zip文件中文件的名称，如果不设置，则默认为文件的完整路径
                    zipf.write(file_path, os.path.basename(file_path))
                    config.is_debug and pro_logger.info(f"文件 {file_path} 添加到zip文件中。")
            config.is_debug and pro_logger.info(f"文件打包完成，保存路径为：【{zip_file_path}】")
            return True
        except:
            config.is_debug and pro_logger.error(f"打包文件失败", exc_info=True)
            return False

    def database_backup(self, remote_file_name: str) -> str:
        """
        备份数据库
        :return: list, 备份文件路径列表
        """

        save_path = file_save_dir_path if config.is_yun_function else os.path.join(project_dir, 'database_backup')
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        file_path_list = []

        for table_class in BaseModel.__subclasses__():
            if not table_class.__tablename__:  # 确保表名已定义
                config.is_debug and pro_logger.error(f"表{table_class.__name__}没有定义表名，无法备份")
                continue

            try:
                file_path = os.path.join(save_path, f"{table_class.__tablename__}.sql")
                self.export_table_to_sql(table_class, self.database.session, file_path)

                file_path_list.append(file_path)
                config.is_debug and pro_logger.info(f"备份表{table_class.__tablename__}成功")
            except:
                config.is_debug and pro_logger.error(f"备份表{table_class.__tablename__}失败", exc_info=True)

        if not file_path_list:
            return ''

        zip_file_path = os.path.join(save_path, remote_file_name)
        result = self.pack_files_to_zip(file_path_list, zip_file_path)

        return zip_file_path if result else ''
