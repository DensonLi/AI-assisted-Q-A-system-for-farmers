import { useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  Layout as AntLayout, Menu, Avatar, Dropdown, Modal, Form,
  Input, Button, Typography, message, Space,
} from "antd";
import {
  MessageOutlined, TeamOutlined, LogoutOutlined,
  KeyOutlined, UserOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../store/auth";
import { changePassword } from "../services/api";

const { Sider, Content, Header } = AntLayout;
const { Text } = Typography;

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, isAdmin } = useAuthStore();
  const [pwdModalOpen, setPwdModalOpen] = useState(false);
  const [pwdLoading, setPwdLoading] = useState(false);
  const [form] = Form.useForm();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const handleChangePwd = async (values: { old_password: string; new_password: string; confirm: string }) => {
    setPwdLoading(true);
    try {
      await changePassword(values.old_password, values.new_password);
      message.success("密码修改成功，请重新登录");
      setPwdModalOpen(false);
      form.resetFields();
      handleLogout();
    } catch (err: any) {
      message.error(err.response?.data?.detail || "密码修改失败");
    } finally {
      setPwdLoading(false);
    }
  };

  const userMenuItems = [
    { key: "pwd", label: "修改密码", icon: <KeyOutlined /> },
    { key: "logout", label: "退出登录", icon: <LogoutOutlined />, danger: true },
  ];

  const sideMenuItems = [
    { key: "/", label: "问答对话", icon: <MessageOutlined /> },
    ...(isAdmin() ? [{ key: "/admin", label: "用户管理", icon: <TeamOutlined /> }] : []),
  ];

  return (
    <AntLayout style={{ minHeight: "100vh" }}>
      <Sider theme="light" style={{ borderRight: "1px solid #f0f0f0" }}>
        <div style={{ padding: "20px 16px 12px", textAlign: "center" }}>
          <div style={{ fontSize: 28 }}>🌱</div>
          <Text strong style={{ fontSize: 13, color: "#389e0d", display: "block" }}>
            种植技巧问答
          </Text>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={sideMenuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <AntLayout>
        <Header
          style={{
            background: "#fff",
            padding: "0 24px",
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            borderBottom: "1px solid #f0f0f0",
            height: 56,
          }}
        >
          <Dropdown
            menu={{
              items: userMenuItems,
              onClick: ({ key }) => {
                if (key === "logout") handleLogout();
                if (key === "pwd") setPwdModalOpen(true);
              },
            }}
            placement="bottomRight"
          >
            <Space style={{ cursor: "pointer" }}>
              <Avatar icon={<UserOutlined />} style={{ backgroundColor: "#52c41a" }} size="small" />
              <Text>{user?.username}</Text>
              {user?.role === "admin" && (
                <Text type="secondary" style={{ fontSize: 12 }}>管理员</Text>
              )}
            </Space>
          </Dropdown>
        </Header>
        <Content style={{ overflow: "auto" }}>
          <Outlet />
        </Content>
      </AntLayout>

      <Modal
        title="修改密码"
        open={pwdModalOpen}
        onCancel={() => { setPwdModalOpen(false); form.resetFields(); }}
        footer={null}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleChangePwd} style={{ marginTop: 16 }}>
          <Form.Item label="原密码" name="old_password" rules={[{ required: true, message: "请输入原密码" }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item label="新密码" name="new_password" rules={[{ required: true, min: 8, message: "新密码至少8位" }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item
            label="确认新密码"
            name="confirm"
            dependencies={["new_password"]}
            rules={[
              { required: true, message: "请再次输入新密码" },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue("new_password") === value) return Promise.resolve();
                  return Promise.reject(new Error("两次密码不一致"));
                },
              }),
            ]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0, textAlign: "right" }}>
            <Button onClick={() => setPwdModalOpen(false)} style={{ marginRight: 8 }}>取消</Button>
            <Button type="primary" htmlType="submit" loading={pwdLoading}>确认修改</Button>
          </Form.Item>
        </Form>
      </Modal>
    </AntLayout>
  );
}
