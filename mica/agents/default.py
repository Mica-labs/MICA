import asyncio
import json
import threading
import time
from typing import Optional, Text, Dict, Any, List

from mica.agents.llm_agent import LLMAgent
from mica.event import BotUtter, Event
from mica.llm.openai_model import OpenAIModel
from mica.tracker import Tracker
from mica.utils import logger

RETRY_COUNT = '_retry_count'

# TODO: analyze policy, from natural language transfer to parameters here
class DefaultFallbackAgent(LLMAgent):
    def __init__(self,
                 name: Optional[Text] = None,
                 description: Optional[Text] = None,
                 config: Optional[Dict[Text, Any]] = None,
                 prompt: Optional[Text] = None,
                 args: Optional[List[Any]] = None,
                 uses: Optional[List[Any]] = None,
                 llm_model: Optional[Any] = None,
                 **kwargs
                 ):
        self.llm_model = llm_model or OpenAIModel.create(config)
        self.prompt = prompt
        self.args = args
        self.uses = uses
        super().__init__(name, description, config, prompt, args, uses, llm_model)

    @classmethod
    def create(cls,
               config: Optional[Dict[Text, Any]] = None,
               llm_model: Optional[Any] = None,
               prompt: Optional[Text] = None,
               **kwargs
               ):
        if kwargs.get("server") and kwargs.get("headers"):
            if config is None:
                config = {}
            config["server"] = kwargs.get("server") + "/rpc/rasa/message"
            config["headers"] = kwargs.get("headers")
        name = "DefaultFallbackAgent"
        description = "This agent can generate a default fallback response."
        return cls(name, description, config=config, llm_model=llm_model, prompt=prompt)

    def _generate_agent_prompt(self, tracker: Tracker, is_tool=False):
        prompt = [{'role': 'system',
                   'content': 'You are an intelligent chatbot. '
                              'Please generate a bot response according to the conversation I provide. '
                              'What you generate is that you cannot understand. For example, you can say: '
                              "\"I'm sorry, I didn't understand that. Can you please rephrase?\""},
                  {'role': 'user',
                   'content': f"Conversation: \n"
                              f"{tracker.get_history_str()}\n"
                              f"Bot: "}]
        return prompt

    async def run(self, tracker: Tracker, is_tool=False, **kwargs):
        # directly output self.prompt content
        if self.prompt is not None:
            return True, [BotUtter(text=self.prompt, provider=self.name)]
        prompt = self._generate_agent_prompt(tracker)
        logger.debug("Default fallback agent prompt: \n%s", json.dumps(prompt, indent=2, ensure_ascii=False))
        llm_result = await self.llm_model.generate_message(prompt, tracker=tracker,
                                                           provider=self.name)
        is_end = True
        final_result = []
        for event in llm_result:
            if isinstance(event, BotUtter):
                final_result.append(event)

        return is_end, final_result


class DefaultExitAgent(LLMAgent):
    def __init__(self,
                 name: Optional[Text] = None,
                 description: Optional[Text] = None,
                 config: Optional[Dict[Text, Any]] = None,
                 prompt: Optional[Text] = None,
                 args: Optional[List[Any]] = None,
                 uses: Optional[List[Any]] = None,
                 llm_model: Optional[Any] = None,
                 timeout: Optional[Any] = 5,
                 retry: Optional[Any] = 3,
                 retry_response: Optional[Text] = None,
                 exit_response: Optional[Text] = None,
                 **kwargs
                 ):
        self.llm_model = llm_model or OpenAIModel.create(config)
        self.prompt = prompt
        self.args = args
        self.run_flag = False
        self.timeout = timeout
        self.retry = retry
        self.retry_response = retry_response or "Do you have any other question?"
        self.exit_response = exit_response or "Goodbye!"
        super().__init__(name, description, config, prompt, args, uses, llm_model)

    @classmethod
    def create(cls,
               config: Optional[Dict[Text, Any]] = None,
               prompt: Optional[Text] = None,
               args: Optional[List[Any]] = None,
               uses: Optional[List[Text]] = None,
               llm_model: Optional[Any] = None,
               **kwargs
               ):
        if kwargs.get("server") and kwargs.get("headers"):
            if config is None:
                config = {}
            config["server"] = kwargs.get("server") + "/rpc/rasa/message"
            config["headers"] = kwargs.get("headers")
        name = "DefaultExitAgent"
        description = "This agent can generate a default exit response."
        return cls(name, description, config, prompt, args, uses, llm_model)

    async def check_user_timeout(self, tracker: Tracker) -> bool:
        current_time = time.time()
        latest_event = tracker.events[-1]
        retry_count, _ = tracker.get_arg(self.name, RETRY_COUNT)
        if retry_count > self.retry:
            return True
        if current_time - latest_event.timestamp > self.timeout:
            tracker.set_arg(self.name, RETRY_COUNT, retry_count+1)
            if retry_count + 1 < self.retry:
                try:
                    tracker.update(BotUtter(self.retry_response))
                    print(BotUtter(self.retry_response))
                    output_channel = tracker.latest_message.metadata
                    await output_channel.send_message(self.retry_response)
                    # await state.client.send_message("您是否还有其他问题")
                    return False
                except ValueError as e:
                    logger.error("Exit agent cannot output timeout message")
            else:
                tracker.update(BotUtter(self.exit_response))
                print(BotUtter(self.exit_response))
                return True
        return False

    async def monitor_user(self, tracker: Tracker):
        while True:
            await asyncio.sleep(1)
            is_exit = await self.check_user_timeout(tracker)
            if is_exit:
                break

    async def run(self, tracker: Tracker, is_tool=False, **kwargs):
        tracker.set_arg(self.name, '_retry_count', 0)
        asyncio.create_task(self.monitor_user(tracker))

        return True, []