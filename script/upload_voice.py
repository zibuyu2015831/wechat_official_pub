# -*- coding: utf-8 -*-
import json
import os
import time
from pathlib import Path
from function.handle_wechat import WechatHandler


def handler():
    project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_dir_path = os.path.join(project_path, 'config')
    config_file_path = os.path.join(config_dir_path, 'config.json')

    with open(config_file_path, mode='r', encoding='utf8') as read_f:
        config_dict = json.load(read_f)
    wechat_handler = WechatHandler(config_dict.get('wechat'))
    # wechat_handler.clear_quota()
    with open('zh_voice.json', mode='r', encoding='utf8') as read_f:
        voice_data = json.load(read_f)

    results = dict()
    for item in voice_data:
        nickname = item['nickname']
        file_name = item['voice_file_name']
        file_path = os.path.join(project_path, 'script', 'voice', file_name)

        res = wechat_handler.upload_hard_source('voice', file_path)
        media_id = res.get('media_id')
        results[f"试听-{nickname}"] = media_id
        time.sleep(0.5)
        print(res)

    print(results)
    with open('results.json', mode='w', encoding='utf8') as write_f:
        write_f.write(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__':
    handler()
