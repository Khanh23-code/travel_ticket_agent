import os
import sys
from typing import Any, Optional
from dotenv import load_dotenv

load_dotenv()


def get_llm(provider: str = "auto", temperature: float = 0.0) -> Any:
    openai_key = os.environ.get("OPENAI_API_KEY")
    openai_base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE")
    openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    google_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

    if (provider == "openai" or provider == "openrouter" or provider == "auto") and openai_key:
        try:
            from langchain_openai import ChatOpenAI
            
            kwargs = {
                "model": openai_model,
                "api_key": openai_key,
                "temperature": temperature
            }
            
            if openai_base_url:
                kwargs["base_url"] = openai_base_url
                print(f"[INFO] Đã kết nối với OpenRouter API Model ({openai_model}) tại Base URL: {openai_base_url}...")
            else:
                print(f"[INFO] Đã kết nối với OpenAI Model ({openai_model})...")

            return ChatOpenAI(**kwargs)
        except Exception as e:
            print(f"[WARNING] Không thể kết nối OpenAI/OpenRouter API ({e}). Thử các provider khác...")

    if (provider == "google" or provider == "auto") and google_key:
        try:
            # pyrefly: ignore [missing-import]
            from langchain_google_genai import ChatGoogleGenerativeAI
            print("[INFO] Đã kết nối với Google Gemini API Model (gemini-1.5-flash)...")
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=google_key,
                temperature=temperature
            )
        except Exception as e:
            print(f"[WARNING] Không thể kết nối Gemini API ({e})...")

    print("[WARNING] THÔNG BÁO: Chưa tìm thấy API Key khả dụng.")
    print("[NOTE] Hệ thống sẽ sử dụng Deterministic Mock ReAct Engine để phục vụ testing offline!")
    return None
