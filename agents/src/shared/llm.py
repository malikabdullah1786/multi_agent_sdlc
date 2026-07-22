import os
import time
from langchain_groq import ChatGroq

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
            
        return ChatOllama(
            model=model_name,
            temperature=temperature
        )
    else:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )


def llm_invoke_with_retry(llm, prompt, max_retries: int = 5, base_wait: int = 15):
    """
    Invokes an LLM with automatic exponential backoff on 429 rate limit errors.
    """
    for attempt in range(max_retries):
        try:
            return llm.invoke(prompt)
        except Exception as e:
            err = str(e)
            if "429" in err or "rate_limit" in err.lower():
                wait = base_wait * (attempt + 1)
                print(f"[LLM] Rate limited (attempt {attempt+1}/{max_retries}). Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"LLM call failed after {max_retries} retries due to rate limiting.")


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
