#!/bin/bash
#
# 一键部署 PNL 监控应用脚本
#
# 功能:
# 1. 拉取最新的代码。
# 2. 停止并删除旧的容器。
# 3. 构建新的 Docker 镜像。
# 4. 启动新的 Docker 容器，并挂载数据和配置文件。
# 5. 设置容器为始终重启。
# 6. 显示容器日志。

# 设置脚本在遇到错误时立即退出
set -e

# --- 配置 ---
IMAGE_NAME="pnl-monitor-app"
CONTAINER_NAME="pnl-monitor-container"
HTTP_PORT=8088 # 主机映射到容器8000端口的端口号

# --- 检查 ---
# 检查 Docker 是否正在运行
if ! docker info > /dev/null 2>&1; then
  echo "❌ Docker 服务没有运行，请先启动 Docker。"
  exit 1
fi

# 检查 API 密钥文件是否存在
if [ ! -f "api_keys.py" ]; then
    echo "❌ 未找到 api_keys.py 文件，请先创建并配置好该文件。"
    exit 1
fi

# --- 部署流程 ---
echo "▶️ 1. 拉取最新代码..."
git pull

echo "▶️ 2. 停止并删除旧容器..."
# 使用 || true 来防止在容器不存在时脚本因错误而退出
docker stop $CONTAINER_NAME || true
docker rm $CONTAINER_NAME || true

echo "▶️ 3. 构建新的 Docker 镜像..."
docker build -t $IMAGE_NAME .

echo "▶️ 4. 准备持久化文件..."
# 如果数据文件不存在，则创建空文件，以确保挂载成功
touch -a pnl_history.json
touch -a pnl_chart.png
echo "   - pnl_history.json 和 pnl_chart.png 已准备就绪。"

echo "▶️ 5. 启动新容器..."
docker run -d \
  --name $CONTAINER_NAME \
  -p $HTTP_PORT:8000 \
  -v "$(pwd)/api_keys.py":/app/api_keys.py:ro \
  -v "$(pwd)/pnl_history.json":/app/pnl_history.json \
  -v "$(pwd)/pnl_chart.png":/app/pnl_chart.png \
  --restart always \
  $IMAGE_NAME

echo "✅ 部署成功！"
echo "   - 镜像名称: $IMAGE_NAME"
echo "   - 容器名称: $CONTAINER_NAME"
echo "   - PNL图表访问地址: http://<你的服务器IP>:$HTTP_PORT/pnl_chart.png"
echo ""
echo "▶️ 6. 正在显示实时日志 (按 Ctrl+C 退出日志查看)..."
echo "-----------------------------------------------------"
docker logs -f $CONTAINER_NAME
