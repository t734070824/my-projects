#!/bin/bash

# Docker 部署脚本（带自动日志备份功能）
# 当任何命令失败时，立即退出脚本
set -e

# 分支选择（默认 main）
BRANCH=${1:-main}

echo "=== Docker 容器重启部署脚本（带日志备份）==="
echo ">>> 使用分支: $BRANCH"

# 1. 备份现有日志文件
echo ">>> 步骤 1/7: 备份现有日志文件..."
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
echo ">>> 步骤 2/7: 正在从 Git 拉取最新代码..."

# 检查当前分支
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "当前分支: $CURRENT_BRANCH"

# 如果需要切换分支
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
    echo "正在切换到分支: $BRANCH"
    # 先拉取所有分支信息
    git fetch origin
    
    # 检查分支是否存在
    if git show-ref --verify --quiet refs/heads/$BRANCH; then
        echo "本地分支 $BRANCH 存在，切换中..."
        git checkout $BRANCH
    elif git show-ref --verify --quiet refs/remotes/origin/$BRANCH; then
        echo "远程分支 origin/$BRANCH 存在，创建并切换到本地分支..."
        git checkout -b $BRANCH origin/$BRANCH
    else
        echo "❌ 错误: 分支 $BRANCH 不存在（本地和远程都没有）"
        echo "可用的分支:"
        git branch -a
        exit 1
    fi
else
    echo "已在目标分支 $BRANCH 上"
fi

# 拉取最新代码
echo "正在拉取分支 $BRANCH 的最新代码..."
git pull origin $BRANCH

# 3. 显示当前代码状态
echo ">>> 步骤 3/7: 显示当前代码状态..."
echo "当前提交: $(git log --oneline -1)"
echo "分支状态: $(git status --porcelain | wc -l) 个未提交的更改"

# 4. 构建新的 Docker 镜像
echo ">>> 步骤 4/7: 正在构建新的 Docker 镜像 'buy_sell_sigal'..."
docker build -t buy_sell_sigal .

# 5. 停止并删除已存在的旧容器
echo ">>> 步骤 5/7: 正在停止并删除旧的容器 'buy_sell_sigal_test'..."
docker stop buy_sell_sigal_test || true
docker rm buy_sell_sigal_test || true

# 6. 创建本地日志目录
echo ">>> 步骤 6/7: 创建本地日志目录..."
mkdir -p ./logs
mkdir -p ./log_backups

# 7. 启动新的容器（挂载日志目录）
echo ">>> 步骤 7/7: 正在启动新容器 'buy_sell_sigal_test'（挂载日志目录）..."
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
echo ""
echo "=== 使用说明 ==="
echo "默认使用 main 分支:"
echo "  bash docker_deploy_with_backup.sh"
echo ""
echo "指定其他分支:"
echo "  bash docker_deploy_with_backup.sh develop"
echo "  bash docker_deploy_with_backup.sh feature/new-notifications"
echo "  bash docker_deploy_with_backup.sh hotfix/urgent-fix"
echo ""
echo "可用的 Git 分支:"
git branch -a | head -10