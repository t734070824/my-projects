#!/bin/bash

# Docker 部署脚本（带自动日志备份功能）
# 当任何命令失败时，立即退出脚本
set -e

echo "=== Docker 容器重启部署脚本（带日志备份）==="

# 1. 备份现有日志文件
echo ">>> 步骤 1/6: 备份现有日志文件..."
if [ -d "./logs" ] && [ "$(ls -A ./logs 2>/dev/null)" ]; then
    echo "发现现有日志文件，正在备份..."
    python3 backup_logs.py
    if [ $? -ne 0 ]; then
        echo "警告: 日志备份失败，但继续部署流程"
    fi
else
    echo "没有找到现有日志文件，跳过备份步骤"
fi

# 2. 从 Git 拉取最新代码
echo ">>> 步骤 2/6: 正在从 Git 拉取最新代码..."
git pull

# 3. 构建新的 Docker 镜像
echo ">>> 步骤 3/6: 正在构建新的 Docker 镜像 'buy_sell_sigal'..."
docker build -t buy_sell_sigal .

# 4. 停止并删除已存在的旧容器
echo ">>> 步骤 4/6: 正在停止并删除旧的容器 'buy_sell_sigal_test'..."
docker stop buy_sell_sigal_test || true
docker rm buy_sell_sigal_test || true

# 5. 创建本地日志目录
echo ">>> 步骤 5/6: 创建本地日志目录..."
mkdir -p ./logs
mkdir -p ./log_backups

# 6. 启动新的容器（挂载日志目录）
echo ">>> 步骤 6/6: 正在启动新容器 'buy_sell_sigal_test'（挂载日志目录）..."
docker run -d --name buy_sell_sigal_test \
    -v $(pwd)/logs:/app/logs \
    -v $(pwd)/log_backups:/app/log_backups \
    --restart unless-stopped \
    buy_sell_sigal

# 7. 检查容器状态
echo ">>> 检查容器状态..."
sleep 3
if docker ps | grep -q buy_sell_sigal_test; then
    echo "✅ 容器启动成功！"
    echo ">>> 容器信息:"
    docker ps --filter name=buy_sell_sigal_test --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo ">>> 日志文件位置:"
    echo "  - 当前日志: ./logs/"
    echo "  - 历史备份: ./log_backups/"
    
    echo ">>> 查看容器日志命令:"
    echo "  docker logs buy_sell_sigal_test"
    echo ">>> 查看交易日志命令:"
    echo "  ./view_logs.sh"
else
    echo "❌ 容器启动失败，请检查Docker状态"
    docker logs buy_sell_sigal_test || true
    exit 1
fi

echo ">>> 部署成功完成！"