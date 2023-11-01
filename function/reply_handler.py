# # -*- coding: utf-8 -*-
# import time
# import xmltodict
# from .post_handler import ReplyHandler
#
#
# def make_reply_text(reply_obj, content):
#     time_stamp = int(time.time())
#
#     resp_dict = {
#         'xml': {
#             'ToUserName': reply_obj.to_user_name,
#             'FromUserName': reply_obj.my_name,
#             'CreateTime': time_stamp,
#             'MsgType': 'text',
#             'Content': content,
#         }
#     }
#     resp_xml = xmltodict.unparse(resp_dict)
#     return resp_xml
#
#
# def make_reply_picture(reply_obj: ReplyHandler, media_id):
#     time_stamp = int(time.time())
#
#     resp_dict = {
#         'xml': {
#             'ToUserName': reply_obj.to_user_name,
#             'FromUserName': reply_obj.my_name,
#             'CreateTime': time_stamp,
#             'MsgType': 'image',
#             'Image': {
#                 'media_id': media_id
#             },
#         }
#     }
#     resp_xml = xmltodict.unparse(resp_dict)
#     return resp_xml
