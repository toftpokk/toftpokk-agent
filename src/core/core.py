from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union, Self

class AuthMethod(Enum):
    API_KEY = "api_key"

class Role(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    # TOOL = "tool"

class Block:
    type_: str

    def __repr__(self) -> str:
        return f"<Block({self.type_})>"
    
    def display(self) -> str:
        return self.__repr__()

@dataclass
class TextBlock(Block):
    type_ = "text"
    text: str

    def display(self) -> str:
        return  self.text

@dataclass
class ThinkingBlock(Block):
    type_ = "thinking"
    signature: str
    thinking: str

    def display(self) -> str:
        return  f"> {self.thinking}"



@dataclass
class Message():
    message_id: str
    role: Role
    content: [Union[
        TextBlock
    ]]
    def __repr__(self):
        return f'<Message({self.role}, {self.content})>'

    @classmethod
    def from_user(cls, id: str, msg: str) -> Self:
        return cls(id, Role.USER, [TextBlock(text=msg)])

    def display(self) -> str:
        output = []
        for block in self.content:
            output.append(block.display())
        return "\n\n".join(output)