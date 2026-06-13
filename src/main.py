import os
import logging

import yaml
from dotenv import load_dotenv, dotenv_values
import asyncio

import providers.registry as providers
import tools.registry as tools
from core.core import Message, MessageMeta, StopReason, AuthMethod
from core.provider import Provider
from core.client import Client

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

class Config:
    model_default: str = None
        
    def __init__(self, filename: str) -> None:
        raw = None
        with open(filename, "r") as f:
            raw = yaml.safe_load(f)
        if raw is None:
            return
        if "model_default" in raw:
            model_default = raw["model_default"]
            try:
                _, _ = _get_valid_model(model_default)
                self.model_default = model_default
            except ValueError as error:
                logging.warning(f"loading from '{filename}': loading model_default: {error}")


class Runner:
    """
    A runner. Handles history data and prompt building, and sending of
    messages.
    """
    client: Client
    history: [Message]
    tools: [str]
    running_id: int
    tool_use_id: int

    def __init__(self, client: Client) -> None:
        self.client = client
        self.running_id = 0
        self.tool_use_id = 0
        self.history = []
        self.tools = tools.list_all()

    async def handle_message(self, message: str) -> [Message]:
        self.running_id += 1

        user_message = Message.from_user(str(self.running_id), message)
        self.history.append(user_message)


        turn_outputs = []
        while True:
            (agent_message, agent_meta) = await self.client.handle_message(self.history)
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
                            tool = tools.load(block.name)
                            tool_result = Message.from_tool_result(str(self.tool_use_id), tool(**block.input))
                            self.history.append(tool_result)
                            turn_outputs.append(tool_result)

        return turn_outputs

def main():
    load_dotenv()

    # TODO create temp config file
    # temporary file
    config = Config("config.yml")

    model_full_name = config.model_default
    if model_full_name is None:
        logging.warning(f"no default model provided, defaulting to 'minimax/MiniMax-M2.7'")
        model_full_name = "minimax/MiniMax-M2.7"
    
    (provider, model_name) = _get_valid_model(model_full_name)

    auth_api_key = None
    if provider.auth_method == AuthMethod.API_KEY:
        auth_api_key = os.getenv(provider.auth_api_key_env)
        if auth_api_key is None or auth_api_key == "":
            raise Exception(f"provider {provider.display} is authenticating with api key, but required environment {provider.auth_api_key_env} not found")

    # Synchronous, for debugging
    runner = Runner(Client(
        provider_name=provider.name,
        model=model_name,
        base_url=provider.base_url,
        auth_method=provider.auth_method,
        auth_api_key=auth_api_key,
        adapter_name=provider.adapter,
    ))
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