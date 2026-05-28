"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Alert,
  Breadcrumb,
  Button,
  Card,
  Col,
  Row,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import AppShell from "@/app/components/AppShell";
import EvidenceVerificationPanel from "@/app/components/EvidenceVerificationPanel";
import {
  api,
  ApiError,
  MentionResultOut,
  ProviderResultOut,
} from "@/lib/api";

const { Paragraph, Text } = Typography;

interface ResultRow extends ProviderResultOut {
  mention?: MentionResultOut;
}

function phaseTag(phase?: string | null) {
  if (!phase) return null;
  const color = phase === "decision" ? "blue" : phase === "doubt" ? "orange" : "default";
  return <Tag color={color}>{phase}</Tag>;
}

function modeTag(mode?: string | null) {
  if (!mode) return null;
  return <Tag color={mode === "organic" ? "green" : "purple"}>{mode}</Tag>;
}

function channelTag(channel?: string | null) {
  if (!channel) return null;
  return <Tag color={channel === "api" ? "geekblue" : "cyan"}>{channel}</Tag>;
}

function sentimentTag(s?: string | null) {
  if (!s) return <Tag>-</Tag>;
  const color =
    s === "positive" ? "green" : s === "negative" ? "red" : "default";
  return <Tag color={color}>{s}</Tag>;
}

const columns: ColumnsType<ResultRow> = [
  {
    title: "问题",
    key: "prompt",
    width: 280,
    render: (_, r) => (
      <Space direction="vertical" size={4}>
        <Paragraph
          ellipsis={{ rows: 3, expandable: true, symbol: "展开" }}
          style={{ marginBottom: 0, fontSize: 13 }}
        >
          {r.prompt_text || <Text type="secondary">（无问题文本）</Text>}
        </Paragraph>
        <Space size={4}>
          {phaseTag(r.prompt_phase)}
          {modeTag(r.prompt_mode)}
        </Space>
      </Space>
    ),
  },
  {
    title: "平台 / 模型",
    key: "provider_model",
    width: 160,
    render: (_, r) => (
      <Space direction="vertical" size={4}>
        <Text strong>{r.provider ?? "-"}</Text>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {r.model ?? "-"}
        </Text>
        {channelTag(r.channel)}
      </Space>
    ),
  },
  {
    title: "AI 回答",
    dataIndex: "answer_text",
    key: "answer_text",
    render: (v?: string | null) => (
      <Paragraph
        ellipsis={{ rows: 4, expandable: true, symbol: "展开全文" }}
        style={{ marginBottom: 0, maxWidth: 480 }}
      >
        {v || <Text type="secondary">（无回答）</Text>}
      </Paragraph>
    ),
  },
  {
    title: "提及",
    key: "is_mentioned",
    width: 70,
    render: (_, r) =>
      r.mention == null ? (
        <Tag>-</Tag>
      ) : r.mention.is_mentioned ? (
        <Tag color="green">是</Tag>
      ) : (
        <Tag>否</Tag>
      ),
  },
  {
    title: "排名",
    key: "rank",
    width: 60,
    render: (_, r) => (
      <Text>{r.mention?.rank_position == null ? "-" : r.mention.rank_position}</Text>
    ),
  },
  {
    title: "情感",
    key: "sentiment",
    width: 90,
    render: (_, r) => sentimentTag(r.mention?.sentiment),
  },
  {
    title: "提及品牌",
    key: "brands",
    width: 200,
    render: (_, r) => {
      const brands = r.mention?.mentioned_brands;
      if (!brands) return <Text type="secondary">-</Text>;
      const list = Array.isArray(brands) ? brands : Object.values(brands);
      if (list.length === 0) return <Text type="secondary">-</Text>;
      return (
        <Space size={[4, 4]} wrap>
          {list.map((b, i) => {
            const name =
              typeof b === "string"
                ? b
                : typeof (b as Record<string, unknown>).name === "string"
                ? (b as Record<string, unknown>).name as string
                : typeof (b as Record<string, unknown>).brand === "string"
                ? (b as Record<string, unknown>).brand as string
                : JSON.stringify(b);
            return <Tag key={i}>{name}</Tag>;
          })}
        </Space>
      );
    },
  },
  {
    title: "状态",
    dataIndex: "status",
    key: "status",
    width: 90,
    render: (v?: string | null) => (
      <Tag color={v === "success" ? "green" : v === "failed" ? "red" : "blue"}>
        {v ?? "-"}
      </Tag>
    ),
  },
];

export default function RunDetailPage() {
  const params = useParams<{ runId: string }>();
  const router = useRouter();
  const runId = params?.runId;

  const [rows, setRows] = useState<ResultRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!runId) return;
    setLoading(true);
    setError(null);
    try {
      const [results, mentions] = await Promise.all([
        api.runResults(runId),
        api.runMentions(runId),
      ]);
      const mentionMap = new Map<string, MentionResultOut>(
        mentions.map((m) => [m.provider_result_id, m])
      );
      setRows(
        results.map((r) => ({ ...r, mention: mentionMap.get(r.id) }))
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    load();
  }, [load]);

  const mentionedCount = rows.filter((r) => r.mention?.is_mentioned).length;
  const mentionTotal = rows.filter((r) => r.mention != null).length;

  return (
    <AppShell>
      <Space direction="vertical" style={{ width: "100%" }} size="middle">
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => router.back()}>
            返回
          </Button>
          <Breadcrumb
            items={[
              { title: "商家列表" },
              { title: "测评" },
              { title: `AI 原始回答 · ${runId?.slice(0, 8) ?? ""}` },
            ]}
          />
        </Space>

        {error && (
          <Alert
            type="error"
            showIcon
            message="加载失败"
            description={error}
          />
        )}

        {loading ? (
          <Spin style={{ display: "block", marginTop: 48 }} />
        ) : (
          <Card
            title={
              <Space>
                <span>AI 原始回答</span>
                <Tag>{rows.length} 条</Tag>
                {mentionTotal > 0 && (
                  <Tag color="green">
                    提及 {mentionedCount}/{mentionTotal}
                  </Tag>
                )}
              </Space>
            }
            extra={
              <Button size="small" onClick={load}>
                刷新
              </Button>
            }
          >
            <Row gutter={[16, 8]} style={{ marginBottom: 16 }}>
              <Col>
                <Text type="secondary" style={{ fontSize: 13 }}>
                  每行对应一次"问题 × 平台"调用，展示问题文本、AI 完整回答及提及判定结果，用于追溯 GEO 分的来源。
                </Text>
              </Col>
            </Row>
            <Table<ResultRow>
              rowKey="id"
              size="small"
              columns={columns}
              dataSource={rows}
              scroll={{ x: 1300 }}
              pagination={{ pageSize: 20, showSizeChanger: true }}
              locale={{ emptyText: "暂无数据，请先完成测评并抽取提及" }}
            />
          </Card>
        )}
      </Space>
    </AppShell>
  );
}
