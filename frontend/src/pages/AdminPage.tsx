import { useState, useEffect } from "react";
import {
  Table, Button, Modal, Form, Input, Select, Switch,
  Popconfirm, Tag, message, Space, Typography,
} from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, KeyOutlined } from "@ant-design/icons";
import {
  listUsers, createUser, updateUser,
  deleteUser, resetUserPassword,
} from "../services/api";
import { useAuthStore } from "../store/auth";

const { Title } = Typography;

interface User {
  id: number;
  username: string;
  email: string;
  role: "admin" | "user";
  is_active: boolean;
  created_at: string;
}

type ModalMode = "create" | "edit" | "reset_pwd";

export default function AdminPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<ModalMode>("create");
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();
  const currentUser = useAuthStore((s) => s.user);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const { data } = await listUsers();
      setUsers(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadUsers(); }, []);

  const openCreate = () => {
    setModalMode("create");
    setSelectedUser(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (user: User) => {
    setModalMode("edit");
    setSelectedUser(user);
    form.setFieldsValue({ email: user.email, role: user.role, is_active: user.is_active });
    setModalOpen(true);
  };

  const openResetPwd = (user: User) => {
    setModalMode("reset_pwd");
    setSelectedUser(user);
    form.resetFields();
    setModalOpen(true);
  };

  const handleSubmit = async (values: any) => {
    setSubmitting(true);
    try {
      if (modalMode === "create") {
        await createUser(values);
        message.success("用户创建成功");
      } else if (modalMode === "edit" && selectedUser) {
        await updateUser(selectedUser.id, values);
        message.success("用户信息已更新");
      } else if (modalMode === "reset_pwd" && selectedUser) {
        await resetUserPassword(selectedUser.id, values.new_password);
        message.success("密码重置成功");
      }
      setModalOpen(false);
      form.resetFields();
      loadUsers();
    } catch (err: any) {
      message.error(err.response?.data?.detail || "操作失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    await deleteUser(id);
    message.success("用户已删除");
    setUsers((prev) => prev.filter((u) => u.id !== id));
  };

  const modalTitle: Record<ModalMode, string> = {
    create: "新建用户",
    edit: "编辑用户",
    reset_pwd: `重置密码 — ${selectedUser?.username}`,
  };

  const columns = [
    { title: "用户名", dataIndex: "username" },
    { title: "邮箱", dataIndex: "email" },
    {
      title: "角色",
      dataIndex: "role",
      render: (role: string) =>
        role === "admin" ? <Tag color="volcano">管理员</Tag> : <Tag color="blue">普通用户</Tag>,
    },
    {
      title: "状态",
      dataIndex: "is_active",
      render: (v: boolean) => v ? <Tag color="success">正常</Tag> : <Tag color="default">已禁用</Tag>,
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      render: (v: string) => new Date(v).toLocaleDateString("zh-CN"),
    },
    {
      title: "操作",
      render: (_: any, record: User) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
          <Button size="small" icon={<KeyOutlined />} onClick={() => openResetPwd(record)}>重置密码</Button>
          {record.id !== currentUser?.id && (
            <Popconfirm title="确定删除该用户？" onConfirm={() => handleDelete(record.id)}>
              <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>用户管理</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建用户</Button>
      </div>

      <Table
        columns={columns}
        dataSource={users}
        loading={loading}
        rowKey="id"
        pagination={{ pageSize: 20 }}
      />

      <Modal
        title={modalTitle[modalMode]}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); form.resetFields(); }}
        footer={null}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit} style={{ marginTop: 16 }}>
          {modalMode === "create" && (
            <>
              <Form.Item label="用户名" name="username" rules={[{ required: true, message: "请输入用户名" }]}>
                <Input />
              </Form.Item>
              <Form.Item label="邮箱" name="email" rules={[{ required: true, type: "email", message: "请输入有效邮箱" }]}>
                <Input />
              </Form.Item>
              <Form.Item label="初始密码" name="password" rules={[{ required: true, min: 8, message: "密码至少8位" }]}>
                <Input.Password />
              </Form.Item>
            </>
          )}
          {modalMode === "edit" && (
            <>
              <Form.Item label="邮箱" name="email" rules={[{ required: true, type: "email", message: "请输入有效邮箱" }]}>
                <Input />
              </Form.Item>
              <Form.Item label="角色" name="role">
                <Select options={[{ value: "user", label: "普通用户" }, { value: "admin", label: "管理员" }]} />
              </Form.Item>
              <Form.Item label="账户状态" name="is_active" valuePropName="checked">
                <Switch checkedChildren="正常" unCheckedChildren="禁用" />
              </Form.Item>
            </>
          )}
          {modalMode === "reset_pwd" && (
            <>
              <Form.Item label="新密码" name="new_password" rules={[{ required: true, min: 8, message: "密码至少8位" }]}>
                <Input.Password />
              </Form.Item>
              <Form.Item
                label="确认新密码"
                name="confirm"
                dependencies={["new_password"]}
                rules={[
                  { required: true, message: "请确认新密码" },
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
            </>
          )}
          <Form.Item style={{ marginBottom: 0, textAlign: "right" }}>
            <Button onClick={() => setModalOpen(false)} style={{ marginRight: 8 }}>取消</Button>
            <Button type="primary" htmlType="submit" loading={submitting}>确认</Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
