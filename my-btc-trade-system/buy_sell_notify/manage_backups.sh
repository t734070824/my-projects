#!/bin/bash

# 日志备份管理脚本
# 用于手动管理日志备份

show_help() {
    echo "日志备份管理脚本使用说明："
    echo "  ./manage_backups.sh backup          - 立即备份当前日志"
    echo "  ./manage_backups.sh list            - 列出所有备份"
    echo "  ./manage_backups.sh clean [days]    - 清理N天前的备份 (默认30天)"
    echo "  ./manage_backups.sh restore [backup] - 从备份恢复日志"
    echo "  ./manage_backups.sh size            - 显示备份占用空间"
    echo "  ./manage_backups.sh help            - 显示此帮助"
}

list_backups() {
    echo "=== 日志备份列表 ==="
    if [ ! -d "./log_backups" ]; then
        echo "备份目录不存在"
        return
    fi
    
    echo "备份目录: ./log_backups"
    echo ""
    
    for backup_dir in ./log_backups/backup_*; do
        if [ -d "$backup_dir" ]; then
            backup_name=$(basename "$backup_dir")
            backup_time=$(echo "$backup_name" | sed 's/backup_//' | sed 's/_/ /')
            
            # 计算备份大小
            size=$(du -sh "$backup_dir" 2>/dev/null | cut -f1)
            
            # 读取备份信息文件
            info_file="$backup_dir/backup_info.txt"
            file_count="未知"
            if [ -f "$info_file" ]; then
                file_count=$(grep "备份文件数量:" "$info_file" | cut -d: -f2 | xargs)
            fi
            
            echo "📁 $backup_name"
            echo "   时间: $backup_time"
            echo "   大小: $size"
            echo "   文件数: $file_count"
            echo ""
        fi
    done
}

backup_now() {
    echo "=== 立即备份当前日志 ==="
    python3 backup_logs.py
}

clean_old_backups() {
    days=${1:-30}
    echo "=== 清理 $days 天前的备份 ==="
    python3 -c "
import sys
sys.path.append('.')
from backup_logs import cleanup_old_backups
cleanup_old_backups($days)
"
}

restore_backup() {
    backup_name=$1
    if [ -z "$backup_name" ]; then
        echo "请指定要恢复的备份名称"
        echo "可用的备份:"
        ls -1 ./log_backups/ | grep backup_ | head -5
        return 1
    fi
    
    backup_path="./log_backups/$backup_name"
    if [ ! -d "$backup_path" ]; then
        echo "备份不存在: $backup_path"
        return 1
    fi
    
    echo "=== 恢复备份: $backup_name ==="
    echo "警告: 这将覆盖当前的日志文件!"
    read -p "确定要继续吗? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 先备份当前日志
        echo "先备份当前日志..."
        backup_now
        
        # 清空当前日志目录
        echo "清空当前日志目录..."
        rm -f ./logs/*.log*
        
        # 恢复备份的日志文件
        echo "恢复日志文件..."
        cp "$backup_path"/*.log* ./logs/ 2>/dev/null || true
        
        echo "恢复完成!"
        echo "恢复的文件:"
        ls -la ./logs/
    else
        echo "恢复操作已取消"
    fi
}

show_backup_size() {
    echo "=== 备份空间使用情况 ==="
    
    if [ ! -d "./log_backups" ]; then
        echo "备份目录不存在"
        return
    fi
    
    echo "当前日志目录大小:"
    if [ -d "./logs" ]; then
        du -sh ./logs
    else
        echo "  日志目录不存在"
    fi
    
    echo ""
    echo "备份目录总大小:"
    du -sh ./log_backups
    
    echo ""
    echo "各备份占用空间:"
    du -sh ./log_backups/backup_* 2>/dev/null | sort -hr || echo "  没有备份文件"
    
    echo ""
    echo "磁盘空间使用情况:"
    df -h . | tail -1
}

case "${1:-help}" in
    "backup")
        backup_now
        ;;
    "list")
        list_backups
        ;;
    "clean")
        clean_old_backups $2
        ;;
    "restore")
        restore_backup $2
        ;;
    "size")
        show_backup_size
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "未知选项: $1"
        show_help
        exit 1
        ;;
esac