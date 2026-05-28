"""Question generation (P1.3).

Each question is tagged with both mode (organic/diagnostic) and phase
(decision/doubt) — see doc §二. organic questions never name the merchant
(used for real-exposure eval); diagnostic questions may reference it.

Pure helpers (build_generation_prompt / normalize_questions) are unit-tested.
generate_and_store accepts an injectable channel so tests can feed canned output.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geo import GeoPrompt
from app.models.merchant import Merchant
from app.prompts import load_prompt, render
from app.providers.base import BaseChannel, LLMRequest
from app.providers.factory import build_channel
from app.providers.json_utils import repair_json

TIER_COUNTS = {"basic": 20, "standard": 50, "professional": 100}
VALID_MODES = {"organic", "diagnostic"}
VALID_PHASES = {"decision", "doubt"}

_PROFILE_FIELDS = ("name", "category", "city", "district", "services")


def build_generation_prompt(merchant: dict, mode: str, phase: str, count: int) -> tuple[str, str]:
    cfg = load_prompt("generate_questions")
    services = merchant.get("services") or []
    services_str = "、".join(services) if isinstance(services, list) else str(services)
    merchant_line = ""
    if mode == "diagnostic" and merchant.get("name"):
        merchant_line = f"\n目标商家：{merchant['name']}"
    user = render(
        cfg["template"],
        count=count,
        phase_label=cfg["phase_label"][phase],
        mode_guidance=cfg["mode_guidance"][mode],
        phase_guidance=cfg["phase_guidance"][phase],
        category=merchant.get("category") or "",
        city=merchant.get("city") or "",
        district=merchant.get("district") or "",
        services=services_str,
        merchant_line=merchant_line,
    )
    return cfg["system"], user


def normalize_questions(raw: object, mode: str, phase: str, merchant: dict) -> list[dict]:
    """Turn raw LLM JSON into rows ready for GeoPrompt construction."""
    if isinstance(raw, dict):
        raw = raw.get("questions") or raw.get("data") or []
    if not isinstance(raw, list):
        return []

    rows: list[dict] = []
    for it in raw:
        if isinstance(it, str):
            question, scenario, intent = it, None, None
        elif isinstance(it, dict):
            question = it.get("question") or it.get("q") or it.get("text")
            scenario = it.get("scenario_type") or it.get("scenario")
            intent = it.get("intent")
        else:
            continue
        if not question or not str(question).strip():
            continue
        rows.append(
            {
                "prompt_text": str(question).strip(),
                "scenario_type": scenario,
                "intent": intent,
                "mode": mode,
                "phase": phase,
                "city": merchant.get("city"),
                "category": merchant.get("category"),
            }
        )
    return rows


async def generate_and_store(
    session: AsyncSession,
    merchant: Merchant,
    *,
    count: int,
    modes: list[str],
    phases: list[str],
    provider: str = "deepseek",
    channel: BaseChannel | None = None,
) -> list[GeoPrompt]:
    ch = channel or build_channel(provider, "api")
    merchant_dict = {f: getattr(merchant, f, None) for f in _PROFILE_FIELDS}

    buckets = [(m, p) for m in modes for p in phases]
    per_bucket = max(1, count // len(buckets))

    created: list[GeoPrompt] = []
    errors: list[str] = []
    for mode, phase in buckets:
        system, user = build_generation_prompt(merchant_dict, mode, phase, per_bucket)
        resp = await ch.chat(
            LLMRequest(
                provider=provider,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.7,
                max_tokens=2048,
            )
        )
        if resp.status != "ok":
            errors.append(f"{mode}/{phase}: {resp.error_message}")
            continue
        try:
            raw = repair_json(resp.content)
        except ValueError as e:
            errors.append(f"{mode}/{phase}: JSON 解析失败 ({e})")
            continue
        for row in normalize_questions(raw, mode, phase, merchant_dict):
            gp = GeoPrompt(merchant_id=merchant.id, **row)
            session.add(gp)
            created.append(gp)

    if not created:
        raise RuntimeError("问题生成失败：" + ("; ".join(errors) or "无有效问题"))

    await session.commit()
    for gp in created:
        await session.refresh(gp)
    return created


async def list_prompts(
    session: AsyncSession,
    merchant_id,
    mode: str | None = None,
    phase: str | None = None,
) -> list[GeoPrompt]:
    stmt = select(GeoPrompt).where(GeoPrompt.merchant_id == merchant_id)
    if mode:
        stmt = stmt.where(GeoPrompt.mode == mode)
    if phase:
        stmt = stmt.where(GeoPrompt.phase == phase)
    stmt = stmt.order_by(GeoPrompt.created_at.desc())
    return list((await session.execute(stmt)).scalars().all())
