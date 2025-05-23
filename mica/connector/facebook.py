import os
import aiohttp
from fastapi import HTTPException
from mica.utils import logger
## TODO page access token
facebookToken ="facebook_token"
async def send_to_facebook(receiver: str, messages: list, bot: str):
    """发送消息到Facebook Messenger API"""
    # 从环境变量或配置中获取Facebook访问令牌
    facebook_token = facebookToken
    if not facebook_token:
        logger.error("Facebook page token not configured")
        return

    # 检查messages是否为None或空
    if not messages:
        logger.error(f"[{receiver}] No messages to send")
        return

    url = "https://graph.facebook.com/v21.0/me/messages"
    headers = {
        "Authorization": f"Bearer {facebook_token}",
        "Content-Type": "application/json"
    }

    # 合并所有文本消息
    combined_text = " ".join(msg.get("text", "") for msg in messages if msg.get("text"))
    
    # 如果没有有效的文本消息，返回默认消息
    if not combined_text:
        combined_text = "I'm sorry, I couldn't process your request properly."

    data = {
        "recipient": {"id": receiver},
        "message": {"text": combined_text}
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                result = await response.json()
                logger.info(f"[{receiver}][send to facebook user with result:{result}]")
                return result
    except Exception as e:
        logger.error(f"Error sending message to Facebook: {str(e)}")
        return None

async def verify_facebook_webhook(bot, request):
    """验证Facebook webhook"""
    # 获取查询参数
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    logger.info(f"verify facebook webhook with token: {verify_token} and challenge: {challenge}")
    # 从配置中获取Facebook验证token TODO
    facebook_verify_token = os.getenv("FACEBOOK_VERIFY_TOKEN", "")

    # 验证token
    if not verify_token or verify_token != facebook_verify_token:
        logger.error(f"invalid facebook verify token: {verify_token}")
        raise HTTPException(status_code=400, detail="Invalid verify token")

    # 返回challenge参数
    return int(challenge)

async def handle_facebook_webhook(body, bot, manager):
    """处理Facebook webhook消息"""
    # 验证这是一个页面消息事件
    if body.get("object") != "page":
        raise HTTPException(status_code=400, detail="Invalid request")
    logger.info(f"[{bot}][handle facebook webhook:{body}]")
    try:
        # 处理每个消息入口
        for entry in body.get("entry", []):
            # 处理每个消息
            for messaging in entry.get("messaging", []):
                sender_id = messaging.get("sender", {}).get("id")
                recipient_id = messaging.get("recipient", {}).get("id")

                # 获取消息内容
                message = messaging.get("message", {})
                if message:
                    text = message.get("text", "")
                    if text:
                        logger.info(f"[{bot}][handle facebook webhook with {sender_id}]:{text}")

                        # 使用manager处理消息
                        response = await manager.chat(bot, sender_id, text)
                        logger.info(f"[{bot}][handle facebook webhook with mica res:{response}]")
                        # 发送响应回Facebook
                        await send_to_facebook(sender_id, response, bot)

        # Facebook要求返回200 OK
        return "OK"
    except Exception as e:
        logger.error(f"Error handling Facebook webhook: {str(e)}")
        return None