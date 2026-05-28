# 一、GEO 商家画像

## 核心用户

主要面向：

商家、品牌方、本地生活服务商、连锁门店、代运营公司、SEO/GEO 服务商。

## 核心功能

平台要解决 5 件事：

1. **商家资料上传与结构化画像**
 用户上传商家名称、地址、电话、官网、营业时间、服务项目、价格、荣誉、案例、图片、社媒链接、地图链接、点评链接等，系统自动抽取成标准商家画像。 

2. **多 AI 平台曝光测评**
 对 DeepSeek、豆包、Kimi、智谱、腾讯、文心一言、通义千问等平台发起统一问题集，统计商家是否被 AI 提及。 

3. **GEO 指标计算**
 包括当前 GEO 分数、AI 提及率、推荐排名、正向描述率、竞品对比、证据可验证率、资料一致性、信息完整度等。 

4. **证据验证**
 把 AI 回答里的事实拆成原子声明，例如“该商家位于杭州”“主营宠物美容”“营业到晚上 9 点”，再去商家官网、地图平台、点评平台、新闻稿、公众号、小红书、抖音等证据源里验证。 

5. **优化建议生成**
 输出具体可执行建议，例如：官网缺少结构化地址、地图平台 NAP 信息不一致、没有 FAQ 页面、服务项目描述太少、没有可被 AI 引用的权威证据页、缺少本地化关键词内容等。 

6. 整体开发计划周期

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YmE2MWU1MWU1MjZkOGYwYzNmMmZhMjlmOTcxMmFlYzFfNTM1ZDBjNDNmYjZlZGI4OThlOTQ1ZjA2NzViOWZiMzhfSUQ6NzY0Mzc0Mjc3NjA4MjM2OTUwOF8xNzc5OTM3MzQwOjE3ODAwMjM3NDBfVjM)

# 二、非常关键的产品口径：必须区分“两种测评模式”

这是这个系统能不能做准的关键。

## 真实曝光测评模式

这个模式用于计算：

AI 提及率、推荐排名、竞品曝光、真实 GEO 分数。

做法是：

用户只提供商家 ID，系统拿到商家名称、行业、城市、服务范围之后，生成一批真实用户可能问的问题，比如：

“杭州滨江附近哪家宠物医院比较好？”

“西湖区适合公司团建的餐厅推荐？”

“杭州有没有比较靠谱的儿童摄影店？”

“推荐几家杭州做牙齿矫正比较好的机构。”

然后系统调用各 AI 平台，**不能把商家的完整资料喂给模型**，否则模型当然会提到该商家，这样测出来的是“被投喂后的结果”，不是“真实 AI 曝光”。

## 资料诊断优化模式

这个模式用于生成：

商家画像、问题诊断、证据缺口、优化建议、内容生成。

做法是：

把商家上传资料、公开证据源、竞品资料一起输入模型，让模型分析：

资料是否完整？

AI 为什么不容易提到它？

和竞品相比缺什么？

哪些页面、内容、平台信息需要补齐？

应该写哪些 FAQ、服务页、门店页、案例页？

所以系统内部必须有两个任务类型：

```Plain Text
organic_eval    真实曝光测评，不喂商家详情
diagnostic_eval 资料诊断优化，允许喂商家详情
```

## 第二个维度：正面决策期 vs 负面质疑期（与上面正交）

除了"是否喂资料"，问题本身还要区分**用户的情绪/意图阶段**，这是最终报告里实际呈现的维度（每个平台都分"品牌决策期"和"负面质疑期"两套数据）。

```Plain Text
decision_phase（品牌决策期 / 正面）
  用户在正向选择，例如："南京医美哪个医院好""南京玻尿酸哪个机构值得推荐"
  统计：正面提及率、推荐排名、被推荐的原因

doubt_phase（负面质疑期 / 负面）
  用户在排雷、查负面，例如："南京医美哪个口碑不好""南京玻尿酸哪些机构不靠谱""哪些医院被投诉多"
  统计：是否出现在负面名单里、负面竞品有哪些
```

所以一条问题同时带两个标签：`mode`（organic/diagnostic）+ `phase`（decision/doubt）。提及率、排名、竞品对比都要**按 phase 分别统计**，不能混在一起。

## 产品定位（影响后续所有方案选择）

```Plain Text
定位：内部 / 授权测评工具，不是对外规模化 SaaS
账号池规模：几十个账号量级
合规风险：当前阶段先搁置，优先做出能跑通、能落地的版本
首要目标：能完整生成出最终的 GEO 品牌诊断报告（HTML）
```

这个定位直接决定了下面第三节"为什么必须做账号池"以及调用量级、调度方式的取舍。

---

# 三、国内大模型平台接入策略（API + 账号池 双渠道）

> 重要修订：早期版本曾建议"只用官方 API、不要做网页模拟"。但最终报告里最核心的三块数据——**真实曝光率、引用源平台排行榜、信源投放建议**——纯 API 拿不到，必须靠账号池（App/网页版）。结合"内部测评工具"的定位，本系统采用 **API + 账号池双渠道**，二者是分工关系而非二选一。详细采集方案见第二十四节。

## 两个渠道的分工

```Plain Text
api 渠道（纯模型）
  能力：稳定、便宜、可大批量、合规
  用途：① 所有"分析类"任务——问题生成 / 提及抽取 / 情感判断 / 声明拆分 / 优化建议生成
        ② 对支持联网的平台做大批量补充或兜底
  局限：裸模型测的是"训练记忆"而非"真实曝光"，且基本不返回引用源

web 渠道（账号池 / App）
  能力：能拿到 App 的联网搜索结果 + 引用源 + 接近真实用户看到的回答
  用途：真实曝光测评 + 引用源采集（报告的核心数据来源）
  局限：实现/维护成本高、易碎、有封号风险（内部工具+人类化节奏可控）
```

一句话原则：**测评走账号池（web 渠道），分析走 API。**

## 为什么不能只做 API

- 引用源排行榜：南京晨报、淘宝、光明网这些是 AI 联网搜索时引用的网页，**纯 API 调用不返回**，只有 App/联网版才有。
- 信源投放建议：直接从"引用源"反推出来，没有引用源就没有这块。
- 平台清单本身就要求账号池：报告里的 **腾讯元宝、纳米AI、带联网的豆包 App** 没有"改个 base_url 就能用"的等价 API（元宝 ≠ 混元 API，纳米是 360 的搜索 App）。

