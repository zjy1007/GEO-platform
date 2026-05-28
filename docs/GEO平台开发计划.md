# GEO 商家画像平台 — 开发计划

> 本计划依据《一、GEO 商家画像.md》（25 节）与样例产物《南京医科大学友谊整形外科医院_GEO品牌诊断报告.html》制定。
> 资源口径：**1–2 人全栈小团队**，串行为主、可并行处少量并行。工期为净开发周（不含需求反复/外部等待），按人周(pw)给区间。
> 战略主线（来自文档第二十五节）：**先用 API 把整条流水线跑通，再把最难、最易碎的账号池逐平台换进来**——每接通一个平台都是可见进展，整体风险最低。

---

## 0. 一页纸总览

| 阶段 | 名称 | 交付价值 | 工期(1–2人) | 依赖 |
|---|---|---|---|---|
| P0 | 工程基建与骨架 | 可运行的空壳：DB/队列/Docker/配置 | 0.5–1 pw | — |
| P1 | API 跑通闭环 + HTML 报告 | **能生成完整诊断报告 HTML**（数据为模型记忆口径） | 3–4 pw | P0 |
| P2 | 账号池 Web 渠道 | **真实曝光率 + 引用源 + 信源投放**（产品核心价值） | 3–5 pw | P1 |
| P3 | 证据系统 | 证据可验证率、证据缺口分析 | 2–3 pw | P1 |
| P4 | 竞品分析 | 竞品可见度对比、差距建议 | 1–2 pw | P1（大部分随提及抽取顺带完成） |
| P5 | 商业化与打磨 | 多租户、PDF 导出、历史趋势、监控 | 2–3 pw | P1–P4 |

**首要目标（来自文档定位）**：先把 P0+P1 打通，能完整生成出 GEO 诊断报告 HTML。这是验证"除渠道外所有环节都对"的最快路径。

**MVP 核心闭环**：
```
商家信息 → 生成问题(决策期+质疑期) → 多平台调用 → 提及/排名/情感抽取(含竞品) → 打分 → 渲染 HTML 报告
```

---

## 1. 不可动摇的产品口径（贯穿所有阶段）

这几条是系统能不能"做准"的前提，任何阶段的任务都必须遵守：

1. **两种测评模式正交存在**
   - `organic_eval`（真实曝光）：**绝不把商家完整资料喂给模型**，否则测的是"被投喂结果"而非真实曝光。
   - `diagnostic_eval`（资料诊断）：允许把商家资料 + 证据 + 竞品一起喂给模型做分析。
2. **两个情绪阶段正交存在**：每条问题同时带 `mode`(organic/diagnostic) + `phase`(decision 决策期/正面 | doubt 质疑期/负面)。**提及率、排名、竞品对比一律按 phase 分开统计**，不能混。
3. **双渠道分工**：测评走账号池(web channel)，分析走 API(api channel)。引用源、真实曝光率、信源投放建议**纯 API 拿不到**。
4. **总分口径以报告为准**：MVP 阶段总分 ≈ `AI 提及率(各平台综合) × 排名/曝光加权`；7 因子加权是远期目标，证据可验证率/信息一致性等子指标先算、先展示，但**不进总分**直到 P3 数据可靠。
5. **报告维度对齐样例 HTML**：8 平台(DeepSeek/豆包/元宝/千问/文心/纳米/Kimi/智谱) × (决策期 + 质疑期)，外加引用源平台排行榜、竞品数据对比、信源投放建议、优化建议。

---

## 2. 技术栈（采用文档第二十三节最终选型）

```
前端：Next.js + TypeScript + Ant Design Pro + ECharts + TanStack Query + Zod
后端：FastAPI + SQLAlchemy(async) + asyncpg + Pydantic
队列：Redis + Celery（或 Arq，单人可优先 Arq 更轻）
模型调用：统一 OpenAI-compatible Adapter + 各家 SDK
账号池：Playwright(chromium)，每账号独立 user_data_dir profile
文件存储：MinIO
向量检索：PostgreSQL + pgvector
部署：Docker Compose
监控：Prometheus + Grafana + Sentry（小团队可先只上 Sentry）
```

