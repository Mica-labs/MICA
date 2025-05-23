import os
import aiohttp
from fastapi import HTTPException
from mica.utils import logger

async def send_to_slack(messages: list, bot: str):
   combined_text = " ".join(msg.get("text", "") for msg in messages if msg.get("text"))

   # 如果没有有效的文本消息，返回默认消息
   if not combined_text:
       combined_text = "I'm sorry, I couldn't process your request properly."

   data = {"text": combined_text}

   # 从环境变量或配置中获取URL TODO
#    url = os.getenv("SLACK_WEBHOOK_URL")
   url = "slack_imcoming_url"
   if not url:
       logger.error(f"[{bot}][Slack webhook URL not configured]")
       return None

   headers = {"Content-Type": "application/json"}
   
   try:
      async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            result = await response.text()
            logger.info(f"[{bot}][send to slack user with result:{result}]")
            return result
   except Exception as e:
       logger.error(f"Error sending message to Slack: {str(e)}")
       return None

async def handle_slack_webhook(request, bot, manager):
    # 如果是重试请求，则忽略
    if request.headers.get("X-Slack-Retry-Num"):
        logger.warning(f"[{bot}][Slack retry detected, ignoring]: {request.headers}")
        return "ok"
    body = await request.json()

    """处理Slack webhook消息"""
    if not body:
        return "ok"
    logger.info(f"[handle slack webhook:{body}]")
    # 验证回调地址
    if body.get("type") == "url_verification":
        logger.info(f"[{bot}][handle slack verify webhook:{body}]")
        return body.get("challenge")

    event = body.get("event")
    if not event:
        logger.error(f"[{bot}][No event in webhook body]")
        return "ok"

    subtype = event.get("subtype")
    # bot 发送的消息，不处理
    if subtype:
        logger.info(f"[{bot}][ignore slack bot msg]")
        return "ok"

    sender_id = event.get("user")
    text = event.get("text")

    try:
        # 处理每个消息入口
        if text and sender_id:
            logger.info(f"[{bot}][handle slack webhook with {sender_id}]:{text}")

            # 使用manager处理消息
            response = await manager.chat(bot, sender_id, text)
            logger.info(f"[{bot}][handle slack webhook with mica res:{response}]")
            # 发送响应回slack
            await send_to_slack(response, bot)
            return "ok"
        return "ok"
    except Exception as e:
        logger.error(f"Error handling Slack webhook: {str(e)}")
        return "ok"