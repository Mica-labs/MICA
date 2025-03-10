import time
from abc import ABC
from typing import Text, Optional, Any, Dict, List


class Event(ABC):
    """Events describe everything that occurs in
    a conversation and tell the :class:`tracker.Tracker`
    how to update its state."""

    type_name = "event"

    def __init__(self,
                 timestamp: Optional[float] = None,
                 metadata: Optional[Any] = None
                 ):
        self.timestamp = timestamp or time.time()
        self.metadata = metadata


class UserInput(Event):
    def __init__(self,
                 text: Text = None,
                 timestamp: Optional[float] = None,
                 metadata: Optional[Any] = None):
        self.timestamp = timestamp or time.time()
        self.text = text

        super().__init__(timestamp, metadata)

    def __repr__(self):
        return f"UserInput(text={self.text}, " \
               f"timestamp={self.timestamp})"


class BotUtter(Event):
    def __init__(self,
                 text: Text = None,
                 timestamp: Optional[float] = None,
                 metadata: Optional[Any] = None,
                 additional: Optional[Dict[Any, Any]] = None,
                 provider: Optional[Text] = None,
                 ):
        self.text = text
        self.additional = additional
        self.provider = provider

        super().__init__(timestamp, metadata)

    @classmethod
    def from_dict(cls, data: Dict):
        text = data.get("text")
        timestamp = data.get("timestamp")
        metadata = data.get("metadata")
        additional = data.get("additional")
        return cls(text, timestamp, metadata, additional)

    def __repr__(self):
        return f"BotUtter(text={self.text}, " \
               f"timestamp={self.timestamp})"


class SetSlot(Event):
    def __init__(self,
                 slot_name: Text,
                 value: Any,
                 provider: Optional[Text] = None,
                 timestamp: Optional[float] = None,
                 metadata: Optional[Any] = None):
        self.slot_name = slot_name
        self.value = value
        self.provider = provider

        super().__init__(timestamp, metadata)

    def __repr__(self):
        return f"SetSlot(slot_name={self.slot_name}, " \
               f"value={self.value}, " \
               f"provider={self.provider}, " \
               f"timestamp={self.timestamp})"

    @classmethod
    def from_dict(cls, data: Dict):
        slot_name = data.get("slot_name")
        value = data.get("value")
        provider = data.get("provider")
        timestamp = data.get("timestamp")
        metadata = data.get("metadata")
        return cls(slot_name, value, provider, timestamp, metadata)


class AgentComplete(Event):
    def __init__(self,
                 timestamp: Optional[float] = None,
                 provider: Optional[Text] = None,
                 metadata: Optional[Any] = None):
        self.timestamp = timestamp or time.time()
        self.provider = provider

        super().__init__(timestamp, metadata)

    def __repr__(self):
        return f"AgentComplete(provider={self.provider}, metadata={self.metadata})"


class AgentFail(Event):
    def __init__(self,
                 timestamp: Optional[float] = None,
                 provider: Optional[Text] = None,
                 metadata: Optional[Any] = None):
        self.timestamp = timestamp or time.time()
        self.provider = provider

        super().__init__(timestamp, metadata)

    def __repr__(self):
        return f"AgentFail(provider={self.provider})"


class AgentRunResult(Event):
    def __init__(self,
                 timestamp: Optional[float] = None,
                 provider: Optional[Text] = None,
                 result: Optional[List[Event]] = None,
                 status: Optional[Text] = "active",
                 metadata: Optional[Any] = None):
        self.timestamp = timestamp or time.time()
        self.provider = provider
        self.result = result or []
        self.status = status

        super().__init__(timestamp, metadata)

    def __repr__(self):
        return f"AgentRunResult(provider={self.provider}, status={self.status}, result={self.result})"


class AgentException(Event):
    def __init__(self,
                 timestamp: Optional[float] = None,
                 provider: Optional[Text] = None,
                 metadata: Optional[Any] = None):
        self.timestamp = timestamp or time.time()
        self.provider = provider

        super().__init__(timestamp, metadata)

    def __repr__(self):
        return f"AgentException(provider={self.provider})"


class FollowUpAgent(Event):
    def __init__(self,
                 timestamp: Optional[float] = None,
                 provider: Optional[Text] = None,
                 next_agent: Optional[Text] = None,
                 metadata: Optional[Any] = None):
        self.timestamp = timestamp or time.time()
        self.provider = provider
        self.next_agent = next_agent

        super().__init__(timestamp, metadata)


class CurrentAgent(Event):
    def __init__(self,
                 timestamp: Optional[float] = None,
                 agent: Optional[Any] = None,
                 metadata: Optional[Any] = None):
        self.timestamp = timestamp or time.time()
        self.agent = agent

        super().__init__(timestamp, metadata)

    def __repr__(self):
        return f"CurrentAgent(agent={self.agent}, metadata={self.metadata})"


class FunctionCall(Event):
    def __init__(self,
                 timestamp: Optional[float] = None,
                 function_name: Optional[Any] = None,
                 args: Optional[Any] = None,
                 call_id: Optional[Any] = None,
                 metadata: Optional[Any] = None):
        self.timestamp = timestamp or time.time()
        self.function_name = function_name
        self.call_id = call_id
        self.args = args

        super().__init__(timestamp, metadata)

    def __repr__(self):
        return f"FunctionCall(function_name={self.function_name})"
