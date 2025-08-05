#!/bin/bash

# 当任何命令失败时，立即退出脚本
set -e

echo "=== 快速部署脚本（无备份）==="
echo "注意: 此脚本不会备份日志，如需备份请使用 docker_deploy_with_backup.sh"

# 1. 备份现有日志文件（可选，用户确认）
if [ -d "./logs" ] && [ "$(ls -A ./logs 2>/dev/null)" ]; then
    echo ">>> 发现现有日志文件"
    read -p "是否要备份现有日志？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "正在备份日志..."
        python3 backup_logs.py || echo "备份失败，但继续部署"
    fi
fi

# 2. 从 Git 拉取最新代码
echo ">>> 步骤 1/5: 正在从 Git 拉取最新代码..."
git pull

# 3. 构建新的 Docker 镜像
echo ">>> 步骤 2/5: 正在构建新的 Docker 镜像 'buy_sell_sigal'..."
docker build -t buy_sell_sigal .

# 4. 停止并删除已存在的旧容器，`|| true` 可以防止在容器不存在时报错
echo ">>> 步骤 3/5: 正在停止并删除旧的容器 'buy_sell_sigal_test'..."
docker stop buy_sell_sigal_test || true
docker rm buy_sell_sigal_test || true

# 5. 创建本地日志目录
echo ">>> 步骤 4/5: 创建本地日志目录..."
mkdir -p ./logs
mkdir -p ./log_backups

# 6. 启动新的容器（挂载日志目录）
echo ">>> 步骤 5/5: 正在启动新容器 'buy_sell_sigal_test'（挂载日志目录）..."
docker run -d --name buy_sell_sigal_test \
    -v $(pwd)/logs:/app/logs \
    -v $(pwd)/log_backups:/app/log_backups \
    --restart unless-stopped \
    buy_sell_sigal

echo ">>> 部署成功完成！"
echo "提示: 下次使用 docker_deploy_with_backup.sh 可以自动备份日志"