## 平台按渠道归类

```Plain Text
有可用 API，可 API 渠道起步：DeepSeek、通义千问、智谱、Kimi、文心(千帆)、混元
基本只能账号池(web 渠道)：腾讯元宝、纳米AI、豆包(联网 App 体验)
```

## API 接入注意（不是全部"OpenAI 兼容"）

```Plain Text
DeepSeek / 通义(DashScope) / 智谱 / Kimi  改 base_url 即可，OpenAI 兼容
豆包(火山方舟)                           需用 endpoint id 而非 model 名
百度千帆 / 腾讯混元                       鉴权/签名各不相同，不能简单复用
模型名要核实                             如 deepseek-v4-pro 等型号请以官方为准，不要写死臆测型号
```

## 推荐接入表

---

# 四、总体技术架构

推荐采用：

前端：**React / Next\.js \+ TypeScript \+ Ant Design Pro 或 shadcn/ui**
 后端：**FastAPI \+ Python**
 任务队列：**Celery / RQ / Arq \+ Redis**
 数据库：**PostgreSQL**
 向量检索：**pgvector，后续可升级 Milvus**
 对象存储：**MinIO / 阿里 OSS / 腾讯 COS**
 部署：**Docker Compose 起步，后续 Kubernetes**
 监控：**Prometheus \+ Grafana \+ OpenTelemetry \+ Sentry**

整体架构如下：

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NTMxOWFkOTAzODdlYWJhMjQ3ZTAxODNiNjMzZjNmZmFfNWQwZTJjY2VkODc1ZGQxYWJlZjlkOGZkOTVkZmZjZTBfSUQ6NzY0MzczNDUyMjA1NTYyNTkyMV8xNzc5OTM3MzQwOjE3ODAwMjM3NDBfVjM)

# 五、核心业务流程

## 流程 1：商家入驻与资料上传

用户填写或上传：

```Plain Text
商家名称
别名/品牌名
所属行业
所在城市/区域
详细地址
联系电话
营业时间
服务项目
价格区间
官网
地图链接
美团/大众点评/抖音/小红书/公众号链接
门店照片
资质证书
优势卖点
竞品名单
```

系统做 4 件事：

1. OCR / 文档解析 

2. 商家资料结构化 

3. 商家别名生成 

4. 资料完整度检查 

结构化后的商家画像示例：

```Plain Text
{
  "merchant_name": "杭州某某宠物医院",
  "aliases": ["某某宠物医院", "某某动物医院", "杭州某某宠医"],
  "category": "宠物医疗",
  "city": "杭州",
  "district": "滨江区",
  "address": "杭州市滨江区xxx路xxx号",
  "phone": "0571-xxxxxxx",
  "business_hours": "09:00-21:00",
  "services": ["宠物体检", "疫苗接种", "绝育手术", "皮肤病诊疗"],
  "target_keywords": ["杭州宠物医院", "滨江宠物医院", "猫咪绝育", "宠物疫苗"],
  "official_sources": [
    "官网链接",
    "高德地图链接",
    "大众点评链接"
  ]
}
```

---

## 流程 2：生成 GEO 测评问题集

系统根据行业、城市、用户意图生成问题。

问题分为 6 类：

每个商家建议生成：

```Plain Text
基础版：20 个问题
标准版：50 个问题
专业版：100 个问题
```

为了减少偶然性，每个问题可以对每个平台重复调用 2\-3 次。

---

## 流程 3：多平台并发调用

后端不直接在接口请求里调用大模型，而是创建异步任务。

```Plain Text
用户点击开始测评
→ 创建 geo_run
→ 生成 prompt_jobs
→ 写入 Redis 队列
→ Worker 并发调用各 Provider
→ 原始回答入库
→ 解析提及、排名、情感、证据
→ 计算指标
→ 生成报告
```

每个调用任务的数据结构：

```Plain Text
{
  "run_id": "run_20260525_001",
  "merchant_id": "m_001",
  "provider": "deepseek",
  "model": "deepseek-v4-pro",
  "scenario_type": "category_recommendation",
  "prompt": "杭州滨江区宠物医院推荐几家？",
  "mode": "organic_eval",
  "temperature": 0.2,
  "max_tokens": 2048
}
```

---

# 六、Provider Adapter 统一适配层设计

不要在业务代码里到处写 DeepSeek、豆包、Kimi 的调用代码。必须设计统一接口。

## 关键：channel 抽象（api / web 双渠道）

同一个 provider 可能同时有两种"渠道"：纯 API，或账号池（App/网页）。业务层不应该关心数据是怎么来的，只面向统一的 `Channel` 接口。

```Plain Text
provider（如 deepseek）
  ├── api channel   → 走官方 API（OpenAI 兼容 / 各家 SDK）
  └── web channel   → 走账号池（Playwright 驱动 App，拦截响应拿回答 + 引用源）

两种 channel 都实现同一个接口，返回同一个 LLMResponse；
区别只在 response.channel 字段，以及 web 渠道会填充 citations（API 渠道通常为空）。
```

## 抽象接口

```Plain Text
class BaseChannel:
    provider_name: str
    channel: str            # "api" | "web"

    async def chat(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError

    async def health_check(self) -> ChannelHealth:
        raise NotImplementedError

# api 渠道实现：OpenAICompatibleChannel / DoubaoApiChannel / ...
# web 渠道实现：DeepSeekWebChannel / YuanbaoWebChannel / ...（详见第二十四节）
```

统一请求结构：

```Python
class LLMRequest(BaseModel):
    provider: str
    channel: str = "api"          # "api" | "web"
    model: str | None = None      # web 渠道可能没有模型名
    messages: list[dict]
    temperature: float = 0.2
    max_tokens: int = 2048
    stream: bool = False
    web_search: bool = True       # web 渠道必须开启联网搜索才有引用源
    tools: list[dict] | None = None
    metadata: dict = {}           # 可带 account_id / phase 等
```

统一响应结构（新增 channel 与 citations）：

