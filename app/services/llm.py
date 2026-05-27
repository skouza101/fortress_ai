"""
LLM Service — Gemini via the OpenAI-compatible API.

Uses the OpenAI-compatible chat completions API.
"""

from __future__ import annotations

import logging
import asyncio
import json
from typing import AsyncGenerator, Optional, List, Dict, Any

import httpx
from openai import AsyncOpenAI, RateLimitError, APIStatusError

from app.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_FALLBACK_MODEL = "gemini-3.5-flash"


# ── Local clients (OpenAI-compatible) ────────────────────────

_gemini_client: Optional[AsyncOpenAI] = None

def _get_client() -> AsyncOpenAI:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_api_base,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            max_retries=settings.LLM_MAX_RETRIES,
        )
    return _gemini_client

def _get_model_name(model: Optional[str] = None) -> str:
    return model or settings.llm_model


def _gemini_native_base_url() -> str:
    return settings.GEMINI_API_BASE.rstrip("/").removesuffix("/openai")


def _gemini_thinking_level(model: str) -> str:
    return "high" if "pro" in model.lower() else "minimal"


def _supports_gemini_thinking(model: str) -> bool:
    model_lower = model.lower()
    return "gemini-3" in model_lower or "gemini-2.5" in model_lower


def _to_gemini_contents(messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    contents: List[Dict[str, Any]] = []
    pending_user_parts: List[str] = []

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if not content:
            continue

        if role == "assistant":
            if pending_user_parts:
                contents.append({
                    "role": "user",
                    "parts": [{"text": "\n\n".join(pending_user_parts)}],
                })
                pending_user_parts = []
            contents.append({"role": "model", "parts": [{"text": content}]})
        else:
            pending_user_parts.append(content)

    if pending_user_parts:
        contents.append({
            "role": "user",
            "parts": [{"text": "\n\n".join(pending_user_parts)}],
        })

    return contents or [{"role": "user", "parts": [{"text": ""}]}]


async def _gemini_stream_content(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str],
    temperature: float,
    max_tokens: int,
    model: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    if not settings.llm_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    original_model = _get_model_name(model)
    selected_model = original_model
    
    max_attempts = 3
    retry_delay = 1.0  # seconds
    fallback_active = False

    for attempt in range(max_attempts):
        url = f"{_gemini_native_base_url()}/models/{selected_model}:streamGenerateContent"
        payload = _build_gemini_payload(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            selected_model=selected_model,
        )

        try:
            async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                async with client.stream(
                    "POST",
                    url,
                    params={"alt": "sse"},
                    headers={
                        "x-goog-api-key": settings.llm_api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    
                    if fallback_active:
                        yield f"*(Note: Gemini 3.1 Pro is currently rate-limited on this API key. Automatically fell back to {GEMINI_FALLBACK_MODEL} to continue your analysis without interruption.)*\n\n"
                        fallback_active = False
                        
                    in_thought = False  # Track if we're inside a thinking block

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue

                        try:
                            event = json.loads(line.removeprefix("data: "))
                            parts = event["candidates"][0]["content"].get("parts", [])
                        except (KeyError, IndexError, json.JSONDecodeError, TypeError):
                            continue

                        for part in parts:
                            text = part.get("text")
                            has_thought_signature = bool(part.get("thoughtSignature") or part.get("thought_signature"))
                            is_thought = bool(part.get("thought", False))

                            if text:
                                if is_thought:
                                    # Gemini thinking part - wrap in <think> tags
                                    if not in_thought:
                                        yield "<think>"
                                        in_thought = True
                                    yield text
                                else:
                                    # Regular content - close thinking block if open
                                    if in_thought:
                                        yield "</think>"
                                        in_thought = False
                                    yield text
                            elif has_thought_signature:
                                logger.debug("Received Gemini thoughtSignature without displayable thought text.")

                    # Close any unclosed thinking block at end of stream
                    if in_thought:
                        yield "</think>"
            # Success, exit function
            return

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 503):
                logger.warning(
                    f"Gemini API returned HTTP {e.response.status_code} for {selected_model} (attempt {attempt + 1}/{max_attempts})"
                )
                
                # If we are on the pro/thinking model and hit a rate limit, fallback to flash
                if selected_model != GEMINI_FALLBACK_MODEL and "pro" in selected_model.lower():
                    logger.info("429 rate limit hit. Falling back to %s.", GEMINI_FALLBACK_MODEL)
                    selected_model = GEMINI_FALLBACK_MODEL
                    fallback_active = True
                    # Small wait before retrying with fallback model
                    await asyncio.sleep(0.5)
                    continue
                
                # Standard exponential backoff retry for other cases
                if attempt < max_attempts - 1:
                    logger.warning(f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
            
            raise


def _gemini_parts_to_text(parts: List[Dict[str, Any]]) -> str:
    output: List[str] = []
    in_thought = False

    for part in parts:
        text = part.get("text")
        if not text:
            continue

        if part.get("thought", False):
            if not in_thought:
                output.append("<think>")
                in_thought = True
            output.append(text)
        else:
            if in_thought:
                output.append("</think>")
                in_thought = False
            output.append(text)

    if in_thought:
        output.append("</think>")

    return "".join(output)


def _build_gemini_payload(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str],
    temperature: float,
    max_tokens: int,
    selected_model: str,
) -> Dict[str, Any]:
    gen_config: Dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max_tokens,
    }

    if _supports_gemini_thinking(selected_model):
        thinking_config: Dict[str, Any] = {"includeThoughts": True}
        model_lower = selected_model.lower()
        if "gemini-3" in model_lower:
            thinking_config["thinkingLevel"] = _gemini_thinking_level(selected_model)
        elif "gemini-2.5" in model_lower:
            thinking_config["thinkingBudget"] = -1
        gen_config["thinkingConfig"] = thinking_config

    payload: Dict[str, Any] = {
        "contents": _to_gemini_contents(messages),
        "generationConfig": gen_config,
    }

    if system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

    return payload


async def _gemini_generate_content(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str],
    temperature: float,
    max_tokens: int,
    model: Optional[str] = None,
) -> str:
    if not settings.llm_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    selected_model = _get_model_name(model)
    retry_delay = 1.0

    for attempt in range(3):
        url = f"{_gemini_native_base_url()}/models/{selected_model}:generateContent"
        payload = _build_gemini_payload(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            selected_model=selected_model,
        )

        try:
            async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    url,
                    headers={
                        "x-goog-api-key": settings.llm_api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 503):
                logger.warning(
                    "Gemini API returned HTTP %s for %s in generate (attempt %d/3)",
                    e.response.status_code,
                    selected_model,
                    attempt + 1,
                )

                if selected_model != GEMINI_FALLBACK_MODEL and "pro" in selected_model.lower():
                    logger.info("Falling back to %s in native generate.", GEMINI_FALLBACK_MODEL)
                    selected_model = GEMINI_FALLBACK_MODEL
                    await asyncio.sleep(0.5)
                    continue

                if attempt < 2:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue

            raise

        try:
            data = response.json()
            candidates = data.get("candidates") or []
            if not candidates:
                logger.warning("Gemini native response missing candidates")
                return ""
            parts = candidates[0].get("content", {}).get("parts", [])
            return _gemini_parts_to_text(parts)
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("Unable to parse Gemini native response: %s", exc)
            return ""

    return ""


