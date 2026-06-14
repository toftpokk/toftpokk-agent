from anthropic import Anthropic
import anthropic.types as ant_types
from enum import Enum

from .core import Message, MessageMeta, Block, Role, TextBlock, ThinkingBlock, ToolUseBlock, StopDetails
    
class Adapter():
    # TODO return None is lazy
    async def send_message(self, messages: list[Message], model: str, tools: list[dict])-> (Message, MessageMeta):
        pass

class AnthropicAdapter(Adapter):
    sdk: Anthropic

    def __init__(self, api_key: str, base_url: str) -> None:
        self.sdk = Anthropic(
            api_key=api_key,
            base_url=base_url,
        )
    
    def _block_to_ant_param(block: Block) -> ant_types.ContentBlockParam:
        match block.type_:
            case "text":
                return {
                    "type": "text",
                    "text": block.text,
                }
            case "thinking":
                return {
                    "type": "thinking",
                    "signature": block.signature,
                    "thinking": block.thinking,
                }
            case "tool_use":
                return {
                    "type": "tool_use",
                    "input": block.input,
                    "name": block.name,
                    "id": block.tool_use_id,
                }
            case "tool_result":
                content = []
                for b in block.content:
                    content.append(AnthropicAdapter._block_to_ant_param(b))
                return{
                    "type": "tool_result",
                    "tool_use_id": block.tool_use_id,
                    "content": content
                }
            case t:
                raise ValueError(f"unknown content type '{t}'")
        
    
    def _convert_message_to_ant_param(message: Message) -> ant_types.MessageParam:
        roles: dict[Role, str] = {
            Role.USER: "user",
            Role.TOOL: "user",
            Role.ASSISTANT: "assistant",
            Role.SYSTEM: "system",
        }
        role = roles[message.role]

        content = []
        for block in message.content:
            content.append(AnthropicAdapter._block_to_ant_param(block))
            
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
                case "thinking":
                    content.append(ThinkingBlock(
                        signature=block.signature,
                        thinking=block.thinking,
                    ))
                case "tool_use":
                    content.append(ToolUseBlock(
                        tool_use_id=block.id,
                        input=block.input,
                        name=block.name,
                    ))
                case t:
                    raise ValueError(f"unknown content type '{t}'")

        return Message(
            message_id=message.id,
            role=role,
            content=content
        )

    
    
    def send_message(self, messages: list[Message], model: str, tools: list[dict]) -> (Message, MessageMeta):
        ant_msgs: [ant_types.MessageParam] = []
        for msg in messages:
            ant_msg = AnthropicAdapter._convert_message_to_ant_param(msg)
            ant_msgs.append(ant_msg)
        message = self.sdk.messages.create(
            tools=tools,
            max_tokens=1024,
            messages=ant_msgs,
            model=model,
        )
        stop_details = None
        if not message.stop_details is None:
            stop_details = StopDetails(
                category=message.stop_details.category,
                explanation=message.stop_details.explanation,
            )
        return (
            AnthropicAdapter._convert_message_from_ant(message),
            MessageMeta(
                stop_reason=message.stop_reason,
                stop_details=stop_details,
            )
        )