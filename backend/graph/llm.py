from langchain_google_genai import ChatGoogleGenerativeAI

from config import settings


def get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-3.5-flash",
        google_api_key=settings.gemini_api_key,
        temperature=0.2,
    )
