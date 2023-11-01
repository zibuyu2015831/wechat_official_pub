# 微信公众号开发——基于flask框架

## 关于text_handler.py中的TextHandler类

### 1. function_mapping
    
该函数存放调用名与方法的对应关系，开发新功能时，先书写业务处理函数，再在 `mapping_dict` 中填写对应关系。

关于文本处理的方法，至少接收两个位置参数，第一个参数为处理的文本，第二个参数（key）为附带参数。