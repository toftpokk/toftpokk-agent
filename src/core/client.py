import importlib.metadata
from typing import Optional

from .core import AuthMethod, Message
from .adapter import Adapter, Adapter, AnthropicAdapter

# TODO: consider removing middleman
class Client():
    """
    A message transporter. Handles message translation and
    authentication.
    """
    provider_name: str
    model: str
    adapter: Adapter

    def __init__(
        self, 
        provider_name: str, 
        model: str,
        adapter: Adapter,
    ) -> None:
        self.model = model
        self.provider_name = provider_name
        self.adapter = adapter
    
    async def handle_message(self, messages: [Message], tools: [dict]) -> Message:
        return self.adapter.send_message(messages, self.model, tools)