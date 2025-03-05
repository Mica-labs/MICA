import json
import os
from typing import Any, Optional, Dict, Text, List

import requests as requests
import asyncio
import httpx

from mica.constants import OPENAI_API_KEY
from mica.event import BotUtter, SetSlot, AgentComplete, AgentFail, FunctionCall
from mica.llm.base import BaseModel
from mica.llm.constants import OPENAI_CHAT_URL
from mica.tracker import Tracker
from mica.utils import logger


class NoValidRequestHeader(Exception):
    """Exception that can be raised when valid request headers are not provided."""


class OpenAIModel(BaseModel):
    def __init__(self,
                 model: Optional[Text] = "gpt-4",
                 temperature: Optional[float] = 0.2,
                 top_p: Optional[float] = 0.8,
                 presence_penalty: Optional[float] = 0.1,
                 frequency_penalty: Optional[float] = 0.1,
                 max_tokens: Optional[int] = 512,
                 headers: Optional[Any] = None,
                 server: Optional[Text] = None,
                 api_key: Optional[Text] = None,
                 max_concurrent_requests: int = 5):
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty
        self.max_tokens = max_tokens
        self.server = server or OPENAI_CHAT_URL
        self.headers = headers or {}
        self.client = httpx.AsyncClient(timeout=10)

        if headers is None:
            if api_key is None:
                api_key = os.getenv(OPENAI_API_KEY)
            if api_key is None:
                raise NoValidRequestHeader()
            self.headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"}

    @classmethod
    def create(cls, llm_config: Optional[Dict] = None):
        if llm_config is not None:
            return cls(**llm_config)
        return cls()

    async def generate_message(self, prompts: Any,
                         tracker: Optional[Tracker] = None,
                         functions: Optional[Any] = None,
                         provider: Optional[Text] = None,
                         **kwargs: Any
                         ) -> List:
        formatted_prompts = self._generate_prompts(prompts, functions)
        llm_result = []

        logger.debug(f"url: {self.server}, headers: {self.headers}")
        response = await self.client.post(self.server, headers=self.headers, json=formatted_prompts)
        logger.debug("GPT response status: %s", response.status_code)
        if response.status_code == 200:
            response_json = response.json()
            if response_json is not None \
                    and response_json.get("choices") is not None \
                    and len(response_json.get("choices")) > 0:
                message: Dict = response_json.get("choices")[0].get("message")
                logger.debug("GPT message: \n%s", json.dumps(message, indent=2, ensure_ascii=False))
                if message.get("content") is not None:
                    next_response_text = message.get("content")
                    llm_result.append(BotUtter(text=next_response_text, metadata=provider, additional=message))

                if message.get("tool_calls") is not None:
                    for func in message["tool_calls"]:
                        func_details = func["function"]
                        name = func_details.get("name")
                        args = json.loads(func_details.get("arguments"))
                        call_id = func.get("id")
                        # if func.get("name") == "extract_data":
                        #     args = json.loads(func.get("arguments"))
                        #     next_response_text = args.get("next_response")
                        #     llm_result.append(BotUtter(text=next_response_text, metadata=provider, additional=message))
                        #
                        #     for arg_name, arg_value in args.items():
                        #         if arg_name in ["next_response", "is_complete"]:
                        #             continue
                        #         llm_result.append(SetSlot(slot_name=arg_name, value=arg_value))
                        #     is_complete = args.get("is_complete")
                        #     if is_complete:
                        #         llm_result.append(AgentComplete(provider=provider))
                        # if func.get("name") == "conversation_complete":
                        #     llm_result.append(AgentComplete(provider=provider))
                        # if func.get("name") == "conversation_exception":
                        #     llm_result.append(AgentFail(provider=provider))
                        llm_result.append(FunctionCall(function_name=name,
                                                       args=args,
                                                       call_id=call_id,
                                                       metadata=message))
        else:
            logger.error("GPT request fail, respond: %s", response.text)
        return llm_result

    def _generate_prompts(self, prompts: Any, functions: Optional[List] = None):
        data = {
            "model": self.model,
            "messages": prompts,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "presence_penalty": self.presence_penalty,
            "frequency_penalty": self.frequency_penalty,
            "max_tokens": self.max_tokens,
        }
        if functions is not None and len(functions) > 0:
            tools = []
            for function in functions:
                tools.append({
                    "type": "function",
                    "function": function
                })
            data["tools"] = tools
            data["tool_choice"] = "auto"

        return data
