import os
import time
import concurrent.futures
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Transient HTTP errors that are safe to retry with a short backoff
_TRANSIENT_HTTP_ERRORS = (
    "500", "502", "503", "504", "bad gateway", "service unavailable",
    "connection error", "connection reset", "timeout", "timed out",
    "internal server error", "server error",
)


def _is_rate_or_token_limit(err: str) -> bool:
    return any(
        k in err
        for k in (
            "429", "rate_limit", "413", "tokens per minute", "tpm",
            "request too large", "resource_exhausted", "quota",
        )
    )


def _get_gemini_api_key() -> str:
    return (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()


def _build_gemini(model_name: str, temperature: float, max_tokens: int):
    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key = _get_gemini_api_key()
    if not api_key:
        raise ValueError("GOOGLE_API_KEY / GEMINI_API_KEY is not set.")

    timeout = float(os.getenv("LLM_TIMEOUT", "90"))
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=temperature,
        max_output_tokens=max_tokens,
        timeout=timeout,
        max_retries=1,
    )


def _build_ollama(model_name: str, temperature: float, max_tokens: int):
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        from langchain_community.chat_models import ChatOllama

    num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    timeout = float(os.getenv("LLM_TIMEOUT", "180"))

    return ChatOllama(
        model=model_name,
        temperature=temperature,
        base_url=base_url,
        num_ctx=num_ctx,
        num_predict=max_tokens,
        keep_alive=-1,
        client_kwargs={"timeout": timeout},
    )


def _build_groq(model_name: str, temperature: float, max_tokens: int):
    from langchain_groq import ChatGroq

    timeout = float(os.getenv("LLM_TIMEOUT", "90"))
    return ChatGroq(
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        request_timeout=timeout,
        max_retries=1,
    )


def _build_provider(provider: str, temperature: float, max_tokens: int, tier: str = "heavy"):
    provider = provider.lower().strip()
    if provider == "gemini":
        fast_default = os.getenv("GEMINI_FAST_MODEL", "gemini-2.5-flash")
        heavy_default = os.getenv("GEMINI_HEAVY_MODEL", "gemini-2.5-flash")
        configured = os.getenv("LLM_MODEL", "")
        if tier == "fast":
            model_name = fast_default
        elif configured and configured.startswith("gemini"):
            model_name = configured
        else:
            model_name = heavy_default
        return _build_gemini(model_name, temperature, max_tokens)

    if provider == "groq":
        fast_default = os.getenv("GROQ_FAST_MODEL", "openai/gpt-oss-20b")
        heavy_default = os.getenv("GROQ_HEAVY_MODEL", "qwen/qwen3.8-27b")
        configured = os.getenv("LLM_MODEL", "")
        if tier == "fast":
            model_name = fast_default
        elif configured and ":" not in configured and not configured.startswith("gemini"):
            model_name = configured
        else:
            model_name = heavy_default
        return _build_groq(model_name, temperature, max_tokens)

    # Ollama (local)
    env_key = "OLLAMA_FAST_MODEL" if tier == "fast" else "OLLAMA_FALLBACK_MODEL"
    model_name = os.getenv(env_key, os.getenv("OLLAMA_MODEL", "llama3.2:3b"))
    return _build_ollama(model_name, temperature, max_tokens)


def _provider_of(llm) -> str:
    cls_name = type(llm).__name__
    if "Google" in cls_name or "Gemini" in cls_name:
        return "gemini"
    if "Groq" in cls_name:
        return "groq"
    return "ollama"


def get_llm(temperature: float = 0.1, max_tokens: int = 4000, tier: str = "heavy"):
    """
    Centralized LLM initialization with priority chain:
    gemini (Google AI Studio) -> groq -> ollama (local).
    If primary provider's API key is missing, automatically starts at the next available provider.
    """
    primary = os.getenv("LLM_PROVIDER", "gemini").lower().strip()
    if primary == "gemini" and not _get_gemini_api_key():
        primary = "groq" if os.getenv("GROQ_API_KEY") else "ollama"
    elif primary == "groq" and not os.getenv("GROQ_API_KEY"):
        primary = "ollama"

    return _build_provider(primary, temperature, max_tokens, tier=tier)