> 小团队取舍：队列可先用 **Arq**（比 Celery 配置轻）；监控 P1 阶段先只接 Sentry，Prometheus/Grafana 留到 P5。

---

## P0 · 工程基建与骨架（0.5–1 pw）

**目标**：一条命令把空壳跑起来，后续所有功能往里填。

任务：
- [ ] 按文档第十节目录结构搭 `backend/` + `frontend/` 骨架
- [ ] `docker-compose.yml`：postgres(+pgvector) / redis / minio / backend / frontend
- [ ] FastAPI 启动 + `/health`；`core/config.py` 用 pydantic-settings 读环境变量
- [ ] Alembic 接好，建第一版迁移（先建 merchants 系列表，见 §数据库顺序）
- [ ] `core/logging.py`（结构化日志 + trace_id）、`core/security.py`（鉴权骨架）
- [ ] Provider 配置表用 YAML（文档第六节格式），`api_key_env` 引用环境变量，**Key 绝不入库明文**
- [ ] 前端起 Next.js + AntD Pro 模板，跑通一个能调后端 `/health` 的页面

**验收**：`docker compose up` 后前端能打开、后端 `/health` 通、数据库迁移成功、Sentry 收到一次测试事件。

---

## P1 · API 跑通整条流水线 + HTML 报告（3–4 pw）

**目标**：只接 4 个 OpenAI 兼容平台（DeepSeek / 通义 / 智谱 / Kimi），把"商家→问题→调用→抽取→打分→报告"全链路跑通。**明确接受**：本阶段引用源为空、提及率是"模型记忆"而非真实曝光。

### P1.1 商家资料与画像（0.5–1 pw）
- [ ] `POST /api/merchants`、`POST /api/merchants/{id}/assets`（PDF/Word/Excel/图片，存 MinIO 私有桶 + 签名 URL）
- [ ] 文档解析（pypdf/python-docx/openpyxl）+ OCR（图片）→ 资料结构化为商家画像 JSON（文档第五节示例结构）
- [ ] 别名生成（LLM）写入 `merchant_aliases`；资料完整度评分；NAP 一致性检查骨架
- [ ] 前端：商家资料页（基础资料 / 别名管理 / 服务项目 / 证据链接 / 完整度评分）

**验收**：上传一份商家资料 → 自动产出结构化画像 + 别名 + 完整度分数。

### P1.2 Provider Adapter 统一适配层（0.5–1 pw）— *关键基础设施*
- [ ] `BaseChannel` 抽象 + `LLMRequest/LLMResponse/Citation`（文档第六节 Pydantic 模型，含 `channel` 与 `citations` 字段，为 P2 预留）
- [ ] `OpenAICompatibleChannel`（覆盖 DeepSeek/通义/智谱/Kimi，只改 base_url）
- [ ] 调用层能力：超时 / 重试(tenacity) / 限流 / 熔断 / token 统计 / 成本统计 / 原始响应保存 / JSON 输出修复 / `health_check`
- [ ] `GET /api/providers` 健康检查与状态

> **注意（文档第三节）**：模型名以官方为准，不要写死臆测型号（如 `deepseek-v4-pro` 等需核实）；豆包用 endpoint id 而非 model 名（P3/P2 再接）。

**验收**：用同一 `LLMRequest` 调通 4 个平台，返回统一 `LLMResponse`；断网/超时能正确重试与熔断。

### P1.3 问题生成（0.5 pw）
- [ ] 问题生成 Prompt（文档第十三节），按行业/城市/区域/服务生成
- [ ] **每条问题打 `mode` + `phase` 双标签**；决策期与质疑期两套问题都要生成
- [ ] 分层：基础版 20 / 标准版 50 / 专业版 100；写入 `geo_prompts`

