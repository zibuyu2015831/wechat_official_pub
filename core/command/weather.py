# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: mind_workshop
author: 子不语
date: 2024/4/24
contact: 【公众号】思维兵工厂
description: 【关键词回复功能】天气查询功能
--------------------------------------------
"""

import time
from typing import TYPE_CHECKING

from .base import WeChatKeyword, register_function
from ..types import WechatReplyData
from ..models import KeyWord

if TYPE_CHECKING:
    from ..handle_post import BasePostHandler

FUNCTION_DICT = dict()
FIRST_FUNCTION_DICT = dict()


class KeywordFunction(WeChatKeyword):
    model_name = "weather"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__weather_handler = None

    @property
    def weather_handler(self):
        """惰性引入WeatherHandler类"""

        if not self.__weather_handler:
            from ..utils.weather import WeatherHandler
            self.__weather_handler = WeatherHandler()
        return self.__weather_handler

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['查询天气', '天气查询', '天气', '获取天气'], is_first=False,
                       function_intro='根据传入的地点，查询天气信息，支持市、镇、区等，不支持省份')
    def get_weather(self, content: str, *args, **kwargs):
        """天气---地点：通过调用免费接口获取天气信息"""

        post_handler: BasePostHandler = kwargs.get('post_handler')

        current_timestamp = int(time.time())
        expire_time = 60 * 60 * 3 + current_timestamp

        obj = None
        try:
            weather_info = self.weather_handler.free_weather(content)
            if not weather_info:
                obj = WechatReplyData(
                    msg_type="text",
                    content=f"---{content}天气查询地点有误---",
                )

            update_time = f"更新时间:  {weather_info['time'].rsplit(':', maxsplit=1)[0]}".center(22, '-')

            city_info = weather_info['cityInfo']
            city_info_tip = f" 📍 {city_info.get('parent') or ''}{city_info['city']}".center(16, '-')

            reply = ''
            forecast_list = weather_info['data']['forecast']
            for index, day_info in enumerate(forecast_list):
                high = day_info['high'].strip('高低温').strip()
                low = day_info['low'].strip('高低温').strip()

                temperature = f"🌡高低气温:  {low}~{high}"

                week = day_info['week']
                ymd = day_info['ymd']
                day = f"📅  {ymd} {week}"

                sunrise = day_info['sunrise']
                sunset = day_info['sunset']
                sun_info = f"🌅日出日落:  {sunrise} <--> {sunset}"

                weather_type = day_info['type']
                wind_direction = day_info['fx']
                wind_level = day_info['fl']
                weather_info = f"☁天气现象:  {weather_type} {wind_direction}{wind_level}"

                notice = day_info['notice']
                sentence = f"📙温馨提醒:  {notice}"

                tip = f"{day}\n\n{temperature}\n\n{sun_info}\n\n{weather_info}\n\n{sentence}"
                final_reply = city_info_tip + '\n\n' + tip + '\n\n' + update_time

                keyword = f"{index}天后天气"
                if index == 0:
                    reply = final_reply
                    keyword = f"{content}天气"

                keyword_obj = KeyWord(
                    keyword=keyword,
                    reply_content=final_reply,
                    reply_type='text',
                    official_user_id=post_handler.request_data.to_user_id,
                    expire_time=expire_time
                )

                post_handler.database.session.add(keyword_obj)
            post_handler.database.session.commit()

            obj = WechatReplyData(
                msg_type="text",
                content=reply
            )

        except Exception:
            obj = WechatReplyData(
                msg_type="text",
                content=f"---{content}天气查询失败---"
            )
            self.logger.error(f"查询天气失败", exc_info=True)
        finally:
            return obj

    @register_function(first_function_dict=FIRST_FUNCTION_DICT, function_dict=FUNCTION_DICT,
                       commands=['查询天气', '天气查询', '天气', '获取天气'], is_first=True)
    def correct_get_weather(self, content: str, *args, **kwargs):
        """当用户输入“天气、查询天气”等短指令而没有携带参数时，给出示例提示"""

        msg = f"""👉指令名称：{content}；
👉参数要求：需携带参数；
👉使用注意：以三个减号（---）分隔参数。

🌱示例🌱
输入【{content}---地点】，将查询该地点15天内的天气信息。

🌱提示🌱
查询天气后，回复【具体数字+天后天气】将返回对应天数后的天气信息。

如：回复【2天后天气】，将给出2天后的天气信息。"""

        return WechatReplyData(msg_type="text", content=self.command_intro_title.format(msg))


def add_keyword_function(*args, **kwargs):
    obj = KeywordFunction(*args, **kwargs)
    return {obj: FUNCTION_DICT}


def add_first_keyword_function(*args, **kwargs):
    obj = KeywordFunction(*args, **kwargs)
    return {obj: FIRST_FUNCTION_DICT}
