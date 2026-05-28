"use client";

import { Form, Input, Row, Col } from "antd";
import type { FormInstance } from "antd";
import type { MerchantBase } from "@/lib/api";

// Form values: list fields are edited as comma-separated text and converted
// to string[] on submit via `valuesToMerchant`.
export interface MerchantFormValues {
  name: string;
  category?: string;
  city?: string;
  district?: string;
  address?: string;
  phone?: string;
  website?: string;
  business_hours?: string;
  price_range?: string;
  services?: string;
  target_keywords?: string;
  official_sources?: string;
  competitors?: string;
}

const LIST_FIELDS = [
  "services",
  "target_keywords",
  "official_sources",
  "competitors",
] as const;

function splitCsv(v?: string): string[] | undefined {
  if (!v) return undefined;
  const arr = v
    .split(/[,，]/)
    .map((s) => s.trim())
    .filter(Boolean);
  return arr.length ? arr : undefined;
}

function joinCsv(v?: string[] | null): string {
  return v && v.length ? v.join(", ") : "";
}

/** Convert raw form values into a MerchantBase payload (splitting CSV lists). */
export function valuesToMerchant(v: MerchantFormValues): MerchantBase {
  return {
    name: v.name,
    category: v.category || undefined,
    city: v.city || undefined,
    district: v.district || undefined,
    address: v.address || undefined,
    phone: v.phone || undefined,
    website: v.website || undefined,
    business_hours: v.business_hours || undefined,
    price_range: v.price_range || undefined,
    services: splitCsv(v.services),
    target_keywords: splitCsv(v.target_keywords),
    official_sources: splitCsv(v.official_sources),
    competitors: splitCsv(v.competitors),
  };
}

/** Convert a MerchantBase into form values (joining lists to CSV text). */
export function merchantToValues(m: MerchantBase): MerchantFormValues {
  return {
    name: m.name,
    category: m.category ?? undefined,
    city: m.city ?? undefined,
    district: m.district ?? undefined,
    address: m.address ?? undefined,
    phone: m.phone ?? undefined,
    website: m.website ?? undefined,
    business_hours: m.business_hours ?? undefined,
    price_range: m.price_range ?? undefined,
    services: joinCsv(m.services),
    target_keywords: joinCsv(m.target_keywords),
    official_sources: joinCsv(m.official_sources),
    competitors: joinCsv(m.competitors),
  };
}

export default function MerchantForm({
  form,
}: {
  form: FormInstance<MerchantFormValues>;
}) {
  const csvHelp = "多个值用逗号分隔";
  return (
    <Form form={form} layout="vertical" requiredMark>
      <Form.Item
        name="name"
        label="名称"
        rules={[{ required: true, message: "请输入商家名称" }]}
      >
        <Input placeholder="商家名称" />
      </Form.Item>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item name="category" label="行业 / 类目">
            <Input placeholder="如：火锅、健身房" />
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item name="city" label="城市">
            <Input />
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item name="district" label="区县">
            <Input />
          </Form.Item>
        </Col>
      </Row>
      <Form.Item name="address" label="地址">
        <Input />
      </Form.Item>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item name="phone" label="电话">
            <Input />
          </Form.Item>
        </Col>
        <Col span={16}>
          <Form.Item name="website" label="官网">
            <Input placeholder="https://" />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item name="business_hours" label="营业时间">
            <Input placeholder="如：09:00-22:00" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item name="price_range" label="价格区间">
            <Input placeholder="如：￥100-200/人" />
          </Form.Item>
        </Col>
      </Row>
      {LIST_FIELDS.map((field) => {
        const labels: Record<string, string> = {
          services: "服务项目",
          target_keywords: "目标关键词",
          official_sources: "官方信息源",
          competitors: "竞争对手",
        };
        return (
          <Form.Item
            key={field}
            name={field}
            label={labels[field]}
            extra={csvHelp}
          >
            <Input placeholder={csvHelp} />
          </Form.Item>
        );
      })}
    </Form>
  );
}
