"use client";

import { useMemo, useState } from "react";
import { Card, Segmented, Progress, Space, Tag, Typography, Empty } from "antd";
import type { Competitor } from "@/lib/api";

type Phase = "overall" | "decision" | "doubt";

const PHASE_OPTIONS = [
  { label: "综合", value: "overall" as const },
  { label: "决策期", value: "decision" as const },
  { label: "质疑期", value: "doubt" as const },
];

// Pull the visibility rate for a competitor under the chosen phase view.
function rateFor(c: Competitor, phase: Phase): number {
  if (phase === "overall") return c.rate ?? 0;
  const ph = c.by_phase?.[phase];
  return ph?.rate ?? 0;
}

interface Props {
  competitors?: Competitor[] | null;
  title?: string;
  // Top-N rows to render (target merchant is always kept). Default 8.
  max?: number;
}

/**
 * 竞品可见度对比图（目标商家 vs 竞品）。
 *
 * NOTE: echarts is not installed in frontend/package.json, so this falls back
 * to a horizontal AntD Progress bar list. The target merchant is highlighted.
 * Install `echarts` + `echarts-for-react` to upgrade to a real bar chart.
 */
export default function CompetitorVisibilityChart({
  competitors,
  title = "竞品可见度对比",
  max = 8,
}: Props) {
  const [phase, setPhase] = useState<Phase>("overall");

  const rows = useMemo(() => {
    const list = (competitors ?? []).slice();
    const sorted = list
      .map((c) => ({ c, value: rateFor(c, phase) }))
      .sort((a, b) => b.value - a.value);
    // Keep the target merchant even if it falls outside the top-N window.
    const top = sorted.slice(0, max);
    const targetIncluded = top.some((r) => r.c.is_target);
    if (!targetIncluded) {
      const target = sorted.find((r) => r.c.is_target);
      if (target) top.push(target);
    }
    return top;
  }, [competitors, phase, max]);

  return (
    <Card
      title={title}
      extra={
        <Segmented
          size="small"
          options={PHASE_OPTIONS}
          value={phase}
          onChange={(v) => setPhase(v as Phase)}
        />
      }
    >
      {rows.length === 0 ? (
        <Empty description="暂无竞品数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <Space direction="vertical" style={{ width: "100%" }} size={12}>
          {rows.map(({ c, value }) => (
            <div key={c.brand}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: 4,
                }}
              >
                <Space size={6}>
                  <Typography.Text strong={!!c.is_target}>
                    {c.brand}
                  </Typography.Text>
                  {c.is_target && <Tag color="blue">本商家</Tag>}
                  {c.avg_rank != null && (
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      均排 {c.avg_rank}
                    </Typography.Text>
                  )}
                </Space>
                <Typography.Text type="secondary">
                  {(value * 100).toFixed(0)}%
                </Typography.Text>
              </div>
              <Progress
                percent={Math.round(value * 100)}
                showInfo={false}
                strokeColor={c.is_target ? "#2f6df6" : "#bfbfbf"}
              />
            </div>
          ))}
        </Space>
      )}
    </Card>
  );
}
