"""Render a GEO report (report_json) into a self-contained HTML document.

Structure mirrors docs/样例-GEO品牌诊断报告.html: headline score, per-platform
decision/doubt tables, phase comparison, competitor visibility, citation ranking
(placeholder until the account pool lands in P2), and optimization suggestions.
"""
from html import escape

_PROVIDER_LABEL = {
    "deepseek": "DeepSeek", "qwen": "通义千问", "zhipu": "智谱", "kimi": "Kimi",
    "doubao": "豆包", "yuanbao": "元宝", "nami": "纳米AI", "baidu": "文心",
}
_PHASE_LABEL = {"decision": "品牌决策期", "doubt": "负面质疑期"}
_PRIORITY_LABEL = {"high": "高", "medium": "中", "low": "低"}


def _pct(x: float) -> str:
    return f"{(x or 0) * 100:.0f}%"


def _provider(p: str) -> str:
    return _PROVIDER_LABEL.get(p, p or "-")


def _score_grade(score: float) -> str:
    if score >= 75:
        return "优秀"
    if score >= 50:
        return "中等"
    if score >= 25:
        return "偏低"
    return "较差"


def _provider_phase_table(rows: list[dict]) -> str:
    if not rows:
        return "<p class='muted'>暂无数据</p>"
    trs = []
    for r in rows:
        trs.append(
            "<tr>"
            f"<td>{_provider(r['provider'])}</td>"
            f"<td>{_PHASE_LABEL.get(r['phase'], r['phase'] or '-')}</td>"
            f"<td>{_pct(r['mention_rate'])}</td>"
            f"<td>{r['avg_rank'] if r['avg_rank'] is not None else '-'}</td>"
            f"<td>{r['mentioned']}/{r['total']}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>平台</th><th>阶段</th><th>提及率</th><th>平均排名</th><th>提及/总数</th>"
        "</tr></thead><tbody>" + "".join(trs) + "</tbody></table>"
    )


def _phase_compare_table(by_phase: dict) -> str:
    trs = []
    for ph in ("decision", "doubt"):
        m = by_phase.get(ph, {})
        trs.append(
            "<tr>"
            f"<td>{_PHASE_LABEL[ph]}</td>"
            f"<td>{_pct(m.get('mention_rate', 0))}</td>"
            f"<td>{_pct(m.get('exposure_avg', 0))}</td>"
            f"<td>{_pct(m.get('positive_rate', 0))}</td>"
            f"<td>{m.get('mentioned', 0)}/{m.get('total', 0)}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>阶段</th><th>提及率</th><th>曝光加权</th><th>正向描述率</th><th>提及/总数</th>"
        "</tr></thead><tbody>" + "".join(trs) + "</tbody></table>"
    )


def _competitor_table(competitors: list[dict]) -> str:
    if not competitors:
        return "<p class='muted'>暂无竞品数据</p>"
    trs = []
    for i, c in enumerate(competitors[:10], 1):
        tag = "<span class='tag'>本商家</span>" if c["is_target"] else ""
        trs.append(
            "<tr>"
            f"<td>{i}</td>"
            f"<td>{escape(c['brand'])} {tag}</td>"
            f"<td>{c['appearances']}</td>"
            f"<td>{_pct(c['rate'])}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>#</th><th>商家/品牌</th><th>被提及次数</th><th>可见度</th>"
        "</tr></thead><tbody>" + "".join(trs) + "</tbody></table>"
    )


_PRIORITY_TIER = {"high": "第一优先级", "medium": "第二优先级", "low": "第三优先级"}


def _citation_section(ranking: list[dict], investment: list[dict]) -> str:
    if not ranking and not investment:
        return ("<div class='note'>该板块需账号池（Web 渠道）联网搜索引用源数据，"
                "将在 P2 账号池接入后填充。</div>")
    parts = []
    if ranking:
        trs = "".join(
            f"<tr><td>{i}</td><td>{escape(r['label'])}</td><td>{r['count']}</td><td>{_pct(r['rate'])}</td></tr>"
            for i, r in enumerate(ranking, 1)
        )
        parts.append(
            "<h3 class='sub'>引用源平台排行榜</h3>"
            "<table><thead><tr><th>#</th><th>来源</th><th>被引用次数</th><th>占比</th></tr></thead>"
            f"<tbody>{trs}</tbody></table>"
        )
    if investment:
        trs = "".join(
            f"<tr><td>{escape(s['label'])}</td><td>{s['percentage']}%</td>"
            f"<td>{_PRIORITY_TIER.get(s['priority'], s['priority'])}</td></tr>"
            for s in investment
        )
        parts.append(
            "<h3 class='sub'>信源投放建议</h3>"
            "<table><thead><tr><th>建议投放来源</th><th>建议占比</th><th>优先级</th></tr></thead>"
            f"<tbody>{trs}</tbody></table>"
        )
    return "".join(parts)


def _recommendations(recs: list[dict]) -> str:
    items = [
        f"<li><span class='prio prio-{r['priority']}'>{_PRIORITY_LABEL.get(r['priority'], r['priority'])}</span>"
        f"{escape(r['text'])}</li>"
        for r in recs
    ]
    return "<ul class='recs'>" + "".join(items) + "</ul>"


