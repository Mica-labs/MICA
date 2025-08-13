from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Text

from starlette.websockets import WebSocket


class ChatChannel(ABC):
    @abstractmethod
    async def send_message(self, message: List) -> None:
        pass


class WebSocketChannel(ChatChannel):
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def send_message(self, message: List) -> None:
        for msg in message:
            await self.websocket.send_text(msg)


class RESTChannel(ChatChannel):
    def __init__(self):
        self.messages: List[str] = []

    async def send_message(self, message: str) -> None:
        self.messages.append(message)


class GradioChannel(ChatChannel):
    def __init__(self, history: List[Tuple[Optional[str], str]]):
        self.history = history

    async def send_message(self, message: str, user: Optional[Text] = "") -> None:
        self.history.append((user, message))
        # print("from output channel", self.history)
