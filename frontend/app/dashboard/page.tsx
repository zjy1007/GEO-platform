"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, Statistic, Row, Col, Alert, Button } from "antd";
import { ShopOutlined } from "@ant-design/icons";
import AppShell from "@/app/components/AppShell";
import { api, ApiError } from "@/lib/api";

export default function DashboardPage() {
  const [count, setCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const merchants = await api.listMerchants(200, 0);
        setCount(merchants.length);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <AppShell>
      {error && (
        <Alert
          type="error"
          showIcon
          message="无法连接后端"
          description={error}
          style={{ marginBottom: 16 }}
        />
      )}
      <Row gutter={16}>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="商家总数"
              value={count ?? 0}
              loading={loading}
              prefix={<ShopOutlined />}
            />
            <Link href="/merchants">
              <Button type="link" style={{ paddingLeft: 0, marginTop: 8 }}>
                查看商家列表 →
              </Button>
            </Link>
          </Card>
        </Col>
      </Row>
    </AppShell>
  );
}
