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

@dataclass
class TextBlock:
    text: str
    type_ = "text"

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