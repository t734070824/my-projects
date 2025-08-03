
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

    :param title: 消息标题，会显示在通知列表。
    :param markdown_text: Markdown格式的消息内容。
    """
    logger = logging.getLogger("DingTalkNotifier")
    
    webhook_url = getattr(config, 'DINGTALK_WEBHOOK', None)
    secret = getattr(config, 'DINGTALK_SECRET', None)

    if not (webhook_url and secret and "YOUR_WEBHOOK_URL" not in webhook_url):
        logger.info("钉钉机器人的配置不完整或未修改，跳过发送。")
        return

    try:
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode('utf-8')
        string_to_sign = f'{timestamp}\n{secret}'
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

        final_url = f'{webhook_url}&timestamp={timestamp}&sign={sign}'
        headers = {'Content-Type': 'application/json'}
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": markdown_text
            }
        }

        response = requests.post(final_url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()

        result = response.json()
        if result.get("errcode") == 0:
            logger.info(f"成功发送钉钉通知，标题: '{title}'")
        else:
            logger.error(f"发送钉钉通知失败: {result}")

    except requests.exceptions.RequestException as e:
        logger.error(f"发送钉钉通知时发生网络错误: {e}")
    except Exception as e:
        logger.error(f"发送钉钉通知时发生未知错误: {e}", exc_info=True)
