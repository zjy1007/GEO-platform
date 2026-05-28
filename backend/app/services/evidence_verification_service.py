"""Claim verification (P3.2).

For one AI answer: split atomic claims about the merchant (LLM) → retrieve the most
relevant evidence (char-bigram similarity, no extra deps) → NLI judge supported/
contradicted/unsupported (LLM) → store verification_results. evidence_rate =
supported / total claims (doc §七).

Pure helpers (parse_claims / similarity / retrieve_evidence / parse_verification /
compute_evidence_rate) are unit-tested; LLM + DB live verification runs in container.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import EvidenceSource
from app.models.geo import ProviderResult, VerificationResult
from app.models.merchant import Merchant
from app.prompts import load_prompt, render
from app.providers.base import BaseChannel, LLMRequest
from app.providers.json_utils import repair_json

VALID_STATUS = {"supported", "contradicted", "unsupported"}
_RETRIEVAL_THRESHOLD = 0.3


def _bigrams(s: str) -> set[str]:
    s = "".join((s or "").split())
    if len(s) < 2:
        return {s} if s else set()
    return {s[i : i + 2] for i in range(len(s) - 1)}


def similarity(claim: str, text: str) -> float:
    cb = _bigrams(claim)
    if not cb:
        return 0.0
    return len(cb & _bigrams(text)) / len(cb)


def retrieve_evidence(claim: str, evidences: list[dict], threshold: float = _RETRIEVAL_THRESHOLD):
    """Return (best_evidence, score). best is None if nothing clears the threshold."""
    best, best_score = None, 0.0
    for e in evidences:
        s = similarity(claim, e.get("content_text") or "")
        if s > best_score:
            best, best_score = e, s
    return (best, round(best_score, 4)) if best_score >= threshold else (None, round(best_score, 4))


def build_split_prompt(answer: str, merchant_name: str) -> tuple[str, str]:
    cfg = load_prompt("split_claims")
    return cfg["system"], render(cfg["template"], name=merchant_name or "", answer=answer or "")


def parse_claims(raw: object) -> list[dict]:
    if isinstance(raw, dict):
        raw = raw.get("claims") or raw.get("data") or []
    out: list[dict] = []
    for it in raw if isinstance(raw, list) else []:
        if isinstance(it, str):
            claim, ctype = it, None
        elif isinstance(it, dict):
            claim = it.get("claim") or it.get("text")
            ctype = it.get("claim_type") or it.get("type")
        else:
            continue
        if claim and str(claim).strip():
            out.append({"claim": str(claim).strip(), "claim_type": ctype})
    return out


def build_verify_prompt(claim: str, evidence_text: str) -> tuple[str, str]:
    cfg = load_prompt("verify_claims")
    return cfg["system"], render(cfg["template"], claim=claim, evidence=evidence_text or "")


def parse_verification(raw: object) -> dict:
    d = raw if isinstance(raw, dict) else {}
    status = d.get("status")
    status = status if status in VALID_STATUS else "unsupported"
    try:
        confidence = float(d.get("confidence"))
    except (TypeError, ValueError):
        confidence = None
    return {"status": status, "confidence": confidence, "reason": d.get("reason")}


def compute_evidence_rate(statuses: list[str]) -> float | None:
    """supported / total claims. None when there are no claims."""
    total = len(statuses)
    if total == 0:
        return None
    return round(sum(1 for s in statuses if s == "supported") / total, 4)


async def verify_answer(
    session: AsyncSession,
    pr: ProviderResult,
    merchant: Merchant,
    evidences: list[EvidenceSource],
    channel: BaseChannel,
) -> list[VerificationResult]:
    sys_p, user_p = build_split_prompt(pr.answer_text or "", merchant.name)
    resp = await channel.chat(
        LLMRequest(provider=channel.provider_name,
                   messages=[{"role": "system", "content": sys_p}, {"role": "user", "content": user_p}],
                   temperature=0.0, max_tokens=1024)
    )
    if resp.status != "ok":
        raise RuntimeError(resp.error_message or "claim split failed")
    claims = parse_claims(repair_json(resp.content))

    ev = [{"id": e.id, "content_text": e.content_text} for e in evidences]
    results: list[VerificationResult] = []
    for cl in claims:
        best, _score = retrieve_evidence(cl["claim"], ev)
        if best is None:
            vr = VerificationResult(
                provider_result_id=pr.id, claim_text=cl["claim"],
                verification_status="unsupported", evidence_source_id=None,
                confidence=0.0, explanation="未找到相关证据",
            )
        else:
            vsys, vuser = build_verify_prompt(cl["claim"], best["content_text"])
            vresp = await channel.chat(
                LLMRequest(provider=channel.provider_name,
                           messages=[{"role": "system", "content": vsys}, {"role": "user", "content": vuser}],
                           temperature=0.0, max_tokens=300)
            )
            if vresp.status != "ok":
                raise RuntimeError(vresp.error_message or "claim verify failed")
            parsed = parse_verification(repair_json(vresp.content))
            vr = VerificationResult(
                provider_result_id=pr.id, claim_text=cl["claim"],
                verification_status=parsed["status"], evidence_source_id=best["id"],
                confidence=parsed["confidence"], explanation=parsed["reason"],
            )
        session.add(vr)
        results.append(vr)
    await session.flush()
    return results


async def fetch_run_verification_statuses(session: AsyncSession, run_id) -> list[str]:
    stmt = (
        select(VerificationResult.verification_status)
        .join(ProviderResult, VerificationResult.provider_result_id == ProviderResult.id)
        .where(ProviderResult.run_id == run_id)
    )
    return [s for (s,) in (await session.execute(stmt)).all() if s]


async def list_verifications(session: AsyncSession, run_id) -> list[VerificationResult]:
    stmt = (
        select(VerificationResult)
        .join(ProviderResult, VerificationResult.provider_result_id == ProviderResult.id)
        .where(ProviderResult.run_id == run_id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def pending_verify_result_ids(session: AsyncSession, run_id) -> list:
    already = select(VerificationResult.provider_result_id)
    stmt = select(ProviderResult.id).where(
        ProviderResult.run_id == run_id,
        ProviderResult.status == "ok",
        ProviderResult.id.notin_(already),
    )
    return list((await session.execute(stmt)).scalars().all())
