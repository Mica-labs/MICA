import os
import aiohttp
from fastapi import HTTPException
from mica.utils import logger


async def send_to_facebook(receiver: str, messages: list, bot: str, page_access_token: str):
    if not messages:
        logger.error(f"[{bot}:{receiver}][No messages were send to facebook]")
        return

    url = "https://graph.facebook.com/v21.0/me/messages"
    headers = {
        "Authorization": f"Bearer {page_access_token}",
        "Content-Type": "application/json"
    }

    combined_text = " ".join(msg.get("text", "") for msg in messages if msg.get("text"))
    
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
                logger.info(f"[{bot}:{receiver}][send to facebook user with result:{result}]")
                return result
    except Exception as e:
        logger.error(f"[{bot}:{receiver}][Error sending message to Facebook: {str(e)}]")
        return None

async def verify_facebook_webhook(request, bot, manager):
    """verify Facebook webhook"""

    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    logger.info(f"[{bot}][verify facebook webhook with token: {verify_token} and challenge: {challenge}]")

    facebook_verify_token = manager.get_credential_info(bot,"facebook.verify_token")
    if not facebook_verify_token:
      logger.error("[{bot}][Facebook verify token not configured]")
      raise HTTPException(status_code=400, detail="Facebook verify token not configured")

    # verify token
    if not verify_token or verify_token != facebook_verify_token:
      logger.error(f"[{bot}][invalid facebook verify token: {verify_token}]")
      raise HTTPException(status_code=400, detail="Invalid verify token")

    # return challenge
    return int(challenge)

async def handle_facebook_webhook(body, bot, manager):
    """start handle facebook message"""

    if body.get("object") != "page":
        raise HTTPException(status_code=400, detail="Invalid request")

    logger.info(f"[{bot}][handle facebook webhook:{body}]")

    page_access_token  = manager.get_credential_info(bot,"facebook.page_access_token")
    if not page_access_token:
        logger.error("[{bot}:{receiver}][Facebook page_access_token not configured]")
        return None

    try:
        for entry in body.get("entry", []):
            for messaging in entry.get("messaging", []):
                sender_id = messaging.get("sender", {}).get("id")
                recipient_id = messaging.get("recipient", {}).get("id")

                message = messaging.get("message", {})
                if message:
                    text = message.get("text", "")
                    if text:
                        logger.info(f"[{bot}:{sender_id}][handle facebook webhook with {sender_id}]:{text}")

                        response = await manager.chat(bot, sender_id, text)
                        logger.info(f"[{bot}:{sender_id}][handle facebook webhook with mica res:{response}]")

                        await send_to_facebook(sender_id, response, bot, page_access_token)
        return "OK"
    except Exception as e:
        logger.error(f"Error handling Facebook webhook: {str(e)}")
        return None