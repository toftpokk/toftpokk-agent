import inspect
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union, Self, Callable, ParamSpec, TypeVar
from pydantic import create_model

P = ParamSpec("P")
R = TypeVar("R")

def tool(
    func: Callable[P, R] | None = None,
    *, # disallow positional arguments
    name: str | None = None,
    description: str | None = None,
    dependencies: [str] = [],
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
            "input_schema": input_schema,
            "dependencies": dependencies
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
    TOOL = "tool"

class StopReason(Enum):
    END_TURN = "end_turn"
    TOOL_USE = "tool_use"

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
        output = self.thinking.replace("\n", "\n> ")
        return f"> {output}"

@dataclass
class ToolUseBlock(Block):
    type_ = "tool_use"
    name: str
    input: str

    def display(self) -> str:
        # TODO clean this up
        return  f">TOOL {self.name} {self.input}"

@dataclass
class ToolResultBlock(Block):
    type_ = "tool_result"
    tool_use_id: str
    content: [Union[
        TextBlock,
    ]]
    # name: str
    # input: str

    def display(self) -> str:
        # TODO clean this up
        content_outputs = []
        for content in self.content:
            content_outputs.append(content.display())
        
        return f">TOOL RESULT {self.tool_use_id}"

@dataclass
class MessageMeta():
    stop_reason: StopReason | None = None

@dataclass
class Message():
    message_id: str
    role: Role
    content: [Union[
        TextBlock,
        ThinkingBlock,
        ToolUseBlock,
    ]]
    def __repr__(self):
        return f'<Message({self.role}, {self.content})>'

    @classmethod
    def from_user(cls, id: str, msg: str) -> Self:
        return cls(id, Role.USER, [TextBlock(text=msg)])
    
    @classmethod
    def from_tool_result(cls, id: str, content: str) -> Self:
        return cls(id, Role.TOOL, [ToolResultBlock(tool_use_id=id, content=[TextBlock(text=content)])])

    def display(self) -> str:
        output = []
        for block in self.content:
            output.append(block.display())
        return "\n\n".join(output)