#!/bin/bash

# 当任何命令失败时，立即退出脚本
set -e

# 1. 从 Git 拉取最新代码
echo ">>> 步骤 1/4: 正在从 Git 拉取最新代码..."
git pull

# 2. 构建新的 Docker 镜像
echo ">>> 步骤 2/4: 正在构建新的 Docker 镜像 'buy_sell_sigal'..."
docker build -t buy_sell_sigal .

# 3. 停止并删除已存在的旧容器，`|| true` 可以防止在容器不存在时报错
echo ">>> 步骤 3/4: 正在停止并删除旧的容器 'buy_sell_sigal_test'..."
docker stop buy_sell_sigal_test || true
docker rm buy_sell_sigal_test || true

# 4. 创建本地日志目录
echo ">>> 步骤 4/5: 创建本地日志目录..."
mkdir -p ./logs

# 5. 启动新的容器（挂载日志目录）
echo ">>> 步骤 5/5: 正在启动新容器 'buy_sell_sigal_test'（挂载日志目录）..."
docker run -d --name buy_sell_sigal_test -v $(pwd)/logs:/app/logs buy_sell_sigal

echo ">>> 部署成功完成！"
