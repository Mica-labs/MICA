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

    async def chat(self, bot_name: Text, user_id: Text, message: Text, channel: Optional[ChatChannel] = None):
        if self.bots.get(bot_name) is None:
            return
        bot_responses = await self.bots[bot_name].handle_message(user_id, message)
        final_response = [{"text": res} for res in bot_responses]
        if channel is not None:
            print(bot_responses)
            await channel.send_message(bot_responses)
        return final_response

    def load(self, bot_name: Text, data: Any, config: Any, python_script: Text = None):
        try:
            validator = Validator()
            validate_result = validator.validate(data)
            assert validate_result == []
            parsed_data = parser.parse_agents(data)
            self.bots[bot_name] = Bot.from_json(bot_name, parsed_data, config, python_script)
            return True
        except AssertionError as e:
            msgs = [f"Error Type: {err.rule_name}, Message: {err.message}" for err in validate_result]
            msgs_str = '\n'.join(msgs)
            logger.error(f"Did not pass the validation. "
                         f"Identified the following potential issues: {msgs_str}")

    # @classmethod
    # def load(cls, path: Text,
    #          bots: Optional[Dict[Text, Bot]] = None
    #          ) -> Manager:
    #     return Manager(bots)