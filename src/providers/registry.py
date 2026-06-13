from core.provider import Provider, AuthMethod

REGISTRY = {}

def register_provider(provider: Provider) -> None:
    REGISTRY[provider.name] = provider

def load_provider(name: str) -> Provider:
    return REGISTRY.get(name)

_deepseek = Provider(
    name = "deepseek",
    display = "DeepSeek",
    base_url="https://api.deepseek.com/v1",
    models=["deepseek-v4-flash", "deepseek-v4-pro"],
    auth_method=AuthMethod.API_KEY,
    auth_api_key_env="DEEPSEEK_API_KEY",
)
register_provider(_deepseek)

_deepseek = Provider(
    name = "minimax",
    display = "MiniMax",
    base_url="https://api.minimax.io/anthropic/v1/messages",
    models=["MiniMax-M2.7"],
    auth_method=AuthMethod.API_KEY,
    auth_api_key_env="MINIMAX_API_KEY",
)
register_provider(_deepseek)