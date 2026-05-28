"use client";

import { useEffect, useState } from "react";
import { Card, Statistic, Tag, Button, Space, Typography, Alert } from "antd";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

type Health = { status: string; app: string; env: string };

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const check = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setHealth(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    check();
  }, []);

  return (
    <main style={{ maxWidth: 720, margin: "48px auto", padding: 24 }}>
      <Typography.Title level={3}>GEO 商家画像平台</Typography.Title>
      <Typography.Paragraph type="secondary">
        P0 工程骨架 — 前端探活后端 /api/health
      </Typography.Paragraph>

      <Card
        title="后端连通性"
        extra={
          <Button onClick={check} loading={loading} size="small">
            重新检测
          </Button>
        }
      >
        {error && <Alert type="error" message={`无法连接后端: ${error}`} showIcon />}
        {health && (
          <Space size="large">
            <Statistic
              title="状态"
              valueRender={() => <Tag color="green">{health.status}</Tag>}
            />
            <Statistic title="应用" value={health.app} />
            <Statistic title="环境" value={health.env} />
          </Space>
        )}
      </Card>
    </main>
  );
}
