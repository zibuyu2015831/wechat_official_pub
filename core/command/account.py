# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: mind_workshop
author: 子不语
date: 2024/4/24
contact: 【公众号】思维兵工厂
description: 【关键词回复功能】与账号相关功能
--------------------------------------------
"""

import time
import uuid
from typing import TYPE_CHECKING

from ..config import config
from ..constant import cancel_command_list
from ..models import AuthenticatedCode, WechatUser, KeyWord, UserCredit
from ..types import WechatReplyData, Command, SinglePageData
from .base import WeChatKeyword, register_function

if TYPE_CHECKING:
    from ..handle_post import BasePostHandler

FUNCTION_DICT = dict()
FIRST_FUNCTION_DICT = dict()


class KeywordFunction(WeChatKeyword):
    model_name = "account"

    @staticmethod
    def make_authenticated_code() -> str:
        """
        生成一次性的用户授权码，该授权码可用于重置密码等操作。

        :return:str
        """

        crt_authenticated_code = uuid.uuid4().hex

        return crt_authenticated_code

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['授权码', '获取授权码', '一次性授权码'], is_first=True,
                       function_intro='获取一次性授权码，用于重置密码等操作')
    def get_authenticated_code(self, *args, **kwargs) -> WechatReplyData:
        """获取一次性授权码，用于重置密码等操作"""

        post_handler: BasePostHandler = kwargs.get('post_handler')

        auth_code = self.make_authenticated_code()

        current_timestamp = int(int(time.time()))

        auth_code_obj = AuthenticatedCode(
            code=auth_code,
            official_user_id=post_handler.request_data.to_user_id,
            expire_time=current_timestamp + 60 * 5,
            create_time=current_timestamp
        )

        post_handler.database.session.add(auth_code_obj)
        post_handler.database.session.commit()

        msg = (f'您的一次性授权码是：\n\n'
               f'{auth_code}\n\n'
               f'👇使用事项👇\n\n'
               f'该授权码对账户具有最高操作权限，可用于重置密码等；5分钟内有效，一次性使用，请勿外泄！')

        return WechatReplyData(msg_type="text", content=msg)

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['邀请码', '获取邀请码', '专属码', '获取专属码'], is_first=True,
                       function_intro='获取用户个人专属码，用于激活web端或企业微信，或积分交易')
    def get_invite_code(self, *args, **kwargs) -> WechatReplyData:
        """获取该用户的邀请码，用于激活web端或企业微信"""

        post_handler: BasePostHandler = kwargs.get('post_handler')

        # 原来的消息里包含敏感信息（用户唯一ID），这里重设
        post_handler.message_object.receive_content = '获取激活码'

        msg = (f'您的专属码是：\n\n'
               f'{post_handler.wechat_user.unique_user_id}\n\n'
               f'👇使用事项👇\n\n'
               f'该专属码只属于您，可用于激活账户或积分交易，一人一码，请勿外泄！')

        return WechatReplyData(msg_type="text", content=msg)

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['用户名', '我的用户名', '用户名称', '获取用户名'], is_first=True,
                       function_intro='获取您的用户名称，用于登录wen端')
    def get_username(self, *args, **kwargs) -> WechatReplyData:
        """获取用户名"""

        post_handler: BasePostHandler = kwargs.get('post_handler')
        if post_handler.wechat_user.username:
            msg = f'您的用户名是：【{post_handler.wechat_user.username}】'
        else:
            msg = '您尚未设置用户名，请先在网页端注册~'

        return WechatReplyData(msg_type="text", content=msg)

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['设置管理员', '管理员', '设置超级用户', '超级用户'], is_first=False, is_show=False,
                       function_intro='设置此公众号管理员')
    def set_super_user(self, content: str, *args, **kwargs) -> WechatReplyData:
        """设置超级用户"""

        post_handler: BasePostHandler = kwargs.get('post_handler')

        # 原来的消息里包含敏感信息（token），这里重设
        post_handler.message_object.receive_content = '设置管理员'

        obj = WechatReplyData(msg_type="text", content=f"---管理员设置失败---")

        try:

            if content.strip() != config.wechat_config.wechat_token:
                obj.content = f"---管理员设置失败---\n\n无效的token"
                return obj

            post_handler.wechat_user.is_master = 1
            obj.content = f"---管理员设置成功---\n\n您已成为本公众号的管理员"

            if config.wechat_config.manager:
                post_handler.wechat_user.username = config.wechat_config.manager.strip()
                obj.content = obj.content + f'，同时，根据配置文件，您的昵称已设置为【{config.wechat_config.manager.strip()}】'

            post_handler.database.session.commit()

            config.is_debug and self.logger.info(
                f'已将用户【{post_handler.request_data.to_user_id}】设置为公众号管理员'
            )

        except Exception:
            obj.content = f"---管理员设置失败：未知错误---"
            self.logger.error('set_super_user方法出现错误', exc_info=True)
        finally:
            return obj

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['设置用户名', '设置用户名称'], is_first=False,
                       function_intro='设置您的web端登录用户名')
    def set_username(self, content: str, *args, **kwargs) -> WechatReplyData:
        """昵称---用户输入的昵称：用户主动设置自身昵称"""

        post_handler: BasePostHandler = kwargs.get('post_handler')

        obj = WechatReplyData(msg_type="text", content=f"---昵称重设失败---")

        try:

            is_exist = post_handler.database.session.query(WechatUser).filter(WechatUser.username == content).first()

            if is_exist:
                obj.content = f"---昵称【{content}】已存在，请重新设置---"
                return obj

            post_handler.wechat_user.username = content
            post_handler.database.session.commit()
            obj.content = f"---您的昵称已成功设置为【{content}】---"

            config.is_debug and self.logger.info(
                f'已将用户【{post_handler.request_data.to_user_id}】的昵称设置为【{content}】'
            )

        except Exception:
            obj.content = f"---昵称设置失败：未知错误---"
            self.logger.error('set_username方法出现错误', exc_info=True)
        finally:
            return obj

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['积分', '我的积分'], is_first=True,
                       function_intro='获取当前积分总数')
    def get_credit(self, *args, **kwargs) -> WechatReplyData:
        post_handler: BasePostHandler = kwargs.get('post_handler')
        credit = post_handler.wechat_user.credit
        obj = WechatReplyData(msg_type="text", content=f"您当前的积分总数为：{credit}")

        return obj

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['添加积分', '添加用户积分', '增加用户积分', '增加积分'],
                       is_master=True, is_first=False,
                       function_intro='为用户添加积分，仅管理员可用')
    def add_credit(self, content: str, *args, **kwargs) -> WechatReplyData:

        obj = WechatReplyData(msg_type="text")
        post_handler: BasePostHandler = kwargs.get('post_handler')

        try:

            # 判断权限：只有超级管理员才能使用本功能
            if not post_handler.wechat_user.is_master:
                obj.content = '您并非公众号管理者，没法使用此功能'
                return obj

            key = kwargs.get('key')

            if not key:
                obj.content = f'添加积分命令的形式是：\n\n添加积分{self.sep_char}用户专属码{self.sep_char}积分数'
                return obj

            try:
                credit_num = int(key)
            except ValueError:
                obj.content = f'添加积分命令的形式是：\n\n添加积分{self.sep_char}用户专属码{self.sep_char}积分数\n\n【积分数】必须为整数'
                return obj

            result, total_credit, msg = UserCredit.update_user_credit(
                session=post_handler.database.session,
                credit_num=credit_num,
                reason='管理员为用户添加积分',
                unique_user_id=content
            )

            if result:
                obj.content = f"成功更新用户【{content[:6]}】的积分，\n\n增加了 {credit_num} 积分；\n\n当前用户总积分：{total_credit}"
            else:
                obj.content = f"---添加积分失败：{msg}---"
        except Exception:
            obj.content = f"---添加积分失败：未知错误---"
        finally:
            return obj

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['删除关键词回复', '删除关键字回复', '删除关键字', '删除关键词'],
                       is_master=True, is_first=False, is_show=False,
                       function_intro='删除本公众号的一个关键词回复，仅管理员可用')
    def delete_keyword(self, content: str, *args, **kwargs) -> WechatReplyData:

        obj = WechatReplyData(msg_type="text", content=f"---删除关键词---")

        post_handler: BasePostHandler = kwargs.get('post_handler')
        try:

            # 判断权限：只有超级管理员才能使用本功能
            if not post_handler.wechat_user.is_master:
                obj.content = obj.content + '\n\n您并非公众号管理者，没法使用此功能'
                return obj

            is_exist = post_handler.database.session.query(KeyWord).filter(KeyWord.keyword == content).first()

            if is_exist:
                post_handler.database.session.delete(is_exist)
                post_handler.database.session.commit()
                obj.content = obj.content + f"\n\n关键词【{content}】已被删除"
            else:
                obj.content = obj.content + f"\n\n关键词【{content}】不存在"

        except Exception:
            obj.content = obj.content + f"\n\n未知错误"
        finally:
            return obj

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['设置关键词回复', '设置关键字回复'],
                       is_master=True, is_first=False,
                       function_intro='设置本公众号的关键词回复，仅管理员可用')
    def set_keyword(self, content: str, *args, **kwargs) -> WechatReplyData:

        obj = WechatReplyData(msg_type="text")

        post_handler: BasePostHandler = kwargs.get('post_handler')
        try:

            # 判断权限：只有超级管理员才能使用本功能
            if not post_handler.wechat_user.is_master:
                obj.content = '您并非公众号管理者，没法使用此功能'
                return obj

            key = kwargs.get('key')

            if not key:
                obj.content = f'设置关键词回复功能的命令形式是：设置关键词回复{self.sep_char}关键词{self.sep_char}回复语'
                return obj

            is_exist = post_handler.database.session.query(KeyWord).filter(KeyWord.keyword == content).first()

            if is_exist:
                obj.content = f"---关键词【{content}】已存在，请重新设置---"
                return obj

            keyword_obj = KeyWord(
                keyword=content,
                reply_content=key,
                reply_type='text',
            )

            post_handler.database.session.add(keyword_obj)
            post_handler.database.session.commit()

            obj.content = f"---关键词回复设置成功：【{content}】---"

        except Exception:
            obj.content = f"---关键词回复设置失败：未知错误---"
        finally:
            return obj

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['所有音色', '音色列表', '配音音色', '音色选择'], is_first=True,
                       function_intro='输出所有指令菜单，无需参数')
    def get_all_commands_text(self, content: str, *args, **kwargs) -> WechatReplyData:
        post_handler: BasePostHandler = kwargs.get('post_handler')

        reply_obj = WechatReplyData(msg_type="text", content='---无配音音色---')

        voice_dict = {}

        for keyword, info_dict in post_handler.keywords_dict.items():

            if keyword.startswith('试听-'):
                voice_dict[keyword] = info_dict.get('info')

        if not voice_dict:
            return reply_obj

        msg = '---目前支持的配音音色---\n\n'
        index = 1
        for voice, info in voice_dict.items():
            msg += f'{str(index).zfill(2)}. {voice.replace("试听-", "")}-{info}\n'
            index += 1
        msg += '\n发送【试听-(音色名称)】，如【试听-晓晓】，可试听该音色'

        return WechatReplyData(msg_type="text", content=msg)

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['所有指令', '指令列表', '所有功能', '帮助'], is_first=True,
                       function_intro='输出所有指令菜单，无需参数')
    def get_all_commands_text(self, content: str, *args, **kwargs) -> WechatReplyData:
        """获取所有指令，生成菜单"""

        post_handler: BasePostHandler = kwargs.get('post_handler')
        system_function_dict = kwargs.get('function_dict')

        function_dict = dict()

        for handler_obj, functions in system_function_dict.items():

            for command, function_obj in functions.items():

                if not function_obj.is_show:
                    continue

                if not function_obj.function_intro:
                    continue

                if function_obj.is_master and not post_handler.wechat_user.is_master:
                    continue

                if function_obj.function_name not in function_dict:
                    function_dict[function_obj.function_name] = {'command_intro': function_obj.function_intro,
                                                                 'command_list': [command, ]}
                else:
                    function_dict[function_obj.function_name]['command_list'].append(command)

        command_obj_list = []

        k = 1
        for function_name, command_info in function_dict.items():
            command_list = command_info['command_list']
            command_intro = command_info['command_intro']

            command_obj = Command(
                order=k,
                title=command_list.pop(0),
                sub_title='、'.join(command_list[-self.config.command_another_count:]) if command_list else '',
                intro=command_intro
            )

            command_obj_list.append(command_obj)
            k += 1
        first_page_content = self.paginate(content, self.command_single_page, command_obj_list, post_handler)

        return WechatReplyData(msg_type="text", content=first_page_content)

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['当前指令', '指令', ], is_first=True, function_intro='输出当前进入的指令')
    def get_current_short_cmd(self, *args, **kwargs) -> WechatReplyData:
        """获取当前指令"""

        post_handler: BasePostHandler = kwargs.get('post_handler')

        if post_handler.current_command:
            return WechatReplyData(msg_type="text", content=f"---当前指令：{post_handler.current_command}---")
        return WechatReplyData(msg_type="text", content=f"---当前指令：无---")

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=cancel_command_list, is_first=True,
                       function_intro='当进入某个指令时，需要退出才可以回到主菜单')
    def cancel_short_cmd(self, *args, **kwargs) -> WechatReplyData:
        """退出指令模式，将数据库中记录的当前指令删除"""

        post_handler: BasePostHandler = kwargs.get('post_handler')
        return self.cancel_command(post_handler)

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['command_single_page', ], is_show=False, )
    def command_single_page(self, single_page: SinglePageData, *args, **kwargs) -> str:
        """【所有指令】输出结果的单页处理方法"""

        header, middle, footer = self.make_pagination(
            current_page_num=single_page.current_page,
            pages_num=single_page.total_page,
            search_keyword=single_page.title
        )

        header = f"- - -🔑所有指令菜单🔑- - -\n\n"

        command_obj_list = single_page.data

        lines = []
        for command_obj in command_obj_list:
            if command_obj.sub_title:
                line = (
                    f"{command_obj.order}.\n✍🏻【指令名称】：{command_obj.title}\n✍🏻【指令别称】：{command_obj.sub_title}\n"
                    f"✍🏻【指令介绍】：{command_obj.intro}\n\n")
            else:
                line = f"{command_obj.order}.\n✍🏻【指令名称】：{command_obj.title}\n✍🏻【指令介绍】：{command_obj.intro}\n\n"
            lines.append(line)

        message = ''.join(lines)
        return header + message + middle + footer

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['设置昵称', '昵称'], is_first=True)
    def correct_set_nickname(self, content: str, *args, **kwargs) -> WechatReplyData:
        """当用户输入“设置昵称、昵称”等短指令而没有携带参数时，给出示例提示"""
        msg = f"""👉指令名称：{content}；
