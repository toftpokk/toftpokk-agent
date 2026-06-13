import importlib.metadata
from typing import Optional

from .core import AuthMethod, Message
from .adapter import Adapter, AdapterBase, AnthropicAdapter

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
    adapter: AdapterBase

    def __init__(
        self, 
        provider_name: str, 
        model: str,
        base_url: str,
        auth_method: AuthMethod,
        auth_api_key: Optional[str] = None,
        adapter_name: Optional[Adapter] = None,
    ) -> None:
        self.model = model
        self.provider_name = provider_name
        self.base_url = base_url
        self.auth_method = auth_method
        self.auth_api_key = auth_api_key

        adapter: AdapterBase = None
        if adapter_name == Adapter.ANTHROPIC:
            if self.auth_method != AuthMethod.API_KEY:
                raise Exception(f"adapter '{adapter_name}': unsupported auth_method '{self.auth_method}'")
            if self.auth_api_key is None:
                raise Exception(f"adapter '{adapter_name}': missing auth_api_key")
            
            adapter = AnthropicAdapter(
                self.auth_api_key,
                self.base_url,
            )
        else:
            raise Exception(f"invalid adapter '{adapter_name}'")
        self.adapter = adapter
    
    async def handle_message(self, messages: [Message]):
        await self.adapter.send_message(messages, self.model)