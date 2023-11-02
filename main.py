# -*- coding: utf-8 -*-
from pathlib import Path  # 不能删，代码内部需要用到此路径
from flask import Flask, request
from function.logger import get_logger
from function.handle_request import handle_get, handle_post

app = Flask(__name__)
logger = get_logger()


@app.route('/', methods=['get', 'post'])
def run():
    request_method = request.method.lower().strip()  # 获取请求方式

    if request_method == 'get':
        return handle_get(request, logger)
    elif request_method == 'post':
        return handle_post(request, logger)
    else:
        return 'hello'


if __name__ == '__main__':

    app.run('127.0.0.1', 8080)