**验收**：对一个商家生成出正面 + 负面两套问题，标签齐全，存库可查。

### P1.4 异步任务队列与并发（0.5 pw）
- [ ] `POST /api/geo-runs` 创建 run → 生成 prompt_jobs → 入队 → Worker 并发调用
- [ ] 任务状态机：created/queued/running/partial_failed/completed/failed/cancelled
- [ ] API 渠道按 qps/并发限流（文档第十四节 rate_limits）；失败指数退避；超时标 retryable
- [ ] `GET /api/geo-runs/{id}` 返回进度（total/finished/failed/progress）
- [ ] 前端：GEO 测评页（选平台/问题数/模式/启动/进度/失败重跑）+ RunProgressDrawer

**验收**：启动一次 50 题测评，进度实时更新，失败任务可单独重跑。

### P1.5 回答入库 + 提及/排名/情感抽取（0.5–1 pw）
- [ ] 原始回答入 `provider_results`（channel='api'）
- [ ] 提及抽取 Prompt（文档第十三节）→ `mention_results`，支持别名/模糊/地址辅助匹配 + 实体消歧
- [ ] **同时抽取回答里全部品牌及排名顺序写入 `mentioned_brands`**（为竞品分析铺路）
- [ ] 排名得分（倒数或归一化）、情感判断(positive/neutral/negative/mixed)
- [ ] 前端：AI 原始回答页（问题/平台/模型/回答/是否提及/位置/排名/情感）——**这页很重要，用户会质疑分数怎么来的**

**验收**：随机抽 10 条回答人工核对，提及判断与排名/情感与人工一致率达标（先定 ≥85%）。

### P1.6 打分 + HTML 报告渲染（0.5–1 pw）— *阶段产物*
- [ ] `geo_scoring_service`：MVP 简化口径（提及率 × 排名/曝光加权），子指标照算
- [ ] **按 phase 分别聚合**：每平台决策期/质疑期两套数据
- [ ] 报告 5 部分（文档第十五节）：总览 / 多平台表现 / 竞品分析 / 证据缺口(占位) / 优化任务清单
- [ ] 渲染成 HTML，**结构对齐样例报告**：综合得分 + 8 平台×2 phase + 竞品对比 + 优化建议（引用源排行榜/信源投放本阶段留空占位，P2 填）
- [ ] `GET /api/reports/{run_id}` + 前端 Dashboard（GeoScoreCard / MentionRateChart / ProviderComparisonTable）

**验收（P1 总验收 / Definition of Done）**：
对一个真实商家走完整链路，**生成出一份结构完整、可在浏览器打开的 GEO 诊断报告 HTML**，含综合得分、各平台决策期/质疑期提及率与排名、基础优化建议。引用源相关板块为合理占位。

---

## P2 · 账号池 Web 渠道（3–5 pw）— *产品核心价值，最易碎*

**目标**：拿到纯 API 拿不到的三块数据——真实曝光率、引用源平台排行榜、信源投放建议。

> 核心思路（文档第二十四节）：账号池只需从 App 抓两样东西——**①完整回答文本 ②本次回答的引用源列表(标题+URL/域名)**，其余全是后处理。**不抓 DOM，拦网络层**（浏览器内 TLS 之后的已解密明文，不存在破解 https 问题）。

### P2.1 最小验证（1 pw）— *先证明方案可行，再扩量*
- [ ] 挑 1 个网页端最稳的平台（建议 DeepSeek 联网版或腾讯元宝）
- [ ] 人工扫码登录 1 个账号，保存 `storage_state` / user_data_dir profile
- [ ] DevTools 抓包确定接口 URL 与引用源字段结构
- [ ] 写出最小链路：**问 1 个问题 → 拿到 answer + citations → 落库**
- [ ] `page.add_init_script` 注入，包一层 `window.fetch`/`EventSource`，chunk 经 `expose_function` 回传 Python 累积

