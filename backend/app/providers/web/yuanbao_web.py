"""腾讯元宝 web channel parser (P2.4 — locked against real packet capture 2026-06-01).

实际抓包 (yuanbao.tencent.com) 显示元宝走 SSE 流，回答与引用源都在
`POST /api/chat/{conversation_id}` 的 text/event-stream 响应里：

    data: {"type":"text", "msg":"<答案分片>"}
    data: {"type":"searchGuid", "docs":[<引用条目>...], "citations":[...]}

driver 拿到原始 SSE 文本后，先用 :func:`parse_sse` 转成 normalized payload
`{"answer": str, "docs": list, "citations": list}`，再走标准 locate_* 接口。
这样 SSE 解析与字段提取解耦，便于单测 + 兼容老的占位 payload 形态。
"""
import json

from app.providers.base import LLMRequest, LLMResponse
from app.providers.web_base import WebChannel


def parse_sse(raw: str) -> dict:
    """元宝 SSE 流 → normalized payload。

    返回:
        {"answer":  str,                 # type=text 的 msg 顺序拼接
         "docs":    list[dict],          # type=searchGuid 的 docs[]（plugin/网页引用）
         "citations": list[dict]}        # type=searchGuid 的 citations[]（footnote 编号引用）

    无法解析的 data 行（如 `data: status`、`data: search_with_text`）会被静默跳过；
    联网关闭时 docs/citations 自然为空，不报错。
    """
    answer_parts: list[str] = []
    docs: list[dict] = []
    cits: list[dict] = []
    seen: set = set()

    def _dedupe_key(item: dict) -> object:
        return item.get("docId") or item.get("url") or (item.get("title"), item.get("index"))

    for chunk in (raw or "").split("\n\n"):
        data_lines = [line[5:].lstrip() for line in chunk.splitlines() if line.startswith("data:")]
        if not data_lines:
            continue
        try:
            obj = json.loads("\n".join(data_lines))
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        t = obj.get("type")
        if t == "text":
            msg = obj.get("msg")
            if isinstance(msg, str):
                answer_parts.append(msg)
        elif t == "searchGuid":
            for d in obj.get("docs") or []:
                if isinstance(d, dict):
                    k = _dedupe_key(d)
                    if k not in seen:
                        seen.add(k)
                        docs.append(d)
            for c in obj.get("citations") or []:
                if isinstance(c, dict):
                    k = _dedupe_key(c)
                    if k not in seen:
                        seen.add(k)
                        cits.append(c)
    return {"answer": "".join(answer_parts), "docs": docs, "citations": cits}


class YuanbaoWebChannel(WebChannel):
    """腾讯元宝联网版 web channel."""

    provider_name = "yuanbao"

    # 真包字段 → Citation 字段。source_name 若 web_site_name 缺失，
    # locate_citations 会按 sourceType 兜底（plugin 类除外）。
    field_map = {
        "title": "title",
        "url": "url",
        "snippet": "quote",
        "source_name": "web_site_name",
    }

    # --- SSE 解析对外暴露，便于 driver / 测试调用 ---
    @staticmethod
    def parse_sse(raw: str) -> dict:
        return parse_sse(raw)

    def locate_answer(self, payload: dict) -> str:
        """优先读 normalized 'answer'；兜底兼容若干占位/嵌套形式。"""
        if not isinstance(payload, dict):
            return ""
        for key in ("answer", "reply"):
            v = payload.get(key)
            if isinstance(v, str) and v:
                return v
        data = payload.get("data")
        if isinstance(data, dict):
            v = data.get("content")
            if isinstance(v, str) and v:
                return v
        return ""

    def locate_citations(self, payload: dict) -> list[dict]:
        """合并 docs + citations；同时兼容老占位字段 `references`。

        plugin 类 sourceType 的 web_site_name 通常为空——这里**复制**条目并把
        非 plugin 的 sourceType 回填到 web_site_name，避免下游 source_name 为空。
        不就地修改输入。
        """
        if not isinstance(payload, dict):
            return []
        out: list[dict] = []
        for key in ("docs", "citations", "references"):
            v = payload.get(key)
            if not isinstance(v, list):
                continue
            for item in v:
                if not isinstance(item, dict):
                    continue
                item = dict(item)
                if not item.get("web_site_name"):
                    st = item.get("sourceType")
                    if st and st != "plugin":
                        item["web_site_name"] = st
                out.append(item)
        return out

    async def _drive_session(self, request: LLMRequest) -> LLMResponse:
        """Playwright 驱动 — 待 P2 最小闭环接入（下一步）。

        实现要点：
          1. 用 ~/.geo-playwright-profiles/yuanbao-<account_id> 打开持久 profile
          2. 确认 [联网搜索] 开关已开
          3. 注入 init script 包 fetch/EventSource 抓 /api/chat/* 的 SSE 流
          4. 调用 :func:`parse_sse` → 走 build_response_from_payload
        """
        raise NotImplementedError(
            "YuanbaoWebChannel._drive_session 待接 Playwright 驱动（最小闭环步骤）"
        )
