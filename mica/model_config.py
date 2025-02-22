from typing import Text, Optional, Dict, Any

from mica.constants import DEFAULT_MODEL_ENGINE

KEY_ENGINE = "engine"
KEY_CONFIG = "config"

class ModelConfig:
    def __init__(self,
                 engine: Text,
                 config: Optional[Dict[Text, Any]] = None):
        self.engine = engine
        self.config = config

    @classmethod
    def from_dict(cls, data: Dict):
        engine = data.get(KEY_ENGINE, DEFAULT_MODEL_ENGINE)
        config = data.get(KEY_CONFIG, {})
        return cls(engine, config)