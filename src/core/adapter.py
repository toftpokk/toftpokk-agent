from anthropic import Anthropic
import anthropic.types as ant_types
from enum import Enum

from .core import Message, Role, TextBlock

class Adapter(Enum):
    ANTHROPIC = "anthropic"
    
class AdapterBase():
    # TODO return None is lazy
    async def send_message(self, messages: [Message], model: str) -> None:
        pass

class AnthropicAdapter(AdapterBase):
    sdk: Anthropic

    def __init__(self, api_key: str, base_url: str) -> None:
        self.sdk = Anthropic(
            api_key=api_key,
            base_url=base_url,
        )
    
    def _convert_message_to_ant_param(message: Message) -> ant_types.MessageParam:
        roles: dict[Role, str] = {
            Role.USER: "user",
            Role.ASSISTANT: "assistant" ,
            Role.SYSTEM: "system" ,
        }
        role = roles[message.role]

        content = []
        for block in message.content:
            match block.type_:
                case "text":
                    content.append({
                        "type": "text",
                        "text": block.text,
                    })
                case t:
                    raise ValueError(f"unknown content type '{t}'")
        return {
            "role": role,
            "content": content, 
        }

    def _convert_message_from_ant(message: ant_types.Message) -> Message:
        roles: dict[str, Role] = {
            "user": Role.USER,
            "assistant": Role.ASSISTANT,
            "system": Role.SYSTEM,
        }
        role = roles[message.role]

        content = []
        for block in message.content:
            match block.type:
                case "text":
                    content.append(TextBlock(
                        text=block.text,
                    ))
                case t:
                    raise ValueError(f"unknown content type '{t}'")

        return Message(
            message_id=message.id,
            role=role,
            content=content
        )

    
    
    async def send_message(self, messages: [Message], model: str) -> None:
        ant_msgs: [ant_types.MessageParam] = []
        for msg in messages:
            ant_msg = AnthropicAdapter._convert_message_to_ant_param(msg)
            ant_msgs.append(ant_msg)
        message = self.sdk.messages.create(
            max_tokens=1024,
            messages=ant_msgs,
            model=model,
        )
        print(message)