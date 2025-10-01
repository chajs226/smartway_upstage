import os
from dotenv import load_dotenv
from openai import OpenAI
from langchain_upstage import ChatUpstage

# Load .env on import
load_dotenv(override=True)


def get_upstage_api_key() -> str:
    api_key = os.getenv("UPSTAGE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("UPSTAGE_API_KEY is not set. Please set it in your .env file.")
    return api_key


def get_tavily_api_key() -> str:
    return os.getenv("TAVILY_API_KEY", "").strip()


def build_openai_client() -> OpenAI:
    return OpenAI(api_key=get_upstage_api_key(), base_url="https://api.upstage.ai/v1")


def build_chat_model(temperature: float = 0) -> ChatUpstage:
    return ChatUpstage(model="solar-pro2", temperature=temperature)
