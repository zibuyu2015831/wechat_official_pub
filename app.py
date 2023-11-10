# -*- coding: utf-8 -*-
from pathlib import Path
from flask import Flask, request
from function.handle_request import RequestHandler

app = Flask(__name__)


@app.route('/', methods=['get', 'post'])
def run():
    request_method = request.method.lower().strip()  # 获取请求方式
    request_handler = RequestHandler()
    if request_method == 'get':
        return request_handler.get(request)
    elif request_method == 'post':
        return request_handler.post(request)
    else:
        return 'not support method!'


if __name__ == '__main__':
    app.run('127.0.0.1', 8080)
