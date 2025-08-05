#!/usr/bin/env python3
"""
日志备份脚本
在Docker容器重启前自动备份现有日志文件
"""

import os
import shutil
import datetime
from pathlib import Path
import logging
import config

def setup_backup_logger():
    """设置备份专用日志器"""
    logger = logging.getLogger("LogBackup")
    if logger.handlers:
        return logger
    
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

def backup_logs():
    """
    备份日志文件到备份目录
    """
    logger = setup_backup_logger()
    
    try:
        # 获取配置
        log_dir = Path(config.LOG_CONFIG["log_dir"])
        
        # 创建备份目录结构
        backup_base_dir = Path("./log_backups")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = backup_base_dir / f"backup_{timestamp}"
        
        # 确保目录存在
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"开始备份日志文件到: {backup_dir}")
        
        # 检查日志目录是否存在
        if not log_dir.exists():
            logger.warning(f"日志目录不存在: {log_dir}")
            return False
        
        # 备份所有日志文件
        backup_count = 0
        total_size = 0
        
        for log_file in log_dir.glob("*.log*"):
            if log_file.is_file():
                dest_file = backup_dir / log_file.name
                try:
                    shutil.copy2(log_file, dest_file)
                    file_size = log_file.stat().st_size
                    total_size += file_size
                    backup_count += 1
                    logger.info(f"已备份: {log_file.name} ({file_size:,} bytes)")
                except Exception as e:
                    logger.error(f"备份文件 {log_file.name} 失败: {e}")
        
        if backup_count > 0:
            logger.info(f"备份完成! 共备份 {backup_count} 个文件，总大小: {total_size:,} bytes")
            
            # 创建备份信息文件
            info_file = backup_dir / "backup_info.txt"
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(f"备份时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"备份文件数量: {backup_count}\n")
                f.write(f"总大小: {total_size:,} bytes\n")
                f.write(f"原始日志目录: {log_dir.absolute()}\n")
                f.write("\n备份的文件列表:\n")
                for log_file in backup_dir.glob("*.log*"):
                    if log_file.name != "backup_info.txt":
                        size = log_file.stat().st_size
                        f.write(f"- {log_file.name} ({size:,} bytes)\n")
            
            return True
        else:
            logger.info("没有找到需要备份的日志文件")
            # 删除空的备份目录
            backup_dir.rmdir()
            return False
            
    except Exception as e:
        logger.error(f"备份过程中发生错误: {e}")
        return False

def cleanup_old_backups(keep_days=30):
    """
    清理旧的备份文件
    
    Args:
        keep_days: 保留最近多少天的备份，默认30天
    """
    logger = setup_backup_logger()
    
    try:
        backup_base_dir = Path("./log_backups")
        if not backup_base_dir.exists():
            return
        
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=keep_days)
        deleted_count = 0
        total_freed_size = 0
        
        for backup_dir in backup_base_dir.iterdir():
            if backup_dir.is_dir() and backup_dir.name.startswith("backup_"):
                try:
                    # 从目录名提取时间戳
                    timestamp_str = backup_dir.name.replace("backup_", "")
                    backup_date = datetime.datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    if backup_date < cutoff_date:
                        # 计算目录大小
                        dir_size = sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file())
                        
                        # 删除旧备份
                        shutil.rmtree(backup_dir)
                        deleted_count += 1
                        total_freed_size += dir_size
                        logger.info(f"已删除旧备份: {backup_dir.name} (释放 {dir_size:,} bytes)")
                        
                except (ValueError, OSError) as e:
                    logger.warning(f"处理备份目录 {backup_dir.name} 时出错: {e}")
        
        if deleted_count > 0:
            logger.info(f"清理完成! 删除了 {deleted_count} 个旧备份，释放空间: {total_freed_size:,} bytes")
        else:
            logger.info("没有找到需要清理的旧备份")
            
    except Exception as e:
        logger.error(f"清理旧备份时发生错误: {e}")

def main():
    """主函数"""
    logger = setup_backup_logger()
    logger.info("=== 开始执行日志备份任务 ===")
    
    # 执行备份
    backup_success = backup_logs()
    
    # 清理旧备份
    cleanup_old_backups(keep_days=30)
    
    logger.info("=== 日志备份任务完成 ===")
    return backup_success

if __name__ == "__main__":
    main()