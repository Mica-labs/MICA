import re
from abc import ABC
from typing import Dict, Text

from mica.tracker import Tracker


class TrackerStore(ABC):
    def __init__(self):
        pass

    def get_or_create_tracker(self, user_id: Text, **kwargs) -> "Tracker":
        tracker = self.retrieve(user_id)
        if tracker is None:
            kwargs.get("args")["sender"] = user_id
            tracker = self.create_tracker(user_id, **kwargs)
        return tracker

    def retrieve(self, user_id: Text):
        """Retrieves tracker for the latest conversation session.
        This method will be overridden by the specific tracker store.
        Args:
            user_id: Conversation ID to fetch the tracker for.
        Returns:
            Tracker containing events from the latest conversation sessions.
        """
        raise NotImplementedError()

    def create_tracker(self, user_id: Text, **kwargs):
        raise NotImplementedError()


class InMemoryTrackerStore(TrackerStore):
    def __init__(self):
        self.store: Dict[Text, Tracker] = {}
        super().__init__()

    @classmethod
    def create(cls):
        return cls()

    def retrieve(self, user_id: Text):
        return self.store.get(user_id)

    def create_tracker(self, user_id: Text, **kwargs):
        new_tracker = Tracker.create(user_id, **kwargs)
        self.store[user_id] = new_tracker
        return new_tracker





