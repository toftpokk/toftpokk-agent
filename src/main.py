import os
import logging

import yaml
from dotenv import load_dotenv, dotenv_values
import asyncio

from providers import registry
from core import Message, Provider, Client, AuthMethod

def _get_valid_model(model_full_name: str) -> (Provider, str):
    try:
        (provider_name, model_name) = model_full_name.split("/", 1)
    except ValueError:
        raise ValueError("invalid model format, should be 'provider/model'")
    
    provider = registry.load_provider(provider_name)
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
    running_id: int

    def __init__(self, client: Client) -> None:
        self.client = client
        self.running_id = 0
        self.history = []

    async def handle_message(self, message: str) -> Message:
        self.running_id += 1

        user_message = Message.from_user(str(self.running_id), message)
        self.history.append(user_message)

        output_message = await self.client.handle_message(self.history)
        self.history.append(output_message)
        return output_message

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


    async def loop():
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
                output_message = await runner.handle_message(user_message)
            except KeyboardInterrupt:
                break
            print(output_message.display())
    
    asyncio.run(loop())

if __name__ == "__main__":
    main()