```Python
class Citation(BaseModel):
    index: int                    # 引用角标序号
    title: str | None = None      # 引用文章标题（用于"GEO 大模型优化建议"取标题）
    url: str | None = None
    domain: str | None = None     # 用于"引用源排行榜"按域名聚合
    source_name: str | None = None
    snippet: str | None = None

class LLMResponse(BaseModel):
    provider: str
    channel: str                  # "api" | "web"
    model: str | None = None
    content: str
    citations: list[Citation] = []   # web 渠道填充，api 渠道通常为空
    raw_response: dict
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int
    status: str
    error_message: str | None = None
```

## Provider 配置表

```Python
providers:
  deepseek:
    type: openai_compatible
    base_url: https://api.deepseek.com
    api_key_env: DEEPSEEK_API_KEY
    default_model: deepseek-v4-pro
    timeout_sec: 60
    max_concurrency: 5

  qwen:
    type: openai_compatible
    base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
    api_key_env: DASHSCOPE_API_KEY
    default_model: qwen-plus
    timeout_sec: 60
    max_concurrency: 5

  zhipu:
    type: openai_compatible
    base_url: https://open.bigmodel.cn/api/paas/v4
    api_key_env: ZHIPU_API_KEY
    default_model: glm-4-plus
    timeout_sec: 60
    max_concurrency: 5
```

## 调用层要支持

必须支持这些能力：

```Plain Text
超时控制
失败重试
限流
熔断
日志追踪
token 统计
成本统计
原始响应保存
JSON 输出修复
供应商健康检查
```

---

# 七、GEO 指标体系设计

这个平台最核心的是指标体系。建议不要只给一个总分，而是拆成多个子指标。

## GEO 总分

建议满分 100。

```Plain Text
GEO Score =
AI 提及率 × 30%
+ 推荐排名得分 × 20%
+ 证据可验证率 × 20%
+ 正向描述率 × 10%
+ 信息一致性 × 10%
+ 内容完整度 × 5%
+ 新鲜度 × 5%
```

可以先用这套权重，后续根据行业调整。

> ⚠️ MVP / 报告口径修订：上面这套 7 因子加权是**远期目标**，其中"证据可验证率""信息一致性"在 MVP 阶段拿不到可靠数据（需要大量证据采集 + NLI 判断）。**最终报告里实际只展示一个"GEO 效果评估评分 / 100"**（见报告的"AI 搜索诊断综合得分"），其口径主要由**提及率 + 曝光/排名**驱动。
>
> 因此 MVP 阶段先用简化口径，避免一上来就被算不出来的子指标卡住：
>
> ```Plain Text
> 效果评估评分 ≈ AI 提及率(各平台综合) × 排名/曝光加权
> ```
>
> 等账号池跑通、证据系统补齐后，再逐步把 7 因子补上。子指标可以照常计算并展示，但**总分口径以报告为准**。

---

## AI 提及率

定义：

```Plain Text
AI 提及率 = 提及目标商家的有效回答数 / 总有效回答数
```

例如：

7 个平台 × 50 个问题 × 2 次重复 = 700 条回答。

其中 84 条回答提到该商家。

```Plain Text
AI 提及率 = 84 / 700 = 12%
```

注意：提及判断要支持别名匹配。

例如商家叫：

```Plain Text
杭州某某宠物医院
```

模型可能写成：

```Plain Text
某某宠医
某某动物医院
滨江某某宠物诊所
```

所以要做：

```Plain Text
标准名称匹配
别名匹配
模糊匹配
地址辅助匹配
实体消歧
```

---

## 推荐排名得分

如果 AI 回答推荐了 5 家商家：

```Plain Text
1. A 商家
2. B 商家
3. 目标商家
4. D 商家
5. E 商家
```

目标商家排第 3，则排名分可以用倒数排名：

```Plain Text
rank_score = 1 / rank
```

也可以归一化：

```Plain Text
rank_score = (max_rank - rank + 1) / max_rank
```

例如最多取前 5 名：

```Plain Text
第 1 名 = 1.0
第 2 名 = 0.8
第 3 名 = 0.6
第 4 名 = 0.4
第 5 名 = 0.2
未出现 = 0
```

---

## 证据可验证率

这项非常重要，因为 GEO 不是让 AI 胡乱夸商家，而是让 AI 能基于可验证资料正确推荐商家。

流程：

```Plain Text
AI 回答
→ 拆分原子事实
→ 匹配证据源
→ 判断支持/矛盾/无证据
→ 计算证据可验证率
```

例如 AI 回答：

```Plain Text
杭州某某宠物医院位于滨江区，提供宠物疫苗、绝育手术和皮肤病诊疗，营业时间到晚上 9 点。
```

拆成：

```Plain Text
声明 1：该商家位于滨江区
声明 2：提供宠物疫苗
声明 3：提供绝育手术
声明 4：提供皮肤病诊疗
声明 5：营业时间到晚上 9 点
```

然后去证据库验证：

计算：

```Plain Text
证据可验证率 = supported / 全部声明
```

也可以更严格：

```Plain Text
证据可信率 = supported / (supported + unsupported + contradicted)
```

---

## 正向描述率

判断 AI 对商家的描述是：

```Plain Text
positive
neutral
negative
mixed
```

例如：

```Plain Text
“口碑较好、服务专业” → positive
“信息较少，建议进一步核实” → neutral
“评价分歧较大” → mixed
“投诉较多” → negative
```

正向描述率：

```Plain Text
positive_mentions / total_mentions
```

---

## 竞品可见度差距

系统不仅要看目标商家，还要看 AI 回答里反复推荐了哪些竞品。

例如用户商家 AI 提及率 12%，竞品 A 是 43%，竞品 B 是 31%。

平台要输出：

```Plain Text
你当前 AI 可见度低于主要竞品 A 31 个百分点。
竞品 A 高频被推荐的原因可能是：
1. 官网信息完整
2. 地图平台评价多
3. 有大量第三方文章提及
4. 服务项目描述更清晰
5. 地址、电话、营业时间一致性更高
```

---

# 八、证据源系统设计

GEO 的核心不是单纯问模型，而是要让商家有“可被 AI 引用的证据”。

## 证据源分类

## 证据采集策略

正式商业系统不要随便爬取受限平台。建议：

9499. 用户授权上传链接和资料。 

9500. 对官网和自有页面做合规抓取。 

