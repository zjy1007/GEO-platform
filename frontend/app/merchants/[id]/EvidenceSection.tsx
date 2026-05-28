"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import { PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  api,
  ApiError,
  EvidenceSourceIn,
  EvidenceSourceOut,
  SourceType,
} from "@/lib/api";

const { Text } = Typography;

const SOURCE_TYPE_OPTIONS: { label: string; value: SourceType }[] = [
  { label: "官方网站", value: "official_website" },
  { label: "用户上传", value: "user_upload" },
  { label: "地图", value: "map" },
  { label: "评价", value: "review" },
  { label: "新闻", value: "news" },
  { label: "社交媒体", value: "social" },
  { label: "其他", value: "other" },
];

function trustTag(trust?: number | null) {
  if (trust == null) return <Tag>-</Tag>;
  const color = trust >= 0.8 ? "green" : trust >= 0.5 ? "orange" : "red";
  return <Tag color={color}>{(trust * 100).toFixed(0)}%</Tag>;
}

const columns: ColumnsType<EvidenceSourceOut> = [
  {
    title: "类型",
    dataIndex: "source_type",
    key: "source_type",
    width: 120,
    render: (v?: string | null) => <Tag>{v ?? "-"}</Tag>,
  },
  {
    title: "标题 / URL",
    key: "title_url",
    render: (_, r) => (
      <Space direction="vertical" size={2}>
        <Text>{r.title || <Text type="secondary">（无标题）</Text>}</Text>
        {r.url && (
          <a href={r.url} target="_blank" rel="noopener noreferrer">
            <Text type="secondary" style={{ fontSize: 12 }}>
              {r.url.length > 60 ? r.url.slice(0, 60) + "…" : r.url}
            </Text>
          </a>
        )}
      </Space>
    ),
  },
  {
    title: "可信度",
    key: "trust_level",
    dataIndex: "trust_level",
    width: 90,
    render: (v?: number | null) => trustTag(v),
  },
  {
    title: "抓取时间",
    dataIndex: "retrieved_at",
    key: "retrieved_at",
    width: 160,
    render: (v?: string | null) =>
      v ? (
        <Text style={{ fontSize: 12 }}>{new Date(v).toLocaleString("zh-CN")}</Text>
      ) : (
        <Text type="secondary">-</Text>
      ),
  },
  {
    title: "内容摘要",
    dataIndex: "content_text",
    key: "content_text",
    render: (v?: string | null) =>
      v ? (
        <Typography.Paragraph
          ellipsis={{ rows: 2, expandable: true, symbol: "展开" }}
          style={{ marginBottom: 0, fontSize: 13 }}
        >
          {v}
        </Typography.Paragraph>
      ) : (
        <Text type="secondary">-</Text>
      ),
  },
];

export default function EvidenceSection({ merchantId }: { merchantId: string }) {
  const [sources, setSources] = useState<EvidenceSourceOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form] = Form.useForm<EvidenceSourceIn>();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSources(await api.listEvidence(merchantId));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [merchantId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleAdd = async (values: EvidenceSourceIn) => {
    setAdding(true);
    try {
      const created = await api.addEvidence(merchantId, values);
      setSources((prev) => [created, ...prev]);
      form.resetFields();
      setShowForm(false);
      message.success("证据来源已添加");
    } catch (e) {
      message.error(e instanceof ApiError ? e.message : String(e));
    } finally {
      setAdding(false);
    }
  };

  return (
    <Space direction="vertical" style={{ width: "100%" }} size="middle">
      {error && (
        <Alert type="error" showIcon message="加载失败" description={error} />
      )}

      <Card
        title={`证据来源（${sources.length}）`}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} size="small" onClick={load}>
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              size="small"
              onClick={() => setShowForm((v) => !v)}
            >
              {showForm ? "取消" : "添加证据"}
            </Button>
          </Space>
        }
      >
        {showForm && (
          <Card
            size="small"
            style={{ marginBottom: 16, background: "#fafafa" }}
            bordered
          >
            <Form
              form={form}
              layout="inline"
              onFinish={handleAdd}
              initialValues={{ source_type: "official_website" }}
            >
              <Form.Item name="source_type" label="类型">
                <Select
                  options={SOURCE_TYPE_OPTIONS}
                  style={{ width: 140 }}
                />
              </Form.Item>
              <Form.Item name="url" label="URL">
                <Input placeholder="https://..." style={{ width: 300 }} />
              </Form.Item>
              <Form.Item name="title" label="标题">
                <Input placeholder="可选" style={{ width: 180 }} />
              </Form.Item>
              <Form.Item name="text" label="直接粘贴文本">
                <Input.TextArea
                  placeholder="如无 URL，可直接粘贴证据文本"
                  rows={2}
                  style={{ width: 300 }}
                />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={adding}>
                  提交
                </Button>
              </Form.Item>
            </Form>
          </Card>
        )}
        <Table<EvidenceSourceOut>
          rowKey="id"
          size="small"
          columns={columns}
          dataSource={sources}
          loading={loading}
          pagination={{ pageSize: 10, showSizeChanger: true }}
          locale={{ emptyText: "暂无证据来源，点击“添加证据”录入" }}
        />
      </Card>
    </Space>
  );
}
