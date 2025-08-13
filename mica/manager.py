from typing import Optional, Dict, Text, Any

from mica import parser
from mica.bot import Bot
from mica.channel import ChatChannel
from mica.parser import Validator
from mica.utils import logger


class Manager:
    def __init__(self,
                 bots: Optional[Dict[Text, Bot]] = None
                 ):
        self.bots = bots or {}
    
    def get_bot(self, bot_name: Text) -> Optional[Bot]:
        return self.bots.get(bot_name)

    async def chat(self, bot_name: Text, user_id: Text, message: Text, channel: Optional[ChatChannel] = None):
        if self.bots.get(bot_name) is None:
            return
        bot_responses = await self.bots[bot_name].handle_message(user_id, message)
        final_response = [{"text": res} for res in bot_responses]
        if channel is not None:
            print(bot_responses)
            await channel.send_message(bot_responses)
        return final_response

    def load(self,
             bot_name: Text,
             data: Any,
             llm_config: Optional[Dict] = None,
             python_script: Optional[Text] = None,
             connector: Optional[Dict] = None):
        try:
            validator = Validator()
            validate_result = validator.validate(data)
            assert validate_result == []
            parsed_data = parser.parse_agents(data)
            self.bots[bot_name] = Bot.from_json(name=bot_name,
                                                data=parsed_data,
                                                config=llm_config,
                                                tool_code=python_script,
                                                connector=connector)
            return True
        except AssertionError as e:
            msgs = [f"Error Type: {err.rule_name}, Message: {err.message}" for err in validate_result]
            msgs_str = '\n'.join(msgs)
            logger.error(f"Did not pass the validation. "
                         f"Identified the following potential issues: {msgs_str}")
            raise Exception(msgs_str)

    def get_credential_info(self, bot_name, key):
        if self.bots.get(bot_name) is None:
            return
        return self.bots.get(bot_name).connector.get(key)

    def slack_incoming_webhook(self, bot_name):
        slack = self.get_credential_info(bot_name, "slack")
        if slack is None:
             return None
        return slack.get('incoming_webhook')

    def facebook_secret(self, bot_name):
        facebook = self.get_credential_info(bot_name, "facebook")
        if facebook is None:
            return None
        return facebook.get('secret')

    def facebook_verify_token(self, bot_name):
        facebook = self.get_credential_info(bot_name, "facebook")
        if facebook is None:
            return None
        return facebook.get('verify_token')

    def facebook_page_access_token(self, bot_name):
        facebook = self.get_credential_info(bot_name, "facebook")
        if facebook is None:
            return None
        return facebook.get('page_access_token')