👉参数要求：需携带参数；
👉使用注意：以三个减号（---）分隔参数。

🌱示例🌱
输入【{content}---梅长苏】，将设置您的昵称为“梅长苏”。"""

        return WechatReplyData(msg_type="text", content=self.command_intro_title.format(msg))

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['设置关键词回复', '设置关键字回复'], is_first=True, is_master=True)
    def correct_set_keyword(self, content: str, *args, **kwargs) -> WechatReplyData:

        msg = f"""👉指令名称：{content}；
👉参数要求：需携带两个参数；
👉使用注意：以三个减号（---）分隔参数。

🌱示例🌱
输入【{content}---关键词---回复的文本】，用户输入关键词之后，自动回复设置的文本。"""
        return WechatReplyData(msg_type="text", content=self.command_intro_title.format(msg))

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT, is_show=True,
                       commands=['添加积分', '添加用户积分', '增加用户积分', '增加积分'], is_first=True, is_master=True)
    def correct_add_credit(self, content: str, *args, **kwargs) -> WechatReplyData:

        msg = f"""👉指令名称：{content}；
👉参数要求：需携带两个参数；
👉使用注意：以三个减号（---）分隔参数。

🌱示例🌱
输入【{content}---用户专属码---添加的积分数量】，管理员给用户添加积分。"""
        return WechatReplyData(msg_type="text", content=self.command_intro_title.format(msg))

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT, is_show=True,
                       commands=['购买积分', '积分购买', '获取积分', '如何获取积分', '增加积分', '积分介绍', '介绍积分'],
                       is_first=True, is_master=True)
    def correct_buy_credit(self, content: str, *args, **kwargs) -> WechatReplyData:
        header = '------ ✍🏻 积分介绍------\n\n'
        msg = f"""公众号的积分用于使用高级功能，
目前积分获取方式如下：

👉1. 通过签到获取；
👉2. 联系管理员购买；

🌱提示🌱
单次签到可获得 {config.min_credit} 积分；
连续签到有额外积分奖励；
单次签到最高可获得 {config.max_credit} 积分"""
        return WechatReplyData(msg_type="text", content=header + msg)


def add_keyword_function(agent_id=None, *args, **kwargs):
    obj = KeywordFunction(agent_id=agent_id, *args, **kwargs)
    return {obj: FUNCTION_DICT}


def add_first_keyword_function(agent_id=None, *args, **kwargs):
    obj = KeywordFunction(agent_id=agent_id, *args, **kwargs)
    return {obj: FIRST_FUNCTION_DICT}
