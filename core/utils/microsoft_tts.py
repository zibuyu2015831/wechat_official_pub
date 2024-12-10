# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/11/25
contact: 【公众号】思维兵工厂
description: 
--------------------------------------------
"""

import json


def main_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))
    print("Received context: " + str(context))
    print("Hello world")
    return ("Received context: " + str(context) + '\n\n' + "Received event: " + json.dumps(event, indent=2))
