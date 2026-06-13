from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union, Self

class AuthMethod(Enum):
    API_KEY = "api_key"

class Role(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

@dataclass
class TextContent:
    text: str
    type_ = "text"

@dataclass
class Message():
    message_id: str
    role: Role
    content: Union[
        TextContent
    ]
    def __repr__(self):
        return f'<Message({self.role}, {self.content})>'

    @classmethod
    def from_user(cls, id: str, msg: str) -> Self:
        return cls(id, Role.USER, TextContent(text=msg))