def get_fallback_chain(primary_llm, max_tokens: int = 4000) -> list:
    """
    Returns ordered fallback LLMs:
      gemini -> [groq, ollama]
      groq   -> [ollama]
      ollama -> [groq] (if key present)
    """
    if os.getenv("ENABLE_LLM_FALLBACK", "true").lower() == "false":
        return []

    temperature = getattr(primary_llm, "temperature", 0.1) or 0.1
    current = _provider_of(primary_llm)

    if current == "gemini":
        order = ["groq", "ollama"]
    elif current == "groq":
        order = ["ollama"]
    else:
        order = ["groq"]

    fallbacks = []
    for prov in order:
        if prov == "groq" and not os.getenv("GROQ_API_KEY"):
            continue
        if prov == "gemini" and not _get_gemini_api_key():
            continue
        try:
            fallbacks.append(_build_provider(prov, temperature, max_tokens, tier="heavy"))
        except Exception:
            continue
    return fallbacks


def get_fallback_llm(primary_llm, max_tokens: int = 4000):
    """Returns the first available fallback LLM (backward-compatible helper)."""
    chain = get_fallback_chain(primary_llm, max_tokens=max_tokens)
    return chain[0] if chain else None


def needs_external_research(user_req: str) -> bool:
    """
    Fast deterministic gate replacing redundant YES/NO LLM calls in research_node.
    Returns True only when the request references external APIs, existing codebases,
    compliance standards, or specialized integrations.
    """
    text = (user_req or "").lower()
    research_signals = (
        "existing codebase", "integrate with", "compliance", "hipaa", "gdpr",
        "pci", "soc2", "oauth", "stripe", "webhook", "graphql", "kubernetes",
        "microservice", "migrate", "legacy", "third-party", "sdk", "documentation",
    )
    if any(sig in text for sig in research_signals):
        return True
    return len(text) > 500


def _log_token_usage(response, label: str = "LLM"):
    """Prints token usage metrics and generation speed."""
    try:
        usage = getattr(response, "usage_metadata", None)
        meta = getattr(response, "response_metadata", {}) or {}
        if usage:
            inp = usage.get("input_tokens", 0)
            out = usage.get("output_tokens", 0)
            tot = usage.get("total_tokens", inp + out)
            dur = meta.get("eval_duration", 0)
            speed = f" | {out / (dur / 1e9):.1f} tok/s" if dur and out else ""
            print(f"\033[96m[{label} Metrics] Prompt: {inp} | Output: {out} | Total: {tot} tokens{speed}\033[0m")
        elif "eval_count" in meta:
            inp = meta.get("prompt_eval_count", 0)
            out = meta.get("eval_count", 0)
            dur = meta.get("eval_duration", 0)
            speed = f" | {out / (dur / 1e9):.1f} tok/s" if dur and out else ""
            print(f"\033[96m[{label} Metrics] Prompt: {inp} | Output: {out} | Total: {inp+out} tokens{speed}\033[0m")
    except Exception:
        pass


