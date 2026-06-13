import inspect
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union, Self, Callable, ParamSpec, TypeVar
from pydantic import create_model

P = ParamSpec("P")
R = TypeVar("R")

def tool(
    func: Callable[P, R],
    *, # disallow positional arguments
    name: str | None = None,
    description: str | None = None,
) -> Callable[P, R]:
    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        tool_name = name or fn.__name__
        tool_desc = description or fn.__doc__ or "No description provided."
    
        sig = inspect.signature(fn)
        fields: dict[str, Any] = {}

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls") or param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue
            annotation = Any if param.annotation is inspect.Parameter.empty else param.annotation

            if param.default is not inspect.Parameter.empty:
                fields[param_name] = (annotation, param.default)
            else:
                fields[param_name] = (annotation, ...)
        
        DynamicModel = create_model(f"{tool_name}_input", **fields)
        input_schema = DynamicModel.model_json_schema()

        input_schema.pop("title", None)
        if "properties" in input_schema:
            for prop in input_schema["properties"].values():
                prop.pop("title", None)
        
        tool_definition = {
            "name": tool_name,
            "description": tool_desc,
            "input_schema": input_schema
        }

        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return fn(*args, **kwargs)
        
        wrapper.tool_definition = tool_definition
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator

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