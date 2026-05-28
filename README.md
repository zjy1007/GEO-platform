# GEO 商家画像平台

AI 搜索（GEO）商家曝光测评与诊断报告平台。详见 [开发计划](docs/GEO平台开发计划.md)、[需求说明](docs/GEO商家画像-需求说明.md)、[样例诊断报告](docs/样例-GEO品牌诊断报告.html)。

当前阶段：**P0 工程基建与骨架**（可运行空壳，后续功能往里填）。

## 技术栈

- 后端：FastAPI + SQLAlchemy(async) + asyncpg + Pydantic
- 队列：Arq + Redis
- 数据库：PostgreSQL + pgvector
- 对象存储：MinIO
- 前端：Next.js + TypeScript + Ant Design
- 部署：Docker Compose

## 目录结构

```
geo-platform/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口 + /api/health
│   │   ├── core/             # config / logging(trace_id) / security / database
│   │   ├── models/           # SQLAlchemy 模型（doc §9 全量表）
│   │   ├── providers/        # providers.yaml + 配置加载器
│   │   ├── workers/          # Arq worker（P0 占位）
│   │   ├── api/ services/ schemas/ prompts/   # P1+ 填充
│   ├── alembic/              # 迁移（0001 建全量表）
│   └── requirements.txt
└── frontend/                 # Next.js + AntD，首页探活 /api/health
```

## 用 Docker 一键起（需本机装 Docker）

```bash
cp .env.example .env
docker compose up --build
# 后端 http://localhost:8000/api/health
# 前端 http://localhost:3000
# MinIO 控制台 http://localhost:9001 (minioadmin/minioadmin)
```

backend 容器启动时会自动 `alembic upgrade head` 建表。

## 不装 Docker：本地跑后端

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# 探活（不需要数据库）
uvicorn app.main:app --reload
# 跑测试
pytest -q
# 建表（需本地有 Postgres，并设置 DATABASE_URL）
alembic upgrade head
```

> P0 的 `/api/health` 不依赖数据库；`/api/health/db` 才需要数据库连接。

## P0 验收

- `docker compose up` 后前端能打开、`/api/health` 通、`alembic upgrade head` 成功、（配置 SENTRY_DSN 后）Sentry 收到事件。
- 本地：`pytest -q` 通过。

## 下一步（P1）

按开发计划 P1.1→P1.6：商家画像 → Provider Adapter → 问题生成(决策期+质疑期) → 异步队列 → 回答入库+提及/排名/情感抽取 → 打分 + HTML 报告。
