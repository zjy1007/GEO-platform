"""元宝（腾讯）扫码登录 + 一题抓包（P2 最小验证 · 步骤 1）

干嘛用：在真实浏览器里走一次「登录 → 提问 → 收回答」的完整动线，
把所有元宝域名下的网络响应都抠下来。我（开发者）拿到这份 JSON 后，
就能定位到「回答正文」和「引用源列表」分别藏在哪个接口的哪个字段，
据此修正 backend/app/providers/web/yuanbao_web.py 里的 parser。

跑法（在仓库根目录 geo-platform/）：
    source backend/.venv/bin/activate
    python scripts/yuanbao_bootstrap.py

会弹一个 Chromium 窗口（小心别关），按窗口提示走：
    1) 用元宝 / 微信 App 扫码登录（profile 复用，登过之后下次免登）
    2) 在元宝输入框里随便问一个**带本地信息**的问题，建议：
         "杭州滨江哪家宠物医院好？"
       —— 带城市/区域的问题更可能触发联网搜索，引用源会更丰富
    3) **务必把"联网搜索"开关打开**（元宝界面里那个开关，不然没引用源）
    4) 等回答完整生成完毕（看到完整内容 + 引用列表展开）
    5) 回这个终端，按 Enter 结束抓包

产出：
    - 登录态保存到：~/.geo-playwright-profiles/yuanbao-001/
    - 抓包数据保存到：geo-platform/.tmp/yuanbao_capture_<时间戳>.json

⚠️ 这两个路径都 gitignored，profile 内含 cookie，**严禁手动 commit 或外发**。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Response, sync_playwright

PROFILE_DIR = Path.home() / ".geo-playwright-profiles" / "yuanbao-001"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / ".tmp"
OUT_DIR.mkdir(exist_ok=True)
OUT_FILE = OUT_DIR / f"yuanbao_capture_{datetime.now():%Y%m%d_%H%M%S}.json"

# 只捕这些域，避免被全站资源刷屏
DOMAIN_HINTS = ("yuanbao.tencent.com", "yuanbao", "hunyuan")
# 只关心这些响应类型（接口/流），过滤掉 png/css/js
CONTENT_TYPE_HINTS = ("application/json", "text/event-stream", "text/plain", "application/x-ndjson")

captured: list[dict] = []


def _interesting(response: Response) -> bool:
    url = response.url
    if not any(h in url for h in DOMAIN_HINTS):
        return False
    ct = (response.headers.get("content-type") or "").lower()
    return any(h in ct for h in CONTENT_TYPE_HINTS)


def on_response(response: Response) -> None:
    try:
        if not _interesting(response):
            return
        try:
            body = response.text()
        except Exception as e:  # 流可能未完结/已关闭
            body = f"<read failed: {e}>"
        req = response.request
        req_body = None
        try:
            if req.method in ("POST", "PUT", "PATCH"):
                req_body = req.post_data
                if req_body and len(req_body) > 4000:
                    req_body = req_body[:4000] + "…<truncated>"
        except Exception:
            pass
        item = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "method": req.method,
            "url": response.url,
            "status": response.status,
            "content_type": response.headers.get("content-type"),
            "req_body": req_body,
            "body_len": len(body or ""),
            # 保留前 8KB 足够看结构；完整原文太大不利于阅读
            "body_preview": (body or "")[:8000],
        }
        captured.append(item)
        # 实时打印一条短日志，让你知道抓到了
        sys.stdout.write(f"  [cap] {req.method} {response.status} {response.url[:90]}\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write(f"  [err] {e}\n")


def main() -> int:
    print("====================================================")
    print(" 元宝扫码 + 抓包  (P2 最小验证 步骤 1)")
    print("====================================================")
    print(f" profile: {PROFILE_DIR}")
    print(f" 输出   : {OUT_FILE}")
    print("====================================================")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 860},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.on("response", on_response)

        try:
            page.goto("https://yuanbao.tencent.com/", wait_until="domcontentloaded", timeout=60_000)
        except Exception as e:
            print(f"[warn] 首屏加载报错（可忽略，继续操作即可）: {e}")

        print("\n>>> 浏览器已打开元宝。请按顺序操作：")
        print("    1) 未登录就用元宝/微信 App 扫码登录")
        print("    2) ⚠️ 打开元宝界面的 [联网搜索] 开关（不开就没引用源）")
        print("    3) 在输入框里随便问一个问题（建议：杭州滨江哪家宠物医院好？）")
        print("    4) 等回答完整生成 + 引用源都出来")
        print("    5) 回到这里按 Enter 结束抓包\n")
        input(">>> 一切就绪后按 Enter: ")

        try:
            ctx.storage_state(path=str(PROFILE_DIR / "storage_state.json"))
        except Exception as e:
            print(f"[warn] 保存 storage_state 失败: {e}")
        ctx.close()

    OUT_FILE.write_text(json.dumps(captured, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 抓到 {len(captured)} 条响应，已保存到:\n   {OUT_FILE}")
    print("   把这个文件路径告诉助手，我来分析字段结构、修 yuanbao_web.py。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
