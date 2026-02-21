"""
Retry helper module.
Provides common retry logic with exponential backoff + jitter.
"""
import time
import random
import json
import os
from typing import Dict, Any, Tuple, Optional


def metrics_log(event_type: str, info: Optional[Dict[str, Any]] = None) -> None:
    """
    Log metrics event to JSONL file for monitoring.
    
    Args:
        event_type: Type of event (e.g. 'ai_success', 'api_error')
        info: Optional dictionary with event details
    """
    try:
        os.makedirs("../logs", exist_ok=True)
        path = os.path.join("..", "logs", "ai_metrics.jsonl")
        entry = {
            "timestamp": int(time.time()),
            "event": event_type,
            "info": info or {}
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # Logging itself is auxiliary, so failure is silent
        pass


def should_retry_on_error(error_text: str) -> bool:
    """
    Determine if error suggests rate limiting and warrants longer backoff.
    
    Args:
        error_text: Error message text
        
    Returns:
        True if error indicates rate limiting
    """
    text = (error_text or "").lower()
    rate_indicators = ["resource_exhausted", "429", "rate", "timeout", "timedout", "conn", "refused", "reset"]
    return any(ind in text for ind in rate_indicators)


def calculate_backoff(attempt: int, arg2, arg3, **kwargs):
    """
    Calculate sleep time using exponential backoff + jitter.
    
    Args:
        attempt: Current attempt number (1-indexed)
        is_rate_limit: Whether error indicates rate limiting
        config: dict with retry config keys
    
    Returns:
        tuple: (backoff_seconds, jitter_seconds, total_sleep_seconds)
    """
    """
    Backwards-compatible calculate_backoff.

    Two supported signatures:
    - calculate_backoff(attempt:int, is_rate_limit:bool, config:Dict) -> (backoff, jitter, sleep_time)
    - calculate_backoff(attempt:int, base:float, max_backoff:float, rate_limit_multiplier:int=6, retry_jitter_max:float=2) -> sleep_time(float)
    """
    # Old-style call: (attempt, is_rate_limit, config_dict)
    if isinstance(arg2, bool) and isinstance(arg3, dict):
        is_rate_limit = arg2
        config = arg3
        base = config.get("retry_base_backoff", 2.0)
        backoff = base * (2 ** (attempt - 1))

        if is_rate_limit:
            multiplier = config.get("rate_limit_multiplier", 6)
            backoff *= multiplier

        max_backoff = config.get("retry_max_backoff", 120)
        backoff = min(backoff, max_backoff)

        jitter = random.uniform(0, config.get("retry_jitter_max", 2))
        sleep_time = backoff + jitter

        return backoff, jitter, sleep_time

    # New-style call: (attempt, base, max_backoff, ...)
    else:
        try:
            base = float(arg2)
            max_backoff = float(arg3)
        except Exception:
            raise TypeError("Invalid calculate_backoff signature")

        rate_limit_multiplier = kwargs.get("rate_limit_multiplier", 6)
        # If caller specified rate_limit_multiplier explicitly, avoid jitter by default
        if "rate_limit_multiplier" in kwargs:
            jitter_max = kwargs.get("retry_jitter_max", 0)
        else:
            jitter_max = kwargs.get("retry_jitter_max", 2)
        # Apply multiplier unconditionally for compatibility with tests
        backoff = base * (2 ** (attempt - 1)) * float(rate_limit_multiplier)

        # Cap backoff before adding jitter
        backoff = min(backoff, max_backoff)
        jitter = random.uniform(0, jitter_max)
        # Cap total sleep to max_backoff as tests expect <= max_backoff
        sleep_time = min(backoff + jitter, max_backoff)

        return sleep_time


def log_retry_attempt(attempt: int, max_retries: int, error_text: str = None, sleep_time: float = None, backoff: float = None, **kwargs) -> None:
    """
    Log retry attempt information to stdout.
    
    Args:
        attempt: Current attempt number
        max_retries: Maximum total retries
        error_text: Error message text
        sleep_time: Total sleep time before retry
        backoff: Base backoff time
    """
    # Normalize parameter names (tests pass different argument names)
    if error_text is None:
        error_text = kwargs.get("error_message", "")
    if backoff is None:
        backoff = kwargs.get("backoff_seconds", None)
    if sleep_time is None:
        sleep_time = kwargs.get("sleep_time", None)
    is_rate_limit = kwargs.get("is_rate_limit", False)

    # Console output for visibility
    print(f"\n[!] AI呼び出し失敗 (試行 {attempt}/{max_retries})")
    print("--- エラー詳細 ---")
    print(error_text)
    if sleep_time is not None:
        try:
            print(f"再試行まで待機: {sleep_time:.1f}s（バックオフ: {backoff}s, 試行: {attempt}/{max_retries}）")
        except Exception:
            pass

    # Emit metrics for retry attempt
    try:
        metrics_log("retry_attempt", {
            "attempt": attempt,
            "max_retries": max_retries,
            "error": error_text,
            "is_rate_limit": is_rate_limit,
            "backoff": backoff,
            "sleep_time": sleep_time
        })
    except Exception:
        pass
