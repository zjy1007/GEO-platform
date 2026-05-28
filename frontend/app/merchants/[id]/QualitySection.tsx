"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Card,
  Progress,
  List,
  Alert,
  Tag,
  Space,
  Table,
  Button,
  Row,
  Col,
} from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  api,
  ApiError,
  CompletenessResult,
  NapCheckResult,
  AliasOut,
} from "@/lib/api";

export default function QualitySection({
  merchantId,
}: {
  merchantId: string;
}) {
  const [completeness, setCompleteness] = useState<CompletenessResult | null>(
    null
  );
  const [nap, setNap] = useState<NapCheckResult | null>(null);
  const [aliases, setAliases] = useState<AliasOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [c, n, a] = await Promise.all([
        api.completeness(merchantId),
        api.napCheck(merchantId),
        api.aliases(merchantId),
      ]);
      setCompleteness(c);
      setNap(n);
      setAliases(a);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [merchantId]);

  useEffect(() => {
    load();
  }, [load]);

  const aliasColumns: ColumnsType<AliasOut> = [
    { title: "别名", dataIndex: "alias", key: "alias" },
    {
      title: "类型",
      dataIndex: "alias_type",
      key: "alias_type",
      render: (v?: string) => (v ? <Tag>{v}</Tag> : "-"),
    },
    {
      title: "置信度",
      dataIndex: "confidence",
      key: "confidence",
      render: (v?: number) => (v == null ? "-" : v.toFixed(2)),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: "100%" }} size="middle">
      {error && (
        <Alert type="error" showIcon message="无法连接后端" description={error} />
      )}
      <div style={{ textAlign: "right" }}>
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
          刷新
        </Button>
      </div>

      <Row gutter={16}>
        <Col xs={24} md={10}>
          <Card title="资料完整度" loading={loading}>
            {completeness && (
              <>
                <Progress
                  type="dashboard"
                  percent={completeness.score}
                  format={(p) => `${p}分`}
                />
                {completeness.missing_fields.length > 0 && (
                  <p style={{ marginTop: 12 }}>
                    缺失字段：
                    <Space size={[4, 4]} wrap>
                      {completeness.missing_fields.map((f) => (
                        <Tag color="orange" key={f}>
                          {f}
                        </Tag>
                      ))}
                    </Space>
                  </p>
                )}
                {completeness.suggestions.length > 0 && (
                  <List
                    size="small"
                    header={<strong>改进建议</strong>}
                    dataSource={completeness.suggestions}
                    renderItem={(s) => <List.Item>{s}</List.Item>}
                  />
                )}
              </>
            )}
          </Card>
        </Col>
        <Col xs={24} md={14}>
          <Card title="NAP 一致性检查" loading={loading}>
            {nap && (
              <>
                {nap.consistent ? (
                  <Tag icon={<CheckCircleOutlined />} color="success">
                    一致
                  </Tag>
                ) : (
                  <Tag icon={<CloseCircleOutlined />} color="error">
                    存在不一致
                  </Tag>
                )}
                {nap.issues.length > 0 && (
                  <List
                    style={{ marginTop: 12 }}
                    size="small"
                    dataSource={nap.issues}
                    renderItem={(s) => (
                      <List.Item>
                        <CloseCircleOutlined
                          style={{ color: "#ff4d4f", marginRight: 8 }}
                        />
                        {s}
                      </List.Item>
                    )}
                  />
                )}
              </>
            )}
          </Card>
        </Col>
      </Row>

      <Card title="别名">
        <Table<AliasOut>
          rowKey="id"
          loading={loading}
          size="small"
          columns={aliasColumns}
          dataSource={aliases}
          pagination={false}
          locale={{ emptyText: "暂无别名" }}
        />
      </Card>
    </Space>
  );
}
