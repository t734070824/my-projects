# 1. 使用官方的 Python 3.11 slim 版本作为基础镜像
FROM python:3.11-slim

# 2. 在容器中创建一个工作目录
WORKDIR /app

# 3. 复制依赖文件并安装依赖
#    我们先只复制 requirements.txt 并安装，这样可以利用Docker的层缓存
#    只有当 requirements.txt 发生变化时，才会重新安装依赖，加快后续构建速度
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 复制项目中的所有代码到工作目录
#    注意：.dockerignore 文件可以用来排除不需要复制的文件
COPY . .

# 5. 设置容器启动时要执行的命令
#    这将运行你的主程序 main.py
CMD ["python", "-u", "main.py"]
