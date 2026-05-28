"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Table,
  Button,
  Modal,
  Form,
  Card,
  Alert,
  Tag,
  Space,
  message,
} from "antd";
import { PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import AppShell from "@/app/components/AppShell";
import MerchantForm, {
  MerchantFormValues,
  valuesToMerchant,
} from "@/app/components/MerchantForm";
import { api, ApiError, MerchantOut } from "@/lib/api";

function statusTag(status?: string | null) {
  if (!status) return <Tag>未知</Tag>;
  const color =
    status === "active"
      ? "green"
      : status === "archived" || status === "inactive"
      ? "default"
      : "blue";
  return <Tag color={color}>{status}</Tag>;
}

export default function MerchantsPage() {
  const router = useRouter();
  const [data, setData] = useState<MerchantOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm<MerchantFormValues>();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await api.listMerchants());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const created = await api.createMerchant(valuesToMerchant(values));
      message.success("商家已创建");
      setModalOpen(false);
      form.resetFields();
      router.push(`/merchants/${created.id}`);
    } catch (e) {
      if (e instanceof ApiError) message.error(`创建失败：${e.message}`);
      // form validation errors are handled by antd inline
    } finally {
      setSaving(false);
    }
  };

  const columns: ColumnsType<MerchantOut> = [
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
      render: (v: string) => <strong>{v}</strong>,
    },
    {
      title: "行业",
      dataIndex: "category",
      key: "category",
      render: (v?: string) => v || "-",
    },
    {
      title: "城市",
      dataIndex: "city",
      key: "city",
      render: (_: unknown, r) =>
        [r.city, r.district].filter(Boolean).join(" / ") || "-",
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (v?: string) => statusTag(v),
    },
  ];

  return (
    <AppShell>
      <Card
        title="商家列表"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setModalOpen(true)}
            >
              新建商家
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
        <Table<MerchantOut>
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={data}
          onRow={(record) => ({
            onClick: () => router.push(`/merchants/${record.id}`),
            style: { cursor: "pointer" },
          })}
          pagination={{ pageSize: 20, showSizeChanger: false }}
        />
      </Card>

      <Modal
        title="新建商家"
        open={modalOpen}
        onOk={handleCreate}
        confirmLoading={saving}
        onCancel={() => setModalOpen(false)}
        okText="创建"
        cancelText="取消"
        width={720}
        destroyOnClose
      >
        <MerchantForm form={form} />
      </Modal>
    </AppShell>
  );
}
