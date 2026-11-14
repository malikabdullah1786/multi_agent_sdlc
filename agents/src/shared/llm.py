import os
import time
from dotenv import load_dotenv
load_dotenv()
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
# Transient HTTP errors that are safe to retry with a short backoff
_TRANSIENT_HTTP_ERRORS = ("500", "502", "503", "504", "bad gateway", "service unavailable",
                          "connection error", "connection reset", "timeout", "internal server error", "server error")

def get_llm(temperature: float = 0.1, max_tokens: int = 4000):
    """
    Centralized LLM initialization.
    Reads the model from the environment variable LLM_MODEL.
    Uses LLM_PROVIDER to determine the backend (default: groq, alternative: ollama).
    """
    model_name = os.getenv("LLM_MODEL", "llama-3.1-70b-versatile")
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    
    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            from langchain_community.chat_models import ChatOllama

        num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "16384"))
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        return ChatOllama(
            model=model_name,
            temperature=temperature,
            base_url=base_url,
            num_ctx=num_ctx,
            # Keep the connection alive so rapid sequential calls don't get 502s
            keep_alive=-1,
        )
    else:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )


def _log_token_usage(response, label: str = "LLM"):
    """Prints token usage metrics and generation speed."""
    try:
        usage = getattr(response, "usage_metadata", None)
        meta = getattr(response, "response_metadata", {})
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


def llm_invoke_with_retry(llm, prompt, max_retries: int = 6, base_wait: int = 15):
    """
    Invokes an LLM with automatic retry on:
    - 429 rate-limit / TPM exceeded / 413 token limit errors
    - 502/503/504 transient errors
    """
    for attempt in range(max_retries):
        try:
            res = llm.invoke(prompt)
            _log_token_usage(res, label="LLM")
            return res
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "rate_limit" in err or "413" in err or "tokens per minute" in err or "tpm" in err:
                wait = base_wait * (attempt + 1)
                print(f"[LLM] TPM / Rate limited (attempt {attempt+1}/{max_retries}). Waiting {wait}s for token bucket reset...")
                time.sleep(wait)
            elif any(code in err for code in _TRANSIENT_HTTP_ERRORS):
                wait = 5 * (attempt + 1)
                print(f"[LLM] Transient HTTP error (attempt {attempt+1}/{max_retries}): {str(e)[:120]}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"LLM call failed after {max_retries} retries.")


def llm_tool_invoke_with_retry(llm_with_tools, messages, agent_name: str = "Agent", max_retries: int = 6, base_wait: int = 15):
    """
    Drop-in replacement for `llm_with_tools.invoke(messages)` in multi-turn agent loops.
    - Handles TPM/rate limit (429, 413, tokens per minute) with progressive wait.
    - Handles transient HTTP errors (502, 503, 504).
    - Automatically trims older conversational turns if payload size hits TPM limit.
    - Handles Groq tool_use_failed (e.g. attempted to call tool 'json') by nudging the model.
    """
    from langchain_core.messages import AIMessage, HumanMessage

    import json

    for attempt in range(max_retries):
        try:
            res = llm_with_tools.invoke(messages)
            _log_token_usage(res, label=agent_name)
            return res
        except Exception as e:
            err = str(e).lower()
            if "tool_use_failed" in err or "attempted to call tool" in err:
                print(f"[{agent_name}] Tool formatting error from LLM. Extracting payload if present...")
                # If Groq rejected the call because model called tool 'json' with the file payload,
                # extract that payload directly into an AIMessage so the agent loop finishes!
                error_str = str(e)
                try:
                    import re
                    match = re.search(r"'failed_generation':\s*('|\")(.*)('|\")\s*\}\s*\}", error_str, re.DOTALL)
                    if match:
                        raw_json_str = match.group(2).replace("\\n", "\n").replace('\\"', '"').replace("\\'", "'")
                        # Return an AIMessage with the content as markdown json block
                        return AIMessage(content=f"```json\n{raw_json_str}\n```")
                except Exception:
                    pass
                messages.append(HumanMessage(
                    content="SYSTEM NOTICE: Do not output markdown code blocks or hallucinated tools like 'json'. You must strictly invoke one of the provided function tools directly."
                ))
                time.sleep(2)
                continue
            elif "413" in err or "tokens per minute" in err or "tpm" in err or "429" in err or "rate_limit" in err:
                # If message history is growing too long in multi-turn agent, aggressively trim
                if len(messages) > 2:
                    print(f"[{agent_name}] Context too large for TPM limit ({len(messages)} messages). Aggressively pruning conversation history...")
                    # Keep system prompt (messages[0]) and only the very latest message
                    messages[:] = [messages[0], messages[-1]]
                wait = base_wait * (attempt + 1)
                print(f"[{agent_name}] Rate limited/TPM limit hit (attempt {attempt+1}/{max_retries}). Waiting {wait}s...")
                time.sleep(wait)
            elif any(code in err for code in _TRANSIENT_HTTP_ERRORS):
                wait = 5 * (attempt + 1)
                print(f"[{agent_name}] Transient LLM error (attempt {attempt+1}/{max_retries}): {str(e)[:100]}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"[{agent_name}] LLM tool call failed after {max_retries} retries.")


import concurrent.futures
from langchain_community.tools.ddg_search.tool import DuckDuckGoSearchResults

def safe_web_search(query: str, timeout: int = 5) -> str:
    """
    Executes DuckDuckGo search with a strict timeout to prevent indefinite hangs.
    """
    search_tool = DuckDuckGoSearchResults(backend="html")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(search_tool.invoke, {"query": query})
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return "Search timed out. Proceeding without web results."
        except Exception as e:
            return f"Search failed: {e}"
