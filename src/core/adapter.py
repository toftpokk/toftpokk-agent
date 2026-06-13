from anthropic import Anthropic
import anthropic.types as ant_types
from enum import Enum

from .core import Message, Role, TextBlock, ThinkingBlock, ToolUseBlock

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
                case "thinking":
                    content.append({
                        "type": "thinking",
                        "signature": block.signature,
                        "thinking": block.thinking,
                    })
                case "tool_use":
                    content.append({
                        "type": "tool_use",
                        "input": block.input,
                        "name": block.name,
                    })
                # case "tool_result":
                #     content.append({
                #         "type": "tool_result",
                #         "content": block.content
                #     })
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
                case "thinking":
                    content.append(ThinkingBlock(
                        signature=block.signature,
                        thinking=block.thinking,
                    ))
                case "tool_use":
                    print("caller", block.caller)
                    content.append(ToolUseBlock(
                        # caller=block.caller,
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

    
    
    def send_message(self, messages: [Message], model: str) -> Message:
        ant_msgs: [ant_types.MessageParam] = []
        for msg in messages:
            ant_msg = AnthropicAdapter._convert_message_to_ant_param(msg)
            ant_msgs.append(ant_msg)
        message = self.sdk.messages.create(
            tools=[{'name': 'read_file', 'description': "Read a text file with line numbers and pagination. Use this instead of cat/head/tail in terminal. \nOutput format: 'LINE_NUM|CONTENT'. Suggests similar filenames if not found. Use offset and limit for large files. \nReads exceeding ~100K characters are rejected; use offset and limit to read specific sections of large files. \n\nNOTE: Cannot read images or binary files\n", 'input_schema': {'properties': {'path': {'description': 'Path to the file to read (absolute, relative, or ~/path)', 'type': 'string'}, 'offset': {'default': 1, 'description': 'Line number to start reading from (1-indexed, default: 1)', 'ge': 1, 'type': 'string'}, 'limit': {'default': 500, 'description': 'Maximum number of lines to read (default: 500, max: 2000)', 'le': 2000, 'type': 'string'}}, 'required': ['path'], 'type': 'object'}, 'dependencies': []}],
            max_tokens=1024,
            messages=ant_msgs,
            model=model,
        )
        return AnthropicAdapter._convert_message_from_ant(message)