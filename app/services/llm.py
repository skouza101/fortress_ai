"""
LLM Service — Local inference via vLLM (Qwen-3.6).

Uses the OpenAI-compatible chat completions API.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import AsyncGenerator, Optional, List, Dict, Any

from openai import AsyncOpenAI, APIError, APITimeoutError, APIConnectionError

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Local clients (OpenAI-compatible) ────────────────────────

_qwen_client: Optional[AsyncOpenAI] = None

def _get_client() -> AsyncOpenAI:
    global _qwen_client
    if _qwen_client is None:
        api_key = settings.llm_api_key
        if "huggingface.co" in settings.llm_api_base and settings.HUGGING_FACE_HUB_TOKEN:
            api_key = settings.HUGGING_FACE_HUB_TOKEN
        if "integrate.api.nvidia.com" in settings.llm_api_base and settings.NIM_API_KEY:
            api_key = settings.NIM_API_KEY

        _qwen_client = AsyncOpenAI(
            api_key=api_key,
            base_url=settings.llm_api_base,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            max_retries=settings.LLM_MAX_RETRIES,
        )
    return _qwen_client

def _get_model_name() -> str:
    return settings.llm_model


# ── Call presets ─────────────────────────────────────────────
# Different tasks need different penalty settings.
# JSON extraction must have penalties at 0 — repeated tokens are required for valid JSON.
# Creative/chat responses benefit from mild penalties to reduce repetition.

PRESET_JSON = dict(presence_penalty=0.0, frequency_penalty=0.0)
PRESET_CHAT = dict(presence_penalty=0.3, frequency_penalty=0.3)


# ─── Public API ──────────────────────────────────────────────

async def generate(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    json_mode: bool = False,
) -> str:
    """
    Generate a complete response from the LLM (non-streaming).

    Args:
        json_mode: When True, sets penalties to 0 so JSON structure tokens
                   (quotes, braces, commas) are not penalized. Use for any
                   call that expects a JSON response.
    """
    client = _get_client()
    model = _get_model_name()

    messages: List[Dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    penalties = PRESET_JSON if json_mode else PRESET_CHAT

    logger.info(
        f"LLM generate | model={model} | prompt_len={len(prompt)} "
        f"| max_tokens={max_tokens} | json_mode={json_mode} | temp={temperature}"
    )

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            **penalties,
        )
        content = response.choices[0].message.content or ""
        finish_reason = response.choices[0].finish_reason

        if finish_reason == "length":
            logger.warning(
                f"LLM generate: response was TRUNCATED (hit max_tokens={max_tokens}). "
                f"JSON output will likely be incomplete. Consider increasing max_tokens."
            )

        logger.info(f"LLM response | len={len(content)} | finish_reason={finish_reason}")
        return content

    except APITimeoutError as e:
        logger.error(f"LLM generate: TIMEOUT after {settings.LLM_TIMEOUT_SECONDS}s — {e}")
        raise
    except APIConnectionError as e:
        logger.error(f"LLM generate: CONNECTION ERROR (is vLLM running at {settings.llm_api_base}?) — {e}")
        raise
    except APIError as e:
        logger.error(f"LLM generate: API ERROR status={e.status_code} — {e.message}")
        raise


async def stream(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncGenerator[str, None]:
    """Stream response chunks from the LLM."""
    client = _get_client()
    model = _get_model_name()

    messages: List[Dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    logger.info(f"LLM stream | model={model} | prompt_len={len(prompt)}")

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **PRESET_CHAT,
        )

        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except (APITimeoutError, APIConnectionError, APIError) as e:
        logger.error(f"LLM stream error: {e}")
        raise


async def generate_with_history(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Generate with full conversation history (for multi-turn chat)."""
    client = _get_client()
    model = _get_model_name()

    api_messages: List[Dict[str, Any]] = []
    if system_prompt:
        api_messages.append({"role": "system", "content": system_prompt})
    api_messages.extend(messages)

    logger.info(f"LLM generate_with_history | model={model} | turns={len(messages)}")

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=api_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            **PRESET_CHAT,
        )
        return response.choices[0].message.content or ""
    except (APITimeoutError, APIConnectionError, APIError) as e:
        logger.error(f"LLM generate_with_history error: {e}")
        raise


async def stream_with_history(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncGenerator[str, None]:
    """Stream with full conversation history."""
    client = _get_client()
    model = _get_model_name()

    api_messages: List[Dict[str, Any]] = []
    if system_prompt:
        api_messages.append({"role": "system", "content": system_prompt})
    api_messages.extend(messages)

    logger.info(f"LLM stream_with_history | model={model} | turns={len(messages)}")

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=api_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **PRESET_CHAT,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except (APITimeoutError, APIConnectionError, APIError) as e:
        logger.error(f"LLM stream_with_history error: {e}")
        raise


async def check_connectivity() -> Dict[str, bool]:
    """Quick check if the model responds."""
    results = {}
    try:
        resp = await generate("Say OK", max_tokens=5)
        results["qwen"] = len(resp) > 0
    except Exception as e:
        logger.warning(f"LLM connectivity check failed: {e}")
        results["qwen"] = False
    return results

# Made with Bob
