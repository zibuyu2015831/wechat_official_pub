# 使用Ubuntu 20.04作为基础镜像
FROM ubuntu:20.04

# 设置工作目录
WORKDIR /app

# 配置国内镜像源
RUN sed -i 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list

# 更新并安装必要的软件包
RUN apt-get update && \
    apt-get install -y software-properties-common gnupg2 && \
    apt-get clean

# 手动添加 deadsnakes PPA 并导入 GPG 密钥
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys F23C5A6CF475977595C89F51BA6932366A755776 && \
    add-apt-repository "deb http://ppa.launchpad.net/deadsnakes/ppa/ubuntu focal main"

# 更新并安装 Python 3.9 和相关依赖
RUN apt-get update && \
    apt-get install -y python3.9 python3.9-dev python3.9-distutils && \
    apt-get clean

# 安装pip
RUN apt-get install -y curl && \
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    python3.9 get-pip.py && \
    rm get-pip.py

# 安装 PostgreSQL 依赖和构建工具，解决 psycopg2 编译问题
RUN apt-get update && \
    apt-get install -y libpq-dev build-essential gcc python3-dev make && \
    apt-get clean

# 复制项目文件到容器中
COPY . /app

# 安装Python依赖
RUN pip3.9 install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 暴露端口
EXPOSE 9000

# 设置环境变量
ENV FLASK_APP=app.py

# 运行Flask应用
CMD ["python3.9", "app.py"]