9501. 地图、点评等平台优先使用开放 API、商家后台导出或用户手动上传截图/链接。 

9502. 第三方公开网页只保存摘要、链接、时间和关键片段，不要大规模复制原文。 

9503. 所有证据记录来源 URL、抓取时间、哈希值、可信等级。 

## 证据库结构

```Plain Text
{
  "source_id": "src_001",
  "merchant_id": "m_001",
  "source_type": "official_website",
  "url": "https://example.com/services",
  "title": "服务项目",
  "content_text": "本店提供宠物疫苗、绝育手术、皮肤病诊疗...",
  "retrieved_at": "2026-05-25T10:00:00+08:00",
  "trust_level": 0.95,
  "content_hash": "sha256..."
}
```

---

# 九、数据库设计

## merchants 商家表

```Plain Text
CREATE TABLE merchants (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    city VARCHAR(100),
    district VARCHAR(100),
    address TEXT,
    phone VARCHAR(100),
    website TEXT,
    status VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## merchant\_aliases 商家别名表

```Plain Text
CREATE TABLE merchant_aliases (
    id UUID PRIMARY KEY,
    merchant_id UUID REFERENCES merchants(id),
    alias VARCHAR(255),
    alias_type VARCHAR(50),
    confidence FLOAT
);
```

## evidence\_sources 证据源表

```Plain Text
CREATE TABLE evidence_sources (
    id UUID PRIMARY KEY,
    merchant_id UUID REFERENCES merchants(id),
    source_type VARCHAR(100),
    url TEXT,
    title TEXT,
    content_text TEXT,
    trust_level FLOAT,
    retrieved_at TIMESTAMP,
    content_hash VARCHAR(255)
);
```

## geo\_runs 测评任务表

```Plain Text
CREATE TABLE geo_runs (
    id UUID PRIMARY KEY,
    merchant_id UUID REFERENCES merchants(id),
    run_type VARCHAR(50),           -- organic_eval / diagnostic_eval
    status VARCHAR(50),
    total_jobs INT,
    finished_jobs INT,
    failed_jobs INT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);
