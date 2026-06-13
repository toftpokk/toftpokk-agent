from anthropic import Anthropic
from enum import Enum

class Adapter(Enum):
    ANTHROPIC = "anthropic"
    
class AdapterBase():
    pass
    # TODO return None is lazy
    # async def send_message(self, messages: [str], model: str) -> None:
    #     pass

class AnthropicAdapter(AdapterBase):
    sdk: Anthropic

    def __init__(self, api_key: str, base_url: str) -> None:
        self.sdk = Anthropic(
            api_key=api_key,
            base_url=base_url,
        )
    
    # async def send_message(self, messages: [str], model: str) -> None:
    #     message = await self.sdk.messages.create(
    #         max_tokens=1024,
    #         messages=[],
    #         model=model,
    #     )
    #     print(message.content)
        
        

def adapter_from_name(adapter: Adapter) -> AdapterBase:
    if adapter == Adapter.ANTHROPIC:
        return AnthropicAdapter
    raise Exception(f"unknown adapter '{adapter}'")