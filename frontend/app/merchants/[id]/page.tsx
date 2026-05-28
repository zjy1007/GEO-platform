"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Tabs,
  Spin,
  Alert,
  Breadcrumb,
  Space,
  Typography,
  Button,
} from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import AppShell from "@/app/components/AppShell";
import { api, ApiError, MerchantOut } from "@/lib/api";
import ProfileSection from "./ProfileSection";
import QualitySection from "./QualitySection";
import PromptsSection from "./PromptsSection";
import EvalSection from "./EvalSection";
import EvidenceSection from "./EvidenceSection";

export default function MerchantDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params?.id;

  const [merchant, setMerchant] = useState<MerchantOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setMerchant(await api.getMerchant(id));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <AppShell>
      <Space direction="vertical" style={{ width: "100%" }} size="middle">
        <Space>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => router.push("/merchants")}
          >
            返回
          </Button>
          <Breadcrumb
            items={[
              { title: "商家列表" },
              { title: merchant?.name ?? id },
            ]}
          />
        </Space>

        {error && (
          <Alert type="error" showIcon message="无法连接后端" description={error} />
        )}

        {loading && !merchant ? (
          <Spin style={{ display: "block", marginTop: 48 }} />
        ) : merchant && id ? (
          <>
            <Typography.Title level={3} style={{ marginBottom: 0 }}>
              {merchant.name}
            </Typography.Title>
            <Tabs
              defaultActiveKey="profile"
              destroyInactiveTabPane
              items={[
                {
                  key: "profile",
                  label: "资料",
                  children: (
                    <ProfileSection merchant={merchant} onUpdated={setMerchant} />
                  ),
                },
                {
                  key: "quality",
                  label: "质量诊断",
                  children: <QualitySection merchantId={id} />,
                },
                {
                  key: "prompts",
                  label: "问题集",
                  children: <PromptsSection merchantId={id} />,
                },
                {
                  key: "eval",
                  label: "测评",
                  children: <EvalSection merchantId={id} />,
                },
                {
                  key: "evidence",
                  label: "证据中心",
                  children: <EvidenceSection merchantId={id} />,
                },
              ]}
            />
          </>
        ) : null}
      </Space>
    </AppShell>
  );
}
