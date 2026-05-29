"use client";

import { useEffect } from "react";
import Link from "next/link";
import {
  Drawer,
  Progress,
  Row,
  Col,
  Statistic,
  Space,
  Button,
  Alert,
  Typography,
} from "antd";
import {
  ExperimentOutlined,
  FileTextOutlined,
  EyeOutlined,
} from "@ant-design/icons";
import { useRunProgress } from "./useRunProgress";

interface Props {
  open: boolean;
  runId: string | null;
  onClose: () => void;
  // Optional shortcut handlers (reuse the parent's extract/report actions).
  onExtract?: () => void;
  onGenerateReport?: () => void;
  extracting?: boolean;
  reporting?: boolean;
}

/**
 * Controlled Drawer that polls a geo-run's progress (via useRunProgress) and
 * shows status / totals / a progress bar. Once the run reaches a terminal
 * state it surfaces quick entry points: 抽取提及 / 生成报告 / 查看原始回答.
 */
export default function RunProgressDrawer({
  open,
  runId,
  onClose,
  onExtract,
  onGenerateReport,
  extracting,
  reporting,
}: Props) {
  const { progress, terminal, percent, error, startPolling, clearPoll } =
    useRunProgress();

  // Start polling whenever the drawer opens for a run; stop when it closes.
  useEffect(() => {
    if (open && runId) {
      startPolling(runId);
    } else {
      clearPoll();
    }
    return clearPoll;
  }, [open, runId, startPolling, clearPoll]);

  return (
    <Drawer
      title="测评进度"
      width={420}
      open={open}
      onClose={onClose}
      destroyOnClose
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

      {!progress && (
        <Typography.Text type="secondary">正在获取进度…</Typography.Text>
      )}

      {progress && (
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Row gutter={16}>
            <Col span={12}>
              <Statistic title="状态" value={progress.status ?? "-"} />
            </Col>
            <Col span={12}>
              <Statistic title="总任务" value={progress.total_jobs} />
            </Col>
            <Col span={12}>
              <Statistic title="已完成" value={progress.finished_jobs} />
            </Col>
            <Col span={12}>
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
            <Space direction="vertical" style={{ width: "100%" }}>
              <Typography.Text type="secondary">测评已结束，可继续：</Typography.Text>
              <Space wrap>
                {onExtract && (
                  <Button
                    icon={<ExperimentOutlined />}
                    loading={extracting}
                    onClick={onExtract}
                  >
                    抽取提及
                  </Button>
                )}
                {onGenerateReport && (
                  <Button
                    type="primary"
                    icon={<FileTextOutlined />}
                    loading={reporting}
                    onClick={onGenerateReport}
                  >
                    生成报告
                  </Button>
                )}
                {runId && (
                  <Link href={`/runs/${runId}`}>
                    <Button icon={<EyeOutlined />}>查看原始回答</Button>
                  </Link>
                )}
              </Space>
            </Space>
          )}
        </Space>
      )}
    </Drawer>
  );
}