```

## geo\_prompts 问题表

```Plain Text
CREATE TABLE geo_prompts (
    id UUID PRIMARY KEY,
    merchant_id UUID REFERENCES merchants(id),
    scenario_type VARCHAR(100),
    phase VARCHAR(20),              -- decision(决策期/正面) | doubt(质疑期/负面)
    mode VARCHAR(20),              -- organic | diagnostic
    prompt_text TEXT,
    city VARCHAR(100),
    category VARCHAR(100),
    intent VARCHAR(100),
    created_at TIMESTAMP
);
```

## provider\_results 平台回答表

```Plain Text
CREATE TABLE provider_results (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES geo_runs(id),
    prompt_id UUID REFERENCES geo_prompts(id),
    provider VARCHAR(100),
    channel VARCHAR(20),            -- api | web(账号池)
    account_id UUID,               -- web 渠道：用哪个账号采集的（便于排查/配额）
    model VARCHAR(100),
    answer_text TEXT,
    raw_response JSONB,             -- web 渠道存拦截到的原始 SSE/JSON
    latency_ms INT,
    prompt_tokens INT,
    completion_tokens INT,
    status VARCHAR(50),
    created_at TIMESTAMP
);
```

## citation\_sources 引用源表（新增，账号池核心产出）

记录每条 AI 回答里引用了哪些网页/平台。报告的"引用源平台排行榜""信源投放建议""GEO 大模型优化建议（文章标题）"都来自这张表的聚合。

```Plain Text
CREATE TABLE citation_sources (
    id UUID PRIMARY KEY,
    provider_result_id UUID REFERENCES provider_results(id),
    idx INT,                       -- 引用角标序号
    title TEXT,                    -- 引用文章标题（用于优化建议取标题）
    url TEXT,
    domain VARCHAR(255),           -- 用于排行榜按域名聚合
    source_name VARCHAR(255),      -- 平台/站点名（如 南京晨报、淘宝）
    snippet TEXT,
    created_at TIMESTAMP
);
```

## mention\_results 提及分析表

```Plain Text
CREATE TABLE mention_results (
    id UUID PRIMARY KEY,
    provider_result_id UUID REFERENCES provider_results(id),
    merchant_id UUID REFERENCES merchants(id),
    is_mentioned BOOLEAN,
    mention_text TEXT,
    rank_position INT,
    mentioned_brands JSONB,        -- 本次回答里提及的所有品牌(含竞品)及其顺序，用于竞品可见度对比
    sentiment VARCHAR(50),
    confidence FLOAT
);
```

> 说明：报告的"竞品可见度对比"需要一次回答里**提及的全部品牌列表**（目标 + 竞品 + 排名顺序），单个 `rank_position` 存不下，所以加 `mentioned_brands`（如 `[{"brand":"江苏省人民医院","rank":1},...]`）。竞品的提及率统计直接对这个字段做聚合。

## verification\_results 证据验证表

```Plain Text
CREATE TABLE verification_results (
    id UUID PRIMARY KEY,
    provider_result_id UUID REFERENCES provider_results(id),
    claim_text TEXT,
    verification_status VARCHAR(50),
    evidence_source_id UUID,
    confidence FLOAT,
    explanation TEXT
);
```

## geo\_reports 报告表

```Plain Text
CREATE TABLE geo_reports (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES geo_runs(id),
    merchant_id UUID REFERENCES merchants(id),
    geo_score FLOAT,
    mention_rate FLOAT,
    evidence_rate FLOAT,
    positive_rate FLOAT,
    rank_score FLOAT,
    report_json JSONB,
    created_at TIMESTAMP
);
```

---

# 十、后端模块拆分

建议项目目录：

```Plain Text
geo-platform/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   ├── logging.py
│   │   │   └── rate_limit.py
│   │   ├── api/
│   │   │   ├── merchants.py
│   │   │   ├── uploads.py
│   │   │   ├── geo_runs.py
│   │   │   ├── reports.py
│   │   │   ├── providers.py
│   │   │   └── evidence.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── merchant_profile_service.py
│   │   │   ├── prompt_generation_service.py
│   │   │   ├── geo_scoring_service.py
│   │   │   ├── evidence_service.py
│   │   │   ├── verification_service.py
│   │   │   └── report_service.py
│   │   ├── providers/
│   │   │   ├── base.py
│   │   │   ├── openai_compatible.py
│   │   │   ├── deepseek.py
│   │   │   ├── doubao.py
│   │   │   ├── kimi.py
│   │   │   ├── zhipu.py
│   │   │   ├── tencent.py
│   │   │   ├── baidu.py
│   │   │   └── qwen.py
│   │   ├── workers/
│   │   │   ├── geo_eval_worker.py
│   │   │   ├── evidence_worker.py
│   │   │   └── report_worker.py
│   │   └── prompts/
│   │       ├── generate_questions.yaml
│   │       ├── extract_mentions.yaml
│   │       ├── verify_claims.yaml
│   │       └── generate_recommendations.yaml
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
├── frontend/
├── docker-compose.yml
└── README.md
```

---

# 十一、API 接口设计

## 创建商家

```Plain Text
POST /api/merchants
```

请求：

```Plain Text
{
  "name": "杭州某某宠物医院",
  "category": "宠物医疗",
  "city": "杭州",
  "district": "滨江区",
  "address": "杭州市滨江区xxx路xxx号",
  "phone": "0571-xxxxxxx",
  "website": "https://example.com"
}
```

## 上传商家资料

```Plain Text
POST /api/merchants/{merchant_id}/assets
```

支持：

```Plain Text
PDF
Word
Excel
图片
营业执照
服务介绍文档
门店照片
截图
```

## 创建 GEO 测评任务

```Plain Text
POST /api/geo-runs
```

请求：

```Plain Text
{
  "merchant_id": "m_001",
  "run_type": "organic_eval",
  "providers": ["deepseek", "doubao", "kimi", "zhipu", "tencent", "baidu", "qwen"],
  "prompt_count": 50,
  "repeat_count": 2
}
```

## 查询任务状态

```Plain Text
GET /api/geo-runs/{run_id}
```

返回：

```Plain Text
{
  "run_id": "run_001",
  "status": "running",
  "total_jobs": 700,
  "finished_jobs": 260,
  "failed_jobs": 3,
  "progress": 0.371
}
```

## 获取 GEO 报告

```Plain Text
GET /api/reports/{run_id}
```

返回：

```Plain Text
{
  "geo_score": 63.5,
  "mention_rate": 0.12,
  "evidence_rate": 0.68,
  "positive_rate": 0.74,
  "rank_score": 0.42,
  "provider_breakdown": {
    "deepseek": {
      "mention_rate": 0.16,
      "avg_rank": 3.2
    },
    "qwen": {
      "mention_rate": 0.09,
      "avg_rank": 4.1
    }
  },
  "recommendations": []
}
```

---

# 十二、前端页面设计

## 首页 Dashboard

展示：

```Plain Text
GEO 总分
AI 提及率
证据可验证率
平均推荐排名
正向描述率
主要竞品
最近一次测评时间
```

卡片示例：

```Plain Text
GEO 总分：63.5 / 100
AI 提及率：12%
证据可验证率：68%
平均推荐排名：3.7
竞品最高提及率：43%
```

---

## 商家资料页

功能：

```Plain Text
基础资料编辑
别名管理
服务项目管理
证据链接管理
上传文档
资料完整度评分
NAP 一致性检查
```

NAP 指：

```Plain Text
Name 商家名称
Address 地址
Phone 电话
```

这三个信息在官网、地图、点评、公众号上必须一致。

---

## GEO 测评页

功能：

```Plain Text
选择测评平台
选择问题数量
选择测评模式
启动测评
查看任务进度
查看失败原因
重新运行失败任务
```

---

## 多平台对比页

表格：

---

## AI 原始回答页

用户可以看到每个平台的原始回答。

字段：

```Plain Text
问题
平台
模型
回答内容
是否提及
提及位置
推荐排名
情感判断
证据验证结果
```

这个页面非常重要，因为用户会质疑分数怎么来的。

---

## 证据中心

展示：

```Plain Text
官网证据
地图证据
点评证据
社媒证据
新闻证据
用户上传证据
```

每条证据有：

```Plain Text
来源
可信等级
更新时间
支持的声明
是否过期
是否冲突
```

---

## 优化建议页

建议不要只给泛泛建议，要给“任务清单”。

例如：

```Plain Text
高优先级：
1. 官网缺少“滨江区宠物医院”独立服务页，建议新增。
2. 百度地图和官网营业时间不一致，建议统一为 09:00-21:00。
3. 当前 AI 回答中有 4 条声明无证据支撑，建议补充服务项目说明页。
4. 缺少 FAQ 页面，建议新增“猫咪绝育多少钱”“宠物疫苗注意事项”等问答内容。

中优先级：
1. 增加医生团队介绍。
2. 增加真实案例页。
3. 增加用户评价精选页。
```

---

# 十三、Prompt 设计

## 问题生成 Prompt

用途：根据商家行业和城市生成真实用户问题。

```Plain Text
你是本地生活服务搜索用户行为分析专家。
请根据以下商家信息，生成 {count} 个用户可能在 AI 助手中提出的问题。

要求：
1. 不要直接暴露这是测评任务。
2. 问题要自然，符合真实用户搜索习惯。
3. 覆盖品牌直搜、品类推荐、服务场景、价格、对比、信任判断。
4. 输出 JSON 数组。

商家行业：{category}
城市：{city}
区域：{district}
核心服务：{services}
```

---

## 提及抽取 Prompt

用途：判断 AI 回答是否提到目标商家。

```Plain Text
你是实体识别与商家消歧专家。
请判断下面回答中是否提到了目标商家。

目标商家：
{name}

商家别名：
{aliases}

商家地址：
{address}

AI回答：
{answer}

请输出 JSON：
{
  "is_mentioned": true/false,
  "matched_name": "...",
  "rank_position": 1,
  "mention_text": "...",
  "confidence": 0.0-1.0
}
```

---

## 事实声明拆分 Prompt

```Plain Text
请把下面 AI 回答中关于目标商家的事实性描述拆分成最小原子声明。
只提取可以被验证的事实，不要提取主观评价。

AI回答：
{answer}

