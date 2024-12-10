# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/11/20
contact: 【公众号】思维兵工厂
description: 项目主入口

对于比较敏感的接口，请求时需要携带 request_token 参数
    - /database_cleanup  数据库过期数据清理；
    - /add_source  向数据库添加资源链接；
    - /add_keywords  向数据库添加系统关键词；
--------------------------------------------
"""

from datetime import datetime
from flask import Flask, request, jsonify
from core.utils.storage import Qiniu
from core.handle_db import DBManager
from core.config import config, pro_logger
from core.handle_request import RequestHandler
from core.models import UserCredit, DatabaseHandler

app = Flask(__name__)


def is_pre_check_failed(
        check_database: bool = True,
        check_qiniu_config: bool = False,
        check_request_token: bool = True,
) -> str:
    """
    根据 request_token参数，判断请求是否合法
    :param check_database: 是否检查数据库配置
    :param check_qiniu_config: 是否检查七牛云配置
    :param check_request_token: 是否检查请求token
    :return: 如果检测不通过，返回检测信息字符串；如果通过，放回空字符串
    """

    failed_msg = ''

    # 1. 检查数据库配置信息
    if check_database and not config.db_config.is_valid():
        new_failed_msg = '配置文件【config.json】中没有数据库连接信息'
        failed_msg = failed_msg + new_failed_msg + '\n\n'
        config.is_debug and pro_logger.error(new_failed_msg)

    # 2. 检查request_token：如果服务端没有设置request_token，则不检查
    request_data = request.args.get('request_token') or request.get_json().get('request_token')
    if not config.request_token or not check_request_token:
        config.is_debug and pro_logger.info('未设置request_token，不进行接口鉴权')
    elif not request_data or request_data != config.request_token:
        new_failed_msg = 'request_token参数校验失败'
        failed_msg = failed_msg + new_failed_msg + '\n\n'
        config.is_debug and pro_logger.error(new_failed_msg)

    # 3. 检查七牛云配置信息
    if check_qiniu_config and not config.qiniu_config.is_valid():
        new_failed_msg = '配置文件【config.json】中没有七牛云连接信息'
        failed_msg = failed_msg + new_failed_msg
        config.is_debug and pro_logger.error(new_failed_msg)

    return failed_msg


@app.route('/update_credit', methods=['post'])
def update_credit():
    # 1. 此接口操作比较敏感，需先判断请求是否合法
    if is_pre_check_failed():
        return is_pre_check_failed()

    # 2. 获取传入的数据
    data = request.get_json()
    if not data:
        return '请求数据为空或格式不正确，必须以json格式传入数据'

    for item in ['credit_num', 'reason', 'is_add']:
        if item not in data:
            return f'请求数据缺少【{item}】参数'

    if 'official_user_id' not in data and 'unique_user_id' not in data:
        return 'official_user_id和unique_user_id参数至少有一个不能为空'

    if data['is_add'] not in [0, 1]:
        return 'is_add参数值不正确，必须是0或1'

    database = DatabaseHandler(
        db_user=config.db_config.db_user,
        db_password=config.db_config.db_password,
        db_host=config.db_config.db_host,
        db_port=config.db_config.db_port,
        db_name=config.db_config.db_name,
    )

    result, total_credit, msg = UserCredit.update_user_credit(
        is_add=data['is_add'],
        credit_num=data['credit_num'],
        reason=data['reason'],
        official_user_id=data.get('official_user_id'),
        unique_user_id=data.get('unique_user_id'),
        session=database.session
    )

    return jsonify({
        'msg': msg,
        'total_credit': total_credit,
        'change_num': f'{"+" if data["is_add"] else "-"}{data["credit_num"]}',
        'reason': data['reason'],
    })


@app.route('/database_backup', methods=['get', 'post'])
def database_backup() -> str:
    """备份数据库"""

    if is_pre_check_failed(check_qiniu_config=True):
        return is_pre_check_failed(check_qiniu_config=True)

    remote_file_name = f"database_backup_{datetime.now().strftime('%Y%m%d')}.zip"
    remote_file_path = f"database_backup/{remote_file_name}"

    qiniu_handle = Qiniu(
        access_key=config.qiniu_config.access_key,
        secret_key=config.qiniu_config.secret_key,
        bucket_name=config.qiniu_config.bucket_name,
    )

    if qiniu_handle.get_file_info(remote_file_path):
        return '今日备份文件已存在，跳过备份'

    db_manager = DBManager()
    zip_file_path = db_manager.database_backup(remote_file_name)

    if not zip_file_path:
        return '数据备份失败，无法生成zip文件'

    result = qiniu_handle.upload_file(
        local_file_path=zip_file_path,
        remote_file_path=remote_file_path
    )

    msg = f'备份失败，文件无法上传到七牛云'
    if result:
        msg = f'备份成功，文件【{remote_file_name}】已上传到七牛云'

    config.is_debug and pro_logger.info(msg)
    return msg


@app.route('/database_cleanup', methods=['get', 'post'])
def database_cleanup() -> str:
    """删除数据库中过期的消息"""

    # 1. 此接口操作比较敏感，需先判断请求是否合法
    if is_pre_check_failed():
        return is_pre_check_failed()

    # 2. 执行数据库操作
    db_manager = DBManager()
    result = db_manager.delete_expired_data()

    msg = '数据库清理失败'
    if result:
        msg = '数据库清理成功'

    # 3. 拟删除，不应该由主程序发送微信消息
    # from core.utils.postman import send_wechat_msg
    # send_wechat_msg(token=config.note_card_wechat_token, msg=msg)

    return msg


@app.route('/add_source', methods=['post'])
def add_source():
    """上传资源到数据库"""

    # 1. 此接口操作比较敏感，需先判断请求是否合法
    if is_pre_check_failed():
        return is_pre_check_failed()

    # 2. 获取传入的数据
    data = request.get_json()
    if not data:
        return '请求数据为空或格式不正确，必须以json格式传入数据'

    # 3. 执行数据库操作
    db_manager = DBManager()

    return db_manager.upload_source(data)


@app.route('/add_keywords', methods=['post'])
def upload_system_keywords():
    # 1. 此接口操作比较敏感，需先判断请求是否合法
    if not is_pre_check_failed():
        return 'request_token参数校验失败；或无数据库配置'

    # 2. 获取传入的数据
    data = request.get_json()
    if not data:
        return '请求数据为空或格式不正确，必须以json格式传入数据'

    # 3. 执行数据库操作
    db_manager = DBManager()
    return db_manager.upload_system_keyword(data)


@app.route('/wechat', methods=['get', 'post'])
def handle_wechat_request():
    # 获取请求方式
    request_method = request.method.lower().strip()

    request_handler = RequestHandler()

    # 传入配置信息
    request_handler.config = config

    if request_method == 'get':
        result = request_handler.get(request)
    elif request_method == 'post':
        result = request_handler.post(request)
    else:
        result = 'not support method!'

    return result


if __name__ == '__main__':

    if config.is_yun_function:
        app.run(host='0.0.0.0', port=9000)
    else:
        app.run(host='127.0.0.1', port=9000)