**验收**：这条通了，账号池方案即被验证，剩下都是复制扩平台。

### P2.2 WebChannel 适配层 + 账号管理（1–1.5 pw）
- [ ] `WebChannel.ask(platform, account, question) -> {answer_text, citations[], raw_payload}`，与 api channel 并列实现同一接口
- [ ] 每平台一个子类：`DeepSeekWebChannel` / `YuanbaoWebChannel` / `DoubaoWebChannel` …
- [ ] 封装流程：打开会话 → **确认"联网搜索"开关已开**（不开则引用源全空=白跑）→ 输入问题 → 用 SSE done 事件判完成 → 返回
- [ ] 账号池调度（文档第十四节）：每账号串行、每问随机 sleep、每账号每日配额(30–50问)、按"空闲账号"领取任务
- [ ] 风控：检测验证码/异常页 → 暂停该账号 + 告警 + 切下一个；登录态过期 → 标 `need_relogin` 人工补登

**验收**：3 个账号轮转跑一批问题，节奏拟人、配额生效、异常自动切换不中断整体。

### P2.3 落库与三大指标产出（0.5–1 pw）
- [ ] `provider_results`：channel='web' + account_id + raw_payload(JSONB)
- [ ] `citation_sources`：逐条引用入库（idx/title/url/domain/source_name/snippet）
- [ ] 回答文本 → 丢便宜 API 模型做提及抽取（含竞品多品牌）→ `mention_results`，**按 phase 分开**
- [ ] 报告板块填充：
      - 真实曝光率 = answer + 提及抽取，按正/负面分算
      - 引用源平台排行榜 = `citation_sources` 按 domain/source_name 聚合降序
      - 信源投放建议 = Top N 域名归一化成百分比 + 优先级分层
      - GEO 优化建议(文章标题) = 取高频引用文章 title

### P2.4 扩平台（1–2 pw，按平台滚动推进）
- [ ] 扩到没有等价 API、必须账号池的平台：**腾讯元宝、纳米AI、带联网的豆包**
- [ ] 每接一个平台 ≈ 半天–1 天（抓包 + 写 parser）；个别平台搜索结果与正文拆两个请求则两个都拦
- [ ] 此时账号池成为"测评"主数据源，API 退居二线（分析任务 + 联网平台兜底）

**验收（P2 总验收）**：报告里"引用源平台排行榜""信源投放建议""真实曝光率"用账号池真实数据填满，与样例 HTML 维度一致。

---

## P3 · 证据系统（2–3 pw）

**目标**：让总分能纳入"证据可验证率"，并产出证据缺口分析。

- [ ] 证据采集（文档第八节合规策略）：用户授权链接/上传、官网合规抓取(trafilatura/bs4)、第三方只存摘要+链接+时间+片段
- [ ] `evidence_sources` 入库：url/title/content_text/trust_level/retrieved_at/content_hash
- [ ] pgvector 向量化证据，先规则+向量召回，再 LLM/NLI 判 supported/unsupported/contradicted
- [ ] 事实声明拆分 Prompt → 证据验证 Prompt（文档第十三节）→ `verification_results`
- [ ] 证据可验证率计算；低置信度进人工复核队列
- [ ] 前端：证据中心（来源/可信等级/更新时间/支持的声明/是否过期/是否冲突）+ EvidenceVerificationPanel
- [ ] 报告"证据缺口"板块从占位换成真实数据；评估是否把证据率纳入总分

**验收**：对一条回答完成"拆声明→找证据→判支持/矛盾→算可验证率"全流程，证据可在前端逐条查看。

---

## P4 · 竞品分析（1–2 pw，大部分随 P1.5 顺带完成）