输出 JSON：
[
  {
    "claim": "该商家位于杭州市滨江区",
    "claim_type": "address"
  },
  {
    "claim": "该商家提供宠物疫苗服务",
    "claim_type": "service"
  }
]
```

---

## 证据验证 Prompt

```Plain Text
你是事实核查专家。
请判断声明是否被证据支持。

声明：
{claim}

证据：
{evidence_text}

输出 JSON：
{
  "status": "supported / contradicted / unsupported",
  "confidence": 0.0-1.0,
  "reason": "简短说明"
}
```

---

## 优化建议 Prompt

```Plain Text
你是 GEO 商家优化顾问。
请根据以下测评结果，为商家生成可执行优化建议。

商家信息：
{merchant_profile}

GEO指标：
{metrics}

低分问题：
{weaknesses}

竞品表现：
{competitor_summary}

证据缺口：
{evidence_gaps}

要求：
1. 按高/中/低优先级输出。
2. 每条建议必须说明原因、影响指标、执行方式。
3. 不要输出空泛建议。
4. 输出 JSON。
```

---

# 十四、任务队列与并发控制

这个系统一定要异步化。

原因是一次测评可能是：

```Plain Text
7 个平台 × 50 个问题 × 2 次重复 = 700 次模型调用
```

如果是 8 平台、100 问题、3 次重复：

```Plain Text
8 × 100 × 3 = 2400 次调用
```

必须使用任务队列。

> ⚠️ 调用量级修订（账号池现实）：上面 700~2400 是 **API 渠道**能扛的量。**账号池(web 渠道)扛不住这个量**。结合内部工具定位，账号池实际量级应对齐报告：
>
> ```Plain Text
> 8 平台 × (10 正面 + 10 负面) × 1 次 ≈ 160 次/轮
> ```
>
> 即"分析类大批量任务（问题生成/提及抽取等）走 API；真实曝光采集走账号池、控制在百量级"。

## 推荐任务状态机

```Plain Text
created
queued
running
partial_failed
completed
failed
cancelled
```

## Worker 并发策略

```Plain Text
每个平台单独限流
每个租户单独限流
失败任务指数退避重试
供应商错误自动熔断
超时任务标记 retryable
```

API 渠道示例（按 qps / 并发限流）：

```Plain Text
rate_limits:
  deepseek:
    max_concurrency: 5
    qps: 2
  doubao:
    max_concurrency: 5
    qps: 2
  kimi:
    max_concurrency: 3
    qps: 1
```

## 账号池（web 渠道）调度：按账号配额，而不是 qps

账号池的瓶颈不是 token 成本，而是"**每个账号每天能问几次不被封**"。所以 web 渠道要换一套调度模型：

```Plain Text
web_channel:
  每账号串行（同一账号同一时刻只跑一个会话）
  每问之间随机 sleep 几秒~十几秒（模拟人类）
  每账号每日配额上限（如 30~50 问）
  调度按"空闲账号"领取任务，而非并发打满
  检测到验证码/异常页 → 暂停该账号 + 告警 + 切下一个账号
  登录态过期 → 标记账号 need_relogin，人工补登

account_quota:
  deepseek_web:  { per_account_daily: 40 }
  yuanbao_web:   { per_account_daily: 30 }
  doubao_web:    { per_account_daily: 30 }
