import importlib.metadata
from typing import Optional

from .core import AuthMethod, Message

class Client():
    """
    A message transporter. Handles message translation and
    authentication.
    """
    provider_name: str
    model: str
    base_url: str
    auth_method: AuthMethod
    auth_api_key: Optional[str]

    def __init__(
        self, 
        provider_name: str, 
        model: str,
        base_url: str,
        auth_method: str,
        auth_api_key: Optional[str] = None
    ) -> None:
        self.model = model
        self.provider_name = provider_name
        self.base_url = base_url
        self.auth_method = auth_method
        self.auth_api_key = auth_api_key
    
    def handle_message_synchronous(self, message: Message):
        print(importlib.metadata.version("kong_agent"))