# ─── Public API ──────────────────────────────────────────────

async def generate(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    model: Optional[str] = None,
) -> str:
    """Generate a complete response from the LLM (non-streaming)."""
    if settings.LLM_PROVIDER.lower() == "gemini":
        return await _gemini_generate_content(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )

    client = _get_client()
    selected_model = _get_model_name(model)

    messages: List[Dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    logger.info(f"LLM generate | model={selected_model} | provider={settings.LLM_PROVIDER}")

    max_attempts = 3
    retry_delay = 1.0

    for attempt in range(max_attempts):
        try:
            kwargs = {
                "model": selected_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            }
            response = await client.chat.completions.create(**kwargs)
            if not response or not getattr(response, "choices", None):
                logger.warning("LLM response missing choices in generate")
                return ""
            if len(response.choices) == 0:
                logger.warning("LLM response returned empty choices in generate")
                return ""
            message = response.choices[0].message
            content = getattr(message, "content", None) or ""
            logger.info(f"LLM response | response_len={len(content)}")
            return content
        except Exception as e:
            is_429 = False
            if isinstance(e, RateLimitError):
                is_429 = True
            elif isinstance(e, APIStatusError) and e.status_code in (429, 503):
                is_429 = True

            if is_429:
                logger.warning(f"Rate limit or 503 error hit in generate (attempt {attempt + 1}/{max_attempts})")
                if selected_model != GEMINI_FALLBACK_MODEL and "pro" in selected_model.lower():
                    logger.info("Falling back to %s in generate.", GEMINI_FALLBACK_MODEL)
                    selected_model = GEMINI_FALLBACK_MODEL
                    await asyncio.sleep(0.5)
                    continue

                if attempt < max_attempts - 1:
                    logger.warning(f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue

            logger.error(f"LLM generation failed: {e}")
            if "chat template" in str(e).lower():
                return "Error: The LLM service requires a chat template."
            raise


async def stream(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    model: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Stream response chunks from the LLM."""
    if settings.LLM_PROVIDER.lower() == "gemini":
        messages = [{"role": "user", "content": prompt}]
        async for chunk in _gemini_stream_content(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        ):
            yield chunk
        return

    client = _get_client()
    selected_model = _get_model_name(model)

    messages: List[Dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    logger.info(f"LLM stream | model={selected_model} | provider={settings.LLM_PROVIDER}")

    max_attempts = 3
    retry_delay = 1.0

    for attempt in range(max_attempts):
        try:
            kwargs = {
                "model": selected_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            }
            response = await client.chat.completions.create(**kwargs)

            async for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if getattr(delta, "content", None) is not None:
                    yield delta.content
            return
        except Exception as e:
            is_429 = False
            if isinstance(e, RateLimitError):
                is_429 = True
            elif isinstance(e, APIStatusError) and e.status_code in (429, 503):
                is_429 = True

            if is_429:
                logger.warning(f"Rate limit or 503 error hit in stream (attempt {attempt + 1}/{max_attempts})")
                if selected_model != GEMINI_FALLBACK_MODEL and "pro" in selected_model.lower():
                    logger.info("Falling back to %s in stream.", GEMINI_FALLBACK_MODEL)
                    selected_model = GEMINI_FALLBACK_MODEL
                    await asyncio.sleep(0.5)
                    continue

                if attempt < max_attempts - 1:
                    logger.warning(f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue

            logger.error(f"LLM stream failed: {e}")
            if "chat template" in str(e).lower():
                yield "Error: The LLM service requires a chat template."
            else:
                raise


async def generate_with_history(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    model: Optional[str] = None,
) -> str:
    """Generate with full conversation history (for multi-turn chat)."""
    if settings.LLM_PROVIDER.lower() == "gemini":
        gemini_messages = messages
        merged_system_prompt = system_prompt
        system_messages = [m.get("content", "") for m in messages if m.get("role") == "system" and m.get("content")]
        if system_messages:
            merged_system_prompt = "\n\n".join(
                part for part in [system_prompt, *system_messages] if part
            )
            gemini_messages = [m for m in messages if m.get("role") != "system"]

        return await _gemini_generate_content(
            messages=gemini_messages,
            system_prompt=merged_system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )

    client = _get_client()
    selected_model = _get_model_name(model)

    # Consolidate all system messages at the top to satisfy API protocols
    api_messages: List[Dict[str, Any]] = []
    system_content = []
    if system_prompt:
        system_content.append(system_prompt)
    
    # Extract any system messages from history and move to top
    user_assistant_messages = []
    for m in messages:
        if m.get("role") == "system":
            system_content.append(m.get("content", ""))
        else:
            user_assistant_messages.append(m)

    if system_content:
        api_messages.append({"role": "system", "content": "\n\n".join(system_content)})
    
    api_messages.extend(user_assistant_messages)

    logger.info(f"LLM generate_with_history | model={selected_model} | provider={settings.LLM_PROVIDER}")

    max_attempts = 3
    retry_delay = 1.0

    for attempt in range(max_attempts):
        try:
            kwargs = {
                "model": selected_model,
                "messages": api_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            }
            response = await client.chat.completions.create(**kwargs)
            if not response or not getattr(response, "choices", None):
                logger.warning("LLM response missing choices in generate_with_history")
                return ""
            if len(response.choices) == 0:
                logger.warning("LLM response returned empty choices in generate_with_history")
                return ""
            message = response.choices[0].message
            return getattr(message, "content", None) or ""
        except Exception as e:
            is_429 = False
            if isinstance(e, RateLimitError):
                is_429 = True
            elif isinstance(e, APIStatusError) and e.status_code in (429, 503):
                is_429 = True

            if is_429:
                logger.warning(f"Rate limit or 503 error hit in generate_with_history (attempt {attempt + 1}/{max_attempts})")
                if selected_model != GEMINI_FALLBACK_MODEL and "pro" in selected_model.lower():
                    logger.info("Falling back to %s in generate_with_history.", GEMINI_FALLBACK_MODEL)
                    selected_model = GEMINI_FALLBACK_MODEL
                    await asyncio.sleep(0.5)
                    continue

                if attempt < max_attempts - 1:
                    logger.warning(f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue

            logger.error(f"LLM history generate failed: {e}")
            if "chat template" in str(e).lower():
                return "Error: The LLM service requires a chat template."
            raise


async def stream_with_history(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    model: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Stream with full conversation history."""
    if settings.LLM_PROVIDER.lower() == "gemini":
        gemini_messages = messages
        merged_system_prompt = system_prompt
        system_messages = [m.get("content", "") for m in messages if m.get("role") == "system" and m.get("content")]
        if system_messages:
            merged_system_prompt = "\n\n".join(
                part for part in [system_prompt, *system_messages] if part
            )
            gemini_messages = [m for m in messages if m.get("role") != "system"]

        async for chunk in _gemini_stream_content(
            messages=gemini_messages,
            system_prompt=merged_system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        ):
            yield chunk
        return

    client = _get_client()
    selected_model = _get_model_name(model)

    # Consolidate all system messages at the top to satisfy API protocols
    api_messages: List[Dict[str, Any]] = []
    system_content = []
    if system_prompt:
        system_content.append(system_prompt)
    
    # Extract any system messages from history and move to top
    user_assistant_messages = []
    for m in messages:
        if m.get("role") == "system":
            system_content.append(m.get("content", ""))
        else:
            user_assistant_messages.append(m)

    if system_content:
        api_messages.append({"role": "system", "content": "\n\n".join(system_content)})
    
    api_messages.extend(user_assistant_messages)

    logger.info(f"LLM stream_with_history | model={selected_model} | provider={settings.LLM_PROVIDER}")

    try:
        kwargs = {
            "model": selected_model,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        response = await client.chat.completions.create(**kwargs)

        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            # Yield regular content (check is not None, not falsy, to avoid dropping empty strings)
            if getattr(delta, "content", None) is not None:
                yield delta.content
    except Exception as e:
        logger.error(f"LLM history stream failed: {e}")
        if "chat template" in str(e).lower():
            yield "Error: The LLM service requires a chat template."
        else:
            raise


async def check_connectivity() -> Dict[str, bool]:
    """Quick check if the model responds."""
    results = {}
    try:
        resp = await generate("Say OK", max_tokens=5)
        results["gemini"] = len(resp) > 0
    except Exception as e:
        logger.warning(f"LLM connectivity check failed: {e}")
        results["gemini"] = False
    return results
