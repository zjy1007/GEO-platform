"use client";

import { useCallback, useState } from "react";
import {
  Button,
  Card,
  Progress,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import { CheckCircleOutlined, SyncOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { api, ApiError, VerificationResultOut } from "@/lib/api";

const { Text, Paragraph } = Typography;

function statusTag(status?: string | null) {
  if (!status) return <Tag>-</Tag>;
  const map: Record<string, string> = {
    supported: "green",
    unsupported: "red",
    contradicted: "volcano",
    pending: "default",
    error: "red",
  };
  return <Tag color={map[status] ?? "default"}>{status}</Tag>;
}

const columns: ColumnsType<VerificationResultOut> = [
  {
    title: "声明文本",
    dataIndex: "claim_text",
    key: "claim_text",
    render: (v?: string | null) => (
      <Paragraph
        ellipsis={{ rows: 3, expandable: true, symbol: "展开" }}
        style={{ marginBottom: 0, fontSize: 13 }}
      >
        {v || <Text type="secondary">（无文本）</Text>}
      </Paragraph>
    ),
  },
  {
    title: "验证状态",
    dataIndex: "verification_status",
    key: "verification_status",
    width: 120,
    render: (v?: string | null) => statusTag(v),
  },
  {
    title: "置信度",
    dataIndex: "confidence",
    key: "confidence",
    width: 110,
    render: (v?: number | null) =>
      v == null ? (
        <Text type="secondary">-</Text>
      ) : (
        <Progress
          percent={Math.round(v * 100)}
          size="small"
          strokeColor={v >= 0.8 ? "#52c41a" : v >= 0.5 ? "#faad14" : "#ff4d4f"}
        />
      ),
  },
  {
    title: "解释",
    dataIndex: "explanation",
    key: "explanation",
    render: (v?: string | null) => (
      <Paragraph
        ellipsis={{ rows: 2, expandable: true, symbol: "展开" }}
        style={{ marginBottom: 0, fontSize: 13 }}
      >
        {v || <Text type="secondary">-</Text>}
      </Paragraph>
    ),
  },
];

interface Props {
  runId: string;
}

export default function EvidenceVerificationPanel({ runId }: Props) {
  const [verifications, setVerifications] = useState<VerificationResultOut[]>([]);
  const [verifying, setVerifying] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      setVerifications(await api.runVerifications(runId));
    } catch (e) {
      message.error(e instanceof ApiError ? e.message : String(e));
    } finally {
      setRefreshing(false);
    }
  }, [runId]);

  const triggerVerify = async () => {
    setVerifying(true);
    try {
      const res = await api.verifyRun(runId);
      message.success(`已入队 ${res.enqueued} 条声明验证任务`);
      // Brief wait then refresh.
      await refresh();
    } catch (e) {
      message.error(e instanceof ApiError ? e.message : String(e));
    } finally {
      setVerifying(false);
    }
  };

  const supportedCount = verifications.filter(
    (v) => v.verification_status === "supported"
  ).length;
  const contradictedCount = verifications.filter(
    (v) => v.verification_status === "contradicted"
  ).length;

  return (
    <Card
      title={
        <Space>
          <span>声明验证</span>
          {verifications.length > 0 && (
            <>
              <Tag color="green">支持 {supportedCount}</Tag>
              <Tag color="volcano">矛盾 {contradictedCount}</Tag>
              <Tag>共 {verifications.length}</Tag>
            </>
          )}
        </Space>
      }
      extra={
        <Space>
          <Button
            icon={<SyncOutlined />}
            size="small"
            loading={refreshing}
            onClick={refresh}
          >
            刷新验证结果
          </Button>
          <Button
            type="primary"
            icon={<CheckCircleOutlined />}
            size="small"
            loading={verifying}
            onClick={triggerVerify}
          >
            触发验证
          </Button>
        </Space>
      }
    >
      <Table<VerificationResultOut>
        rowKey="id"
        size="small"
        columns={columns}
        dataSource={verifications}
        pagination={{ pageSize: 10, showSizeChanger: true }}
        locale={{
          emptyText: "暂无验证结果，点击“触发验证”并等待 worker 处理后刷新",
        }}
      />
    </Card>
  );
}
