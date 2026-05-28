"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Card,
  Button,
  Progress,
  Space,
  Statistic,
  Row,
  Col,
  Table,
  Tag,
  Alert,
  Descriptions,
  Typography,
  message,
} from "antd";
import {
  PlayCircleOutlined,
  ExperimentOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  api,
  ApiError,
  GeoRunProgress,
  ProviderResultOut,
  MentionResultOut,
  GeoReportOut,
  TERMINAL_RUN_STATUSES,
} from "@/lib/api";

const POLL_MS = 2000;

function isTerminal(status?: string | null): boolean {
  return !!status && TERMINAL_RUN_STATUSES.includes(status);
}

function pct(v?: number | null): string {
  return v == null ? "-" : `${(v * 100).toFixed(1)}%`;
}

function sentimentTag(s?: string | null) {
  if (!s) return <Tag>-</Tag>;
  const color =
    s === "positive"
      ? "green"
      : s === "negative"
      ? "red"
      : s === "neutral"
      ? "default"
      : "blue";
  return <Tag color={color}>{s}</Tag>;
}

export default function EvalSection({ merchantId }: { merchantId: string }) {
  const [runId, setRunId] = useState<string | null>(null);
  const [progress, setProgress] = useState<GeoRunProgress | null>(null);
  const [results, setResults] = useState<ProviderResultOut[]>([]);
  const [mentions, setMentions] = useState<MentionResultOut[]>([]);
  const [report, setReport] = useState<GeoReportOut | null>(null);

  const [starting, setStarting] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [reporting, setReporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearPoll = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => clearPoll, [clearPoll]);

  const loadResultsAndMentions = useCallback(async (id: string) => {
    try {
      const [r, m] = await Promise.all([
        api.runResults(id),
        api.runMentions(id),
      ]);
      setResults(r);
      setMentions(m);
    } catch (e) {
      if (e instanceof ApiError) setError(e.message);
    }
  }, []);

  const startPolling = useCallback(
    (id: string) => {
      clearPoll();
      pollRef.current = setInterval(async () => {
        try {
          const p = await api.getGeoRun(id);
          setProgress(p);
          if (isTerminal(p.status)) {
            clearPoll();
            await loadResultsAndMentions(id);
          }
        } catch (e) {
          clearPoll();
          if (e instanceof ApiError) setError(e.message);
        }
      }, POLL_MS);
    },
    [clearPoll, loadResultsAndMentions]
  );

  const startRun = async () => {
    setStarting(true);
    setError(null);
    setReport(null);
    setResults([]);
    setMentions([]);
    try {
      const run = await api.createGeoRun({
        merchant_id: merchantId,
        run_type: "organic_eval",
        providers: ["deepseek"],
        repeat_count: 1,
      });
      setRunId(run.id);
      // Seed progress from create response, then poll for live updates.
      setProgress({
        run_id: run.id,
        status: run.status,
        total_jobs: run.total_jobs ?? 0,
        finished_jobs: run.finished_jobs ?? 0,
        failed_jobs: run.failed_jobs ?? 0,
        progress: 0,
      });
      startPolling(run.id);
      message.success("测评已发起");
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.message);
        message.error(`发起失败：${e.message}`);
      }
    } finally {
      setStarting(false);
    }
  };

  const extract = async () => {
    if (!runId) return;
    setExtracting(true);
    try {
      const res = await api.extractMentions(runId);
      message.success(`已入队 ${res.enqueued} 条提及抽取任务`);
      // Give the worker a moment, then refresh mentions a few times.
      await loadResultsAndMentions(runId);
    } catch (e) {
      if (e instanceof ApiError) message.error(`抽取失败：${e.message}`);
    } finally {
      setExtracting(false);
    }
  };

  const refreshMentions = async () => {
    if (!runId) return;
    await loadResultsAndMentions(runId);
  };

  const generateReport = async () => {
    if (!runId) return;
    setReporting(true);
    try {
      const r = await api.generateReport(runId);
      setReport(r);
      message.success("报告已生成");
    } catch (e) {
      if (e instanceof ApiError) message.error(`生成报告失败：${e.message}`);
    } finally {
      setReporting(false);
    }
  };

  const terminal = isTerminal(progress?.status);
  const percent = progress
    ? progress.total_jobs > 0
      ? Math.round((progress.finished_jobs / progress.total_jobs) * 100)
      : Math.round((progress.progress ?? 0) * 100)
    : 0;

  const resultColumns: ColumnsType<ProviderResultOut> = [
    { title: "Provider", dataIndex: "provider", key: "provider", width: 110 },
    { title: "Model", dataIndex: "model", key: "model", width: 140 },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (v?: string) => (
        <Tag color={v === "success" ? "green" : v === "failed" ? "red" : "blue"}>
          {v || "-"}
        </Tag>
      ),
    },
    {
      title: "原始回答",
      dataIndex: "answer_text",
      key: "answer_text",
      render: (v?: string) => (
        <Typography.Paragraph
          ellipsis={{ rows: 3, expandable: true, symbol: "展开" }}
          style={{ marginBottom: 0 }}
        >
          {v || "-"}
        </Typography.Paragraph>
      ),
    },
  ];

  const mentionColumns: ColumnsType<MentionResultOut> = [
    {
      title: "是否提及",
      dataIndex: "is_mentioned",
      key: "is_mentioned",
      width: 100,
      render: (v?: boolean) =>
        v ? <Tag color="green">是</Tag> : <Tag>否</Tag>,
    },
    {
      title: "排名",
      dataIndex: "rank_position",
      key: "rank_position",
      width: 80,
      render: (v?: number) => (v == null ? "-" : v),
    },
    {
      title: "情感",
      dataIndex: "sentiment",
      key: "sentiment",
      width: 100,
      render: (v?: string) => sentimentTag(v),
    },
    {
      title: "提及品牌",
      dataIndex: "mentioned_brands",
      key: "mentioned_brands",
      render: (v?: Array<Record<string, unknown>>) => {
        if (!v || v.length === 0) return "-";
        return (
          <Space size={[4, 4]} wrap>
            {v.map((b, i) => {
              const name =
                typeof b.name === "string"
                  ? b.name
                  : typeof b.brand === "string"
                  ? b.brand
                  : JSON.stringify(b);
              return <Tag key={i}>{name}</Tag>;
            })}
          </Space>
        );
      },
    },
  ];

  const mentionedCount = mentions.filter((m) => m.is_mentioned).length;

  return (
    <Space direction="vertical" style={{ width: "100%" }} size="middle">
      {error && (
        <Alert type="error" showIcon message="无法连接后端" description={error} />
      )}

      <Card
        title="测评执行"
        extra={
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            loading={starting}
            onClick={startRun}
          >
            发起测评
          </Button>
        }
      >
        {!progress && (
          <Typography.Text type="secondary">
            点击“发起测评”对该商家发起一次 organic_eval 测评（provider: deepseek）。
          </Typography.Text>
        )}
        {progress && (
          <>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Statistic title="状态" value={progress.status ?? "-"} />
              </Col>
              <Col span={6}>
                <Statistic title="总任务" value={progress.total_jobs} />
              </Col>
              <Col span={6}>
                <Statistic title="已完成" value={progress.finished_jobs} />
              </Col>
              <Col span={6}>
                <Statistic title="失败" value={progress.failed_jobs} />
              </Col>
            </Row>
            <Progress
              percent={percent}
              status={
                progress.status === "failed"
                  ? "exception"
                  : terminal
                  ? "success"
                  : "active"
              }
            />
            {terminal && (
              <Space style={{ marginTop: 16 }} wrap>
                <Button
                  icon={<ExperimentOutlined />}
                  loading={extracting}
                  onClick={extract}
                >
                  抽取提及
                </Button>
                <Button onClick={refreshMentions}>刷新结果 / 提及</Button>
                <Button
                  type="primary"
                  icon={<FileTextOutlined />}
                  loading={reporting}
                  onClick={generateReport}
                >
                  生成报告
                </Button>
              </Space>
            )}
          </>
        )}
      </Card>

      {runId && terminal && (
        <Card title={`原始回答（${results.length}）`}>
          <Table<ProviderResultOut>
            rowKey="id"
            size="small"
            columns={resultColumns}
            dataSource={results}
            pagination={{ pageSize: 5 }}
            locale={{ emptyText: "暂无结果" }}
          />
        </Card>
      )}

      {runId && terminal && (
        <Card title={`提及结果（命中 ${mentionedCount} / 共 ${mentions.length}）`}>
          <Table<MentionResultOut>
            rowKey="id"
            size="small"
            columns={mentionColumns}
            dataSource={mentions}
            pagination={{ pageSize: 5 }}
            locale={{ emptyText: "暂无提及，先点击“抽取提及”并刷新" }}
          />
        </Card>
      )}

      {report && runId && (
        <Card title="诊断报告">
          <Descriptions bordered column={3} size="small" style={{ marginBottom: 16 }}>
            <Descriptions.Item label="GEO 分">
              {report.geo_score == null ? "-" : report.geo_score.toFixed(1)}
            </Descriptions.Item>
            <Descriptions.Item label="提及率">
              {pct(report.mention_rate)}
            </Descriptions.Item>
            <Descriptions.Item label="正面率">
              {pct(report.positive_rate)}
            </Descriptions.Item>
          </Descriptions>
          <iframe
            title="report"
            src={api.reportHtmlUrl(runId)}
            style={{
              width: "100%",
              height: 720,
              border: "1px solid #f0f0f0",
              borderRadius: 6,
            }}
          />
        </Card>
      )}
    </Space>
  );
}