def render_html(report: dict, run_created_at: str = "") -> str:
    merchant = report.get("merchant", {})
    name = escape(merchant.get("name") or "未命名商家")
    sub = " · ".join(x for x in [merchant.get("city"), merchant.get("category")] if x)
    score = report.get("geo_score", 0)
    overall = report.get("overall", {})

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} · GEO 品牌诊断报告</title>
<style>
  :root {{ --brand:#2f6df6; }}
  * {{ box-sizing:border-box; }}
  body {{ font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; color:#1f2329; margin:0; background:#f5f7fa; }}
  .wrap {{ max-width:960px; margin:0 auto; padding:32px 20px 64px; }}
  header {{ display:flex; align-items:center; justify-content:space-between; gap:24px; background:#fff; border-radius:14px; padding:28px 32px; box-shadow:0 1px 4px rgba(0,0,0,.06); }}
  header h1 {{ font-size:22px; margin:0 0 6px; }}
  header .muted {{ color:#86909c; font-size:14px; }}
  .score {{ text-align:center; }}
  .score .num {{ font-size:48px; font-weight:700; color:var(--brand); line-height:1; }}
  .score .grade {{ color:#86909c; font-size:13px; margin-top:6px; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:14px; margin:20px 0; }}
  .card {{ background:#fff; border-radius:12px; padding:18px; box-shadow:0 1px 4px rgba(0,0,0,.06); }}
  .card .k {{ color:#86909c; font-size:13px; }}
  .card .v {{ font-size:24px; font-weight:700; margin-top:6px; }}
  section {{ background:#fff; border-radius:12px; padding:22px 24px; margin:16px 0; box-shadow:0 1px 4px rgba(0,0,0,.06); }}
  section h2 {{ font-size:16px; margin:0 0 14px; padding-left:10px; border-left:4px solid var(--brand); }}
  h3.sub {{ font-size:14px; color:#4e5969; margin:18px 0 8px; }}
  h3.sub:first-of-type {{ margin-top:0; }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; }}
  th,td {{ text-align:left; padding:9px 10px; border-bottom:1px solid #eef0f3; }}
  th {{ color:#86909c; font-weight:500; background:#fafbfc; }}
  .muted {{ color:#86909c; }}
  .tag {{ background:#e8f0ff; color:var(--brand); font-size:12px; padding:1px 7px; border-radius:4px; }}
  .note {{ background:#fff7e6; color:#a8741a; border-radius:8px; padding:12px 14px; font-size:13px; }}
  .recs {{ list-style:none; padding:0; margin:0; }}
  .recs li {{ padding:10px 0; border-bottom:1px solid #eef0f3; font-size:14px; }}
  .prio {{ display:inline-block; min-width:30px; text-align:center; border-radius:4px; font-size:12px; padding:1px 6px; margin-right:10px; color:#fff; }}
  .prio-high {{ background:#f53f3f; }} .prio-medium {{ background:#ff9a2e; }} .prio-low {{ background:#86909c; }}
  footer {{ color:#a9b0bb; font-size:12px; text-align:center; margin-top:24px; }}
</style></head>
<body><div class="wrap">
  <header>
    <div><h1>{name}</h1><div class="muted">{escape(sub)}</div>
      <div class="muted" style="margin-top:8px">生成时间：{escape(run_created_at)}</div></div>
    <div class="score"><div class="num">{score}</div><div class="muted">GEO 效果评估评分 / 100</div>
      <div class="grade">等级：{_score_grade(score)}</div></div>
  </header>

  <div class="cards">
    <div class="card"><div class="k">AI 提及率</div><div class="v">{_pct(overall.get('mention_rate', 0))}</div></div>
    <div class="card"><div class="k">曝光/排名加权</div><div class="v">{_pct(overall.get('exposure_avg', 0))}</div></div>
    <div class="card"><div class="k">正向描述率</div><div class="v">{_pct(overall.get('positive_rate', 0))}</div></div>
    <div class="card"><div class="k">证据可验证率</div><div class="v">{_pct(report['evidence_rate']) if report.get('evidence_rate') is not None else '—'}</div></div>
    <div class="card"><div class="k">资料完整度</div><div class="v">{report.get('completeness', 0)}</div></div>
  </div>

  <section><h2>各平台 × 决策期 / 质疑期</h2>{_provider_phase_table(report.get('by_provider_phase', []))}</section>
  <section><h2>决策期 vs 负面质疑期</h2>{_phase_compare_table(report.get('by_phase', {}))}</section>
  <section><h2>竞品可见度对比</h2>{_competitor_table(report.get('competitors', []))}</section>
  <section><h2>引用源平台排行榜 / 信源投放建议</h2>
    {_citation_section(report.get('citation_ranking', []), report.get('source_investment', []))}</section>
  <section><h2>优化建议</h2>{_recommendations(report.get('recommendations', []))}</section>

  <footer>本报告当前为 API 渠道「模型记忆」口径；真实曝光率与引用源数据在 P2 账号池接入后提供。</footer>
</div></body></html>"""
