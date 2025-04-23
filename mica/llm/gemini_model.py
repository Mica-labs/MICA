import json
import os
from typing import Any, Optional, Dict, Text, List

import requests as requests
import asyncio
import httpx

from mica.constants import GEMINI_API_KEY
from mica.llm.base import BaseModel
from mica.llm.constants import GEMINI_URL
from mica.tracker import Tracker


class NoValidRequestHeader(Exception):
    """Exception that can be raised when valid request headers are not provided."""


class GeminiModel(BaseModel):
    def __init__(
        self,
        model: Optional[Text] = "gemini-2.0-flash",
        temperature: Optional[float] = 0.2,
        top_p: Optional[float] = 0.8,
        presence_penalty: Optional[float] = 0.1,
        frequency_penalty: Optional[float] = 0.1,
        max_tokens: Optional[int] = 512,
        headers: Optional[Any] = None,
        server: Optional[Text] = None,
        api_key: Optional[Text] = None,
        max_concurrent_requests: int = 5,
    ):
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty
        self.max_tokens = max_tokens
        self.server = server or GEMINI_URL
        self.headers = headers or {}
        self.client = httpx.AsyncClient(timeout=10)

        if headers is None:
            if api_key is None:
                api_key = os.getenv("GEMINI_API_KEY")
            if api_key is None:
                raise NoValidRequestHeader()
            self.headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

    @classmethod
    def create(cls, llm_config: Optional[Dict] = None):
        if llm_config is not None:
            return cls(**llm_config)
        return cls()

    def generate_message(
        self,
        prompts: Any,
        tracker: Optional[Tracker] = None,
        **kwargs: Any,
    ):
        pass
