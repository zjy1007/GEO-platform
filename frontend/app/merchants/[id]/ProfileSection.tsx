"use client";

import { useState } from "react";
import {
  Descriptions,
  Button,
  Form,
  Space,
  Card,
  message,
  Tag,
} from "antd";
import { EditOutlined } from "@ant-design/icons";
import MerchantForm, {
  MerchantFormValues,
  merchantToValues,
  valuesToMerchant,
} from "@/app/components/MerchantForm";
import { api, ApiError, MerchantOut } from "@/lib/api";

function listText(v?: string[] | null): React.ReactNode {
  if (!v || v.length === 0) return "-";
  return (
    <Space size={[4, 4]} wrap>
      {v.map((item, i) => (
        <Tag key={i}>{item}</Tag>
      ))}
    </Space>
  );
}

export default function ProfileSection({
  merchant,
  onUpdated,
}: {
  merchant: MerchantOut;
  onUpdated: (m: MerchantOut) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm<MerchantFormValues>();

  const startEdit = () => {
    form.setFieldsValue(merchantToValues(merchant));
    setEditing(true);
  };

  const save = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const updated = await api.updateMerchant(
        merchant.id,
        valuesToMerchant(values)
      );
      message.success("已保存");
      onUpdated(updated);
      setEditing(false);
    } catch (e) {
      if (e instanceof ApiError) message.error(`保存失败：${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  if (editing) {
    return (
      <Card
        title="编辑商家资料"
        extra={
          <Space>
            <Button onClick={() => setEditing(false)}>取消</Button>
            <Button type="primary" loading={saving} onClick={save}>
              保存
            </Button>
          </Space>
        }
      >
        <MerchantForm form={form} />
      </Card>
    );
  }

  return (
    <Card
      extra={
        <Button icon={<EditOutlined />} onClick={startEdit}>
          编辑
        </Button>
      }
    >
      <Descriptions bordered column={2} size="small">
        <Descriptions.Item label="名称" span={2}>
          {merchant.name}
        </Descriptions.Item>
        <Descriptions.Item label="行业">
          {merchant.category || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="状态">
          {merchant.status ? <Tag color="blue">{merchant.status}</Tag> : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="城市">
          {merchant.city || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="区县">
          {merchant.district || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="地址" span={2}>
          {merchant.address || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="电话">
          {merchant.phone || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="官网">
          {merchant.website || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="营业时间">
          {merchant.business_hours || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="价格区间">
          {merchant.price_range || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="服务项目" span={2}>
          {listText(merchant.services)}
        </Descriptions.Item>
        <Descriptions.Item label="目标关键词" span={2}>
          {listText(merchant.target_keywords)}
        </Descriptions.Item>
        <Descriptions.Item label="官方信息源" span={2}>
          {listText(merchant.official_sources)}
        </Descriptions.Item>
        <Descriptions.Item label="竞争对手" span={2}>
          {listText(merchant.competitors)}
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
}