```

几十个账号 × 每账号每天几十问 = 每天可跑上千问，足够覆盖百量级/轮的测评需求。

---

# 十五、报告生成设计

报告分为 5 部分。

## 总览

```Plain Text
GEO 总分：63.5
等级：中等
核心结论：该商家在 AI 问答中的自然曝光较低，主要问题是第三方证据不足、地图平台信息不一致、服务项目内容不完整。
```

## 多平台表现

```Plain Text
DeepSeek：提及率较高，但证据支撑不足
通义千问：提及率较低，但回答较保守
Kimi：对长文本资料理解较好，诊断建议质量较高
文心一言：本地生活问题中更依赖地图和百科类证据
```

## 竞品分析

输出：

```Plain Text
哪些竞品经常被 AI 推荐
竞品被推荐的原因
目标商家和竞品的差距
```

## 证据缺口

例如：

```Plain Text
缺少官网服务页
缺少价格说明
缺少医生/团队介绍
缺少用户案例
地图平台营业时间不一致
公众号内容未结构化
```

## 优化任务清单

输出成可执行 checklist：

```Plain Text
[高] 统一官网、高德、百度地图、大众点评的地址和营业时间
[高] 新增“滨江宠物医院”本地化服务页
[高] 新增 FAQ 页面，覆盖 20 个高频用户问题
[中] 新增医生团队介绍和资质证明页面
[中] 将用户案例整理成结构化内容
[低] 增加门店照片 alt 文本和图片说明
```

---

# 十六、前端技术方案

## 技术栈

```Plain Text
React 18 / Next.js
TypeScript
Ant Design Pro 或 shadcn/ui
TanStack Query
Zustand / Redux Toolkit
ECharts / Recharts
React Hook Form
Zod
```

## 页面路由

```Plain Text
/dashboard
/merchants
/merchants/:id/profile
/merchants/:id/evidence
/merchants/:id/geo-runs
/merchants/:id/reports/:reportId
/merchants/:id/recommendations
/providers
/settings
```

## 关键组件

```Plain Text
GeoScoreCard
MentionRateChart
ProviderComparisonTable
PromptResultTable
EvidenceVerificationPanel
CompetitorVisibilityChart
RecommendationChecklist
RunProgressDrawer
MerchantProfileForm
```

---

# 十七、后端技术方案

## FastAPI 服务模块

```Plain Text
AuthService
MerchantService
UploadService
EvidenceService
PromptService
GeoRunService
ProviderService
ScoringService
ReportService
BillingService
```

## 推荐 Python 依赖

```Plain Text
fastapi
uvicorn
sqlalchemy
alembic
asyncpg
pydantic
celery
redis
httpx
tenacity
python-multipart
pypdf
python-docx
openpyxl
beautifulsoup4
trafilatura
pgvector
prometheus-client
sentry-sdk
```

---

# 十八、安全与合规设计

## API Key 安全

所有供应商 API Key 不能明文存数据库。

建议：

```Plain Text
环境变量存系统级 Key
企业客户自有 Key 使用 KMS 加密
数据库只保存密文
接口返回时永不展示完整 Key
支持 Key 轮换
```

## 数据隔离

必须支持多租户：

```Plain Text
tenant_id
user_id
merchant_id
```

所有查询都要带 tenant\_id。

## 敏感资料处理

商家可能上传营业执照、联系人电话、合同、内部资料。需要：

```Plain Text
对象存储私有桶
下载签名 URL
访问日志
文件病毒扫描
权限校验
定期清理
```

## 平台调用合规

不要做：

```Plain Text
模拟网页登录
绕过验证码
批量刷问答
规避平台限制
抓取受限内容
```

建议做：

```Plain Text
官方 API
企业 API
开放平台 API
用户授权数据
公开网页合理抓取
```

---

# 十九、MVP 版本规划

## v0\.1：最小可运行版本

目标：跑通从商家资料上传到 GEO 报告生成。

功能：

```Plain Text
商家资料录入
商家别名管理
接入 3 个模型：DeepSeek、通义千问、Kimi
生成 20 个测评问题
异步调用模型
统计 AI 提及率
生成基础 GEO 分数
输出报告页面
```

这个版本先不做复杂证据验证，只做：

```Plain Text
是否提及
推荐排名
正负向描述
平台对比
基础建议
```

---

## v0\.2：证据验证版本

新增：

```Plain Text
官网链接抓取
用户上传资料解析
证据库
事实声明拆分
证据可验证率
证据缺口分析
```

---

## v0\.3：完整多平台版本

新增：

```Plain Text
豆包/火山方舟
智谱 GLM
百度千帆/文心
腾讯混元/元器
第 8 平台
供应商状态页
失败重试
成本统计
```

---

## v0\.4：竞品分析版本

新增：

```Plain Text
自动识别 AI 回答中的竞品
竞品提及率
竞品排名
竞品证据分析
差距建议
```

---

## v0\.5：商业化版本

新增：

```Plain Text
租户管理
套餐计费
报告导出 PDF
周期性监控
历史趋势图
客户管理
团队协作
审计日志
```

---

# 二十、推荐的开发优先级

你可以按这个顺序开发：

```Plain Text
第一步：数据库和商家资料管理
第二步：Provider Adapter 统一模型调用
第三步：GEO 问题生成
第四步：异步任务队列
第五步：AI 回答入库
第六步：提及率和排名计算
第七步：报告页面
第八步：证据源和证据验证
第九步：竞品分析
第十步：优化建议和商业化
```

其中最核心的 MVP 闭环是：

```Plain Text
商家信息 → 生成问题 → 调用多模型 → 分析是否提及 → 计算 GEO 分数 → 生成报告
```

---

# 二十一、最小 MVP 数据流



---

# 二十二、核心难点与解决方案

## 难点 1：不同平台回答不稳定

解决：

```Plain Text
同一问题重复调用 2-3 次
temperature 固定低值
问题集固定版本
记录模型版本
统计平均值而不是单次结果
```

---

## 难点 2：API 回答和 App 回答不一致

很多 C 端 App 有联网搜索、推荐系统、个性化策略，而 API 可能只是纯模型。

解决：

报告里明确标注测评口径：

```Plain Text
API 非联网测评
API 联网测评
官方 Agent 测评
人工 App 抽样测评
```

不能把 API 测评结果绝对等同于 App 真实结果。

---

## 难点 3：证据验证容易误判

解决：

```Plain Text
先用规则和向量召回找证据
再用 LLM/NLI 判断 supported/unsupported/contradicted
低置信度进入人工复核
证据必须展示给用户
```

---

## 难点 4：模型调用成本高

解决：

```Plain Text
问题分层：基础版 20 问，专业版 100 问
缓存相同问题结果
支持按平台选择
失败重试有限次数
定时任务错峰运行
token 用量统计到租户
```

---

## 难点 5：商家名称歧义

例如同名门店很多。

解决：

```Plain Text
名称 + 城市 + 区域 + 地址 + 电话联合消歧
维护 alias 表
回答中出现地址/区域时提高置信度
只出现泛化名称时标记 uncertain
```

---

# 二十三、最终建议的技术选型

我建议你第一版这样定：

```Plain Text
前端：Next.js + TypeScript + Ant Design Pro + ECharts
后端：FastAPI + SQLAlchemy + PostgreSQL
队列：Redis + Celery
模型调用：统一 OpenAI-compatible adapter
文件存储：MinIO
向量检索：PostgreSQL + pgvector
部署：Docker Compose
监控：Prometheus + Grafana + Sentry
```

第一版先接：

```Plain Text
DeepSeek
通义千问
Kimi
智谱 GLM
```

因为这些最容易走统一 API 适配。第二版再接：

```Plain Text
豆包/火山方舟
百度千帆/文心
腾讯混元/元器
第 8 平台
```

核心原则是：**先跑通 GEO 测评闭环，再扩平台数量；不要一开始就陷入 8 个平台的接口细节。**

最终这个系统的核心竞争力不是“调了多少个模型”，而是：

```Plain Text
问题集设计是否真实
提及识别是否准确
GEO 分数是否可解释
证据验证是否可信
优化建议是否可执行
报告是否能让商家看懂并愿意付费
```

---

# 二十四、账号池（Web 渠道）采集方案

报告里最值钱的三块数据——**真实曝光率、引用源平台排行榜、信源投放建议**——纯 API 拿不到，必须靠账号池。本节给出可落地的采集方案。

## 核心：账号池只需从 App 抓两样东西

```Plain Text
① 完整回答文本
② 这次回答的引用源列表（标题 + URL / 域名）
```

其余全是后处理：
- **真实曝光率** = 对"回答文本"跑提及抽取，看目标商家是否被提到（按 phase 分别算）。
- **引用源排行榜** = 把所有问题抓到的引用源域名聚合计数、排序。
- **信源投放建议** = 引用源排行榜 Top N 换算成百分比 + 优先级分层。
- **GEO 大模型优化建议（文章标题）** = 取高频引用文章的 title，建议商家产出同类内容。

## 关键思路：不要抓 DOM，去拦网络层

App 网页版自己也是调它后端接口拿数据的，返回的 JSON/SSE 里**本来就带结构化的 content + 引用源**。我们在浏览器内部把这个响应截下来，而不是等它渲染成 HTML 再抠。

```Plain Text
抓 DOM（脆）：CSS/类名一改就挂、引用列表常要点"展开"、难判断流式是否结束
拦网络（稳）：直接拿后端返回的结构化引用，对 UI 改动免疫
注：拦截发生在浏览器内、TLS 之后，读到的是已解密明文，不存在"破解 https"问题
```

## 采集流程（即第二阶段的账号池 Worker）

### ① 浏览器 + 账号层
```Plain Text
Playwright(chromium)，每个账号一个独立 user_data_dir profile（存 cookie/登录态），账号天然隔离
登录：首次人工扫码/短信登录一次，保存 storage_state；过期再补登（几十个账号可接受）
账号标准化：尽量关掉历史记忆/个性化、统一地域，保证不同账号结果可比
代理：内部小批量可先不挂；扩量再按账号绑定独立 IP
（几十账号用 Playwright profile 即可，暂不需要商业指纹浏览器）
```

### ② WebChannel 适配层（与 API channel 并列，见第六节）
```Plain Text
WebChannel.ask(platform, account, question) -> { answer_text, citations[], raw_payload }
每个平台一个子类：DeepSeekWebChannel / YuanbaoWebChannel / DoubaoWebChannel ...
封装：打开会话 → 确保"联网搜索"开关已开 → 输入问题 → 等回答结束 → 返回结果
```

### ③ 抓取核心：劫持流式响应
```Plain Text
用 page.add_init_script 注入脚本，包一层 window.fetch 和 EventSource，
把每个流式 chunk 通过 expose_function 回传 Python 端累积（比 response.body() 对 SSE 更可靠）
拼成完整 JSON → 取出 content 和引用字段 → 规整成 {title, url, domain, snippet, index}
字段名各家不同：每接一个平台，先人工开 DevTools 抓一次包，确定接口 URL 与字段结构再写 parser
（一个平台抓包 + 写 parser 约半天到一天）
```

### ④ "联网搜索"必须开（最容易踩的坑）
```Plain Text
元宝/豆包/DeepSeek 网页都有联网/深度搜索开关
不开 → 退化成裸模型 → 引用源全空 → 等于白跑
每次提问前用代码确认开关状态
```

### ⑤ 完成判定 + 反风控节奏
```Plain Text
完成判定：优先用网络层结束信号（SSE done 事件），比看 DOM"停止生成"按钮稳
节奏：每账号串行、每问随机 sleep、每账号每日配额上限（调度细节见第十四节）
风控：检测到验证码/异常页 → 暂停该账号 + 告警 + 切下一个账号，不要硬刚
```

### ⑥ 落库
```Plain Text
provider_results：channel='web'、account_id、answer_text、raw_payload(JSONB)
citation_sources：逐条引用入库（用于排行榜/信源投放/优化建议标题）
回答文本 → 丢给便宜的 API 模型做提及抽取（含竞品多品牌）→ mention_results，按 phase 分开统计
```

## 三个指标如何从抓到的数据落出来（对照报告验证）

```Plain Text
真实曝光率（如 DeepSeek 正面提及率 10%）
  来源：answer_text + 提及抽取
  算法：提及目标商家的回答数 / 有效回答数，按正/负面期分算

