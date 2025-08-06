"""
通知系统模块
提供各种通知渠道的实现
"""

from .dingtalk import DingTalkNotifier

__all__ = [
    'DingTalkNotifier'
]