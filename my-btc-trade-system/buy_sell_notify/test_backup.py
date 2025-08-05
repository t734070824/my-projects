#!/usr/bin/env python3
"""
备份功能测试脚本
用于测试日志备份和清理功能
"""

import os
import sys
from pathlib import Path
import logging

# 添加当前目录到Python路径
sys.path.insert(0, '.')

from backup_logs import backup_logs, cleanup_old_backups, setup_backup_logger

def create_test_logs():
    """创建测试日志文件"""
    logger = setup_backup_logger()
    
    # 创建日志目录
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    # 创建一些测试日志文件
    test_files = [
        "trading_system.log",
        "position_monitor.log",
        "trading_system.log.1",
        "position_monitor.log.1"
    ]
    
    for filename in test_files:
        file_path = log_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"这是测试日志文件: {filename}\n")
            f.write("2025-01-15 10:00:00 - TestLogger - INFO - 测试日志消息1\n")
            f.write("2025-01-15 10:01:00 - TestLogger - INFO - 测试日志消息2\n")
            f.write("2025-01-15 10:02:00 - TestLogger - WARNING - 测试警告消息\n" * 50)
        logger.info(f"创建测试文件: {file_path}")
    
    return len(test_files)

def test_backup_with_removal():
    """测试备份并删除原文件"""
    logger = setup_backup_logger()
    logger.info("=== 测试备份并删除原文件 ===")
    
    # 创建测试日志
    created_count = create_test_logs()
    
    # 执行备份（删除原文件）
    success = backup_logs(remove_original=True)
    
    if success:
        logger.info("✅ 备份成功")
        
        # 检查原文件是否被删除
        log_dir = Path("./logs")
        remaining_files = list(log_dir.glob("*.log*"))
        
        if not remaining_files:
            logger.info("✅ 原始日志文件已成功删除")
        else:
            logger.warning(f"⚠️ 仍有 {len(remaining_files)} 个原始文件未删除: {[f.name for f in remaining_files]}")
    else:
        logger.error("❌ 备份失败")
    
    return success

def test_backup_without_removal():
    """测试备份但保留原文件"""
    logger = setup_backup_logger()
    logger.info("=== 测试备份但保留原文件 ===")
    
    # 创建测试日志
    created_count = create_test_logs()
    
    # 执行备份（保留原文件）
    success = backup_logs(remove_original=False)
    
    if success:
        logger.info("✅ 备份成功")
        
        # 检查原文件是否仍然存在
        log_dir = Path("./logs")
        remaining_files = list(log_dir.glob("*.log*"))
        
        if remaining_files:
            logger.info(f"✅ 原始日志文件已保留: {len(remaining_files)} 个文件")
        else:
            logger.warning("⚠️ 原始文件意外消失")
    else:
        logger.error("❌ 备份失败")
    
    return success

def list_backup_status():
    """显示备份状态"""
    logger = setup_backup_logger()
    logger.info("=== 当前备份状态 ===")
    
    # 检查备份目录
    backup_dir = Path("./log_backups")
    if backup_dir.exists():
        backups = list(backup_dir.glob("backup_*"))
        logger.info(f"找到 {len(backups)} 个备份:")
        for backup in sorted(backups):
            files = list(backup.glob("*.log*"))
            info_file = backup / "backup_info.txt"
            if info_file.exists():
                with open(info_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                logger.info(f"  📁 {backup.name} - {first_line}")
            else:
                logger.info(f"  📁 {backup.name} - {len(files)} 个文件")
    else:
        logger.info("没有找到备份目录")
    
    # 检查当前日志目录
    log_dir = Path("./logs")
    if log_dir.exists():
        current_files = list(log_dir.glob("*.log*"))
        logger.info(f"当前日志目录有 {len(current_files)} 个文件")
    else:
        logger.info("当前日志目录不存在")

def main():
    """主测试函数"""
    logger = setup_backup_logger()
    logger.info("=== 开始备份功能测试 ===")
    
    try:
        # 测试1: 备份并删除原文件
        test_backup_with_removal()
        list_backup_status()
        
        print("\n" + "="*50 + "\n")
        
        # 测试2: 备份但保留原文件
        test_backup_without_removal()
        list_backup_status()
        
        logger.info("=== 备份功能测试完成 ===")
        logger.info("请检查 ./log_backups/ 目录查看备份结果")
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}", exc_info=True)

if __name__ == "__main__":
    main()