引用源平台排行榜（南京晨报 6 次…）
  来源：citation_sources
  算法：按 domain/source_name 聚合计数，降序

信源投放建议（新浪 20%、优先级分层）
  来源：citation_sources
  算法：Top N 域名归一化成百分比，按频次切第一/二/三优先级

GEO 大模型优化建议（文章标题）
  来源：citation_sources 的 title
  算法：取高频引用文章标题，建议商家产出同类内容
```

## 最小验证（第二阶段第一步只做这个）

```Plain Text
挑 1 个网页端最稳的平台（建议 DeepSeek 联网版或腾讯元宝）
→ 人工登录 1 个账号
→ 抓包确定接口
→ 写出"问 1 个问题、拿到 answer + citations 并落库"的最小链路
这条通了，账号池方案就验证了，剩下都是复制扩平台。
```

## 需要正视的风险/未知

```Plain Text
1. 每个平台引用字段结构不同，必须逐个抓包——这是账号池主要的人力成本
2. 个别平台可能把"搜索结果"和"回答正文"拆成两个请求，那就两个都拦
3. 极少数平台响应可能加密/混淆，但因读的是浏览器内已解密内容通常仍可拿到，真遇到再退回 DOM 兜底
4. 即使低频、内部账号，封号风险依然存在，人类化节奏 + 账号配额不能省
```

---

# 二十五、修订后的分阶段开发计划（API 先搭骨架 → 账号池为主）

第十九节的 v0.x 规划仍有效，但落地顺序按"先用简单的 API 跑通整条流水线，再把最难的账号池逐平台换进来"来推进，风险最低。

## 第一阶段：API 为主，跑通整条流水线（约 1-2 周）

目的：验证除"渠道"以外的所有环节都通——DB、异步队列、提及抽取、打分、HTML 报告渲染。

```Plain Text
只接 4 个 OpenAI 兼容平台：DeepSeek、通义、智谱、Kimi
正面期 + 负面质疑期 两套问题都生成
明确接受：这一版引用源为空、提及率是"模型记忆"而非"真实曝光"
产物：能完整生成出 GEO 诊断报告 HTML（哪怕数据口径还不是真实曝光）
```

闭环：`商家信息 → 生成问题(正面+负面) → API 调用 → 提及抽取(含竞品) → 打分 → 渲染 HTML`

## 第二阶段：账号池接入，拿真实数据（产品核心价值）

```Plain Text
1. 先用 1 个平台跑通账号池最小链路（见第二十四节"最小验证"）
2. 打通登录态管理 + 引用源抽取 + 落库
3. 扩到没有等价 API、必须账号池的平台：腾讯元宝、纳米AI、带联网的豆包
4. 此时账号池成为"测评"的主数据源；API 退居二线，专做分析任务 + 联网平台兜底
```

## 为什么不直接账号池先做

```Plain Text
提及抽取、打分、报告渲染是否正确，需要先有数据流过才能验证
API 几天就能让整份报告"长出来"，再把最难、最易碎的账号池一个平台一个平台换进去
每接通一个平台都是可见进展，整体风险最低
```



