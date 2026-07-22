"""
LLM usage telemetry.

Responsibilities:
- Estimate provider usage cost for observability.
- Log BYO/local model calls when needed.
- Never deduct Matemium credits or apply resale margins.
"""

from __future__ import annotations

from typing import Any

from .supabase import SupabaseService, get_supabase_service

# Base pricing (USD per 1M tokens) for usage observability only.
# Users pay their chosen provider directly through their own account.
DEFAULT_PRICING: dict[tuple[str, str], dict[str, float]] = {
    ("openai", "gpt-4o-mini"): {"input": 0.15, "output": 0.60},
    ("openai", "gpt-4o"): {"input": 2.50, "output": 10.00},
    ("groq", "llama-3.1-70b"): {"input": 0.59, "output": 0.79},
    ("xai", "grok-2"): {"input": 2.00, "output": 10.00},
    # Audio is usually priced per 1M characters or per request; approximate here
    ("openai", "tts-1"): {"input": 15.0, "output": 0.0},   # rough per 1M chars
}


async def get_profit_margin() -> float:
    """Deprecated compatibility helper. Matemium does not apply provider margins."""
    return 0.0


def get_model_cost_per_million(provider: str, model: str) -> dict[str, float]:
    """Estimated provider cost per million tokens (input/output)."""
    key = (provider.lower(), model)
    if key in DEFAULT_PRICING:
        return DEFAULT_PRICING[key]
    # Fallback cheap model
    return {"input": 0.50, "output": 1.50}


async def calculate_cost_and_price(
    provider: str,
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> dict[str, Any]:
    """
    Returns estimated provider cost for telemetry. No Matemium price or credits.
    """
    pricing = get_model_cost_per_million(provider, model)

    p_tok = prompt_tokens or 0
    c_tok = completion_tokens or 0

    input_cost = (p_tok / 1_000_000) * pricing["input"]
    output_cost = (c_tok / 1_000_000) * pricing["output"]
    our_cost = round(input_cost + output_cost, 6)

    return {
        "our_cost_usd": our_cost,
        "user_price_usd": our_cost,
        "margin": 0.0,
        "charged_credits": 0,
        "prompt_tokens": p_tok,
        "completion_tokens": c_tok,
    }


async def record_provider_usage(
    user_id: str,
    provider_name: str,
    model: str,
    call_type: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    request_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Log the call and estimate provider cost without deducting credits.
    Returns the calculation result.
    """
    supabase: SupabaseService = get_supabase_service()

    calc = await calculate_cost_and_price(provider_name, model, prompt_tokens, completion_tokens)

    log_data = {
        "user_id": user_id,
        "provider_name": provider_name,
        "model": model,
        "call_type": call_type,
        "prompt_tokens": calc["prompt_tokens"],
        "completion_tokens": calc["completion_tokens"],
        "total_tokens": (calc["prompt_tokens"] or 0) + (calc["completion_tokens"] or 0),
        "cost_usd": calc["our_cost_usd"],
        "charged_credits": 0,
        "margin_applied": 0,
        "request_id": request_id,
        "metadata": extra or {},
    }

    await supabase.log_llm_usage(log_data)

    return {**calc, "charged_credits": 0, "margin": 0}


async def get_spend_summary() -> dict[str, Any]:
    """Simple aggregate spend for admin."""
    supabase = get_supabase_service()
    # This is a naive sum - for real use you would do proper SQL aggregates or materialized views.
    rows = await supabase._rest_get(
        "llm_usages",
        {"select": "cost_usd,charged_credits,provider_name,model,created_at"},
    )
    total_cost = sum(float(r.get("cost_usd") or 0) for r in rows)
    total_credits = sum(int(r.get("charged_credits") or 0) for r in rows)
    by_provider: dict[str, float] = {}
    for r in rows:
        p = r.get("provider_name", "unknown")
        by_provider[p] = by_provider.get(p, 0) + float(r.get("cost_usd") or 0)

    return {
        "total_cost_usd": round(total_cost, 4),
        "total_charged_credits": total_credits,
        "by_provider": {k: round(v, 4) for k, v in by_provider.items()},
        "call_count": len(rows),
    }


async def get_autonomous_status() -> dict[str, Any]:
    """
    Basic autonomous health for the BYO/local model architecture.
    """
    summary = await get_spend_summary()

    return {
        "margin": await get_profit_margin(),
        "total_provider_cost_usd": summary["total_cost_usd"],
        "active_providers": 0,
        "recommendations": [],
    }
