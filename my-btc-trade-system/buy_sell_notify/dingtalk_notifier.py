import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
import logging

import config

def send_dingtalk_markdown(title: str, markdown_text: str):
    """
    发送Markdown格式的消息到钉钉机器人。
    兼容“加签”和“自定义关键词/IP”两种安全设置。
    """
    logger = logging.getLogger("DingTalkNotifier")
    
    webhook_url = getattr(config, 'DINGTALK_WEBHOOK', None)
    secret = getattr(config, 'DINGTALK_SECRET', None)

    # 检查 webhook_url 是否有效配置
    if not webhook_url or "YOUR_WEBHOOK_URL" in webhook_url:
        logger.info("钉钉机器人的 DINGTALK_WEBHOOK 未配置或未修改，跳过发送。")
        return

    final_url = webhook_url

    
    # --- 智能判断：如果提供了secret，则进行签名计算 ---
    if secret:
        logger.debug("检测到钉钉Secret，将使用加签模式发送。")
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode('utf-8')
        string_to_sign = f'{timestamp}\n{secret}'
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        final_url = f'{webhook_url}&timestamp={timestamp}&sign={sign}'
    else:
        logger.debug("未检测到钉钉Secret，将使用普通模式发送。")

    try:
        # 检查消息大小，钉钉限制20000字节
        message_size = len(markdown_text.encode('utf-8'))
        if message_size > 19000:  # 留1000字节缓冲
            logger.warning(f"消息过大 ({message_size} bytes)，将截断处理")
            # 截断消息并添加提示
            max_chars = 19000 // 3  # 粗略估算，UTF-8中文字符约3字节
            markdown_text = markdown_text[:max_chars] + "\n\n⚠️ 消息过长已截断，完整信息请查看系统日志"
        
        # 准备请求数据 (这部分对于两种模式是相同的)
        headers = {'Content-Type': 'application/json'}
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": markdown_text
            }
        }

        # 发送HTTP POST请求
        response = requests.post(final_url, json=payload, headers=headers, timeout=15)
        response.raise_for_status() # 如果请求失败 (非2xx状态码)，则抛出异常

        result = response.json()
        if result.get("errcode") == 0:
            logger.info(f"成功发送钉钉通知，标题: '{title}' (大小: {message_size} bytes)")
        else:
            logger.error(f"发送钉钉通知失败: {result}, payload:{payload}")
            # 如果是消息过大错误，尝试发送超精简版本
            if result.get("errcode") == 460101:
                logger.warning("消息过大，尝试发送超精简版本")
                simple_payload = {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": title,
                        "text": f"### {title}\n\n⚠️ 原消息过大，请查看系统日志获取详细信息\n\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                }
                fallback_response = requests.post(final_url, json=simple_payload, headers=headers, timeout=15)
                fallback_result = fallback_response.json()
                if fallback_result.get("errcode") == 0:
                    logger.info("超精简版本发送成功")
                else:
                    logger.error(f"超精简版本也发送失败: {fallback_result}")

    except requests.exceptions.RequestException as e:
        logger.error(f"发送钉钉通知时发生网络错误: {e}")
    except Exception as e:
        logger.error(f"发送钉钉通知时发生未知错误: {e}", exc_info=True)