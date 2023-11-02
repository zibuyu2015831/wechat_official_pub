# 微信公众号开发——基于flask框架

## 关于text_handler.py中的TextHandler类

### 1. function_mapping
    
该函数存放调用名与方法的对应关系，开发新功能时，先书写业务处理函数，再在 `mapping_dict` 中填写对应关系。

关于文本处理的方法，至少接收两个位置参数，第一个参数为处理的文本，第二个参数（key）为附带参数。

## 用于会话记录

示例：
```json
{
  "user_id": "ojk036kPB99gY-Ehw0rS8qVs4PgM",
  "last_msg_id": "24322210829239184",
  "last_msg_reply": "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<xml><ToUserName>ojk036kPB99gY-Ehw0rS8qVs4PgM</ToUserName><FromUserName>gh_0436edeba6fb</FromUserName><CreateTime>1698887096</CreateTime><MsgType>text</MsgType><Content>我没有获取实时日期的能力，没法回答...</Content></xml>",
  "short_command": [],
  "user_ai_talk": [
    {
      "msg_time": 1698887096,
      "msg_list": [
        {
          "role": "user",
          "content": "今天星期几？"
        },
        {
          "role": "assistant",
          "content": "我没有获取实时日期的能力，没法回答..."
        }
      ]
    }
  ]
}
```