def llm_invoke_with_retry(llm, prompt, max_retries: int = 2, base_wait: int = 4, label: str = "LLM"):
    """
    Invokes an LLM with bounded retry on rate-limits/transient errors and
    automatic multi-tier fallback: Gemini -> Groq -> Ollama.
    """
    last_error: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            res = llm.invoke(prompt)
            _log_token_usage(res, label=label)
            return res
        except Exception as e:
            last_error = e
            err = str(e).lower()
            if _is_rate_or_token_limit(err):
                wait = base_wait * (attempt + 1)
                print(f"[{label}] Rate/token limit hit (attempt {attempt+1}/{max_retries}). Waiting {wait}s...")
                time.sleep(wait)
            elif any(code in err for code in _TRANSIENT_HTTP_ERRORS):
                wait = 3 * (attempt + 1)
                print(f"[{label}] Transient error (attempt {attempt+1}/{max_retries}): {str(e)[:120]}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                break

    base_llm = getattr(llm, "bound", llm)
    for fb in get_fallback_chain(base_llm):
        prov = _provider_of(fb).upper()
        try:
            print(f"[{label}] Falling back to {prov} ({getattr(fb, 'model', getattr(fb, 'model_name', ''))})...")
            res = fb.invoke(prompt)
            _log_token_usage(res, label=f"{label}-{prov}")
            return res
        except Exception as fb_err:
            last_error = fb_err
            print(f"[{label}] Fallback {prov} failed: {str(fb_err)[:120]}")

    raise RuntimeError(f"[{label}] All LLM providers failed. Last error: {last_error}")


def llm_tool_invoke_with_retry(
    llm_with_tools,
    messages,
    agent_name: str = "Agent",
    max_retries: int = 3,
    base_wait: int = 4,
    tools=None,
):
    """
    Drop-in replacement for `llm_with_tools.invoke(messages)` in multi-turn agent loops.
    Handles TPM/rate limits, transient HTTP errors, Groq malformed tool calls,
    aggressive history pruning, and multi-tier fallback (Gemini -> Groq -> Ollama).
    """
    from langchain_core.messages import AIMessage, HumanMessage
    import re

    last_error: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            res = llm_with_tools.invoke(messages)
            _log_token_usage(res, label=agent_name)
            return res
        except Exception as e:
            last_error = e
            err = str(e).lower()
            if "tool_use_failed" in err or "attempted to call tool" in err:
                print(f"[{agent_name}] Tool formatting error from LLM. Extracting payload if present...")
                error_str = str(e)
                try:
                    match = re.search(r"'failed_generation':\s*('|\")(.*)('|\")\s*\}\s*\}", error_str, re.DOTALL)
                    if match:
                        raw_json_str = match.group(2).replace("\\n", "\n").replace('\\"', '"').replace("\\'", "'")
                        return AIMessage(content=f"```json\n{raw_json_str}\n```")
                except Exception:
                    pass
                messages.append(HumanMessage(
                    content="SYSTEM NOTICE: Do not output markdown code blocks or hallucinated tools like 'json'. You must strictly invoke one of the provided function tools directly."
                ))
                time.sleep(1)
                continue
            elif _is_rate_or_token_limit(err):
                if len(messages) > 2:
                    print(f"[{agent_name}] Context too large ({len(messages)} msgs). Pruning history...")
                    messages[:] = [messages[0], messages[-1]]
                wait = base_wait * (attempt + 1)
                print(f"[{agent_name}] Rate/TPM limit hit (attempt {attempt+1}/{max_retries}). Waiting {wait}s...")
                time.sleep(wait)
            elif any(code in err for code in _TRANSIENT_HTTP_ERRORS):
                wait = 3 * (attempt + 1)
                print(f"[{agent_name}] Transient error (attempt {attempt+1}/{max_retries}): {str(e)[:100]}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                break

    # Multi-tier fallback preserving bound tools if available
    bound = getattr(llm_with_tools, "bound", llm_with_tools)
    bound_tools = tools or getattr(llm_with_tools, "kwargs", {}).get("tools")
    for fb in get_fallback_chain(bound):
        prov = _provider_of(fb).upper()
        try:
            target = fb.bind_tools(bound_tools) if bound_tools else fb
            print(f"[{agent_name}] Falling back to {prov}...")
            res = target.invoke(messages)
            _log_token_usage(res, label=f"{agent_name}-{prov}")
            return res
        except Exception as fb_err:
            last_error = fb_err
            print(f"[{agent_name}] Fallback {prov} failed: {str(fb_err)[:120]}")

    raise RuntimeError(f"[{agent_name}] All LLM providers failed. Last error: {last_error}")


def safe_web_search(query: str, timeout: int = 5) -> str:
    """
    Executes DuckDuckGo search with a strict timeout to prevent indefinite hangs.
    """
    from langchain_community.tools.ddg_search.tool import DuckDuckGoSearchResults

    search_tool = DuckDuckGoSearchResults(backend="html")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(search_tool.invoke, {"query": query})
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return "Search timed out. Proceeding without web results."
        except Exception as e:
            return f"Search failed: {e}"
