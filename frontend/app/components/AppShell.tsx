"use client";

import { useRouter, usePathname } from "next/navigation";
import { Layout, Menu, Typography } from "antd";
import { ShopOutlined, DashboardOutlined } from "@ant-design/icons";

const { Header, Sider, Content } = Layout;

const NAV = [
  { key: "/merchants", icon: <ShopOutlined />, label: "商家列表" },
  { key: "/dashboard", icon: <DashboardOutlined />, label: "Dashboard" },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  // Highlight the top-level section the current route belongs to.
  const selected = pathname?.startsWith("/dashboard")
    ? "/dashboard"
    : "/merchants";

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider breakpoint="lg" collapsedWidth="0" theme="dark">
        <div
          style={{
            color: "#fff",
            fontWeight: 600,
            fontSize: 15,
            padding: "16px 20px",
            whiteSpace: "nowrap",
            overflow: "hidden",
          }}
        >
          GEO 商家画像
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selected]}
          items={NAV}
          onClick={({ key }) => router.push(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ background: "#fff", paddingInline: 24 }}>
          <Typography.Title level={4} style={{ margin: "16px 0" }}>
            AI 搜索曝光测评与诊断报告
          </Typography.Title>
        </Header>
        <Content style={{ margin: 24 }}>{children}</Content>
      </Layout>
    </Layout>
  );
}
