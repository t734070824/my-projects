# 1. 使用官方的 Python 3.11 slim 版本作为基础镜像
FROM python:3.11-slim

# 2. 在容器中创建一个工作目录
WORKDIR /app

# 3. 更新包管理器并安装 supervisor
RUN apt-get update && apt-get install -y supervisor

# 4. 复制依赖文件并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 复制项目中的所有代码和配置文件到工作目录
COPY . .

# 6. 暴露HTTP服务器的8000端口
EXPOSE 8000

# 7. 设置容器启动时要执行的命令
#    这将使用 supervisord 来启动和管理我们的两个程序
CMD ["/usr/bin/supervisord", "-c", "/app/supervisord.conf"]