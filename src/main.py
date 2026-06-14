import os
import logging
from typing import Callable, ParamSpec, TypeVar, Self
from dataclasses import dataclass, fields, is_dataclass

import yaml
from dotenv import load_dotenv, dotenv_values
import asyncio

import providers.registry as providers
from tools.registry import make_tools
from core.core import Message, MessageMeta, StopReason, AuthMethod
from core.provider import Provider
from core.client import Client
from core.file_op import FileAccessor
from core import adapter

P = ParamSpec("P")
R = TypeVar("R")

def _get_valid_model(model_full_name: str) -> (Provider, str):
    try:
        (provider_name, model_name) = model_full_name.split("/", 1)
    except ValueError:
        raise ValueError("invalid model format, should be 'provider/model'")
    
    provider = providers.load(provider_name)
    if provider is None:
        raise ValueError(f"unsupported provider '{provider_name}'")
    if not provider.model_exists(model_name):
        raise ValueError(f"unknown model '{model_name}' for provider '{provider_name}', supported models: {provider.models}")
    return (provider, model_name)

@dataclass
class ConfigFileOp:
    blacklist: list = None
    whitelist: list = None
    sensitive_suffixes: list = None

@dataclass  
class Config:
    model_default: str = None
    file_op: ConfigFileOp = None

    @classmethod
    def from_file(cls, filename: str) -> "Config":
        with open(filename, "r") as f:
            raw = yaml.safe_load(f) or {}
        return _load(cls, raw, filename)
    
    def _validate(self, filename: str, path: str):
        if self.model_default is not None:
            try:
                _, _ = _get_valid_model(self.model_default)
            except ValueError as e:
                logging.warning(f"parsing config '{filename}': '{path}.model_default': {e}")
                self.model_default = None

def _load(cls, raw: dict, filename: str, path: str = ""):
    if not isinstance(raw, dict):
        logging.error(f"parsing config'{filename}': '{path}' expected a mapping, got {type(raw).__name__}")
        return cls()

    known = {f.name: f for f in fields(cls)}
    kwargs = {}
    for k, v in raw.items():
        if k not in known:
            continue
        field = known[k]
        field_path = f"{path}.{k}" if path else k
        if is_dataclass(field.type):
            kwargs[k] = _load(field.type, v, filename, field_path)
        else:
            kwargs[k] = v

    instance = cls(**kwargs)
    if hasattr(instance, "_validate"):
        instance._validate(filename, path or cls.__name__.lower())
    return instance



class Runner:
    """
    A runner. Handles history data and prompt building, and sending of
    messages.
    """
    client: Client
    history: [Message]
    tools: dict[str, Callable[P,R]]
    running_id: int
    tool_use_id: int

    def __init__(self, client: Client, file_accessor: FileAccessor) -> None:
        self.client = client
        self.history = []
        self.running_id = 0
        self.tool_use_id = 0
        self.tools = make_tools(file_accessor=file_accessor)

    async def handle_message(self, message: str) -> [Message]:
        self.running_id += 1

        user_message = Message.from_user(str(self.running_id), message)
        self.history.append(user_message)

        all_tools = []
        for tool in self.tools:
            all_tools.append(self.tools[tool].tool_definition)

        turn_outputs = []
        while True:
            (agent_message, agent_meta) = await self.client.handle_message(self.history, all_tools)
            self.history.append(agent_message)
            turn_outputs.append(agent_message)

            if not agent_meta.stop_reason is None:
                match agent_meta.stop_reason:
                    case StopReason.END_TURN.value:
                        break
                    case StopReason.TOOL_USE.value:
                        pass
                    case r:
                        raise Exception(f"unknown stop reason {r}")

                for block in agent_message.content:
                    if block.type_ == "tool_use":
                        self.tool_use_id += 1
                        if block.name in self.tools:
                            tool = self.tools[block.name]
                            tool_result = Message.from_tool_result(str(self.tool_use_id), tool(**block.input))
                            self.history.append(tool_result)
                            turn_outputs.append(tool_result)

        return turn_outputs

def main():
    load_dotenv()

    # TODO create temp config file
    # temporary file
    config = Config.from_file("config.yml")

    model_full_name = config.model_default
    if model_full_name is None:
        logging.warning(f"no default model provided, defaulting to 'minimax/MiniMax-M2.7'")
        model_full_name = "minimax/MiniMax-M2.7"
    
    (provider, model_name) = _get_valid_model(model_full_name)

    auth_api_key = None
    if provider.auth_method == AuthMethod.API_KEY:
        auth_api_key = os.getenv(provider.auth_api_key_env)
        if auth_api_key is None or auth_api_key == "":
            raise Exception(f"provider {provider.display} is authenticating with {provider.auth_method}, but required environment {provider.auth_api_key_env} is not set")

    model_adapter : adapter.Adapter = None
    match provider.adapter:
        case "anthropic":
            if provider.auth_method != AuthMethod.API_KEY:
                raise Exception(f"provider '{provider.display}' is authenticating with '{provider.auth_method}', but adapter '{provider.adapter}' does not support this method")
            model_adapter = adapter.AnthropicAdapter(
                api_key=auth_api_key,
                base_url=provider.base_url,
            )
        case _:
            raise Exception(f"provider '{provider.name}' uses unknown adapter '{provider.adapter}'")
    
    # blacklist = (config.file_op and config.file_op.blacklist) or []
    # whitelist = (config.file_op and config.file_op.whitelist) or []
    # fa = FileAccessor(
    #         blacklist=blacklist, 
    #         whitelist=whitelist
    #     )
    # print(fa.search_content("*", ".", "*", limit=10, offset=0))

    blacklist = (config.file_op and config.file_op.blacklist) or []
    whitelist = (config.file_op and config.file_op.whitelist) or []
    sensitive_suffixes = (config.file_op and config.file_op.sensitive_suffixes) or []
    runner = Runner(
        Client(
            provider_name=provider.name,
            model=model_name,
            adapter=model_adapter
        ),
        FileAccessor(
            blacklist=blacklist, 
            whitelist=whitelist,
            sensitive_suffixes=sensitive_suffixes,
        )
    )
    while True:
        try:
            user_message = input()
            output_messages = asyncio.run(runner.handle_message(user_message))
        except KeyboardInterrupt:
            break
        for output in output_messages:
            print(output.display())

    # async def loop():
    #     runner = Runner(Client(
    #         provider_name=provider.name,
    #         model=model_name,
    #         base_url=provider.base_url,
    #         auth_method=provider.auth_method,
    #         auth_api_key=auth_api_key,
    #         adapter_name=provider.adapter,
    #     ))
    #     while True:
    #         try:
    #             user_message = input()
    #             output_message = await runner.handle_message(user_message)
    #         except KeyboardInterrupt:
    #             break
    #         print(output_message.display())
    # asyncio.run(loop())

if __name__ == "__main__":
    main()