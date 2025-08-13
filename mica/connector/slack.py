import os
import aiohttp
from fastapi import HTTPException
from mica.utils import logger

async def send_to_slack(messages: list, bot: str, slack_incoming_webhook: str):
   combined_text = " ".join(msg.get("text", "") for msg in messages if msg.get("text"))

   if not combined_text:
       combined_text = "I'm sorry, I couldn't process your request properly."

   data = {"text": combined_text}

   if not slack_incoming_webhook:
       logger.error(f"[{bot}][Slack webhook URL not configured]")
       return None

   headers = {"Content-Type": "application/json"}

   try:
      async with aiohttp.ClientSession() as session:
        async with session.post(slack_incoming_webhook, headers=headers, json=data) as response:
            result = await response.text()
            logger.info(f"[{bot}][send to slack user with result:{result}]")
            return result
   except Exception as e:
       logger.error(f"Error sending message to Slack: {str(e)}")
       return None

async def handle_slack_webhook(request, bot, manager):
    # ignore retry message
    if request.headers.get("X-Slack-Retry-Num"):
        logger.warning(f"[{bot}][Slack retry detected, ignoring]: {request.headers}")
        return "ok"
    body = await request.json()

    """start handle slack message"""
    if not body:
        return "ok"
    logger.info(f"[handle slack webhook:{body}]")
    # verify webhook url
    if body.get("type") == "url_verification":
        logger.info(f"[{bot}][handle slack verify webhook:{body}]")
        return body.get("challenge")

    event = body.get("event")
    if not event:
        logger.error(f"[{bot}][No event in webhook body]")
        return "ok"

    subtype = event.get("subtype")

    # this message comes for bot, just ignore it
    if subtype:
        logger.info(f"[{bot}][ignore slack bot msg]")
        return "ok"

    sender_id = event.get("user")
    text = event.get("text")

    slack_incoming_webhook = manager.slack_incoming_webhook(bot)
    if not slack_incoming_webhook:
        logger.error(f"[{bot}][Slack incoming URL not configured]")
        return "ok"

    try:
        if text and sender_id:
            logger.info(f"[{bot}][handle slack webhook with {sender_id}]:{text}")

            response = await manager.chat(bot, sender_id, text)
            logger.info(f"[{bot}][handle slack webhook with mica response:{response}]")

            await send_to_slack(response, bot, slack_incoming_webhook)
            return "ok"
        return "ok"
    except Exception as e:
        logger.error(f"Error handling Slack webhook: {str(e)}")
        return "ok"