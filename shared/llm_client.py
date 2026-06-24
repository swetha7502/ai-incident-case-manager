# shared/llm_client.py
#
# Shared LLM calling utility with 3-provider fallback chain.
# Used by investigation-agent/agent.py and report-generator/generator.py.
#
# Provider order (try first, fall through on any error):
#   1. GitHub Models  (openai/gpt-4.1)     -- confirmed working
#   2. Google Gemini  (gemini-2.5-flash)   -- first fallback
#   3. Groq           (llama-3.3-70b)      -- second fallback
#
# If all three fail, raises a RuntimeError with a summary of all failures.

import os
import json
import requests
from dotenv import load_dotenv

# Load .env from the repo root (two levels up from shared/)
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=_env_path, override=False)


def _call_github_models(system_prompt: str, user_message: str) -> str:
    """
    Call GitHub Models API (openai/gpt-4.1).
    Endpoint: https://models.github.ai/inference/chat/completions
    """
    token = os.getenv("GITHUB_MODELS_TOKEN", "")
    if not token:
        raise ValueError("GITHUB_MODELS_TOKEN not set in .env")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    body = {
        "model": "openai/gpt-4.1",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }

    response = requests.post(
        "https://models.github.ai/inference/chat/completions",
        headers=headers,
        json=body,
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"GitHub Models returned {response.status_code}: {response.text}"
        )

    return response.json()["choices"][0]["message"]["content"]


def _call_gemini(system_prompt: str, user_message: str) -> str:
    """
    Call Google AI Studio (Gemini 2.5 Flash) via google-generativeai package.
    """
    try:
        import google.generativeai as genai
    except ImportError:
        raise RuntimeError(
            "google-generativeai package not installed. "
            "Run: pip install google-generativeai"
        )

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not set in .env")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        system_instruction=system_prompt,
    )
    response = model.generate_content(user_message)
    return response.text


def _call_groq(system_prompt: str, user_message: str) -> str:
    """
    Call Groq (llama-3.3-70b-versatile) via OpenAI-compatible client.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "openai package not installed. Run: pip install openai"
        )

    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in .env")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content


def call_llm(system_prompt: str, user_message: str) -> str:
    """
    Call an LLM with a 3-provider fallback chain. Tries each provider in order;
    on any failure, logs the error and falls through to the next provider.
    Prints which provider answered so it's visible during testing and demo.

    Args:
        system_prompt: The system instruction for the LLM.
        user_message:  The user-turn message (incident payload, etc.)

    Returns:
        str: The raw text response from whichever provider succeeds.

    Raises:
        RuntimeError: If all three providers fail, with a summary of all errors.
    """
    providers = [
        ("GitHub Models (openai/gpt-4.1)", _call_github_models),
        ("Google Gemini (gemini-2.5-flash)", _call_gemini),
        ("Groq (llama-3.3-70b-versatile)", _call_groq),
    ]

    failures = []

    for name, fn in providers:
        try:
            print(f"[LLM] Trying provider: {name} ...")
            result = fn(system_prompt, user_message)
            print(f"[LLM] Answered by: {name}")
            return result
        except Exception as exc:
            msg = f"{name} failed: {exc}"
            print(f"[LLM] {msg}")
            failures.append(msg)

    raise RuntimeError(
        "All LLM providers failed. Errors:\n" + "\n".join(f"  - {f}" for f in failures)
    )
