# 1. 使用官方的 Python 3.11 slim 版本作为基础镜像
FROM python:3.11-slim

# 2. 设置时区环境变量
ENV TZ=Asia/Shanghai

# 3. 在容器中创建一个工作目录
WORKDIR /app

# 4. 更新包管理器并安装 supervisor 和时区数据
#    下面的命令会根据 TZ 环境变量设置系统时区
RUN apt-get update && apt-get install -y supervisor tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 5. 复制依赖文件并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. 复制项目中的所有代码和配置文件到工作目录
COPY . .

# 7. 创建日志目录并设置权限
RUN mkdir -p /app/logs && chmod 755 /app/logs

# 8. 创建日志卷挂载点
VOLUME ["/app/logs"]

# 9. 暴露HTTP服务器的8001端口
EXPOSE 8001

# 10. 设置容器启动时要执行的命令
CMD ["/usr/bin/supervisord", "-c", "/app/supervisord.conf"]