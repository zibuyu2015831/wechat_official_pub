import datetime
import logging
import os
import coloredlogs


# 生成日志记录对象
def get_logger(log_name="app_log", fmt=None, if_console=True, base_path=None):
    today = datetime.date.today()
    formatted_date = today.strftime("%Y%m%d")

    if not fmt:
        fmt = f'%(asctime)s.%(msecs)04d | %(levelname)8s | %(message)s'
        # fmt = f'%(asctime)s.%(msecs)03d {name}.%(levelname)s %(message)s'
        # fmt = "%(asctime)s|%(levelname)8s|代码行号：%(lineno)4s|%(message)s"

    # 创建一个Logger，名称是app_log
    logger = logging.getLogger(log_name)

    # 设置为日志输出级别
    logger.setLevel(logging.DEBUG)

    # 创建formatter，并设置formatter的格式
    formatter = logging.Formatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S", )

    # 创建终端输出handler，为其设置格式，并添加到logger中
    if if_console:
        # 方式一：
        # console_handler = logging.StreamHandler()
        # console_handler.setLevel(logging.INFO)  # 设置终端的输出级别为info
        #
        # console_handler.setFormatter(formatter)
        # logger.addHandler(console_handler)

        # 方式二：使用coloredlogs打印更好看的日志，注册即可，无需创建终端handler

        # 自定义日志的级别颜色
        level_color_mapping = {
            'DEBUG': {'color': 'blue'},
            'INFO': {'color': 'green'},
            'WARNING': {'color': 'yellow', 'bold': True},
            'ERROR': {'color': 'red'},
            'CRITICAL': {'color': 'red', 'bold': True}
        }
        # 自定义日志的字段颜色
        field_color_mapping = dict(
            asctime=dict(color='green'),
            hostname=dict(color='magenta'),
            levelname=dict(color='white', bold=True),
            name=dict(color='blue'),
            programname=dict(color='cyan'),
            username=dict(color='yellow'),
        )

        coloredlogs.install(
            level=logging.DEBUG,
            logger=logger,
            milliseconds=True,
            datefmt='%X',
            fmt=fmt,
            level_styles=level_color_mapping,
            field_styles=field_color_mapping
        )

    # 若传入base_path，即传入日志文件存放目录，则创建文件输出handler，为其设置格式，并添加到logger中
    if base_path:
        # 拼接路径
        log_dir = os.path.join(base_path, "log_file")
        # 判断路径是否存在，不存在则创建
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_path = os.path.join(log_dir, f"{formatted_date}.log")

        file_handler = logging.FileHandler(filename=file_path, mode='a', encoding='utf8', delay=False)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
