"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Card,
  Button,
  Select,
  Space,
  Table,
  Tag,
  Alert,
  message,
} from "antd";
import { ThunderboltOutlined, ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { api, ApiError, GeoPromptOut, PromptTier } from "@/lib/api";

const PHASE_LABELS: Record<string, { label: string; color: string }> = {
  decision: { label: "品牌决策期", color: "geekblue" },
  doubt: { label: "负面质疑期", color: "volcano" },
};

function phaseTag(phase?: string | null) {
  if (!phase) return <Tag>-</Tag>;
  const meta = PHASE_LABELS[phase];
  return meta ? <Tag color={meta.color}>{meta.label}</Tag> : <Tag>{phase}</Tag>;
}

export default function PromptsSection({
  merchantId,
}: {
  merchantId: string;
}) {
  const [prompts, setPrompts] = useState<GeoPromptOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [tier, setTier] = useState<PromptTier>("basic");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setPrompts(await api.listPrompts(merchantId));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [merchantId]);

  useEffect(() => {
    load();
  }, [load]);

  const generate = async () => {
    setGenerating(true);
    try {
      const res = await api.generatePrompts(merchantId, {
        tier,
        modes: ["organic"],
        phases: ["decision", "doubt"],
        provider: "deepseek",
      });
      message.success(`已生成 ${res.total} 条测评问题`);
      await load();
    } catch (e) {
      if (e instanceof ApiError) message.error(`生成失败：${e.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const columns: ColumnsType<GeoPromptOut> = [
    {
      title: "阶段",
      dataIndex: "phase",
      key: "phase",
      width: 130,
      filters: Object.entries(PHASE_LABELS).map(([k, v]) => ({
        text: v.label,
        value: k,
      })),
      onFilter: (value, record) => record.phase === value,
      render: (v?: string) => phaseTag(v),
    },
    {
      title: "模式",
      dataIndex: "mode",
      key: "mode",
      width: 100,
      render: (v?: string) => (v ? <Tag>{v}</Tag> : "-"),
    },
    {
      title: "问题",
      dataIndex: "prompt_text",
      key: "prompt_text",
      render: (v?: string) => v || "-",
    },
  ];

  return (
    <Card
      title="测评问题集"
      extra={
        <Space>
          <Select<PromptTier>
            value={tier}
            onChange={setTier}
            style={{ width: 160 }}
            options={[
              { value: "basic", label: "basic (20)" },
              { value: "standard", label: "standard (50)" },
              { value: "professional", label: "professional (100)" },
            ]}
          />
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            loading={generating}
            onClick={generate}
          >
            生成测评问题
          </Button>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
            刷新
          </Button>
        </Space>
      }
    >
      {error && (
        <Alert
          type="error"
          showIcon
          message="无法连接后端"
          description={error}
          style={{ marginBottom: 16 }}
        />
      )}
      <Table<GeoPromptOut>
        rowKey="id"
        loading={loading}
        size="small"
        columns={columns}
        dataSource={prompts}
        pagination={{ pageSize: 15 }}
        locale={{ emptyText: "暂无问题，点击“生成测评问题”" }}
      />
    </Card>
  );
}
