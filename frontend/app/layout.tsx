import type { Metadata } from "next";
import { AntdRegistry } from "@ant-design/nextjs-registry";

export const metadata: Metadata = {
  title: "GEO 商家画像平台",
  description: "AI 搜索曝光测评与诊断报告",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body style={{ margin: 0 }}>
        <AntdRegistry>{children}</AntdRegistry>
      </body>
    </html>
  );
}
