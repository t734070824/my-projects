#!/bin/bash

# 日志查看脚本
# 用法：./view_logs.sh [选项]

show_help() {
    echo "日志查看脚本使用说明："
    echo "  ./view_logs.sh              - 查看主程序最新日志"
    echo "  ./view_logs.sh main         - 查看主程序日志"
    echo "  ./view_logs.sh monitor      - 查看仓位监控日志"
    echo "  ./view_logs.sh all          - 同时查看所有日志"
    echo "  ./view_logs.sh tail         - 实时跟踪主程序日志"
    echo "  ./view_logs.sh tail monitor - 实时跟踪仓位监控日志"
    echo "  ./view_logs.sh grep 'EXECUTE' - 搜索包含EXECUTE的日志行"
    echo "  ./view_logs.sh help         - 显示此帮助信息"
}

case "${1:-main}" in
    "main"|"")
        echo "=== 查看主程序日志 (最近100行) ==="
        if [ -f "./logs/trading_system.log" ]; then
            tail -n 100 ./logs/trading_system.log
        else
            echo "日志文件不存在: ./logs/trading_system.log"
        fi
        ;;
    "monitor")
        echo "=== 查看仓位监控日志 (最近100行) ==="
        if [ -f "./logs/position_monitor.log" ]; then
            tail -n 100 ./logs/position_monitor.log
        else
            echo "日志文件不存在: ./logs/position_monitor.log"
        fi
        ;;
    "all")
        echo "=== 查看主程序日志 ==="
        if [ -f "./logs/trading_system.log" ]; then
            tail -n 50 ./logs/trading_system.log
        fi
        echo -e "\n=== 查看仓位监控日志 ==="
        if [ -f "./logs/position_monitor.log" ]; then
            tail -n 50 ./logs/position_monitor.log
        fi
        ;;
    "tail")
        if [ "$2" = "monitor" ]; then
            echo "=== 实时跟踪仓位监控日志 ==="
            tail -f ./logs/position_monitor.log
        else
            echo "=== 实时跟踪主程序日志 ==="
            tail -f ./logs/trading_system.log
        fi
        ;;
    "grep")
        if [ -z "$2" ]; then
            echo "请提供搜索关键词，例如: ./view_logs.sh grep 'EXECUTE'"
            exit 1
        fi
        echo "=== 搜索关键词: $2 ==="
        if [ -f "./logs/trading_system.log" ]; then
            echo "--- 主程序日志匹配行 ---"
            grep -i "$2" ./logs/trading_system.log | tail -n 20
        fi
        if [ -f "./logs/position_monitor.log" ]; then
            echo "--- 仓位监控日志匹配行 ---"
            grep -i "$2" ./logs/position_monitor.log | tail -n 20
        fi
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