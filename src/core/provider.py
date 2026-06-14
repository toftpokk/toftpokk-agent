
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .core import AuthMethod

@dataclass
class Provider:
    name: str
    base_url: str
    # TODO dynamically load latest models
    models: [dict]
    auth_method: AuthMethod

    # for humans
    display: str
    adapter: str

    auth_api_key_env: Optional[str] = None

    # TODO: checking is useless, make a method that matters
    def model_exists(self, model_name: str) -> bool:
        return model_name in self.models