from core.provider import Provider, AuthMethod
from core.adapter import Adapter

REGISTRY: dict[str, Provider] = {}

def register(provider: Provider) -> None:
    REGISTRY[provider.name] = provider

def load(name: str) -> Provider:
    return REGISTRY.get(name)

register(Provider(
    name = "deepseek",
    display = "DeepSeek",
    base_url="https://api.deepseek.com/v1",
    models=["deepseek-v4-flash", "deepseek-v4-pro"],
    auth_method=AuthMethod.API_KEY,
    auth_api_key_env="DEEPSEEK_API_KEY",
))

register(Provider(
    name = "minimax",
    display = "MiniMax",
    base_url="https://api.minimax.io/anthropic/",
    models=["MiniMax-M2.7"],
    auth_method=AuthMethod.API_KEY,
    auth_api_key_env="MINIMAX_API_KEY",
    adapter=Adapter.ANTHROPIC,
))