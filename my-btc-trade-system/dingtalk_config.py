# 钉钉机器人配置文件
# 请将此文件重命名为 dingtalk_config.py 并填入真实配置

# 钉钉机器人Webhook地址
# 获取方式：
# 1. 在钉钉群聊中添加"自定义机器人"
# 2. 选择"自定义关键词"安全设置，添加关键词如"交易提醒"
# 3. 复制生成的Webhook地址到下方
DINGTALK_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=f039bbc0bc60ddc6ef65edb56505af5aa16e057e1e295a6bfd8835f57858f82e"

# 是否启用钉钉通知
ENABLE_DINGTALK_NOTIFICATION = True

# 使用说明：
# 1. 将YOUR_ACCESS_TOKEN替换为实际的access_token
# 2. 确保机器人安全设置中包含"交易提醒"关键词
# 3. 将ENABLE_DINGTALK_NOTIFICATION设置为True启用通知 