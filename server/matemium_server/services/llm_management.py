"""
LLM Management, Cost Tracking, Autonomous Pricing.

Responsibilities:
- Track real money we spend on providers (our cost).
- Apply profit margin to automatically price tokens for users.
- Log every platform call with accurate token + dollar cost.
- Provide helpers for picking providers, calculating deductions.
- Future: health of our provider balances, auto-replenish hooks.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ..config import settings
from .supabase import SupabaseService, get_supabase_service

# Base pricing (USD per 1M tokens). These are our purchase costs.
# Can be overridden / extended in llm_model_pricing table.
DEFAULT_PRICING: dict[tuple[str, str], dict[str, float]] = {
    ("openai", "gpt-4o-mini"): {"input": 0.15, "output": 0.60},
    ("openai", "gpt-4o"): {"input": 2.50, "output": 10.00},
    ("groq", "llama-3.1-70b"): {"input": 0.59, "output": 0.79},
    ("xai", "grok-2"): {"input": 2.00, "output": 10.00},
    # Audio is usually priced per 1M characters or per request; approximate here
    ("openai", "tts-1"): {"input": 15.0, "output": 0.0},   # rough per 1M chars
}


async def get_profit_margin() -> float:
    """Global profit margin (e.g. 0.40 = 40%). Can be changed in system_settings."""
    supabase = get_supabase_service()
    rows = await supabase._rest_get("system_settings", {"key": "eq.llm_profit_margin", "select": "value"})
    if rows:
        try:
            val = rows[0]["value"]
            if isinstance(val, (int, float, str)):
                return float(val)
        except Exception:
            pass
    return getattr(settings, "llm_default_margin", 0.40)


def get_model_cost_per_million(provider: str, model: str) -> dict[str, float]:
    """Our cost per million tokens (input/output)."""
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
    Returns our_cost_usd, user_price_usd (with margin), suggested_credits.
    """
    margin = await get_profit_margin()
    pricing = get_model_cost_per_million(provider, model)

    p_tok = prompt_tokens or 0
    c_tok = completion_tokens or 0

    input_cost = (p_tok / 1_000_000) * pricing["input"]
    output_cost = (c_tok / 1_000_000) * pricing["output"]
    our_cost = round(input_cost + output_cost, 6)

    user_price = round(our_cost * (1 + margin), 6)

    # Simple credit model: 1 credit ≈ $0.001 (or make configurable)
    # For now we map price to "credits". You can tune this.
    credits = max(1, int(user_price * 1000))   # e.g. $0.001 = 1 credit

    return {
        "our_cost_usd": our_cost,
        "user_price_usd": user_price,
        "margin": margin,
        "charged_credits": credits,
        "prompt_tokens": p_tok,
        "completion_tokens": c_tok,
    }


async def record_platform_usage(
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
    Log the call + calculate cost + deduct appropriate credits from user.
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
        "charged_credits": calc["charged_credits"],
        "margin_applied": calc["margin"],
        "request_id": request_id,
        "metadata": extra or {},
    }

    await supabase.log_llm_usage(log_data)

    # Deduct the credits the user owes us
    if calc["charged_credits"] > 0:
        await supabase.adjust_llm_credits(user_id, -calc["charged_credits"])

    return calc


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
    Very basic autonomous health.
    In future: compare spend against budgets in llm_providers, suggest top-ups.
    """
    supabase = get_supabase_service()
    providers = await supabase.list_active_platform_providers()
    summary = await get_spend_summary()

    recommendations = []
    for p in providers:
        budget = float(p.get("monthly_budget_usd") or 0)
        # Very rough: we don't have per-provider monthly yet, so global hint
        if budget > 0 and summary["total_cost_usd"] > budget * 0.8:
            recommendations.append({
                "provider": p["name"],
                "message": "Approaching or over budget. Consider replenishing.",
                "current_spend": summary["total_cost_usd"],
                "budget": budget,
            })

    return {
        "margin": await get_profit_margin(),
        "total_platform_spend_usd": summary["total_cost_usd"],
        "active_providers": len(providers),
        "recommendations": recommendations,
    }
