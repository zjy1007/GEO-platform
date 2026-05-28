"""Mention / rank / sentiment extraction (P1.5).

For each provider answer, one analysis call returns: is_mentioned, rank_position,
sentiment, and the full list of brands+order (mentioned_brands, used for competitor
visibility in P4). A deterministic alias-substring floor guards against LLM false
negatives on exact matches.

Pure helpers (build_mention_prompt / parse_mention) are unit-tested.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geo import MentionResult, ProviderResult
from app.models.merchant import Merchant, MerchantAlias
from app.prompts import load_prompt, render
from app.providers.base import BaseChannel, LLMRequest
from app.providers.json_utils import repair_json

VALID_SENTIMENTS = {"positive", "neutral", "negative", "mixed"}
_MIN_ALIAS_LEN = 3  # avoid matching very short/generic tokens


def build_mention_prompt(answer: str, merchant: Merchant, aliases: list[str]) -> tuple[str, str]:
    cfg = load_prompt("extract_mentions")
    user = render(
        cfg["template"],
        name=merchant.name or "",
        aliases="、".join(aliases) if aliases else "无",
        address=merchant.address or "无",
        city=merchant.city or "",
        district=merchant.district or "",
        answer=answer or "",
    )
    return cfg["system"], user


def _norm_brands(brands: object) -> list[dict]:
    out: list[dict] = []
    if not isinstance(brands, list):
        return out
    for i, b in enumerate(brands):
        if isinstance(b, str):
            name = b.strip()
            rank: int | None = i + 1
        elif isinstance(b, dict):
            name = (b.get("brand") or b.get("name") or "").strip()
            raw_rank = b.get("rank")
            rank = int(raw_rank) if isinstance(raw_rank, (int, float)) and raw_rank else None
        else:
            continue
        if name:
            out.append({"brand": name, "rank": rank})
    return out


def _alias_hit(answer: str, aliases: list[str]) -> str | None:
    if not answer:
        return None
    for a in aliases:
        if a and len(a) >= _MIN_ALIAS_LEN and a in answer:
            return a
    return None


def parse_mention(raw: object, answer: str, aliases: list[str]) -> dict:
    data = raw if isinstance(raw, dict) else {}

    is_mentioned = bool(data.get("is_mentioned"))

    rank = data.get("rank_position")
    rank = int(rank) if isinstance(rank, (int, float)) and rank and rank > 0 else None

    sentiment = data.get("sentiment")
    sentiment = sentiment if sentiment in VALID_SENTIMENTS else "neutral"

    try:
        confidence = float(data.get("confidence"))
    except (TypeError, ValueError):
        confidence = None

    brands = _norm_brands(data.get("mentioned_brands"))
    mention_text = data.get("mention_text") or data.get("matched_name")

    # deterministic floor: an exact alias appearing in the answer means it IS mentioned
    hit = _alias_hit(answer, aliases)
    if hit and not is_mentioned:
        is_mentioned = True
        if confidence is None or confidence < 0.6:
            confidence = 0.6
        if not mention_text:
            mention_text = hit

    if not is_mentioned:
        rank = None  # rank is meaningless when not mentioned

    return {
        "is_mentioned": is_mentioned,
        "mention_text": mention_text,
        "rank_position": rank,
        "mentioned_brands": brands,
        "sentiment": sentiment,
        "confidence": confidence,
    }


async def load_alias_names(session: AsyncSession, merchant_id) -> list[str]:
    rows = (
        await session.execute(select(MerchantAlias.alias).where(MerchantAlias.merchant_id == merchant_id))
    ).scalars().all()
    return [a for a in rows if a]


async def extract_for_result(
    session: AsyncSession,
    pr: ProviderResult,
    merchant: Merchant,
    aliases: list[str],
    channel: BaseChannel,
) -> MentionResult:
    system, user = build_mention_prompt(pr.answer_text or "", merchant, aliases)
    resp = await channel.chat(
        LLMRequest(
            provider=channel.provider_name,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.0,
            max_tokens=1024,
        )
    )
    if resp.status != "ok":
        raise RuntimeError(resp.error_message or "analysis call failed")
    raw = repair_json(resp.content)
    fields = parse_mention(raw, pr.answer_text or "", aliases)

    mr = MentionResult(provider_result_id=pr.id, merchant_id=merchant.id, **fields)
    session.add(mr)
    await session.flush()
    return mr


async def pending_result_ids(session: AsyncSession, run_id) -> list:
    already = select(MentionResult.provider_result_id)
    stmt = select(ProviderResult.id).where(
        ProviderResult.run_id == run_id,
        ProviderResult.status == "ok",
        ProviderResult.id.notin_(already),
    )
    return list((await session.execute(stmt)).scalars().all())


async def list_mentions(session: AsyncSession, run_id) -> list[MentionResult]:
    stmt = (
        select(MentionResult)
        .join(ProviderResult, MentionResult.provider_result_id == ProviderResult.id)
        .where(ProviderResult.run_id == run_id)
    )
    return list((await session.execute(stmt)).scalars().all())
