# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: wechat_official_SCF
author: 子不语
date: 2024/11/20
contact: 【公众号】思维兵工厂
description: 存储一些常量
--------------------------------------------
"""

sep_char = '---'

# 使用云函数时，文件的保存路径
file_save_dir_path = '/tmp'

# 天气信息对应表
weather_info = {
    "CLEAR_DAY": [
        "晴（白天）",
        "☀"
    ],
    "CLEAR_NIGHT": [
        "晴（夜间）",
        "🌙"
    ],
    "PARTLY_CLOUDY_DAY": [
        "多云（白天）",
        "⛅"
    ],
    "PARTLY_CLOUDY_NIGHT": [
        "多云（夜间）",
        "⛅"
    ],
    "CLOUDY": [
        "阴",
        "☁"
    ],
    "LIGHT_HAZE": [
        "轻度雾霾",
        "🌫"
    ],
    "MODERATE_HAZE": [
        "中度雾霾",
        "🌫"
    ],
    "HEAVY_HAZE": [
        "重度雾霾",
        "🌫"
    ],
    "LIGHT_RAIN": [
        "小雨",
        "🌂"
    ],
    "MODERATE_RAIN": [
        "中雨",
        "☔"
    ],
    "HEAVY_RAIN": [
        "大雨",
        "🌨"
    ],
    "STORM_RAIN": [
        "暴雨",
        "💦"
    ],
    "FOG": [
        "雾",
        "🌫"
    ],
    "LIGHT_SNOW": [
        "小雪",
        "❄"
    ],
    "MODERATE_SNOW": [
        "中雪",
        "⛄"
    ],
    "HEAVY_SNOW": [
        "大雪",
        "☃"
    ],
    "STORM_SNOW": [
        "暴雪",
        "☃"
    ],
    "DUST": [
        "浮尘",
        "🌪"
    ],
    "SAND": [
        "沙尘",
        "🌪"
    ],
    "WIND": [
        "大风",
        "🌪"
    ]
}

# 符号表情
emotion_icon = [
    "\\(^o^)/~O(∩_∩)O",
    "(๑´ㅂ`๑)",
    "ヾ(✿ﾟ▽ﾟ)ノ",
    "ヾ(≧≦*)ヾ(*≧∪≦)",
    "(*´・ｖ・)",
    "(≧≦)(*≧▽≦)",
    "(｡◕ˇ∀ˇ◕)",
    "( *︾▽︾)ヾ(≧ ▽ ≦)ゝ",
    "(●''●)",
    "(*ｖ) *(ˊˋ*)*",
    "(*^▽^*)（*＾-＾*）",
    "｡◕ᴗ◕｡",
    "ƪ(˘⌣˘)ʃ",
    "(～￣▽￣)～",
    "(*￣︶￣) (ノ￣▽￣)",
    "(☆▽☆)^o^",
    "♪(^∇^*)",
    "φ(゜▽゜*) <(￣︶￣)↗",
    "(σ`)σ (*)=3",
    "ヾ(•ω•`。)",
    "(◕ᴗ◕✿)",
    "(´▽`)ﾉ",
    "(≖ᴗ≖)✧",
    "✧⁺⸜(๑˙▾˙๑)⸝⁺✧",
    "⁽⁽ (๑˃̶͈̀ ᗨ ˂̶͈́) ⁾⁾",
    "✧⁺⸜(●˙▾˙●)⸝⁺✧",
    "(*｀) ヽ()()",
    "(*^▽^*)",
    "(*^_^*)(`)",
    "()＼(⌒⌒*)/",
    "♡ (ू˃o˂ ू)⁼³₌₃",
    "(●＾o＾●)(★＞U＜★)",
    "(*^_^*) ()",
    "()",
    "ヾ(◍°∇°◍)ﾉﾞ",
    "(*￣▽￣*)ブ",
    "(★^O^★)(★★)",
    "(≧≦) (▽`)○",
    "o(*￣▽￣*)o( ω )y",
    "ヾ(▽)ノ ()",
    "٩(๑❛ᴗ❛๑)۶",
    "(￣▽￣)~*",
    "( ω ) []~(￣▽￣)~*",
    "\\^o^/()",
    "(❁´◡`❁)*✲ﾟ*",
    "（＾＾●）(●｀●)",
    "ㄟ(≧◇≦)ㄏ o((>ω< ))o",
    "ヾ(●´∀｀●)",
    "o(*￣▽￣*)o",
    "ヾ(๑╹◡╹)ﾉ",
    "(｡•̀ᴗ-)✧",
    "( •͈ᴗ⁃͈)ᓂ- - -♡﻿",
    "( ＾皿＾)っ Hiahia…",
    "ヾ(@^▽^@)ノ(`)*",
    "(づ｡◕ᴗᴗ◕｡)づ",
    "ヾ(◍°∇°◍)ﾉ",
    "(◍˃̶ᗜ˂̶◍)✩",
    "(oﾟ▽ﾟ)o",
    "✧*｡ (ˊᗜˋ*) ✧*",
    "(≧∀≦)ゞ",
    "- ̗̀(๑ᵔ⌔ᵔ๑)εïз",
    "(｀▽*)╭(′▽`)╭(′▽`)╯",
    "(▽*) φ(゜▽゜*)",
    "⸂⸂⸜(രᴗര )⸝⸃⸃",
    "(▽｀)( *^-^)",
    "ヾ(°°) ヾ()\"",
    "(￣y▽￣)╭ Ohohoho.....",
    "(*^__^*) Y(^o^)Y",
    "(灬°ω°灬)",
    "(￣︶￣〃) o(*^▽^*)┛o",
    "o(*≧▽≦)ツ┏━┓",
    "(-_^) o(*￣▽￣*)ブ",
    "(☆^O^☆)(ｖ＾＿＾)ｖ",
    "(*´ﾟ∀ﾟ｀)ﾉ",
    "（▽）(o▽｀o)",
    "ヽ(✿ﾟ▽ﾟ)ノ",
    "(●ˇˇ●)",
    "(๑¯∀¯๑)",
    "╰(*°▽°*)╯",
    "(^^*) (≧≦)ゞ",
    "( • ̀ω•́ )✧",
    "(￣３￣)a",
    "ヾ(^Д^*)/ヾ(o｀o)",
    "o(*^＠^*)o O(∩_∩)O",
    "ฅ( ̳• ◡ • ̳)ฅ",
    "੭ ᐕ)੭*⁾⁾",
    "(><) ()\"\"\"",
    "(︶`)★,:*:\\(￣▽￣)/:*°★*",
    "｡ﾟ+.ღ(ゝ◡ ⚈᷀᷁ღ)",
    "(￣▽￣) ~*(￣▽￣)／",
    "ヾ(=･ω･=)o",
    "(●ツ●)",
    "༼ つ ◕‿◕ ༽つ",
    "()`(*>﹏<*)′",
    "(｀・ω・´)",
    "(^///^)(p≧w≦q)",
    "( ^∀^)/欢迎\\( ^∀^)",
    "◔.̮◔✧",
    "︿(￣︶￣)︿",
    "~(￣▽￣)~*",
    "(o゜▽゜)o☆ ()",
    "( ω ) *^____^*",
    "(/≧▽≦)/ ( $ _ $ )"
]

# 退出指令
cancel_command_list = ['退出指令', '退出', '取消指令', '取消']

# 网盘信息对应表
drive_info = {
    1: {
        "order": 1,
        "drive_name": "阿里网盘",
        "pattern": "https://www\\.alipan\\.com/s/[a-zA-Z0-9\\?=#]+",
        "prefix": "https://www.alipan.com/s/"
    },
    2: {
        "order": 2,
        "drive_name": "百度网盘",
        "pattern": "https://pan\\.baidu\\.com/s/[a-zA-Z0-9\\?=#]+",
        "prefix": "https://pan.baidu.com/s/"
    },
    3: {
        "order": 3,
        "drive_name": "夸克网盘",
        "pattern": "https://pan\\.quark\\.cn/s/[a-zA-Z0-9\\?=#]+",
        "prefix": "https://pan.quark.cn/s/"
    },
    4: {
        "order": 4,
        "drive_name": "蓝奏云",
        "pattern": "https://wwf\\.lanzouo\\.com/[a-zA-Z0-9\\?=#]+",
        "prefix": "https://wwf.lanzouo.com/"
    },
    5: {
        "order": 5,
        "drive_name": "迅雷网盘",
        "pattern": "https://pan\\.xunlei\\.com/s/[a-zA-Z0-9\\?=#]+",
        "prefix": "https://pan.xunlei.com/s/"
    },
    "阿里网盘": {
        "order": 1,
        "drive_name": "阿里网盘",
        "pattern": "https://www\\.alipan\\.com/s/[a-zA-Z0-9\\?=#]+",
        "prefix": "https://www.alipan.com/s/"
    },
    "百度网盘": {
        "order": 2,
        "drive_name": "百度网盘",
        "pattern": "https://pan\\.baidu\\.com/s/[a-zA-Z0-9\\?=#]+",
        "prefix": "https://pan.baidu.com/s/"
    },
    "夸克网盘": {
        "order": 3,
        "drive_name": "夸克网盘",
        "pattern": "https://pan\\.quark\\.cn/s/[a-zA-Z0-9\\?=#]+",
        "prefix": "https://pan.quark.cn/s/"
    },
    "蓝奏云": {
        "order": 4,
        "drive_name": "蓝奏云",
        "pattern": "https://wwf\\.lanzouo\\.com/[a-zA-Z0-9\\?=#]+",
        "prefix": "https://wwf.lanzouo.com/"
    },
    "迅雷网盘": {
        "order": 5,
        "drive_name": "迅雷网盘",
        "pattern": "https://pan\\.xunlei\\.com/s/[a-zA-Z0-9\\?=#]+",
        "prefix": "https://pan.xunlei.com/s/"
    },
    "aliyundrive": {
        "order": 1,
        "drive_name": "阿里网盘",
        "pattern": "https://www\\.aliyundrive\\.com/s/[a-zA-Z0-9\\?=#]+",
        "prefix": "https://www.aliyundrive.com/s/"
    },
    "alipan": {
        "order": 1,
        "drive_name": "阿里网盘",
        "pattern": "https://www\\.alipan\\.com/s/[a-zA-Z0-9\\?=#]+",
        "prefix": "https://www.alipan.com/s/"
    },
    "baidu": {
        "order": 2,
        "drive_name": "百度网盘",
        "pattern": "https://pan\\.baidu\\.com/s/[a-zA-Z0-9\\?=#]+",
        "prefix": "https://pan.baidu.com/s/"
    },
    "quark": {
        "order": 3,
        "drive_name": "夸克网盘",
        "pattern": "https://pan\\.quark\\.cn/s/[a-zA-Z0-9\\?=#]+",
        "prefix": "https://pan.quark.cn/s/"
    },
    "lanzouo": {
        "order": 4,
        "drive_name": "蓝奏云",
        "pattern": "https://wwf\\.lanzouo\\.com/[a-zA-Z0-9\\?=#]+",
        "prefix": "https://wwf.lanzouo.com/"
    },
    "xunlei": {
        "order": 5,
        "drive_name": "迅雷网盘",
        "pattern": "https://pan\\.xunlei\\.com/s/[a-zA-Z0-9\\?=#]+",
        "prefix": "https://pan.xunlei.com/s/"
    }
}