- [ ] 基于 `mentioned_brands` 聚合：竞品提及率、竞品平均排名、竞品在负面期出现情况
- [ ] 竞品可见度差距文案（文档第七节示例：低于竞品 A 多少个百分点 + 原因推断）
- [ ] 前端：CompetitorVisibilityChart + 多平台对比页 + 报告竞品数据对比板块

**验收**：报告竞品对比板块输出目标商家 vs 竞品的提及率/排名差距与差距原因。

---

## P5 · 商业化与打磨（2–3 pw）

- [ ] 多租户：所有查询带 tenant_id；数据隔离 tenant/user/merchant
- [ ] API Key 安全：企业自有 Key 走 KMS 加密、只存密文、永不返回完整 Key、支持轮换
- [ ] 报告导出 PDF；历史趋势图；周期性监控（定时 run）
- [ ] 套餐计费 / 审计日志 / 团队协作（按需）
- [ ] 监控补齐：Prometheus + Grafana + OpenTelemetry

**验收**：可按租户隔离数据、导出 PDF、查看历史趋势。

---

## 附录 A · 数据库建表推荐顺序

按外键依赖（文档第九节）：
```
1. merchants → 2. merchant_aliases → 3. evidence_sources
4. geo_runs → 5. geo_prompts
6. provider_results（含 channel/account_id/raw_response）
7. citation_sources（依赖 provider_results）
8. mention_results（含 mentioned_brands）
9. verification_results
10. geo_reports
```
P0/P1 先建 1–6、8、10；P2 建 7；P3 建 9。

---

## 附录 B · 开发优先级速查（文档第二十节）

```
DB与商家资料 → Provider Adapter → 问题生成 → 异步队列 → 回答入库
→ 提及率/排名 → 报告页 → 证据系统 → 竞品分析 → 优化建议/商业化
```

---

## 附录 C · 核心难点与对策（文档第二十二节，需在对应阶段落实）

| 难点 | 阶段 | 对策 |
|---|---|---|
| 平台回答不稳定 | P1 | 同题重复 2–3 次、低 temperature、固定问题集版本、记录模型版本、取均值 |
| API 与 App 回答不一致 | P1/P2 | 报告标注测评口径（API非联网/API联网/Agent/人工App抽样），不等同真实 |
| 证据验证易误判 | P3 | 规则+向量召回 → LLM/NLI 判定 → 低置信人工复核 → 证据必展示 |
| 调用成本高 | 全程 | 问题分层、缓存相同问题、按平台选择、有限重试、错峰、token 计入租户 |
| 商家名称歧义 | P1 | 名称+城市+区域+地址+电话联合消歧，维护 alias 表，泛化名标 uncertain |

---

## 附录 D · 启动前必须拍板的开放项

1. **模型型号核实**：DeepSeek/通义/智谱/Kimi 的确切可用 model 名（文档警告不要写死臆测型号）。
2. **账号池首个验证平台**：DeepSeek 联网版 vs 腾讯元宝，二选一作为 P2.1 最小验证目标。
3. **账号与登录态**：谁提供、几十个账号的获取与人工补登责任人。
4. **HTML 报告模板**：是否直接以样例报告为唯一模板基线（建议是），以锁定 P1.6 渲染目标。
5. **队列选型**：Celery vs Arq（小团队建议 Arq）。
6. **合规边界**：文档定位"内部/授权测评工具、合规风险暂搁置"，需确认账号池采集在授权范围内。

---

## 关键提醒

- **不要一开始就陷入 8 个平台的接口细节**：先跑通闭环，再扩平台数量。
- **不要直接从账号池开做**：提及抽取/打分/报告渲染是否正确，需先有数据流过才能验证；API 几天能让整份报告"长出来"，再逐平台把账号池换进去。
- 系统真正的竞争力不是"调了多少模型"，而是：问题集是否真实、提及识别是否准确、分数是否可解释、证据是否可信、建议是否可执行、报告能否让商家看懂并愿意付费。
