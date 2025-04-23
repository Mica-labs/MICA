import json
import os
from typing import Any, Optional, Dict, Text, List

import requests as requests
import asyncio
import httpx

from mica.constants import API_KEY
from mica.event import BotUtter, SetSlot, AgentComplete, AgentFail, FunctionCall
from mica.llm.base import BaseModel
from mica.llm.constants import CHAT_URL
from mica.tracker import Tracker
from mica.utils import logger


class NoValidApiUrl(Exception):
    """Exception that can be raised when there is no valid api url provided"""


class NoValidRequestHeader(Exception):
    """Exception that can be raised when valid request headers are not provided."""


class AnthropicModel(BaseModel):
    def __init__(
        self,
        model: Optional[Text] = None,
        anthropic_version: Optional[Text] = None,
        temperature: Optional[float] = 0.2,
        top_p: Optional[float] = 0.8,
        top_k: Optional[float] = 0.8,
        max_tokens: Optional[int] = 512,
        headers: Optional[Any] = None,
        server: Optional[Text] = None,
        api_key: Optional[Text] = None,
        max_concurrent_requests: int = 5,
    ):
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.max_tokens = max_tokens
        self.headers = headers or {}
        self.client = httpx.AsyncClient(timeout=10)

        self.server = server
        if self.server is None:
            raise NoValidApiUrl()

        if headers is None:
            if api_key is None:
                api_key = os.getenv(API_KEY)
            if api_key is None:
                raise NoValidRequestHeader()

            self.headers = {
                "content-type": "application/json",
                "anthropic-version": f"{anthropic_version}",
                "x-api-key": f"{api_key}",
            }

    @classmethod
    def create(cls, llm_config: Optional[Dict] = None):
        if llm_config is not None:
            return cls(**llm_config)
        return cls()

    async def generate_message(
        self,
        prompts: Any,
        tracker: Optional[Tracker] = None,
        functions: Optional[Any] = None,
        provider: Optional[Text] = None,
        **kwargs: Any,
    ) -> List:
        formatted_prompts = self._generate_prompts(prompts, functions)
        print("Prompts: ", json.dumps(formatted_prompts, indent=4))
        llm_result = []

        logger.debug(
            f"url: {self.server}, headers: {self.headers}, data: {formatted_prompts}"
        )
        response = await self.client.post(
            self.server, headers=self.headers, json=formatted_prompts
        )
        logger.debug("GPT response status: %s", response.status_code)
        if response.status_code == 200:
            response_json = response.json()
            print("Response: ", json.dumps(response_json, indent=4))
            # print("Response: ", response_json)
            if (
                response_json is not None
                and response_json.get("content") is not None
                and len(response_json.get("content")) > 0
            ):
                message = next(
                    (
                        msg
                        for msg in response_json.get("content", [])
                        if msg.get("type") == "text"
                    ),
                    None,
                )
                # message: Dict = response_json.get("content")[0]
                logger.debug(
                    "GPT message: \n%s",
                    json.dumps(message, indent=2, ensure_ascii=False),
                )
                if message.get("text") is not None:
                    next_response_text = message.get("text")
                    llm_result.append(
                        BotUtter(
                            text=next_response_text,
                            metadata=provider,
                            additional=message,
                        )
                    )
                tool_use = []
                for item in response_json.get("content"):
                    if item.get("type") == "tool_use":
                        tool_use.append(item)
                # print("Tools: ", tool_use)
                if tool_use is not None:
                    for func in tool_use:
                        name = func.get("name")
                        args = json.loads(func.get("input"))
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
                        llm_result.append(
                            FunctionCall(
                                function_name=name,
                                args=args,
                                call_id=call_id,
                                metadata=message,
                            )
                        )
        else:
            logger.error("GPT request fail, respond: %s", response.text)
        return llm_result

    def _generate_prompts(self, prompts: Any, functions: Optional[List] = None):
        data = {
            "model": self.model,
            "messages": prompts,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
        }
        data["system"] = prompts[0]["content"]
        data["messages"].pop(0)
        if functions is not None and len(functions) > 0:
            tools = []
            for function in functions:
                # print("Function: ", json.dumps(function, indent=4))
                tools.append(
                    {
                        "name": function.get("name"),
                        "input_schema": {
                            "type": function.get("parameters").get("type"),
                            "properties": function.get("parameters").get("properties"),
                            "required": function.get("parameters").get("required"),
                        },
                    }
                )
                # tools.append({"type": "function", "function": function})
            data["tools"] = tools
            data["tool_choice"] = {"type": "auto"}

        return data
