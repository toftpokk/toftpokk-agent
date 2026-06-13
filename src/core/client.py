import importlib.metadata
from typing import Optional

from .core import AuthMethod, Message
from .adapter import Adapter, AdapterBase, adapter_from_name

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
    adapter: Optional[AdapterBase]

    def __init__(
        self, 
        provider_name: str, 
        model: str,
        base_url: str,
        auth_method: AuthMethod,
        auth_api_key: Optional[str] = None,
        adapter: Optional[Adapter] = None,
    ) -> None:
        self.model = model
        self.provider_name = provider_name
        self.base_url = base_url
        self.auth_method = auth_method
        self.auth_api_key = auth_api_key

        self.adapter = adapter
    
    def handle_message_synchronous(self, message: Message):
        print(message)
    
    # async def handle_message(self, message: Message):
    #     # TODO handle errors. This is lazy
    #     adapter = adapter_from_name(self.adapter)
    #     adapter.send_message()